## 0. Harness extraction (no data read or written)

- [x] 0.1 Capture golden output: full stdout of `python scripts/validate_concept_datasets.py` and of `python scripts/record_concept_verdicts.py worksheet`, into the scratchpad
- [x] 0.2 Create `linguistics/lisan/harness/{__init__,draw,guard,verdicts}.py` with the table-agnostic code moved out of `concept/confront.py`, `concept/witness_guard.py` and the two `*_concept_*` scripts; `guard.py` parametrised by a holdout loader
- [x] 0.3 Rewire the closed engine and its two scripts onto `harness/`; keep every public name they exported
- [x] 0.4 Re-run 0.1's commands and diff byte-for-byte; run the full closed test suite unchanged. Any diff → revert, do not adjust
- [x] 0.5 Add `harness/` to `tests/test_import_direction.py` and `tests/test_module_root_depth.py`; commit

## 1. Second holdout (before any row is transcribed)

- [x] 1.1 Add `ISLAMBOULI_WITNESS_SET_JSON` to `quran_data/paths.py`, its `manifest.py` entry and loader
- [x] 1.2 Write `scripts/draw_islambouli_witness_set.py` on `harness/draw.py`: pinned exclusions, assert frame 280 = 205 + 75, assert seed `20260925` reproduces the burned 40, remove them, assert 176 + 64, draw 29 + 11 on one `Random(20260928)`, lower first, sorted lists
- [x] 1.3 Run it once; write the file with seed, rationale, date, procedure, frame, strata and the recorded structure (weak radicals, hamza carriers, bare alef, overlap with probe roots / widening / `ضرب`)
- [x] 1.4 Validator replay + tests (`test_islambouli_witness_set.py`): reproducibility, no burned root, file tamper fails
- [x] 1.5 Commit the set and its replay — **no Islambouli file in this commit or any ancestor**

## 2. Transcription

- [x] 2.0 **Gate:** replace the truncated deposit at `data/source/islambouli_letters_poster.png` with the original (1132×1646, sha256 `e64906b3…abcac0c`); read the title band, banner and footer at 3× on it
- [x] 2.1 Add the CSV and lock paths + manifest entries (the poster as a `source/` original with its sha256)
- [x] 2.2 Transcribe the 29 rows from the image into `islambouli_letters.csv` (`row`, `label_as_printed`, `text_as_printed`, `text`, `status`, `reading_note`), re-checking every row at 3× crop; row 12 without shadda/tanween and with its `reading_note`
- [x] 2.3 Validator: 29 rows 0–28; whitespace-stripped identity per row; status only `transcribed_from_poster`; row 26 label «آ - ى», row 25 «هـ»; no field relating row 0 to row 26
- [x] 2.4 Commit the transcription (git ancestry check: 1.5 precedes)

## 3. System check (before any root)

- [x] 3.1 Write `islambouli_letters_grid.json` by the D11 parsing rules (formula excluded, split on «،»/«أو», nearest-noun attachment, row 0's «خفيف» on «صوت»)
- [x] 3.2 Validator: C1 substring check on every slot, C2 residue list, C3 same-form contradictions + root-level observations, C4 discrimination; H1–H4 each `holds`/`fails` with deciding rows; recompute the verdict and fail on mismatch
- [x] 3.3 Publish the grid and its verdict (in the doc draft) and commit

## 4. Freeze

- [x] 4.1 Write `islambouli_letters.lock.json` v1.0.0: `frozen_on`, sha256 of the CSV bytes, `history[0].source` with authority, witness + sha256, `witness_origin`, `witness_imprint` (title band, banner, footer, top edge — as read in 2.0), `pages: []`, `attribution_basis` naming the imprint
- [x] 4.2 Validator: CSV digest match; witness file digest match; imprint entries with identity check, banner non-empty, empty entries noted; refuse `attested` and non-empty `pages`; refuse a history reason that cites a root, a use or `k`
- [x] 4.3 Commit the lock

## 5. Composer, blindness and guard

- [x] 5.1 Write the blindness rules for `linguistics/lisan/islambouli/` into `tests/test_import_direction.py` first (banned names incl. the grid for every module, `confront.py` exemption for the meaning layer only, `harness/verdicts.py` banned from the composer)
- [x] 5.2 `islambouli/compose.py`: load + digest-check the table, D5 letter mapping (carrier table imported from the closed harness), three verbatim positions, quadriliteral refusal, partial path; guard call on its first line
- [x] 5.3 Tests on roots off both holdouts: verbatim bytes, «أو» kept whole, `اول` → row 26, no partial over all triliteral QAC roots, partial on a synthetic key, quadriliteral refusal
- [x] 5.4 Guard tests: a new-witness root raises under pytest; empty holdout raises; the closed guard still covers its own 40
- [x] 5.5 Commit

## 6. Uses freeze (no reading generated)

- [x] 6.1 Add `islambouli_attestation.json` path, manifest entry, loader; meta carrying the ordering, the inherited criterion verbatim, the two D7 applications, and who wrote the uses and what they had read (per the answer to Open Question 1)
- [x] 6.2 Build the inline input bundle (procedure, 40 roots + `ضرب`, occurrences, Maqāyīs verbatim); dispatch the blind, tool-free sub-agent; store its prompt and raw output in the meta
- [x] 6.2b Record the 40 roots' uses from that output (verse-membership check only; failures recorded, not hand-repaired); copy `ضرب`'s five reference uses unchanged and store the blind ones as `uses_blind`
- [x] 6.2c Match `ضرب` reference ↔ blind uses with reasons, before any `ضرب` reading is looked at; compute the concordance verdict by the fixed rule
- [x] 6.3 Validator: every verse belongs to its root; all verdicts `not_judged`; `ضرب` identical across files; no reading recorded
- [x] 6.4 Commit the frozen uses

## 7. Generate, judge, compute

- [x] 7.1 `islambouli/confront.py` (reads the result, never imported back) and `scripts/record_islambouli_verdicts.py` (`worksheet`, `record`, `collisions`) on `harness/verdicts.py`, taking the sanctioned guard context
- [x] 7.2 Generate and record the 41 readings with lock version + sha256 and `reading_recorded_at`; commit before judging
- [x] 7.3 Judge every use under the criterion, including `ضرب`'s `uses_blind` (counted nowhere); each miss reason starts with its class; commit
- [x] 7.4 Compute `collision` after the verdicts over all triliteral roots; commit

## 8. Publish

- [x] 8.1 `scripts/validate_islambouli_datasets.py`: `k / 40`, `0 / 40` read from the closed record, covered-use counts, class distributions for both, inherited signature split, grid verdict and its meaning, R1–R6 in the same block, and the `ضرب` calibration table; no literal `0 / 40` in source
- [x] 8.2 `documentation/lisan-islambouli-table.md` (English): result first with reservations, the transcription check table, the grid, the protocol and its order, the scope statement
- [x] 8.3 One-line pointer in `documentation/lisan-concept-from-physics.md` §0; update `CLAUDE.md`'s `linguistics/` section and `scripts/README.md`
- [x] 8.4 Full `pytest -q`; re-run the closed validator and confirm it still prints `k / 40 = 0` unchanged; commit
