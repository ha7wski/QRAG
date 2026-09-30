## 0. Review gate

- [x] 0.1 User reviews design.md (§D1 gaps and Open Questions 1–6) and approves before any code

## 1. Data

- [x] 1.1 Write `data/references/islambouli_wasf.csv` (four entries from §D4, each with form and justification) and `islambouli_wasf.lock.json` (with `segment_notes` for ء, ع, ض)
- [x] 1.2 Deposit the two screenshots under `data/source/`, hash them, and record their origin (episode reference if the user supplies it)
- [x] 1.3 Write `data/references/islambouli_citations.json` (ضرب physical, ضرب cultural, كتب physical, `development_cases`) and its lock
- [x] 1.4 Add the `quran_data/paths.py` constants, the `manifest.py` entries and the loaders; `test_quran_data.py` passes

## 2. Assembly engine

- [x] 2.1 Write `linguistics/lisan/islambouli/wasf.py`: load, verify the lock, enforce the 20-entry ceiling, check the criterion fields
- [x] 2.2 Write `linguistics/lisan/islambouli/assemble.py`:
  - [x] 2.2.1 Extract the segment (§D2)
  - [x] 2.2.2 Split the alternative groups (§D5)
  - [x] 2.2.3 Apply the template (§D3)
  - [x] 2.2.4 Inherit the refusals from `compose()`
- [x] 2.3 Write the acceptance tests: ضرب and كتب outputs pinned to §D1, and the published fixture with its exact diff
- [x] 2.4 Write the no-automatic-selection tests:
  - [x] 2.4.1 Property test over all rows × positions
  - [x] 2.4.2 Static import and choice-origin test
- [x] 2.5 Test that the development cases are disjoint from both witness sets

## 3. Personal readings

- [x] 3.1 Add the `lisan_readings` table and its accessors to `api/store.py`
- [x] 3.2 Add `GET` and `PUT /lisan/reading/{root}`:
  - [x] 3.2.1 Validate the author, the position and the alternative index
  - [x] 3.2.2 Test with a temp `APP_DB_PATH`
- [x] 3.3 Update `test_served_surface.py` to serve the two routes

## 4. API join

- [x] 4.1 Join `islambouli_assembly` and `cultural_stage` in `api/routers/lisan.py`, with the choice read only from the stored reading
- [x] 4.2 Add the matching `api/models/lisan.py` fields
- [x] 4.3 Test that a request-body choice is not honoured, and that a lock failure omits both fields

## 5. Frontend

- [x] 5.1 Add the `lisanTypes.ts` and `api.ts` types and calls (reading get/put)
- [x] 5.2 Build the assembly block in `LisanResult.tsx`: the sentence, the label, the bracketed groups, and a per-group signed-choice control with an author field (remembered in localStorage)
- [x] 5.2b Build Islambouli's cited physical sentence (printed label) above the assembly, and the named word gap
- [x] 5.3 Build the cultural block: citation and/or personal reading, each attributed; nothing rendered when both are absent
- [x] 5.4 Add the `strings.ts` entries
- [x] 5.5 Write the Vitest tests:
  - [x] 5.5.1 Section order
  - [x] 5.5.2 Label present
  - [x] 5.5.3 Both alternatives by default
  - [x] 5.5.4 A signed choice shows its author
  - [x] 5.5.5 No cultural section without a source
  - [x] 5.5.6 The cited sentence carries its printed label
  - [x] 5.5.7 The gap is named
- [x] 5.6 Run `tsc` on both configs

## 6. Wrap-up

- [x] 6.1 Run the full pytest and Vitest suites; check the live app on ضرب, كتب and a root with neither source
- [x] 6.2 Update CLAUDE.md (`/lexical` description, served routes) and the `islambouli-letter-table` documentation with the §D1 gap
