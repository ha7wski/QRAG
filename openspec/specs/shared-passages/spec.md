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

### Requirement: Measured against a gold set drafted blind

A gold set of cross-surah pairs SHALL be drafted from the verse texts before the build runs on the
corpus, and an evaluation script SHALL report recall of its positives and the negatives found against a
target pre-registered in tasks.md, refusing a gold file whose digest differs from the dataset header's.

#### Scenario: The header names the gold set

- **WHEN** the dataset header is read
- **THEN** its gold digest SHALL equal the sha256 of the committed gold file

