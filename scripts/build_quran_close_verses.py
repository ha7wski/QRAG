#!/usr/bin/env python3
"""
build_quran_close_verses.py — the offline «close verses» build.

Composes the two cross-surah relations into ONE and writes it to
`data/derived/quran_close_verses.json`, which `GET /quran-similarity/*` and
`GET /surah/{number}/annotations` serve without loading any model. The design
is `openspec/changes/unify-close-verses/design.md`, its common part replaced by
`openspec/changes/order-invariant-common-words/design.md`; every value below was
frozen there before this build ran on the corpus — decisions to record there,
never tuning knobs:

  * D1 — the pair set is the UNION `S ∪ W` of the pairs `quran_similarity.json`
    stores in either verse's list (S) and the passages `quran_passages.json`
    holds (W). Each pair records which input holds it (`from`). Neither input is
    rebuilt or filtered here.
  * D2 — `sim = sem × syn`. For a pair of S: its stored `s`, READ (the higher of
    the two sides should they ever disagree). For a pair of W \\ S: computed by
    the similarity build's own functions, IMPORTED, with NO gate — `dense` is the
    cosine's percentile among the re-derived syntax survivors, ignored between
    verbatim verses, and these pairs are cross-encoded in a call of their own.
    The integrity check recomputes `dense` for every pair of S and refuses to
    write when it differs from the stored value at 4 decimals.
  * D3 — `pas = k / min(n_a, n_b)` for a pair of W (`n` = the passage build's
    QAC word count), 0 for any other pair.
  * D4 — `score = 1 − (1 − sim)(1 − pas)`, rounded to 4 decimals.
  * D5 — the common part (order-invariant-common-words D1–D5), computed the
    same way for EVERY pair, passage or not. Display only: it never changes the
    pair set, `sim`, `pas` or `score`.
      - content word: the passage build's `content` flag (the word carries a
        root) AND its `s:a:w` is not a grammatical tool in `word_function.json`;
      - the matching: a maximum-weight one-to-one matching of the two verses'
        content words (`scipy.optimize.linear_sum_assignment`, maximize), edge
        weight `W_LEMMA` for the same passage-build token, `W_ROOT` for the same
        resolved primary root under another token, no edge otherwise, each
        minus `TIE_BREAK × |p/n_a − q/n_b|` (relative place, n = QAC word
        count), so order only ever breaks an exact tie; edges of weight > 0 kept;
      - bridged function words: the unmatched words strictly between two
        matched pairs `(p, q) < (p', q')` that run in the same order on both
        sides with no matched pair between them on both sides at once, when
        the two sequences of unmatched in-between tokens are identical —
        coloured, never counted;
      - a common part needs ≥ `MARK_MIN` matched words.
    Stored as `m` (`[[p, q, "lemma"|"root"]]`, sorted by `p`, `p` in the
    lower-surah verse) and, per verse, `ca` / `cb`: one half-open character
    span per RUN of consecutive coloured words, in the DISPLAYED
    `text_ar_tashkil` (Basmala stripped). The passage's own `k` / `wa` / `wb`
    stay on passage pairs only — `pas` reads `k` — and are not the display.
  * D6 — the file layout, schema 2, byte-identical across builds.

order-invariant-common-words D3 was AMENDED during implementation (design.md
D3, spec «Every pair carries its common part»): its first wording («consecutive
among A's matched words and among B's») could not produce its own outcome — the
«مِنْ» of 28:20 / 36:20 coloured, one run per verse — because the displaced
«رَجُل» is matched between «مِنْ»'s neighbours on one side. The bridge therefore
skips matched words when it compares the in-between sequences, and asks only
that no matched pair sits between the two on BOTH sides. It colours everything
the first wording did; on today's 2 403 common parts it adds bridged words to 65
(one to three function words each, identical on both sides: «مِن», «ما», «عَلَى»,
«لا»…), e.g. «وَمِمَّا» of 2:3 with «مِمَّا» of 14:31.

Two points unify-close-verses D2/D4 leave open, settled here and recorded in the header:

  * `score` is computed from the UNROUNDED `sim` and `pas`, then rounded; `sim`
    and `pas` are stored rounded too. So `score` may differ in its last digit
    from the formula applied to the two stored values. For a pair of S `sim` is
    the stored (already rounded) `s`, so `pas = 0` gives `score = sim` exactly.
  * The models named in the header are the ones this build loads; the build
    refuses when the similarity dataset names other ones, since its stored `s`
    and the ungated `sim` would then sit on two scales.

Needs the backend STOPPED (the verse vectors come out of the embedded Qdrant,
which takes an exclusive lock) and loads the cross-encoder (~1.1 GB). No
checkpoint: one cross-encoder call. Build order:
`build_quran_similarity.py` → `build_quran_passages.py` → this script.

    python scripts/build_quran_close_verses.py              # full build
    python scripts/build_quran_close_verses.py --no-gold    # without the local-only gold sets
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# The two builders are sibling scripts, not package modules: `scripts/` sits
# outside the layered packages, so importing them breaks no direction rule.
sys.path.insert(0, str(ROOT / "scripts"))

from quran_data import loaders, paths  # noqa: E402

import build_quran_passages as passages_build  # noqa: E402
import build_quran_similarity as similarity_build  # noqa: E402
from build_quran_similarity import (  # noqa: E402 — D2: the definition, imported
    RERANKER_MODEL, CrossEncoderScorer, dense_stage, load_vectors, qdrant_lock_held, rnd,
    sem_score, syn_similarity, syntax_stage,
)

SCHEMA = loaders.QURAN_CLOSE_VERSES_SCHEMA
SCOPE = "cross-surah"
# Frozen in openspec/changes/order-invariant-common-words/design.md (D2, D4).
MARK_MIN = 2
W_LEMMA, W_ROOT = 1.0, 0.5
TIE_BREAK = 1e-3
LEMMA, ROOT_ONLY = "lemma", "root"
FROM_SIMILARITY, FROM_PASSAGE = "similarity", "passage"
REBUILD = "python scripts/build_quran_close_verses.py"
BUILD_ORDER = (f"{similarity_build.REBUILD}  →  {passages_build.REBUILD}  →  {REBUILD}"
               f"  (backend stopped)")
SCORE_RULE = ("1 - (1 - sim)(1 - pas), computed from the unrounded sim and pas, "
              "rounded to 4 decimals")
SIM_RULE = ("sem x syn: the stored s for a pair quran_similarity.json stores (the higher "
            "side); otherwise the similarity build's functions with no gate, dense = the "
            "cosine's percentile among the syntax survivors, ignored between verbatim verses")
PAS_RULE = ("k / min(n_a, n_b) for a pair quran_passages.json holds, n = QAC word count; "
            "0 otherwise")
MARK_RULE = ("the order-invariant matching of the two verses' content words when it joins "
             ">= mark_min words, for every pair (passage or not): m = [[p, q, lemma|root]] "
             "sorted by p, and per verse one half-open character span per run of "
             "consecutive coloured words (matched or bridged) in the displayed "
             "text_ar_tashkil, Basmala stripped; display only, never in sim, pas or score")
CONTENT_WORD_RULE = ("the word carries a root (the passage build's content flag) and its "
                     "s:a:w is not a grammatical tool in word_function.json")
MATCHING_RULE = ("maximum-weight one-to-one matching (scipy linear_sum_assignment, maximize) "
                 "of content words: weight 1 for the same passage-build lemma token, 0.5 for "
                 "the same resolved primary root under another token, no edge otherwise; "
                 "edges of weight > 0 kept")
TIE_RULE = ("every weight minus tie_break x |p/n_a - q/n_b|, p and q 1-based, n = QAC word "
            "count: among equal partners the nearest relative place wins")
BRIDGE_RULE = ("the unmatched words strictly between two matched pairs (p, q) < (p', q') in "
               "the same order on both sides, with no matched pair (r, s) such that "
               "p < r < p' and q < s < q', are coloured on both sides when their token "
               "sequences are identical; bridged words are not counted; matched words between "
               "them on one side only are skipped (D3 as amended)")


class StaleInput(Exception):
    """An input the build composes disagrees with what it recomputes — write nothing."""


# ═══════════════════════════════════════════════════════════════════════════
#  Pure functions — importable by tests, no disk, no model
# ═══════════════════════════════════════════════════════════════════════════

def parse_ref(raw: str) -> tuple[int, int]:
    s, a = raw.split(":")
    return int(s), int(a)


def ref_str(ref: tuple[int, int]) -> str:
    return f"{ref[0]}:{ref[1]}"


def pair_key(x: str, y: str) -> tuple[str, str]:
    """The unordered pair as `(a, b)`, `a` the lower `(surah, ayah)`."""
    return (x, y) if parse_ref(x) <= parse_ref(y) else (y, x)


def _order(key: tuple[str, str]) -> tuple[tuple[int, int], tuple[int, int]]:
    return parse_ref(key[0]), parse_ref(key[1])


def similarity_pairs(sim_data: dict) -> dict[tuple[str, str], dict]:
    """S: `{(a, b): stored entry}` over both verses' lists, the higher `s` kept (D2)."""
    out: dict[tuple[str, str], dict] = {}
    for ref, lst in sim_data["neighbours"].items():
        for e in lst:
            key = pair_key(ref, e["r"])
            if key[0] == key[1] or parse_ref(key[0])[0] == parse_ref(key[1])[0]:
                raise StaleInput(f"quran_similarity.json lists {ref} with {e['r']}, "
                                 f"which are not a cross-surah pair")
            if key not in out or e["s"] > out[key]["s"]:
                out[key] = e
    return out


def passage_pairs(pas_data: dict) -> dict[tuple[str, str], dict]:
    """W: `{(a, b): passage}`; a passage stored with `a` in the higher surah is refused."""
    out: dict[tuple[str, str], dict] = {}
    for p in pas_data["passages"]:
        key = pair_key(p["a"], p["b"])
        if key != (p["a"], p["b"]) or parse_ref(p["a"])[0] == parse_ref(p["b"])[0]:
            raise StaleInput(f"quran_passages.json stores {p['a']} / {p['b']}, which is not "
                             f"a cross-surah pair with `a` in the lower surah")
        out[key] = p
    return out


def union_pairs(s_keys, w_keys) -> dict[tuple[str, str], list[str]]:
    """D1: `{(a, b): from}` over `S ∪ W`, sorted by `(a, b)` numerically."""
    s_set, w_set = set(s_keys), set(w_keys)
    out = {}
    for key in sorted(s_set | w_set, key=_order):
        out[key] = ([FROM_SIMILARITY] if key in s_set else []) + \
                   ([FROM_PASSAGE] if key in w_set else [])
    return out


def pas_of(k: int, n_a: int, n_b: int) -> float:
    """D3: the share of the shorter verse the passage covers."""
    return k / min(n_a, n_b)


def combined_score(sim: float, pas: float) -> float:
    """D4: `1 − (1 − sim)(1 − pas)`, UNROUNDED (the caller rounds once)."""
    return 1.0 - (1.0 - sim) * (1.0 - pas)


def ungated_sim(ce: float, dense: float, cov: float, syn: float, verbatim: bool) -> float:
    """D2 for a pair of W \\ S: `sem × syn` with no gate; dense ignored between verbatim verses."""
    return sem_score(ce, None if verbatim else dense, cov) * syn


def content_flags(content: Sequence[bool], surah: int, ayah: int,
                  tools) -> tuple[bool, ...]:
    """D1: carries a root AND is not a grammatical-tool occurrence (`word_function.json`)."""
    return tuple(bool(c) and f"{surah}:{ayah}:{w}" not in tools
                 for w, c in enumerate(content, start=1))


def match_words(tok_a: Sequence, tok_b: Sequence, roots_a: Sequence, roots_b: Sequence,
                content_a: Sequence[bool], content_b: Sequence[bool]
                ) -> list[tuple[int, int, str]]:
    """D2: the order-invariant matching, `[(p, q, "lemma"|"root")]` sorted by `p`.

    Positions are 1-based QAC word numbers. Same token → `W_LEMMA`; another token
    under the same (non-null) resolved root → `W_ROOT`; else no edge. Every edge
    loses `TIE_BREAK × |p/n_a − q/n_b|`, which is below half the smallest weight
    gap, so it never trades a heavier matching for a better-placed one.
    """
    ia = [p for p in range(1, len(tok_a) + 1) if content_a[p - 1]]
    ib = [q for q in range(1, len(tok_b) + 1) if content_b[q - 1]]
    if not ia or not ib:
        return []
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    na, nb = len(tok_a), len(tok_b)
    weight = np.zeros((len(ia), len(ib)))
    kind: dict[tuple[int, int], str] = {}
    for x, p in enumerate(ia):
        for y, q in enumerate(ib):
            if tok_a[p - 1] == tok_b[q - 1]:
                w, k = W_LEMMA, LEMMA
            elif roots_a[p - 1] is not None and roots_a[p - 1] == roots_b[q - 1]:
                w, k = W_ROOT, ROOT_ONLY
            else:
                continue
            weight[x, y] = w - TIE_BREAK * abs(p / na - q / nb)
            kind[(x, y)] = k
    rows, cols = linear_sum_assignment(weight, maximize=True)
    return sorted((ia[x], ib[y], kind[(x, y)]) for x, y in zip(rows.tolist(), cols.tolist())
                  if weight[x, y] > 0)


def bridge_words(m: Sequence, tok_a: Sequence, tok_b: Sequence) -> tuple[set[int], set[int]]:
    """D3: the function words coloured between matched words, `(words of a, words of b)`.

    For two matched pairs `(p, q)`, `(p', q')` with `p < p'` and `q < q'` and no
    matched pair `(r, s)` such that `p < r < p'` AND `q < s < q'`, the UNMATCHED
    words strictly between them are coloured on both sides when their token
    sequences are identical (and not empty).
    """
    pairs = sorted((p, q) for p, q, *_ in m)
    used_a, used_b = {p for p, _ in pairs}, {q for _, q in pairs}
    out_a: set[int] = set()
    out_b: set[int] = set()
    for x, (p, q) in enumerate(pairs):
        for p2, q2 in pairs[x + 1:]:
            if q2 <= q or any(p < r < p2 and q < t < q2 for r, t in pairs):
                continue
            ua = [w for w in range(p + 1, p2) if w not in used_a]
            ub = [w for w in range(q + 1, q2) if w not in used_b]
            if ua and [tok_a[w - 1] for w in ua] == [tok_b[w - 1] for w in ub]:
                out_a.update(ua)
                out_b.update(ub)
    return out_a, out_b


def coloured_runs(words) -> list[list[int]]:
    """`[[first, last], …]` of the runs of consecutive word numbers, ascending."""
    runs: list[list[int]] = []
    for w in sorted(words):
        if runs and w == runs[-1][1] + 1:
            runs[-1][1] = w
        else:
            runs.append([w, w])
    return runs


def common_part(tok_a: Sequence, tok_b: Sequence, roots_a: Sequence, roots_b: Sequence,
                content_a: Sequence[bool], content_b: Sequence[bool]) -> dict | None:
    """D2–D4: `{m, runs_a, runs_b}` when ≥ `MARK_MIN` words match, else None."""
    m = match_words(tok_a, tok_b, roots_a, roots_b, content_a, content_b)
    if len(m) < MARK_MIN:
        return None
    br_a, br_b = bridge_words(m, tok_a, tok_b)
    return {"m": m,
            "runs_a": coloured_runs({p for p, _, _ in m} | br_a),
            "runs_b": coloured_runs({q for _, q, _ in m} | br_b)}


def char_span(word_index: dict, raw: str, shown: str, surah: int, ayah: int,
              words: Sequence[int]) -> list[int]:
    """The half-open `[start, end)` of words `words[0]..words[1]` in the DISPLAYED text.

    `word_index`'s `chakl_char_start` / `chakl_char_end` address the RAW chakl row,
    Basmala included; `shown` is that row through `strip_leading_basmala`, so both
    offsets move back by exactly what the strip removed. Raises `StaleInput` when
    a word is missing or the span leaves the displayed text — the build fails.
    """
    if not shown or not raw.endswith(shown):
        raise StaleInput(f"{surah}:{ayah}: the displayed text is not a suffix of its chakl row")
    shift = len(raw) - len(shown)
    try:
        first = word_index[f"{surah}:{ayah}:{words[0]}"]
        last = word_index[f"{surah}:{ayah}:{words[1]}"]
        start = first["chakl_char_start"] - shift
        end = last["chakl_char_end"] - shift
    except (KeyError, TypeError, IndexError) as exc:
        raise StaleInput(f"{surah}:{ayah}: words {list(words)} are not in word_index.json "
                         f"({type(exc).__name__}: {exc})") from exc
    if not 0 <= start < end <= len(shown):
        raise StaleInput(f"span [{start}, {end}) of {surah}:{ayah} lies outside its "
                         f"{len(shown)}-character displayed text")
    return [start, end]


def run_char_spans(word_index: dict, raw: str, shown: str, surah: int, ayah: int,
                   runs: Sequence[Sequence[int]]) -> list[list[int]]:
    """D5: one half-open character span per run, through `char_span` (its rebase and checks)."""
    spans = [char_span(word_index, raw, shown, surah, ayah, run) for run in runs]
    if any(e1 > s2 for (_, e1), (s2, _) in zip(spans, spans[1:])):
        raise StaleInput(f"{surah}:{ayah}: the spans {spans} overlap or are out of order")
    return spans


def dense_mismatches(stored: dict[tuple[str, str], dict],
                     dense_of: dict[tuple[str, str], float]) -> list[str]:
    """D2's integrity check: the S pairs whose recomputed dense ≠ the stored one (4 decimals)."""
    bad = []
    for key in sorted(stored, key=_order):
        got = dense_of.get(key)
        if got is None or rnd(got) != stored[key]["dense"]:
            bad.append(f"{key[0]}/{key[1]}: stored {stored[key]['dense']}, "
                       f"recomputed {None if got is None else rnd(got)}")
    return bad


def unscored_of(sim_unscored: Sequence[str], pairs: Sequence[dict]) -> list[str]:
    """The similarity dataset's unscored verses minus any verse holding a pair (D6)."""
    held = {p["a"] for p in pairs} | {p["b"] for p in pairs}
    return [r for r in sim_unscored if r not in held]


def pair_record(key: tuple[str, str], frm: list[str], sim: float, pas: float,
                roots: Sequence[str], passage: dict | None, part: dict | None,
                ca: list | None = None, cb: list | None = None) -> dict:
    """One stored pair, in the D6 key order.

    `k` / `wa` / `wb` come from `passage` (a passage pair), `m` / `ca` / `cb` from
    `part` and its spans — each group together or not at all.
    """
    rec = {"a": key[0], "b": key[1], "score": rnd(combined_score(sim, pas)),
           "sim": rnd(sim), "pas": rnd(pas), "from": list(frm), "roots": list(roots)}
    if passage is not None:
        rec.update({"k": passage["k"], "wa": list(passage["wa"]), "wb": list(passage["wb"])})
    if part is not None:
        rec.update({"m": [[p, q, k] for p, q, k in part["m"]],
                    "ca": [list(x) for x in ca], "cb": [list(x) for x in cb]})
    return rec


def dataset(pairs: list[dict], unscored: list[str], head: dict) -> dict:
    return {"schema": SCHEMA, "build": head, "unscored": unscored, "pairs": pairs}


def dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=False, separators=(",", ":"))


# ═══════════════════════════════════════════════════════════════════════════
#  The composition — every input injected, so tests run it on fixtures
# ═══════════════════════════════════════════════════════════════════════════

def compose(sim_data: dict, pas_data: dict, sc, pc, survivors: dict[tuple[int, int], float],
            vectors: dict, scorer, texts: Sequence[str], word_index: dict,
            displayed: Callable[[int, int], tuple[str, str]], *, tools
            ) -> tuple[list[dict], list[str], dict]:
    """`(pairs, unscored, stats)` — raises `StaleInput` before anything is written.

    `sc` is the similarity build's `Corpus` (refs, index, seqs, roots, verbatim,
    cov), `pc` the passage build's (refs, index, seqs, content, roots); `tools`
    the grammatical-tool occurrences (`word_function.json`); `survivors` the
    re-derived syntax survivors keyed on `sc` indexes; `scorer.symmetric` the
    cross-encoder, called ONCE and only after every check has passed; `texts`
    the cross-encoder texts by `sc` index; `displayed(s, a)` → `(raw chakl row,
    displayed text)`.
    """
    stats: dict = {}
    S = similarity_pairs(sim_data)
    W = passage_pairs(pas_data)
    union = union_pairs(S, W)

    def sidx(key):
        try:
            i, j = sc.index[parse_ref(key[0])], sc.index[parse_ref(key[1])]
        except KeyError as exc:
            raise StaleInput(f"{key[0]}/{key[1]} names a verse the corpus does not hold") from exc
        return i, j

    def pidx(key):
        try:
            return pc.index[parse_ref(key[0])], pc.index[parse_ref(key[1])]
        except KeyError as exc:
            raise StaleInput(f"{key[0]}/{key[1]} names a verse the QAC corpus does not hold") from exc

    # D2 — dense, ranked among the syntax survivors, for S (the check) and W \ S (sim).
    t0 = time.time()
    idx_of = {key: sidx(key) for key in union}
    not_survivor = [k for k in S if idx_of[k] not in survivors]
    if not_survivor:
        raise StaleInput(
            f"{len(not_survivor)} pair(s) quran_similarity.json stores do not pass today's "
            f"syntactic gate (first: {not_survivor[0][0]}/{not_survivor[0][1]})")
    only_w = [k for k in union if k not in S]
    wanted = {idx_of[k] for k in union}
    _, dense_idx, n_pop = dense_stage(vectors, sc.refs, set(survivors), wanted)
    dense_of = {k: dense_idx[idx_of[k]] for k in union}
    bad = dense_mismatches(S, dense_of)
    if bad:
        raise StaleInput(
            f"dense differs from quran_similarity.json on {len(bad)} pair(s) "
            f"(first: {bad[0]}): the verse vectors or the similarity dataset moved since it "
            f"was built")
    stats.update({"survivors": n_pop, "dense_s": round(time.time() - t0, 1)})

    # D5 / D3 — common parts, their character spans and pas, all settled before the
    # model loads, so every refusal comes first.
    t0 = time.time()
    parts: dict[tuple[str, str], dict] = {}
    for key in union:
        i, j = pidx(key)
        ra, rb = parse_ref(key[0]), parse_ref(key[1])
        part = common_part(pc.seqs[i], pc.seqs[j], pc.roots[i], pc.roots[j],
                           content_flags(pc.content[i], *ra, tools),
                           content_flags(pc.content[j], *rb, tools))
        if part is not None:
            parts[key] = part
    spans: dict[tuple[str, str], tuple[list, list]] = {}
    for key, part in parts.items():
        ra, rb = parse_ref(key[0]), parse_ref(key[1])
        spans[key] = (run_char_spans(word_index, *displayed(*ra), *ra, part["runs_a"]),
                      run_char_spans(word_index, *displayed(*rb), *rb, part["runs_b"]))
    # D3 — pas, from the passage build's own word counts.
    pas: dict[tuple[str, str], float] = {}
    for key in union:
        if key in W:
            pi, pj = pidx(key)
            pas[key] = pas_of(W[key]["k"], len(pc.seqs[pi]), len(pc.seqs[pj]))
        else:
            pas[key] = 0.0
    stats.update({
        "parts": len(parts),
        "parts_s_only": sum(1 for k in parts if k not in W),
        "passages_without_part": sum(1 for k in W if k not in parts),
        "matched_words": sum(len(p["m"]) for p in parts.values()),
        "root_edges": sum(1 for p in parts.values() for e in p["m"] if e[2] == ROOT_ONLY),
        "multi_run": sum(1 for p in parts.values()
                         if len(p["runs_a"]) > 1 or len(p["runs_b"]) > 1),
        "parts_s": round(time.time() - t0, 1)})

    # D2 — W \ S cross-encoded in a call of their own, then sim with no gate.
    t0 = time.time()
    ce_keys = sorted(only_w, key=lambda k: idx_of[k])
    ce = dict(zip(ce_keys, scorer.symmetric(
        [(texts[idx_of[k][0]], texts[idx_of[k][1]]) for k in ce_keys]))) if ce_keys else {}
    stats.update({"ce_pairs": len(ce_keys), "ce_s": round(time.time() - t0, 1)})

    pairs = []
    n_verbatim = 0
    for key, frm in union.items():
        i, j = idx_of[key]
        if key in S:
            sim, roots = S[key]["s"], S[key]["roots"]
        else:
            verbatim = sc.verbatim(i, j)
            n_verbatim += verbatim
            sim = ungated_sim(ce[key], dense_of[key], sc.cov(i, j),
                              syn_similarity(sc.seqs[i], sc.seqs[j]), verbatim)
            roots = sorted(sc.roots[i] & sc.roots[j])
        ca, cb = spans.get(key, (None, None))
        pairs.append(pair_record(key, frm, sim, pas[key], roots, W.get(key), parts.get(key),
                                 ca, cb))
    stats["verbatim_w_only"] = n_verbatim
    return pairs, unscored_of(sim_data["unscored"], pairs), stats


# ═══════════════════════════════════════════════════════════════════════════
#  The build
# ═══════════════════════════════════════════════════════════════════════════

def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gold_digests(no_gold: bool) -> dict:
    out = {}
    for name, path in (("quran_similarity_gold", similarity_build.GOLD_JSON),
                       ("quran_passages_gold", passages_build.GOLD_JSON)):
        if no_gold:
            out[name] = None
        elif not path.exists():
            sys.exit(f"Gold set not found at {path}. The header must name both gold sets this "
                     f"build is measured against; pass --no-gold to build without them.")
        else:
            out[name] = sha256_of(path)
    return out


def header(input_digests: dict, gold: dict) -> dict:
    return {
        "scope": SCOPE,
        "score": SCORE_RULE,
        "sim": SIM_RULE,
        "pas": PAS_RULE,
        "common_part": MARK_RULE,
        "content_word": CONTENT_WORD_RULE,
        "matching": MATCHING_RULE,
        "match_weights": {LEMMA: W_LEMMA, ROOT_ONLY: W_ROOT},
        "tie_break_rule": TIE_RULE,
        "tie_break": TIE_BREAK,
        "bridge": BRIDGE_RULE,
        "mark_min": MARK_MIN,
        "reranker": RERANKER_MODEL,
        "embedder": similarity_build.header(None)["embedder"],
        "inputs": input_digests,
        "gold": gold,
    }


def read_inputs() -> tuple[dict, dict, dict]:
    """`(similarity data, passage data, their sha256)`, parsed from the very bytes hashed."""
    data, digests = [], {}
    for name, path, schema, rebuild in (
            ("quran_similarity", paths.QURAN_SIMILARITY_JSON, loaders.QURAN_SIMILARITY_SCHEMA,
             similarity_build.REBUILD),
            ("quran_passages", paths.QURAN_PASSAGES_JSON, loaders.QURAN_PASSAGES_SCHEMA,
             passages_build.REBUILD)):
        if not path.exists():
            sys.exit(f"{path} is missing. Build order:\n    {BUILD_ORDER}\n(missing step: {rebuild})")
        raw = path.read_bytes()
        d = json.loads(raw)
        if not isinstance(d, dict) or d.get("schema") != schema:
            sys.exit(f"{path} has schema {d.get('schema') if isinstance(d, dict) else None!r}, "
                     f"expected {schema}. Build order:\n    {BUILD_ORDER}")
        data.append(d)
        digests[name] = hashlib.sha256(raw).hexdigest()
    return data[0], data[1], digests


class LazyScorer:
    """The cross-encoder, loaded on the first call — after every check has passed."""

    def __init__(self):
        self._scorer = None

    def symmetric(self, pairs):
        if self._scorer is None:
            t0 = time.time()
            print("Loading the cross-encoder…")
            self._scorer = CrossEncoderScorer()
            print(f"  ready in {time.time() - t0:.1f}s (device={self._scorer.device})")
        return self._scorer.symmetric(pairs)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-gold", action="store_true",
                    help="build without the gold sets (header gold digests = null)")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                    help="worker processes for the re-derived syntactic stage (default: CPUs − 1)")
    args = ap.parse_args(argv)

    held = qdrant_lock_held()
    if held is not None:
        sys.exit(f"The embedded Qdrant store at {held} is locked by another process "
                 f"(the backend, or build_index.py). Stop the backend first — the build reads "
                 f"the verse vectors out of that store — then rerun:\n    {REBUILD}")

    t_start = time.time()
    sim_data, pas_data, input_digests = read_inputs()
    head = header(input_digests, gold_digests(args.no_gold))
    want = (head["reranker"], head["embedder"])
    have = (sim_data["build"].get("reranker"), sim_data["build"].get("embedder"))
    if want != have:
        sys.exit(f"quran_similarity.json was built with {have}, this build loads {want}: its "
                 f"stored scores and the ones computed here would sit on two scales. "
                 f"Build order:\n    {BUILD_ORDER}")

    t0 = time.time()
    sc = similarity_build.Corpus()
    pc = passages_build.Corpus()
    print(f"Corpora: {len(sc.refs)} verses (similarity), {len(pc.refs)} (passages) "
          f"[{time.time() - t0:.1f}s]")
    t0 = time.time()
    survivors, _ = syntax_stage(sc.seqs, sc.surah_of, sc.scored,
                                sorted(set(sc.surah_of)), args.jobs)
    print(f"SYNTAX: {len(survivors)} cross-surah syntax survivors re-derived "
          f"[{time.time() - t0:.1f}s]")
    t0 = time.time()
    print("Loading the verse vectors…")
    vectors = load_vectors()
    from quran_data.corpus import chakl_by_ref, strip_leading_basmala, verses_by_id
    from retrieval.reranker import _passage_text

    by_ref = {(int(v["surah_number"]), int(v["ayah_number"])): _passage_text(v)
              for v in verses_by_id().values()}
    texts = [by_ref[r] for r in sc.refs]
    word_index = loaders.word_index()
    tools = loaders.word_function()
    chakl = chakl_by_ref()

    def displayed(s: int, a: int) -> tuple[str, str]:
        raw = chakl[(s, a)]["text"]
        return raw, strip_leading_basmala(s, a, raw)

    print(f"  inputs ready [{time.time() - t0:.1f}s]")
    try:
        pairs, unscored, stats = compose(sim_data, pas_data, sc, pc, survivors, vectors,
                                         LazyScorer(), texts, word_index, displayed,
                                         tools=tools)
    except StaleInput as exc:
        sys.exit(f"REFUSED — nothing written. {exc}\nRebuild in this order:\n    {BUILD_ORDER}")

    by_from = Counter(tuple(p["from"]) for p in pairs)
    print(f"DENSE: percentile over {stats['survivors']} syntax survivors; check passed on "
          f"{by_from[(FROM_SIMILARITY,)] + by_from[(FROM_SIMILARITY, FROM_PASSAGE)]} stored "
          f"pairs [{stats['dense_s']}s]")
    print(f"CROSS-ENCODER: {stats['ce_pairs']} passage-only pairs, {2 * stats['ce_pairs']} "
          f"predictions; {stats['verbatim_w_only']} verbatim [{stats['ce_s']}s]")
    print(f"PAIRS: {len(pairs)} — similarity only {by_from[(FROM_SIMILARITY,)]}, passage only "
          f"{by_from[(FROM_PASSAGE,)]}, both {by_from[(FROM_SIMILARITY, FROM_PASSAGE)]}")
    print(f"COMMON PART: {stats['parts']} pairs ({stats['parts_s_only']} without a passage; "
          f"{stats['passages_without_part']} passage pair(s) without one), "
          f"{stats['matched_words']} matched words, {stats['root_edges']} root-only edges, "
          f"{stats['multi_run']} pairs in several runs [{stats['parts_s']}s]; "
          f"unscored verses: {len(unscored)}")

    out = paths.QURAN_CLOSE_VERSES_JSON
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(dumps(dataset(pairs, unscored, head)), encoding="utf-8")
    tmp.replace(out)
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.2f} MB) — {time.time() - t_start:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
