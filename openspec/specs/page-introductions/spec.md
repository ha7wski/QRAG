# page-introductions Specification

## Purpose
TBD - created by archiving change add-page-intros. Update Purpose after archive.
## Requirements
### Requirement: Every feature page carries an introduction under its heading
The pages «سور القرآن» (`/surah` and `/surah/[number]`), «دراسة الآيات»
(`/verse-study`), «فهرس الجذور» (`/roots`), «تحليل لساني عربي» (`/lexical`), «فواصل الآيات والسور»
(`/fassila`) and «بطاقة الكلمة» (`/qlisan`) SHALL each render a page introduction placed directly
after the page heading and its caption, and before the page's first control. The landing page `/`,
the deep-link page `/verse/[surah]/[ayah]` and the chat page `/chat` SHALL NOT render one, and this
change SHALL leave `/chat` unchanged.

#### Scenario: Introduction follows the heading
- **WHEN** a reader opens `/roots`
- **THEN** the introduction appears immediately below «فهرس الجذور» and its caption, and above the
  letter strip

#### Scenario: Excluded pages
- **WHEN** a reader opens `/`, `/verse/2/255` or `/chat`
- **THEN** no page introduction is rendered

#### Scenario: Chat is left as it is
- **WHEN** a reader opens `/chat` after this change
- **THEN** the page renders exactly as before — no heading added, no introduction, no layout change

### Requirement: An introduction is a summary plus feature cards
An introduction SHALL consist of one summary sentence describing what the page is for, followed by
one card per feature of the page. Each card SHALL show an icon, the feature's name — the exact
string the page labels it with on screen when it has one, a short descriptive name otherwise — and
one sentence explaining how the feature works. A page SHALL have between 2
and 6 cards.

#### Scenario: Verse Study lists its tabs
- **WHEN** the introduction of «دراسة الآيات» is open
- **THEN** it shows a card for «الكلمة في الآيات», one for «الآيات المتقاربات» and one for «الآية في
  سياقها», each named exactly as its tab

#### Scenario: Feature name matches the screen
- **WHEN** a card names a feature that the page labels on screen
- **THEN** the name is the same string the page uses for that tab, mode, section or switch

### Requirement: Introduction size is bounded
The summary SHALL be a single sentence of at most 30 words. Each card's explanation SHALL be a single
sentence of at most 25 words. The open introduction SHALL fit within roughly one viewport third on a
desktop viewport (≥ 1024 px wide), laying its cards in at most 3 columns on desktop, 2 on tablet and
1 on phone, with no horizontal scroll at 360 px.

#### Scenario: Phone width
- **WHEN** the introduction is open at a viewport 360 px wide
- **THEN** cards stack in one column and nothing overflows horizontally

#### Scenario: Copy length
- **WHEN** the strings of any introduction are reviewed
- **THEN** no summary exceeds 30 words and no card sentence exceeds 25 words

### Requirement: An introduction is collapsible and remembers its state per page
Each introduction SHALL be open by default on a reader's first visit to that page and SHALL offer a
control to fold it. Once folded, the page SHALL remember the folded state for that page across
reloads, and the folded introduction SHALL occupy a single line holding a toggle that reopens it.
Storage failure SHALL degrade to the default (open) without error.

#### Scenario: First visit
- **WHEN** a reader with no stored state opens `/lexical`
- **THEN** the introduction is open

#### Scenario: Folded state persists
- **WHEN** the reader folds the introduction of `/lexical` and reloads the page
- **THEN** the introduction is folded and shows only its one-line toggle

#### Scenario: State is per page
- **WHEN** the reader has folded the introduction of `/lexical` and opens `/roots` for the first time
- **THEN** the introduction of `/roots` is open

#### Scenario: Storage unavailable
- **WHEN** browser storage throws on read or write
- **THEN** the introduction renders open and folding still works for the current view

### Requirement: Introduction copy is Arabic and lives in the strings dictionary
All introduction text — summaries, feature names, explanations, the toggle label and its accessible
name — SHALL be Arabic and SHALL be read from `lib/strings.ts`; no introduction text SHALL be a
literal inside a component. Feature names that already exist in the dictionary SHALL be referenced,
not re-typed.

#### Scenario: No literal copy
- **WHEN** `PageIntro` and the pages rendering it are inspected
- **THEN** every visible introduction string comes from `S`

#### Scenario: Shared feature name
- **WHEN** the «دراسة الآيات» card for the word tab is rendered
- **THEN** its title is `S.verseStudy.tabs.word`

### Requirement: The introduction is accessible and RTL-correct
The toggle SHALL be a `button` exposing `aria-expanded` and controlling the introduction region by
`aria-controls`. The introduction SHALL be a labelled region. Layout SHALL use logical properties
only, icons SHALL be decorative (`aria-hidden`), and the block SHALL use the interface typeface and the
existing brand palette.

#### Scenario: Screen reader
- **WHEN** a screen reader focuses the toggle
- **THEN** it announces the toggle's Arabic name and whether the introduction is expanded

#### Scenario: Keyboard
- **WHEN** a keyboard user presses Enter or Space on the toggle
- **THEN** the introduction folds or unfolds and focus stays on the toggle

