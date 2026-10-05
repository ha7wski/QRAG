## Why

`quran_similarity.json` (shipped by `add-quran-wide-similar-verses`) already knows which verses of
one surah are close to verses of another — 605 cross-surah pairs, under the two-gate definition
(meaning-or-subject AND near syntax). Today it is only reachable verse by verse, from a group of
«المتشابهات داخل السورة». The question a reader asks one level up — *which surahs speak to each
other, and how much?* — has no answer on screen: that al-Najm and ar-Raḥmān share 31 close pairs
(the «فَبِأَيِّ آلَاءِ» refrain), that ash-Shuʿarāʾ and aṣ-Ṣāffāt share 13, that al-Mursalāt echoes
aṭ-Ṭūr, al-Muṭaffifīn and al-Ghāshiya. The data already holds this map; it only needs to be drawn.

## What Changes

- **A third mode in the «الآيات المتشابهات» tab**, labelled «الآيات المتشابهات في سائر القرآن»,
  beside «المتشابهات داخل السورة» and «المتشابهات من عبارة» in the same switch.
- **A surah × surah matrix**: both axes carry the 114 surah names in mushaf order; each cell
  (A, B), A ≠ B, is shaded by the **number of close verse pairs** between surah A and surah B
  (a pair = one verse of A and one verse of B stored as close in the cross-surah dataset). The
  matrix is symmetric; the diagonal is empty (intra-surah closeness is the other mode's question).
- **Clicking a cell lists its pairs**: below the matrix, each close pair of verses, vocalized, with
  their surah names and ayah numbers and their shared roots, ranked; a verse opens «الآية في
  سياقها» like every verse of the tab.
- **Two model-free routes** read the existing dataset — no new dataset, no rebuild:
  `GET /quran-similarity/matrix` (the per-surah-pair counts) and
  `GET /quran-similarity/pairs/{a}/{b}` (the pairs of one cell). The served-surface table gains two
  rows.
- No change to the dataset, its builder, `GET /verse/{s}/{a}/similar`, the two existing modes, or
  `GET /search`.

## Capabilities

### New Capabilities
- `cross-surah-similarity-map`: the per-surah-pair aggregation of the cross-surah dataset, the two
  routes that serve it, and the matrix mode that renders it and lists a cell's pairs.

### Modified Capabilities
- `verse-study`: the `similar` tab's switch gains a third mode; each mode keeps its state.
- `served-surface`: the consumed-surface table gains the two routes.

## Impact

- **Backend**: `retrieval/quran_similarity.py` gains a pure aggregation (pairs per surah pair, the
  pairs of one cell) over the loader's dict, memoised per process; a new router (or two handlers in
  `api/routers/quran_similarity.py`), response models, one `include_router` if a new router.
- **Frontend**: a new component (e.g. `components/QuranSimilarityMap.tsx`) — a hand-rolled SVG
  heatmap like the Fassila charts (no chart library is added), its cell detail list reusing the
  verse/root-chip cards of `SurahSimilarity.tsx`; the mode switch in `app/verse-study/page.tsx`;
  `lib/api.ts`, `lib/strings.ts`.
- **Data**: none new. A missing `quran_similarity.json` makes both routes answer 503 with the rebuild
  command, and the mode says so.
- **Tests (local-only)**: aggregation invariants (symmetry, counts sum to the dataset's pair total,
  no diagonal), route contract, served-surface, a Vitest for the matrix and the cell list.
