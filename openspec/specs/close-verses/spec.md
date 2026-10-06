# close-verses Specification

## Purpose
Answer «which verses of other surahs are close to this one, or repeat its wording?» with ONE relation: the union of whole-verse closeness and shared passages, ranked by a combined score, each pair carrying its common part for display.
## Requirements
### Requirement: One relation joins close verses and shared passages

Two verses of different surahs SHALL be a close pair when the cross-surah similarity dataset stores
the pair in either verse's neighbour list, or the shared-passage dataset holds a passage for it.
The pair set SHALL be exactly that union: no pair of either input SHALL be dropped, and no pair
outside both SHALL be added. Each pair SHALL record which input holds it. The two input relations
SHALL keep their own definitions, parameters and builds.

#### Scenario: A pair only the passage relation holds

- **WHEN** the dataset is read
- **THEN** the pair 28:20 / 36:20 SHALL be present with `from` naming the passage relation

#### Scenario: A pair only the similarity relation holds

- **WHEN** a pair is stored by the similarity dataset and shares no passage
- **THEN** it SHALL be present with `from` naming the similarity relation alone

#### Scenario: The size is the union's

- **WHEN** the dataset is built
- **THEN** the number of pairs SHALL equal the number of distinct unordered pairs in the two inputs

### Requirement: A combined score orders the pairs

Each pair SHALL carry `sim`, `pas` and `score = 1 − (1 − sim)(1 − pas)`, each in `[0, 1]`.

`sim` SHALL be the cross-surah similarity score `sem × syn`: for a pair the similarity dataset
stores, its stored score, read and not recomputed; for any other pair, the score computed by the
similarity build's own functions with no gate applied (syntax gate, short-pair rule, candidate cap,
semantic gate, relative cut and K), `dense` being the cosine's percentile among the similarity
build's syntax survivors and ignored between verbatim verses.

`pas` SHALL be, for a pair holding a shared passage, the passage's matched words divided by the word
count of the shorter verse, and 0 for every other pair. A common part shorter than a passage SHALL
NOT contribute to `pas`.

Pairs SHALL be ordered by score descending, ties broken by reference ascending.

#### Scenario: Without a passage the score is the similarity score

- **WHEN** a pair has no shared passage
- **THEN** its `pas` SHALL be 0 and its `score` SHALL equal its `sim`

#### Scenario: Both measures raise the score

- **WHEN** a pair has `sim > 0` and `pas > 0`
- **THEN** its `score` SHALL be at least the larger of the two
- **AND** before rounding it SHALL be greater than both when both are below 1 (a measure equal to 1
  makes the score 1)

#### Scenario: Two aligned frame words do not score

- **WHEN** 26:203 and 37:54 are read
- **THEN** their `pas` SHALL be 0

### Requirement: Every pair carries its common part when it has one

A pair's common part SHALL be the order-invariant matching of the two verses' content words, so that a
word shared by both verses is part of it whatever its position in each. A content word SHALL be a word
that carries a root and whose occurrence is not a grammatical tool in `word_function.json`. The
matching SHALL be a maximum-weight one-to-one matching in which two content words are joined with
weight 1 when they have the same lemma token (the passage relation's token), with weight 0.5 when they
have different lemma tokens but the same resolved primary root, and not at all otherwise; among
partners of equal weight a word SHALL take the one at the nearest relative position. A pair SHALL
carry a common part when the matching joins at least 2 words, and none otherwise.

Function words SHALL be coloured with the common part only when they sit strictly between two matched
pairs that run in the same order in both verses (word `p` before `p'` in one, its partner `q` before
`q'` in the other) with no matched pair lying between them in both verses at once, and the sequences of
UNMATCHED words between them are identical in the two verses (and not empty). Matched words between
them in one verse only — a displaced shared word — SHALL be skipped by that comparison, not block it.
Bridged words SHALL NOT be counted as matched words.

A common part SHALL be recorded as its matched word pairs (`m`: word number in the lower-surah verse,
word number in the other, and whether the pair shares the lemma or only the root) and, for each verse,
a list of half-open character spans in its displayed `text_ar_tashkil` (Basmala stripped), one per run
of consecutive coloured words, computed at build time. These three fields SHALL be present together or
absent together. A pair holding a shared passage SHALL still record that passage's matched word count
and word spans, which `pas` reads. The pair set, `sim`, `pas` and `score` SHALL NOT depend on the
common part.

#### Scenario: A shared word in another order is coloured on both sides

- **WHEN** the pair 2:3 / 14:31 is read
- **THEN** its matched pairs SHALL include word 8 of 2:3 («يُنفِقُونَ») with word 7 of 14:31
  («وَيُنفِقُوا»)
- **AND** no span of 2:3 SHALL cover word 3 («بِالْغَيْبِ»), which 14:31 does not hold

#### Scenario: The span marks the passage in the displayed text

- **WHEN** the pair 28:20 / 36:20 is read
- **THEN** each verse SHALL have one span, whose text starts with «وَجَاءَ» and ends with «قَالَ»

#### Scenario: Spans agree with the word index

- **WHEN** any stored common part is checked against `word_index.json`
- **THEN** each character span SHALL run from its first word's start to its last word's end, rebased
  past the stripped Basmala, and every matched word SHALL lie inside one span of its verse

#### Scenario: A single shared word is not a common part

- **WHEN** the matching of a pair joins one word
- **THEN** the pair SHALL carry no common part

#### Scenario: The scores do not move

- **WHEN** the dataset is rebuilt under this rule from unchanged inputs
- **THEN** every pair's `sim`, `pas` and `score`, and the pair set, SHALL equal the previous build's

### Requirement: An offline close-verses dataset

The system SHALL ship `data/derived/quran_close_verses.json`, built by
`scripts/build_quran_close_verses.py` from `quran_similarity.json` and `quran_passages.json`,
registered in `quran_data/paths.py` and `quran_data/manifest.py` (producer, inputs, consumers,
rebuild command, build order, backend-must-be-stopped note) and read only through one cached loader
that refuses an unknown schema with the rebuild command.

The header SHALL name the score, `sim` and `pas` rules, the common-part parameters, the models, the
sha256 of each input dataset and the sha256 of each gold file. The build SHALL import the similarity
and passage builders' functions rather than copy them, SHALL recompute `dense` for every pair the
similarity dataset stores and refuse to write when it differs from the stored value, and SHALL fail
on a common part whose span leaves the displayed text. Two builds over the same inputs SHALL be
byte-identical.

#### Scenario: A missing dataset names its rebuild command

- **WHEN** the loader is called and `quran_close_verses.json` is absent
- **THEN** it SHALL raise `DatasetMissing` naming `python scripts/build_quran_close_verses.py`

#### Scenario: The header proves what was composed

- **WHEN** the header is read after a build
- **THEN** its input digests SHALL equal the sha256 of the two input files on disk

#### Scenario: A stale similarity dataset stops the build

- **WHEN** a recomputed `dense` differs from the value the similarity dataset stores
- **THEN** the build SHALL write nothing and name the rebuild order

### Requirement: Measured against both gold sets with targets registered beforehand

An evaluation script SHALL measure the dataset against the similarity gold set and the passage gold
set, unchanged, and SHALL refuse to report when either gold digest or either input digest differs
from the header's. It SHALL report the positives present per gold sample, the negatives present per
kind, `neg_same_subject_diff_syntax` apart, the AUC of `score`, of `sim` and of `pas` over the gold
positives present against the gold negatives present, the pair 28:20 / 36:20 and the pair
26:203 / 37:54, against the targets registered in the change's design before the build. A result
short of a target SHALL be recorded as the result, and no parameter SHALL be changed after the
build to meet it.

#### Scenario: Another gold file is refused

- **WHEN** a gold file's sha256 differs from the one in the dataset header
- **THEN** the script SHALL refuse to report

#### Scenario: The ordering is reported with its counts

- **WHEN** the evaluation runs
- **THEN** it SHALL print the AUC of the score together with the number of positives and negatives
  it was computed on

