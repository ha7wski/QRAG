## 1. Axis vocabulary and dataset registry

- [x] 1.1 Draft `data/references/semantic_axes.json`: closed list of axes, each `{id, label_ar, antonym?}`; seed it from the aṣl of the regression roots (خير، خبث، كفر، ظلم، رحم) and the letters they use; target 30–60 axes
- [x] 1.2 Add `SEMANTIC_AXES_JSON`, `ROOT_CORES_JSON`, `LETTER_SENSES_CSV` constants to `quran_data/paths.py` (bucket `references`)
- [x] 1.3 Add one cached loader per new dataset to `quran_data/loaders.py`
- [x] 1.4 Add a `quran_data/manifest.py` entry per new dataset (what / origin / producer / consumers / regenerable) and update the `ARABIC_LETTERS_CSV` entry for its reduced columns
- [x] 1.5 Verify `python -m pytest tests/test_quran_data.py -q` passes (every constant has an entry, every entry names a real constant and real consumers)

## 2. Dataset validator

- [x] 2.1 Write the validator (script + pytest) for `semantic_axes.json`: unique ids, symmetric `antonym` links, no dangling reference
- [x] 2.2 Extend it to `root_cores.json`: every key is a canonical QAC root key, `verbatim` matches its `maqayis_asl.csv` segment byte-for-byte, `axes` non-empty and all ids known, `polarity` ∈ {positive, negative, neutral}, no entry for a `no_asl` / `parse_uncertain` root
- [x] 2.3 Extend it to `letter_senses.csv`: ≥1 sense per base letter, `sense_id` unique per letter, all axis ids known, `pole` and `position` in their enums, non-empty `source` **and** `page`
- [x] 2.4 Make the validator report curated-core coverage (count and share of the 1 656 QAC roots) and assert the figure is reproducible from the shipped files alone

## 3. Seed the cores

- [x] 3.1 Write `scripts/build_root_cores_seed.py`: for each QAC root key, fold with `normalize_root` to find the Maqāyīs row, and emit an entry keyed on the **canonical** spelling with `verbatim`, `source`, `edition`, empty `axes`, null `polarity`
- [x] 3.2 Split multi-aṣl rows on `ASL_DELIM` into a list of cores, preserving order (ظلم → 2)
- [x] 3.3 Make re-running the script non-destructive: existing curated `axes` / `polarity` are preserved, only missing entries are added
- [x] 3.4 Skip `no_asl` and `parse_uncertain` rows; log how many roots were skipped and why
- [x] 3.5 Document the script in `scripts/README.md`

## 4. Curate the regression dataset

- [x] 4.1 Curate axes + polarity for `خير` (neutral, ميل/عطف), `خبث` (negative, خلاف الطيب), `كفر` (neutral, ستر/تغطية), `ظلم` (two cores), `رحم` (positive)
- [x] 4.2 Curate `letter_senses.csv` for every letter of those roots (خ ي ر ب ث ك ف ظ ل م ح) — N sourced senses each, with `gloss_ar`, `pole`, `axes`, `position`, `gesture_ar`, `source`, `page`, `confidence`
- [x] 4.3 Ensure `خ` carries **both** a خشونة/خواء sense and a ميل/انعطاف sense, each independently sourced to a letter-level authority (not authored to fit a root)
  - **Deviation, deliberate:** `خ` carries three sourced senses (خسة/قذارة negative، قطع/شدخ neutral، رقة/نضارة non-negative), so the opposed pair the mechanism needs is there. But NO letter-level authority attributes **ميل** to `خ` — Ḥasan ʿAbbās gives the softened خاء «الرقة والنضارة» (p. 173-179). Authoring a ميل sense for `خ` to make `خ-ي-ر` match would be exactly the circular curation R1 forbids, so it was not done. The core cites «العطف **و**الميل»; the match lands on `atf`, the half attested on both sides. See §7 of `documentation/lisan-constrained-reading.md`.
- [x] 4.4 Run the validator; the curated subset must pass with zero findings

## 5. Letter dataset refonte

- [x] 5.1 Drop `abbas_meaning*` and `abbas_keywords*` from `data/references/arabic_letters_dataset.csv`, keeping its 28 identity + phonetics rows
- [x] 5.2 Rework `linguistics/lisan/letter_lexicon.py` to expose a letter's senses as a list joined to its phonetic row; keep hamza-seat folding and the neutral placeholder for absent letters
- [x] 5.3 Confirm the lexicon never ranks, prefers or defaults a sense (selection belongs to the caller)
- [x] 5.4 Confirm `linguistics/tahlil/huruf.py` and `arabic_letter_semantics_hasan_abbas.json` are untouched

## 6. Selection engine (pure)

- [x] 6.1 Write `linguistics/lisan/sense_selection.py`: eligibility (≥1 shared axis, 0 antonym-conflicting axes) then ranking by `(shared axes, position fit, confidence rank, −declaration index)`
- [x] 6.2 Return per letter: `selected` (or null), `matched_axes`, `selection_rule` ∈ {axis-match, axis-match+position, unmatched}, and `discarded` with reason ∈ {no-shared-axis, conflicting-axis, outranked}
- [x] 6.3 Compute the letter's position in the root (initial / medial / final) and feed the position-fit term
- [x] 6.4 Implement the divergence guard as a **read-only** function over the completed selection; assert in tests that it returns the selection unchanged
- [x] 6.5 Unit-test the module on hand-built inputs only — no disk, no dataset, no network

## 7. Root core store

- [x] 7.1 Write `linguistics/lisan/root_core_store.py`: cached, offline lookup keyed on the canonical root key, modelled on `linguistics/madar/maqayis_store.py`
- [x] 7.2 Canonicalize every incoming root through `LexicalRetriever._canon` before indexing the map; add the geminate orthographic variants (`اب` ↔ `ابب`)
- [x] 7.3 Return an empty list — never a placeholder core — for a root absent from the dataset

## 8. Pipeline and API

- [x] 8.1 Rewrite `linguistics/lisan/synthesis_template.py` to compose from *selected* senses plus the core, to skip `unmatched` letters entirely, and to emit nothing when unconstrained
- [x] 8.2 Reorchestrate `linguistics/lisan/lisan_service.py`: root → cores → one selection pass per core → synthesis per core → guard per core
- [x] 8.3 Implement the no-core path: `constrained: false`, Arabic `warning`, empty `synthesis`, senses returned as an unselected inventory; delete the old concatenation with no flag restoring it
- [x] 8.4 Update `api/models/lisan.py`: `cores`, `readings[]` (per-core letters / synthesis / divergence), `constrained`, `warning`; remove `sequential_reading` and the single `letters[].meaning`
- [x] 8.5 Keep `api/routers/lisan.py` behaviour: 422 on empty / non-Arabic input, 200 with `root: null` + Arabic `message` when nothing resolves
- [x] 8.6 Verify `python -m pytest tests/test_served_surface.py tests/test_import_direction.py tests/test_module_root_depth.py -q` passes

## 9. Frontend

- [x] 9.1 Update `frontend/src/lib/lisanTypes.ts` to the new response shape
- [x] 9.2 Render the core(s) in `LisanResult.tsx`: gloss, verbatim aṣl, source, polarity — as a citation, above the letters
- [x] 9.3 Per letter: show the selected sense with its matched axes; add a collapsed «معانٍ أخرى للحرف لم تُعتمد هنا» section listing the discarded senses with their reason
- [x] 9.4 Render the unconstrained warning banner and the divergence banner as two visually distinct states
- [x] 9.5 Render multi-core roots as parallel readings, first expanded, each naming its aṣl
- [x] 9.6 Move new Arabic UI strings into `frontend/src/lib/strings.ts` (no Arabic literals in components)
- [x] 9.7 Update `LisanResult.test.tsx` and `app/lexical/page.test.tsx`; run `npx vitest run` and `npx tsc --noEmit -p tsconfig.test.json`

## 10. Regression battery

- [x] 10.1 `خير`: reading built on «أصله العطف والميل»; `خ` selects a ميل/انعطاف sense; synthesis contains none of قذارة، خشونة، خواء، فساد
- [x] 10.2 `خبث`: reading built on «خلاف الطيب»; `خ` selects a negative-pole sense
- [x] 10.3 Minimal pair: assert the sense selected for `خ` **differs** between خير and خبث, each sharing an axis with its own core
- [x] 10.4 `كفر`: selection lands on ستر/تغطية/إخفاء; no positive evaluation asserted; not forced negative either
- [x] 10.5 `ظلم`: two readings, one per aṣl, no pooled axes
- [x] 10.6 An uncovered root: `constrained` false, warning present, empty synthesis, senses returned unselected
- [x] 10.7 Synthetic contradiction: the guard fires and leaves the selection byte-identical
- [x] 10.8 Determinism: same word twice in-process and once in a fresh process yields identical selections

## 11. Documentation

- [x] 11.1 Add the new datasets and their curation rules to `documentation/` (French, matching the existing deep dives) — the inverted pipeline, the axis vocabulary, and how to curate a new root
- [x] 11.2 Update the `linguistics/lisan/` section of `CLAUDE.md`: core-first pipeline, the three new datasets, the no-fallback rule, the guard
- [x] 11.3 Record the coverage figure reached at merge time, so the next curation batch starts from a number
- [x] 11.4 Run the full local suite: `python -m pytest -q`, `cd frontend && npx vitest run`, `npx tsc --noEmit -p tsconfig.test.json`
