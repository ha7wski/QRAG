## MODIFIED Requirements

### Requirement: Two read-only routes serve the index

The system SHALL serve two routes:
- `GET /roots`, which returns the 28 letter groups in order, each with its label and its number of
  roots;
- `GET /roots/letter/{letter}`, which returns that group's roots in order, each one carrying:
  - `root`;
  - `words`, `ayat` and `surahs` (counts);
  - `verse_ids`;
  - `surah_list` (number and Arabic name);
  - `forms` (the distinct written forms, from `root_forms`);
  - `reading` (sentence and label), or `reading_refusal`.

`GET /roots/letter/{letter}` SHALL also carry `maani`: the group letter's projection of the
«معاني الحروف» sheet (see `letter-meaning-sheet`), read for the label itself, except the «أ» group,
which reads the sheet's `ا`. `maani` SHALL be null when the sheet has no entry for the letter, is
missing or cannot be read; that SHALL never fail the request.

`{letter}` SHALL accept the group label and any letter that folds into it, so `ا`, `أ` and `ء` all
return the «أ» group. An unknown letter SHALL return 404.

Neither route SHALL call an LLM, load the embedder or load a reranker.

#### Scenario: Letter list

- **WHEN** `GET /roots` is called
- **THEN** it returns 28 groups whose counts sum to the number of listed roots

#### Scenario: A hamza-carrier path resolves to the group

- **WHEN** `GET /roots/letter/ء` is called
- **THEN** the response equals that of `GET /roots/letter/أ`

#### Scenario: The letter's sheet travels with its roots

- **WHEN** `GET /roots/letter/ر` is called
- **THEN** `maani.letter` is `ر` and `maani.core_sense` is «التكرار وعودة الحركة»

#### Scenario: The hamza group reads alif

- **WHEN** `GET /roots/letter/أ` is called
- **THEN** `maani.letter` is `ا`

#### Scenario: A missing sheet does not cost the roots

- **WHEN** the sheet cannot be loaded and `GET /roots/letter/ك` is called
- **THEN** the response is 200 with its roots and `maani` null

#### Scenario: No model memory is paid

- **WHEN** both routes have been called on a fresh backend
- **THEN** `GET /health` still reports the embedder and the reranker as not loaded

### Requirement: The «فهرس الجذور» page

The `/roots` page SHALL show a strip of the 28 letters, each with its root count. The strip buttons
SHALL show the letter and its count only. Selecting a letter SHALL show, in this order, the group
heading, then — when the response carries a non-null `maani` — one box describing the selected
letter, then that group's roots, one card per root.

The letter box SHALL show, in Arabic: the letter and its name, the badge «تأويلي» and its series;
its core sense; its three positions (أول / وسط / آخر), each with its divine name or the
substitute-word tag, its sense, its examples and its origin; the readings by source, each beside its
authority's name; and its drawing, its structure and, when present, its dimensions. The box SHALL
NOT be folded. When `maani` is null, no box and no placeholder SHALL be shown.

Each card SHALL always show its root and its three counts. Everything else on the card SHALL be
**folded by default** and unfolded by activating the card's header:
- the letter reading and its label, or its refusal reason;
- «السور»: the distinct sūras, each a link to `/surah/{n}`;
- «المواضع»: the root's distinct written forms (ألفاظ) as `VerseLookup.root_forms(root)["forms"]`
  returns them, in that order — the Quran's words that come from this root;
- two links styled as primary (green) buttons: `/verse-study?word=<root>` («الكلمة في الآيات») and,
  to its left, `/lexical?word=<root>` («تحليل لساني»).

The card SHALL NOT list the āyāt nor carry an āya control: «الكلمة في الآيات» is where a root's āyāt
are read. The API still serves `verse_ids`.

The selected letter SHALL be reflected in the URL (`/roots?letter=<letter>`) by a history PUSH, so
that a letter can be deep-linked and the browser's Back returns to the previously selected letter.
All Arabic text SHALL render RTL through `ArabicText`.

#### Scenario: Opening a letter

- **WHEN** the reader opens `/roots?letter=ك`
- **THEN** the «ك» group's roots are listed, each card showing its root and counts only

#### Scenario: The letter box precedes the roots

- **WHEN** the reader selects «ر»
- **THEN** a box showing «ر», «راء», «تأويلي» and «التكرار وعودة الحركة» appears
- **AND** it comes after the group heading and before the first root card
- **AND** it lists the three positions with الرزاق at أول

#### Scenario: No box without a sheet

- **WHEN** the letter response carries `maani: null`
- **THEN** the roots are listed and no letter box is rendered

#### Scenario: The strip stays compact

- **WHEN** the letter strip is shown
- **THEN** no button carries any text besides its letter and its count

#### Scenario: A card unfolds

- **WHEN** the reader activates the header of the card of ضرب
- **THEN** its reading, «السور», «المواضع» and the «الكلمة في الآيات» button appear
- **AND** «المواضع» comes right after «السور» and lists the forms of `root_forms("ضرب")`
- **AND** activating the header again folds the card, the root staying visible

#### Scenario: No āya list, two green links

- **WHEN** a card is unfolded
- **THEN** it shows no āya link and no āya control
- **AND** besides the sūra chips it links to `/verse-study?word=<root>` and, to its left,
  `/lexical?word=<root>`, both on green buttons

#### Scenario: Back returns to the previous letter

- **WHEN** the reader selects «ب», then «ك», then presses the browser's Back
- **THEN** the URL is `/roots?letter=ب` and the «ب» group is listed

#### Scenario: Jump to the root's āyāt

- **WHEN** the reader follows a root's «الكلمة في الآيات» button
- **THEN** `/verse-study` opens on that root's «الكلمة في الآيات» results
