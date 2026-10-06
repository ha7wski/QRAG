# surah-reading-annotations Specification

## Purpose
Define the closeness annotations of the «سور القرآن» reading page: an opt-in switch (off by default)
that colours, on the continuous reading text, the āyāt that are close to another āya of their own sūra
(green background over the whole āya, from the intra-sūra groups) and those close to āyāt of other
sūras (an orange ring on the marker for a whole-verse pair, an orange background on the shared words
for a passage-only pair), an in-page bubble listing an āya's close verses without any navigation, and
the one model-free route that feeds them.
## Requirements
### Requirement: The reader switches the annotations on and off

The reading page SHALL offer one switch that shows or hides the closeness annotations. The switch
SHALL be off by default, and its state SHALL be remembered per browser across visits and across
sūras. While it is off, the page SHALL render exactly as it does without this capability, and SHALL
NOT request the annotations.

While it is on, a legend SHALL name the three cues in Arabic: in this order — the green āya background «آية
قريبة داخل السورة», the orange word background «جزء مشترك في سائر القرآن», and the orange marker ring «آية
قريبة في سائر القرآن».

#### Scenario: Off by default

- **WHEN** a reader opens a sūra for the first time
- **THEN** no āya is coloured, no legend is shown and `GET /surah/{number}/annotations` is not called

#### Scenario: The choice is remembered

- **WHEN** the reader turns the annotations on, then opens another sūra or reloads the page
- **THEN** the annotations are shown there too

### Requirement: Green marks an āya close to another āya of its own sūra

An āya SHALL be annotated green when it belongs to one of its sūra's groups in
`surah_similarity.json` — the same groups «المتقاربات داخل السورة» shows, never the wider neighbour
lists. The green cue SHALL be a green background over the āya's WHOLE text; its `﴿n﴾` marker SHALL
NOT be coloured green.

#### Scenario: A group member is green

- **WHEN** sūra 3 is read with annotations on
- **THEN** the whole texts of 3:10 and 3:116 (one group) have a green background, and their markers do not

#### Scenario: A neighbour outside every group is not green

- **WHEN** an āya has intra-sūra neighbours but belongs to no group
- **THEN** its text carries no green background

### Requirement: Orange marks closeness in other sūras, split by relation

An āya SHALL be annotated orange when it appears in at least one pair of `quran_close_verses.json`.
The form of the cue SHALL be decided by each pair's relation, never by a coverage threshold:

- a pair whose `from` contains `similarity` (whole-verse closeness) SHALL colour the āya's `﴿n﴾`
  marker orange;
- a pair whose `from` is `passage` alone SHALL colour orange only the characters of the āya's common
  part, through the pair's stored character span in the displayed `text_ar_tashkil`.

When several passage-only pairs cover the same āya, the coloured characters SHALL be the union of
their spans. A span SHALL be applied only to the vocalized text it was computed against; when the āya
is rendered from its undiacritized fallback, its passage-only cue SHALL fall back to the orange marker.

#### Scenario: Whole-verse closeness colours the marker

- **WHEN** sūra 1 is read with annotations on
- **THEN** the marker of 1:2 (whole-verse pair with 37:182) is orange and none of its words are

#### Scenario: A shared passage colours only the passage

- **WHEN** sūra 28 is read with annotations on
- **THEN** in 28:20 exactly the characters of its stored span with 36:20 (from «وَجَاءَ» to «قَالَ») are
  orange
- **AND** the rest of 28:20 keeps the normal colour

#### Scenario: Overlapping passages merge

- **WHEN** two passage-only pairs of one āya have overlapping spans
- **THEN** the overlap is coloured once, as one continuous run

### Requirement: An āya that is close in both ways shows both cues

When an āya qualifies for green and for orange, both cues SHALL be visible together; neither colour
SHALL replace the other: the green background of the āya text SHALL leave an orange-ringed marker
visible, and orange passage words SHALL stay orange on top of the green text.

#### Scenario: Both relations at once

- **WHEN** an āya belongs to an intra-sūra group and has a whole-verse pair in another sūra
- **THEN** its text has the green background and its marker the orange ring, at the same time

### Requirement: Clicking an annotated āya opens an in-page bubble of its close verses

Clicking (or activating with the keyboard) the marker of an annotated āya, or any of its orange words,
SHALL open a bubble anchored on the page, without navigating and without changing the URL. The bubble
SHALL list the āya's close verses in two sections, each omitted when empty:

- «داخل السورة»: the other members of its group, in mushaf order;
- «في سائر القرآن»: every partner of its pairs, score descending, each with its sūra name and āya
  number, its vocalized text, and its common part marked when the pair carries one.

No entry in the bubble SHALL be a link. The bubble SHALL close on Escape, on a click outside it, and
when another āya's bubble is opened. Only annotated āyāt SHALL be clickable.

#### Scenario: Opening the bubble does not navigate

- **WHEN** the reader clicks the marker of 28:20
- **THEN** a bubble lists 36:20 under «في سائر القرآن» with its common part marked
- **AND** the URL and the scroll position of the page are unchanged

#### Scenario: Closing the bubble

- **WHEN** the bubble is open and the reader presses Escape or clicks outside it
- **THEN** the bubble closes

#### Scenario: Unannotated āyāt are inert

- **WHEN** the reader clicks the marker of an āya with no annotation
- **THEN** nothing opens

### Requirement: One route serves a sūra's annotations

`GET /surah/{number}/annotations` SHALL return, for one sūra, every annotated āya with: its group
partners (āya numbers), its whole-verse partners and its passage-only partners (each with the
partner's reference, the pair's score and, where present, the character span in this āya and in the
partner), plus a record — through `verse_from_record` — for every partner verse the bubble lists. It
SHALL be a model-free static lookup over `surah_similarity.json` and `quran_close_verses.json`.

A sūra with no annotation SHALL answer 200 with an empty list. A sūra outside 1..114 SHALL be a 422.
Either dataset missing or malformed SHALL be a 503 whose detail carries its rebuild command.

#### Scenario: A sūra without any closeness

- **WHEN** the annotations of a sūra with no group and no pair are requested
- **THEN** the route answers 200 with an empty list of āyāt

#### Scenario: A missing dataset

- **WHEN** `quran_close_verses.json` is absent
- **THEN** the route answers 503 with the dataset's rebuild command
- **AND** the reading page shows the sūra unannotated with an Arabic notice, never an error in place of
  the text

