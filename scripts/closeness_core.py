#!/usr/bin/env python3
"""
closeness_core.py — the order-invariant closeness definition, written once.

The four closeness builds (`build_surah_similarity.py`, `build_quran_similarity.py`,
`build_quran_passages.py`, `build_quran_close_verses.py`) IMPORT this module; none
of them carries a copy. The design is
`openspec/changes/order-invariant-closeness/design.md` — VERSION 2, «Decisions
(version 2)» D1–D6; every constant below was frozen there before any build of
that change ran — decisions to record there, never tuning knobs. Version 1
(unigram + bigram bag, relative-position tie-break, best-scoring region) was
measured and closed; its definitions are gone from here.

PURE: no disk, no model, no clock, no randomness. Every input — tokens, roots,
content-root sets, grammatical tools, IDF, QAC segments — is passed in by the
caller, which reads it through `quran_data`. Positions are 1-based QAC word
numbers throughout.

Public API (stable — the builds depend on it):

  constants   W_LEMMA, W_ROOT, W_TOOL, TIE_BREAK_WEIGHT; LEMMA, ROOT_ONLY, TOOL;
              SIGMA, SIGMA_EPS; L_MIN, DENSITY, CONTENT_MIN; N_POS
  names       SIGNATURE, SIGNATURE_MEASURE, LEXICAL, TIE_BREAK, PASSAGE (headers)
  D1          content_words(roots, verse_roots, surah, ayah, tools) -> tuple[bool, ...]
  D2          Edge(p, q, kind); match_all(tok_a, tok_b, roots_a, roots_b,
              content_a, content_b) -> list[Edge]; content_edges(edges); mirror(edges)
  D3          lex(edges, roots_a, roots_b, content_a, content_b, idf) -> float;
              matched_mass(edges, roots_a, roots_b, idf) -> float;
              shared_roots(edges, roots_a, roots_b) -> list[str]
  D4          coarse_element(segments) -> tuple[str, ...]; coarse_signature(words);
              levenshtein(a, b) -> int; syn_seq(a, b) -> float;
              block_reorder(seq_b, edges, n_a) -> tuple; syn(a, b, edges) -> float;
              passes_syntax(value, sigma=SIGMA)
  D5          syn_length_bound(la, lb); syn_bag_bound(bag_a, bag_b)
  D6          Region(k, i1, i2, j1, j2, edges, score, content);
              passage_region(edges) -> Region | None (= best_region_in_a);
              rejection(k, span_a, span_b, content) -> str | None;
              region_rejection(region) -> str | None

Decisions this module settles where the design leaves a detail open (recorded
here and in the builds' headers):

  * D2: an anchor is an identical-token pair whose token occurs once in A and
    once in B AND whose two words are both content or both non-content — a pair
    the matching could join at all. Anchors are forced by solving the assignment
    without them and appending them; forcing never lowers the total (each end's
    only other candidates weigh ½, so the exchange gains ≥ 0), so the matching is
    still maximum-weight. `δ` is `statistics.median` (the mean of the two middle
    shifts for an even count). The penalty `TIE_BREAK_WEIGHT · |(q − p) − δ| /
    max(nA, nB)` is below 2·10⁻³ per edge, hence below the smallest weight gap
    summed over any verse, so placement only ever breaks an exact tie.
  * D3: a `lemma` edge normally joins two words of one root, but nothing forces
    the resolved primaries of two words with the same lemma token to agree. The
    matched mass of an edge is therefore `w · ½(idf(root_p) + idf(root_q))` —
    `w · idf(root)` whenever they agree, and symmetric in (A, B) when they do
    not, which also keeps `Mw ≤ ½(IA + IB)`, hence `lex ≤ 1`.
  * D4, the cut: a block starts at a matched position whose partner is NOT THE
    SUCCESSOR of the previous matched position's partner — a jump in either
    direction. The design's sentence («not after», design.md D4) and the intra
    spec's («partners keep their order») read as a DESCENT alone (≤); under that
    reading «Y X Z» cuts into [Y], [X Z] and sorts to «X Z Y», never A — the
    3-block exchange scores 3/7 and a displaced 3-block in 9 scores 1/3, against
    D4's own «1 for a pure permutation of blocks» and D9's «displaced 3-block
    keeps syn ≥ σ». The successor cut is the reading under which both hold. It is
    NOT a refinement of the descent cut: the two are different relations and
    neither dominates (on a partial matching the descent cut can rebuild A where
    the successor cut splits a run — `tests/test_closeness_core.py` pins one case
    each way; on 20 000 random inputs they differ on 1 245, the descent cut higher
    on 529). A re-implementation from the design's wording would therefore give
    other real verdicts (the version-2 review's probe over 3 989 sampled
    cross-surah pairs found one gate flip, 19:37/25:48 — reproduced and pinned);
    reconciling that wording with this rule is a design edit, outside this
    module.
  * D4, leading unmatched positions: «an unmatched position stays with the block
    it follows» leaves the leading ones, which follow nothing, unsaid. They
    belong to the FIRST block — the one completion under which every block holds
    a matched position, so the order by first partner is total without a rule the
    design does not state (a block of their own would need «pinned at the front»).
    It decides a real verdict (19:37/25:48 reaches σ with it, stays at the plain
    0.6154 without), pinned by a test.
  * D4, a known consequence (not a defect — D4 says «from the D2 edges»): the
    re-ordering follows EVERY edge, tool edges included, and knows no minimum
    block size. So a pair can pass σ on shared function words alone (7:34/27:80:
    plain 0.182, re-ordered 0.727 on إِذَا / لَا / وَلَا — unstorable all the same,
    `Mw = 0`), and a verse against any permutation of its words, every word
    matched, scores 1 (six blocks of one). Both are pinned so the version-2
    figures are read with them; changing either is a design decision.
  * D4/D5, floating point: `syn_seq` is `(M − lev) / M` — one integer numerator,
    one division — and each bound is `count / M`, so a bound whose count is at
    least `M − lev` is at least `syn` in IEEE arithmetic too (`1 − 3/9` exceeds
    `6/9` by one bit): the pre-filters can never be stricter than the gate.
  * D6: only TIGHT candidates are enumerated — the A window's two bounding edges
    both kept, the B window a run of the sorted partners. A loose candidate keeps
    the same edges in a wider window, so it is never accepted when the tight one
    is not and never beats it on `2k − gaps`; the brute-force test over every
    window pair bounded by matched positions pins the equality.
  * D2 symmetry: the tie-break weights are symmetric, but an exact tie between
    two pairings would be settled by the solver's argument order; the assignment
    is therefore always solved in ONE canonical orientation of the pair and
    mirrored back, so `match_all(B, A)` is the mirror of `match_all(A, B)`. D6 is
    deliberately NOT canonicalised: its ties are read in A as passed, the
    lower-surah verse.
  * N_POS lives here: the coarse element is this module's definition, and
    `build_surah_similarity` imports this module at its top, before it could
    define the tuple — the core cannot import it back without a cycle.
"""
from __future__ import annotations

from bisect import insort
from collections import Counter
from statistics import median
from typing import Iterable, NamedTuple, Sequence

# ── frozen values ──────────────────────────────────────────────────────────
# D2 (order-invariant-common-words D2, extended by order-invariant-closeness D2).
W_LEMMA, W_ROOT, W_TOOL = 1.0, 0.5, 1.0
TIE_BREAK_WEIGHT = 1e-3
LEMMA, ROOT_ONLY, TOOL = "lemma", "root", "tool"
CONTENT_KINDS = frozenset({LEMMA, ROOT_ONLY})
IDENTICAL_KINDS = frozenset({LEMMA, TOOL})
# D4 — the syntactic gate (surah-similarity design, «Frozen parameters»).
SIGMA = 2 / 3
SIGMA_EPS = 1e-9          # syn ≥ σ − ε: `1 − 3/9` and `2/3` differ in the last bit
# D4 — the noun subcategories that ARE a part of speech (`N:<subcat>`). Derivation
# and inflection tokens (ACT_PCPL, PASS_PCPL, VN, INDEF, …) are deliberately absent.
N_POS = ("PN", "ADJ", "PRON", "DEM", "REL", "T", "LOC", "NV", "INTG", "COND", "ADDR")
_N_POS_SET = frozenset(N_POS)
_ASPECTS = ("PERF", "IMPF", "IMPV")
# D6 — the passage thresholds (add-shared-passages D3), unchanged.
L_MIN = 6
DENSITY = 0.75
CONTENT_MIN = 3

# Rule names the builds' headers record (D8).
SIGNATURE = "stem-coarse"
SIGNATURE_MEASURE = "levenshtein+block-reorder"
LEXICAL = "matching-idf-jaccard"
TIE_BREAK = "median-shift"
PASSAGE = "largest-accepted-region"


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


def mirror(edges: Iterable[Edge]) -> list[Edge]:
    """The same edges read from B's side (`p` ↔ `q`), sorted by their new `p`."""
    return sorted(Edge(e.q, e.p, e.kind) for e in edges)


def _assign(rows: list[int], cols: list[int], na: int, nb: int, edge_of,
            delta: float) -> list[Edge]:
    """Maximum-weight one-to-one assignment of `rows` × `cols` (positions, 1-based).

    `edge_of(p, q)` → `(weight, kind)` or None. Every weight loses
    `TIE_BREAK_WEIGHT × |(q − p) − delta| / max(na, nb)` (D2: the partner at the
    anchors' offset), below the smallest weight gap, so placement only ever breaks
    an exact tie. Edges of weight > 0 are kept.
    """
    if not rows or not cols:
        return []
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    longest = max(na, nb)
    weight = np.zeros((len(rows), len(cols)))
    kind: dict[tuple[int, int], str] = {}
    for x, p in enumerate(rows):
        for y, q in enumerate(cols):
            e = edge_of(p, q)
            if e is None:
                continue
            weight[x, y] = e[0] - TIE_BREAK_WEIGHT * abs((q - p) - delta) / longest
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

    Ties (version 2, median shift): the ANCHORS — pairs whose token occurs exactly
    once in each verse — are forced, `δ = median(q − p)` over them (0 with none),
    and every other weight loses `TIE_BREAK_WEIGHT · |(q − p) − δ| / max(nA, nB)`,
    so a repeated token takes the partner at the OFFSET of the shared material,
    not at the same relative position of its verse.

    Symmetric: `match_all(B, A)` is exactly the mirror of `match_all(A, B)`. The
    weights are symmetric, but an exact tie between two pairings would be settled
    by the solver's argument order; the assignment is therefore always solved in
    ONE orientation, fixed by `_orientation_key`, and mirrored back.
    """
    if _orientation_key(tok_b, roots_b, content_b) < _orientation_key(tok_a, roots_a, content_a):
        return mirror(_match_oriented(tok_b, tok_a, roots_b, roots_a, content_b, content_a))
    return _match_oriented(tok_a, tok_b, roots_a, roots_b, content_a, content_b)


def _anchors(tok_a: Sequence, tok_b: Sequence, content_a: Sequence[bool],
             content_b: Sequence[bool]) -> list[Edge]:
    """D2: the pairs whose token occurs once in A and once in B, both ends content or
    both non-content (a pair the matching could join), as `lemma` / `tool` edges."""
    count_a, count_b = Counter(tok_a), Counter(tok_b)
    where_b = {t: q for q, t in enumerate(tok_b, start=1) if count_b[t] == 1}
    out: list[Edge] = []
    for p, t in enumerate(tok_a, start=1):
        if count_a[t] == 1 and t in where_b and bool(content_a[p - 1]) == bool(
                content_b[where_b[t] - 1]):
            out.append(Edge(p, where_b[t], LEMMA if content_a[p - 1] else TOOL))
    return out


def _match_oriented(tok_a: Sequence, tok_b: Sequence, roots_a: Sequence, roots_b: Sequence,
                    content_a: Sequence[bool], content_b: Sequence[bool]) -> list[Edge]:
    """`match_all` in the orientation given (see `match_all`)."""
    na, nb = len(tok_a), len(tok_b)
    anchors = _anchors(tok_a, tok_b, content_a, content_b)
    delta = float(median(e.q - e.p for e in anchors)) if anchors else 0.0
    taken_a = {e.p for e in anchors}
    taken_b = {e.q for e in anchors}
    ca = [p for p in range(1, na + 1) if content_a[p - 1] and p not in taken_a]
    cb = [q for q in range(1, nb + 1) if content_b[q - 1] and q not in taken_b]
    fa = [p for p in range(1, na + 1) if not content_a[p - 1] and p not in taken_a]
    fb = [q for q in range(1, nb + 1) if not content_b[q - 1] and q not in taken_b]

    def content_edge(p, q):
        if tok_a[p - 1] == tok_b[q - 1]:
            return W_LEMMA, LEMMA
        if roots_a[p - 1] is not None and roots_a[p - 1] == roots_b[q - 1]:
            return W_ROOT, ROOT_ONLY
        return None

    def tool_edge(p, q):
        return (W_TOOL, TOOL) if tok_a[p - 1] == tok_b[q - 1] else None

    return sorted(anchors + _assign(ca, cb, na, nb, content_edge, delta)
                  + _assign(fa, fb, na, nb, tool_edge, delta))


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
#  D4 — the coarse element
# ═══════════════════════════════════════════════════════════════════════════

def _features(raw: str) -> list[str]:
    return [t for t in raw.split("|") if t]


def _stem_label(tag: str, feats: Sequence[str]) -> str:
    """D4: the label of ONE stem segment — `V.<aspect>[.PASS]`, `N:<subcat>` | `N`,
    `P:<tag>`. No case, no mood, no person: those are what the element must not see."""
    if tag == "V":
        aspect = next((t for t in feats if t in _ASPECTS), None)
        if aspect is None:
            raise ValueError(f"V segment without an aspect (PERF/IMPF/IMPV): {feats!r}")
        return f"V.{aspect}.PASS" if "PASS" in feats else f"V.{aspect}"
    if tag == "N":
        for t in feats:
            if t in _N_POS_SET:
                return "N:" + t
        return "N"
    if tag == "P":
        first = feats[0] if feats else ""
        if not first or first.startswith(("ROOT:", "LEM:")):
            raise ValueError(f"P segment does not open with its particle tag: {feats!r}")
        return "P:" + first
    raise ValueError(f"unknown QAC tag {tag!r}")


def coarse_element(segments: Sequence[tuple[str, str]]) -> tuple[str, ...]:
    """D4: one word's element from its `(tag, features)` segments in file order —
    the tuple of its STEM segments' labels, prefix (`PREF`) and suffix (`SUFF`)
    segments dropped. A pronoun suffix, a clitic, a case ending or a mood never
    changes it. A word with no stem segment, or a segment the QAC vocabulary does
    not cover, is refused, not guessed (the corpus holds none)."""
    labels: list[str] = []
    for tag, raw in segments:
        feats = _features(raw)
        if "PREF" in feats or "SUFF" in feats:
            continue
        labels.append(_stem_label(tag, feats))
    if not labels:
        raise ValueError(f"a word with no stem segment: {list(segments)!r}")
    return tuple(labels)


def coarse_signature(words: Iterable[Sequence[tuple[str, str]]]) -> tuple[tuple[str, ...], ...]:
    """D4: a verse's signature — `coarse_element` of each word, in word order."""
    return tuple(coarse_element(w) for w in words)


# ═══════════════════════════════════════════════════════════════════════════
#  D4 — syn: Levenshtein over the coarse elements, blocks re-orderable
# ═══════════════════════════════════════════════════════════════════════════

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


def syn_seq(a: Sequence, b: Sequence) -> float:
    """D4: `1 − lev(A, B) / max(|A|, |B|)`, computed as `(M − lev) / M` so that the D5
    bounds (`count / M`) compare exactly in floating point. Symmetric, in [0, 1], 1
    when identical (two empty signatures included)."""
    longest = max(len(a), len(b))
    if longest == 0:
        return 1.0
    return (longest - levenshtein(a, b)) / longest


def block_reorder(seq_b: Sequence, edges: Iterable[Edge], n_a: int) -> tuple:
    """D4: B with its blocks concatenated in the order of their first partner in A.

    B's positions are cut into blocks: a block starts at a matched position whose
    partner in A is not the successor of the previous matched position's partner;
    an unmatched position stays with the block it follows (leading ones with the
    first block). With no edge, B itself. `n_a` is A's length; an edge off either
    sequence, or two edges on one position of EITHER sequence, is refused — a
    signature and the token sequence it was matched on must have one entry per
    QAC word, and the edges must be one-to-one (D2's are).
    """
    seq_b = tuple(seq_b)
    nb = len(seq_b)
    partner: dict[int, int] = {}
    seen_a: set[int] = set()
    for e in edges:
        if not (1 <= e.p <= n_a and 1 <= e.q <= nb):
            raise ValueError(f"edge {tuple(e)} off the sequences (|A| = {n_a}, |B| = {nb})")
        if e.q in partner:
            raise ValueError(f"two edges on B's position {e.q}")
        if e.p in seen_a:
            raise ValueError(f"two edges on A's position {e.p}")
        partner[e.q] = e.p
        seen_a.add(e.p)
    if not partner:
        return seq_b
    blocks: list[tuple[int, list[int]]] = []
    first: int | None = None
    current: list[int] = []
    prev: int | None = None
    for q in range(1, nb + 1):
        p = partner.get(q)
        if p is not None and prev is not None and p != prev + 1:
            blocks.append((first, current))
            first, current = None, []
        current.append(q)
        if p is not None:
            if first is None:
                first = p
            prev = p
    blocks.append((first, current))
    blocks.sort(key=lambda block: block[0])        # every block holds a matched position
    return tuple(seq_b[q - 1] for _, qs in blocks for q in qs)


def syn(a: Sequence, b: Sequence, edges: Iterable[Edge]) -> float:
    """D4: the best of three alignments — `syn_seq(A, B)`, `syn_seq(A, B′)`,
    `syn_seq(A′, B)` — where `B′` (`A′`) is B (A) with its blocks re-ordered along
    the D2 `edges` (`block_reorder`). Symmetric, in [0, 1], 1 for identical
    signatures and for a pure permutation of blocks, a substitution costs `1/n`,
    never below the plain Levenshtein (the first alignment).
    """
    edges = list(edges)
    plain = syn_seq(a, b)
    if not edges:
        return plain
    return max(plain, syn_seq(a, block_reorder(b, edges, len(a))),
               syn_seq(block_reorder(a, mirror(edges), len(b)), b))


def passes_syntax(value: float, sigma: float = SIGMA) -> bool:
    """The syntactic gate: `syn ≥ σ`, tolerant of the last bit."""
    return value >= sigma - SIGMA_EPS


# ═══════════════════════════════════════════════════════════════════════════
#  D5 — exact upper bounds of syn
# ═══════════════════════════════════════════════════════════════════════════

def _common(ca: Counter, cb: Counter) -> int:
    if len(ca) > len(cb):
        ca, cb = cb, ca
    return sum(min(n, cb[e]) for e, n in ca.items() if e in cb)


def syn_length_bound(la: int, lb: int) -> float:
    """D5: `m / M` — `syn`'s bound from the two word counts alone (`lev ≥ M − m`,
    whatever the order of the blocks)."""
    longest = max(la, lb)
    return 1.0 if longest == 0 else min(la, lb) / longest


def syn_bag_bound(bag_a: Counter, bag_b: Counter) -> float:
    """D5: `|bagA ∩ bagB| / M` over the coarse-element multisets — exact under any
    re-ordering (a re-ordering keeps the bag; an element outside the intersection
    costs at least one edit)."""
    la, lb = sum(bag_a.values()), sum(bag_b.values())
    longest = max(la, lb)
    return 1.0 if longest == 0 else _common(bag_a, bag_b) / longest


# ═══════════════════════════════════════════════════════════════════════════
#  D6 — the passage as the largest accepted order-free region
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
    """D6: the LARGEST ACCEPTED region, or None when no candidate is accepted.

    Over the identical-token edges (`lemma`, `tool`; `root` edges are gaps): a
    candidate is a window `[i1, i2]` of A bounded by matched positions with a window
    `[j1, j2]` of B bounded by matched positions, `k` counting the edges with both
    ends inside; it is accepted when `k ≥ L_MIN`, `k ≥ DENSITY × the longer window`
    and at least `CONTENT_MIN` kept edges are `lemma`. Among the accepted: the
    largest `k`, then the larger `2k − (spanA − k) − (spanB − k)`, then the smaller
    `i1`, then the smaller `i2`, then the smaller `j1` — read in A AS PASSED (the
    lower-surah verse). The order of the kept edges inside the windows is irrelevant.

    Enumeration: for each A window `[p_x, p_y]` (edges sorted by `p`), the window's
    partners sorted; every contiguous run holding both bounding edges is a B window —
    the tight candidates, which is exact (module docstring). Pruned exactly: a window
    pair that cannot reach `L_MIN` or the density is never scored.
    """
    ident = sorted(e for e in edges if e.kind in IDENTICAL_KINDS)
    n = len(ident)
    if n < L_MIN:
        return None
    best: Region | None = None
    best_key: tuple | None = None
    for x in range(n):
        by_q: list[tuple[int, int]] = []          # (q, index in ident) of the A window
        for y in range(x, n):
            insort(by_q, (ident[y].q, y))
            m = y - x + 1
            span_a = ident[y].p - ident[x].p + 1
            if m < L_MIN or m < DENSITY * span_a:      # k ≤ m: nothing here is accepted
                continue
            pref = [0]
            for _, idx in by_q:
                pref.append(pref[-1] + (ident[idx].kind == LEMMA))
            ranks = [t for t, (_, idx) in enumerate(by_q) if idx in (x, y)]
            lo, hi = ranks[0], ranks[-1]
            for l in range(lo + 1):
                for r in range(max(hi, l + L_MIN - 1), m):
                    k = r - l + 1
                    j1, j2 = by_q[l][0], by_q[r][0]
                    content = pref[r + 1] - pref[l]
                    if rejection(k, span_a, j2 - j1 + 1, content) is not None:
                        continue
                    score = 2 * k - (span_a - k) - (j2 - j1 + 1 - k)
                    key = (-k, -score, ident[x].p, ident[y].p, j1)
                    if best_key is None or key < best_key:
                        kept = tuple(sorted(ident[idx] for _, idx in by_q[l:r + 1]))
                        best = Region(k, ident[x].p, ident[y].p, j1, j2, kept, score, content)
                        best_key = key
    return best


# The passage build calls the region by this name (ties in A as passed — the only
# reading D6 keeps); the same function.
best_region_in_a = passage_region
