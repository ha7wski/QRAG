# surah-reading Specification

## Purpose

Define the one surface of the application whose purpose is **reading** rather than
analysis: a sūra chosen from a picker and rendered whole, as one continuous vocalized
Arabic block, with no translation, no transliteration and no annotation of any kind.

It fixes what belongs on that surface and what does not — the sūra header, the Basmala in
its correct role (a heading for the sūras that open with one, āya `﴿١﴾` in al-Fātiḥa,
absent in at-Tawba), and the āya markers that make a position inside a sūra addressable.
It fixes the addressing contract too: sūra selection lives in the URL, so every sūra on
screen is shareable and the verse references emitted elsewhere in the application keep
landing here. And it fixes what the reader is owed between visits — the sūra and the āya
they had reached, restored when they return through the navigation, while a deep link
still lands where it points.

## Requirements
### Requirement: The «سور القرآن» page reads one whole sūra

The application SHALL offer a page whose purpose is reading, not analysis: a sūra picker,
and below it the chosen sūra rendered in full.

The sūra SHALL be rendered as one continuous Arabic block, fully vocalized, each āya
followed by its number in Arabic-Indic digits inside āya brackets `﴿…﴾`. No translation, no
transliteration, no per-āya card and no analytical annotation SHALL appear on this page.

An āya SHALL be rendered from its vocalized text when the API provides one, and from its
undiacritized text otherwise.

#### Scenario: Reading a sūra

- **WHEN** a sūra is chosen
- **THEN** all of its āyāt are rendered as one continuous vocalized Arabic block
- **AND** each āya is followed by its number in Arabic-Indic digits inside `﴿…﴾`
- **AND** no translation or analytical annotation is shown.

#### Scenario: The reading page shows no Latin text

- **WHEN** the page is rendered
- **THEN** every string on it is Arabic, apart from data that is legitimately Latin.

### Requirement: Sūra selection is carried by the URL

The picker SHALL list all 114 sūras by their Arabic names, preceded by the sūra number in
Arabic-Indic digits.

Choosing a sūra SHALL navigate to that sūra's own address, so that what is on screen is
always shareable and reproducible from the URL alone. Opening a sūra's address directly
SHALL render the same page with the picker already showing that sūra.

The navigation entry SHALL lead to the reading page addressed at the reader's remembered
sūra, falling back to al-Fātiḥa when there is none — matching the sūra pickers elsewhere in
the application, which open on a concrete sūra rather than on an empty prompt.

An āya within a rendered sūra SHALL be individually addressable, so that a position inside
a sūra can be expressed in the address and shared.

#### Scenario: Choosing a sūra

- **WHEN** the reader picks a sūra from the picker
- **THEN** the browser address becomes that sūra's address
- **AND** the sūra is rendered below the picker.

#### Scenario: Opening a sūra address directly

- **WHEN** a sūra's address is opened directly
- **THEN** the page renders that sūra
- **AND** the picker shows it as the current selection.

#### Scenario: Entering from the navigation

- **WHEN** the reader selects «سور القرآن» in the navigation
- **THEN** the reading page opens on the remembered sūra, or on al-Fātiḥa if there is none
- **AND** the address is that sūra's address
- **AND** the navigation entry is highlighted as active.

#### Scenario: An āya is addressable

- **WHEN** a sūra is rendered
- **THEN** each āya carries an address of its own within the page
- **AND** opening the sūra's address with an āya named in it renders the sūra scrolled to
  that āya.

#### Scenario: The navigation entry stays active on a sūra address

- **WHEN** any sūra's address is open
- **THEN** the «سور القرآن» navigation entry is highlighted as active.

### Requirement: The Basmala appears exactly once, in its own role

For a sūra whose Basmala is an opening rather than an āya, the Basmala SHALL be rendered as
a centred heading above the sūra's text, unnumbered and visually distinct from the āyāt.

For al-Fātiḥa no such heading SHALL be rendered: its Basmala is āya 1 and appears in the
body, numbered `﴿١﴾` like any other āya. For at-Tawba no Basmala SHALL be rendered at all.

The page SHALL take this decision from the API field that names the sūra's opening Basmala,
and SHALL NOT re-derive it from the sūra number.

#### Scenario: A sūra that opens with the Basmala

- **WHEN** al-Baqara is rendered
- **THEN** «بسم الله الرحمن الرحيم» appears once, centred above the text, without an āya
  number
- **AND** the body begins «الم ﴿١﴾».

#### Scenario: Al-Fātiḥa

- **WHEN** al-Fātiḥa is rendered
- **THEN** no separate Basmala heading is shown
- **AND** the Basmala appears in the body as āya `﴿١﴾`.

#### Scenario: At-Tawba

- **WHEN** at-Tawba is rendered
- **THEN** no Basmala appears anywhere on the page
- **AND** the body begins «براءة من الله ورسوله».

#### Scenario: The rule is not duplicated in the interface

- **WHEN** the page decides whether to render the heading
- **THEN** it renders the API's Basmala field when non-empty and renders nothing otherwise
- **AND** it contains no test on the sūra's number.

### Requirement: The sūra header names the sūra

Above the Basmala and the text, the page SHALL show the sūra's Arabic name with its number,
its revelation period, and its āya count. Numbers in this header SHALL be Arabic-Indic,
this being a reading context.

The revelation period SHALL be rendered through the interface's period vocabulary; an
unrecognised value SHALL render nothing rather than leak the corpus identifier.

#### Scenario: The header of a sūra

- **WHEN** a sūra is rendered
- **THEN** its Arabic name, its number, its period and its āya count are shown above the
  text, with Arabic-Indic digits.

#### Scenario: An unrecognised period

- **WHEN** the corpus reports a period the interface does not know
- **THEN** the period is omitted
- **AND** the raw corpus value is not displayed.

### Requirement: Existing links into a sūra keep working

References already rendered elsewhere in the application — on a verse card, on a verse
context card, and on the verse page — SHALL continue to open the sūra they name, and SHALL
land on this page.

#### Scenario: Following a sūra reference from a verse card

- **WHEN** the sūra reference on a verse card is followed
- **THEN** the reading page opens on that sūra
- **AND** the address is that sūra's address.

### Requirement: The sūra stepper continues sequential reading

The previous/next sūra links at the foot of the page SHALL be kept alongside the picker.
The picker serves jumping to a sūra; the stepper serves continuing from the one just
finished.

Each link SHALL navigate to the same address the picker would produce for that sūra. A link
SHALL be absent at the range's edge: no previous link on al-Fātiḥa, no next link on an-Nās.

#### Scenario: Continuing to the next sūra

- **WHEN** the next-sūra link is followed at the foot of al-Baqara
- **THEN** Āl ʿImrān is rendered
- **AND** the address is Āl ʿImrān's address
- **AND** the picker shows Āl ʿImrān as the current selection.

#### Scenario: The edges of the range

- **WHEN** al-Fātiḥa is rendered
- **THEN** no previous-sūra link is shown
- **AND** when an-Nās is rendered, no next-sūra link is shown.

### Requirement: The reading position is remembered

The application SHALL remember where the reader left off — the sūra and the āya within it —
and SHALL restore it when the reader returns through the navigation entry.

The position SHALL survive a page reload, closing the tab, and restarting the browser. It
is per-browser and SHALL NOT be synchronised anywhere.

The remembered unit SHALL be the **āya**, not a scroll offset: the reading block reflows
with viewport width and font size, and a position must survive both.

The position SHALL be updated as the reader scrolls, so that leaving the page at any moment
records where they actually were.

#### Scenario: Resuming through the navigation entry

- **WHEN** a reader who last read al-Baqara at āya 200 selects «سور القرآن» in the
  navigation
- **THEN** al-Baqara is rendered
- **AND** the page is scrolled to āya 200.

#### Scenario: The position survives a reload

- **WHEN** the reader reloads the browser, or closes and reopens it, and then enters
  through the navigation entry
- **THEN** the same sūra and āya are restored.

#### Scenario: Nothing has been read yet

- **WHEN** a reader with no stored position enters through the navigation entry
- **THEN** al-Fātiḥa is rendered, from its beginning.

#### Scenario: A deep link is not a resume

- **WHEN** a sūra's address is opened directly, or reached from a verse reference elsewhere
  in the application
- **THEN** the sūra is rendered from its beginning, not from the stored position
- **AND** that sūra becomes the remembered one.

#### Scenario: The stepper advances the position

- **WHEN** the reader follows the next-sūra link
- **THEN** the newly opened sūra becomes the remembered one.

#### Scenario: An unusable stored position

- **WHEN** the stored position is absent, unreadable, or names a sūra outside 1–114 or an
  āya beyond that sūra's length
- **THEN** the reader is taken to al-Fātiḥa from its beginning
- **AND** no error is shown.

#### Scenario: Storage is unavailable

- **WHEN** the browser refuses to store the position — private mode, blocked site data, or
  an exhausted quota
- **THEN** the reading page still renders and remains fully usable
- **AND** no error is shown.

#### Scenario: The resume hop leaves no trace in history

- **WHEN** the reader resumes through the navigation entry and then goes back
- **THEN** they return to the page they came from, not to the navigation entry.
