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
    `sem = (w_ce·ce + w_dense·dense) × (floor + (1 − floor)·lex)`; pairs that
    pass both rank by `score = sem × syn`. Between two VERBATIM-identical verses
    (equal `qac.ayah_words()` tuples) dense is ignored — `sem = ce × (…)` — and
    the candidate cap ranks them on `lex` alone (amendment of 2026-10-02).
  * D3 — the syntactic signature: one element per QAC word, since
    order-invariant-closeness version 2 the COARSE element of the core (its
    D4): the stem segments' labels only — `V.<aspect>[.PASS]`, `N:<subcat>` |
    `N`, `P:<tag>` — so a pronoun suffix, a clitic, a case ending or a mood
    never changes it. The treebank role was removed from the element before
    the first build (design.md, amendment of 2026-10-02); `qac_syntax.json` is
    not read.
  * D4 — tool words out of the root signal (`word_function.json` + the
    `SimilarVerses` stoplist).
  * D5 — `|Δayah| = 1` pairs are dropped before scoring.
  * D6 — cheap gates first: syntax on every pair, then dense/lex, then at most
    M pairs per verse go to the cross-encoder.
  * D8 — groups are the components of the mutual-neighbour graph above τ.
  * D10 — the file layout (schema 2 since order-invariant-closeness).

`openspec/changes/order-invariant-closeness` (version 2: D2, D4, D5, D8)
replaced the two order-dependent measures, and both now come from
`scripts/closeness_core.py`, imported, never copied:

  * `syn` — the Levenshtein similarity over the coarse signatures taken as the
    best of three alignments: as written, and each verse against the other
    with its blocks re-ordered along the pair's D2 matching (`block_reorder`),
    so a pure permutation of blocks scores 1 and a substitution costs `1/n`.
    The matching is therefore an INPUT of the syntactic gate: the syntax stage
    computes it (`syntax_similarity`) for every pair it scores, and the lexical
    signal reuses those edges. Candidate generation is unchanged (every
    non-consecutive pair of scored verses is examined); the core's EXACT
    bounds of `syn` (D5: length, coarse-element bag) only let the stage skip
    the matching of a pair that provably scores below σ — the survivors, their
    `syn` and their edges are what a full scoring gives, pinned by a test.
  * `lex` — the word-level IDF Jaccard of the order-invariant content-word
    matching (was `cov`, the IDF Jaccard of the two content-root SETS), ties
    broken by the median shift of the anchors (version 2 D2). A pair is stored
    only when its matched mass is positive (was «shares a content root»); the
    shared roots shown are the roots of the matched content words. The stored
    field is `lex`.

`openspec/changes/short-verse-material` (D1) adds one rule, the core's
`short_material_ok`: a pair whose SHORTER verse has at most
`SHORT_MATERIAL_MAX_LEN` (5) QAC words is stored only when its matching holds at
least `SHORT_MATERIAL_MIN_LEMMAS` (2) `lemma` edges — root-only edges do not
count. Applied after the semantic gate and before the matched-mass rule; a gold
row it drops reports the stage `short_material`. The header names both values.

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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator, NamedTuple, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))   # the shared closeness core, a sibling script

from arabic_text import normalize_search  # noqa: E402
from quran_data import loaders, paths  # noqa: E402
from retrieval.similar_verses import STOPWORDS, SimilarVerses  # noqa: E402
# σ, its gate, the syntactic measure and the lexical signal live in the shared
# core (order-invariant-closeness D8), not here.
import closeness_core as cc  # noqa: E402
from closeness_core import SIGMA, SIGMA_EPS, passes_syntax, syn  # noqa: E402,F401

# ── frozen parameters (design.md «Frozen parameters», task 1.4) ───────────
SCHEMA = loaders.SURAH_SIMILARITY_SCHEMA
K = 10
M = 30
W_CE = 0.7
W_DENSE = 0.3
FLOOR = 0.25
# SIGMA (= 2/3) and SIGMA_EPS: imported above from closeness_core, unchanged.
TAU_SEM = 0.125
TAU_GROUP = 0.4
# Task 3.6, as order-invariant-closeness D3 restates it: a neighbour is stored
# only when the content-word matching carries a positive mass (`Mw > 0`).
# Recorded in the header so the rule is visible; the gold positives it cannot
# reach (design D8 «Open point») are a reported result.
REQUIRE_SHARED_ROOT = True
# short-verse-material D1: a pair whose SHORTER verse has ≤ 5 QAC words is stored only
# when its matching holds ≥ 2 `lemma` edges — the core's frozen values and rule,
# applied after the semantic gate, before the matched-mass rule (`short_material`).
SHORT_MATERIAL_MAX_LEN = cc.SHORT_MATERIAL_MAX_LEN
SHORT_MATERIAL_MIN_LEMMAS = cc.SHORT_MATERIAL_MIN_LEMMAS
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
# Which element the signature uses, recorded in the header (and so in the
# checkpoint digest): a checkpoint computed under another element is stale.
# order-invariant-closeness D8: the element, the measure over it, the lexical
# signal and the matching's tie-break are the core's names.
SIGNATURE = cc.SIGNATURE
SIGNATURE_MEASURE = cc.SIGNATURE_MEASURE
LEXICAL = cc.LEXICAL
TIE_BREAK = cc.TIE_BREAK
# The source files a checkpoint was computed BY: this builder, the core it
# imports the definitions from, and the passage build whose `word_of` gives the
# lexical tokens. Imported code changes a checkpoint as surely as this file does.
CHECKPOINT_SOURCES = (Path(__file__).resolve(), ROOT / "scripts" / "closeness_core.py",
                      ROOT / "scripts" / "build_quran_passages.py")
# Amendment of 2026-10-02 (design.md): dense is not a signal between two verses
# whose Arabic is verbatim identical. The E5 passage embeds the FR/EN
# translations beside the Arabic, so whatever dense measures between identical
# Arabic texts is translation variance, not the verses. Recorded in the header.
DENSE_ON_VERBATIM = "ignored"

# The noun subcategories that ARE a part of speech in the coarse element: the
# core's list (version 2 D4 is the core's definition), named here for readers.
N_POS = cc.N_POS

Signature = tuple  # one coarse element (a tuple of stem labels) per QAC word


# ═══════════════════════════════════════════════════════════════════════════
#  Pure functions — importable by tests, no disk, no model
# ═══════════════════════════════════════════════════════════════════════════

def build_signatures(records: Iterable) -> dict[tuple[int, int], Signature]:
    """D3 / version 2 D4: `{(surah, ayah): (coarse element, …)}` over every word QAC
    records, through `closeness_core.coarse_signature`.

    `records` yields `quran_data.qac.Record`s (file order).
    """
    words: dict[tuple[int, int], dict[int, list[tuple[str, str]]]] = defaultdict(dict)
    for rec in records:
        words[(rec.surah, rec.ayah)].setdefault(rec.word, []).append((rec.tag, rec.features))
    out: dict[tuple[int, int], Signature] = {}
    for (s, a), by_word in words.items():
        out[(s, a)] = cc.coarse_signature(by_word[w] for w in sorted(by_word))
    return out


class VerseWords(NamedTuple):
    """One verse's words as the lexical signal reads them, one entry per QAC word:
    its token (`build_quran_passages.word_of`), its resolved primary root (None for
    a rootless word) and its D1 content flag (`closeness_core.content_words`)."""

    tokens: tuple
    roots: tuple
    content: tuple


class Lexical(NamedTuple):
    """`lex`, the matched mass `Mw` it is built on, and the shared roots shown."""

    lex: float
    mass: float
    roots: list


def pair_edges(va: VerseWords, vb: VerseWords) -> list:
    """order-invariant-closeness D2, through the core: the order-invariant matching of
    ALL words of the two verses (`lemma` / `root` / `tool` edges, median-shift
    tie-break). The one input both gates read: `syn` re-orders blocks along it,
    `lex` sums its content edges."""
    return cc.match_all(va.tokens, vb.tokens, va.roots, vb.roots, va.content, vb.content)


def lexical(va: VerseWords, vb: VerseWords, idf: dict[str, float],
            edges: Sequence | None = None) -> Lexical:
    """order-invariant-closeness D3, through the core: the word-level IDF Jaccard
    `lex` of the two verses' matching (`pair_edges`, or the `edges` already computed
    for the pair), its matched mass, and the roots of its content edges. Symmetric
    in (A, B)."""
    edges = pair_edges(va, vb) if edges is None else edges
    return Lexical(cc.lex(edges, va.roots, vb.roots, va.content, vb.content, idf),
                   cc.matched_mass(edges, va.roots, vb.roots, idf),
                   cc.shared_roots(edges, va.roots, vb.roots))


def short_material(va: VerseWords, vb: VerseWords, edges: Sequence) -> bool:
    """short-verse-material D1, through the core: `short_material_ok` over the pair's
    D2 `edges`, `n` read from the two verses' QAC word counts."""
    return cc.short_material_ok(edges, len(va.tokens), len(vb.tokens))


class Syntax(NamedTuple):
    """A pair's `syn` and the D2 edges it was re-ordered along (which `lexical` reuses)."""

    syn: float
    edges: list


def syntax_similarity(sig_a: Signature, sig_b: Signature, va: VerseWords,
                      vb: VerseWords) -> Syntax:
    """Version 2 D4, through the core: the pair's matching (D2) and `syn` over the two
    coarse signatures with the blocks re-orderable along it."""
    edges = pair_edges(va, vb)
    return Syntax(syn(sig_a, sig_b, edges), edges)


def prefilter_stage(a: Signature, b: Signature, bag_a: Counter | None = None,
                    bag_b: Counter | None = None) -> str | None:
    """Version 2 D5: the exact bound that proves `syn(a, b) < σ` whatever the
    re-ordering — `length_window` (`m / M`), `bag_bound` (`|bagA ∩ bagB| / M` over
    the coarse elements) — or None when the pair must be scored in full.

    The scalar reference of the cross build's vectorised pre-filters, and the
    shortcut of the intra stage. `bag_a` / `bag_b` are the signatures' Counters
    when the caller holds them already.
    """
    if not passes_syntax(cc.syn_length_bound(len(a), len(b))):
        return "length_window"
    bag_a = Counter(a) if bag_a is None else bag_a
    bag_b = Counter(b) if bag_b is None else bag_b
    if not passes_syntax(cc.syn_bag_bound(bag_a, bag_b)):
        return "bag_bound"
    return None


def sem_score(ce: float, dense: float | None, lex: float) -> float:
    """D2: `(w_ce·ce + w_dense·dense) × (floor + (1 − floor)·lex)`.

    `dense=None` means dense is ignored (a verbatim pair): the base is `ce` alone.
    """
    base = ce if dense is None else W_CE * ce + W_DENSE * dense
    return base * (FLOOR + (1 - FLOOR) * lex)


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
    """D6 step 4: per verse, keep at most `m` survivors by `max(dense rank, lex rank)`.

    `survivors` maps `(a, b)` to `(dense, lex)`. A pair is kept when EITHER of
    its verses keeps it. Ranks are 1-based, best first; ties in a verse's
    ordering break on `min` of the two ranks, then the partner's ayah. A pair
    whose dense is `None` (verbatim: dense ignored) ranks on its lex rank alone.
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
            d_rank = lambda p: by_d.get(p, by_c[p])  # noqa: E731 — dense ignored: lex alone
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


def load_signatures() -> dict[tuple[int, int], Signature]:
    return build_signatures(_qac_records())


def verse_words(refs: Sequence[tuple[int, int]], tokens: Sequence, roots: Sequence,
                content_sets: dict[tuple[int, int], frozenset],
                tools) -> dict[tuple[int, int], VerseWords]:
    """`{(surah, ayah): VerseWords}` — per verse its tokens and resolved roots (as the
    passage build's `Corpus` gives them, index-aligned with `refs`) and the D1 content
    flags, judged against that verse's content roots (`content_root_sets`)."""
    out: dict[tuple[int, int], VerseWords] = {}
    for ref, tok, rts in zip(refs, tokens, roots):
        out[ref] = VerseWords(tuple(tok), tuple(rts), cc.content_words(
            rts, content_sets.get(ref, frozenset()), ref[0], ref[1], tools))
    return out


def load_verse_words(content_sets: dict[tuple[int, int], frozenset]
                     ) -> dict[tuple[int, int], VerseWords]:
    """Every verse's `VerseWords`, read through `quran_data` (QAC + roots_resolved +
    word_function). The tokens come from the passage build's `Corpus` — the one token
    rule, imported (lazily: that build may import this one)."""
    import build_quran_passages as passages_build

    corpus = passages_build.Corpus(_qac_records())
    return verse_words(corpus.refs, corpus.seqs, corpus.roots, content_sets,
                       loaders.word_function())


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
        "signature_measure": SIGNATURE_MEASURE,
        "lexical": LEXICAL,
        "tie_break": TIE_BREAK,
        "dense_on_verbatim": DENSE_ON_VERBATIM,
        "require_shared_root": REQUIRE_SHARED_ROOT,
        "short_material_max_len": SHORT_MATERIAL_MAX_LEN,
        "short_material_min_lemmas": SHORT_MATERIAL_MIN_LEMMAS,
        "gold_sha256": gold_sha,
    }


def params_digest(head: dict) -> str:
    return hashlib.sha256(json.dumps(head, sort_keys=True).encode()).hexdigest()


# A built header may differ from what this code writes on these keys without being
# another build's file: the digests name the gold / blind files' bytes AT BUILD TIME
# (the tests check them against the files as they are now), and the embedder is
# read from the environment. `blind_short_sha256` is the cross builds' digest of the
# short-verse-material blind sample (short-verse-material D2).
RUNTIME_HEADER_KEYS = frozenset({"gold_sha256", "blind_sample_sha256", "blind_short_sha256",
                                 "embedder"})


def header_drift(built: dict, code: dict) -> list[str]:
    """The keys of `code` — a header as this code writes it — on which `built`, a
    file's header, differs, `RUNTIME_HEADER_KEYS` aside: empty exactly when the file
    was built under this code's parameters AND definitions. A key the file lacks is
    drift (version 1's header names no `tie_break`); listed in `code`'s key order.

    The loaders refuse a file by its SCHEMA only, and version 2 kept version 1's
    schema (order-invariant-closeness D8): a file built under the other definition
    is served exactly like this build's, so this comparison is the one place the
    drift can show. Pure. The test suite reads it in two halves — see
    `definition_drift`. The cross build's header is checked through it too.
    """
    return [k for k in code if k not in RUNTIME_HEADER_KEYS and built.get(k) != code[k]]


# The keys that NAME the definition a file was computed under (D8: `signature`,
# `signature_measure`, `lexical`, `tie_break`, `passage`, «as applicable»). Version 2
# kept version 1's schema, so these names are the version marker a schema bump would
# have been: a file whose names differ is ANOTHER VERSION's file, which the dataset
# tests skip over exactly as they skip a file at another schema — naming the rebuild,
# so a definition can be developed with a green suite before its rebuild — while a
# file naming THIS definition with another frozen value FAILS them (a frozen value is
# never changed, D9).
DEFINITION_HEADER_KEYS = frozenset({"signature", "signature_measure", "lexical", "tie_break",
                                    "passage"})


def definition_drift(built: dict, code: dict) -> list[str]:
    """The keys of `header_drift(built, code)`, in its order, that make the file
    another version's: a `DEFINITION_HEADER_KEYS` name that differs, or ANY key this
    code writes that the file lacks altogether — it was built before that key (and the
    rule it names) existed, as a file predating `short_material_*`
    (short-verse-material) is. A key the file carries with another value is not
    listed here: that is a changed frozen value, for `header_drift` to fail on. Pure."""
    return [k for k in header_drift(built, code)
            if k in DEFINITION_HEADER_KEYS or k not in built]


def inputs_digest(vectors: dict) -> str:
    """sha256 over everything a checkpoint depends on that the header does not name.

    The sources of `CHECKPOINT_SOURCES` (this file and the definitions it
    imports), the derived inputs of `CHECKPOINT_INPUTS`, the `SimilarVerses`
    stoplist and the verse vectors (rounded, so a reload of the same collection
    hashes the same). Other imported code (the retrieval stack) is not covered:
    after changing it, rebuild with `--fresh`.
    """
    import numpy as np

    h = hashlib.sha256()
    for src in CHECKPOINT_SOURCES:
        h.update(src.name.encode())
        h.update(src.read_bytes())
    for name in CHECKPOINT_INPUTS:
        f = getattr(paths, name)
        h.update(name.encode())
        h.update(f.read_bytes() if f.exists() else b"<absent>")
    h.update(json.dumps(sorted(STOPWORDS), ensure_ascii=False).encode())
    for key in sorted(vectors):
        h.update(f"{key[0]}:{key[1]}".encode())
        h.update(np.round(np.asarray(vectors[key], dtype="float64"), 6).tobytes())
    return h.hexdigest()


def syntax_survivors(surah: int, ayahs: list[int], scored: set[int], sigs: dict,
                     words: dict) -> tuple[dict[tuple[int, int], Syntax], int]:
    """D6 steps 1-2: `{(a, b): Syntax}` passing the gate, and the pairs examined.

    Every non-consecutive pair of scored verses is examined (candidate generation
    is unchanged). The version 2 `syn` needs the pair's D2 matching, computed
    here from `words` (`VerseWords` per verse) — except for a pair the core's
    exact bounds (D5, `prefilter_stage`) prove below σ under ANY re-ordering,
    whose matching is skipped: the result is the one a full scoring gives.
    """
    out: dict[tuple[int, int], Syntax] = {}
    examined = 0
    mine = [x for x in ayahs if x in scored]
    bags = {a: Counter(sigs[(surah, a)]) for a in mine}
    for a, b in candidate_pairs(mine):
        examined += 1
        sig_a, sig_b = sigs[(surah, a)], sigs[(surah, b)]
        if prefilter_stage(sig_a, sig_b, bags[a], bags[b]) is not None:
            continue
        got = syntax_similarity(sig_a, sig_b, words[(surah, a)], words[(surah, b)])
        if passes_syntax(got.syn):
            out[(a, b)] = got
    return out, examined


def build_surah(surah: int, ayahs: list[int], ctx: dict, gold: list[dict]) -> dict:
    """One surah's entry plus the gold diagnostics that fall in it."""
    import numpy as np

    sigs, roots, idf, lw = ctx["signatures"], ctx["roots"], ctx["idf"], ctx["lexical"]
    unscored = [a for a in ayahs if not roots.get((surah, a))]
    scored_set = {a for a in ayahs if roots.get((surah, a))}
    survivors, examined = syntax_survivors(surah, ayahs, scored_set, sigs, lw)

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
    # the lexical signal over the matching the syntax stage already computed
    lex_of = {p: lexical(lw[(surah, p[0])], lw[(surah, p[1])], idf, sy.edges)
              for p, sy in survivors.items()}
    signals = {p: (eff_dense[p], lex_of[p].lex) for p in survivors}
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
        dense, lex = signals[p]
        sem = sem_score(ce_of[p], dense, lex)
        if sem < TAU_SEM:
            continue
        # short-verse-material D1: after the semantic gate, before the matched mass
        if not short_material(lw[(surah, p[0])], lw[(surah, p[1])], survivors[p].edges):
            continue
        if REQUIRE_SHARED_ROOT and not lex_of[p].mass > 0:
            continue
        sy = survivors[p].syn
        # `dense` stays the measured value; `verbatim` says it did not enter `sem`
        stored_pairs[p] = {"s": rnd(sem * sy), "sem": rnd(sem), "syn": rnd(sy), "ce": rnd(ce_of[p]),
                           "dense": rnd(dense_of[p]), "lex": rnd(lex), "roots": lex_of[p].roots}
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
            # scored in full, whatever the bounds said: a gold row reports the value
            syx = syntax_similarity(sigs[(surah, p[0])], sigs[(surah, p[1])],
                                    lw[(surah, p[0])], lw[(surah, p[1])])
            sy = syx.syn
            lx = lex_of.get(p) or lexical(lw[(surah, p[0])], lw[(surah, p[1])], idf, syx.edges)
            dense, ce = dense_of[p], ce_of.get(p)
            sem = sem_score(ce, eff_dense[p], lx.lex) if ce is not None else None
            row.update({"syn": rnd(sy), "dense": rnd(dense), "lex": rnd(lx.lex),
                        "verbatim": p in verbatim,
                        "ce": None if ce is None else rnd(ce), "sem": None if sem is None else rnd(sem)})
            if not passes_syntax(sy):
                row["stage"] = "syntax_gate"
            elif p not in kept:
                row["stage"] = "candidate_cap"
            elif sem < TAU_SEM:
                row["stage"] = "semantic_gate"
            elif not short_material(lw[(surah, p[0])], lw[(surah, p[1])], syx.edges):
                row["stage"] = "short_material"
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
    words = load_verse_words(roots)
    ayahs_by_surah = surah_ayahs()
    total_ex = total_sv = total_unscored = 0
    for s, ayahs in ayahs_by_surah.items():
        if only and s not in only:
            continue
        scored = {a for a in ayahs if roots.get((s, a))}
        survivors, examined = syntax_survivors(s, ayahs, scored, sigs, words)
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
            sy = syntax_similarity(sigs[(g["surah"], g["a"])], sigs[(g["surah"], g["b"])],
                                   words[(g["surah"], g["a"])], words[(g["surah"], g["b"])]).syn
            by_label[g["label"]][0] += passes_syntax(sy)
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
        ctx["lexical"] = load_verse_words(ctx["roots"])
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
