## MODIFIED Requirements

### Requirement: The «سور القرآن» page reads one whole sūra

The application SHALL offer a page whose purpose is reading, not analysis: a sūra picker,
and below it the chosen sūra rendered in full.

The sūra SHALL be rendered as one continuous Arabic block, fully vocalized, each āya
followed by its number in Arabic-Indic digits inside āya brackets `﴿…﴾`. No translation, no
transliteration and no per-āya card SHALL appear on this page. No analytical annotation SHALL
appear either, except the closeness annotations of `surah-reading-annotations`, and those only
while the reader has turned them on (they are off by default).

An āya SHALL be rendered from its vocalized text when the API provides one, and from its
undiacritized text otherwise.

#### Scenario: Reading a sūra

- **WHEN** a sūra is chosen and the annotations are off
- **THEN** all of its āyāt are rendered as one continuous vocalized Arabic block
- **AND** each āya is followed by its number in Arabic-Indic digits inside `﴿…﴾`
- **AND** no translation or analytical annotation is shown.

#### Scenario: Annotations are the reader's choice

- **WHEN** the reader turns the annotations on
- **THEN** the closeness annotations appear on the same continuous block, which stays one block
- **AND** no other analytical annotation appears.

#### Scenario: The reading page shows no Latin text

- **WHEN** the page is rendered
- **THEN** every string on it is Arabic, apart from data that is legitimately Latin.
