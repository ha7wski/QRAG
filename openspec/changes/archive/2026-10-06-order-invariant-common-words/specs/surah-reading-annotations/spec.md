## MODIFIED Requirements

### Requirement: Orange marks closeness in other sūras, split by relation

An āya SHALL be annotated orange when it appears in at least one pair of `quran_close_verses.json`.
The form of the cue SHALL be decided by each pair's relation, never by a coverage threshold:

- a pair whose `from` contains `similarity` (whole-verse closeness) SHALL colour the āya's `﴿n﴾`
  marker orange;
- a pair whose `from` is `passage` alone SHALL colour orange only the characters of the āya's common
  part, through the pair's stored list of character spans in the displayed `text_ar_tashkil`.

When several spans cover the same āya, from one pair or several passage-only pairs, the coloured
characters SHALL be the union of those spans. A span SHALL be applied only to the vocalized text it
was computed against; when the āya is rendered from its undiacritized fallback, its passage-only cue
SHALL fall back to the orange marker.

#### Scenario: Whole-verse closeness colours the marker

- **WHEN** sūra 1 is read with annotations on
- **THEN** the marker of 1:2 (whole-verse pair with 37:182) is orange and none of its words are

#### Scenario: A shared passage colours only the passage

- **WHEN** sūra 28 is read with annotations on
- **THEN** in 28:20 exactly the characters of its stored span with 36:20 (from «وَجَاءَ» to «قَالَ») are
  orange
- **AND** the rest of 28:20 keeps the normal colour

#### Scenario: A shared word in another order is coloured

- **WHEN** sūra 2 is read with annotations on
- **THEN** in 2:3 «يُنفِقُونَ» is orange and «بِالْغَيْبِ» is not

#### Scenario: Overlapping passages merge

- **WHEN** two passage-only pairs of one āya have overlapping spans
- **THEN** the overlap is coloured once, as one continuous run

### Requirement: One route serves a sūra's annotations

`GET /surah/{number}/annotations` SHALL return, for one sūra, every annotated āya with: its group
partners (āya numbers), its whole-verse partners and its passage-only partners (each with the
partner's reference, the pair's score and, where present, the list of character spans in this āya and
in the partner), plus a record — through `verse_from_record` — for every partner verse the bubble
lists. It SHALL be a model-free static lookup over `surah_similarity.json` and
`quran_close_verses.json`.

A sūra with no annotation SHALL answer 200 with an empty list. A sūra outside 1..114 SHALL be a 422.
Either dataset missing or malformed SHALL be a 503 whose detail carries its rebuild command.

#### Scenario: A sūra without any closeness

- **WHEN** the annotations of a sūra with no group and no pair are requested
- **THEN** the route answers 200 with an empty list of āyāt

#### Scenario: Spans are lists oriented to the āya

- **WHEN** the annotations of sūra 2 are requested
- **THEN** 2:3's partner 14:31 carries a list of spans in 2:3 that covers «يُنفِقُونَ» and a list of
  spans in 14:31 that covers «وَيُنفِقُوا»

#### Scenario: A missing dataset

- **WHEN** `quran_close_verses.json` is absent
- **THEN** the route answers 503 with the dataset's rebuild command
- **AND** the reading page shows the sūra unannotated with an Arabic notice, never an error in place of
  the text
