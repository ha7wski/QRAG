#!/usr/bin/env python3
"""
closeness_core.py — the order-invariant closeness definition, written once.

The four closeness builds (`build_surah_similarity.py`, `build_quran_similarity.py`,
`build_quran_passages.py`, `build_quran_close_verses.py`) IMPORT this module; none
of them carries a copy. The design is
`openspec/changes/order-invariant-closeness/design.md` (D1–D6); every constant
below was frozen there before any build of that change ran — decisions to record
there, never tuning knobs.

PURE: no disk, no model, no clock, no randomness. Every input — tokens, roots,
content-root sets, grammatical tools, IDF — is passed in by the caller, which
reads it through `quran_data`. Positions are 1-based QAC word numbers throughout.

Public API (stable — the builds depend on it):

  constants   W_LEMMA, W_ROOT, W_TOOL, TIE_BREAK; LEMMA, ROOT_ONLY, TOOL;
              SIGMA, SIGMA_EPS; L_MIN, DENSITY, CONTENT_MIN
  D1          content_words(roots, verse_roots, surah, ayah, tools) -> tuple[bool, ...]
  D2          Edge(p, q, kind); match_all(tok_a, tok_b, roots_a, roots_b,
              content_a, content_b) -> list[Edge]; content_edges(edges)
  D3          lex(edges, roots_a, roots_b, content_a, content_b, idf) -> float;
              matched_mass(edges, roots_a, roots_b, idf) -> float;
              shared_roots(edges, roots_a, roots_b) -> list[str]
  D4          syn(a, b) -> float; bigrams(seq); passes_syntax(syn, sigma=SIGMA)
  D5          syn_length_bound(la, lb); syn_bag_bound(bag_a, bag_b);
              syn_bigram_bound(bigram_bag_a, bigram_bag_b, la, lb)
  D6          Region(k, i1, i2, j1, j2, edges, score, content);
              best_region(edges) -> Region | None; rejection(k, span_a, span_b,
              content) -> str | None; passage_region(edges) -> Region | None

Decisions this module settles where the design leaves a detail open (recorded
here and in the builds' headers):

  * D3: a `lemma` edge normally joins two words of one root, but nothing forces
    the resolved primaries of two words with the same lemma token to agree. The
    matched mass of an edge is therefore `w · ½(idf(root_p) + idf(root_q))` —
    `w · idf(root)` whenever they agree, and symmetric in (A, B) when they do
    not, which also keeps `Mw ≤ ½(IA + IB)`, hence `lex ≤ 1`.
  * D4/D5: `syn` and every bound go through ONE arithmetic expression
    (`_syn_value`) fed with integer counts, so a bound computed from a count at
    least the true one is at least the true `syn` in floating point, not only in
    exact arithmetic: the pre-filters can never be stricter than the gate.
  * D5: the unigram-bag bound caps the bigram count by `min(c_uni, m − 1)`. The
    first elements of the k matched bigrams of B are k distinct words of B whose
    multiset equals that of the first elements of their partners in A — a common
    sub-multiset of size k — so `k ≤ c_uni`.
  * D6: the region is the maximum over EVERY window pair, `k` counting the edges
    with both ends inside both windows. Enumerating only A windows with their
    partners' full span in B (D6's wording read literally) misses pairs whose B
    window is narrower and made acceptance depend on which verse is passed first
    (≈ 8 % of accepted passages flipped with the swap); the delta spec's «the region
    maximising 2k − unmatched words of both windows» is the rule kept.
  * D2/D6 symmetry: exact ties (the matching's relative-position term, the region's
    tie-break) are settled in ONE canonical orientation of the pair and mirrored
    back, so `f(B, A)` is always the mirror of `f(A, B)`: the builds enumerate pairs
    in mushaf order, and that order must decide nothing.
"""
from __future__ import annotations

from bisect import insort
from collections import Counter
from typing import Iterable, NamedTuple, Sequence

# ── frozen values ──────────────────────────────────────────────────────────
# D2 (order-invariant-common-words D2, extended by order-invariant-closeness D2).
W_LEMMA, W_ROOT, W_TOOL = 1.0, 0.5, 1.0
TIE_BREAK = 1e-3
LEMMA, ROOT_ONLY, TOOL = "lemma", "root", "tool"
CONTENT_KINDS = frozenset({LEMMA, ROOT_ONLY})
IDENTICAL_KINDS = frozenset({LEMMA, TOOL})
# D4 — the syntactic gate (surah-similarity design, «Frozen parameters»).
SIGMA = 2 / 3
SIGMA_EPS = 1e-9          # syn ≥ σ − ε: `1 − 3/9` and `2/3` differ in the last bit
# D6 — the passage thresholds (add-shared-passages D3), unchanged.
L_MIN = 6
DENSITY = 0.75
CONTENT_MIN = 3

# Rule names the builds' headers record.
SIGNATURE_MEASURE = "uni+bigram-bag"
LEXICAL = "matching-idf-jaccard"
PASSAGE = "dense-region"


# ═══════════════════════════════════════════════════════════════════════════
#  D1 — content words
# ═══════════════════════════════════════════════════════════════════════════

def content_words(roots: Sequence[str | None], verse_roots, surah: int, ayah: int,
                  tools) -> tuple[bool, ...]:
    """D1: one flag per word — its resolved primary root is in the verse's content roots
    (`verse_roots`, as `build_surah_similarity.content_root_sets` computes them) AND its
    own `s:a:w` is not a grammatical-tool occurrence (`tools`, `word_function.json`)."""
    return tuple(r is not None and r in verse_roots and f"{surah}:{ayah}:{w}" not in tools
                 for w, r in enumerate(roots, start=1))


# ═══════════════════════════════════════════════════════════════════════════
#  D2 — the matching
# ═══════════════════════════════════════════════════════════════════════════

class Edge(NamedTuple):
    """One matched word pair: `p` in A, `q` in B (1-based), `kind` lemma | root | tool."""

    p: int
    q: int
    kind: str


def _assign(rows: list[int], cols: list[int], na: int, nb: int, edge_of) -> list[Edge]:
    """Maximum-weight one-to-one assignment of `rows` × `cols` (positions, 1-based).

    `edge_of(p, q)` → `(weight, kind)` or None. Every weight loses
    `TIE_BREAK × |p/na − q/nb|`, below half the smallest weight gap, so placement
    only ever breaks an exact tie. Edges of weight > 0 are kept.
    """
    if not rows or not cols:
        return []
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    weight = np.zeros((len(rows), len(cols)))
    kind: dict[tuple[int, int], str] = {}
    for x, p in enumerate(rows):
        for y, q in enumerate(cols):
            e = edge_of(p, q)
            if e is None:
                continue
            weight[x, y] = e[0] - TIE_BREAK * abs(p / na - q / nb)
            kind[(x, y)] = e[1]
    if not kind:
        return []
    r, c = linear_sum_assignment(weight, maximize=True)
    return [Edge(rows[x], cols[y], kind[(x, y)]) for x, y in zip(r.tolist(), c.tolist())
            if weight[x, y] > 0]


def _orientation_key(tok: Sequence, roots: Sequence, content: Sequence[bool]) -> tuple:
    """A total order on verses that does not depend on the caller's argument order.

    Length, content flags and resolved roots come first because they mean the same in
    every corpus; the tokens (vocabulary ids, corpus-dependent) only break what those
    leave equal.
    """
    return (len(tok), tuple(bool(c) for c in content),
            tuple("" if r is None else str(r) for r in roots), repr(tuple(tok)))


def match_all(tok_a: Sequence, tok_b: Sequence, roots_a: Sequence, roots_b: Sequence,
              content_a: Sequence[bool], content_b: Sequence[bool]) -> list[Edge]:
    """D2: the order-invariant matching of ALL words of A × B, sorted by `p`.

    Two content words: same token → `lemma` (`W_LEMMA`), another token under the
    same non-null resolved primary root → `root` (`W_ROOT`). Two NON-content words
    with the same token → `tool` (`W_TOOL`). Nothing else: a content word never
    pairs with a non-content word, so the assignment decomposes into the content
    problem (order-invariant-common-words' matching, unchanged up to D1) and an
    identical-token function-word problem, solved apart.

    Symmetric: `match_all(B, A)` is exactly the mirror of `match_all(A, B)`. The
    relative-position term leaves exact ties (a crossing and a non-crossing pairing
    cost the same when the differences share a sign), which the solver would settle
    by its argument order; the assignment is therefore always solved in ONE
    orientation, fixed by `_orientation_key`, and mirrored back.
    """
    if _orientation_key(tok_b, roots_b, content_b) < _orientation_key(tok_a, roots_a, content_a):
        return sorted(Edge(e.q, e.p, e.kind)
                      for e in _match_oriented(tok_b, tok_a, roots_b, roots_a, content_b, content_a))
    return _match_oriented(tok_a, tok_b, roots_a, roots_b, content_a, content_b)


def _match_oriented(tok_a: Sequence, tok_b: Sequence, roots_a: Sequence, roots_b: Sequence,
                    content_a: Sequence[bool], content_b: Sequence[bool]) -> list[Edge]:
    """`match_all` in the orientation given (see `match_all`)."""
    na, nb = len(tok_a), len(tok_b)
    ca = [p for p in range(1, na + 1) if content_a[p - 1]]
    cb = [q for q in range(1, nb + 1) if content_b[q - 1]]
    fa = [p for p in range(1, na + 1) if not content_a[p - 1]]
    fb = [q for q in range(1, nb + 1) if not content_b[q - 1]]

    def content_edge(p, q):
        if tok_a[p - 1] == tok_b[q - 1]:
            return W_LEMMA, LEMMA
        if roots_a[p - 1] is not None and roots_a[p - 1] == roots_b[q - 1]:
            return W_ROOT, ROOT_ONLY
        return None

    def tool_edge(p, q):
        return (W_TOOL, TOOL) if tok_a[p - 1] == tok_b[q - 1] else None

    return sorted(_assign(ca, cb, na, nb, content_edge) + _assign(fa, fb, na, nb, tool_edge))


def content_edges(edges: Iterable[Edge]) -> list[Edge]:
    """The edges joining two content words (`lemma`, `root`), in their order."""
    return [e for e in edges if e.kind in CONTENT_KINDS]


# ═══════════════════════════════════════════════════════════════════════════
#  D3 — lex
# ═══════════════════════════════════════════════════════════════════════════

def _edge_weight(kind: str) -> float:
    return W_LEMMA if kind == LEMMA else W_ROOT


def matched_mass(edges: Iterable[Edge], roots_a: Sequence, roots_b: Sequence,
                 idf: dict[str, float]) -> float:
    """`Mw`: Σ over content edges of `w · ½(idf(root_p) + idf(root_q))` (see the docstring)."""
    return sum(_edge_weight(e.kind) * 0.5 * (idf.get(roots_a[e.p - 1], 0.0)
                                             + idf.get(roots_b[e.q - 1], 0.0))
               for e in content_edges(edges))


def _content_mass(roots: Sequence, content: Sequence[bool], idf: dict[str, float]) -> float:
    return sum(idf.get(r, 0.0) for r, c in zip(roots, content) if c)


def lex(edges: Iterable[Edge], roots_a: Sequence, roots_b: Sequence,
        content_a: Sequence[bool], content_b: Sequence[bool], idf: dict[str, float]) -> float:
    """D3: `Mw / (IA + IB − Mw)` — the word-level IDF Jaccard of the content matching.

    `IA` / `IB`: Σ `idf(root)` over each verse's content WORDS (a repeated root counts
    per occurrence). A root absent from `idf` (nobody holds it as primary) weighs 0.
    0 when the union mass is 0.
    """
    mw = matched_mass(edges, roots_a, roots_b, idf)
    union = _content_mass(roots_a, content_a, idf) + _content_mass(roots_b, content_b, idf) - mw
    if union <= 0:
        return 0.0
    return min(1.0, mw / union)


def shared_roots(edges: Iterable[Edge], roots_a: Sequence, roots_b: Sequence) -> list[str]:
    """The roots displayed as shared: both ends' roots of every content edge, sorted."""
    return sorted({r for e in content_edges(edges)
                   for r in (roots_a[e.p - 1], roots_b[e.q - 1]) if r})


# ═══════════════════════════════════════════════════════════════════════════
#  D4 — syn, and D5 — its exact upper bounds
# ═══════════════════════════════════════════════════════════════════════════

def bigrams(seq: Sequence) -> list[tuple]:
    """The consecutive element pairs of `seq`, in order."""
    return list(zip(seq, seq[1:]))


def _common(ca: Counter, cb: Counter) -> int:
    if len(ca) > len(cb):
        ca, cb = cb, ca
    return sum(min(n, cb[e]) for e, n in ca.items() if e in cb)


def _syn_value(c_uni: int, c_bi: int, la: int, lb: int) -> float:
    """The ONE expression `syn` and every bound evaluate — monotone in both counts."""
    longest = max(la, lb)
    if longest == 0:
        return 1.0
    uni = c_uni / longest
    bi = uni if longest == 1 else c_bi / (longest - 1)
    return 0.5 * uni + 0.5 * bi


def syn(a: Sequence, b: Sequence) -> float:
    """D4: `½·uni + ½·bi` over two signatures (one hashable element per word).

    `uni = |EA ∩ EB| / max(nA, nB)` (multisets of elements), `bi = |BA ∩ BB| /
    max(nA − 1, nB − 1)` (multisets of consecutive pairs), `bi = uni` when the longer
    has one word; 1 for two empty signatures. Symmetric, in [0, 1], 1 iff equal as
    multisets of elements and of bigrams. A displaced block costs only its junctions.
    """
    return _syn_value(_common(Counter(a), Counter(b)),
                      _common(Counter(bigrams(a)), Counter(bigrams(b))), len(a), len(b))


def passes_syntax(value: float, sigma: float = SIGMA) -> bool:
    """The syntactic gate: `syn ≥ σ`, tolerant of the last bit."""
    return value >= sigma - SIGMA_EPS


def syn_length_bound(la: int, lb: int) -> float:
    """D5: `½(m/M + (m−1)/(M−1))` — `syn`'s bound from the two word counts alone."""
    m = min(la, lb)
    return _syn_value(m, max(m - 1, 0), la, lb)


def syn_bag_bound(bag_a: Counter, bag_b: Counter) -> float:
    """D5: `syn`'s bound from the two element bags: exact `uni`, `bi` capped by
    `min(c_uni, m − 1)` (see the module docstring for why `k ≤ c_uni`)."""
    la, lb = sum(bag_a.values()), sum(bag_b.values())
    c = _common(bag_a, bag_b)
    return _syn_value(c, min(c, max(min(la, lb) - 1, 0)), la, lb)


def syn_bigram_bound(bi_a: Counter, bi_b: Counter, la: int, lb: int) -> float:
    """D5: `syn`'s bound from the two bigram bags: exact `bi`, `uni` capped by `m`."""
    return _syn_value(min(la, lb), _common(bi_a, bi_b), la, lb)


# ═══════════════════════════════════════════════════════════════════════════
#  D6 — the passage as an order-free dense region
# ═══════════════════════════════════════════════════════════════════════════

class Region(NamedTuple):
    """A window pair of identical-token edges: `[i1, i2]` in A, `[j1, j2]` in B (1-based,
    inclusive), its `k` kept edges, `score = 2k − gaps` and `content` = kept `lemma` edges."""

    k: int
    i1: int
    i2: int
    j1: int
    j2: int
    edges: tuple[Edge, ...]
    score: int
    content: int


def best_region(edges: Iterable[Edge]) -> Region | None:
    """D6: the window pair maximising `2k − (i2 − i1 + 1 − k) − (j2 − j1 + 1 − k)`.

    Over the identical-token edges (`lemma`, `tool`; `root` edges are gaps) and EVERY
    window pair `[i1, i2] × [j1, j2]`, `k` counting the edges with both ends inside
    both windows. Ties: smaller `i1`, then the shorter A window, then smaller `j1`,
    then the shorter B window — read in ONE orientation of the pair (the smaller of
    the edge list and its mirror), so that `best_region` of the mirrored edges is
    exactly the mirrored region: whether two verses share a passage, and where, never
    depends on which one is passed first. (An edge set equal to its own mirror has no
    orientation to read the tie in; a region and its mirror then tie, with the same k,
    score, content and acceptance.) None when there is no identical-token edge.
    NOT the acceptance rule.
    """
    ident = sorted(e for e in edges if e.kind in IDENTICAL_KINDS)
    mirror = sorted(Edge(e.q, e.p, e.kind) for e in ident)
    if mirror < ident:
        r = _best_region_oriented(mirror)
        return None if r is None else Region(
            r.k, r.j1, r.j2, r.i1, r.i2, tuple(sorted(Edge(e.q, e.p, e.kind) for e in r.edges)),
            r.score, r.content)
    return _best_region_oriented(ident)


def best_region_in_a(edges: Iterable[Edge]) -> Region | None:
    """D6's region with its ties read in A AS PASSED: smaller `i1`, then the shorter A
    window, then smaller `j1`, then the shorter B window.

    The reading the shared-passages spec pre-registers for the stored relation, whose
    `a` is the lower-surah verse; `best_region` reads the same ties in a canonical
    orientation instead (symmetric in its arguments), and the two may keep different
    regions on an exact tie (5:33 / 7:124). Same score as `best_region` always.
    """
    return _best_region_oriented(sorted(e for e in edges if e.kind in IDENTICAL_KINDS))


def _best_region_oriented(ident: list[Edge]) -> Region | None:
    """`best_region` over `ident` (identical-token edges sorted by `p`), as oriented.

    An optimal region is tight: its windows start and end on kept edges (a loose end
    is an unmatched word that only lowers the score). So it is enumerated as an A window
    `[p_x, p_y]` (both edges kept) and, among that window's edges sorted by `q`, a
    contiguous run `l..r` holding both: `score = (4r − q_r) − (4l − q_l) + 3 − spanA`,
    whose two halves are maximised apart — O(m³) over m edges.
    """
    best: Region | None = None
    n = len(ident)
    for x in range(n):
        by_q: list[tuple[int, int]] = []          # (q, index in ident) of the A window
        for y in range(x, n):
            insort(by_q, (ident[y].q, y))
            span_a = ident[y].p - ident[x].p + 1
            ranks = [t for t, (_, idx) in enumerate(by_q) if idx in (x, y)]
            lo, hi = ranks[0], ranks[-1]
            # l ≤ lo maximising q_l − 4l (ties: smaller q_l, i.e. smaller j1)
            l = max(range(lo + 1), key=lambda t: (by_q[t][0] - 4 * t, -by_q[t][0]))
            # r ≥ hi maximising 4r − q_r (ties: smaller q_r, i.e. the shorter B window)
            r = max(range(hi, len(by_q)), key=lambda t: (4 * t - by_q[t][0], -by_q[t][0]))
            k = r - l + 1
            j1, j2 = by_q[l][0], by_q[r][0]
            score = 2 * k - (span_a - k) - (j2 - j1 + 1 - k)
            if best is None or score > best.score:     # strict: the first tie stays
                kept = tuple(sorted(ident[idx] for _, idx in by_q[l:r + 1]))
                best = Region(k, ident[x].p, ident[y].p, j1, j2, kept, score,
                              sum(1 for e in kept if e.kind == LEMMA))
    return best


def rejection(k: int, span_a: int, span_b: int, content: int) -> str | None:
    """The first acceptance rule a region fails — `l_min`, `density`, `content_min` — or None."""
    if k < L_MIN:
        return "l_min"
    if k < DENSITY * max(span_a, span_b):
        return "density"
    if content < CONTENT_MIN:
        return "content_min"
    return None


def region_rejection(region: Region | None) -> str | None:
    """`rejection` of a region (None → `l_min`), or None when it is accepted."""
    if region is None:
        return "l_min"
    return rejection(region.k, region.i2 - region.i1 + 1, region.j2 - region.j1 + 1,
                     region.content)


def passage_region(edges: Iterable[Edge]) -> Region | None:
    """D6: the best region when it is accepted (`k ≥ L_MIN`, `k ≥ DENSITY × the longer
    window`, `≥ CONTENT_MIN` kept `lemma` edges), else None."""
    region = best_region(edges)
    return region if region is not None and region_rejection(region) is None else None
