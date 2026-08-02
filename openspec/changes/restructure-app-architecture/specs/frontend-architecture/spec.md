## ADDED Requirements

### Requirement: Single Arabic-text rendering source of truth

Arabic text SHALL be rendered through one shared mechanism. The current three parallel
approaches — the `ArabicText` component, the `.arabic-text` global CSS class, and the
`font-arabic` Tailwind utility applied with ad-hoc `dir`/`lang` attributes — SHALL be
collapsed so that every Arabic-text render goes through the single canonical component,
which owns direction (`rtl`), `lang="ar"`, font, and line-height. Rendered output SHALL be
visually equivalent to today.

#### Scenario: all Arabic text uses the shared renderer

- **WHEN** the frontend is searched for Arabic-text rendering
- **THEN** Arabic strings are rendered via the single canonical Arabic-text component
- **AND** no page applies the raw `.arabic-text` class or bespoke `dir="rtl" lang="ar"`
  markup in place of that component.

### Requirement: Single verse-rendering component

Verse display SHALL reuse the canonical `VerseCard` (or a shared verse-render primitive it
is built from) everywhere a verse is shown. The bespoke inline verse blocks in
`app/verse-study/page.tsx` (Similar Verses results, `SurahCard`/`HighlightedVerse`) and in
`app/surah/[number]/page.tsx` SHALL be replaced by the shared component, including the
ayah-marker `﴿n﴾` treatment. Displayed verses SHALL remain visually and behaviorally
equivalent (highlighting, vocalization, clickable references).

#### Scenario: no bespoke verse markup

- **WHEN** the frontend is searched for verse rendering
- **THEN** verses render through the shared verse component
- **AND** Verse Study and the surah page no longer re-implement the Arabic-verse-with-ayah-marker
  block inline.

### Requirement: Centralized typed API client

Every call to the backend SHALL go through `lib/api.ts`. No page or component may issue a
raw `fetch` to a backend endpoint. Backend response types SHALL have a single owner so the
same shape is not hand-redeclared in multiple files.

#### Scenario: lisan endpoint routed through the client

- **WHEN** the "Lisan Analysis" page calls the letter-symbolism endpoint
- **THEN** it calls a function in `lib/api.ts`
- **AND** no component contains an inline `fetch` to a backend route.

#### Scenario: no duplicated response types

- **WHEN** the frontend type definitions are inspected
- **THEN** each backend response shape is declared once (shared/generated), not
  independently re-declared across `types.ts`, `lisanTypes.ts`, and `madarTypes.ts` for
  the same object.

### Requirement: Remove dead frontend code

Frontend code with zero call sites SHALL be removed. Specifically `components/LexicalResult.tsx`,
the unused `lexical()` function and `LexicalResponse` type in `lib/api.ts`, and any other
symbol proven to have no importers SHALL be deleted.

#### Scenario: dead modules deleted

- **WHEN** the change is applied
- **THEN** `components/LexicalResult.tsx` no longer exists
- **AND** `lib/api.ts` no longer exports an unused `lexical()`/`LexicalResponse`.

### Requirement: Shared data-fetching and utilities

Repeated data-fetching scaffolding (loading/error/data state with try/catch) SHALL be
provided by one shared hook rather than copy-pasted across pages. Shared helpers SHALL have
a single definition; `toArabicDigits` SHALL be imported from `lib/` rather than redefined
inline. A `test` script SHALL be present in `frontend/package.json`.

#### Scenario: one fetch hook

- **WHEN** a page loads data from the API
- **THEN** it uses the shared fetch hook for loading/error/data handling
- **AND** the per-tab/per-page copies of that scaffolding are removed.

#### Scenario: single toArabicDigits and a test script

- **WHEN** the frontend is inspected
- **THEN** `toArabicDigits` is defined once in `lib/` and imported where needed (no inline
  copy in `app/surah/[number]/page.tsx`)
- **AND** `frontend/package.json` defines a `test` script that runs Vitest.
