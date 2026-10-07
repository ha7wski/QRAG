## Context

After `order-invariant-closeness`, a pair is stored when it passes the syntax gate (coarse element,
blocks re-orderable, σ = 2/3), the semantic gate (`sem ≥ τ_sem`, `lex` from the order-invariant
matching) and the matched-mass rule (`Mw > 0`). For a verse of 3–5 words the coarse mould alone often
reaches σ, and one shared lemma gives `Mw > 0`; the semantic gate is the only remaining filter, and the
cross-encoder rates formulaic short verses as close (69:3/83:19). Measured (in-sample): 9 negatives in a
top-3 against a target of ≤ 4.

## Goals / Non-Goals

**Goals:** drop single-lemma pairs of short verses; keep every frozen value; measure on a sample drawn
for this class before the build.

**Non-Goals:** changing σ, `τ_sem`, weights, the short-exact rule (≤ 3 elements needs `syn = 1`, which
stays), passages, the display.

## Decisions

**D1 — The rule.** Let `n = min(nA, nB)` (QAC words) and `L` = the number of `lemma` content edges of
the pair's matching (closeness_core D2). A pair with `n ≤ SHORT_MATERIAL_MAX_LEN = 5` is stored only
when `L ≥ SHORT_MATERIAL_MIN_LEMMAS = 2`. Root-only edges (`root`, weight 0.5) do not count: the user
asked for shared lemmas. Applied where the matched-mass rule is applied (intra neighbours and groups,
cross neighbours), AFTER the semantic gate, as its own stage `short_material` in the diagnostics. Pure
function `short_material_ok(edges, na, nb)` in `closeness_core`, imported by both builds. Headers name
`short_material_max_len` and `short_material_min_lemmas`.

**D2 — Measurement, registered before the draw and the build.**
- *Short blind sample* (`tests/eval/closeness_blind_short.json`): 40 cross-surah pairs drawn model-free
  with a fixed seed, no gate, excluding every pair of the existing gold and blind files; population =
  pairs whose shorter verse has ≤ 5 QAC words, whose longer verse has ≤ 10, sharing ≥ 1 content lemma,
  and passing the SYNTAX gate (model-free: coarse signature, σ, short-exact rule) — the class the rule
  targets, «same mould»; neither the semantic gate nor the rule itself is applied (a first draw without
  the syntax condition was discarded unlabelled: 133 277 of its 1-lemma pairs were unrelated verses the
  relation already rejects, which would have measured nothing);
  20 with exactly 1 shared content lemma, 20 with ≥ 2. Labelled from the written definition and the
  texts only, in a fresh context, before the build. The SAME definition text as `closeness_blind_v2`.
- Targets on the short sample (the rule's own figure): **negatives stored ≤ 0.25**; **positives stored
  ≥ 0.65**. The positives of the 1-lemma stratum, all dropped by construction, are reported apart as
  the rule's recall cost.
- Non-regression on `closeness_blind_v2`: positives stored ≥ 0.65, negatives ≤ 0.25 (unchanged targets).
- In-sample (relabelled gold): cross T2 ≤ 4; intra and cross T1 ≥ 0.75 / 0.65; U1 AUC ≥ 0.80.
- A miss is recorded, never tuned.

## Risks / Trade-offs

- [Genuine short refrains differing by one content word are dropped — «ثُمَّ أَغْرَقْنَا / دَمَّرْنَا
  الْآخَرِينَ», «فِيهِمَا عَيْنَانِ تَجْرِيَانِ / نَضَّاخَتَانِ»] → accepted by the user's rule; the cost is
  measured on the 1-lemma stratum and in the intra recall.
- [Verbatim short refrains are unaffected] → they share all their lemmas (55:13/55:16: 3 lemmas).

## Migration Plan

Draw + label the short sample → implement D1 (TDD) → stop the backend → rebuild intra → cross → close
verses → evals → record under «Measured result» → restart.

## Measured result (rebuild 2026-10-07, intra → cross → close verses)

No parameter changed after the build. Cross close pairs 3 681 (4 148 before; similarity-only 803, was 1 270).

| Eval | Target | Before the rule | Measured | |
|---|---|---|---|---|
| **short blind** negatives stored | ≤ 0.25 | — | 6/29 = 0.207 (all six in the ≥ 2-lemma stratum) | PASS |
| **short blind** positives stored, all positives | ≥ 0.65 | — | 10/11 = 0.909 | PASS |
| short blind — 1-lemma stratum (the rule's own class) | reported | — | positives 0/1 stored (37:27/68:30, the recall cost), negatives 0/19 | — |
| blind v2 positives / negatives | ≥ 0.65 / ≤ 0.25 | 36/42, 2/18 | 36/42, 2/18 | PASS |
| intra recall@10 | ≥ 0.75 | 49/50 | 42/50 = 0.840 (7 lost at `short_material`: 55:50/66, 26:66/172, 26:66/120, 37:109/120, 37:123/133 …) | PASS |
| intra negatives in a top-3 | ≤ 2 | 2 | 1 | PASS |
| cross T1 | ≥ 0.65 | 52/53 | 50/53 | PASS |
| cross T2 negatives in a top-3 | ≤ 4 | 9 | **3** | PASS |
| cross T3 | ≤ 1 | 2 | 0 | PASS |
| cross T4 | ≥ 80 % of 7 | 5/6 | 5/6 | MISS (unchanged, by the formula) |
| close verses U1 AUC(score) | ≥ 0.80 | 0.875 | **0.752** (89 × 9) | **MISS** |
| close verses U3 26:203/37:54 | `pas` 0, last of its cell | rank 16 of 33 | no longer stored at all | MISS by the eval's letter (absent) — the frame-only pair the rule was written for is gone |

**Reading.** The rule does what it was meant to: the blind short sample's 1-lemma stratum stores 0 of
its 19 negatives, cross T2 falls from 9 to 3, T3 from 2 to 0. Its cost is the short refrains that differ
by one content word — «سَلَامٌ عَلَىٰ X», «ثُمَّ أَغْرَقْنَا / دَمَّرْنَا الْآخَرِينَ», «فِيهِمَا عَيْنَانِ X» —
which the relabelled gold keeps positive under its slot-fill convention: they leave the lists (intra
recall 49 → 42) and, absent, rank below every negative in the close-verses AUC (0.875 → 0.752).
The remaining stored short negatives (6/29) are 2-lemma moulds the rule does not reach (51:12/75:6,
75:22/88:2). Recorded; not tuned.
