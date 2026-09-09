# rtl-app-shell Specification

## Purpose

Define the direction of the application shell: direction declared once at the document
root, navigation on the inline-start edge, layout expressed in logical properties rather
than physical sides, the LTR islands that content ordered left-to-right still needs, the
direction-isolation of content whose script the interface cannot know, and an interface
typeface distinct from the one reserved for Qurʾānic text.
## Requirements
### Requirement: Direction is declared once, at the document root

The application SHALL declare `dir="rtl"` on the `<html>` element. Element-level
`dir="rtl"` attributes that only restate the inherited document direction SHALL be
removed.

An element MAY carry an explicit `dir` attribute only when it overrides the inherited
direction — that is, `dir="ltr"` for an LTR island (see the LTR-islands requirement) —
when it re-establishes `dir="rtl"` inside such an island, or when it declares `dir="auto"`
for content of unknown direction (see the direction-isolation requirement).

One further exemption: the application's canonical Arabic-text renderer MAY keep an
explicit `dir="rtl"`, because the direction it declares is part of that component's
contract rather than a restatement scattered through the tree.

The redundant attributes SHALL be removed **after** the physical-utility sweep, not before
it: they are the only record of which sites resolved left-to-right before the flip, and that
record is what shows where the conversion changed an author's *intent* rather than only its
spelling (see the logical-properties requirement).

#### Scenario: Document direction

- **WHEN** the application is loaded
- **THEN** the `<html>` element carries `dir="rtl"`
- **AND** text flows right-to-left without any component having to set direction itself.

#### Scenario: Redundant direction attributes are gone

- **WHEN** a component renders Arabic content that inherits the document direction
- **THEN** it does not carry its own `dir="rtl"` attribute.

#### Scenario: The shell declares direction exactly once

- **WHEN** the root layout is rendered on its own
- **THEN** exactly one element in it carries a `dir` attribute, and that element is the
  document element — the shell contains no island, so any second carrier is a restatement.

### Requirement: Navigation sits on the right

The persistent navigation SHALL be anchored to the **right** edge of the viewport on
`md` and wider screens, and the main content SHALL be offset on its right accordingly.
On narrow screens the navigation SHALL be a drawer that slides in **from the right**,
opened from a top bar whose menu control sits at the right.

#### Scenario: Sidebar on wide screens

- **WHEN** the viewport is `md` or wider
- **THEN** the navigation sidebar is pinned to the right edge
- **AND** the main content area is offset so that it does not sit under the sidebar.

#### Scenario: Drawer on narrow screens

- **WHEN** the viewport is narrower than `md` and the user opens the menu
- **THEN** the drawer slides in from the right edge
- **AND** it closes on backdrop click, on close-button click, and on selecting an item.

#### Scenario: Navigation item set and order

- **WHEN** the navigation renders its items
- **THEN** it shows exactly six entries, top to bottom: «محاورة القرآن»، «سور القرآن»،
  «دراسة الآية»، «تحليل اللسان»، «التحليل النحوي»، «الفواصل»
- **AND** no entry points to `/qlisan`
- **AND** each item's icon and Arabic label read right-to-left within the row.

#### Scenario: Each entry is told apart by its icon

- **WHEN** the navigation renders its items
- **THEN** no two entries carry the same icon
- **AND** no entry carries the icon used for the brand.

#### Scenario: Brand in the navigation header

- **WHEN** the navigation header renders the application name
- **THEN** it reads «القرآن بالقرآن».

### Requirement: Action buttons render on the leading-left of their input

In every input row — the chat composer, the word search, the phrase search, and the
sūra/āya verse pickers — the submit or action button SHALL be rendered on the **left**
of the input control it acts on, which is the trailing edge in an RTL layout.

DOM order SHALL be logical: the input control comes first in source order, its action
button last. Rows whose DOM order was hand-reversed to fake RTL under an LTR document
SHALL be restored to logical order, so that document-level RTL — not a manual
inversion — is what produces the placement.

#### Scenario: Chat composer

- **WHEN** the chat page renders its composer
- **THEN** the textarea occupies the right of the row and the send button sits at its left.

#### Scenario: Verse picker

- **WHEN** a page renders the sūra select + āya number + load button row **on one line**
- **THEN** the row reads right-to-left as sūra name, then āya number, then the load button
  at the left end
- **AND** the DOM order of that row is select, then number input, then button — which holds
  at every width, whereas the placement rule binds only while the row is unwrapped.

#### Scenario: No hand-reversed row remains anywhere

- **WHEN** any horizontal row is inspected — an input row, a summary bar, a card header,
  a status line
- **THEN** its source order equals its right-to-left reading order, and its visual placement
  is produced by the document direction rather than by a reversed DOM or by a `justify-end`
  that means "left"
- **AND** no comment in the source has to explain which trick produced the placement.

### Requirement: Layout uses logical properties, not physical sides

Layout SHALL express insets, margins, padding, borders, corner radii and text alignment
with direction-aware logical utilities (`ms-`/`me-`, `ps-`/`pe-`, `start-`/`end-`,
`border-s`/`border-e`, `rounded-s`/`rounded-e`, `text-start`/`text-end`) rather than
physical ones (`ml-`/`mr-`, `pl-`/`pr-`, `left-`/`right-`, `border-l`/`border-r`,
`rounded-l`/`rounded-r`, `text-left`/`text-right`).

Converting a physical utility to a logical one is **not** a name-for-name substitution, and
which substitution is correct SHALL be settled by measuring the rendered result rather than
by reasoning about the author's intent.

Once direction is declared at the root, every element outside an LTR island resolves
right-to-left. The rendering-preserving conversion is therefore the **mirror** one, and it is
uniform: `mr-`→`ms-`, `ml-`→`me-`, `text-right`→`text-start`, `text-left`→`text-end`,
`right-`→`start-`, `left-`→`end-`. The obvious name-for-name table (`mr-`→`me-`) does not
invert *some* sites — it inverts **every** site outside an island.

The direction an element resolved to before the flip does not choose the table; it says
whether the conversion preserved the author's intent as well as the pixels. On an element
that already resolved RTL it preserves both. On one that resolved LTR the author wrote the
utility meaning inline-end and the mirror hands them inline-start, so those sites SHALL be
decided individually and each decision recorded.

**One class is exempt, and exempt in the opposite direction.** An auto inline margin on a
flex item is not a position: it is the side of the main axis that absorbs the free space.
Mirroring it moves the margin to the side where the free space already sits, which does not
weaken the push but removes it — the element renders identically to one carrying no margin at
all. For auto margins the conversion SHALL preserve the main-axis **side**, which is the
name-for-name table on an LTR-authored site (`ml-`→`ms-`) and the mirror on an RTL-authored
one (`mr-`→`ms-`).

A residue grep confirms **coverage**, never correctness — it passes identically on a correct
and an inverted conversion.

Utilities that are *already* logical — `justify-end`, `items-end`, `self-end`, and auto
inline margins — are invisible to that grep and yet invert when the root direction flips.
Each SHALL be re-derived from its intent rather than assumed correct because the diff did not
touch it; for auto margins, by the main-axis rule above.

Physical utilities MAY remain only inside a declared LTR island, where the physical side
is the intended one regardless of document direction. An LTR island SHALL be **bounded so
that it contains every physical utility attributed to it**: a physical utility on an outer
wrapper, a sibling, or a portalled tooltip is a violation even when a nearby inner element
declares `dir="ltr"`. Flow-layout chrome around a chart — a legend, a bar row, a zoom
control, a table — is **not** part of the chart's island; only the coordinate-bearing SVG
and its own scroll container are exempt.

Properties that are physical and have **no** logical counterpart — CSS transforms, gradient
direction, `background-position`, horizontal shadow offsets, and inline `style` insets —
follow no direction at all. They SHALL be enumerated and decided by hand, and the enumeration
SHALL record its empty results too, so the check can be re-run identically.

#### Scenario: Text alignment set across a direction boundary

- **WHEN** an element sets a text alignment inherited by a descendant whose own direction
  differs from its own
- **THEN** the alignment is expressed so that the *descendant* resolves it to the side it
  renders on today — `text-align` being inherited but resolved against each element's own
  `direction`, the physical and logical keywords are not interchangeable here
- **AND** verse bodies stay flush to the right edge of their container.

#### Scenario: An auto margin that pushes a flex item to the far edge

- **WHEN** a flex item carries an auto inline margin so that it sits at the far end of its row
- **THEN** the converted utility places that margin on the item's main-**start** side, so the
  free space is absorbed before the item rather than after it
- **AND** the mirror conversion is a defect here although it is correct everywhere else: an
  auto margin on the main-end side renders identically to no margin at all, so the push is
  not weakened but silently removed.

#### Scenario: A component spaces its icon logically

- **WHEN** a component needs space between an icon and the label that follows it
- **THEN** it uses a logical utility, so the space falls on the correct side under RTL.

#### Scenario: Physical utilities are confined to LTR islands

- **WHEN** a physical directional utility appears in the source
- **THEN** it is inside an element that declares `dir="ltr"`.

### Requirement: LTR islands are explicit and preserved

Content whose meaning depends on left-to-right ordering SHALL be wrapped in an element
declaring `dir="ltr"`. This SHALL cover, at minimum:

- Every Fassila chart's SVG, its axis labels and its own scroll container. The archived
  `fassila-surah-comparison` requirements mandate an X axis ascending left-to-right and a
  scroller that opens at the lowest X value; document-level RTL SHALL NOT reverse either.
  Where such an island is absent today it SHALL be **added**, not merely preserved.
  Chart **tooltips are excluded**: their text is Arabic prose and they render outside the
  scroll container, so they remain right-to-left. A scrollable **table** is likewise not a
  chart: it keeps the document direction, so that its first column is what the reader sees
  on open.
- Verse references written as `surah:ayah` (e.g. `2:255`).
- Latin technical tags emitted by the analysis pipeline (QAC segment tags, provenance
  identifiers).

#### Scenario: Chart axes still ascend to the right

- **WHEN** a Fassila line chart is rendered under the RTL document
- **THEN** its leftmost vertex is still the lowest X value and its rightmost vertex the
  highest, matching the archived comparison requirements.

#### Scenario: A chart opens at its axis origin, not at its far end

- **WHEN** a chart is wider than the viewport and its scroll container is inspected
- **THEN** that container declares `dir="ltr"`, so it opens at the lowest X value
- **AND** this holds for the sequence chart as well as the diversity chart, both of which
  are reachable from a page whose own direction would otherwise open them at the last āya.

#### Scenario: A symbol that binds to a number

- **WHEN** a label pairs a neutral symbol with a number — a zoom factor «×2», a percentage
- **THEN** that pair is isolated left-to-right, because a neutral takes the paragraph
  direction and would otherwise render on the wrong side of its digits
- **AND** the isolate wraps the pair alone, not the row that contains it: an island large
  enough to also place the row is doing two jobs, and removing it for one breaks the other.

#### Scenario: Verse references read correctly

- **WHEN** a component renders the reference of sūra 2, āya 255
- **THEN** it reads `2:255`, not `255:2`.

#### Scenario: A reference adjacent to Arabic, or in brackets

- **WHEN** a reference is rendered next to an Arabic sūra name or inside parentheses or
  brackets
- **THEN** the numeric part and its surrounding brackets are inside the `dir="ltr"` island,
  because `(` `)` `[` `]` are bidi-mirrored and reverse when their resolved level is RTL
- **AND** the ordering does not depend on whether the adjacent name arrived in Arabic or in
  Latin transliteration.

### Requirement: Directional icons follow the reading direction

An icon is an SVG: it does not mirror with `dir`. Every icon whose **glyph encodes a
direction** SHALL be chosen for the RTL reading direction, decided per site rather than by a
blanket swap:

- **Semantically directional** — the glyph means forward, back, next, previous, submit, or
  "go there". Forward, next, send and go point **left**; back and previous point **right**.
- **Decorative or vertical** — a down-chevron, a spinner, an up-arrow, a 180° rotation of a
  vertically symmetric glyph. Unchanged.

Where the icon set offers no mirrored counterpart, the glyph SHALL be flipped with an
explicit horizontal transform rather than replaced by a different glyph. Icons already
authored for an RTL subtree SHALL NOT be re-flipped. A literal arrow character whose
codepoint is `Bidi_Mirrored` SHALL NOT be used to express direction, since its rendered
orientation inside an RTL run is engine-dependent.

#### Scenario: Verse and sūra pagination

- **WHEN** a previous/next pagination row is rendered
- **THEN** the *previous* link sits at the right of the row and its arrow points right
- **AND** the *next* link sits at the left of the row and its arrow points left.

#### Scenario: Send control

- **WHEN** the chat composer renders its submit control
- **THEN** the glyph points along the direction the composed Arabic text reads.

#### Scenario: An RTL-correct icon is not re-flipped

- **WHEN** a control that already carried an RTL-correct glyph is rendered — a sūra stepper
  labelled «السابقة»/«التالية», or a collapsed disclosure
- **THEN** it points the way it did before this change.

### Requirement: Content of unknown direction is direction-isolated

Text whose script the interface cannot know in advance — a translation field, a model
answer, the user's typed query, and any such text echoed back inside an Arabic sentence —
SHALL be rendered inside an element declaring `dir="auto"`, so the bidi algorithm derives the
run's direction from its first strong character instead of inheriting the document's.

An element wrapping known-Latin content SHALL also declare `lang` for that language, so a
screen reader does not read it with an Arabic voice.

A Latin or numeric token interpolated into an Arabic sentence built as a plain string SHALL
be isolated with Unicode isolate characters (FSI…PDI), since a string cannot carry an
element. A raw interpolation into an Arabic template is a defect.

#### Scenario: A non-Arabic answer in an RTL application

- **WHEN** the user asks a question in French and the model answers in French
- **THEN** the answer paragraph is laid out left-to-right with its punctuation at the end of
  each line
- **AND** the Arabic chrome around it stays right-to-left.

#### Scenario: A Latin token inside an Arabic sentence

- **WHEN** an Arabic status or error sentence embeds a Latin identifier, a bracketed brand
  name, or the user's own query
- **THEN** that token is isolated, so it does not reorder the Arabic sentence around it
- **AND** its parentheses render in their authored orientation.

### Requirement: Typefaces are served by the application itself

Both typefaces SHALL be served by the application itself — vendored into the repository and
declared in its own stylesheet — and SHALL NOT be fetched from a third party at build time or
at runtime. A build-time fetch turns an offline build into a failure rather than a
degradation, and a runtime one makes an application that needs no network depend on one.

#### Scenario: The application is built with no outbound network

- **WHEN** the frontend is built on a machine that cannot reach a font CDN
- **THEN** the build completes and both typeface families are emitted as static assets
- **AND** no rendered page requests a font from a third-party host.

### Requirement: Amiri is the typeface of the whole interface

Every Arabic string the application renders SHALL be set in Amiri — headings, sidebar
entries, tab strips, buttons, labels, captions, status lines, chart annotations and tooltips,
as well as verse bodies, vocalized words and analysed tokens. Amiri SHALL be the document's
default face, so that a surface obtains it by rendering Arabic and not by carrying a class.

The distinction between revealed text and the software commenting on it SHALL be carried by
size, weight and leading rather than by a second typeface: Qurʾānic renderings keep their
larger type and their `.arabic-text` leading, and no chrome surface reproduces both.

#### Scenario: Chrome is set in Amiri

- **WHEN** the navigation, a tab strip, a button, or a page heading renders its Arabic label
- **THEN** it is set in Amiri.

#### Scenario: Verses keep Amiri

- **WHEN** a verse or a vocalized Qurʾānic word is rendered
- **THEN** it is set in Amiri, as before this change.

#### Scenario: A new Arabic surface needs no font class

- **WHEN** a component renders an Arabic string and applies no font-family class at all
- **THEN** that string is set in Amiri.

### Requirement: Digits and Latin text render in the secondary face

The secondary face — the vendored Arabic screen sans — SHALL remain loaded and SHALL be the
face that draws every character outside the Arabic Unicode ranges: Western digits, percent
and decimal signs, verse references such as `2:255`, Latin technical tags, and the
French/English translation paragraphs. Selection SHALL be **by script, not by element**: the
faces SHALL be declared over Unicode ranges that give Amiri every Arabic character, so that a
run falls to the correct face on its own, inside an Arabic sentence as well as outside one.
Where both faces claim a character, the stack order SHALL resolve it in Amiri's favour.

The **word space inside an Arabic sentence SHALL be drawn by Amiri**, not by the secondary
face. It is a character of the Arabic run — it sets the word spacing of the Qurʾānic text —
and the subset boundaries these faces are published with put it on the wrong side.

Numbers SHALL render exactly as they did before this change. The numeral policy of
`arabic-ui-locale` is unaffected: analytical numbers stay Western with `locl` disabled,
and reading numerals produced by `toArabicDigits()` are Arabic-Indic characters
(U+0660–U+0669), which lie inside the Arabic ranges and therefore stay in Amiri.

#### Scenario: An analytical number keeps its present rendering

- **WHEN** a Fassila tile, a table cell, or a chart axis renders a count or a percentage
- **THEN** it is set in the secondary face, with the same glyphs and metrics as before this
  change
- **AND** it is not set in Amiri.

#### Scenario: A digit inside an Amiri sentence

- **WHEN** an Arabic label set in Amiri embeds a Western digit or a verse reference
- **THEN** the Arabic characters are set in Amiri and the digits in the secondary face
- **AND** neither run needs a font-family class of its own to obtain its face.

#### Scenario: A reading numeral stays Arabic-Indic and stays in Amiri

- **WHEN** an āya number is rendered through `toArabicDigits()` inside a verse rendering
- **THEN** it appears in Arabic-Indic digits, set in Amiri.

#### Scenario: Word spacing inside an Arabic sentence

- **WHEN** a verse body or any other Arabic sentence is rendered
- **THEN** the spaces between its words are drawn by Amiri, at Amiri's own advance width
- **AND** the word spacing of Qurʾānic text is unchanged by this change.

#### Scenario: A translation paragraph

- **WHEN** a French or English translation is rendered under a verse
- **THEN** it is set in the secondary face, unchanged by this change.

