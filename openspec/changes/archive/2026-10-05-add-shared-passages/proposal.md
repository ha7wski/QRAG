## Why

The cross-surah map links two verses only when their WHOLE syntax is close (≤ 1/3 of the longer
verse differs). A verse that repeats another's opening and then continues differently is never
linked: 28:20 and 36:20 share «وَجَاءَ رَجُلٌ مِّنْ أَقْصَى الْمَدِينَةِ يَسْعَىٰ قَالَ يَا…» (18 and 10 words;
the length pre-filter drops the pair before any score), and «رَجُلٌ» even sits in a different place. A
diagnostic counted 3 051 cross-surah pairs that share an exact run of ≥ 5 syntactic elements and
≥ 3 content roots yet are not stored (2:57/7:160, 7:54/10:3, 4:43/5:6, 35:13/39:5…). The user
asked (2026-10-05) for a second relation, «shared passage», beside the existing one.

## What Changes

- A new relation, **shared passage** (مقطع مشترك): two verses of different surahs share a passage
  when a local alignment of their QAC lemma sequences finds ≥ 6 matched words, dense (≥ 0.75 of the
  longer aligned span) and carrying ≥ 3 content words. A displaced word costs two gaps, so 28:20/36:20
  is reachable; a whole verse is never required to match.
- A model-free offline build `scripts/build_quran_passages.py` → `data/derived/quran_passages.json`
  (registered in `paths.py` / `manifest.py` / `loaders.py`), one best passage per verse pair, with
  the aligned word spans.
- Two model-free routes, `GET /quran-passages/matrix` and `GET /quran-passages/pairs/{a}/{b}`, the
  same shapes and error rules as the similarity map's, each pair carrying the passage's character
  span in each verse's `text_ar_tashkil`.
- The map mode gains a relation switch, «الآيات المتشابهات» / «المقاطع المشتركة»; with the second, the
  cells count shared-passage pairs and a picked cell lists both verses with the passage highlighted.
- A gold set drafted blind from the verse texts, a pre-registered target, an evaluation script.

## Capabilities

### New Capabilities
- `shared-passages`: the shared-passage relation, its dataset, routes, map switch and evaluation.

### Modified Capabilities

## Impact

`quran_data/{paths,manifest,loaders}.py`, new `scripts/build_quran_passages.py`,
`scripts/eval_quran_passages.py`, `retrieval/quran_passages.py`, `api/routers/quran_passages.py` +
models + `api/main.py`, `frontend/src/components/QuranSimilarityMap.tsx`, `lib/api.ts`,
`lib/strings.ts`, local tests and `tests/eval/quran_passages_gold.json`. The similarity dataset and
its routes are unchanged.
