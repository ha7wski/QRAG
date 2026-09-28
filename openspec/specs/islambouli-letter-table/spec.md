# islambouli-letter-table Specification

## Purpose

Samer Islambouli's letter table, transcribed verbatim from a poster that prints the book and the author, never curated, and frozen by digest — so that the one remaining risk of a transcribed table, a wrong copy, is checked mechanically.

## Requirements

### Requirement: The table is transcribed from the poster, as printed

`data/references/islambouli_letters.csv` SHALL hold one row per row of the poster
`data/source/islambouli_letters_poster.png` — **29 rows**, indexed 0–28 by the poster's own
numbering — with the columns `row`, `label_as_printed`, `text_as_printed`, `text`, `status`,
`reading_note`.

`text_as_printed` SHALL reproduce the image: fused words, punctuation (including the commas before
«أو» on rows 18, 20, 21, 24 and the final periods where printed) and every diacritic that is legible
on the image. `text` SHALL differ from `text_as_printed` **only by whitespace**. A mark that cannot
be read at the image's resolution SHALL NOT be transcribed and SHALL be named in `reading_note`.

A reading supplied from outside the image — including the user's — SHALL NOT be stored and SHALL NOT
prevail over the image.

#### Scenario: The separated form is the printed form

- **WHEN** the validator compares `text` and `text_as_printed` with all whitespace removed
- **THEN** they SHALL be byte-identical for every row
- **AND** any row where they differ SHALL fail validation, naming the row

#### Scenario: An unreadable mark is left out and named

- **WHEN** row 12 (ش) is transcribed
- **THEN** its text SHALL be «انتشار وتفش.» with no shadda and no tanween
- **AND** `reading_note` SHALL state that a mark below the line could not be read

#### Scenario: The table has exactly the poster's rows

- **WHEN** the CSV is loaded
- **THEN** it SHALL have 29 rows with `row` values 0–28, each once
- **AND** row 26's `label_as_printed` SHALL be «آ - ى» and row 25's «هـ»

### Requirement: No row is attested, and no page is recorded

Every row's `status` SHALL be `transcribed_from_poster`. The value `attested` SHALL NOT be accepted
by the validator in this version. The lock's source SHALL name the authority (سامر إسلامبولي،
«علمية اللسان العربي وعالميته»), the witness file and its sha256, `witness_origin` («supplied by the
user, origin unrecorded»), an **empty** `pages` list, and `witness_imprint`: every printed text on the
poster outside the table — title band, banner, footer, and the cut-off top edge. Each is transcribed
verbatim, with `text_as_printed` and a `text` equal to it up to whitespace, under the same rule as the
rows: a mark that cannot be read is left out and named in `reading_note`, and a text that cannot be
read at all is recorded empty with its note. `attribution_basis` SHALL state that title and author are
printed on the witness and transcribed in `witness_imprint`, together with the user's statement that
the witness reproduces the book's table. The recorded witness SHALL be the original image (sha256
`e64906b3b351539cc600f1bff88c9156b703142f740df5a691fac56feabcac0c`). The truncated first deposit
SHALL NOT be the recorded witness, and its digest SHALL NOT appear in any dataset.

#### Scenario: A page cannot be recorded without having been read

- **WHEN** any row carries `attested`, or the lock's source carries a non-empty `pages`
- **THEN** validation SHALL fail

#### Scenario: The attribution rests on the printed imprint

- **WHEN** the lock is read
- **THEN** `witness_imprint` SHALL hold the title band, the banner, the footer and the top edge, each
  passing the whitespace-stripped identity check
- **AND** the banner SHALL be non-empty, and an empty entry SHALL carry a `reading_note`
- **AND** `attribution_basis` SHALL name `witness_imprint`
- **AND** the documentation SHALL NOT cite the book with a page

#### Scenario: The witness on disk is the recorded one

- **WHEN** the file at the witness path does not hash to the lock's `witness_sha256`
- **THEN** validation SHALL fail

### Requirement: The hamza row's relation is recorded as text only

Row 0's clause «وهو جزء من صوت (آ)» SHALL be stored in the row's text and nowhere else. No field,
edge or rule SHALL encode a relation between row 0 and row 26, and no consumer SHALL split the
clause from the gloss.

#### Scenario: The relation is not structured

- **WHEN** the dataset and its consumers are inspected
- **THEN** no column other than `text_as_printed`/`text` SHALL mention row 26 from row 0
- **AND** a reading placing row 0 SHALL show its full text, clause included

### Requirement: The table is frozen and changes only against the image

`islambouli_letters.lock.json` SHALL carry `version`, `frozen_on`, the sha256 of the CSV bytes and a
`history[]` of sourced entries. The freeze SHALL be committed before any `uses[]` of the second
holdout is written. A row SHALL change **only** to correct a transcription error demonstrated against
the image, through a new lock version whose reason names the row and the evidence. A row SHALL NOT
change because a root reads badly: that would stop citing Islambouli.

#### Scenario: A digest mismatch is loud

- **WHEN** the CSV bytes do not hash to the lock's `sha256`
- **THEN** validation SHALL fail and the composer SHALL refuse to load the table

#### Scenario: A rescue edit is refused

- **WHEN** a change edits a row's text with a reason that cites a root, a use or `k / 40`
- **THEN** it SHALL be refused
- **AND** only a reason citing the image (row, crop) SHALL be admissible

#### Scenario: A measurement stays attached to its table

- **WHEN** a later lock version changes any row
- **THEN** the recorded readings and verdicts SHALL keep the lock version and sha256 they ran on
