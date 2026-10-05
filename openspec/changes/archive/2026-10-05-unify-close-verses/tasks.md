## 1. Freeze

- [x] 1.1 Freeze the pair set, `sim`, `pas`, the score, the common part, the dataset, the routes, the frontend and the targets U1–U4 in design.md (D1–D10) before `build_quran_close_verses.py` exists or runs — frozen 2026-10-05 against gold `e1acf7805c6a3115…` (similarity) and `717802bdb636b106…` (passages), inputs `ce5f8fef490d1af7…` (`quran_similarity.json`) and `1e7782279718db74…` (`quran_passages.json`)
- [x] 1.2 Re-check the four digests of 1.1 immediately before the first build; a difference is recorded here with its cause before going on — checked 2026-10-05 at apply time: all four unchanged

## 2. Dataset registry

- [x] 2.1 `QURAN_CLOSE_VERSES_JSON` in `quran_data/paths.py`, its `manifest.py` entry (producer, the two input datasets, consumers, rebuild command, build order, backend-stopped note) and `loaders.quran_close_verses()` (schema check, `DatasetMissing` with the rebuild command)
- [x] 2.2 Update the manifest consumers of `quran_similarity.json` and `quran_passages.json` (the unified build and their own eval script; no route)

## 3. Build

- [x] 3.1 `scripts/build_quran_close_verses.py`: read both inputs, the pair set and `from` (D1); refuse on a held Qdrant lock with the similarity build's message
- [x] 3.2 `sim` (D2): stored `s` for S; for W \ S the imported `syn_similarity`, `cov`, cross-encoder and `sem_score`, ungated, `dense` ranked among the re-derived syntax survivors, in a cross-encoder call of its own; the dense integrity check over S
- [x] 3.3 `pas` (D3) and `score` (D4)
- [x] 3.4 The common part (D5): stored passage for W; imported Smith–Waterman + the mark rule for S \ W; word spans and character spans rebased past the Basmala; fail on a span outside the displayed text
- [x] 3.5 Header, `unscored`, `roots`, ordering, atomic write, byte-identical output (D6)
- [x] 3.6 Tests: union and `from`; `score` on hand values (`pas = 0` → `sim`; both > 0 → above both); `pas` only for passage pairs; the mark rule (1 word, sparse alignment, no content word, 26:203/37:54 → «قال هل» marked and `pas = 0`); character spans against `word_index.json` including an āya 1 with a Basmala; the dense check refusing a tampered input; determinism

## 4. Reader and API

- [x] 4.1 `retrieval/quran_close_verses.py`: `ayah_view`, `pair_set`, `matrix`, `cell_pairs` over the unified dataset, `MalformedEntry`, memoised; delete `retrieval/quran_similarity.py` and `retrieval/quran_passages.py`
- [x] 4.2 `api/models/quran_similarity.py`: `SimilarPair` gains `words`, `span_u`, `span_v` (nullable together); a cross-surah neighbour model with `words` and `span`; `api/routers/quran_similarity.py` reads the new reader, no `word_index.json`, 503 naming the new build command (D7)
- [x] 4.3 Delete `api/routers/quran_passages.py` and `api/models/quran_passages.py`; unmount in `api/main.py`
- [x] 4.4 Tests: reader (order, symmetry, no cap, list ≡ map, malformed → `MalformedEntry`); routes (422 / 404 / 503 / empty cell / `(b, a)` / spans on 28:20/36:20 / `GET /verse/28/20/similar` lists 36:20); `test_served_surface.py` names the two removed routes; `test_import_direction.py` and `test_quran_data.py` pass

## 5. Frontend

- [x] 5.1 `lib/api.ts`: nullable `words` / spans on the pair and neighbour types; delete the passage client functions and types; `lib/strings.ts`: drop the switch strings, new empty-list sentence
- [x] 5.2 `SimilarVerseParts.tsx`: verse text with an optional marked span (moved out of `QuranSimilarityMap.tsx`)
- [x] 5.3 `QuranSimilarityMap.tsx`: remove the relation switch, the passage panel and their state; one pair card with marks, «N كلمات مشتركة» and root chips (D8)
- [x] 5.4 `SurahSimilarity.tsx`: mark each close verse's span and show its word count; the new empty-list sentence
- [x] 5.5 Vitest: no switch and no `quran-passages` request; marked spans and count on a pair with a common part, plain text without; the anchor panel's marks; `tsc` on both configs; `test_frontend_reachability.py`

## 6. Evaluate

- [x] 6.1 `scripts/eval_quran_close_verses.py`: digest refusals, positives and negatives present per sample and kind, the three AUCs with their counts, 28:20/36:20, 26:203/37:54, targets U1–U4 printed PASS / MISS
- [x] 6.2 Stop the backend; build once; evaluate once; record the result here (a miss is the result — no value of D2–D5 moves)

  **Result (2026-10-05, one build, one evaluation; inputs `ce5f8fef…` / `1e778227…`, gold `e1acf780…` / `717802bd…`).**
  Build 140 s (cross-encoder 137 s on mps): 1 316 syntax survivors re-derived, dense check passed on
  the 451 stored pairs, 2 040 passage-only pairs cross-encoded (0 verbatim). **2 491 pairs** —
  similarity only 300, passage only 2 040, both 151; common part on 2 462 (2 191 passages + 271
  marked alignments); 22 unscored verses.
  - **U1 — MISS.** AUC(score) **0.726** on 89 positives × 7 negatives (target ≥ 0.80). Beside it:
    AUC(sim) 0.567, AUC(pas) 0.847. Two of the seven negatives are the label conflicts
    37:80/77:44 (score 1.0) and 77:15/83:10 (0.9999), positives of the similarity gold that the
    passage gold calls short formulas: they sit at the top of the ranking by construction. The
    other five: 21:33/36:40 0.597, 79:15/88:1 0.283, 69:3/83:19 0.265, 86:2/90:12 0.254,
    75:1/90:1 0.096. Recorded, not tuned.
  - **U2 — PASS.** 28:20/36:20 present, score 0.661 (sim 0.153, pas 0.6, k 6); common part
    «وَجَاءَ رَجُلٌ مِنْ أَقْصَى الْمَدِينَةِ يَسْعَىٰ قَالَ» / «وَجَاءَ مِنْ أَقْصَى الْمَدِينَةِ رَجُلٌ يَسْعَىٰ قَالَ».
  - **U3 — PASS.** 26:203/37:54: pas 0, score 0.184, rank 8 of 8 in cell (26, 37).
  - **U4 — PASS.** 2 491 stored = |S ∪ W|; the dense check is enforced by the build's refusal
    (not recorded in the header).
  - Reported: positives present — passages 38 / 40, similarity v1 51 / 60, v2 6 / 17;
    `neg_same_subject_diff_syntax` 5 / 13 present (apart).

## 7. Verify and document

- [x] 7.1 Full suites: `python -m pytest -q`, `npx vitest run`, both `tsc` configs
- [x] 7.2 Adversarial review of the build, the reader and the frontend against the specs
- [x] 7.3 `CLAUDE.md`: the unified relation, the build order, the routes, the map without its switch, the current figures
- [x] 7.4 Browser check: the single map; cell (28, 36) shows 28:20/36:20 marked; a similarity-only pair shows its short common part; the verse panel of «داخل السورة» marks its close verses — map checked live (no switch, 28×36 marked, 26×37 short parts marked incl. «فَيَقُولُوا هَلْ» / «قَالَ هَلْ»); the «داخل السورة» marks are covered by Vitest, not checked in the browser
