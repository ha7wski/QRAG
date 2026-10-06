## 1. Matching (pure functions, build script)

- [x] 1.1 Write failing tests in `tests/test_quran_close_verses_build.py`: 2:3 / 14:31 matching includes `(8, 7, "lemma")` and excludes 2:3 word 3; a tool occurrence (vocative أَيّ) is never matched; same-root/different-lemma gives `"root"`; equal-weight ties take the nearest relative position; fewer than 2 matches → no common part
- [x] 1.2 Implement `content_flags` (root carried AND not in `word_function.json`) and `match_words` (D2, `linear_sum_assignment`, weights 1 / 0.5, relative-position tie-break) in `scripts/build_quran_close_verses.py`
- [x] 1.3 Write failing tests for bridging (D3): «مِنْ» inside 28:20 / 36:20 is coloured; a function word held by one verse only, or between non-consecutive partners, is not; bridged words are not counted
- [x] 1.4 Implement `bridge_words` and `coloured_runs` (consecutive coloured words → runs) and `run_char_spans` (one half-open span per run, reusing `char_span`'s Basmala rebase and its `StaleInput` checks)

## 2. Dataset (schema 2)

- [x] 2.1 Replace D5's alignment-based common part in `compose()` by `m` / `ca` / `cb` (lists), keeping `k` / `wa` / `wb` for passage pairs and `pas` unchanged; update the module docstring (D5, D6) and the header (matching rule, weights, tie-break, bridge rule, threshold)
- [x] 2.2 Bump `QURAN_CLOSE_VERSES_SCHEMA` to 2 in `quran_data/loaders.py`; update the dataset's entry in `quran_data/manifest.py`
- [x] 2.3 Test: a rebuild on fixture inputs keeps the pair set, `sim`, `pas`, `score` identical to the schema-1 composition; two builds are byte-identical; every matched word lies inside one span of its verse

## 3. Reader and routes

- [x] 3.1 `retrieval/quran_close_verses.py`: validate the new common-part shape (`m`, `ca`, `cb` together; spans ascending, disjoint); served pairs carry `words = len(m)`, `spans_u`, `spans_v` oriented lower surah first; `ayah_view` orients the lists to the āya
- [x] 3.2 `api/models/quran_similarity.py` and `api/models/surah_annotations.py`: span fields become lists of `(int, int)`; `api/routers/quran_similarity.py` and `api/routers/surah_annotations.py` place each span through the existing displayed-text check
- [x] 3.3 Update `tests/test_quran_similarity_api.py`, `tests/test_quran_similarity_map.py`, `tests/test_surah_annotations.py` to the new fields; add the 2:3 / 14:31 route scenarios (pairs 2/14 → `words` = 5, a span of 2:3 covering «يُنفِقُونَ»; annotations of sūra 2 likewise)

## 4. Frontend

- [x] 4.1 `frontend/src/lib/types.ts`: `spans_u` / `spans_v` (pairs) and the annotation partner span lists
- [x] 4.2 `lib/annotations.ts`: take each pair's list of spans into the union (no wrapping of a single span); update its Vitest tests
- [x] 4.3 `components/QuranSimilarityMap.tsx` (`groupPairs`: hub = union of every span of its pairs, partner = its list) and `components/CloseVersesBubble.tsx` (partner marks its list); update their Vitest tests
- [x] 4.4 `npx vitest run` and `npx tsc --noEmit -p tsconfig.test.json` and `npx tsc --noEmit` pass

## 5. Rebuild and verify

- [x] 5.1 Stop the backend, run `python scripts/build_quran_close_verses.py`, restart
- [x] 5.2 `python scripts/eval_quran_close_verses.py` reports the same figures as before (AUC 0.726, counts unchanged); record the new common-part counts (pairs with a common part, `root` edges) in the design
- [x] 5.3 `python -m pytest -q` passes
- [x] 5.4 In the app: sūra 2 with annotations on colours «يُنفِقُونَ» in 2:3 and not «بِالْغَيْبِ»; the map cell 2 × 14 and the bubble show the same; 28:20 / 36:20 is one run
- [x] 5.5 Update CLAUDE.md's close-verses paragraph (the common part is the order-invariant matching, schema 2, `spans_u`/`spans_v`)
