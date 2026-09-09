## REMOVED Requirements

### Requirement: Interface typography is distinct from Qurʾānic typography

**Reason**: The role assignment is inverted. Seen running, the two-face split reads as two
applications sharing a window rather than as a boundary between the revealed text and the
software around it; the owner has decided the product speaks in one Arabic voice, and that
voice is Amiri. The typographic boundary D6 defended is not abandoned — it moves from *face*
to size, weight and leading, which `.arabic-text` already carries.

**Migration**: Replaced, without loss, by the three requirements added below. The
self-hosting clause and its offline-build scenario are carried over verbatim under
*Typefaces are served by the application itself*; the role assignment is restated, inverted,
under *Amiri is the typeface of the whole interface*; and what the second face is now for is
made normative under *Digits and Latin text render in the secondary face*.

## ADDED Requirements

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
