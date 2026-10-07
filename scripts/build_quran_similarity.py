#!/usr/bin/env python3
"""
build_quran_similarity.py — the offline cross-surah similarity build.

Answers, once and for every verse, «which verses of the OTHER surahs are close to
this one?» and writes the answer to `data/derived/quran_similarity.json`, which
`GET /verse/{surah}/{ayah}/similar` serves without loading any model. The design
is `openspec/changes/add-quran-wide-similar-verses/design.md`; it reuses the
intra-surah definition unchanged and only changes the population:

  * D1 — the signature, the syntactic similarity, the lexical signal, the
    semantic score, the candidate cap, the neighbour selection, the
    cross-encoder, the loaders and every frozen parameter are IMPORTED from
    `scripts/build_surah_similarity.py` (which takes the measure and the
    matching from `scripts/closeness_core.py`), never copied, so the two
    datasets cannot drift on what «close» means.
  * D2 — the population is every pair of scored verses in two DIFFERENT surahs
    (19 113 299 pairs over the full corpus). Verses are keyed by their global
    corpus index (0…6235, i.e. (surah, ayah) order) inside the build, so the
    intra helpers keyed on `int` work unchanged; the file uses `"s:a"` refs.
  * D3 — the syntactic gate runs behind two EXACT pre-filters, the core's
    upper bounds of `syn` (order-invariant-closeness version 2, D5): the
    length window (`syn_length_bound`, `m / M`) and the coarse-element bag
    bound (`syn_bag_bound`, `|bagA ∩ bagB| / M`) — both exact under any
    re-ordering of blocks, which is why version 1's bigram bound is gone. Each
    is evaluated through the very float expression the core uses (vectorised
    here with the same IEEE operations, tested bit for bit against the core),
    so a pruned pair provably scores below σ. Survivors are scored by the
    intra `syntax_similarity`: the pair's D2 matching, then the core's `syn`
    with the blocks re-orderable along it — so the syntax workers hold the
    verses' words (`VerseWords`) beside their signatures.
  * D4 — dense is the cosine's average-rank percentile among the cross-surah
    pairs that pass the syntactic gate (one global population, so it is
    symmetric). It used to be ranked among ALL 19 M cross-surah pairs, where
    every candidate sits near the top (590 of 605 stored pairs had dense ≥ 0.95)
    and dense became a constant +0.3 in `sem` — change
    `tighten-cross-surah-similarity`, design D1.
  * D5 — `cap_pairs(M)`, the symmetrised cross-encoder, the semantic gate, the
    matched-mass rule (a pair is stored only when its content-word matching
    carries `Mw > 0`), `score = sem × syn`, `select_neighbours(K)`.
  * Two rules of the cross-surah population only (tighten-cross-surah-similarity
    D2, D3): a pair whose LONGER signature has ≤ `SHORT_EXACT_MAX_LEN` elements
    passes the syntactic gate only with `syn = 1` (`passes_short_rule`), and each
    verse's list keeps a neighbour only when its score is ≥ `RHO` × the list's best
    (`relative_cut`). The intra build is untouched.
  * D7 — the file layout; schema 2 since `order-invariant-closeness`: `syn` is
    the coarse-element Levenshtein with blocks re-orderable along the matching
    (version 2 D4; version 1's `½·uni + ½·bi` was measured and closed), and the
    stored `lex` — the word-level IDF Jaccard of the order-invariant content-word
    matching — replaces `cov`; `roots` are the matched content words' roots.
    The header names every definition (D8: `signature`, `signature_measure`,
    `lexical`, `tie_break`) and, under `blind_sample_sha256`, the sha256 of the
    BYTES of `tests/eval/closeness_blind_v2.json` (D10.3 — the blind sample the
    build is measured on; its content is never parsed here; null when absent).

Needs the backend STOPPED: the verse vectors are read out of the embedded Qdrant,
which takes an exclusive file lock. The script checks that lock before loading
anything and refuses with a clear message when it is held — except under
`--syntax-only`, which reads neither Qdrant nor a model and so can be timed while
the backend runs.

    python scripts/build_quran_similarity.py                # full build (resumes)
    python scripts/build_quran_similarity.py --syntax-only  # syntax stage only: no lock, no Qdrant, no model
    python scripts/build_quran_similarity.py --dry-run      # every stage up to the cross-encoder (needs the lock)
    python scripts/build_quran_similarity.py --surahs 3,58  # checkpoint a few anchor surahs
    python scripts/build_quran_similarity.py --fresh        # ignore existing checkpoints
    python scripts/build_quran_similarity.py --jobs 4       # syntax-stage worker processes
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import multiprocessing
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# The intra builder is a sibling script, not a package module: `scripts/` sits
# outside the layered packages, so importing it breaks no direction rule (D1).
sys.path.insert(0, str(ROOT / "scripts"))

from quran_data import loaders, paths  # noqa: E402

import build_surah_similarity as intra  # noqa: E402
from build_surah_similarity import (  # noqa: E402 — D1: the definition, imported
    DENSE_ON_VERBATIM, FLOOR, K, LEXICAL, M, REQUIRE_SHARED_ROOT, RERANKER_MODEL, SIGMA,
    SIGMA_EPS, SIGNATURE, SIGNATURE_MEASURE, TAU_SEM, TIE_BREAK, W_CE, W_DENSE,
    CrossEncoderScorer, cap_pairs, lexical, load_content_roots, load_signatures, load_vectors,
    load_verse_words, pair_edges, passes_syntax, prefilter_stage, qdrant_lock_held, rnd,
    select_neighbours, sem_score, syn, syntax_similarity,
)
# order-invariant-closeness D5: the exact bounds, from the core itself.
from closeness_core import syn_bag_bound, syn_length_bound  # noqa: E402

SCHEMA = loaders.QURAN_SIMILARITY_SCHEMA
SCOPE = "cross-surah"
# Frozen in openspec/changes/tighten-cross-surah-similarity/design.md BEFORE the
# gold set's second sample was labelled and before any rebuild — decisions to
# record there, never tuning knobs.
DENSE_POPULATION = "syntax-survivors"   # D1
SHORT_EXACT_MAX_LEN = 3                 # D2
RHO = 0.5                               # D3
GOLD_JSON = ROOT / "tests" / "eval" / "quran_similarity_gold.json"
# order-invariant-closeness D10.3: the blind sample the version-2 build is measured
# on. Its sha256 (of the BYTES — never parsed here) goes into the header so
# `eval_closeness_blind.py` can refuse a mismatch; null when the file is absent.
BLIND_SAMPLE_JSON = ROOT / "tests" / "eval" / "closeness_blind_v2.json"
REBUILD = "python scripts/build_quran_similarity.py"
# The intra header keys this build must share verbatim (spec «The parameters are
# the intra-surah ones»); their digest is recorded so the equality is checkable.
# D8's definition names are among them: two datasets under two definitions must
# not be read as one relation.
SHARED_PARAMS = ("K", "M", "w_ce", "w_dense", "floor", "sigma", "tau_sem", "signature",
                 "signature_measure", "lexical", "tie_break", "dense_on_verbatim",
                 "require_shared_root")
# `passes_syntax`'s threshold, as the one float it compares against.
_SYN_THRESHOLD = SIGMA - SIGMA_EPS


# ═══════════════════════════════════════════════════════════════════════════
#  Pure functions — importable by tests, no disk, no model
# ═══════════════════════════════════════════════════════════════════════════

def bag_bound_np(c_uni, la, lb):
    """`syn_bag_bound` from the common element count, vectorised (D5): `count / M`,
    the core's one true division over int64 arrays, so each element is
    bit-identical to the core's scalar — tested; two empty signatures bound at 1."""
    import numpy as np

    longest = np.maximum(la, lb)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = c_uni / longest
    return np.where(longest == 0, 1.0, out)


def passes_short_rule(la: int, lb: int, syn: float,
                      max_len: int = SHORT_EXACT_MAX_LEN) -> bool:
    """D2: a pair whose longer signature has ≤ `max_len` elements needs `syn = 1`.

    With three words one element is the whole difference between a shared frame
    and a shared construction. `syn` returns exactly 1.0 iff one of its three
    alignments is an identity: the two signatures equal as written, or equal once
    the blocks of one are re-ordered along the pair's matching — for ≤ 3 words,
    the same construction up to the order of its matched blocks, never a
    substitution (which costs ≥ 1/3). Applied AFTER `σ`, so the pre-filters (upper
    bounds for the `σ` gate) stay exact.
    """
    return max(la, lb) > max_len or syn == 1.0


def relative_cut(lists: dict[int, list[dict]], rho: float = RHO) -> dict[int, list[dict]]:
    """D3: each list keeps the entries scoring ≥ `rho` × its best (stored, rounded) score.

    Per list: a pair cut from u's list stays wherever v's list keeps it. Lists are
    score-descending, so the best is the first entry; order is preserved.
    """
    out = {}
    for v, lst in lists.items():
        best = lst[0]["s"] if lst else 0.0
        out[v] = [e for e in lst if e["s"] >= rho * best]
    return out


def length_windows(max_len: int) -> list[tuple[int, int]]:
    """`[(lo, hi)]` per length n: the partner lengths the length bound lets through.

    Derived from the exact inequality itself — every L is tested through
    `passes_syntax(syn_length_bound(n, L))` — not from a closed form, so the
    window cannot drift from the gate at a float edge. The admitted set is an
    interval (`m / M` falls as L leaves n on either side); asserted.
    """
    out = []
    for n in range(max_len + 1):
        ok = [L for L in range(max_len + 1) if passes_syntax(syn_length_bound(n, L))]
        assert ok == list(range(ok[0], ok[-1] + 1)), f"length window of {n} is not an interval"
        out.append((ok[0], ok[-1]))
    return out


def intern_signatures(sigs: Sequence[Sequence]) -> list[tuple[int, ...]]:
    """Each element replaced by a small int, first-seen order.

    A bijection on elements, so `syn` (equality only, positions re-ordered along
    the matching) gives the same value on the interned sequences as on the
    element tuples.
    """
    ids: dict = {}
    return [tuple(ids.setdefault(e, len(ids)) for e in sig) for sig in sigs]


def percentile_in(sorted_population, values) -> list[float]:
    """Average-rank percentile `(r − 1)/(n − 1)` of each value in a sorted population.

    The numpy counterpart of `intra.percentile_ranks` for a population too large
    to rank in Python: ties take their average rank; same float operations
    (`(i + j) / 2`, then `/ (n − 1)`), so the result is bit-identical.
    """
    import numpy as np

    pop = np.asarray(sorted_population, dtype="float64")
    vals = np.asarray(values, dtype="float64")
    n = len(pop)
    if n == 0:
        return []
    if n == 1:
        return [0.5] * len(vals)
    lo = np.searchsorted(pop, vals, side="left")
    hi = np.searchsorted(pop, vals, side="right")
    return [float(x) for x in ((lo + hi - 1) / 2) / (n - 1)]


def percentile_ranks_np(values: Sequence[float]) -> list[float]:
    """`intra.percentile_ranks(values)` computed by `percentile_in` (tests compare them)."""
    import numpy as np

    return percentile_in(np.sort(np.asarray(values, dtype="float64")), values)


# ═══════════════════════════════════════════════════════════════════════════
#  D3 — the syntactic stage over the cross-surah population
# ═══════════════════════════════════════════════════════════════════════════

class SyntaxIndex:
    """The length-sorted, count-matrix view of the scored signatures.

    `seqs[i]` is verse i's interned signature (global index), `surah_of[i]` its
    surah, `scored` the global indexes with ≥ 1 content root, `vwords[i]` its
    intra `VerseWords` — the tokens, roots and content flags the pair's D2
    matching is computed from, which `syn` re-orders blocks along (version 2 D4).
    `counts` holds each verse's coarse-element bag (dense: the vocabulary is small).
    """

    def __init__(self, seqs: Sequence[tuple[int, ...]], surah_of: Sequence[int],
                 scored: Sequence[int], vwords: Sequence):
        import numpy as np

        self.seqs = list(seqs)
        self.vwords = list(vwords)
        if len(self.vwords) != len(self.seqs):
            raise ValueError(f"{len(self.seqs)} signatures against {len(self.vwords)} verses' words")
        self.surah_of = np.asarray(surah_of, dtype="int32")
        self.lengths = np.asarray([len(s) for s in self.seqs], dtype="int64")
        self.scored = sorted(scored)
        vocab = 1 + max((e for s in self.seqs for e in s), default=0)
        self.counts = np.zeros((len(self.seqs), vocab), dtype="int16")
        for i, s in enumerate(self.seqs):
            for e, c in Counter(s).items():
                self.counts[i, e] = c
        order = sorted(self.scored, key=lambda i: (int(self.lengths[i]), i))
        self.by_length = np.asarray(order, dtype="int64")
        self.sorted_lengths = self.lengths[self.by_length]
        self.windows = length_windows(int(self.lengths.max(initial=0)))
        per_surah = Counter(int(self.surah_of[i]) for i in self.scored)
        self.scored_after = {s: sum(n for t, n in per_surah.items() if t > s) for s in range(1, 116)}

    def survivors(self, surah: int) -> tuple[list[tuple[int, int, float]], dict]:
        """Every cross-surah pair `(i, j)`, `i` in `surah`, `j` in a LATER surah.

        Each unordered cross-surah pair is examined exactly once (by the anchor
        surah of its lower verse). Returns `[(i, j, syn)]` passing the gate AND
        the short-pair rule (D2), sorted, and the per-stage counts (each count is
        the number of pairs still in after that stage). A pair past both bounds
        is scored in full: its matching, then `syn` (`syntax_similarity`).
        """
        import numpy as np

        out: list[tuple[int, int, float]] = []
        stats = {"examined": 0, "length_window": 0, "bag_bound": 0,
                 "syntax_gate": 0, "short_exact": 0}
        anchors = [i for i in self.scored if self.surah_of[i] == surah]
        for i in anchors:
            stats["examined"] += self.scored_after.get(surah, 0)
            n = int(self.lengths[i])
            lo, hi = self.windows[n]
            start = int(np.searchsorted(self.sorted_lengths, lo, side="left"))
            end = int(np.searchsorted(self.sorted_lengths, hi, side="right"))
            cands = self.by_length[start:end]
            cands = np.sort(cands[self.surah_of[cands] > surah])
            stats["length_window"] += len(cands)
            if not len(cands):
                continue
            # D5, the coarse-element bag bound: syn_bag_bound with the same IEEE operations
            mine = self.counts[i]
            nz = np.flatnonzero(mine)
            common = np.minimum(self.counts[np.ix_(cands, nz)], mine[nz]).sum(axis=1, dtype="int64")
            la = np.full(len(cands), n, dtype="int64")
            lb = self.lengths[cands]
            cands = cands[bag_bound_np(common, la, lb) >= _SYN_THRESHOLD]
            stats["bag_bound"] += len(cands)
            a, va = self.seqs[i], self.vwords[i]
            for j in cands.tolist():
                s = syntax_similarity(a, self.seqs[j], va, self.vwords[j]).syn
                if passes_syntax(s):
                    stats["syntax_gate"] += 1
                    if passes_short_rule(len(a), len(self.seqs[j]), s):
                        out.append((i, j, s))
        stats["short_exact"] = len(out)
        return out, stats


_WORKER: SyntaxIndex | None = None


def _init_worker(seqs, surah_of, scored, vwords) -> None:
    global _WORKER
    _WORKER = SyntaxIndex(seqs, surah_of, scored, vwords)


def _worker_survivors(surah: int):
    t0 = time.time()
    out, stats = _WORKER.survivors(surah)
    stats["elapsed"] = time.time() - t0
    return surah, out, stats


def syntax_stage(seqs, surah_of, scored, vwords, anchors: Sequence[int], jobs: int
                 ) -> tuple[dict[tuple[int, int], float], dict[int, dict]]:
    """`{(i, j): syn}` over the anchor surahs, and their per-surah stats.

    `seqs`, `surah_of` and `vwords` are index-aligned per verse (the `Corpus`
    attributes of those names). The result does not depend on `jobs`: each anchor
    surah's pairs are computed independently and merged in surah order.
    """
    results = {}
    if jobs <= 1:
        _init_worker(seqs, surah_of, scored, vwords)
        for s in anchors:
            surah, out, st = _worker_survivors(s)
            results[surah] = (out, st)
    else:
        # Largest first: surah 2 alone is ~1/8 of the work.
        sizes = Counter(surah_of[i] for i in scored)
        order = sorted(anchors, key=lambda s: -sizes.get(s, 0) * _after(sizes, s))
        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(jobs, initializer=_init_worker,
                      initargs=(seqs, surah_of, scored, vwords)) as pool:
            for surah, out, st in pool.imap_unordered(_worker_survivors, order, chunksize=1):
                results[surah] = (out, st)
    survivors: dict[tuple[int, int], float] = {}
    stats: dict[int, dict] = {}
    for s in sorted(results):
        out, st = results[s]
        survivors.update(((i, j), syn) for i, j, syn in out)
        stats[s] = st
    return survivors, stats


def _after(sizes: Counter, surah: int) -> int:
    return sum(n for t, n in sizes.items() if t > surah)


# ═══════════════════════════════════════════════════════════════════════════
#  D4 — dense over the cross-surah population
# ═══════════════════════════════════════════════════════════════════════════

def dense_stage(vectors: dict, refs: list[tuple[int, int]], population: set[tuple[int, int]],
                wanted: set[tuple[int, int]]
                ) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], float], int]:
    """`(cos_of, dense_of, n_population)` for the `wanted` pairs (D4, design D1).

    The population is `population`: the cross-surah pairs that pass the syntactic
    gate — the candidates the semantic gate actually decides between. A wanted pair
    outside it (a gold pair the gate dropped) is ranked against the same population.
    Every cosine, population and wanted alike, comes out of the same per-pair dot
    product, so a pair's value is bit-identical to the one it is ranked among.
    """
    import numpy as np

    pairs = sorted(population | wanted)
    cos_of: dict[tuple[int, int], float] = {}
    for i, j in pairs:
        a = np.asarray(vectors[refs[i]], dtype="float64")
        b = np.asarray(vectors[refs[j]], dtype="float64")
        cos_of[(i, j)] = float(a @ b)
    pop = np.sort(np.asarray([cos_of[p] for p in population], dtype="float64"))
    keys = sorted(wanted)
    dense_of = dict(zip(keys, percentile_in(pop, [cos_of[k] for k in keys])))
    return {k: cos_of[k] for k in keys}, dense_of, len(population)


# ═══════════════════════════════════════════════════════════════════════════
#  The build
# ═══════════════════════════════════════════════════════════════════════════

def gold_digest(no_gold: bool) -> tuple[str | None, list[dict]]:
    if not GOLD_JSON.exists():
        if no_gold:
            return None, []
        sys.exit(f"Gold set not found at {GOLD_JSON}. The header must name the gold set "
                 f"this build is measured against; pass --no-gold to build without one.")
    raw = GOLD_JSON.read_bytes()
    return hashlib.sha256(raw).hexdigest(), json.loads(raw)["pairs"]


def blind_sample_digest() -> str | None:
    """sha256 of the BYTES of `BLIND_SAMPLE_JSON` (D10.3), or None when it is absent.
    The file is hashed, never parsed: its labels are the evaluation's, not the build's."""
    if not BLIND_SAMPLE_JSON.exists():
        return None
    return hashlib.sha256(BLIND_SAMPLE_JSON.read_bytes()).hexdigest()


def header(gold_sha: str | None) -> dict:
    intra_head = intra.header(None)
    shared = {k: intra_head[k] for k in SHARED_PARAMS}
    return {
        "scope": SCOPE,
        "reranker": RERANKER_MODEL,
        "embedder": intra_head["embedder"],
        "K": K, "M": M, "w_ce": W_CE, "w_dense": W_DENSE, "floor": FLOOR,
        "sigma": SIGMA, "tau_sem": TAU_SEM,
        "signature": SIGNATURE,
        "signature_measure": SIGNATURE_MEASURE,
        "lexical": LEXICAL,
        "tie_break": TIE_BREAK,
        "dense_on_verbatim": DENSE_ON_VERBATIM,
        "dense_population": DENSE_POPULATION,
        "short_exact_max_len": SHORT_EXACT_MAX_LEN,
        "rho": RHO,
        "require_shared_root": REQUIRE_SHARED_ROOT,
        # D1: the intra builder's digest of the parameters both builds share
        "intra_params_sha256": intra.params_digest(shared),
        "gold_sha256": gold_sha,
        # D10.3: the blind sample this build is measured on (bytes hashed, not read)
        "blind_sample_sha256": blind_sample_digest(),
    }


def inputs_digest(vectors: dict) -> str:
    """The intra digest (the sources it covers — its own, the closeness core's and the
    passage build's token rule —, the derived inputs, stoplist, vectors) + this source."""
    h = hashlib.sha256(intra.inputs_digest(vectors).encode())
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()


def ref_str(ref: tuple[int, int]) -> str:
    return f"{ref[0]}:{ref[1]}"


def parse_ref(raw: str) -> tuple[int, int]:
    s, a = raw.split(":")
    return int(s), int(a)


class Corpus:
    """The verses in global order, their signatures, content roots, the words the
    lexical signal matches (`vwords`, the intra `VerseWords`) and verbatim words."""

    def __init__(self):
        from quran_data import qac

        self.refs = [(s, a) for s, ayahs in intra.surah_ayahs().items() for a in ayahs]
        self.index = {r: i for i, r in enumerate(self.refs)}
        sigs = load_signatures()
        self.signatures = [sigs[r] for r in self.refs]
        self.seqs = intern_signatures(self.signatures)
        self.roots_by_ref, self.idf = load_content_roots()
        self.roots = [self.roots_by_ref.get(r, frozenset()) for r in self.refs]
        self.scored = [i for i, r in enumerate(self.roots) if r]
        self.unscored = [ref_str(self.refs[i]) for i, r in enumerate(self.roots) if not r]
        self.surah_of = [r[0] for r in self.refs]
        self.words = qac.ayah_words()
        verse_words = load_verse_words(self.roots_by_ref)
        self.vwords = [verse_words[r] for r in self.refs]

    def verbatim(self, i: int, j: int) -> bool:
        return self.words.get(self.refs[i]) == self.words.get(self.refs[j])

    def lexical(self, i: int, j: int):
        """The intra `lexical` of verses i and j: `lex`, the matched mass `Mw` and the
        matched content words' roots (order-invariant-closeness D3)."""
        return lexical(self.vwords[i], self.vwords[j], self.idf)

    def syntax(self, i: int, j: int):
        """The intra `syntax_similarity` of verses i and j: their matching and `syn`
        over the interned signatures with the blocks re-orderable along it (D4)."""
        return syntax_similarity(self.seqs[i], self.seqs[j], self.vwords[i], self.vwords[j])


def gold_pairs(corpus: Corpus, gold: list[dict]) -> list[dict]:
    """The gold rows with global indexes; a same-surah pair is a gold-file error."""
    out = []
    for g in gold:
        a, b = corpus.index[parse_ref(g["a"])], corpus.index[parse_ref(g["b"])]
        i, j = min(a, b), max(a, b)
        if corpus.surah_of[i] == corpus.surah_of[j]:
            sys.exit(f"Gold pair {g['a']}/{g['b']} lies in one surah; the cross-surah gold "
                     f"set must hold cross-surah pairs only.")
        out.append({**g, "i": i, "j": j})
    return out


def build_anchor(surah: int, kept: list[tuple[int, int]], gold: list[dict], ctx: dict) -> dict:
    """One anchor surah's checkpoint: the stored pairs whose lower verse is in it.

    `kept` holds the capped pairs `(i, j)` with `i` in `surah`; `gold` the gold
    rows whose lower verse is in it. The `stage` of a gold row stops at
    `passed` — whether it is then `stored`, cut at `relative_cut` or lost at `top_k` depends on the
    other surahs and is settled at assembly.
    """
    corpus: Corpus = ctx["corpus"]
    survivors, dense_of, signals = ctx["survivors"], ctx["dense_of"], ctx["signals"]
    texts = ctx["texts"]
    pair_text = lambda p: (texts[p[0]], texts[p[1]])  # noqa: E731

    pairs = sorted(kept)
    kept_set = set(pairs)
    ce_of = dict(zip(pairs, ctx["ce"].symmetric([pair_text(p) for p in pairs])))
    scored = set(corpus.scored)
    # Gold pairs the dataset does not need are scored in a call of their own, so
    # the gold set never shares a padded batch with — and so can never nudge —
    # a stored value; these scores feed the diagnostics only.
    gold_only = sorted({(g["i"], g["j"]) for g in gold
                        if g["i"] in scored and g["j"] in scored} - set(ce_of))
    ce_of.update(zip(gold_only, ctx["ce"].symmetric([pair_text(p) for p in gold_only])))

    stored: list[list] = []
    passed: set[tuple[int, int]] = set()
    for p in pairs:
        dense, lex = signals[p]
        sem = sem_score(ce_of[p], dense, lex)
        if sem < TAU_SEM:
            continue
        lx = corpus.lexical(*p)
        # D3: «shares a content root» is now «the matching carries a positive mass»
        if REQUIRE_SHARED_ROOT and not lx.mass > 0:
            continue
        sy = survivors[p]
        # `dense` stays the measured value; `verbatim` says it did not enter `sem`
        sig = {"s": rnd(sem * sy), "sem": rnd(sem), "syn": rnd(sy), "ce": rnd(ce_of[p]),
               "dense": rnd(dense_of[p]), "lex": rnd(lex), "roots": lx.roots}
        if dense is None:
            sig["verbatim"] = True
        stored.append([ref_str(corpus.refs[p[0]]), ref_str(corpus.refs[p[1]]), sig])
        passed.add(p)

    diag = []
    for g in gold:
        p = (g["i"], g["j"])
        row = {"a": g["a"], "b": g["b"], "label": g["label"]}
        if p[0] not in scored or p[1] not in scored:
            row["stage"] = "unscored"
            diag.append(row)
            continue
        a_sig, b_sig = corpus.seqs[p[0]], corpus.seqs[p[1]]
        sy = corpus.syntax(*p).syn
        verbatim = corpus.verbatim(*p)
        lex = corpus.lexical(*p).lex
        ce = ce_of.get(p)
        sem = sem_score(ce, None if verbatim else dense_of[p], lex) if ce is not None else None
        row.update({"syn": rnd(sy), "dense": rnd(dense_of[p]), "lex": rnd(lex),
                    "verbatim": verbatim, "ce": None if ce is None else rnd(ce),
                    "sem": None if sem is None else rnd(sem)})
        # A pair below σ is a `syntax_gate` loss whichever stage dropped it first;
        # a pre-filter stage is reported only for a pair whose syn ≥ σ — a bug.
        dropped_by = prefilter_stage(a_sig, b_sig)
        if not passes_syntax(sy):
            row["stage"] = "syntax_gate"
        elif dropped_by:
            row["stage"] = dropped_by
        elif not passes_short_rule(len(a_sig), len(b_sig), sy):
            row["stage"] = "short_exact"
        elif p not in survivors:
            # syn ≥ σ and the scalar pre-filter keeps the pair, yet the vectorised
            # path dropped it: a pre-filter defect, counted as one so the eval's
            # «pre-filter loss = 0» target breaks instead of hiding it as a gate loss.
            row["stage"] = "bag_bound"
        elif p not in kept_set:
            row["stage"] = "candidate_cap"
        elif sem < TAU_SEM:
            row["stage"] = "semantic_gate"
        elif p not in passed:
            row["stage"] = "no_shared_root"
        else:
            row["stage"] = "passed"
        diag.append(row)

    return {"pairs": stored, "diagnostics": diag,
            "stats": {"ce_pairs": len(pairs), "stored_pairs": len(stored)}}


def assemble(corpus: Corpus, done: dict[int, dict], head: dict) -> dict:
    """The dataset from every anchor surah's checkpoint (D7)."""
    stored: dict[tuple[int, int], dict] = {}
    for s in sorted(done):
        for a, b, sig in done[s]["pairs"]:
            stored[(corpus.index[parse_ref(a)], corpus.index[parse_ref(b)])] = sig
    # Keys are global indexes, so the listed order «score desc, then `a` asc» is
    # «score desc, then (surah, ayah) asc». WHICH K are kept on a tied score follows
    # the imported intra rule, nearest index first (D5 records it; D1 forbids a
    # cross-only variant of the helper).
    full = select_neighbours(stored, corpus.scored)
    lists = relative_cut(full)        # design D3, after top-K
    neighbours = {}
    for i in sorted(lists):
        if lists[i]:
            neighbours[ref_str(corpus.refs[i])] = [
                {"r": ref_str(corpus.refs[e["a"]]), **{k: v for k, v in e.items() if k != "a"}}
                for e in lists[i]]
    listed = {ref: {e["r"] for e in lst} for ref, lst in neighbours.items()}
    top_k = {ref_str(corpus.refs[i]): {ref_str(corpus.refs[e["a"]]) for e in lst}
             for i, lst in full.items()}

    def holds(table: dict, row: dict) -> bool:
        return row["b"] in table.get(row["a"], ()) or row["a"] in table.get(row["b"], ())

    gold_rows = []
    for s in sorted(done):
        for row in done[s]["diagnostics"]:
            if row["stage"] == "passed":
                stage = ("stored" if holds(listed, row)
                         else "relative_cut" if holds(top_k, row) else "top_k")
                row = {**row, "stage": stage}
            gold_rows.append(row)
    return {
        "schema": SCHEMA,
        "build": head,
        "unscored": corpus.unscored,
        "neighbours": neighbours,
        # The per-gold-pair stage the evaluation reads (task 4.1). Ignored by the route.
        "diagnostics": {"gold": gold_rows},
    }


def print_syntax_stats(stats: dict[int, dict], elapsed: float, per_surah: bool) -> dict:
    total = defaultdict(float)
    for s, st in sorted(stats.items()):
        for k_, v in st.items():
            total[k_] += v
        if per_surah:
            print(f"  anchor surah {s:3d}: {st['examined']:8d} pairs → {st['length_window']:7d} "
                  f"length window → {st['bag_bound']:6d} bag bound → "
                  f"{st['syntax_gate']:5d} syntax gate → {st['short_exact']:5d} "
                  f"short-pair rule [{st['elapsed']:.1f}s]")
    print(f"SYNTAX: {int(total['examined'])} cross-surah scored pairs → "
          f"{int(total['length_window'])} in the length window → {int(total['bag_bound'])} "
          f"past the bag bound → "
          f"{int(total['syntax_gate'])} pass the syntax gate "
          f"(σ = {SIGMA:.4f}) → {int(total['short_exact'])} pass the short-pair rule "
          f"(≤ {SHORT_EXACT_MAX_LEN} elements: syn = 1) — {elapsed:.1f}s wall, "
          f"{total['elapsed']:.1f}s summed over workers")
    return total


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--syntax-only", action="store_true",
                    help="run the syntactic stage only and print its counts (no lock, no Qdrant, no model)")
    ap.add_argument("--dry-run", action="store_true",
                    help="run every stage up to (not including) the cross-encoder and print counts")
    ap.add_argument("--surahs", help="comma-separated anchor surahs to (re)build into checkpoints")
    ap.add_argument("--fresh", action="store_true", help="ignore existing checkpoints")
    ap.add_argument("--no-gold", action="store_true",
                    help="build without the gold set (header gold_sha256 = null)")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                    help="worker processes for the syntactic stage (default: CPUs − 1)")
    ap.add_argument("--per-surah", action="store_true", help="print the syntax counts per anchor surah")
    args = ap.parse_args(argv)
    only = intra.parse_surahs(args.surahs)

    if not args.syntax_only:
        held = qdrant_lock_held()
        if held is not None:
            sys.exit(f"The embedded Qdrant store at {held} is locked by another process "
                     f"(the backend, or build_index.py). Stop it first — the build reads the "
                     f"verse vectors out of that store — then rerun:\n    {REBUILD}"
                     f"\n(`--syntax-only` needs no lock.)")

    t0 = time.time()
    corpus = Corpus()
    print(f"Corpus: {len(corpus.refs)} verses, {len(corpus.scored)} scored, "
          f"{len(corpus.unscored)} unscored [{time.time() - t0:.1f}s]")
    all_surahs = sorted(set(corpus.surah_of))

    def run_syntax(anchors: list[int]) -> dict[tuple[int, int], float]:
        t1 = time.time()
        survivors, stats = syntax_stage(corpus.seqs, corpus.surah_of, corpus.scored,
                                        corpus.vwords, anchors, args.jobs)
        print_syntax_stats(stats, time.time() - t1, args.per_surah)
        return survivors

    if args.syntax_only:
        run_syntax(only or all_surahs)
        if only:
            print(f"(anchor surahs {only} only — each pair is counted under its lower verse's surah)")
        return 0

    gold_sha, gold_raw = gold_digest(args.no_gold)
    head = header(gold_sha)
    gold = gold_pairs(corpus, gold_raw)
    print("Loading the verse vectors…")
    vectors = load_vectors()
    digest = hashlib.sha256(
        f"{intra.params_digest(head)}:{inputs_digest(vectors)}".encode()).hexdigest()
    ckpt_dir = paths.QURAN_SIMILARITY_CHECKPOINT_DIR

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
        return data if all(k in data for k in ("pairs", "stats", "diagnostics")) else None

    todo = [s for s in (only or all_surahs) if args.dry_run or load_ckpt(s) is None]
    reused = len(only or all_surahs) - len(todo)
    if reused:
        print(f"Reusing {reused} checkpoint(s) whose parameters, inputs, vectors and builders' "
              f"sources match this run (--fresh to recompute them).")

    if todo:
        # The cap is per VERSE across all its partners, so the syntactic and dense
        # stages always run over the whole population, whatever --surahs says.
        survivors = run_syntax(all_surahs)
        t1 = time.time()
        scored = set(corpus.scored)
        wanted = set(survivors) | {(g["i"], g["j"]) for g in gold
                                   if g["i"] in scored and g["j"] in scored}
        _, dense_of, n_pop = dense_stage(vectors, corpus.refs, set(survivors), wanted)
        print(f"DENSE: percentile over the {n_pop} syntax survivors [{time.time() - t1:.1f}s]")
        t1 = time.time()
        signals = {p: (None if corpus.verbatim(*p) else dense_of[p], corpus.lexical(*p).lex)
                   for p in survivors}
        kept = cap_pairs(signals, M)
        n_verbatim = sum(1 for d, _ in signals.values() if d is None)
        print(f"LEX: the content-word matching of the {len(signals)} survivors; {n_verbatim} "
              f"verbatim survivor pair(s) rank on lex alone [{time.time() - t1:.1f}s]")
        print(f"CAP (M = {M}): {len(survivors)} syntax survivors → {len(kept)} pairs kept → "
              f"{2 * len(kept)} cross-encoder predictions (both directions)")
        kept_by_surah: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for p in kept:
            kept_by_surah[corpus.surah_of[p[0]]].append(p)
        gold_by_surah: dict[int, list[dict]] = defaultdict(list)
        for g in gold:
            gold_by_surah[corpus.surah_of[g["i"]]].append(g)

        if args.dry_run:
            sel = sum(len(kept_by_surah[s]) for s in todo)
            print(f"DRY RUN: stops before the cross-encoder; anchor surahs selected: "
                  f"{len(todo)} → {sel} pairs, {2 * sel} predictions. Total elapsed "
                  f"{time.time() - t0:.1f}s")
            return 0

        t1 = time.time()
        print("Loading the cross-encoder…")
        from quran_data.corpus import verses_by_id
        from retrieval.reranker import _passage_text

        by_ref = {(int(v["surah_number"]), int(v["ayah_number"])): _passage_text(v)
                  for v in verses_by_id().values()}
        ctx = {
            "corpus": corpus, "survivors": survivors, "dense_of": dense_of,
            "signals": signals, "texts": [by_ref[r] for r in corpus.refs],
            "ce": CrossEncoderScorer(),
        }
        print(f"  ready in {time.time() - t1:.1f}s (device={ctx['ce'].device})")
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        for s in todo:
            t2 = time.time()
            out = build_anchor(s, sorted(kept_by_surah[s]), gold_by_surah[s], ctx)
            # Atomic: an interrupted write leaves the previous file (or none), never a torn one.
            tmp = ckpt_dir / f"{s}.json.tmp"
            tmp.write_text(json.dumps({"params": digest, **out}, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, ckpt_dir / f"{s}.json")
            st = out["stats"]
            print(f"  anchor surah {s:3d}: {st['ce_pairs']:5d} cross-encoded → "
                  f"{st['stored_pairs']:4d} stored [{time.time() - t2:.1f}s]")

    done = {s: load_ckpt(s, honour_fresh=False) for s in all_surahs}
    missing = [s for s, c in done.items() if c is None]
    if missing:
        print(f"{len(all_surahs) - len(missing)}/{len(all_surahs)} anchor surahs checkpointed; "
              f"{paths.QURAN_SIMILARITY_JSON.name} is written only once all are. "
              f"Rerun without --surahs to finish.")
        return 0

    totals = defaultdict(int)
    for c in done.values():
        for k_, v in c["stats"].items():
            totals[k_] += v
    dataset = assemble(corpus, done, head)
    print("TOTAL: " + ", ".join(f"{k_}={v}" for k_, v in totals.items())
          + f", verses with neighbours={len(dataset['neighbours'])}")
    out = paths.QURAN_SIMILARITY_JSON
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dataset, ensure_ascii=False, sort_keys=False,
                              separators=(",", ":")), encoding="utf-8")
    tmp.replace(out)
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.2f} MB) — {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
