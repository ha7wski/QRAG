## 1. Samples (before any threshold is chosen)

- [x] 1.1 Write `scripts/draw_cross_material_samples.py` (D4): population = current `quran_similarity.json` pairs, coverage `L/c` and `syn` per pair, six strata, seeded draw, exclusions (four gold/blind files + 2:10/39:26), definition (D5, both languages) stored in each file; print stratum sizes
- [x] 1.2 Run it; commit `tests/eval/cross_material_calibration.json` and `tests/eval/cross_material_holdout.json` with `label: null`; assert disjointness
- [x] 1.3 Label both files: three independent fresh-context labellers per file, texts + definition only, majority of three; record vote counts and left-out pairs

## 2. Choose the thresholds (calibration only)

- [x] 2.1 Write the D6 selection script over the calibration labels (grid, `N ≤ 0.15`, tie rules); print the full grid table
- [x] 2.2 Write the chosen `σ_x` and `κ` into the cross build's constants and set `THRESHOLDS_CHOSEN = True` (the build refuses to store pairs until then); record the grid table and the choice in `design.md` before the holdout is scored

## 3. Material and syntax rules (TDD)

- [x] 3.1 Tests for `closeness_core.material_ok` (lemma edges only, `L ≥ 2`, `L/c ≥ κ`, shorter verse's content count, short verse contained in a long one passes)
- [x] 3.2 Implement `material_ok`; `short_material_ok` unchanged
- [x] 3.3 `build_quran_similarity.py`: `syntax_cross` and `material` stages in D3 order, relative cut after them, diagnostics per stage, header `sigma_cross`, `material_min_coverage`, both sample digests; intra build untouched (its params digest unchanged)
- [x] 3.4 `eval_quran_similarity.py`: report losses at the two new stages; new `scripts/eval_cross_material.py` scoring the holdout (and calibration apart), refusing a sample whose digest differs from the header

## 4. Rebuild and measure

- [x] 4.1 Stop the backend; rebuild `quran_similarity.json`, then `quran_close_verses.json` (passages not rebuilt)
- [x] 4.2 Run the holdout eval, `eval_closeness_blind.py` (v2 and short), `eval_quran_similarity.py`, `eval_quran_close_verses.py`
- [x] 4.3 Fill «Measured result» in `design.md`: holdout vs D7 targets, non-regression, per-stage losses, pair counts before/after, fate of 2:10/39:26, 2:2/32:2, 2:2/3:138 — no parameter change after reading it

## 5. One orange cue — API (TDD)

- [x] 5.1 Update route tests: one `cross` list (score desc, mushaf ties), no `whole`/`passage`, 28:20 holds 36:20, 2:3/14:31 spans
- [x] 5.2 `api/models/surah_annotations.py` + `api/routers/surah_annotations.py`: replace `whole`/`passage` by `cross`

## 6. One orange cue — frontend (TDD)

- [x] 6.1 Update `annotations.test.ts`: `markerCue.orange` from `cross`, `crossSpans` = union of every `spans_self`, vocalized only, pair without common part = marker only
- [x] 6.2 `lib/api.ts` types, `lib/annotations.ts` (`crossSpans`, `crossPartners` over `cross`), `SurahReader.tsx` (marker orange + orange words for every pair; two-entry legend), `CloseVersesBubble.tsx`, `lib/strings.ts` (drop «جزء مشترك في سائر القرآن»)
- [x] 6.3 `npx vitest run` and `npx tsc --noEmit -p tsconfig.test.json` pass

## 7. Verify and document

- [ ] 7.1 `python -m pytest -q` passes (incl. served-surface and dataset-registry guards)
- [ ] 7.2 Restart the app; check sūra 2 (2:2 marker + common-part words, 2:10) and sūra 28 (28:20) in the browser
- [ ] 7.3 Update `CLAUDE.md` (pair counts, cross-only rules, the single orange cue, route shape) and `quran_data/manifest.py` notes if they cite counts
