#!/usr/bin/env python3
"""
build_quran_similarity.py — the offline cross-surah similarity build.

Answers, once and for every verse, «which verses of the OTHER surahs are close to
this one?» and writes the answer to `data/derived/quran_similarity.json`, which
`GET /verse/{surah}/{ayah}/similar` serves without loading any model. The design
is `openspec/changes/add-quran-wide-similar-verses/design.md`; it reuses the
intra-surah definition unchanged and only changes the population:

  * D1 — the signature, the syntactic similarity, the coverage, the semantic
    score, the candidate cap, the neighbour selection, the cross-encoder, the
    loaders and every frozen parameter are IMPORTED from
    `scripts/build_surah_similarity.py`, never copied, so the two datasets
    cannot drift on what «close» means.
  * D2 — the population is every pair of scored verses in two DIFFERENT surahs
    (19 113 299 pairs over the full corpus). Verses are keyed by their global
    corpus index (0…6235, i.e. (surah, ayah) order) inside the build, so the
    intra helpers keyed on `int` work unchanged; the file uses `"s:a"` refs.
  * D3 — the syntactic gate runs behind two EXACT pre-filters (length window,
    multiset bag distance): each is a lower bound `d ≤ lev`, evaluated through
    the very float expression `syn_similarity` uses, so a pruned pair provably
    scores below σ. Survivors are scored by the intra `syn_similarity` itself.
  * D4 — dense is the cosine's average-rank percentile among ALL cross-surah
    scored pairs (one global population, so it is symmetric).
  * D5 — `cap_pairs(M)`, the symmetrised cross-encoder, the semantic gate, the
    shared-root rule, `score = sem × syn`, `select_neighbours(K)`.
  * D7 — the file layout, schema 1.

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
    DENSE_ON_VERBATIM, FLOOR, K, M, REQUIRE_SHARED_ROOT, RERANKER_MODEL, SIGMA,
    SIGMA_EPS, SIGNATURE, TAU_SEM, W_CE, W_DENSE, CrossEncoderScorer, cap_pairs,
    cov_similarity, load_content_roots, load_signatures, load_vectors, passes_syntax,
    qdrant_lock_held, rnd, select_neighbours, sem_score, syn_similarity,
)

SCHEMA = loaders.QURAN_SIMILARITY_SCHEMA
SCOPE = "cross-surah"
DENSE_POPULATION = "cross-surah"
GOLD_JSON = ROOT / "tests" / "eval" / "quran_similarity_gold.json"
REBUILD = "python scripts/build_quran_similarity.py"
# The intra header keys this build must share verbatim (spec «The parameters are
# the intra-surah ones»); their digest is recorded so the equality is checkable.
SHARED_PARAMS = ("K", "M", "w_ce", "w_dense", "floor", "sigma", "tau_sem", "signature",
                 "dense_on_verbatim", "require_shared_root")
# `passes_syntax`'s threshold, as the one float it compares against.
_SYN_THRESHOLD = SIGMA - SIGMA_EPS


# ═══════════════════════════════════════════════════════════════════════════
#  Pure functions — importable by tests, no disk, no model
# ═══════════════════════════════════════════════════════════════════════════

def syn_upper_bound(d: int, la: int, lb: int) -> float:
    """`syn_similarity`'s own expression with a LOWER bound `d` of lev in its place.

    `syn_similarity` computes `1.0 − lev / longest`. True division and
    subtraction are correctly rounded, hence monotone, so `lev ≥ d` implies
    `syn_similarity(a, b) ≤ syn_upper_bound(d, |a|, |b|)` in floating point,
    not only in exact arithmetic. A pair whose bound fails `passes_syntax`
    therefore fails it too: the pre-filters can never be stricter than the gate.
    """
    longest = max(la, lb)
    if longest == 0:
        return 1.0
    return 1.0 - d / longest


def bag_distance(ca: Counter, cb: Counter) -> int:
    """`max(|A ∖ B|, |B ∖ A|)` over multisets — a lower bound of unit-cost lev.

    Equal to `max(|A|, |B|) − |A ∩ B|`: every edit fixes at most one surplus
    element on each side.
    """
    common = sum(min(n, cb[e]) for e, n in ca.items() if e in cb)
    return max(sum(ca.values()), sum(cb.values())) - common


def prefilter_stage(a: Sequence, b: Sequence) -> str | None:
    """The pre-filter that drops `(a, b)` — `length_window`, `bag_bound` — or None.

    The scalar reference of what `SyntaxIndex.survivors` does vectorised; the
    evaluation and the exactness check read it.
    """
    if not passes_syntax(syn_upper_bound(abs(len(a) - len(b)), len(a), len(b))):
        return "length_window"
    if not passes_syntax(syn_upper_bound(bag_distance(Counter(a), Counter(b)), len(a), len(b))):
        return "bag_bound"
    return None


def length_windows(max_len: int) -> list[tuple[int, int]]:
    """`[(lo, hi)]` per length n: the partner lengths the length bound lets through.

    Derived from the exact inequality itself — every L is tested through
    `passes_syntax(syn_upper_bound(|n − L|, n, L))` — not from a closed form, so
    the window cannot drift from the gate at a float edge. The admitted set is
    an interval (the bound is monotone in |n − L| on each side); asserted.
    """
    out = []
    for n in range(max_len + 1):
        ok = [L for L in range(max_len + 1)
              if passes_syntax(syn_upper_bound(abs(n - L), n, L))]
        assert ok == list(range(ok[0], ok[-1] + 1)), f"length window of {n} is not an interval"
        out.append((ok[0], ok[-1]))
    return out


def intern_signatures(sigs: Sequence[Sequence]) -> list[tuple[int, ...]]:
    """Each element replaced by a small int, first-seen order.

    A bijection on elements, so `syn_similarity` (equality only) gives the same
    value on the interned sequences as on the element tuples.
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
    surah, `scored` the global indexes with ≥ 1 content root.
    """

    def __init__(self, seqs: Sequence[tuple[int, ...]], surah_of: Sequence[int],
                 scored: Sequence[int]):
        import numpy as np

        self.seqs = list(seqs)
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
        surah of its lower verse). Returns `[(i, j, syn)]` passing the gate,
        sorted, and the per-stage counts.
        """
        import numpy as np

        out: list[tuple[int, int, float]] = []
        stats = {"examined": 0, "length_window": 0, "bag_bound": 0, "syntax_gate": 0}
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
            mine = self.counts[i]
            nz = np.flatnonzero(mine)
            common = np.minimum(self.counts[np.ix_(cands, nz)], mine[nz]).sum(axis=1, dtype="int64")
            longest = np.maximum(n, self.lengths[cands])
            with np.errstate(divide="ignore", invalid="ignore"):
                # syn_upper_bound, vectorised: the same IEEE operations on the same ints
                bound = np.where(longest == 0, 1.0, 1.0 - (longest - common) / longest)
            kept = cands[bound >= _SYN_THRESHOLD]
            stats["bag_bound"] += len(kept)
            a = self.seqs[i]
            for j in kept.tolist():
                s = syn_similarity(a, self.seqs[j])
                if passes_syntax(s):
                    out.append((i, j, s))
        stats["syntax_gate"] = len(out)
        return out, stats


_WORKER: SyntaxIndex | None = None


def _init_worker(seqs, surah_of, scored) -> None:
    global _WORKER
    _WORKER = SyntaxIndex(seqs, surah_of, scored)


def _worker_survivors(surah: int):
    t0 = time.time()
    out, stats = _WORKER.survivors(surah)
    stats["elapsed"] = time.time() - t0
    return surah, out, stats


def syntax_stage(seqs, surah_of, scored, anchors: Sequence[int], jobs: int
                 ) -> tuple[dict[tuple[int, int], float], dict[int, dict]]:
    """`{(i, j): syn}` over the anchor surahs, and their per-surah stats.

    The result does not depend on `jobs`: each anchor surah's pairs are
    computed independently and merged in surah order.
    """
    results = {}
    if jobs <= 1:
        _init_worker(seqs, surah_of, scored)
        for s in anchors:
            surah, out, st = _worker_survivors(s)
            results[surah] = (out, st)
    else:
        # Largest first: surah 2 alone is ~1/8 of the work.
        sizes = Counter(surah_of[i] for i in scored)
        order = sorted(anchors, key=lambda s: -sizes.get(s, 0) * _after(sizes, s))
        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(jobs, initializer=_init_worker, initargs=(seqs, surah_of, scored)) as pool:
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

def dense_stage(vectors: dict, refs: list[tuple[int, int]], scored: list[int],
                wanted: set[tuple[int, int]], block: int = 256
                ) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], float], int]:
    """`(cos_of, dense_of, n_population)` for the `wanted` pairs.

    One matrix product per row block over the scored verses (in global order,
    hence grouped by surah); the population is each row's cross-surah upper
    triangle, i.e. every column from the next surah onward. The cosine of a
    wanted pair is read out of the SAME product as its population entry, so a
    pair's value is bit-identical to the one it is ranked among.
    """
    import numpy as np

    X = np.stack([np.asarray(vectors[refs[i]], dtype="float64") for i in scored])
    surahs = np.asarray([refs[i][0] for i in scored], dtype="int32")
    pos = {g: p for p, g in enumerate(scored)}
    # first scored position of a later surah, per row
    nxt = np.searchsorted(surahs, surahs, side="right")
    n_pop = int(sum(len(scored) - int(x) for x in nxt))
    pop = np.empty(n_pop, dtype="float64")
    by_row: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for i, j in wanted:
        by_row[pos[i]].append((pos[j], (i, j)))
    cos_of: dict[tuple[int, int], float] = {}
    filled = 0
    for r0 in range(0, len(scored), block):
        G = X[r0:r0 + block] @ X.T
        for r in range(G.shape[0]):
            p = r0 + r
            row = G[r, int(nxt[p]):]
            pop[filled:filled + len(row)] = row
            filled += len(row)
            for q, key in by_row.get(p, ()):
                cos_of[key] = float(G[r, q])
    assert filled == n_pop
    pop.sort()
    keys = sorted(cos_of)
    dense_of = dict(zip(keys, percentile_in(pop, [cos_of[k] for k in keys])))
    return cos_of, dense_of, n_pop


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
        "dense_on_verbatim": DENSE_ON_VERBATIM,
        "dense_population": DENSE_POPULATION,
        "require_shared_root": REQUIRE_SHARED_ROOT,
        # D1: the intra builder's digest of the parameters both builds share
        "intra_params_sha256": intra.params_digest(shared),
        "gold_sha256": gold_sha,
    }


def inputs_digest(vectors: dict) -> str:
    """The intra digest (its source, the derived inputs, stoplist, vectors) + this source."""
    h = hashlib.sha256(intra.inputs_digest(vectors).encode())
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()


def ref_str(ref: tuple[int, int]) -> str:
    return f"{ref[0]}:{ref[1]}"


def parse_ref(raw: str) -> tuple[int, int]:
    s, a = raw.split(":")
    return int(s), int(a)


class Corpus:
    """The verses in global order, their signatures, content roots and verbatim words."""

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

    def verbatim(self, i: int, j: int) -> bool:
        return self.words.get(self.refs[i]) == self.words.get(self.refs[j])

    def cov(self, i: int, j: int) -> float:
        return cov_similarity(self.roots[i], self.roots[j], self.idf)


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
    `passed` — whether it is then `stored` or lost at `top_k` depends on the
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
        dense, cov = signals[p]
        sem = sem_score(ce_of[p], dense, cov)
        if sem < TAU_SEM:
            continue
        shared = sorted(corpus.roots[p[0]] & corpus.roots[p[1]])
        if REQUIRE_SHARED_ROOT and not shared:
            continue
        syn = survivors[p]
        # `dense` stays the measured value; `verbatim` says it did not enter `sem`
        sig = {"s": rnd(sem * syn), "sem": rnd(sem), "syn": rnd(syn), "ce": rnd(ce_of[p]),
               "dense": rnd(dense_of[p]), "cov": rnd(cov), "roots": shared}
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
        syn = syn_similarity(a_sig, b_sig)
        verbatim = corpus.verbatim(*p)
        cov = corpus.cov(*p)
        ce = ce_of.get(p)
        sem = sem_score(ce, None if verbatim else dense_of[p], cov) if ce is not None else None
        row.update({"syn": rnd(syn), "dense": rnd(dense_of[p]), "cov": rnd(cov),
                    "verbatim": verbatim, "ce": None if ce is None else rnd(ce),
                    "sem": None if sem is None else rnd(sem)})
        # A pair below σ is a `syntax_gate` loss whichever stage dropped it first;
        # a pre-filter stage is reported only for a pair whose syn ≥ σ — a bug.
        dropped_by = prefilter_stage(a_sig, b_sig)
        if not passes_syntax(syn):
            row["stage"] = "syntax_gate"
        elif dropped_by:
            row["stage"] = dropped_by
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
    lists = select_neighbours(stored, corpus.scored)
    neighbours = {}
    for i in sorted(lists):
        if lists[i]:
            neighbours[ref_str(corpus.refs[i])] = [
                {"r": ref_str(corpus.refs[e["a"]]), **{k: v for k, v in e.items() if k != "a"}}
                for e in lists[i]]
    listed = {ref: {e["r"] for e in lst} for ref, lst in neighbours.items()}
    gold_rows = []
    for s in sorted(done):
        for row in done[s]["diagnostics"]:
            if row["stage"] == "passed":
                ok = row["b"] in listed.get(row["a"], ()) or row["a"] in listed.get(row["b"], ())
                row = {**row, "stage": "stored" if ok else "top_k"}
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
                  f"length window → {st['bag_bound']:6d} bag bound → {st['syntax_gate']:5d} "
                  f"syntax gate [{st['elapsed']:.1f}s]")
    print(f"SYNTAX: {int(total['examined'])} cross-surah scored pairs → "
          f"{int(total['length_window'])} in the length window → {int(total['bag_bound'])} "
          f"past the bag bound → {int(total['syntax_gate'])} pass the syntax gate "
          f"(σ = {SIGMA:.4f}) — {elapsed:.1f}s wall, {total['elapsed']:.1f}s summed over workers")
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
                                        anchors, args.jobs)
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
        _, dense_of, n_pop = dense_stage(vectors, corpus.refs, corpus.scored, wanted)
        signals = {p: (None if corpus.verbatim(*p) else dense_of[p], corpus.cov(*p))
                   for p in survivors}
        kept = cap_pairs(signals, M)
        n_verbatim = sum(1 for d, _ in signals.values() if d is None)
        print(f"DENSE: percentile over {n_pop} cross-surah scored pairs; {n_verbatim} verbatim "
              f"survivor pair(s) rank on coverage alone [{time.time() - t1:.1f}s]")
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
