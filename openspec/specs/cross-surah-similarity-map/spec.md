# cross-surah-similarity-map Specification

## Purpose
TBD - created by archiving change add-cross-surah-similarity-map. Update Purpose after archive.
## Requirements
### Requirement: A cell counts the close verse pairs between two surahs

The system SHALL aggregate the unified close-verses dataset (`quran_close_verses.json`, capability
`close-verses`) per pair of surahs. Each of its pairs `{u, v}`, `surah(u) ≠ surah(v)`, SHALL count
once. The cell of surahs `(A, B)`, `A ≠ B`, SHALL hold the number of such pairs with one verse in A
and one in B, and the number of distinct verses of A and of B taking part. The aggregation SHALL be
computed from the dataset at request time (no derived file of its own), SHALL be symmetric, and
SHALL produce no diagonal cell.

#### Scenario: Counts add up to the dataset

- **WHEN** the matrix is computed
- **THEN** the sum of all cells' pair counts SHALL equal the number of pairs in the dataset

#### Scenario: A one-sided listing still counts

- **WHEN** verse u lists v in the similarity dataset but v's top-K list does not hold u
- **THEN** the pair `{u, v}` SHALL be a pair of the unified dataset and SHALL be counted, once

#### Scenario: A passage-only pair counts

- **WHEN** the cell (28, 36) is read
- **THEN** it SHALL count the pair 28:20 / 36:20, which the similarity dataset does not store

#### Scenario: One verse against a refrain

- **WHEN** the cell (53, 55) is read on the current dataset
- **THEN** it SHALL report its pair count together with the distinct verses on each side (one verse of
  surah 53 against the refrain verses of surah 55)

### Requirement: Model-free routes serve the matrix and one cell

The backend SHALL serve `GET /quran-similarity/matrix` — the 114 surahs (number, Arabic name) in
mushaf order, the non-empty cells only (`a < b`, pair count, verses of a, verses of b), the total pair
count and the largest cell count — and `GET /quran-similarity/pairs/{a}/{b}` — that cell's pairs, each
with both verses, the combined score, the shared content roots and, when the pair has a common part,
its matched word count (`words`) and the list of half-open character spans of its coloured words in
each verse's `text_ar_tashkil` (`spans_u`, `spans_v`); the three SHALL be null together when it has
none. Pairs SHALL be ordered by score descending then by reference, the verse of the lower-numbered
surah first. Every verse SHALL go through `verse_from_record`. Neither route SHALL load a model, query
Qdrant or read `word_index.json`.

#### Scenario: A cell's pairs

- **WHEN** the client requests `GET /quran-similarity/pairs/58/3`
- **THEN** the response SHALL list the same pairs as `GET /quran-similarity/pairs/3/58`, each with its
  verse of surah 3 first, including 3:116 with 58:17

#### Scenario: A pair carries its common part

- **WHEN** the client requests `GET /quran-similarity/pairs/28/36`
- **THEN** the pair 28:20 / 36:20 SHALL carry `words` and one span per verse whose text starts with
  «وَجَاءَ» and ends with «قَالَ»

#### Scenario: Displaced shared words are served

- **WHEN** the client requests `GET /quran-similarity/pairs/2/14`
- **THEN** the pair 2:3 / 14:31 SHALL carry `words` = 5 and a span of 2:3 covering «يُنفِقُونَ»

#### Scenario: Invalid and empty cells

- **WHEN** `a` equals `b`, or either is outside 1–114
- **THEN** the route SHALL answer 422
- **AND** a valid pair of surahs with no close pair SHALL answer 200 with an empty list

#### Scenario: Missing dataset

- **WHEN** `quran_close_verses.json` is absent
- **THEN** both routes SHALL answer 503 naming `python scripts/build_quran_close_verses.py`

#### Scenario: No model is loaded

- **WHEN** only these routes are called after startup
- **THEN** `GET /health` SHALL report no embedder and no search reranker resident

### Requirement: The matrix mode draws a surah × surah heatmap

The Verse Study «الآيات المتشابهات في سائر القرآن» mode SHALL draw ONE matrix, with no relation
switch, whose two axes carry the names of the surahs that have at least one close pair (derived from
the route's cells, never hard-coded) in mushaf order, each off-diagonal cell shaded by its pair count
on a single-hue sequential scale with log-spaced bins, empty cells left as background, the diagonal
neutral and not interactive. The matrix SHALL be mirrored, so `(A, B)` and `(B, A)` show the same
cell. A legend SHALL state each bin in digits, and a caption SHALL give the totals read from the
route. The chart SHALL scroll inside its own container, with the axis names kept visible, and SHALL
never scroll the page horizontally. No English label SHALL be rendered.

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

#### Scenario: There is no relation switch

- **WHEN** the mode is shown
- **THEN** no control SHALL offer «المقاطع المشتركة» as a separate view, and no request SHALL go to a
  `quran-passages` route

### Requirement: Selecting a cell lists its verse pairs

Clicking (or activating by keyboard) a non-empty cell SHALL outline it and list below the chart that
cell's pairs, under a heading naming both surahs and the count: each pair as one card with both
verses vocalized, each with its surah's Arabic name and ayah number, in the order served, with no
numeric score. When the pair has a common part, every one of its spans SHALL be highlighted in both
verses and the card SHALL state «N كلمات مشتركة» with N the matched word count; when it has none, the
verses SHALL be shown plain. The shared content roots SHALL be shown as Arabic root chips when there
are any. Activating a verse SHALL open it in «الآية في سياقها». A fetched cell SHALL be cached, so
selecting it again issues no request, and only the latest selection SHALL apply its answer.

#### Scenario: Pick the cell of surahs 3 and 58

- **WHEN** the reader clicks the cell of surahs 3 and 58
- **THEN** the list SHALL show the pair 3:116 / 58:17 with «آل عمران» and «المجادلة»

#### Scenario: The common part is coloured

- **WHEN** the reader clicks the cell of surahs 28 and 36
- **THEN** the list SHALL show 28:20 and 36:20 with «وَجَاءَ … قَالَ» highlighted in both

#### Scenario: Every shared word is coloured

- **WHEN** the reader clicks the cell of surahs 2 and 14
- **THEN** in 2:3 «يُنفِقُونَ» SHALL be highlighted and «بِالْغَيْبِ» SHALL NOT

#### Scenario: Quick successive clicks

- **WHEN** the reader clicks cell X, then cell Y before X's answer arrives
- **THEN** the list SHALL end on Y's pairs

