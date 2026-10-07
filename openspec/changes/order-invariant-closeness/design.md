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
→ not close); the new definition applies intra AND cross; the approach is «everything on the
matching» (B), Smith–Waterman retired. **Refined after version 1 failed (same day): closeness is
invariant to the permutation of blocks AND to pronouns / clitics / function words — two verses that
permute two blocks of the same material are close, not scattered.**

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
- No step of the relation depends on the order of shared lemmas or roots, nor on the order of blocks;
  the construction INSIDE a block of words is still measured.
- No step depends on pronoun suffixes, clitic particles, case endings or verb mood: two words differing
  only there are the same element.
- One definition of content word, one matching, one syntax measure — written once, imported by all
  four builds.
- Every frozen value (σ, τ_sem, weights, floor, K, M, ρ, short-pair rule, passage thresholds, τ_group)
  kept as it is: only definitions change, so the measurement compares definitions, not tunings.
- The measurement is honest about what was looked at: version 2 was DESIGNED after reading the gold
  failures of version 1, so it is measured on a fresh blind sample, and the existing gold is reported
  apart as in-sample.

**Non-Goals:**
- Changing the API shapes or the frontend; changing the display rule of step 1 beyond the shared
  content-word definition (D1) and the matching tie-break (D2).
- Re-tuning any parameter after the build (a miss is recorded).
- A relation without a syntax filter (rejected by the user).
- Intra-surah passages (a short formula inside a longer verse of the same surah, e.g. 37:159/180) —
  out of scope, recorded as a known miss class.

## Version 1 — measured and closed (2026-10-06)

Version 1 defined `syn` as a unigram + bigram bag over the UNCHANGED fine element `(segs, stem)` and
the passage as the best-SCORING dense region with a relative-position tie-break. Implemented, reviewed
and rebuilt (`--fresh`): intra survivors fell sharply (surah 2: 4), cross 1 017 survivors (1 316
before), passages 2 027 (2 191), close verses 2 265 pairs (2 491).

| Eval | Target (D9) | Baseline | Version 1 | |
|---|---|---|---|---|
| intra recall@10 | ≥ 0.75 | 48/60 | 41/60 = 0.683 | **MISS** |
| intra candidate-generation losses | ≤ 15 % | 6/60 | 15/60 = 25 % | **MISS** |
| intra negatives in a top-3 / consecutive stored | ≤ 2 / 0 | 0 / 0 | 0 / 0 | PASS |
| cross T1 | ≥ 0.65 | 41/60 | 34/60 = 0.567 | **MISS** |
| cross T2 | ≤ 4 | 3 | 3 | PASS |
| cross T3 | ≤ 1 | 0 | 0 | PASS |
| cross T4 | ≥ 6 of 17 | 6 | 5 | **MISS** |
| cross T5 (pre-filter exactness) | 0 | 0 | 0 | PASS |
| passages recall | ≥ 0.8 | 38/40 | 32/40 = 0.800 | PASS (at the bound) |
| passages negatives found | ≤ 10 % | 1/20 | 4/20 (all `neg_scattered`) | **MISS** |
| 28:20/36:20, 2:3/14:31 passages | found | found / found | found (k 7) / found (k 7) | PASS |
| close verses U1 AUC(score) | ≥ 0.80 | 0.726 | 0.698 (80 × 9) | **MISS** |
| close verses U2 / U3 / U4 | as specified | PASS | PASS | PASS |
| syntax-gate losses not above baseline | intra ≤ 6, cross ≤ 14 | 6 / 14 | 15 / 24 | **MISS** |
| displaced 3-block keeps `syn ≥ σ` (unit) | holds | — | holds | PASS |

**Diagnosis (in-sample — it read the gold, which is why version 2 needs a blind sample).**
Four distinct causes:

1. *Bigrams punish substitutions.* A substituted element costs `1/n` under Levenshtein, about `1.5/n`
   under the bag of bigrams. Near-parallels in the Quran differ mostly by substitution, rarely by
   displaced blocks, so the common case got harsher (43:83/70:42, identical text with two moods
   tagged differently: 0.750 → 0.661; 6:117/68:7: 0.727 → 0.614).
2. *The element is too fine — the ACTUAL root cause, shared with the baseline.* The element is the
   whole word's segment tuple with case and mood, so a pronoun suffix (رَبِّكُمْ/رَبِّهِمْ), a clitic
   (وَالزُّبُرِ/وَبِالزُّبُرِ) or a mood (يَخُوضُوا SUBJ/JUS) makes two words wholly different. Re-measuring
   the 20 positives the BASELINE lost at the syntax gate with the same Levenshtein over a COARSE element
   (stem POS, verb aspect + voice, noun subcategory; no prefix, suffix, case, mood): 18 of 20 reach σ,
   while 0 of the 13 `neg_same_subject_diff_syntax` negatives do (0 before as well). The two that stay
   out are 3:184/35:25 (five real substitutions: passive/active, aspect, رُسُلٌ/الَّذِينَ) and 37:159/180
   (a 4-word formula inside a 6-word verse — an intra-surah passage, out of scope).
3. *The relative-position tie-break is wrong for partial passages.* 2:255 (long) and 3:2 (short) share
   their opening 7 words verbatim, but 2:255 holds several «لا»; the tie-break pairs the «لا» of 3:2
   (at 2/7 of its verse) with a «لا» near 2/7 of the long verse, not the opening one — k falls to 5 and
   the passage is lost.
4. *The best-SCORING region is not the best ACCEPTED one.* 2:164/45:5: the top-scoring window swallows
   2:164's long clause on ships and the sea and fails density, while a sub-window passes (the same
   defect Smith–Waterman had on 29:8/31:15).

Block permutation was checked and found NOT to be what the whole-verse gate decides on: 6:102/40:62
and 49:15/61:11 permute two blocks but differ by 4–6 words in length, so the longer verse keeps
≥ 1/3 unshared words whatever the order; they are PASSAGES (k = 10) and the order-free region
already finds them. The gold labelled them `neg_scattered`; under the user's definition they are
positives — a gold question (D10), not a mechanism question.

## Decisions (version 2)

**D1 — Content word (shared).** A word is a content word when it carries a resolved primary root that
belongs to its verse's content-root set as `content_root_sets()` computes it today (tools of
`word_function.json`, function nouns, the function-word stoplist removed) AND its own reference is not
in `word_function.json`. One function, in the shared module, used by `lex`, by the passage's content
count and by the displayed common part. The display of step 1 used «rooted and not a tool»; it now
also drops function nouns / stoplisted roots (e.g. كُلّ), so the coloured set can only shrink.

**D2 — The matching (shared), tie-break by median shift.** One maximum-weight one-to-one assignment
over ALL words of A × B (`linear_sum_assignment`, maximize). Edges: two content words with the same
lemma token → 1; two content words with different tokens and the same primary root → 0.5; two
NON-content words with the same token → 1; nothing else (a content word never pairs with a function
word). Ties: first the **anchors** — edges whose token occurs exactly once in each verse — are forced
and `δ = median(q − p)` over them (`δ = 0` with no anchor); then every edge weight is reduced by
`10⁻³ · |(q − p) − δ| / max(nA, nB)`, so a repeated token takes the partner that sits at the same
OFFSET as the shared material, not at the same relative position in its verse. Deterministic;
symmetric up to orientation (read with the lower reference as A). Each edge keeps its kind: `lemma`,
`root`, `tool`. Replaces version 1's `|p/nA − q/nB|`.

**D3 — `lex` replaces `cov`.** `lex = Mw / (IA + IB − Mw)`, where `IA` (resp. `IB`) is the sum of
`idf(root)` over A's content WORDS and `Mw = Σ` over content edges of `w · idf(root)` (w = 1 lemma,
0.5 root; a lemma edge whose two roots differ takes the mean of the two idf). In `[0, 1]`, symmetric,
1 for identical content. IDF = `root_idf` as today. Word-level, not set-level.
`sem = (w_ce·ce + w_dense·dense) × (floor + (1 − floor)·lex)`; «a pair is stored only when it shares
a content root» becomes «only when `Mw > 0`». The stored field is renamed `cov` → `lex`; the shared
roots displayed are the roots of the content edges.

**D4 — `syn`: Levenshtein over a COARSE element, blocks re-orderable.** The element of a word is the
tuple of its STEM segments' labels (prefix and suffix segments dropped): a verb is `V.<aspect>`
(PERF / IMPF / IMPV) plus `.PASS` when passive; a noun is `N:<subcategory>` (PN, ADJ, PRON, DEM, REL,
T, LOC, NV, INTG, COND, ADDR) or `N`; a particle is `P:<tag>`. No case, no mood — a pronoun suffix,
a clitic, a case ending or a mood never changes the element. Particles stay in the signature (negation,
condition, vocative ARE syntax); the «stopword» invariance lives in the lexical signal.
`syn_seq(X, Y) = 1 − lev(X, Y) / max(|X|, |Y|)`. **Block re-ordering**: from the D2 edges, B's
positions are cut into blocks — a block starts at a matched position whose partner in A is not after
the previous matched position's partner; an unmatched position stays with the block it follows —
and the blocks are concatenated in the order of their first partner in A, giving `B′` (and `A′`
symmetrically; with no edge, `B′ = B`). `syn = max(syn_seq(A, B), syn_seq(A, B′), syn_seq(A′, B))`.
Symmetric, in `[0, 1]`, 1 for identical sequences and for a pure permutation of blocks; a substitution
costs `1/n`. σ = 2/3 and `short_exact_max_len = 3` unchanged. Version 1's bag of bigrams is dropped.
Alternative rejected: syntax measured on matched pairs only (lexicon-dependent; the gold's
`neg_same_syntax_diff_subject` presupposes a lexicon-free syntax; a frame-only pair such as
26:203/37:54 would pass).

**D5 — Exact pre-filters for the cross build.** With `m = min(nA, nB)`, `M = max(nA, nB)`:
`syn ≤ m / M` (length) and `syn ≤ |bagA ∩ bagB| / M` over the coarse-element multisets — both exact
for every re-ordering, since re-ordering keeps the bag and an element outside the intersection costs
at least one edit. A pair is skipped only when a bound is `< σ`; the test samples skipped pairs and
checks `syn < σ` on each. The bigram bound of version 1 is dropped (invalid under re-ordering).

**D6 — The passage as the LARGEST ACCEPTED order-free region.** On the identical-token edges of D2
(`lemma` and `tool`; `root` edges count as gaps): a candidate is a window `[i1, i2]` of A bounded by
matched positions together with a window `[j1, j2]` of B bounded by matched positions; its kept edges
are those with both ends inside; `k` their number. It is ACCEPTED when `k ≥ L_MIN = 6`,
`k ≥ DENSITY = 0.75 × max(spanA, spanB)` and at least `CONTENT_MIN = 3` kept edges join content
words. The stored passage is the accepted candidate with the largest `k`; ties: the larger
`2k − (spanA − k) − (spanB − k)`, then the smaller `i1`, then the smaller `i2`, then the smaller
`j1`; read with the lower-surah verse as A. Implementation: for each A window, sort the partners of
its edges; every contiguous run of that sorted list is a B window; `O(m⁴)` with `O(1)` per candidate
(prefix sums), pruned exactly by `k ≥ 6` and `span ≤ k / 0.75`. Stored as today: `k`, `wa`, `wb`,
`roots`. Candidate generation unchanged (token multisets sharing ≥ 6 tokens). Version 1 kept the
best-SCORING candidate with the B window forced to the partners' hull; both are replaced.

**D7 — Close verses.** Unchanged composition (union, `sim`, `pas = k / min(n)`, `score`). Its
ungated `sim` for passage-only pairs uses the new `syn` / `lex`. The common part is D2's content
edges (D1 definition, D2 tie-break), bridging and runs as in `order-invariant-common-words`.

**D8 — Code layout.** One pure module `scripts/closeness_core.py` (content words, matching, `lex`,
coarse element, `syn`, bounds, passage region) imported by the four builds; nothing copied. Schemas
bumped (done in version 1 and kept); each header names `signature: "stem-coarse"`,
`signature_measure: "levenshtein+block-reorder"`, `lexical: "matching-idf-jaccard"`,
`tie_break: "median-shift"`, `passage: "largest-accepted-region"` as applicable. Shared-parameter
digests change on purpose; the cross build still checks it shares the intra values.

**D9 — Pre-registered targets** (unchanged from version 1; a miss is recorded, never tuned). On the
RELABELLED gold (D10), reported as **in-sample**:

| Eval | Target |
|---|---|
| intra | recall@10 ≥ 0.75; candidate-generation losses ≤ 15 %; non-consecutive negatives in a top-3 ≤ 2; consecutive stored = 0 |
| cross | T1 ≥ 0.65; T2 ≤ 4; T3 ≤ 1; T4 ≥ 6 of 17; T5 = 0 (pre-filter exactness) |
| passages | recall ≥ 0.8; negatives found ≤ 10 %; 28:20/36:20 found; 2:3/14:31 found |
| close verses | U1 AUC(score) ≥ 0.80; U2, U3, U4 as specified |
| definition | syntax-gate losses not above baseline (intra ≤ 6, cross ≤ 14); a pure permutation of blocks has `syn = 1` and `lex = 1` (unit) |

On the BLIND sample (D10, the figure that counts): **positives stored (either direction) ≥ 0.65;
negatives stored ≤ 0.25**.

**D10 — Measurement protocol, written before any version-2 code.**
1. *The definition, in writing* (header of every gold file, Arabic and English): two verses are close
   when they share the same material (lemmas or roots; pronoun suffixes, clitics and function words
   do not count), built the same way (verb aspect and voice, noun type, the particles), with their
   blocks in ANY order; two verses share a passage when at least 6 identical words, at least 3 of them
   content words, form one dense region (≥ 3/4 of each window) in both verses, blocks in any order.
2. *Relabel the three existing gold sets* under that definition, in a FRESH context given the
   definition and the verse texts only — no system output of any version. Every changed label records
   its reason. `neg_scattered` splits into permuted blocks (→ positive) and truly scattered words
   (stays negative; e.g. 21:33/36:40, a 4-word formula plus scattered nouns). The formula pairs
   «وَمَا أَدْرَاكَ مَا X» stay `neg_same_syntax_diff_subject` — same construction, other subject — and it is
   the semantic gate's job to drop them. Versions and sha256 bump; the evals refuse the old digests.
3. *A fresh blind sample*: `scripts/draw_closeness_blind_sample.py` draws 60 cross-surah pairs with a
   fixed seed, MODEL-FREE and without any gate: the population is every pair sharing ≥ 3 content
   lemmas (the passage candidate generator at `l_min = 3` over content tokens), stratified by `lex`
   computed on the raw matching — 20 pairs in each of `[0.3, 0.5)`, `[0.5, 0.7)`, `[0.7, 1]`. Labelled
   in a fresh context (definition + texts only) BEFORE the first version-2 build, committed to
   `tests/eval/closeness_blind_v2.json` with its sha256 in the headers of the cross and close-verses
   datasets. `scripts/eval_closeness_blind.py` reports positives stored / negatives stored, and refuses
   a digest mismatch.
4. Nothing is changed after the build; a miss is recorded as the result.

*Done 2026-10-06, before any version-2 build.* Blind sample: 60 pairs drawn from 221 848 (every pair
scored by `lex`; 1 979 / 297 / 163 in the three bins), labelled 42 positive / 18 negative. Relabel:
passages 2 changes (6:102/40:62 → positive; 2:106/35:1 → `neg_short_formula`, أَنَّ ≠ إِنَّ), cross 20
(3:10/58:17 → positive; 19 positives → `neg_same_syntax_diff_subject`), intra 10 (positives →
`neg_same_syntax_diff_subject`). The 29 flips all come from the definition's «same material» clause:
the old gold held parallel formulas with NO shared lemma as positives (81:1/82:1, 77:8/77:10, 94:2/94:4,
oath moulds). **User decision (2026-10-06): material is required** — consistent with the structural
rule «≥ 1 shared content root» the relation has carried since its first build (the baseline's
`no_shared_root` losses were exactly such pairs). Labeller conventions recorded in each file's
reasons; a substituted proper name counts as a slot fill, not as different material.

## Risks / Trade-offs

- [The coarse element is lenient: more syntax survivors → more cross-encoder pairs] → the cap M and
  the pre-filters bound it; survivors and build time recorded; no parameter changed to compensate.
- [Block re-ordering guided by the lexical matching makes `syn` partly lexicon-dependent] → only the
  ORDER of blocks is taken from the matching; the un-reordered alignment is always one of the three
  candidates, so `syn` can never fall below the plain coarse Levenshtein.
- [Relabelling the gold under the new definition changes the denominators of D9] → targets are ratios;
  the baseline's figures are reported on the OLD labels and are not comparable one to one — the blind
  sample is the comparable figure.
- [Word-level `lex` differs from set-level `cov` on repeated roots] → intended; recorded in the header.
- [D1 shrinks the displayed common part (function nouns no longer coloured)] → pinned (2:3/14:31).
- [D2's new tie-break changes a few displayed common parts of step 1] → display only; pinned pairs
  unchanged; reported by the step-1 counts.
- [`O(m⁴)` region search] → `m` is the number of identical-token edges of a candidate pair (median
  ≈ 8); the passage build is multiprocess; exact pruning keeps it in seconds–minutes; measured.

## Migration Plan

1. D10 steps 1–3 (gold relabel + blind sample) — committed before any code.
2. Implement D2 (tie-break), D4, D5, D6 in `closeness_core.py`; rewire the signature builder and the
   cross pre-filters; eval script for the blind sample.
3. Stop the backend. Rebuild in order: intra → cross → passages → close verses. Restart.
4. Run the five evals; record every figure under «Measured result (version 2)», PASS / MISS.
Rollback: revert the commit and rebuild the four datasets.

## Measured result (version 2, rebuild 2026-10-07, all four datasets, `--fresh`)

No parameter changed after the build. Builds: intra 72 s; cross 480 s — 18 978 384 pairs → 5 934 258 in
the length window → 326 672 past the coarse-bag bound → 44 371 pass σ → **25 630** pass the short-pair
rule (1 316 at baseline); passages 2 878 (2 191); close verses **4 148 pairs** (2 491) — similarity
only 1 270, passage only 2 593, both 285; common part on 3 571.

**Blind sample (the figure that counts, labelled before the build):**

| Target | Measured | |
|---|---|---|
| positives stored ≥ 0.65 | 36/42 = **0.857** | PASS |
| negatives stored ≤ 0.25 | 2/18 = **0.111** | PASS |

**Relabelled gold (in-sample — version 2 was designed after reading version 1's failures on it):**

| Eval | Target (D9) | Measured | |
|---|---|---|---|
| intra recall@10 | ≥ 0.75 | 49/50 = 0.980 | PASS |
| intra candidate-generation losses | ≤ 15 % | 1/50 | PASS |
| intra negatives in a top-3 / consecutive stored | ≤ 2 / 0 | 2 / 0 | PASS |
| cross T1 | ≥ 0.65 | 52/53 = 0.981 | PASS |
| cross T2 negatives in a top-3 | ≤ 4 | **9** (all `neg_same_syntax_diff_subject`) | **MISS** |
| cross T3 second-sample negatives stored | ≤ 1 | **2/51** (88:23/92:16, 83:19/101:3) | **MISS** |
| cross T4 second-sample positives stored | ≥ 80 % of 7 | 5/6 (the relabel left 6 positives) | **MISS** (by the formula) |
| cross T5 pre-filter exactness | 0 | 0 | PASS |
| passages recall | ≥ 0.8 | 40/40 | PASS |
| passages negatives found | ≤ 10 % | **4/20** (14:32/45:12, 49:15/61:11, 21:33/36:40, 13:35/47:15) | **MISS** |
| 28:20/36:20, 2:3/14:31 | found | found (k 7) / found (k 7) | PASS |
| close verses U1 AUC(score) | ≥ 0.80 | **0.875** (91 × 19; baseline 0.726) | PASS |
| close verses U2 / U4 | as specified | PASS / PASS | PASS |
| close verses U3 26:203/37:54 | `pas` 0, last of its cell | `pas` 0, score 0.21, rank 16 of 33 | **MISS** |
| syntax-gate losses | intra ≤ 6, cross ≤ 14 | 1 / 1 | PASS |

**Reading.** Recall is solved (the blind sample, intra and cross all ≥ 0.86; the baseline's syntax-gate
losses fall from 6 / 14 to 1 / 1; AUC 0.726 → 0.875) and the blind negatives stay low (2/18). The cost is
PRECISION on one class: short verses that share ONE lemma inside the same mould (69:3/83:19
«وَمَا أَدْرَاكَ مَا X», 43:74/54:47, 81:19/86:13) — the coarse element makes the mould pass σ and the
single shared lemma passes the shared-root rule, so only the semantic gate stands between them and a
list; nine reach a top-3. The passage misses are the definition's borderline: two are permutations
the relabeller kept negative under the stricter «runs ≥ 2» reading (14:32/45:12, 49:15/61:11) which the
definition's text accepts. The volume grew (4 148 pairs, 1 270 similarity-only against 300). Recorded;
not tuned.

## Open Questions

None.
