## MODIFIED Requirements

### Requirement: The reader switches the annotations on and off

The reading page SHALL offer one switch that shows or hides the closeness annotations. The switch
SHALL be off by default, and its state SHALL be remembered per browser across visits and across
sūras. While it is off, the page SHALL render exactly as it does without this capability, and SHALL
NOT request the annotations.

While it is on, a legend SHALL name the two cues in Arabic, in this order: the green āya background
«آية قريبة داخل السورة», and the orange marker with orange words «آية قريبة في سائر القرآن». No other
cue SHALL be named.

#### Scenario: Off by default

- **WHEN** a reader opens a sūra for the first time
- **THEN** no āya is coloured, no legend is shown and `GET /surah/{number}/annotations` is not called

#### Scenario: The choice is remembered

- **WHEN** the reader turns the annotations on, then opens another sūra or reloads the page
- **THEN** the annotations are shown there too

#### Scenario: Two legend entries

- **WHEN** the annotations are on
- **THEN** the legend shows exactly two entries, green then orange

### Requirement: An āya that is close in both ways shows both cues

When an āya qualifies for green and for orange, both cues SHALL be visible together; neither colour
SHALL replace the other: the green background of the āya text SHALL leave the orange marker visible,
and orange common-part words SHALL stay orange on top of the green text.

#### Scenario: Both relations at once

- **WHEN** an āya belongs to an intra-sūra group and has a close verse in another sūra
- **THEN** its text has the green background, its marker is orange and its common-part words are
  orange, at the same time

### Requirement: One route serves a sūra's annotations

`GET /surah/{number}/annotations` SHALL return, for one sūra, every annotated āya with: its group
partners (āya numbers) and ONE list `cross` of its partners in other sūras — every pair of
`quran_close_verses.json` holding it, whatever relation produced the pair — score descending, ties in
mushaf order, each with the partner's reference, the pair's score, its matched word count and, where
present, the list of character spans in this āya (`spans_self`) and in the partner (`spans_other`);
plus a record — through `verse_from_record` — for every partner verse the bubble lists. It SHALL be a
model-free static lookup over `surah_similarity.json` and `quran_close_verses.json`. The response SHALL
NOT carry `whole` nor `passage`.

A sūra with no annotation SHALL answer 200 with an empty list. A sūra outside 1..114 SHALL be a 422.
Either dataset missing or malformed SHALL be a 503 whose detail carries its rebuild command.

#### Scenario: A sūra without any closeness

- **WHEN** the annotations of a sūra with no group and no pair are requested
- **THEN** the route answers 200 with an empty list of āyāt

#### Scenario: Whole-verse and passage partners share one list

- **WHEN** the annotations of sūra 28 are requested
- **THEN** 28:20's `cross` list holds 36:20, and no āya entry carries a `whole` or `passage` key

#### Scenario: Spans are lists oriented to the āya

- **WHEN** the annotations of sūra 2 are requested
- **THEN** 2:3's partner 14:31 carries a list of spans in 2:3 that covers «يُنفِقُونَ» and a list of
  spans in 14:31 that covers «وَيُنفِقُوا»

#### Scenario: A missing dataset

- **WHEN** `quran_close_verses.json` is absent
- **THEN** the route answers 503 with the dataset's rebuild command
- **AND** the reading page shows the sūra unannotated with an Arabic notice, never an error in place of
  the text

## REMOVED Requirements

### Requirement: Orange marks closeness in other sūras, split by relation

**Reason**: two orange cues for one relation hid a whole-verse pair's shared words (2:2 carried a ring
while «الْكِتَابُ لَا رَيْبَ» stayed plain) and made the reader decode which relation produced a pair.
**Migration**: replaced by «Orange marks an āya close to a verse of another sūra, with its common
parts»: every pair now colours the marker AND its common part.

## ADDED Requirements

### Requirement: Orange marks an āya close to a verse of another sūra, with its common parts

An āya SHALL be annotated orange when it appears in at least one pair of `quran_close_verses.json`,
whatever relation produced the pair. The orange cue SHALL be one cue in two parts, both decided by the
same pairs and never by the relation:

- the āya's `﴿n﴾` marker SHALL be orange;
- the characters of the āya's common part with EACH of its partners SHALL be coloured orange, through
  the pair's stored list of character spans in the displayed `text_ar_tashkil`. A pair without a common
  part colours no word, and its āya still carries the orange marker.

When several spans cover the same āya, from one pair or several, the coloured characters SHALL be the
union of those spans. A span SHALL be applied only to the vocalized text it was computed against; when
the āya is rendered from its undiacritized fallback, only its orange marker SHALL be shown.

#### Scenario: A whole-verse pair now colours its shared words

- **WHEN** sūra 2 is read with annotations on
- **THEN** the marker of 2:2 is orange
- **AND** if 2:2 is still paired with 32:2 after the rebuild, «الْكِتَابُ» and «رَيْبَ» in 2:2 are orange

#### Scenario: A shared passage colours only the passage

- **WHEN** sūra 28 is read with annotations on
- **THEN** the marker of 28:20 is orange and exactly the characters of its stored span with 36:20 (from
  «وَجَاءَ» to «قَالَ») are orange
- **AND** the rest of 28:20 keeps the normal colour

#### Scenario: A shared word in another order is coloured

- **WHEN** sūra 2 is read with annotations on
- **THEN** in 2:3 «يُنفِقُونَ» is orange and «بِالْغَيْبِ» is not

#### Scenario: A pair without a common part

- **WHEN** an āya's only pair carries no common part
- **THEN** its marker is orange and none of its words are

#### Scenario: Overlapping spans merge

- **WHEN** two pairs of one āya have overlapping spans
- **THEN** the overlap is coloured once, as one continuous run
