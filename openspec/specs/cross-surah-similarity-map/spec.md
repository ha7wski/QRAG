# cross-surah-similarity-map Specification

## Purpose
TBD - created by archiving change add-cross-surah-similarity-map. Update Purpose after archive.
## Requirements
### Requirement: A cell counts the close verse pairs between two surahs

The system SHALL aggregate the cross-surah similarity dataset (`quran_similarity.json`) per pair of
surahs. A verse pair `{u, v}` with `surah(u) ≠ surah(v)` SHALL count once when `v` is in `u`'s stored
neighbour list or `u` is in `v`'s. The cell of surahs `(A, B)`, `A ≠ B`, SHALL hold the number of such
pairs with one verse in A and one in B, and the number of distinct verses of A and of B taking part.
The aggregation SHALL be computed from the dataset at request time (no derived file of its own), SHALL
be symmetric, and SHALL produce no diagonal cell.

#### Scenario: Counts add up to the dataset

- **WHEN** the matrix is computed
- **THEN** the sum of all cells' pair counts SHALL equal the number of distinct unordered pairs in the
  dataset's neighbour lists

#### Scenario: A one-sided listing still counts

- **WHEN** verse u lists v but v's top-K list does not hold u
- **THEN** the pair `{u, v}` SHALL be counted, once

#### Scenario: One verse against a refrain

- **WHEN** the cell (53, 55) is read on the current dataset
- **THEN** it SHALL report its pair count together with the distinct verses on each side (one verse of
  surah 53 against the refrain verses of surah 55)

### Requirement: Model-free routes serve the matrix and one cell

The backend SHALL serve `GET /quran-similarity/matrix` — the 114 surahs (number, Arabic name) in
mushaf order, the non-empty cells only (`a < b`, pair count, verses of a, verses of b), the total pair
count and the largest cell count — and `GET /quran-similarity/pairs/{a}/{b}` — that cell's pairs, each
with both verses, the score and the shared content roots, ordered by score descending then by
reference, the verse of the lower-numbered surah first. Every verse SHALL go through
`verse_from_record`. Neither route SHALL load a model or query Qdrant.

#### Scenario: A cell's pairs

- **WHEN** the client requests `GET /quran-similarity/pairs/58/3`
- **THEN** the response SHALL list the same pairs as `GET /quran-similarity/pairs/3/58`, each with its
  verse of surah 3 first, including 3:116 with 58:17

#### Scenario: Invalid and empty cells

- **WHEN** `a` equals `b`, or either is outside 1–114
- **THEN** the route SHALL answer 422
- **AND** a valid pair of surahs with no close pair SHALL answer 200 with an empty list

#### Scenario: Missing dataset

- **WHEN** `quran_similarity.json` is absent
- **THEN** both routes SHALL answer 503 naming `python scripts/build_quran_similarity.py`

#### Scenario: No model is loaded

- **WHEN** only these routes are called after startup
- **THEN** `GET /health` SHALL report no embedder and no search reranker resident

### Requirement: The matrix mode draws a surah × surah heatmap

The Verse Study «الآيات المتشابهات في سائر القرآن» mode SHALL draw a matrix whose two axes carry the
names of the surahs that have at least one close pair (derived from the route's cells, never
hard-coded; 97 on the current dataset) in mushaf order, each off-diagonal cell shaded by its pair count on a single-hue
sequential scale with log-spaced bins, empty cells left as background, the diagonal neutral and not
interactive. The matrix SHALL be mirrored, so `(A, B)` and `(B, A)` show the same cell. A legend SHALL
state each bin in digits, and a caption SHALL give the totals read from the route. The chart SHALL
scroll inside its own container, with the axis names kept visible, and SHALL never scroll the page
horizontally. No English label SHALL be rendered.

Hovering or focusing a non-empty cell SHALL name both surahs and give the pair count and the verses on
each side. Non-empty cells SHALL be reachable by keyboard.

#### Scenario: The refrain cell stands out

- **WHEN** the mode is shown on the current dataset
- **THEN** the cell of surahs 53 and 55 SHALL carry the darkest bin
- **AND** both (53, 55) and (55, 53) SHALL be drawn

#### Scenario: A surah with no pair has no row

- **WHEN** a surah takes part in no cross-surah pair
- **THEN** it SHALL have neither a row nor a column in the matrix

#### Scenario: An empty cell is not a target

- **WHEN** the reader hovers or clicks a cell with no pair, or the diagonal
- **THEN** nothing SHALL be selected and no request SHALL be issued

### Requirement: Selecting a cell lists its verse pairs

Clicking (or activating by keyboard) a non-empty cell SHALL outline it and list below the chart that
cell's pairs, under a heading naming both surahs and the count: each pair as one card with both
verses vocalized, each with its surah's Arabic name and ayah number, and the shared content roots as
Arabic root chips, in score order, with no numeric score. Activating a verse SHALL open it in «الآية
في سياقها». A fetched cell SHALL be cached, so selecting it again issues no request, and only the
latest selection SHALL apply its answer.

#### Scenario: Pick the cell of surahs 3 and 58

- **WHEN** the reader clicks the cell of surahs 3 and 58
- **THEN** the list SHALL show the pair 3:116 / 58:17 with «آل عمران» and «المجادلة»

#### Scenario: Quick successive clicks

- **WHEN** the reader clicks cell X, then cell Y before X's answer arrives
- **THEN** the list SHALL end on Y's pairs

