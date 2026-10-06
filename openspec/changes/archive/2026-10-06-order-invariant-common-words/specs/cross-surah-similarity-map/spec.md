## MODIFIED Requirements

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
