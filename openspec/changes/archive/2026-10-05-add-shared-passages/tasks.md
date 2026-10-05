## 1. Freeze

- [x] 1.1 Freeze tokens, alignment, acceptance, dataset, routes, map and target in design.md (D1–D8) before any gold pair or corpus build
- [x] 1.2 Draft `tests/eval/quran_passages_gold.json` blind (no alignment run); record its sha256 here — sha256 `717802bdb636b10624acd0018f334edc7ac6be06fe79908d391971f40415a8fc` (60 pairs: 40 positive, 10 neg_scattered, 10 neg_short_formula)

## 2. Backend

- [x] 2.1 `QURAN_PASSAGES_JSON` in `paths.py` + `manifest.py` entry + `loaders.quran_passages()` (schema check, `DatasetMissing` with the rebuild command)
- [x] 2.2 `scripts/build_quran_passages.py`: tokens (D1), exact candidates (D4), Smith–Waterman + traceback (D2), acceptance (D3), dataset (D5), multiprocessing, deterministic
- [x] 2.3 `retrieval/quran_passages.py`: pure reader — `matrix(data)`, `cell_pairs(data, a, b)` (imports `quran_data` only)
- [x] 2.4 `api/routers/quran_passages.py` + models + mount in `api/main.py`: the two routes (D6), spans from `word_index.json`, Basmala rebase
- [x] 2.5 Tests: tokens, alignment on hand cases (28:20/36:20, a formula, a displaced word), acceptance, candidates exactness, routes (422/503/empty/(b,a)/spans), served surface, dataset invariants

## 3. Frontend

- [x] 3.1 `lib/api.ts` client + types, `lib/strings.ts` strings
- [x] 3.2 Relation switch in `QuranSimilarityMap.tsx`; passage cell list with `<mark>` spans and word count (D7)
- [x] 3.3 Vitest: switch, matrix per relation, highlighted spans, state per relation

## 4. Evaluate and verify

- [x] 4.1 `scripts/eval_quran_passages.py`
- [x] 4.2 Build once; evaluate once; record the result here

  **Result (2026-10-05, one run, gold sha256 `717802bd…`, scores +2/−1/−1 per the D2 amendment).**
  169 592 candidates (D4) → **2 191 passages** (rejected: l_min 166 589, density 461, content_min 351);
  6.6 s with 7 jobs.
  - Recall of positives **38 / 40 = 0.95** (target ≥ 0.80) — PASS.
  - Negatives found **1 / 20** (target ≤ 10 %) — PASS: neg_scattered 21:33/36:40 (k = 6: «اللَّيْل …
    النَّهَار» plus «كُلٌّ فِي فَلَكٍ يَسْبَحُونَ», spans 8 / 7); neg_short_formula 0 / 10.
  - 28:20/36:20 found, words 1–7 / 1–7, k = 6 — PASS.
  - Missed: **29:8/31:15** — the single BEST alignment (by score) runs 17 / 29 words across the
    12 words 31:15 inserts, and fails density, while the 11-word core alone would pass: D2 keeps the
    best-scoring alignment, not the best ACCEPTED passage. **2:106/35:1** — «أَنَّ» and «إِنَّ» are
    different lemmas, leaving 5 words. Both recorded, not tuned.
- [x] 4.3 Adversarial review; full suites; docs (CLAUDE.md); browser check
