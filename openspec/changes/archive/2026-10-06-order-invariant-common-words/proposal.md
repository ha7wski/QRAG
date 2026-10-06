## Why

The common part of a pair of close verses is coloured as ONE contiguous span per verse, cut out of a
Smith–Waterman alignment, which cannot pair words that appear in a different order. On 2:3 / 14:31 the
shared verb أَنفَقَ sits after رزقناهم in one verse and before it in the other: it is matched on
neither side, yet it is coloured in 14:31 (it falls inside the span) and not in 2:3 (it falls just
outside), while بالغيب, which 14:31 does not hold, is coloured in 2:3. Across the 2 462 pairs that carry
a common part, 1 103 colour 2 215 words that are not shared and 916 leave 1 564 shared content words
uncoloured. The display claims «these words are common» and is wrong in both directions.

This is the first step of a two-step plan: fix what is SHOWN now, without touching which pairs exist or
how they are scored; redefine the relation itself (order-invariant lexical core × syntax × semantics)
in a later, separately measured change, which will reuse the matching introduced here.

## What Changes

- The common part of a close pair becomes the set of **matched words** of an order-invariant,
  weighted one-to-one matching between the two verses' content words (same lemma, or same root under
  a different lemma; rootless words and grammatical-tool occurrences excluded), plus the function
  words that sit between two matched words identically on both sides.
- Each pair stores its matched word pairs (with whether they share the lemma or only the root) and,
  per verse, the character RUNS of the coloured words in the displayed `text_ar_tashkil` — a list of
  spans instead of one.
- «N كلمات مشتركة» counts matched content words.
- **BREAKING** (dataset + API): `quran_close_verses.json`'s `ca`/`cb` become lists of spans and the
  schema version bumps; `GET /quran-similarity/pairs/{a}/{b}` replaces `span_u`/`span_v` with
  `spans_u`/`spans_v`; `GET /surah/{number}/annotations` serves lists of spans. The frontend moves in
  the same change; no other consumer exists.
- Unchanged: the pair set, `sim`, `pas`, `score`, their ordering, the passage dataset and its `k`,
  `wa`, `wb`, and every evaluation figure.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `close-verses`: the common-part requirement changes from «the best local alignment's contiguous
  span» to «the order-invariant matching of content words, stored as matched pairs and span runs».
- `cross-surah-similarity-map`: the pairs route serves lists of spans; the cell list colours every
  matched word.
- `surah-reading-annotations`: the orange word cue and the bubble colour the matched words (union of
  runs) instead of one span per pair.

## Impact

- `scripts/build_quran_close_verses.py` (common part, header, schema), `quran_data/loaders.py`
  (schema constant), `quran_data/manifest.py` (description)
- `retrieval/quran_close_verses.py` (reader shape, `ayah_view`, served pairs)
- `api/models/quran_similarity.py`, `api/models/surah_annotations.py`,
  `api/routers/quran_similarity.py`, `api/routers/surah_annotations.py`
- `frontend/src/lib/types.ts`, `lib/annotations.ts`, `components/QuranSimilarityMap.tsx`,
  `components/CloseVersesBubble.tsx`
- Rebuild of `data/derived/quran_close_verses.json` (backend stopped, ≈ 2.5 min); no model or input
  dataset changes.
- Tests: `tests/test_quran_close_verses*.py`, the two route tests, the frontend Vitest files.
