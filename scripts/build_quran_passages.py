#!/usr/bin/env python3
"""
build_quran_passages.py — the offline shared-passage build.

Answers, once and for every pair of verses of DIFFERENT surahs, «does a passage
of this verse's wording come back in that one?» and writes the answer to
`data/derived/quran_passages.json`, which `build_quran_close_verses.py` composes.
The design is `openspec/changes/add-shared-passages/design.md` (tokens D1,
candidates D4, layout D5), its alignment replaced by
`openspec/changes/order-invariant-closeness/design.md` (D1, D2, D6, D8); every
value below was frozen there before the build ran on the corpus — decisions to
record there, never tuning knobs:

  * tokens (add-shared-passages D1) — one token per QAC word: the `LEM:` of the
    word's STEM segment (a segment carrying neither `PREF` nor `SUFF`), else the
    word's surface folded by `arabic_text.bare()`.
  * content words (order-invariant-closeness D1) — the shared definition,
    `closeness_core.content_words`: the word's resolved primary root is among its
    verse's content roots (`build_surah_similarity.content_root_sets`) and its
    `s:a:w` is not a grammatical tool (`word_function.json`).
  * the matching (D2) — `closeness_core.match_all`: one order-invariant
    one-to-one matching of ALL words, edges `lemma` / `root` / `tool`; among
    equal partners a repeated token takes the one at the OFFSET of the shared
    material — the median shift of the anchors, the tokens unique in both verses
    (version 2; version 1's relative position lost 2:255/3:2's opening «لا»).
  * the passage (D6, version 2) — the core's LARGEST ACCEPTED region
    (`closeness_core.passage_region`): over the identical-token edges (`lemma`,
    `tool`; `root` edges are gaps), a candidate is a window of A bounded by
    matched words with a window of B bounded by matched words, in any order; it
    is accepted iff its kept edges number `k ≥ L_MIN`, `k ≥ DENSITY × the longer
    window` and ≥ `CONTENT_MIN` of them are `lemma` edges. The stored passage is
    the accepted candidate with the largest `k`; ties: the larger `2k − unmatched
    words of both windows`, then the smaller `i1`, `i2`, `j1` — read in A, the
    lower-surah verse (`region_of`). A pair with no accepted candidate holds no
    region at all. Version 1's best-SCORING region (which could be a rejected
    hull hiding an accepted sub-window: 2:164/45:5) and Smith–Waterman, its
    scores and its traceback, are gone.
  * candidates (add-shared-passages D4) — only pairs whose token MULTISETS share
    ≥ `L_MIN` tokens are matched (`k` kept edges join `k` pairs of equal tokens,
    one to one, so nothing else can pass), computed exactly with sparse
    count-threshold indicator products.
  * the file layout (D5), schema 2, byte-identical across builds.

Model-free and Qdrant-free: it may run with the backend up.

    python scripts/build_quran_passages.py              # full build
    python scripts/build_quran_passages.py --no-gold    # without the local-only gold set
    python scripts/build_quran_passages.py --jobs 4     # region worker processes
    python scripts/build_quran_passages.py --surahs 28,36   # report only, write nothing

Points the designs leave open, settled here and recorded in the header:

  * A word with SEVERAL stem segments (563 words: «مِمَّا» = مِن + ما, «إِنَّمَا»)
    keeps one token per word: its stem lemmas joined by `+`, in segment order.
  * `roots` is the sorted union of both sides' canonical roots over the kept
    `lemma` edges (the content words of the passage).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator, NamedTuple, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))   # the shared closeness core, a sibling script

from arabic_text import bare  # noqa: E402
from quran_data import loaders, paths, qac  # noqa: E402

# The definition is the shared core's (order-invariant-closeness D8), never a copy:
# content words, the matching, the region and its acceptance thresholds.
import closeness_core as cc  # noqa: E402
from closeness_core import CONTENT_MIN, DENSITY, L_MIN, rejection  # noqa: E402,F401
# The content-root sets D1 reads are the intra build's (`content_root_sets`).
import build_surah_similarity as intra  # noqa: E402

SCHEMA = loaders.QURAN_PASSAGES_SCHEMA
SCOPE = "cross-surah"
TOKEN_RULE = ("one token per QAC word: the LEM of its stem segment(s) (neither PREF nor "
              "SUFF), '+'-joined in segment order; a word with none takes bare(surface)")
CONTENT_RULE = ("the word's resolved primary root is among its verse's content roots "
                "(build_surah_similarity.content_root_sets) and its s:a:w is not a "
                "grammatical tool in word_function.json (closeness_core.content_words)")
MATCHING_RULE = ("closeness_core.match_all: one maximum-weight one-to-one matching of all "
                 "words; content words by lemma token (lemma, 1) or resolved primary root "
                 "(root, 0.5), non-content words by identical token (tool, 1); ties broken "
                 "by the median shift of the anchors (tokens unique in both verses): a "
                 "repeated token takes the partner at the offset of the shared material, "
                 "then in one canonical orientation")
REGION_RULE = ("closeness_core.passage_region over the identical-token edges (lemma, tool; "
               "root edges count as gaps): among the window pairs bounded by matched words "
               "in both verses, in any order, that are ACCEPTED (k >= l_min kept edges, "
               "k >= density x the longer window, >= content_min lemma edges), the one "
               "with the largest k; ties: the larger 2k - unmatched words of both windows, "
               "then the smaller i1, i2, j1, read in A = the lower-surah verse; none when "
               "no window pair is accepted")
CANDIDATES = "token multisets share >= l_min tokens (exact, sparse threshold products)"
GOLD_JSON = ROOT / "tests" / "eval" / "quran_passages_gold.json"
REBUILD = "python scripts/build_quran_passages.py"


# ═══════════════════════════════════════════════════════════════════════════
#  Pure functions — importable by tests, no disk
# ═══════════════════════════════════════════════════════════════════════════

class Word(NamedTuple):
    """One QAC word as this build sees it: its token, whether it carries a root."""

    token: str
    rooted: bool
    root: str | None          # the QAC `ROOT:` as written, None for a rootless word


def _features(rec) -> list[str]:
    return rec.features.split("|")


def word_of(segments: Sequence) -> Word:
    """The word's token, whether it carries a root, and its raw root, from its segments.

    `segments` are `quran_data.qac.Record`s of ONE word, in segment order.
    """
    lemmas: list[str] = []
    root = None
    for seg in segments:
        feats = _features(seg)
        for f in feats:
            if f.startswith("ROOT:") and root is None:
                root = f[5:].strip() or None
        if "PREF" in feats or "SUFF" in feats:
            continue
        lemmas.extend(f[4:] for f in feats if f.startswith("LEM:") and f[4:])
    token = "+".join(lemmas) if lemmas else bare("".join(s.form for s in segments))
    return Word(token, root is not None, root)


def region_of(tok_a: Sequence, tok_b: Sequence, roots_a: Sequence, roots_b: Sequence,
              content_a: Sequence[bool], content_b: Sequence[bool]) -> "cc.Region | None":
    """D6: the largest ACCEPTED region of two verses, or None, through the core only.

    Ties are read in A as passed — the build passes the lower-surah verse, stored as `a` —
    as the shared-passages spec pre-registers («the earlier and then the shorter window in
    A, then the earlier in B»). The core's `passage_region` reads them that way and never
    canonicalises the pair: two blocks exchanged across a wide gap store the T window from
    A and the U window from B (pinned), and 5:33/7:124 lost its passage when a canonical
    orientation read the tie in B.
    """
    edges = cc.match_all(tok_a, tok_b, roots_a, roots_b, content_a, content_b)
    return cc.passage_region(edges)


def common_tokens(a: Iterable, b: Iterable) -> int:
    """`Σ_c min(count_A(c), count_B(c))` — the scalar reference of the D4 bound."""
    ca, cb = Counter(a), Counter(b)
    return sum(min(n, cb[t]) for t, n in ca.items() if t in cb)


def candidate_pairs(seqs: Sequence[Sequence[int]], surah_of: Sequence[int],
                    l_min: int = L_MIN) -> list[tuple[int, int]]:
    """D4: every `(i, j)`, `i < j`, of different surahs sharing ≥ `l_min` tokens.

    `seqs` are interned token sequences (ints ≥ 0). The overlap of two multisets
    is `Σ_t Σ_c [count_A(c) ≥ t][count_B(c) ≥ t]`, so it is the sum, over the
    count thresholds t, of the products `I_t · I_tᵀ` of the 0/1 matrices «verse
    holds token c at least t times». Exact integer arithmetic; returned sorted.
    """
    import numpy as np
    import scipy.sparse as sp

    n = len(seqs)
    if n < 2:
        return []
    counts = [Counter(s) for s in seqs]
    vocab = 1 + max((t for s in seqs for t in s), default=0)
    top = max((max(c.values()) for c in counts if c), default=0)
    total = sp.csr_matrix((n, n), dtype=np.int64)
    for t in range(1, top + 1):
        rows, cols = [], []
        for i, c in enumerate(counts):
            for tok, cnt in c.items():
                if cnt >= t:
                    rows.append(i)
                    cols.append(tok)
        ind = sp.csr_matrix((np.ones(len(rows), dtype=np.int64), (rows, cols)),
                            shape=(n, vocab))
        total = total + ind @ ind.T
    upper = sp.triu(total, k=1).tocoo()
    surah = np.asarray(surah_of)
    keep = (upper.data >= l_min) & (surah[upper.row] != surah[upper.col])
    return sorted(zip(upper.row[keep].tolist(), upper.col[keep].tolist()))


# ═══════════════════════════════════════════════════════════════════════════
#  The corpus
# ═══════════════════════════════════════════════════════════════════════════

def qac_records() -> Iterator:
    """The QAC segments — one seam, so a test can cut the population down."""
    return qac.records()


def ref_str(ref: tuple[int, int]) -> str:
    return f"{ref[0]}:{ref[1]}"


def content_roots(refs: Iterable[tuple[int, int]], resolved: dict, tools: dict
                  ) -> dict[tuple[int, int], frozenset]:
    """D1's content-root sets, as the intra build computes them (its function, imported).

    The function nouns are judged on the WHOLE QAC whatever `refs` holds: the stoplist
    reading is a corpus-wide fact, so a build on two surahs sees the sets the full one does.
    """
    records = intra._qac_records()
    return intra.content_root_sets(loaders.morphology(), resolved, tools,
                                   intra.function_word_refs(records), refs)


class Corpus:
    """Every verse in (surah, ayah) order: its words, interned tokens, roots, content flags.

    `resolved` (`roots_resolved.json`), `tools` (`word_function.json`) and
    `root_sets` (the content roots, `{(s, a): frozenset}`) are read through
    `quran_data` unless given.
    """

    def __init__(self, records: Iterable | None = None, resolved: dict | None = None,
                 tools: dict | None = None, root_sets: dict | None = None):
        by_word: dict[tuple[int, int, int], list] = defaultdict(list)
        for rec in (qac_records() if records is None else records):
            by_word[(rec.surah, rec.ayah, rec.word)].append(rec)
        verses: dict[tuple[int, int], dict[int, Word]] = defaultdict(dict)
        for (s, a, w), segs in by_word.items():
            verses[(s, a)][w] = word_of(sorted(segs, key=lambda r: r.segment))
        self.refs = sorted(verses)
        self.index = {r: i for i, r in enumerate(self.refs)}
        self.surah_of = [r[0] for r in self.refs]
        self.words: list[list[Word]] = []
        for r in self.refs:
            ws = verses[r]
            if sorted(ws) != list(range(1, len(ws) + 1)):
                raise ValueError(f"{ref_str(r)}: QAC word numbers are not 1..{len(ws)}")
            self.words.append([ws[w] for w in sorted(ws)])
        vocab: dict[str, int] = {}
        self.seqs = [tuple(vocab.setdefault(w.token, len(vocab)) for w in ws)
                     for ws in self.words]
        resolved = loaders.roots_resolved() if resolved is None else resolved
        self.roots: list[tuple[str | None, ...]] = []
        for r, ws in zip(self.refs, self.words):
            self.roots.append(tuple(
                ((resolved.get(f"{r[0]}:{r[1]}:{n}") or {}).get("primary") or w.root)
                if w.rooted else None
                for n, w in enumerate(ws, start=1)))
        tools = loaders.word_function() if tools is None else tools
        if root_sets is None:
            root_sets = content_roots(self.refs, resolved, tools)
        self.content: list[tuple[bool, ...]] = [
            cc.content_words(roots, root_sets.get(r, frozenset()), *r, tools)
            for r, roots in zip(self.refs, self.roots)]

    def region(self, i: int, j: int) -> "cc.Region | None":
        """D6: the largest accepted region of verses `i` and `j`, or None."""
        return region_of(self.seqs[i], self.seqs[j], self.roots[i], self.roots[j],
                         self.content[i], self.content[j])

    def judge(self, i: int, j: int, region: "cc.Region | None"
              ) -> tuple[str | None, dict | None]:
        """`("none", None)` when the pair holds no accepted region, else `(None, passage)`
        for the pair `(i, j)`, `i` in the lower surah."""
        if region is None:
            return "none", None
        why = cc.region_rejection(region)
        if why is not None:          # the core returns accepted regions only
            raise ValueError(f"{ref_str(self.refs[i])}/{ref_str(self.refs[j])}: the core "
                             f"returned a region it rejects ({why}): {region}")
        roots = sorted({r for e in region.edges if e.kind == cc.LEMMA
                        for r in (self.roots[i][e.p - 1], self.roots[j][e.q - 1]) if r})
        return None, {"a": ref_str(self.refs[i]), "b": ref_str(self.refs[j]),
                      "wa": [region.i1, region.i2], "wb": [region.j1, region.j2],
                      "k": region.k, "roots": roots}


# ═══════════════════════════════════════════════════════════════════════════
#  The region stage — multiprocessing, independent of the split
# ═══════════════════════════════════════════════════════════════════════════

_VERSES: tuple | None = None          # (seqs, roots, content), one entry per verse


def _init_worker(verses) -> None:
    global _VERSES
    _VERSES = verses


def _region_chunk(chunk: list[tuple[int, int]]) -> list[tuple[int, int, "cc.Region | None"]]:
    seqs, roots, content = _VERSES
    return [(i, j, region_of(seqs[i], seqs[j], roots[i], roots[j], content[i], content[j]))
            for i, j in chunk]


def region_stage(corpus: Corpus, pairs: list[tuple[int, int]], jobs: int, chunk: int = 2000
                 ) -> dict[tuple[int, int], "cc.Region | None"]:
    """`{(i, j): largest accepted region or None}` for every candidate; the result does
    not depend on `jobs`."""
    verses = (corpus.seqs, corpus.roots, corpus.content)
    chunks = [pairs[n:n + chunk] for n in range(0, len(pairs), chunk)]
    out: dict[tuple[int, int], cc.Region | None] = {}
    if jobs <= 1 or len(chunks) <= 1:
        _init_worker(verses)
        for c in chunks:
            out.update(((i, j), r) for i, j, r in _region_chunk(c))
        return out
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(jobs, initializer=_init_worker, initargs=(verses,)) as pool:
        for res in pool.imap_unordered(_region_chunk, chunks, chunksize=1):
            out.update(((i, j), r) for i, j, r in res)
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  The build
# ═══════════════════════════════════════════════════════════════════════════

def gold_digest(no_gold: bool) -> str | None:
    if not GOLD_JSON.exists():
        if no_gold:
            return None
        sys.exit(f"Gold set not found at {GOLD_JSON}. The header must name the gold set "
                 f"this build is measured against; pass --no-gold to build without one.")
    return hashlib.sha256(GOLD_JSON.read_bytes()).hexdigest()


def header(gold_sha: str | None) -> dict:
    return {
        "scope": SCOPE,
        "token": TOKEN_RULE,
        "content": CONTENT_RULE,
        "matching": MATCHING_RULE,
        "tie_break": cc.TIE_BREAK,          # D8: "median-shift"
        "passage": cc.PASSAGE,              # D8: "largest-accepted-region"
        "region": REGION_RULE,
        "l_min": L_MIN,
        "density": DENSITY,
        "content_min": CONTENT_MIN,
        "candidates": CANDIDATES,
        "gold_sha256": gold_sha,
    }


def build(corpus: Corpus, jobs: int) -> tuple[list[dict], dict]:
    """The sorted passages and the per-stage counts."""
    t0 = time.time()
    pairs = candidate_pairs(corpus.seqs, corpus.surah_of)
    stats: dict = {"candidates": len(pairs), "candidates_s": round(time.time() - t0, 1)}
    t1 = time.time()
    regions = region_stage(corpus, pairs, jobs)
    stats["region_s"] = round(time.time() - t1, 1)
    passages, rejected = [], 0
    for i, j in pairs:
        _, passage = corpus.judge(i, j, regions[(i, j)])
        if passage is None:
            rejected += 1
        else:
            passages.append(passage)
    # Global indexes are (surah, ayah) order, so sorting by them is sorting by (a, b)
    # numerically — the order the reader serves ties in.
    passages.sort(key=lambda p: (corpus.index[_ref(p["a"])], corpus.index[_ref(p["b"])]))
    # The region is accepted or absent (D6, version 2): there is no reason to count
    # per pair, only the pairs that hold none.
    stats["rejected"] = rejected
    stats["passages"] = len(passages)
    return passages, stats


def _ref(raw: str) -> tuple[int, int]:
    s, a = raw.split(":")
    return int(s), int(a)


def dataset(passages: list[dict], head: dict) -> dict:
    return {"schema": SCHEMA, "build": head, "passages": passages}


def dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=False, separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-gold", action="store_true",
                    help="build without the gold set (header gold_sha256 = null)")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                    help="region worker processes (default: CPUs − 1)")
    ap.add_argument("--surahs", help="comma-separated surahs: match among these only, "
                                     "print the counts, write nothing")
    args = ap.parse_args(argv)
    only = sorted({int(s) for s in args.surahs.split(",")}) if args.surahs else None

    head = None if only else header(gold_digest(args.no_gold))
    t0 = time.time()
    records = qac_records()
    if only:
        records = (r for r in records if r.surah in set(only))
    corpus = Corpus(records)
    print(f"Corpus: {len(corpus.refs)} verses, "
          f"{sum(len(s) for s in corpus.seqs)} words [{time.time() - t0:.1f}s]")
    passages, stats = build(corpus, args.jobs)
    print(f"CANDIDATES (D4): {stats['candidates']} cross-surah pairs share ≥ {L_MIN} tokens "
          f"[{stats['candidates_s']}s]")
    print(f"REGIONS (D6): {stats['passages']} passages; {stats['rejected']} candidate pairs "
          f"hold no accepted region [{stats['region_s']}s, {args.jobs} job(s)]")
    if only:
        print(f"(surahs {only} only — nothing written)")
        return 0
    out = paths.QURAN_PASSAGES_JSON
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(dumps(dataset(passages, head)), encoding="utf-8")
    tmp.replace(out)
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.2f} MB) — {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
