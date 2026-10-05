## 1. Decisions to confirm before coding

- [x] 1.1 Confirm with the user the two open questions of design.md (all 114 surahs vs the 97 with a pair; mirrored square vs one triangle); record the answer in design.md

## 2. Backend aggregation and routes

- [x] 2.1 In `retrieval/quran_similarity.py`, add the pure `pair_set(data)`, `matrix(data)` and `cell_pairs(data, a, b)` (D1–D2), memoised per loaded dict; imports `quran_data` only
- [x] 2.2 Response models in `api/models/quran_similarity.py` (matrix: surahs, sparse cells, totals; cell: both surah names, pairs with two verses, score, roots)
- [x] 2.3 Handlers `GET /quran-similarity/matrix` and `GET /quran-similarity/pairs/{a}/{b}` in `api/routers/quran_similarity.py` (or a new router + one `include_router`): `verse_from_record` on every verse, 422 for `a == b` or out of range, 200 + empty list for an empty cell, `(b, a)` ≡ `(a, b)`, 503 with the rebuild command when the dataset is missing
- [x] 2.4 Tests (local-only): counts sum to the distinct pair total, symmetry, no diagonal, one-sided listing counted once, cell (53, 55) = 1 × 31 on the current file (skip if absent), route contract (422/200-empty/503, ordering, lower surah first, 3/58 ≡ 58/3), no model resident; `test_import_direction.py`, `test_module_root_depth.py` green

## 3. Frontend

- [x] 3.1 Load the `dataviz` skill; validate the sequential ramp (log bins 1, 2, 3–4, 5–8, 9–16, 17+; empty = background) in light and dark
- [x] 3.2 `lib/api.ts`: `getQuranSimilarityMatrix()`, `getQuranSimilarityPairs(a, b)` and types; `lib/strings.ts`: mode label, caption, legend, tooltip, list heading, empty/unavailable messages (Arabic)
- [x] 3.3 New `components/QuranSimilarityMap.tsx`: SVG heatmap N × N over the surahs with ≥ 1 pair (97 today, derived from the cells) in mushaf order, mirrored, origin bottom-left (al-Fatiha first), names along the bottom and on the left, sticky in a scroll container, legend, caption from the route's totals, tooltip on hover/focus, keyboard reachability of non-empty cells only
- [x] 3.4 Cell selection: outline, list below (heading with both surah names and the count; pair cards with both verses, surah names, ayah numbers, root chips, no score), verse opens «الآية في سياقها»; shared verse/root-chip markup extracted from `SurahSimilarity.tsx` rather than copied
- [x] 3.5 Third button in the `similarModes` switch of `app/verse-study/page.tsx` (داخل السورة · في سائر القرآن · من عبارة; default unchanged); state under `verse-study.similar.quran.*`; matrix fetched once; per-request sequence counters; cached cells
- [x] 3.6 Vitest: mode switch keeps the matrix state, empty cell/diagonal issue no request, clicking a cell lists its pairs, quick successive clicks end on the latest cell, cached revisit issues no request, no numeric score; `npx tsc --noEmit -p tsconfig.test.json` green

## 4. Surface and docs

- [x] 4.1 Update `tests/test_served_surface.py` with the two routes; confirm `tests/test_frontend_reachability.py` sees the new component
- [x] 4.2 Update `CLAUDE.md` (route list, `retrieval/` paragraph, `/verse-study` description)
- [x] 4.3 Manual check in the browser: the 53 × 55 cell is darkest, cells 3 × 58 and 26 × 37 list their pairs, a verse opens in context, phone width scrolls inside the chart only, the two other modes unchanged
