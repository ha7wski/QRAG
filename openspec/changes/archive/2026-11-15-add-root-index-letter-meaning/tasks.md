## 1. Dataset

- [x] 1.1 Move `data/maani-huruf/maani_huruf.json` to `data/references/maani_huruf.json` and remove the empty folder
- [x] 1.2 Add `MAANI_HURUF_JSON` to `quran_data/paths.py` and its entry to `quran_data/manifest.py` (manual compilation, sources from `meta.sources`, not regenerable, consumer `api/routers/roots.py`)
- [x] 1.3 Add the cached loader `loaders.maani_huruf()`; `python -m pytest -q tests/test_quran_data.py` passes

## 2. Projection and route

- [x] 2.1 Add `LetterMeaning` (+ position, source, dimension sub-models) to `api/models/roots.py` and `maani: LetterMeaning | None = None` to `RootLetterResponse`
- [x] 2.2 In `api/routers/roots.py`, add `letter_meaning(label)`: «أ» → `ا`, projection per `letter-meaning-sheet` (Arabic fields, positions أول/وسط/آخر, sources in `meta.sources` order), any load or shape error → None + warning
- [x] 2.3 Join it in `build_letter` so it is memoised with the letter
- [x] 2.4 Pytest: 28 letters project with three positions; «أ» reads `ا`; `ر` core sense; substitute-word position keeps a null name; no French field; loader failure → 200 with `maani` null

## 3. Frontend

- [x] 3.1 Mirror the types in `lib/types.ts` (`LetterMeaning`, `RootLetterResponse.maani`)
- [x] 3.2 Add the Arabic labels to `lib/strings.ts`: box title, «تأويلي», series labels, position names, origin tags, source authority names keyed AQ/IS/HA/BL/NJ/SM, «الرسم» / «البنية» / «الأبعاد»
- [x] 3.3 Create `components/LetterMeaningBox.tsx`: header (letter, name, badge, series) → core sense → three positions (name or substitute tag, sense, examples, origin tag) → readings by source with authority → drawing, structure, dimensions; RTL via `ArabicText`
- [x] 3.4 Render it in `app/roots/page.tsx` after the group heading, before the readings notice and the root cards, only when `data.maani` is non-null; strip buttons unchanged
- [x] 3.5 Vitest (`app/roots/page.test.tsx`): box present for «ر» and placed before the first root card; absent when `maani` is null; strip buttons carry no definition text
- [x] 3.6 `npx vitest run`, `npx tsc --noEmit -p tsconfig.test.json`, `npx tsc --noEmit` pass

## 4. Docs

- [x] 4.1 Update CLAUDE.md's `/roots` and `GET /roots/letter/{letter}` descriptions (box + `maani`), and the `root-index` spec purpose line ("no new dataset" no longer holds)
- [x] 4.2 List the user-facing checks (box for «ر», «أ», a substitute-word position) for the user to verify in the running app
