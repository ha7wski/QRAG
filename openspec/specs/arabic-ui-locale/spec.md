# arabic-ui-locale Specification

## Purpose

Define the interface language of the application: every string a reader sees is Arabic
and comes from one typed dictionary, with a named set of exemptions (identifiers, verse
references, technical detail lines, values in their own script). Covers page names,
navigation, tabs, buttons, placeholders and accessible names, status and failure messages,
document metadata, counted-noun agreement, and the numeral policy.

## Requirements

### Requirement: Every user-facing string is Arabic

The web interface SHALL render every string addressed to the user in Arabic. This
covers page headings, the explanatory caption under each heading, navigation labels,
tab labels, button labels, input placeholders, `aria-label` and other accessible
names, select options, empty states, loading states, status banners, and error
messages.

No Latin-script word SHALL appear in interface chrome. Five classes of Latin text
are exempt, because they are data, identifiers, or diagnostics rather than interface
language:

1. Verse references written in numeric form (`2:255`) and other numeric identifiers.
2. Latin technical tags that the analysis pipeline itself emits and that carry no
   Arabic equivalent in the corpus (e.g. QAC segment tags `STEM` / `PREFIX` / `SUFFIX`,
   already rendered inside `dir="ltr"` spans).
3. Text originating from user input, or **data values** supplied by the backend — a root,
   a lemma, a letter, a tag, a count. Backend **prose** addressed to the reader is NOT
   exempt; see the requirement below.
4. Exception text rendered as a subordinate technical detail per the "Exception text never
   becomes the interface message" requirement — including the English messages thrown by
   `frontend/src/lib/api.ts`, which stay English deliberately.
5. Code comments, TypeScript identifiers, prop and type names, `data-*` values, CSS class
   names and repository documentation, which are not addressed to the user and stay English
   per the project convention.

A Latin string rendered as **decoration** beside its Arabic counterpart — an uppercase
English gloss under an Arabic heading — is exempt under no class and SHALL be removed
rather than translated: the Arabic label is the label. Being wrapped in `dir="ltr"` does
not make a string exempt.

#### Scenario: A page presents itself in Arabic

- **WHEN** a user opens any route of the application
- **THEN** the page heading, its caption, every tab label and every button label on
  that page are in Arabic
- **AND** no English sentence or English button label is rendered.

#### Scenario: Placeholders and accessible names are Arabic

- **WHEN** a page renders a text input, a number input, a `select`, or an icon-only button
- **THEN** it has an accessible name
- **AND** that name is Arabic
- **AND** a `placeholder` is never the only accessible name, because a placeholder is an
  example value rather than a label.

#### Scenario: An English string already written to a reader's storage

- **WHEN** a previous version persisted an interface string into the reader's browser
  storage — a default conversation title, say — so that it reaches the screen from disk
  rather than from the code
- **THEN** it is mapped to its Arabic form **on read**, and no English default reappears
- **AND** the stored data is not discarded to achieve this: bumping a store version would
  make the reader's saved conversations the price of a translation.

#### Scenario: Failure and empty states are Arabic

- **WHEN** a request fails, returns nothing, or the backend reports a degraded or
  unreachable state
- **THEN** the message shown to the user is Arabic.

#### Scenario: Latin identifiers are permitted as data

- **WHEN** a component renders a verse reference such as `2:255`, or a QAC segment
  tag such as `STEM`
- **THEN** that text MAY remain Latin/numeric and is not treated as a violation.

### Requirement: Exception text never becomes the interface message

When a request fails, the sentence presented to the user SHALL be an Arabic string from
the dictionary, chosen by the calling site. Raw exception text (including
browser-generated messages such as `Failed to fetch`) SHALL NOT be used as that
sentence.

The Arabic sentence SHALL be selected by the **kind** of failure, not merely by the call
site: where the API distinguishes a non-Arabic input, an empty input, a missing verse, a
service outage and a network rejection, the interface SHALL keep those distinctions. An
actionable diagnostic MUST NOT become less actionable by being translated.

An exception's text MAY additionally be shown as a secondary technical detail, rendered
inside an element declaring `dir="ltr"` **and `lang="en"`** — the `dir` so it lays out
left-to-right, the `lang` so a screen reader does not read English with an Arabic voice —
and visually subordinate to the Arabic message.

#### Scenario: Network failure

- **WHEN** a fetch rejects because the backend is unreachable
- **THEN** the user reads an Arabic sentence describing the failure
- **AND** the browser's own English exception text is not that sentence.

#### Scenario: Technical detail is subordinate

- **WHEN** a failure carries exception text worth surfacing
- **THEN** that text is rendered as a secondary line inside `dir="ltr"`, below the
  Arabic message.

### Requirement: Interface strings live in one dictionary

All Arabic interface strings SHALL be defined in a single typed module,
`frontend/src/lib/strings.ts`, exported as one `as const` object keyed by page and
component. Components SHALL read their text from that module rather than embedding
Arabic literals in JSX.

Two categories are exempt: (a) strings that are interpolated from backend data, and
(b) Arabic terminology that a component derives from a typed domain map it already
owns (for example QLisan's feature-key → Arabic-label map), which SHALL stay with its
domain type.

The dictionary SHALL be typed so that a missing key is a TypeScript error rather than
a blank render. This holds for static access on the `as const` object and, under `strict`,
for dynamic access too. It does **not** hold for a map typed `Record<string, string>`: a
domain map claiming exemption (b) SHALL therefore be keyed by a closed union and SHALL NOT
substitute a Latin machine identifier when a key is absent.

Typing cannot detect a component that still renders an English literal while its Arabic key
sits unused, because `placeholder`, `title` and `aria-label` accept any string. That case is
covered by the Latin-text audit, not by the compiler.

Nor does typing guard a failure-message migration on its own: a `catch` clause annotated
`any` makes the exception's `message` an `any`, which is assignable to anything, so a site
left un-migrated typechecks silently. Catch clauses handling a failure SHALL therefore be
left to their inferred `unknown` type, so that the shape is checked where it is built.

#### Scenario: A component reads its label from the dictionary

- **WHEN** the chat composer renders its send button and placeholder
- **THEN** both texts come from `strings.ts`, not from literals inside the component.

#### Scenario: A missing key does not reach the screen

- **WHEN** a component references a dictionary key that does not exist
- **THEN** the TypeScript build fails.

### Requirement: Pages are named in Arabic

Each route SHALL carry an Arabic display name, used identically in the navigation, in
the page heading, and in any cross-page link that names it.

URL paths SHALL NOT change **as part of Arabization**: renaming a page in Arabic SHALL NOT
be the occasion for renaming its route. The table below records the routes as they stand at
this change; a route slug MAY still be realigned by a separate change whose purpose is that
realignment.

| Route | Arabic display name | In navigation |
|---|---|---|
| — (application) | «القرآن بالقرآن» | brand |
| `/chat` | «محاورة القرآن» | yes |
| `/surah` | «سور القرآن» | yes |
| `/verse-study` | «دراسة الآية» | yes |
| `/lexical` | «تحليل اللسان» | yes |
| `/tahlil` | «التحليل النحوي» | yes |
| `/fassila` | «الفواصل» | yes |
| `/qlisan` | «بطاقة الكلمة» | **no** |

`/surah/{number}` is the same page as `/surah`, addressed at a particular sūra; it carries
the same Arabic name and is not a separate entry.

The string "Quran RAG" SHALL NOT appear anywhere in the interface; «القرآن بالقرآن» is
the application's only name.

`/qlisan` SHALL keep its Arabic page name and SHALL be Arabized like every other route,
even though it is absent from the navigation, so that a direct URL does not reach a
half-migrated page.

#### Scenario: One name per page, everywhere

- **WHEN** a route is named in the navigation and in its own page heading
- **THEN** both show the same Arabic name
- **AND** the browser URL for that route is unchanged from before this change.

#### Scenario: A route addressed at a resource keeps its page name

- **WHEN** `/surah/2` is opened
- **THEN** the page is named «سور القرآن» wherever the interface names the page
- **AND** the sūra's own name is shown as the content's heading, not as the page's name.

#### Scenario: The old application name is gone

- **WHEN** any page of the application is rendered
- **THEN** the string "Quran RAG" appears nowhere on screen.

#### Scenario: A route absent from the navigation is still Arabic

- **WHEN** `/qlisan` is opened by direct URL
- **THEN** its heading, caption, buttons and messages are Arabic, exactly as for a
  navigable route.

### Requirement: Document metadata is Arabic

The document SHALL declare `lang="ar"`, and its `<title>` and description metadata
SHALL be Arabic.

#### Scenario: Browser tab and language

- **WHEN** the application is loaded
- **THEN** the document element declares `lang="ar"`
- **AND** the browser tab title is Arabic.

### Requirement: Backend prose is interface language, not data

Text the backend supplies that is addressed to the reader **as a sentence** — an explanation
of why an analysis is unavailable, a source attribution, an HTTP `detail` — SHALL be Arabic.
The backend-content exemption covers data values, not prose. Where a payload offers the same
value in both scripts, the interface SHALL render the Arabic field and use the Latin one only
as a fallback.

#### Scenario: An unresolvable word

- **WHEN** «تحليل اللسان» is given a word whose root cannot be resolved
- **THEN** the panel explaining why is Arabic
- **AND** no English sentence is rendered, even though the sentence came from the backend
- **AND** the response is a success, not a failure, so the failure-message rules do not apply.

#### Scenario: A backend field exists in both scripts

- **WHEN** a payload offers a sūra name as both `surah_name_ar` and `surah_name_en`
- **THEN** the interface renders the Arabic field
- **AND** the Latin field appears only when the Arabic one is absent.

### Requirement: Counted nouns take number-aware Arabic forms

A string stating a quantity SHALL select its noun form from the count: singular for one,
dual for two, plural for three to ten, and singular accusative for eleven and above. A single
form used for every count is a defect, not a simplification. This applies to text that is
never rendered visually — an `aria-label`, a `title` — as well as to visible copy.

#### Scenario: A result count

- **WHEN** a search returns five verses
- **THEN** the count reads «أقرب ٥ آيات», not «أقرب ٥ آية».

#### Scenario: A count inside an accessible name

- **WHEN** a chart segment's `aria-label` states a count
- **THEN** the same number-aware rule applies, even though no visual review pass can see it.

#### Scenario: A string that was Arabic before this change

- **WHEN** a component was written in Arabic from the start and interpolates a count into a
  fixed noun
- **THEN** it is in scope, because the requirement is grammatical and not linguistic: a
  language sweep sees Arabic and moves on, which is exactly how «2 آية» reached production.

#### Scenario: A counted noun carrying an adjective

- **WHEN** the counted noun is qualified — «فاصلة مميّزة»
- **THEN** the adjective agrees with the number too, and the four forms are stored as whole
  phrases rather than composed from a noun plus a separately-agreeing adjective.

### Requirement: Numeral rendering policy is preserved

Arabization SHALL NOT change how numbers are rendered. Sūra and āya numbers presented
as part of Qurʾānic reading SHALL keep Arabic-Indic digits (`٣١٣`) via the existing
`toArabicDigits` helper; statistics, percentages, table cells and chart axis labels
SHALL keep Western digits via the existing `.western-digits` class.

#### Scenario: Reading numbers stay Arabic-Indic

- **WHEN** an āya number is rendered inside a verse rendering
- **THEN** it appears in Arabic-Indic digits.

#### Scenario: Analytical numbers stay Western

- **WHEN** a Fassila tile, table cell, or chart axis renders a count or a percentage
- **THEN** it appears in Western digits with `.western-digits` applied.

#### Scenario: The document language does not silently reshape digits

- **WHEN** the document declares `lang="ar"` and a number is rendered in a face carrying an
  Arabic `locl` digit substitution
- **THEN** its digit form is the result of an explicit choice — `toArabicDigits()` for a
  reading number, the Western-digit class for an analytical one
- **AND** never the incidental result of the font feature reacting to the document language.
