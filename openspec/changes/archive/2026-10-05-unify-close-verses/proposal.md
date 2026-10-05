## Why

The cross-surah map now answers two questions behind a switch: «الآيات المتشابهات» (whole-verse
closeness, 451 pairs) and «المقاطع المشتركة» (shared wording, 2 191 pairs). They overlap on only 151
pairs, so the reader has to look twice, and neither view says what the other knows: a close pair does
not show which words it shares, and a shared passage does not say whether the two verses are close.
The user asked (2026-10-05) for ONE feature: detect the common part, measure closeness, rank by a
score that takes both into account, and colour the common part in the results.

## What Changes

- A single relation, **close verses**, whose pairs are the UNION of the two existing relations
  (2 491 pairs today). The common part is a signal, not a filter: requiring a passage first would
  drop 300 of the 451 close pairs, which share fewer than 6 aligned words.
- Each pair carries two measures and one score: `sim` (the similarity score `sem × syn`, computed
  without its gates for the pairs only the passage relation holds), `pas` (the share of the shorter
  verse covered by the shared passage, 0 without one), and
  `score = 1 − (1 − sim)(1 − pas)`. The formula is frozen before the build runs.
- Each pair carries its **common part** when it has one: the passage for a passage pair, else the
  best local alignment of ≥ 2 words. It is displayed, and it enters the score only when it is a
  passage.
- A new offline build `scripts/build_quran_close_verses.py` →
  `data/derived/quran_close_verses.json`, composed from the two existing datasets, which stay as its
  inputs and keep their builds, parameters and gold measurements.
- `GET /quran-similarity/matrix`, `GET /quran-similarity/pairs/{a}/{b}` and
  `GET /verse/{surah}/{ayah}/similar` read the new dataset. Pairs and neighbours gain the common
  part's word count and character spans. The per-verse list is no longer capped at K.
- **BREAKING**: `GET /quran-passages/matrix` and `GET /quran-passages/pairs/{a}/{b}` are removed
  (404), with their router, models, reader and client functions.
- The map loses its relation switch: one chart, and each listed pair shows both verses with the
  common part in `<mark>`, «N كلمات مشتركة» and the shared roots. The verse panel of «داخل السورة»
  marks the common part in each close verse as well.
- An evaluation script over both existing gold sets, with targets registered in design.md D10 before
  the build.

## Capabilities

### New Capabilities
- `close-verses`: the unified relation — its pair set, the two measures, the combined score, the
  common part, the dataset and its evaluation.

### Modified Capabilities
- `cross-surah-similarity-map`: the cells, the two routes and the pair list read the unified
  dataset; pairs carry the common part; the chart has no relation switch.
- `quran-wide-similarity`: the per-verse route and the anchor panel read the unified dataset; no K
  cap; the common part is marked.
- `shared-passages`: its two routes and the map switch are removed; the relation, its dataset and
  its gold measurement stay, as an input.
- `served-surface`: the two shared-passage routes join the removed routes.

## Impact

New `scripts/build_quran_close_verses.py`, `scripts/eval_quran_close_verses.py`,
`retrieval/quran_close_verses.py`; `quran_data/{paths,manifest,loaders}.py`;
`api/routers/quran_similarity.py` + `api/models/quran_similarity.py`; `api/main.py`. Deleted:
`retrieval/quran_similarity.py`, `retrieval/quran_passages.py`, `api/routers/quran_passages.py`,
`api/models/quran_passages.py`. Frontend: `QuranSimilarityMap.tsx`, `SurahSimilarity.tsx`,
`SimilarVerseParts.tsx`, `lib/api.ts`, `lib/strings.ts`. Local tests and `CLAUDE.md`.
`build_quran_similarity.py`, `build_quran_passages.py` and their datasets are unchanged. The build
needs the backend stopped (verse vectors from the embedded Qdrant) and the cross-encoder (~1.1 GB).
