# shared-passages Specification

## Purpose
TBD - created by archiving change add-shared-passages. Update Purpose after archive.
## Requirements
### Requirement: A shared-passage relation between verses of different surahs

Two verses of different surahs SHALL share a passage when the Smith–Waterman local alignment
(match +2, mismatch −1, gap −1, standard traceback) of their token sequences — one token per QAC word, the stem segment's
lemma, else the bare surface — has at least 6 matched positions, matched positions at least 0.75 of
the longer aligned span, and at least 3 matched content words (words carrying a root). Only the best
alignment of a pair SHALL be kept.

#### Scenario: A displaced word does not break a passage

- **WHEN** 28:20 and 36:20 are aligned
- **THEN** they SHALL share a passage covering «وَجَاءَ … قَالَ» in both verses

#### Scenario: A short formula is not a passage

- **WHEN** two verses share only «إِنَّ ٱللَّهَ غَفُورٌ رَّحِيمٌ»
- **THEN** they SHALL NOT share a passage

### Requirement: An offline shared-passage dataset

The system SHALL ship `data/derived/quran_passages.json`, built model-free by
`scripts/build_quran_passages.py`, registered in `quran_data/paths.py` and `manifest.py`, read through
one cached loader. Each passage SHALL record both refs (lower surah first), both aligned word spans,
the matched count and the matched content roots. Two builds over the same inputs SHALL be
byte-identical. Pairs whose token multisets share fewer than 6 tokens MAY be skipped, since they cannot
pass.

#### Scenario: Every stored passage passes the definition

- **WHEN** the dataset is read
- **THEN** every passage SHALL join two different surahs, have `k ≥ 6`, `k ≥ 0.75 ×` its longer span
  and ≥ 3 matched positions joining two content words (words carrying a root)

### Requirement: Model-free routes serve the passage map and a cell's passages

`GET /quran-passages/matrix` SHALL return all 114 surah names, the non-empty cells `a < b` with their
pair and verse counts, `total_pairs` and `max_pairs`. `GET /quran-passages/pairs/{a}/{b}` SHALL return
both surah names, the verse counts and the pairs, `u` in the lower surah, ordered by matched words
descending then `(u, v)`, each with `words` and the passage's half-open character span in each verse's
`text_ar_tashkil`. `a == b` SHALL be a 422 before any read, an empty cell a 200 with no pairs, `(b, a)`
the same answer as `(a, b)`, and a missing or unreadable dataset a 503 naming
`python scripts/build_quran_passages.py`.

#### Scenario: The span marks the passage in the displayed text

- **WHEN** the pairs of cell (28, 36) are requested
- **THEN** the 28:20/36:20 pair SHALL carry spans whose text, in each verse's `text_ar_tashkil`, starts
  with «وَجَاءَ» and ends with «قَالَ»

### Requirement: The map switches between the two relations

The cross-surah map mode SHALL offer a switch «الآيات المتشابهات» / «المقاطع المشتركة», the first by
default. With the second, the chart SHALL show the passage matrix under the same rules, and a picked
cell SHALL list its pairs with each verse's passage highlighted and the matched word count; a verse
SHALL open «الآية في سياقها».

#### Scenario: Picking a passage cell

- **WHEN** the reader switches to «المقاطع المشتركة» and picks cell (28, 36)
- **THEN** the list SHALL show 28:20 and 36:20 with «وَجَاءَ … قَالَ» highlighted in both

### Requirement: Measured against a gold set drafted blind

A gold set of cross-surah pairs SHALL be drafted from the verse texts before the build runs on the
corpus, and an evaluation script SHALL report recall of its positives and the negatives found against a
target pre-registered in tasks.md, refusing a gold file whose digest differs from the dataset header's.

#### Scenario: The header names the gold set

- **WHEN** the dataset header is read
- **THEN** its gold digest SHALL equal the sha256 of the committed gold file

