#!/usr/bin/env python3
"""
build_surah_similarity.py — the offline intra-surah similarity build.

Answers, once and for every surah, «which verses of THIS surah are close to each
other?» and writes the answer to `data/derived/surah_similarity.json`, which
`GET /surah/{number}/similar` serves without loading any model. The design is
`openspec/changes/add-surah-similar-verses/design.md`; the decisions it fixes
are applied here with no further choice:

  * D2 — two gates, not a blend: a pair must pass the SYNTACTIC gate
    (`syn ≥ σ`) AND the SEMANTIC gate (`sem ≥ τ_sem`), where
    `sem = (w_ce·ce + w_dense·dense) × (floor + (1 − floor)·cov)`; pairs that
    pass both rank by `score = sem × syn`. Between two VERBATIM-identical verses
    (equal `qac.ayah_words()` tuples) dense is ignored — `sem = ce × (…)` — and
    the candidate cap ranks them on coverage alone (amendment of 2026-10-02).
  * D3 — the syntactic signature: one `(segs, stem)` element per QAC word,
    compared by unit-cost Levenshtein over the element sequences. The treebank
    role was removed from the element before the first build (design.md,
    amendment of 2026-10-02); `qac_syntax.json` is not read.
  * D4 — tool words out of the root signal (`word_function.json` + the
    `SimilarVerses` stoplist).
  * D5 — `|Δayah| = 1` pairs are dropped before scoring.
  * D6 — cheap gates first: syntax on every pair, then dense/cov, then at most
    M pairs per verse go to the cross-encoder.
  * D8 — groups are the components of the mutual-neighbour graph above τ.
  * D10 — the file layout, schema 1.

The parameters below are the FROZEN values of design.md «Frozen parameters»,
fixed against the gold set before any pair was scored. Changing one is a
decision to record there (task 4.3), never a tuning knob.

Needs the backend STOPPED: the verse vectors are read out of the embedded Qdrant,
which takes an exclusive file lock. The script checks that lock before loading
anything and refuses with a clear message when it is held.

    python scripts/build_surah_similarity.py              # full build (resumes)
    python scripts/build_surah_similarity.py --dry-run    # syntax gate only, no lock/model
    python scripts/build_surah_similarity.py --surahs 55,108   # checkpoint a few surahs
    python scripts/build_surah_similarity.py --fresh      # ignore existing checkpoints
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arabic_text import normalize_search  # noqa: E402
from quran_data import loaders, paths  # noqa: E402
from retrieval.similar_verses import STOPWORDS, SimilarVerses  # noqa: E402

# ── frozen parameters (design.md «Frozen parameters», task 1.4) ───────────
SCHEMA = loaders.SURAH_SIMILARITY_SCHEMA
K = 10
M = 30
W_CE = 0.7
W_DENSE = 0.3
FLOOR = 0.25
SIGMA = 2 / 3
SIGMA_EPS = 1e-9          # syn ≥ σ − ε: `1 − 3/9` and `2/3` differ in the last bit
TAU_SEM = 0.125
TAU_GROUP = 0.4
# Task 3.6 as written: a neighbour is stored only when the two verses share at
# least one content root. Recorded in the header so the rule is visible; the
# gold positives it cannot reach (design D8 «Open point») are a reported result.
REQUIRE_SHARED_ROOT = True
DECIMALS = 4              # stored floats; two builds must be byte-identical
CE_BATCH = 32

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
GOLD_JSON = ROOT / "tests" / "eval" / "surah_similarity_gold.json"
REBUILD = "python scripts/build_surah_similarity.py"
# What a checkpoint was computed FROM, beyond the header's parameters: a
# checkpoint is reused only when these, this file's own source, the stoplist and
# the verse vectors are unchanged too — otherwise a resume after a code fix or an
# input rebuild would assemble surahs computed under two different builds into
# one file whose header claims a single one.
CHECKPOINT_INPUTS = ("MORPHOLOGY_JSON", "ROOTS_RESOLVED_JSON", "WORD_FUNCTION_JSON",
                     "QAC_MORPHOLOGY_TXT", "VERSES_FINAL_JSON")
# Which D3 element the signature uses, recorded in the header (and so in the
# checkpoint digest): a checkpoint computed under another element is stale.
SIGNATURE = "segs+stem"
# Amendment of 2026-10-02 (design.md): dense is not a signal between two verses
# whose Arabic is verbatim identical. The E5 passage embeds the FR/EN
# translations beside the Arabic, so whatever dense measures between identical
# Arabic texts is translation variance, not the verses. Recorded in the header.
DENSE_ON_VERBATIM = "ignored"

# D3 step 2: the N-tag tokens that ARE a part of speech. Derivation and
# inflection tokens (ACT_PCPL, PASS_PCPL, VN, INDEF, P) are deliberately absent.
N_POS = ("PN", "ADJ", "PRON", "DEM", "REL", "T", "LOC", "NV", "INTG", "COND", "ADDR")
_N_POS_SET = frozenset(N_POS)
_ASPECTS = ("PERF", "IMPF", "IMPV")
_CASES = ("NOM", "ACC", "GEN")

Element = tuple  # (segs: tuple[str, ...], stem: tuple[str, ...])


# ═══════════════════════════════════════════════════════════════════════════
#  Pure functions — importable by tests, no disk, no model
# ═══════════════════════════════════════════════════════════════════════════

def _features(raw: str) -> list[str]:
    return [t for t in raw.split("|") if t]


def segment_label(tag: str, feats: Sequence[str]) -> str:
    """D3 step 2: one `segs` label for one segment."""
    if tag == "P":
        first = feats[0] if feats else ""
        if not first or first.startswith(("ROOT:", "LEM:")):
            raise ValueError(f"P segment does not open with its particle tag: {feats!r}")
        return "P:" + first
    if tag == "N":
        for t in feats:
            if t in _N_POS_SET:
                return "N:" + t
        return "N"
    if tag == "V":
        return "V"
    raise ValueError(f"unknown QAC tag {tag!r}")


def stem_feature(tag: str, feats: Sequence[str]) -> str:
    """D3 step 3: the stem string of one STEM segment (no PREF, no SUFF)."""
    if tag == "V":
        aspect = next((t for t in feats if t in _ASPECTS), "")
        mood = next((t[5:] for t in feats if t.startswith("MOOD:")), "")
        return f"{aspect}.{mood}" if mood else aspect
    if tag == "N":
        return next((t for t in feats if t in _CASES), "")
    return ""


def word_element(segments: Sequence[tuple[str, str]]) -> Element:
    """One word's element from its `(tag, features)` segments in file order."""
    segs: list[str] = []
    stem: list[str] = []
    for tag, raw in segments:
        feats = _features(raw)
        segs.append(segment_label(tag, feats))
        if "PREF" not in feats and "SUFF" not in feats:
            stem.append(stem_feature(tag, feats))
    return (tuple(segs), tuple(stem))


def build_signatures(records: Iterable) -> dict[tuple[int, int], tuple[Element, ...]]:
    """D3: `{(surah, ayah): (element, …)}` over every word QAC records.

    `records` yields `quran_data.qac.Record`s (file order).
    """
    words: dict[tuple[int, int], dict[int, list[tuple[str, str]]]] = defaultdict(dict)
    for rec in records:
        words[(rec.surah, rec.ayah)].setdefault(rec.word, []).append((rec.tag, rec.features))
    out: dict[tuple[int, int], tuple[Element, ...]] = {}
    for (s, a), by_word in words.items():
        out[(s, a)] = tuple(word_element(by_word[w]) for w in sorted(by_word))
    return out


def levenshtein(a: Sequence, b: Sequence) -> int:
    """Unit-cost edit distance; elements equal only when wholly equal."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def syn_similarity(a: Sequence, b: Sequence) -> float:
    """`1 − lev(A, B) / max(|A|, |B|)` — symmetric, in [0, 1], 1 when identical."""
    longest = max(len(a), len(b))
    if longest == 0:
        return 1.0
    return 1.0 - levenshtein(a, b) / longest


def passes_syntax(syn: float, sigma: float = SIGMA) -> bool:
    return syn >= sigma - SIGMA_EPS


def cov_similarity(a: frozenset, b: frozenset, idf: dict[str, float]) -> float:
    """IDF-weighted Jaccard of two content-root sets; a root with no weight counts 0."""
    union = sum(idf.get(r, 0.0) for r in a | b)
    if union <= 0:
        return 0.0
    return sum(idf.get(r, 0.0) for r in a & b) / union


def sem_score(ce: float, dense: float | None, cov: float) -> float:
    """D2: `(w_ce·ce + w_dense·dense) × (floor + (1 − floor)·cov)`.

    `dense=None` means dense is ignored (a verbatim pair): the base is `ce` alone.
    """
    base = ce if dense is None else W_CE * ce + W_DENSE * dense
    return base * (FLOOR + (1 - FLOOR) * cov)


def percentile_ranks(values: Sequence[float]) -> list[float]:
    """Rank-normalise to [0, 1]: average rank of ties, `(r − 1)/(n − 1)`.

    The median maps to 0.5 (what τ_sem's justification relies on); a single
    value is its own median, 0.5.
    """
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [0.5]
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2  # zero-based average rank
        for k in range(i, j + 1):
            ranks[order[k]] = avg / (n - 1)
        i = j + 1
    return ranks


def rnd(x: float) -> float:
    """The one rounding every stored float goes through."""
    return round(float(x), DECIMALS)


def sort_neighbours(entries: list[dict]) -> list[dict]:
    """Score descending, ayah ascending — on the STORED (rounded) score."""
    return sorted(entries, key=lambda e: (-e["s"], e["a"]))


def compute_groups(neighbours: dict[int, list[dict]], tau: float = TAU_GROUP) -> list[dict]:
    """D8: components (size ≥ 2) of the graph of MUTUAL stored pairs with s ≥ τ.

    `neighbours` is `{ayah: [entry, …]}` with each entry's `a` and `s`. Groups
    come out ordered by mean internal edge score descending, then first ayah.
    """
    listed = {a: {e["a"]: e["s"] for e in lst} for a, lst in neighbours.items()}
    edges: dict[tuple[int, int], float] = {}
    for a, row in listed.items():
        for b, s in row.items():
            if a < b and a in listed.get(b, {}) and s >= tau:
                edges[(a, b)] = s
    parent: dict[int, int] = {}

    def find(x: int) -> int:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    members: dict[int, list[int]] = defaultdict(list)
    for x in parent:
        members[find(x)].append(x)
    groups = []
    for root_, ayahs in members.items():
        if len(ayahs) < 2:
            continue
        ayahs.sort()
        inside = [s for (a, b), s in edges.items() if find(a) == root_]
        groups.append({"ayahs": ayahs, "strength": rnd(sum(inside) / len(inside))})
    groups.sort(key=lambda g: (-g["strength"], g["ayahs"][0]))
    return groups


def candidate_pairs(ayahs: Sequence[int]) -> Iterator[tuple[int, int]]:
    """Every unordered non-consecutive pair (D5), `a < b`."""
    ordered = sorted(ayahs)
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            if b - a != 1:
                yield a, b


def cap_pairs(survivors: dict[tuple[int, int], tuple[float | None, float]], m: int) -> set[tuple[int, int]]:
    """D6 step 4: per verse, keep at most `m` survivors by `max(dense rank, cov rank)`.

    `survivors` maps `(a, b)` to `(dense, cov)`. A pair is kept when EITHER of
    its verses keeps it. Ranks are 1-based, best first; ties in a verse's
    ordering break on `min` of the two ranks, then the partner's ayah. A pair
    whose dense is `None` (verbatim: dense ignored) ranks on its cov rank alone.
    """
    per_verse: dict[int, list[tuple[int, float, float]]] = defaultdict(list)
    for (a, b), (d, c) in survivors.items():
        per_verse[a].append((b, d, c))
        per_verse[b].append((a, d, c))
    kept: set[tuple[int, int]] = set()
    for v, rows in per_verse.items():
        if len(rows) <= m:
            chosen = [p for p, _, _ in rows]
        else:
            with_d = [t for t in rows if t[1] is not None]
            by_d = {p: i for i, (p, _, _) in enumerate(sorted(with_d, key=lambda t: (-t[1], t[0])), 1)}
            by_c = {p: i for i, (p, _, _) in enumerate(sorted(rows, key=lambda t: (-t[2], t[0])), 1)}
            d_rank = lambda p: by_d.get(p, by_c[p])  # noqa: E731 — dense ignored: cov alone
            ranked = sorted(rows, key=lambda t: (max(d_rank(t[0]), by_c[t[0]]),
                                                 min(d_rank(t[0]), by_c[t[0]]), t[0]))
            chosen = [p for p, _, _ in ranked[:m]]
        for p in chosen:
            kept.add((min(v, p), max(v, p)))
    return kept


def select_neighbours(scored: dict[tuple[int, int], dict], ayahs: Sequence[int],
                      k: int = K) -> dict[int, list[dict]]:
    """Each verse's top-K among the pairs that passed both gates.

    `scored[(a, b)]` holds the pair's rounded signals and `roots` (computed ONCE
    per unordered pair, so both directions carry the same values).

    WHICH K are kept and in WHICH ORDER they are listed are two rules. Kept: score
    descending, then the NEAREST ayah — a verbatim refrain ties on every signal
    (al-Raḥmān's has 31 occurrences for 10 slots), and keeping the lowest ayah
    numbers would give every late occurrence the same ten early partners, none of
    which lists it back, so it could never join the refrain's group. Nearness is
    symmetric, so tied occurrences keep each other and the series stays one
    component. Listed: score descending, ayah ascending (the spec's order).
    """
    lists: dict[int, list[dict]] = {a: [] for a in ayahs}
    for (a, b), sig in scored.items():
        lists[a].append({"a": b, **sig})
        lists[b].append({"a": a, **sig})
    out = {}
    for a, lst in lists.items():
        kept = sorted(lst, key=lambda e: (-e["s"], abs(e["a"] - a), e["a"]))[:k]
        out[a] = sort_neighbours(kept)
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  Inputs — content roots, signatures, vectors, cross-encoder
# ═══════════════════════════════════════════════════════════════════════════

def root_idf(index: dict, n_verses: int) -> dict[str, float]:
    """IDF per root, the formula `SimilarVerses.query_root_idf` applies.

    A root no word holds as primary (empty `verses`, e.g. نوس) carries no
    weight — the same skip, for the same reason.
    """
    out: dict[str, float] = {}
    for root_, entry in index.items():
        if entry.get("verses"):
            df = entry.get("count") or len(entry["verses"])
            out[root_] = math.log(n_verses / max(df, 1))
    return out


_LEM_RE = re.compile(r"LEM:([^|]+)")


def _norm(text: str) -> str:
    return normalize_search(text).replace(" ", "")


def function_nouns(records: Iterable) -> frozenset[str]:
    """The stoplist tokens that name a ROOTED function noun in QAC.

    The `SimilarVerses` stoplist is written for typed, undiacritised queries, so
    each entry is ambiguous on its own: `ام` is the particle أَمْ and the noun أُمّ
    «mother», `من` is مِن and مَنّ «manna», `علي` is عَلَى and عَلِيّ. Only a
    rooted word can put a root into a verse, so the entries that matter here are
    those QAC writes as rooted nouns (كُلّ، بَعْد، قَبْل، بَيْن، عِند، بَعْض، غَيْر،
    دُون …). An entry that is ALSO the lemma of a rootless word (a particle or a
    pronoun) is the particle's spelling, and its rooted homograph keeps its root.
    """
    rooted: set[str] = set()
    rootless: set[str] = set()
    for rec in records:
        m = _LEM_RE.search(rec.features)
        if not m:
            continue
        key = _norm(m.group(1))
        if key not in STOPWORDS:
            continue
        if "ROOT:" in rec.features:
            if rec.tag == "N":
                rooted.add(key)
        else:
            rootless.add(key)
    return frozenset(rooted - rootless)


def function_word_refs(records: Iterable) -> frozenset[str]:
    """`s:a:w` refs whose root-bearing segment is a stoplist function noun.

    Judged on QAC's own segmentation and lemma, never on the written letters, so
    a clitic or a pronoun suffix can neither hide one (`وَكُلٌّ`, `كُلَّهَا` are
    كُلّ) nor invent one (`مَنَنَّا` is the verb مَنَّ, not مِن). Verbs never count.
    Accepted cost: rare rooted nouns spelt like a function noun go with it
    (بُعْد «distance», قِبَل / قُبُل, كَلّ, بَيِّن — 16 of 1 727 in the shipped corpus).
    """
    records = tuple(records)
    nouns = function_nouns(records)
    out = set()
    for rec in records:
        if rec.tag != "N" or "ROOT:" not in rec.features:
            continue
        m = _LEM_RE.search(rec.features)
        if m and _norm(m.group(1)) in nouns:
            out.add(f"{rec.surah}:{rec.ayah}:{rec.word}")
    return frozenset(out)


def content_root_sets(index: dict, resolved: dict, tools: dict, function_words: frozenset,
                      verses: Iterable[tuple[int, int]]) -> dict[tuple[int, int], frozenset]:
    """D4: `{(surah, ayah): content roots}` for every verse in `verses`.

    The roots a verse holds come from `LexicalRetriever.index` (`morphology.json`,
    canonical hamza-bearing keys). A root is dropped when EVERY word of the verse
    carrying it as primary (`roots_resolved.json`) is a grammatical tool
    (`word_function.json`) or a stoplist function noun (`function_word_refs`). A root the
    index places in a verse with no carrying word found there is kept — there is
    nothing to filter on (one case today: أمم in 20:94).
    """
    by_verse: dict[str, set[str]] = defaultdict(set)
    for root_, entry in index.items():
        for vid in entry.get("verses", ()):
            by_verse[vid].add(root_)
    carriers: dict[tuple[str, str], list[str]] = defaultdict(list)
    for ref, entry in resolved.items():
        s, a, _ = ref.split(":")
        carriers[(f"{s}:{a}", entry["primary"])].append(ref)

    out: dict[tuple[int, int], frozenset] = {}
    for (s, a) in verses:
        vid = f"{s}:{a}"
        keep = set()
        for root_ in by_verse.get(vid, ()):
            refs = carriers.get((vid, root_), [])
            if not refs or any(
                ref not in tools and ref not in function_words for ref in refs
            ):
                keep.add(root_)
        out[(s, a)] = frozenset(keep)
    return out


@functools.lru_cache(maxsize=1)
def _qac_records() -> tuple:
    """The QAC segments, read once for both the signatures and the root forms."""
    from quran_data import qac

    return tuple(qac.records())


def load_content_roots() -> tuple[dict[tuple[int, int], frozenset], dict[str, float]]:
    """Content-root sets and IDF, from the shared `LexicalRetriever` index."""
    from retrieval.lexical_retriever import LexicalRetriever

    sv = SimilarVerses(LexicalRetriever())
    index = sv.lex.index
    verses = sorted({(r_.surah, r_.ayah) for r_ in _qac_records()})
    sets = content_root_sets(index, loaders.roots_resolved(), loaders.word_function(),
                             function_word_refs(_qac_records()), verses)
    return sets, root_idf(index, sv.N)


def load_signatures() -> dict[tuple[int, int], tuple[Element, ...]]:
    return build_signatures(_qac_records())


def qdrant_lock_held() -> Path | None:
    """The embedded-Qdrant directory when another process holds its lock.

    Probes the lock file the way `qdrant_client` takes it (portalocker,
    exclusive, non-blocking) and releases at once. Server mode has no lock.
    """
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    store = paths.qdrant_path()
    if store is None:
        return None
    lock = store / ".lock"
    if not lock.exists():
        return None
    import portalocker

    with lock.open("r+") as fh:
        try:
            portalocker.lock(fh, portalocker.LockFlags.EXCLUSIVE | portalocker.LockFlags.NON_BLOCKING)
        except portalocker.exceptions.LockException:
            return store
        portalocker.unlock(fh)
    return None


def load_vectors() -> dict[tuple[int, int], list[float]]:
    """Every verse vector, unit-normalised, keyed `(surah, ayah)`."""
    import numpy as np
    from indexing.qdrant_store import QuranQdrant

    store = QuranQdrant()
    store.require_connection()
    out: dict[tuple[int, int], list[float]] = {}
    offset = None
    while True:
        points, offset = store.client.scroll(
            store.collection, limit=512, offset=offset, with_vectors=True, with_payload=False,
        )
        for p in points:
            vec = p.vector
            if isinstance(vec, dict):  # named vectors: the collection has one
                vec = next(iter(vec.values()))
            arr = np.asarray(vec, dtype="float64")
            out[(int(p.id) // 1000, int(p.id) % 1000)] = arr / (np.linalg.norm(arr) or 1.0)
        if offset is None:
            break
    store.client.close()
    return out


class CrossEncoderScorer:
    """`bge-reranker-v2-m3` on the Arabic text `/search` reranks, sigmoid, symmetrised."""

    def __init__(self):
        import torch
        from sentence_transformers import CrossEncoder
        from retrieval.reranker import _resolve_device

        self.device = _resolve_device(None) or "cpu"
        self.model = CrossEncoder(RERANKER_MODEL, device=self.device)
        self.sigmoid = torch.nn.Sigmoid()

    def symmetric(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        both = [(x, y) for x, y in pairs] + [(y, x) for x, y in pairs]
        scores = self.model.predict(both, batch_size=CE_BATCH, activation_fn=self.sigmoid,
                                    show_progress_bar=False)
        n = len(pairs)
        return [(float(scores[i]) + float(scores[n + i])) / 2 for i in range(n)]


# ═══════════════════════════════════════════════════════════════════════════
#  The build
# ═══════════════════════════════════════════════════════════════════════════

def gold_digest(no_gold: bool) -> tuple[str | None, list[dict]]:
    if not GOLD_JSON.exists():
        if no_gold:
            return None, []
        sys.exit(f"Gold set not found at {GOLD_JSON}. The header must name the gold set "
                 f"the parameters were frozen against; pass --no-gold to build without one.")
    raw = GOLD_JSON.read_bytes()
    return hashlib.sha256(raw).hexdigest(), json.loads(raw)["pairs"]


def header(gold_sha: str | None) -> dict:
    return {
        "reranker": RERANKER_MODEL,
        "embedder": os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large-instruct"),
        "K": K, "M": M, "w_ce": W_CE, "w_dense": W_DENSE, "floor": FLOOR,
        "sigma": SIGMA, "tau_sem": TAU_SEM, "tau_group": TAU_GROUP,
        "signature": SIGNATURE,
        "dense_on_verbatim": DENSE_ON_VERBATIM,
        "require_shared_root": REQUIRE_SHARED_ROOT,
        "gold_sha256": gold_sha,
    }


def params_digest(head: dict) -> str:
    return hashlib.sha256(json.dumps(head, sort_keys=True).encode()).hexdigest()


def inputs_digest(vectors: dict) -> str:
    """sha256 over everything a checkpoint depends on that the header does not name.

    This file's source, the derived inputs of `CHECKPOINT_INPUTS`, the
    `SimilarVerses` stoplist and the verse vectors (rounded, so a reload of the
    same collection hashes the same). Code this file imports from elsewhere is
    not covered: after changing it, rebuild with `--fresh`.
    """
    import numpy as np

    h = hashlib.sha256(Path(__file__).read_bytes())
    for name in CHECKPOINT_INPUTS:
        f = getattr(paths, name)
        h.update(name.encode())
        h.update(f.read_bytes() if f.exists() else b"<absent>")
    h.update(json.dumps(sorted(STOPWORDS), ensure_ascii=False).encode())
    for key in sorted(vectors):
        h.update(f"{key[0]}:{key[1]}".encode())
        h.update(np.round(np.asarray(vectors[key], dtype="float64"), 6).tobytes())
    return h.hexdigest()


def syntax_survivors(surah: int, ayahs: list[int], scored: set[int],
                     sigs: dict) -> tuple[dict[tuple[int, int], float], int]:
    """D6 steps 1-2: `{(a, b): syn}` passing the gate, and the pairs examined."""
    out: dict[tuple[int, int], float] = {}
    examined = 0
    for a, b in candidate_pairs([x for x in ayahs if x in scored]):
        examined += 1
        s = syn_similarity(sigs[(surah, a)], sigs[(surah, b)])
        if passes_syntax(s):
            out[(a, b)] = s
    return out, examined


def build_surah(surah: int, ayahs: list[int], ctx: dict, gold: list[dict]) -> dict:
    """One surah's entry plus the gold diagnostics that fall in it."""
    import numpy as np

    sigs, roots, idf = ctx["signatures"], ctx["roots"], ctx["idf"]
    unscored = [a for a in ayahs if not roots.get((surah, a))]
    scored_set = {a for a in ayahs if roots.get((surah, a))}
    survivors, examined = syntax_survivors(surah, ayahs, scored_set, sigs)

    # dense: cosine, rank-normalised over ALL non-consecutive scored pairs of the surah
    vecs = ctx["vectors"]
    population = list(candidate_pairs(sorted(scored_set)))
    cos = [float(np.dot(vecs[(surah, a)], vecs[(surah, b)])) for a, b in population]
    dense_of = dict(zip(population, percentile_ranks(cos)))
    cos_of = dict(zip(population, cos))

    # dense is ignored between verbatim-identical verses (DENSE_ON_VERBATIM)
    words = ctx["words"]
    verbatim = {p for p in population if words[(surah, p[0])] == words[(surah, p[1])]}
    eff_dense = {p: None if p in verbatim else dense_of[p] for p in population}
    signals = {p: (eff_dense[p], cov_similarity(roots[(surah, p[0])], roots[(surah, p[1])], idf))
               for p in survivors}
    kept = set(signals) if len(ayahs) <= 2 * M + 1 else cap_pairs(signals, M)

    pairs = sorted(kept)
    texts = ctx["texts"]
    gold_pairs = sorted({(g["a"], g["b"]) for g in gold if g["surah"] == surah})
    ce_of = dict(zip(pairs, ctx["ce"].symmetric(
        [(texts[(surah, a)], texts[(surah, b)]) for a, b in pairs])))
    # Gold pairs the dataset does not need are scored in a call of their own, so
    # the gold set never shares a padded batch with — and so can never nudge —
    # a stored value; these scores feed `diag` only.
    gold_only = [p for p in gold_pairs if p in cos_of and p not in ce_of]
    ce_of.update(zip(gold_only, ctx["ce"].symmetric(
        [(texts[(surah, a)], texts[(surah, b)]) for a, b in gold_only])))

    stored_pairs: dict[tuple[int, int], dict] = {}
    for p in pairs:
        dense, cov = signals[p]
        sem = sem_score(ce_of[p], dense, cov)
        if sem < TAU_SEM:
            continue
        shared = sorted(roots[(surah, p[0])] & roots[(surah, p[1])])
        if REQUIRE_SHARED_ROOT and not shared:
            continue
        syn = survivors[p]
        # `dense` stays the measured value; `verbatim` says it did not enter `sem`
        stored_pairs[p] = {"s": rnd(sem * syn), "sem": rnd(sem), "syn": rnd(syn), "ce": rnd(ce_of[p]),
                           "dense": rnd(dense_of[p]), "cov": rnd(cov), "roots": shared}
        if p in verbatim:
            stored_pairs[p]["verbatim"] = True

    neighbours = select_neighbours(stored_pairs, sorted(scored_set))
    groups = compute_groups(neighbours)

    diag = []
    for g in gold:
        if g["surah"] != surah:
            continue
        p = (g["a"], g["b"])
        row = {"surah": surah, "a": p[0], "b": p[1], "label": g["label"]}
        if p[0] not in scored_set or p[1] not in scored_set:
            row["stage"] = "unscored"
        elif p[1] - p[0] == 1:
            row["stage"] = "consecutive"
        else:
            syn = syn_similarity(sigs[(surah, p[0])], sigs[(surah, p[1])])
            cov = cov_similarity(roots[(surah, p[0])], roots[(surah, p[1])], idf)
            dense, ce = dense_of[p], ce_of.get(p)
            sem = sem_score(ce, eff_dense[p], cov) if ce is not None else None
            row.update({"syn": rnd(syn), "dense": rnd(dense), "cov": rnd(cov),
                        "verbatim": p in verbatim,
                        "ce": None if ce is None else rnd(ce), "sem": None if sem is None else rnd(sem)})
            if not passes_syntax(syn):
                row["stage"] = "syntax_gate"
            elif p not in kept:
                row["stage"] = "candidate_cap"
            elif sem < TAU_SEM:
                row["stage"] = "semantic_gate"
            elif p not in stored_pairs:
                row["stage"] = "no_shared_root"
            elif any(e["a"] == p[1] for e in neighbours[p[0]]) or \
                    any(e["a"] == p[0] for e in neighbours[p[1]]):
                row["stage"] = "stored"
            else:
                row["stage"] = "top_k"
        diag.append(row)

    entry = {
        "unscored": unscored,
        "groups": groups,
        "neighbours": {str(a): lst for a, lst in sorted(neighbours.items()) if lst},
    }
    stats = {"examined": examined, "syntax_survivors": len(survivors), "ce_pairs": len(pairs),
             "stored_pairs": len(stored_pairs), "groups": len(groups)}
    return {"entry": entry, "diagnostics": diag, "stats": stats}


def surah_ayahs() -> dict[int, list[int]]:
    from quran_data.corpus import verses_by_id

    out: dict[int, list[int]] = defaultdict(list)
    for v in verses_by_id().values():
        out[int(v["surah_number"])].append(int(v["ayah_number"]))
    return {s: sorted(a) for s, a in sorted(out.items())}


def parse_surahs(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    out = sorted({int(x) for x in raw.split(",") if x.strip()})
    bad = [s for s in out if not 1 <= s <= 114]
    if bad:
        sys.exit(f"--surahs: not surah numbers: {bad}")
    return out


def dry_run(only: list[int] | None) -> None:
    """Syntax gate only: survivor counts per surah. No lock, no Qdrant, no model."""
    t0 = time.time()
    sigs = load_signatures()
    roots, _ = load_content_roots()
    ayahs_by_surah = surah_ayahs()
    total_ex = total_sv = total_unscored = 0
    for s, ayahs in ayahs_by_surah.items():
        if only and s not in only:
            continue
        scored = {a for a in ayahs if roots.get((s, a))}
        survivors, examined = syntax_survivors(s, ayahs, scored, sigs)
        unscored = len(ayahs) - len(scored)
        total_ex += examined
        total_sv += len(survivors)
        total_unscored += unscored
        print(f"  surah {s:3d}: {len(ayahs):3d} ayat, {unscored:2d} unscored, "
              f"{examined:6d} pairs → {len(survivors):5d} pass the syntax gate")
    print(f"TOTAL: {total_ex} non-consecutive scored pairs, {total_sv} pass the syntax gate "
          f"(σ = {SIGMA:.4f}), {total_unscored} unscored ayat — {time.time() - t0:.1f}s")
    if GOLD_JSON.exists():
        by_label: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for g in json.loads(GOLD_JSON.read_text(encoding="utf-8"))["pairs"]:
            if only and g["surah"] not in only:
                continue
            syn = syn_similarity(sigs[(g["surah"], g["a"])], sigs[(g["surah"], g["b"])])
            by_label[g["label"]][0] += passes_syntax(syn)
            by_label[g["label"]][1] += 1
        print("Gold pairs passing the syntax gate: " + ", ".join(
            f"{label} {ok}/{n}" for label, (ok, n) in sorted(by_label.items())))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="stop after the syntax gate and print survivor counts (no Qdrant, no model)")
    ap.add_argument("--surahs", help="comma-separated surah numbers to (re)build into checkpoints")
    ap.add_argument("--fresh", action="store_true", help="ignore existing checkpoints")
    ap.add_argument("--no-gold", action="store_true",
                    help="build without the gold set (header gold_sha256 = null)")
    args = ap.parse_args(argv)
    only = parse_surahs(args.surahs)

    if args.dry_run:
        dry_run(only)
        return 0

    held = qdrant_lock_held()
    if held is not None:
        sys.exit(f"The embedded Qdrant store at {held} is locked by another process "
                 f"(the backend, or build_index.py). Stop it first — the build reads the "
                 f"verse vectors out of that store — then rerun:\n    {REBUILD}")

    gold_sha, gold = gold_digest(args.no_gold)
    head = header(gold_sha)
    print("Loading the verse vectors…")
    vectors = load_vectors()
    digest = hashlib.sha256(
        f"{params_digest(head)}:{inputs_digest(vectors)}".encode()).hexdigest()
    ckpt_dir = paths.SURAH_SIMILARITY_CHECKPOINT_DIR
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    def load_ckpt(s: int, honour_fresh: bool = True) -> dict | None:
        """A checkpoint of THIS build, or None — a stale, torn or foreign file is rebuilt."""
        f = ckpt_dir / f"{s}.json"
        if (honour_fresh and args.fresh) or not f.exists():
            return None
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(data, dict) or data.get("params") != digest:
            return None
        return data if all(k in data for k in ("entry", "stats", "diagnostics")) else None

    ayahs_by_surah = surah_ayahs()
    todo = [s for s in (only or list(ayahs_by_surah)) if load_ckpt(s) is None]
    reused = len(only or ayahs_by_surah) - len(todo)
    if reused:
        print(f"Reusing {reused} checkpoint(s) whose parameters, inputs, vectors and builder "
              f"source match this run (--fresh to recompute them).")

    if todo:
        t0 = time.time()
        print("Loading signatures, content roots and the cross-encoder…")
        from quran_data import qac
        from quran_data.corpus import verses_by_id
        from retrieval.reranker import _passage_text

        ctx = {
            "signatures": load_signatures(),
            "words": qac.ayah_words(),
            "vectors": vectors,
            "texts": {(int(v["surah_number"]), int(v["ayah_number"])): _passage_text(v)
                      for v in verses_by_id().values()},
            "ce": CrossEncoderScorer(),
        }
        ctx["roots"], ctx["idf"] = load_content_roots()
        print(f"  ready in {time.time() - t0:.1f}s (device={ctx['ce'].device})")
        for s in todo:
            t1 = time.time()
            out = build_surah(s, ayahs_by_surah[s], ctx, gold)
            # Atomic: an interrupted write leaves the previous file (or none), never a torn one.
            tmp = ckpt_dir / f"{s}.json.tmp"
            tmp.write_text(json.dumps({"params": digest, **out}, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, ckpt_dir / f"{s}.json")
            st = out["stats"]
            print(f"  surah {s:3d}: {st['examined']:6d} pairs → {st['syntax_survivors']:5d} syntax "
                  f"→ {st['ce_pairs']:5d} cross-encoded → {st['stored_pairs']:4d} stored, "
                  f"{st['groups']} group(s) [{time.time() - t1:.1f}s]")

    done = {s: load_ckpt(s, honour_fresh=False) for s in ayahs_by_surah}
    missing = [s for s, c in done.items() if c is None]
    if missing:
        print(f"{114 - len(missing)}/114 surahs checkpointed; {paths.SURAH_SIMILARITY_JSON.name} "
              f"is written only once all are. Rerun without --surahs to finish.")
        return 0

    totals = defaultdict(int)
    for c in done.values():
        for k_, v in c["stats"].items():
            totals[k_] += v
    print("TOTAL: " + ", ".join(f"{k_}={v}" for k_, v in totals.items()))
    dataset = {
        "schema": SCHEMA,
        "build": head,
        "surahs": {str(s): done[s]["entry"] for s in sorted(done)},
        # The per-gold-pair stage the evaluation reads (task 4.1): where each gold
        # pair was lost, with the signals it had reached. Ignored by the route.
        "diagnostics": {"gold": [row for s in sorted(done) for row in done[s]["diagnostics"]]},
    }
    out = paths.SURAH_SIMILARITY_JSON
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dataset, ensure_ascii=False, sort_keys=False,
                              separators=(",", ":")), encoding="utf-8")
    tmp.replace(out)
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
