## Context

The cross-surah similarity relation (`quran_similarity.json`, 1 088 stored pairs) is the intra-surah
definition plus three cross-only rules (`tighten-cross-surah-similarity`), the order-invariant
signals (`order-invariant-closeness`) and the short-verse material rule (`short-verse-material`, ≥ 2
shared lemmas when the shorter verse has ≤ 5 QAC words). It is composed with the shared passages into
`quran_close_verses.json` (3 681 pairs: 803 similarity only, 2 593 passage only, 285 both), which feeds
the surah × surah map and the reading-page annotations.

Two facts motivate the change:

1. **Shared material is never required on a long verse.** `lex` only modulates `sem`, through
   `floor = 0.25`, so a pair with almost no shared lemma keeps a quarter of its cross-encoder score.
   2:10 / 39:26: `ce` 0.77, `dense` 0.94, `lex` 0.097, `syn` 0.75 → `sem` 0.265 ≥ `τ_sem` 0.125, stored
   with three shared lemmas (الله، عذاب، كان) — the «few scattered shared words» the blind definition
   already calls not close. 314 of the 1 088 pairs have `lex < 0.2` and `syn < 0.9`.
2. **The blind sample never looked there.** `closeness_blind_v2` was drawn with ≥ 3 shared content
   lemmas and `lex ∈ [0.3, 1]`, so the class above was outside its population. Its 0.857 / 0.111 is
   true of what it measured, and silent on this.

On the reading page, a whole-verse pair rings the marker and colours no word; a passage-only pair
colours words and leaves the marker plain. The user wants one cue.

## Goals / Non-Goals

**Goals:** enforce the written definition on cross-surah similarity — same meaning AND same syntax AND
enough shared lemmas, at every length; choose its two thresholds by a rule fixed before any label is
read; measure them on a sample that did not choose them; show one orange cue carrying every common
part.

**Non-Goals:** the intra-surah relation and its groups (green — the user finds it right); the passage
relation and its parameters (a passage still suffices on its own, user's decision); the common-part
matching itself; the cross-encoder, the embedder, `τ_sem`, `floor`, the weights; the map's UI.

## Decisions

**D1 — The material rule (cross only).** From the pair's existing order-invariant content-word matching
(`closeness_core`, the `m` edges): `L` = number of `lemma` edges, `c = min(cA, cB)` = content words of
the verse with fewer content words (content word = the `lex` definition: primary root among the verse's
content roots, occurrence not a grammatical tool). Stored only when `L ≥ 2` AND the coverage ≥ `κ` — first the count `L / c`, then (user decision, «Follow-up: weighted coverage») the IDF-weighted coverage of the better-covered verse; an intermediate `L ≥ 3` was built, measured and reverted («Follow-up: L ≥ 3»). Root-only
edges count for nothing, as in `short-verse-material`, because the user asked for shared lemmas. The
denominator is the shorter verse so a short verse wholly contained in a long one is close (its content
is all shared); requiring coverage of the longer one would reject every quotation. A pure function
`material_ok(edges, ca, cb, kappa)` in `closeness_core`; the existing `short_material_ok` stays (it is
the intra rule too, and for the cross build it becomes implied whenever `L ≥ 2`).

Alternatives rejected: a floor on `lex` (IDF Jaccard over the union — it penalises a short verse inside
a long one, and it is not «enough lemmas»); raising `floor` or `τ_sem` (moves the intra relation too, and
keeps meaning able to buy closeness without material); excluding frequent lemmas such as الله / كان
(a new list to curate; the calibration will show whether coverage alone suffices — recorded as a risk).

**D2 — The syntax rule (cross only).** `syn ≥ σ_x`, `σ_x ∈` grid below, `σ_x ≥ σ = 2/3`. Same `syn`
(coarse signature, block re-ordering): «the same syntax» is tightened by threshold, not by a new
signature, so the intra relation's measure is reused unchanged.

**D3 — Stage order and diagnostics.** syntax (σ, short-exact) → candidate cap → semantic gate →
`short_material` → shared-root → `syntax_cross` (σ_x) → `material` (κ) → top-K → relative cut. Both new
rules are applied as FILTERS after the semantic gate, not before the cap: applied earlier, `σ_x` would
shrink the syntax-survivor population that `dense` is ranked in, and so move `dense`, `sem` and the cap
for every pair — the calibration, which simulates the rules on the stored pairs' `syn` and coverage,
would then no longer predict the build. Applied late, every other value stays exactly as stored and the
calibration's prediction for a stored pair is exact (checked on the holdout after the build). The
relative cut runs AFTER the new rules, so a neighbour that only fell under `0.5 × best` because of a pair
now removed comes back — the only way the build can store a pair the previous build did not (counted
and reported). Each new stage is counted in `diagnostics`.

**D4 — Samples, drawn before any threshold is chosen.** `scripts/draw_cross_material_samples.py`,
model-free, seed fixed, reads the CURRENT `quran_similarity.json` (the population: every stored pair;
the new rules can only remove pairs, so a pair outside it can never be gained). Each pair gets its
coverage `L/c` and `syn`. Strata: coverage `[0, 0.25)`, `[0.25, 0.5)`, `[0.5, 1]` × syn `[σ, 0.85)`,
`[0.85, 1]` — six strata; 10 pairs per stratum for the CALIBRATION file
(`tests/eval/cross_material_calibration.json`) and 10 others for the HOLDOUT
(`tests/eval/cross_material_holdout.json`); a stratum with fewer than 20 pairs is split alternately
between the two in seeded order and its size reported. Excluded: every pair of
`quran_similarity_gold.json`, `quran_passages_gold.json`, `closeness_blind_v2.json`,
`closeness_blind_short.json`, and 2:10 / 39:26 (the pair that motivated the change must not choose nor
measure the rule; it is reported apart).

**D5 — Labelling.** Three independent labellers per file, each in a fresh context, shown the two
vocalized texts and the definition below, no score, no stratum, no `syn`, no coverage; label
`positive` / `negative` + one-line reason; majority of three; no majority → left out and counted. The
definition (both languages, stored in each file):

> Two verses of different surahs are CLOSE when they say the same thing, built the same way, with
> enough of the same lemmas — whatever their length. Pronoun suffixes, clitic particles (و ف ب ل ال)
> and function words do not count, and blocks may come in any order. A few shared words scattered
> through two otherwise different verses is NOT closeness, even when both verses speak of the same
> subject; and the same subject in another construction is NOT closeness. A short verse wholly
> contained in a longer one IS close.
>
> آيتان من سورتين مختلفتين «متقاربتان» إذا قالتا الشيء نفسه، بالبناء نفسه، بقدرٍ كافٍ من الألفاظ
> نفسها — طالتا أو قصرتا. لا تُحسب ضمائر الإضافة ولا الحروف المتصلة (و ف ب ل ال) ولا أدوات المعاني،
> ويجوز أي ترتيب للمقاطع. كلماتٌ قليلة مشتركة متفرقة في آيتين مختلفتين ليست تقاربًا، ولو كان موضوعهما
> واحدًا؛ والموضوع نفسه ببناء آخر ليس تقاربًا. والآية القصيرة الواردة بتمامها في آية أطول متقاربةٌ معها.

**D6 — Selection rule (registered now, before any label).** Grid: `σ_x ∈ {2/3, 0.75, 0.80, 0.85, 0.90,
1.0}`, `κ ∈ {0.20, 0.25, 0.33, 0.40, 0.50, 0.60}`. For each grid point, on the CALIBRATION labels:
`P` = positives that would stay stored, `N` = negatives that would stay stored (fractions of the labelled
positives / negatives). Keep the points with `N ≤ 0.15`; among them pick the highest `P`; ties → the
higher `κ`, then the higher `σ_x`. If no point has `N ≤ 0.15`, pick the lowest `N`, ties → highest `P`,
and record that the ceiling was not reached. The chosen pair is written into the build constants and
the header BEFORE the holdout is scored.

**D7 — Targets (registered now).** HOLDOUT: positives stored ≥ 0.70, negatives stored ≤ 0.20.
Non-regression, unchanged targets: `closeness_blind_v2` positives ≥ 0.65 / negatives ≤ 0.25;
`closeness_blind_short` positives ≥ 0.65 / negatives ≤ 0.25; cross T1 ≥ 0.65. Reported, no target:
pairs lost per new stage, the close-verses AUC(score), pair counts before/after (similarity only,
passage only, both), the fate of 2:10 / 39:26 and of 2:2 / 32:2, 2:2 / 3:138. A miss is recorded, never
tuned; no parameter changes after the holdout is read.

**D8 — One orange cue.** `GET /surah/{n}/annotations` returns `cross` (all pairs, score desc, ties
mushaf order) instead of `whole` + `passage`. Frontend: `markerCue.orange = cross.length > 0`;
`passageSpans` becomes `crossSpans` = union of every `spans_self`, on vocalized text only; legend two
entries; the orange marker keeps today's ring style; the bubble's «في سائر القرآن» list reads `cross`
unchanged in look. `quran_close_verses.json` schema is unchanged (`from` stays, for the map and audits).

## Risks / Trade-offs

- [Coverage counts frequent lemmas (الله، كان، قال) like rare ones] → a pair could reach `κ` on function-
  like lemmas. Measured by the holdout; if it misses, recorded and a follow-up decides (no list now).
- [Genuine pairs with root-only overlap (a verb and its maṣdar) lose material] → accepted, consistent
  with `short-verse-material`; the holdout positives measure the cost.
- [Labellers are models, as in v2] → three independent votes, majority; the user can audit the two
  files.
- [More āyāt get orange words: every whole-verse pair's common part is now coloured] → wanted; the
  material rule reduces whole-verse pairs at the same time.
- [The calibration sample is small (≈ 60)] → the selection rule is coarse by design (a 6 × 6 grid);
  the holdout, not the calibration, is the reported figure.

## Migration Plan

Draw both samples (D4) → label (D5) → apply D6 on calibration, write constants → implement D1–D3 (TDD)
→ stop the backend → rebuild `quran_similarity.json` → `quran_close_verses.json` (passages unchanged,
not rebuilt) → evaluations (D7) → record «Measured result» below → API + frontend (D8, TDD) → restart,
check sūra 2 and 28 in the browser. Rollback: the previous two JSON files are regenerable from the
previous commit's constants.

## Calibration (before the holdout was scored)

Recorded by task 2.2, after the CALIBRATION labels were read and before any holdout outcome was
computed. Nothing below was chosen from the holdout.

**Labels (D5).** Three independent fresh-context labellers per file, each shown only the two vocalized
texts and the definition (no score, stratum, `syn` or coverage); majority of three; every vote and its
reason is stored in the file (`votes[].labeller`, `label`, `reason`), with `labelling`, `label_counts`
and `no_majority` at the top level.

| file | pairs | positive | negative | no majority | unanimous |
|---|---|---|---|---|---|
| `cross_material_calibration.json` | 46 | 21 | 25 | 0 | 42 |
| `cross_material_holdout.json` | 45 | 22 | 23 | 0 | 43 |

(The holdout row is its label tally only — no stored / not-stored outcome was computed.)

**Grid (D6, `scripts/select_cross_material.py`, calibration only).** Kept = `syn ≥ σ_x` (tolerant of the
last bit) AND `L ≥ 2` AND `L / c ≥ κ`, on the stored pairs' `syn`, `L`, `c`. `P` = positives kept / 21,
`N` = negatives kept / 25; eligible = `N ≤ 0.15`.

| σ_x | κ | P | N | eligible |
|---|---|---|---|---|
| 2/3 | 0.20 | 0.952 (20/21) | 0.520 (13/25) | no |
| 2/3 | 0.25 | 0.952 (20/21) | 0.480 (12/25) | no |
| 2/3 | 0.33 | 0.952 (20/21) | 0.480 (12/25) | no |
| 2/3 | 0.40 | 0.905 (19/21) | 0.440 (11/25) | no |
| 2/3 | 0.50 | 0.714 (15/21) | 0.200 (5/25) | no |
| 2/3 | 0.60 | 0.667 (14/21) | 0.080 (2/25) | yes |
| 0.75 | 0.20 | 0.714 (15/21) | 0.120 (3/25) | yes |
| 0.75 | 0.25 | 0.714 (15/21) | 0.120 (3/25) | yes |
| **0.75** | **0.33** | **0.714 (15/21)** | **0.120 (3/25)** | **yes — chosen** |
| 0.75 | 0.40 | 0.667 (14/21) | 0.120 (3/25) | yes |
| 0.75 | 0.50 | 0.524 (11/21) | 0.080 (2/25) | yes |
| 0.75 | 0.60 | 0.524 (11/21) | 0.080 (2/25) | yes |
| 0.80 | 0.20 | 0.619 (13/21) | 0.080 (2/25) | yes |
| 0.80 | 0.25 | 0.619 (13/21) | 0.080 (2/25) | yes |
| 0.80 | 0.33 | 0.619 (13/21) | 0.080 (2/25) | yes |
| 0.80 | 0.40 | 0.619 (13/21) | 0.080 (2/25) | yes |
| 0.80 | 0.50 | 0.476 (10/21) | 0.040 (1/25) | yes |
| 0.80 | 0.60 | 0.476 (10/21) | 0.040 (1/25) | yes |
| 0.85 | 0.20 | 0.571 (12/21) | 0.080 (2/25) | yes |
| 0.85 | 0.25 | 0.571 (12/21) | 0.080 (2/25) | yes |
| 0.85 | 0.33 | 0.571 (12/21) | 0.080 (2/25) | yes |
| 0.85 | 0.40 | 0.571 (12/21) | 0.080 (2/25) | yes |
| 0.85 | 0.50 | 0.429 (9/21) | 0.040 (1/25) | yes |
| 0.85 | 0.60 | 0.429 (9/21) | 0.040 (1/25) | yes |
| 0.90 | 0.20 | 0.429 (9/21) | 0.040 (1/25) | yes |
| 0.90 | 0.25 | 0.429 (9/21) | 0.040 (1/25) | yes |
| 0.90 | 0.33 | 0.429 (9/21) | 0.040 (1/25) | yes |
| 0.90 | 0.40 | 0.429 (9/21) | 0.040 (1/25) | yes |
| 0.90 | 0.50 | 0.381 (8/21) | 0.000 (0/25) | yes |
| 0.90 | 0.60 | 0.381 (8/21) | 0.000 (0/25) | yes |
| 1.00 | 0.20 | 0.333 (7/21) | 0.040 (1/25) | yes |
| 1.00 | 0.25 | 0.333 (7/21) | 0.040 (1/25) | yes |
| 1.00 | 0.33 | 0.333 (7/21) | 0.040 (1/25) | yes |
| 1.00 | 0.40 | 0.333 (7/21) | 0.040 (1/25) | yes |
| 1.00 | 0.50 | 0.286 (6/21) | 0.000 (0/25) | yes |
| 1.00 | 0.60 | 0.286 (6/21) | 0.000 (0/25) | yes |

**Choice.** `σ_x = 0.75`, `κ = 0.33`: the highest `P` among the eligible points is 0.714, reached at
`σ_x = 0.75` with `κ ∈ {0.20, 0.25, 0.33}`; the tie goes to the higher `κ`. The ceiling `N ≤ 0.15` was
reached. Calibration (in-sample, not the reported figure): P 15/21, N 3/25. Written into
`scripts/build_quran_similarity.py` (`SIGMA_CROSS = 0.75`, `MATERIAL_MIN_COVERAGE = 0.33`,
`THRESHOLDS_CHOSEN = True`) before the holdout was scored; computed independently by the orchestrator
with the same result.

## Measured result

Recorded by task 4.3 after the rebuild (`build_quran_similarity.py` 436 s, then
`build_quran_close_verses.py` 192 s; passages not rebuilt; backend stopped). `σ_x = 0.75`, `κ = 0.33`
as chosen above — **no parameter was changed after these figures were read.** «Before» is the
previous `quran_similarity.json` / `quran_close_verses.json` (saved before the rebuild), measured
with the same eval scripts by pointing the loaders at the saved copies.

**Holdout (D7, the reported figure; `scripts/eval_cross_material.py`, both sample digests = header).**

| | stored | target | verdict |
|---|---|---|---|
| holdout positives | 16/22 = 0.727 | ≥ 0.70 | **PASS** |
| holdout negatives | 7/23 = 0.304 | ≤ 0.20 | **MISS** |
| calibration positives (in-sample, apart) | 15/21 = 0.714 | — | — |
| calibration negatives (in-sample, apart) | 3/25 = 0.120 | — | — |

The negative target is missed and stays missed (D7). The seven negatives still stored: 42:26/45:30,
3:189/39:62, 16:3/23:92, 25:35/40:53, 54:42/69:10, 79:15/85:17, 80:40/88:2. Four of them sit in one
stratum — coverage `[0.25, 0.5)` × syn `[0.85, 1]` — with `L = 2` and coverage 0.33–0.40, just above
`κ`: the shape of the risk recorded above (two shared lemmas, possibly frequent ones such as الله /
كل / شيء, reaching `κ`); which lemmas they are was not inspected per pair. The other three pass with
`syn` exactly 0.75 or 0.77. The six positives lost: 3:69/6:123 (syn 0.667 and coverage 0.25),
6:48/7:35 (syn 0.667), 6:154/28:43 (syn 0.706), 92:11/111:2 (syn 0.667 and `L = 1`), 2:157/31:5
(`L = 1`), 9:105/62:8 (syn 0.667, coverage 0.73) — three by the syntax rule alone, one by material
alone, two by both.

**Prediction vs actual.** The eval's own model-free prediction (`syn ≥ σ_x` and `material_ok`
recomputed from the corpus) matches the build on every labelled pair: 0 mismatches on the holdout,
0 on the calibration. The orchestrator's independent prediction for the 45 holdout pairs (from the
sample's `syn` / `L` / coverage) also matches all 45 outcomes and all 45 labels — D3's claim that the
late filters keep the calibration's prediction exact holds.

**Non-regression (D7 targets unchanged).**

| measure | before | after | target | verdict |
|---|---|---|---|---|
| `closeness_blind_v2` positives | 36/42 = 0.857 | 34/42 = 0.810 | ≥ 0.65 | PASS |
| `closeness_blind_v2` negatives | 2/18 = 0.111 | 2/18 = 0.111 | ≤ 0.25 | PASS |
| `closeness_blind_short` positives | 10/10 = 1.000 | 7/10 = 0.700 | ≥ 0.65 | PASS |
| `closeness_blind_short` negatives | 6/29 = 0.207 | 4/29 = 0.138 | ≤ 0.25 | PASS |
| cross T1 recall@10 | 50/53 = 0.943 | 42/53 = 0.792 | ≥ 0.65 | PASS |
| cross T2 (negatives in a top-3) | 3 | 3 | ≤ 4 | PASS |
| cross T3 (second-sample negatives) | 0/51 | 0/51 | ≤ 1 | PASS |
| cross T4 (second-sample positives) | 5/6 | 5/6 | ≥ 80 % of 7 | MISS (unchanged, was already a miss) |
| cross T5 (pre-filter losses) | 0 | 0 | = 0 | PASS |
| close verses AUC(score), no target | 0.752 (89 × 9) | 0.762 (87 × 9) | (U1 ≥ 0.8: MISS before and after) | — |
| U2 28:20/36:20 | present, 0.7838 | present, 0.7838 | | PASS |
| U3 26:203/37:54 | not present | not present | | MISS (unchanged) |

Blind v2 positives now dropped from the similarity relation: 23:13/77:21 and 33:45/48:8 (no longer
listed anywhere), 10:67/27:86 (kept as a passage). Short sample: positives 27:1/28:2, 37:73/43:25,
7:125/26:50 are gone; negatives 23:12/90:4 and 7:14/37:144 are gone. T1's eight losses are all at
`syntax_cross` (syn 0.667–0.727: 7:141/14:6, 3:184/35:25, 15:11/36:30, 9:32/61:8, 61:1/62:1,
26:177/37:124, 89:6/105:1, 3:10/58:17); `material` costs T1 nothing.

**Per-stage losses (capped pairs, `diagnostics.stage_losses`).** semantic_gate 19 709, short_material
787, no_shared_root 47, **syntax_cross 578**, **material 31** — out of 21 692 capped pairs. Of the
1 088 previously stored pairs, 562 are gone: 532 with `syn < 0.75` and 30 with `syn ≥ 0.75` (the
material rule); no stored pair has `syn < 0.75`.

**Re-entered through the relative cut (D3).** 2 pairs stored now and not before: 15:36/29:30
(s 0.1131) and 29:30/38:79 (s 0.1097), both similarity-only in the close verses.

**Pair counts.** `quran_similarity.json`: 1 088 → **528** distinct pairs (984 directed list
entries; the build log's «stored_pairs=540» sums its per-anchor-surah counts, which count a few pairs
twice). `quran_close_verses.json`:

| | before | after |
|---|---|---|
| similarity only | 803 | 346 |
| passage only | 2 593 | 2 696 |
| both | 285 | 182 |
| **total** | **3 681** | **3 224** |
| with a common part | 3 560 | 3 224 (all) |

The passage set is unchanged (2 878 = 2 593 + 285 = 2 696 + 182): 103 pairs moved from «both» to
«passage only», 459 similarity-only pairs left and 2 entered (103 + 459 = the 562 lost).

**Watched pairs.**
- **2:10 / 39:26 — still stored** (s 0.1984; syn 0.75, `L = 3`, `c = 9`, coverage 0.3333 ≥ 0.33). The
  pair that motivated the change passes both new rules by the smallest margin each allows; recorded,
  not tuned.
- **2:2 / 32:2 — stored** (s 0.2427; syn 0.75, `L = 2`, `c = 4`, coverage 0.5).
- **2:2 / 3:138 — dropped** (syn 0.7143 < 0.75; `L = 2`, coverage 0.5). Not present in the close
  verses any more (it had no passage).

## Follow-up: L ≥ 3 (user decision, 2026-10-09, after the holdout was read)

The holdout missed its negative target at `L ≥ 2` (7/23). The user then raised
`MATERIAL_MIN_LEMMAS` from 2 to 3, keeping `σ_x = 0.75` and `κ = 0.33`. **This choice was made after
the holdout was read, so every figure below is in-sample for it** — a fresh blind sample would be
needed for an out-of-sample figure. Rebuilt `quran_similarity.json` → `quran_close_verses.json`
(passages unchanged); the L ≥ 2 files are kept in the session scratchpad (`prev_L2/`).

| measure | L ≥ 2 | **L ≥ 3** | target | |
|---|---|---|---|---|
| holdout positives stored | 16/22 = 0.727 | **10/22 = 0.455** | ≥ 0.70 | **MISS** |
| holdout negatives stored | 7/23 = 0.304 | **1/23 = 0.043** | ≤ 0.20 | PASS |
| calibration positives / negatives | 15/21, 3/25 | 6/21, 1/25 | — | — |
| `closeness_blind_v2` positives / negatives | 34/42, 2/18 | 34/42, 2/18 | ≥ 0.65 / ≤ 0.25 | PASS |
| cross T1 recall@10 | 42/53 = 0.792 | 34/53 = 0.642 | ≥ 0.65 | **MISS** |
| cross T2 / T3 / T4 / T5 | 3 / 0 / 5 of 6 / 0 | 1 / 0 / 4 of 6 / 0 | ≤ 4 / ≤ 1 / ≥ 80 % / 0 | PASS / PASS / MISS / PASS |
| close verses AUC(score) | 0.762 (87 × 9) | 0.885 (78 × 5) | (U1 ≥ 0.80) | PASS |
| predicted vs actual (both samples) | 0 mismatches | 0 mismatches | | |

Per-stage losses: `material` 31 → 270 capped pairs. `quran_similarity.json`: 528 → **296** distinct
pairs (232 lost, 0 gained). `quran_close_verses.json`: 3 224 → **2 992** pairs — similarity only 114,
passage only 2 696, both 182; common part on all.

**Watched pairs.** 2:10 / 39:26 is **still stored** (`L = 3`, `c = 9`, coverage 0.3333, `syn` 0.75 —
it meets every threshold exactly, and two of its three lemmas are الله and كان). 2:2 / 32:2 and
2:2 / 3:138 are dropped (`L = 2`). Reading: L ≥ 3 trades recall for precision — negatives almost
vanish, but over half the labelled positives go with them, and the motivating pair is the one class
it does not reach (three lemmas, two of them very frequent).

## Follow-up: weighted coverage (user decision, 2026-10-09) — the current state

`L ≥ 3` reverted to **`L ≥ 2`**, and the coverage made **IDF-weighted**
(`closeness_core.weighted_coverage`): for each verse, `Σ idf(root)` over its words joined by a `lemma`
edge ÷ `Σ idf(root)` over its content words (the `lex` weights); the larger of the two ratios. Re-chosen
by the unchanged D6 rule on the unchanged calibration labels (`scripts/select_cross_material.py`):
**`σ_x = 2/3` (= σ — the cross syntax rule adds nothing), `κ = 0.40`**, P = 16/21, N = 3/25. The holdout
had been read for the first choice, so its figure below is **not blind**.

| measure | before the change | count `L/c` (κ 0.33, σ_x 0.75) | **weighted (κ 0.40, σ_x 2/3)** | target | |
|---|---|---|---|---|---|
| holdout positives stored | — | 16/22 | **17/22 = 0.773** | ≥ 0.70 | PASS |
| holdout negatives stored | — | 7/23 | **3/23 = 0.130** | ≤ 0.20 | PASS |
| `closeness_blind_v2` positives / negatives | 36/42, 2/18 | 34/42, 2/18 | **36/42, 2/18** | ≥ 0.65 / ≤ 0.25 | PASS |
| cross T1 recall@10 | 50/53 | 42/53 | **50/53 = 0.943** | ≥ 0.65 | PASS |
| cross T2 / T3 / T4 / T5 | 3 / 0 / 5 of 6 / 0 | 3 / 0 / 5 of 6 / 0 | 2 / 0 / 5 of 6 / 0 | ≤ 4 / ≤ 1 / ≥ 80 % / 0 | T4 MISS (unchanged) |
| close verses AUC(score) | 0.752 (89 × 9) | 0.762 (87 × 9) | **0.721 (89 × 8)** | U1 ≥ 0.80 | MISS (was already) |
| predicted vs actual, both samples | | 0 | **0** | | |

Stage losses: `syntax_cross` 0, `material` 362 capped pairs. `quran_similarity.json`: **759** distinct
pairs (1 088 before the change). `quran_close_verses.json`: **3 362** pairs — similarity only 484,
passage only 2 603, both 275 (3 681 before the change).

**Watched pairs.** **2:10 / 39:26 dropped** — weighted coverage 0.178 (الله 1.20, كان 1.67, عذاب
2.92 over nine content words). **2:2 / 32:2 stored** (0.564: ريب weighs 5.18). **2:2 / 3:138 stored**
(0.436). The motivating pair is gone and the two pairs the user expected to see in orange are back —
noted as the reason the weighting was chosen, not as a measurement.

**What stays open.** The holdout is in-sample for this choice; a fresh blind sample is the only
out-of-sample figure. The «same syntax» part of the definition is not tightened: D6 picks `σ_x = σ`.
The close-verses AUC fell under its (already missed) U1 target.
