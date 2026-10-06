## MODIFIED Requirements

### Requirement: Every pair carries its common part when it has one

A pair's common part SHALL be the order-invariant matching of the two verses' content words, so that a
word shared by both verses is part of it whatever its position in each. A content word SHALL be a content word
as the `surah-internal-similarity` lexical signal defines it (its primary root is among its verse's
content roots, and its occurrence is not a grammatical tool), so the coloured words and the scored
words are the same words. The
matching SHALL be a maximum-weight one-to-one matching in which two content words are joined with
weight 1 when they have the same lemma token (the passage relation's token), with weight 0.5 when they
have different lemma tokens but the same resolved primary root, and not at all otherwise; among
partners of equal weight a word SHALL take the one at the offset of the shared material (the median shift
of the uniquely matched words). A pair SHALL
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

- **WHEN** the common-part fields of every pair are removed and the dataset is composed again
- **THEN** every pair's `sim`, `pas` and `score`, and the pair set, SHALL be unchanged
