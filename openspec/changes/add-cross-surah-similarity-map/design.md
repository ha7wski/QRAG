## Context

`data/derived/quran_similarity.json` holds, for each scored verse, up to K = 10 close verses in
other surahs (two gates, frozen parameters; built by `scripts/build_quran_similarity.py`). It is read
through `quran_data.loaders.quran_similarity()` and the pure reader `retrieval/quran_similarity.py`,
and served one verse at a time by `GET /verse/{surah}/{ayah}/similar`.

Measured on the current file: the union of the neighbour lists gives **605 unordered verse pairs**,
falling in **351 of the 6 441 surah pairs** (5.4 %), touching 97 of the 114 surahs. The distribution
is very skewed: one cell holds 31 pairs (53 × 55, the refrain), a handful hold 10–13 (26 × 37,
52 × 77, 77 × 83, 77 × 88, 7 × 26, 15 × 38, 75 × 77), most hold 1–2.

The frontend draws charts by hand in SVG (`FassilaLine`, `FassilaDiversityLine`,
`FassilaDistributionPie`) with validated colour ramps; there is no chart dependency, and the
`similar` tab already hosts a two-way mode switch (`app/verse-study/page.tsx`, `similarModes`).

## Goals / Non-Goals

**Goals:**
- One picture of which surahs share close verses, and how many, readable without a model.
- From any non-empty cell, the list of its verse pairs, each verse opening in context.
- No new dataset and no rebuild: aggregate what `quran_similarity.json` already stores.

**Non-Goals:**
- Intra-surah closeness on the diagonal (the «داخل السورة» mode's question; mixing the two datasets
  would put two different populations on one colour scale).
- Re-ranking, clustering or re-ordering surahs by similarity (axes stay in mushaf order).
- Any change to the definition of «close», the dataset or its builder.
- Weighting cells by surah length (a raw count is what was asked; see Risks).

## Decisions

### D1 — What a cell counts: verse pairs, from the union of the stored lists

A pair is unordered `{u, v}` with `surah(u) ≠ surah(v)`, present when `v ∈ N(u)` **or** `u ∈ N(v)`
(the lists are top-K, so the relation is not always mutual; the score is symmetric, so either side
describes the same pair). Cell `(A, B)` = number of pairs with one verse in A and one in B. The cell
also reports how many distinct verses of A and of B take part, so «31 pairs» between 53 and 55 can be
read as «1 verse of al-Najm × 31 of ar-Raḥmān». The sum over all cells equals the dataset's pair
total (605 today) — an invariant the tests pin.

*Alternative rejected*: counting verses instead of pairs — loses the information that one verse of A
answers many verses of B, and is not additive across cells.

### D2 — Aggregated at request time in the pure reader, memoised

605 pairs aggregate in milliseconds; `retrieval/quran_similarity.py` gains `pair_set(data)`,
`matrix(data)` and `cell_pairs(data, a, b)`, memoised per loaded dict (the loader is already
process-cached). No new derived file, no manifest entry, nothing to rebuild or keep in sync.

*Alternative rejected*: precomputing a matrix file in the builder — a second artefact that can drift
from the one it summarises, for a computation that costs nothing.

### D3 — Two routes

- `GET /quran-similarity/matrix` → `{surahs: [{number, name_ar}] (114, mushaf order), cells:
  [{a, b, pairs, verses_a, verses_b}] (a < b, non-empty cells only), total_pairs, max_pairs}`.
  Sparse on purpose: 351 cells, not 12 996.
- `GET /quran-similarity/pairs/{a}/{b}` → `{a, b, surah names, pairs: [{u: Verse, v: Verse, score,
  roots}]}`, `u` always in the lower-numbered surah, ordered by score descending then (u, v); every
  verse through `verse_from_record`. `a == b` → 422; outside 1–114 → 422; an empty cell → 200 with
  `pairs: []` (not an error — the matrix may be stale against a client cache). `(b, a)` answers the
  same as `(a, b)`.
- Both load no model, touch no Qdrant; a missing dataset → 503 with the manifest's rebuild command,
  as `GET /verse/{s}/{a}/similar` already does. They live in `api/routers/quran_similarity.py` beside
  that route (same dataset, same failure mode).

### D4 — The chart: a hand-rolled SVG heatmap

- **Form**: an N × N matrix over the surahs that have at least one pair (97 today; see Resolved
  Questions), both axes in mushaf order, surah names as tick labels (Arabic,
  origin bottom-left — al-Fatiha is the first column on the left and the first row at the bottom,
  the x-axis reading left to right and the y-axis bottom to top; column names along the bottom, row
  names on the left — user, 2026-10-05). The matrix is drawn **mirrored** (both `(A, B)` and `(B, A)`), so a reader can find a pair
  starting from either surah; the diagonal is a neutral, non-interactive cell.
- **Scale**: a single-hue sequential ramp (the Fassila pie's validated method — monotone lightness,
  light end visible on white), on **log-binned** counts (1, 2, 3–4, 5–8, 9–16, 17+), because a linear
  scale would let the 31-pair cell wash every 1–2 cell into the background. Empty cells are the page
  background, not the lightest step. A legend states each bin in digits; colour carries magnitude,
  never identity, and the tooltip carries the exact count.
- **Size**: cells of ~12 px give a ~1 200 px square plus labels — wider than the page. The chart sits
  in its own scroll container (horizontal and vertical scroll inside the card, never page scroll),
  with sticky axis labels so names stay visible while scrolling. A zoom control is out of scope.
- **Interaction**: hover/focus shows `«سورة A» × «سورة B» : n أزواج (x آية × y آية)`; click or Enter
  selects the cell (outlined) and loads its pairs below the chart. Cells are keyboard-reachable only
  when non-empty (351 stops, not 12 996), in row order.
- The `dataviz` skill is loaded before writing the component (palette validation, legend, tooltip,
  dark mode).

### D5 — The cell list

Below the chart: a heading naming the two surahs and the count, then each pair as one card holding
both verses (vocalized, each with its surah name and ayah number), the shared-root chips, no score,
in score order. A verse opens «الآية في سياقها» through the page's existing `openInContext`. Cards
reuse the `VerseText` / root-chip markup of `SurahSimilarity.tsx` (extracted to a shared component if
needed, not copied).

### D6 — Mode switch and state

The `similarModes` switch gains a third button, «الآيات المتشابهات في سائر القرآن», placed right
after «المتشابهات داخل السورة» (so: داخل السورة · في سائر القرآن · من عبارة); the tab still opens on
the phrase mode. State under `verse-study.similar.quran.*` via `useCachedState`: the matrix response,
the selected cell, the fetched cells keyed `"a:b"`. The matrix is fetched once, when the mode is first
shown; revisiting a cell issues no request. Each request has its own sequence counter, so clicking
cell X then Y never ends on X's pairs.

The label repeats the heading of the cross-surah section under a picked verse in «داخل السورة».
That is deliberate — the user named it — and the two show the same dataset at two scales.

## Risks / Trade-offs

- **114 names on an axis are dense** → sticky labels in a scroll container; names are short in
  Arabic; the tooltip always names both surahs in full.
- **Raw counts favour long surahs and refrain surahs** (53 × 55 is one verse against a refrain) →
  the cell tooltip and the list header give `verses_a × verses_b` beside the pair count, so the reader
  sees when one verse drives a cell. Normalising was not asked and would hide the raw fact.
- **Sparse matrix (5.4 % filled) looks empty at a glance** → log-binned ramp, empty = background,
  and a one-line caption stating «351 زوجًا من السور يجمعها 605 من أزواج الآيات» (figures from the
  route, never hard-coded).
- **Dataset rebuilt with other parameters** → the routes read whatever the file holds; nothing is
  cached across a backend restart.
- **Phone width** → the chart scrolls inside its card; the cell list below is a normal column.

## Migration Plan

Additive: two routes, one mode. Ship backend then frontend. Rollback: remove the mode button and the
two handlers.

## Resolved Questions

Answered by the user on 2026-10-03, before implementation:

- **Axes: only the surahs that have at least one pair (97 today), not all 114.** The axes are the
  surahs appearing in at least one non-empty cell, in mushaf order, derived from the route's `cells`
  (never a hard-coded list), so a rebuilt dataset re-derives them. The route still returns all 114
  surahs (number, Arabic name) so the client can name any surah; it is the chart that drops the empty
  rows and columns. The caption states how many surahs take part.
- **Mirrored square**, as chosen in D4: `(A, B)` and `(B, A)` are both drawn.
