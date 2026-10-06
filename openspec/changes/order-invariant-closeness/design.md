## Context

Four offline builds make up the closeness relation, in order:
`build_surah_similarity.py` (intra, defines `syn`, `cov`, `sem`, the gates) →
`build_quran_similarity.py` (cross-surah, IMPORTS that definition, adds dense-among-survivors, the
short-pair rule, ρ) → `build_quran_passages.py` (Smith–Waterman passages) →
`build_quran_close_verses.py` (union, `pas`, `score`, display common part — order-invariant since
`order-invariant-common-words`).

Order enters at two places: `syn = 1 − lev(sigA, sigB) / max(|A|, |B|)` over the per-word QAC
elements `(segs, stem)`, and the Smith–Waterman passage, whose matches cannot cross. Everything else
(`cov`, cross-encoder, dense) is already order-invariant.

Decisions taken with the user (2026-10-06): syntax stays a FILTER (same subject, other construction
→ not close; the gold sets stay valid as labelled); the new definition applies intra AND cross; the
approach is «everything on the matching» (B), Smith–Waterman retired.

Baseline measured on the current datasets, before any change (recorded here as the comparison point,
not as a tuning target):

| Eval | Figure | Value |
|---|---|---|
| intra (`eval_surah_similarity.py`) | recall@10 of positives | 48/60 = 0.800 |
| | positives lost at candidate generation (syntax gate + cap) | 6/60 |
| | non-consecutive negatives in a top-3 / consecutive stored | 0 / 0 |
| cross (`eval_quran_similarity.py`) | T1 recall@10 first sample | 41/60 = 0.683 |
| | positives lost at the syntax gate | 14 (+3 short_exact, 2 no_shared_root) |
| | T2 negatives in a top-3 / T3 / T4 / T5 | 3 / 0 of 40 / 6 of 17 / 0 |
| passages (`eval_quran_passages.py`) | recall / negatives found | 38/40 / 1/20 |
| close verses (`eval_quran_close_verses.py`) | AUC(score), 89 × 7 | 0.726 |

## Goals / Non-Goals

**Goals:**
- No step of the relation depends on the order of shared lemmas or roots; the construction INSIDE a
  block of words is still measured.
- One definition of content word, one matching, one syntax measure — written once, imported by all
  four builds.
- Every frozen value (σ, τ_sem, weights, floor, K, M, ρ, short-pair rule, passage thresholds, τ_group)
  kept as it is: only definitions change, so the measurement compares definitions, not tunings.

**Non-Goals:**
- Changing the gold sets, the API shapes, the frontend, or the display rule of step 1 beyond the
  shared content-word definition (D1).
- Re-tuning any parameter after the build (a miss is recorded).
- A relation without a syntax filter (rejected by the user).

## Decisions

**D1 — Content word (shared).** A word is a content word when it carries a resolved primary root that
belongs to its verse's content-root set as `content_root_sets()` computes it today (tools of
`word_function.json`, function nouns, the function-word stoplist removed) AND its own reference is not
in `word_function.json`. One function, in the shared module, used by `lex`, by the passage's content
count and by the displayed common part. The display of step 1 used «rooted and not a tool»; it now
also drops function nouns / stoplisted roots (e.g. كُلّ), so the coloured set can only shrink.

**D2 — The matching (shared).** One maximum-weight one-to-one assignment over ALL words of A × B
(`linear_sum_assignment`, maximize). Edges: two content words with the same lemma token → 1; two
content words with different tokens and the same primary root → 0.5; two NON-content words with the
same token → 1; nothing else (a content word never pairs with a function word). Every edge minus
`10⁻³ · |p/n_A − q/n_B|` (nearest relative position breaks ties). The assignment decomposes into the
content problem (step 1's matching, unchanged up to D1) and an identical-token function-word problem.
Each edge is kept with its kind: `lemma`, `root`, `tool`.

**D3 — `lex` replaces `cov`.** `lex = Mw / (IA + IB − Mw)`, where `IA` (resp. `IB`) is the sum of
`idf(root)` over A's content WORDS and `Mw = Σ` over content edges of `w · idf(root)` (w = 1 lemma,
0.5 root). In `[0, 1]`, symmetric, 1 for identical content. IDF = `root_idf` as today. Word-level, not
set-level: a root repeated in one verse counts for each occurrence, and is matched one-to-one.
`sem = (w_ce·ce + w_dense·dense) × (floor + (1 − floor)·lex)`; «a pair is stored only when it shares
a content root» becomes «only when `Mw > 0`». The stored field is renamed `cov` → `lex`; the shared
roots displayed are the roots of the content edges.

**D4 — `syn`, order-robust.** Over the unchanged signature (one element per word: `(segs, stem)`):
`uni = |EA ∩ EB| / max(nA, nB)` (multiset intersection of elements);
`bi = |BA ∩ BB| / max(nA − 1, nB − 1)` (multiset of consecutive element pairs), and `bi = uni` when
`max(nA, nB) = 1`; `syn = ½·uni + ½·bi`. Symmetric, in `[0, 1]`, 1 iff the two signatures are equal
as multisets of elements and of bigrams (so for identical sequences). A displaced block of L words
loses at most 3 bigrams, against 2L edits before. Particles and tools stay in the signature. σ = 2/3
and `short_exact_max_len = 3` (longer signature ≤ 3 → needs `syn = 1`) unchanged.
Alternative rejected: syntax agreement measured on matched pairs only — it would make syntax depend
on the lexicon, while the filter is meant to be structural (and the gold's `neg_same_syntax_diff_
subject` presupposes a lexicon-free syntax).

**D5 — Exact pre-filters for the cross build.** With `m = min(nA, nB)`, `M = max(nA, nB)`:
`uni ≤ m / M` and `bi ≤ (m − 1) / (M − 1)`, so `syn ≤ ½(m/M + (m−1)/(M−1))` — a length window,
exact. Then `uni ≤ |EA ∩ EB| / M` from the bags is exact and cheap; `bi ≤` its bigram analogue. A
pair is skipped only when an upper bound is `< σ`; the test samples skipped pairs and checks
`syn < σ` on each (requirement kept). The intra build needs no pre-filter.

**D6 — The passage as an order-free dense region.** On the identical-token edges of D2 (`lemma` and
`tool`; `root` edges count as gaps — a passage is shared WORDING): for every window `[i1, i2]` of A
bounded by matched positions, take the edges with `p ∈ [i1, i2]`, let `[j1, j2]` be the span of their
partners in B, and keep only edges with both ends inside both windows: `k` of them. Score
`2k − (i2 − i1 + 1 − k) − (j2 − j1 + 1 − k)`; best score wins, ties → smaller `i1`, then smaller span.
Accepted when `k ≥ L_MIN = 6`, `k ≥ DENSITY = 0.75 × max(spanA, spanB)` and at least
`CONTENT_MIN = 3` kept edges join content words — the current thresholds. Stored as today: `k`, `wa`
= `[i1, i2]`, `wb` = `[j1, j2]`, `roots`. Candidate generation unchanged (token multisets sharing
≥ 6 tokens — exact, since `k` ≤ shared tokens). O(m³) per pair with m matched words. Smith–Waterman,
its scores and traceback are removed.

**D7 — Close verses.** Unchanged composition (union, `sim`, `pas = k / min(n)`, `score`). Its
ungated `sim` for passage-only pairs uses the new `syn` / `lex`. The common part is D2's content
edges (D1 definition), bridging and runs as in `order-invariant-common-words`.

**D8 — Code layout.** One new pure module `scripts/closeness_core.py` (content words, matching,
`lex`, `syn`, bounds, passage region) imported by the four builds; nothing copied. Schemas bump:
`SURAH_SIMILARITY_SCHEMA`, `QURAN_SIMILARITY_SCHEMA`, `QURAN_PASSAGES_SCHEMA`,
`QURAN_CLOSE_VERSES_SCHEMA`; each header names `signature_measure: "uni+bigram-bag"`,
`lexical: "matching-idf-jaccard"`, `passage: "dense-region"` as applicable. Shared-parameter digests
change on purpose (the definitions changed); the cross build still checks it shares the intra values.

**D9 — Pre-registered targets** (written before any build of this change; a miss is recorded, never
tuned):

| Eval | Target |
|---|---|
| intra | recall@10 ≥ 0.75; candidate-generation losses ≤ 15 %; non-consecutive negatives in a top-3 ≤ 2; consecutive stored = 0 (the existing four) |
| cross | T1 ≥ 0.65; T2 ≤ 4; T3 ≤ 1; T4 ≥ 6 of 17; T5 = 0 (pre-filter exactness) |
| passages | recall ≥ 0.8; negatives found ≤ 10 %; 28:20/36:20 found; **2:3/14:31 found** |
| close verses | U1 AUC(score) ≥ 0.80; U2, U3, U4 as specified |
| definition (the point of the change) | **syntax-gate losses not above baseline** (intra ≤ 6, cross ≤ 14); a verse pair differing only by one displaced block of ≥ 3 words has `syn ≥ σ` (unit test) |

## Risks / Trade-offs

- [The bag is lenient: two verses with the same words in a scrambled construction can pass] →
  bigrams keep local construction; the semantic gate and the gold's `neg_same_syntax_diff_subject`
  measure it; reported, not tuned.
- [More syntax survivors → more cross-encoder pairs (cross build cost)] → the cap M and the
  pre-filters bound it; build time recorded. If survivors explode beyond the cap's control the build
  reports it; no parameter is changed to compensate.
- [Word-level `lex` differs from set-level `cov` on repeated roots] → intended (matching is one-to-one);
  recorded in the header.
- [D1 shrinks the displayed common part (function nouns no longer coloured)] → consistent single
  definition; pinned in tests (2:3/14:31 unchanged).
- [Passage region picks a different window than Smith–Waterman on some pairs] → reported via the
  passage eval and the pinned pairs.

## Migration Plan

1. Implement `closeness_core.py` + the four builds + eval scripts + tests.
2. Stop the backend. Rebuild in order: intra → cross → passages → close verses. Restart.
3. Run the four evals; record every figure in this design under «Measured result», PASS / MISS.
Rollback: revert the commit and rebuild the four datasets.

## Open Questions

None.
