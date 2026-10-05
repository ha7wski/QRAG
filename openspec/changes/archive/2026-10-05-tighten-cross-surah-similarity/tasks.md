## 1. Freeze before measuring

- [x] 1.1 Freeze A (dense among syntax survivors), B (`short_exact_max_len = 3`), C (`ρ = 0.5`) and targets T1–T5 in design.md, before any sample is labelled or any rebuild
- [x] 1.2 Draw the v2 sample (seed 20261005, 60 pairs from the `σ` survivors, excluding v1 pairs and 26:203/37:54, 26:70/37:124, 26:115/37:15)
- [x] 1.3 Label it with three independent blind labellers (texts only), keep 2-of-3 majorities, append to the gold file as version 2 with `sample: "v2-syntax-survivors"`; record the sha256 and the dropped count here
- [x] 1.4 Compute the T3/T4 baseline on the CURRENT dataset (v2 negatives and positives stored) and write it here, before the rebuild

  **Recorded before the rebuild.** The σ population holds 2 257 pairs (1 316 once B applies). Gold
  version 2: 143 pairs, sha256 `e1acf7805c6a31152ac467c3d7cd5e190ebe18dfedefd10ef00c76251805971b`; the
  second sample keeps 57 of 60 (49 unanimous): 17 positive, 36 neg_same_syntax_diff_subject, 4
  neg_diff_subject_diff_syntax; dropped 101:7/104:9 and 88:12/101:11 (ambiguous ×3), 18:3/56:16 (no
  majority). **Baseline on the current dataset**: v2 negatives stored **2 / 40** (83:19/101:3,
  77:14/83:8 — both «وَمَا أَدْرَاكَ مَا»), v2 positives stored **7 / 17**. Hence T3: ≤ 1 negative
  stored; T4: ≥ 6 positives stored (80 % of 7 = 5.6). Note, recorded now: a random draw from the σ
  survivors is mostly pairs sharing no content root, which the shared-root rule already refuses, so the
  sample measures the motivating defect only weakly.

## 2. Build

- [x] 2.1 B: short-pair rule after `σ` in the syntax stage; gold stage `short_exact`
- [x] 2.2 A: dense percentile over the syntax survivors; header `dense_population: "syntax-survivors"`
- [x] 2.3 C: relative cut after `select_neighbours`; gold stage `relative_cut`; header `rho`, `short_exact_max_len`
- [x] 2.4 Tests for the three rules (pure functions) and the header

## 3. Evaluate

- [x] 3.1 Eval: new stages, v2 sample reported apart, T1–T5 printed
- [x] 3.2 Rebuild with the backend stopped; run the eval once; record T1–T5 here as the result

  **Result (2026-10-05, one run, gold sha256 `e1acf780…`).** Syntax: 2 257 pass `σ` → 1 316 pass the
  short-pair rule; 1 316 cross-encoded → 463 stored; 619 verses with neighbours. Map: 605 → **451**
  verse pairs, 351 → **286** cells, 97 → **96** surahs, darkest cell unchanged (53 × 55 = 31).
  Dense is now spread: 4 % of stored non-verbatim entries at ≥ 0.95 (was 590 / 605).
  - **T1** recall@10 41 / 60 = 0.683 ≥ 0.65 — PASS (was 44: 3 lost to `short_exact`; 14 syntax-gate
    losses unchanged, so the first build's ≤ 20 % candidate-loss line still reads MISS, as before).
  - **T2** first-sample negatives in a top-3: 3 ≤ 4 — PASS (4 / 13 same-syntax negatives still stored).
  - **T3** second-sample negatives stored: 0 / 40 ≤ 1 — PASS (24 stop at `short_exact`, 15 at the
    semantic gate, 1 at the relative cut).
  - **T4** second-sample positives stored: 6 / 17 ≥ 6 — PASS (24:42/57:5 etc. kept; 77:8/81:2 lost to
    `short_exact`).
  - **T5** pre-filter loss 0 — PASS.
  Of the three reported pairs, 26:70/37:124 and 26:115/37:15 are gone; **26:203/37:54 stays**: four
  words each (B does not apply) and the cross-encoder itself scores it 0.76. 75:1/90:1 (gold negative,
  `ce` 0.09) also stays, at `sem` 0.129 against `τ_sem` 0.125. Recorded, not tuned.
- [x] 3.3 Adversarial review of the build/eval changes
- [x] 3.4 Docs (CLAUDE.md, manifest note if needed), full test suites, restart the app, check the map
