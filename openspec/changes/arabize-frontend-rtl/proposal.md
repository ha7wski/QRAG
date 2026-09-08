## Why

The product is now scoped to studying the Qurʾān through itself, in Arabic — yet its
interface still addresses the user in English while the content it serves is Arabic.
The result is a split-personality UI: Arabic verses, Arabic analysis labels (QLisan's
fiche, Fassila's tabs, the نحوي rows) wrapped in English chrome ("Talk to Quran",
"Load verse", "Type your question…"), laid out left-to-right with the navigation
pinned to the left. An Arabic-reading user reads the page in two opposite directions
at once.

The half-migration also costs correctness. RTL is currently faked three different ways
— 58 element-level `dir` attributes (48 of them `dir="rtl"`), hand-reversed DOM order
(four rows, not two: `qlisan`/`tahlil` put the button *before* the input so `justify-end`
makes it *look* right-to-left, and two more rows do the same in `verse-study` and in
`qlisan`'s verse header), and 36 physical LTR utilities — **two thirds of which sit inside
one of those `dir="rtl"` subtrees, where the physical side already means the logical one**,
so they convert by the mirror of the obvious mapping. Every new component has
to re-derive which trick applies. Settling the direction once, at the document root,
removes that decision from every future change.

## What Changes

**Arabic display**
- Every user-facing string becomes Arabic: page titles, navigation labels, tab labels,
  buttons, input placeholders, ARIA labels, empty/loading/error messages, and the
  explanatory captions under each page heading.
- Strings move out of the JSX into **one typed dictionary** (`frontend/src/lib/strings.ts`),
  the single place the Arabic wording is reviewed and corrected.
- The application is renamed «القرآن بالقرآن»; "Quran RAG" disappears from the interface.
- Page identities are named in Arabic: `/chat` → «محاورة القرآن», `/verse-study` →
  «دراسة الآية», `/fassila` → «الفواصل», `/lexical` → «تحليل اللسان», `/tahlil` →
  «التحليل النحوي», `/qlisan` → «بطاقة الكلمة». URL paths are **unchanged by this change** —
  only the displayed names. The requirement is scoped to Arabization rather than absolute, so
  a later change may still realign a slug for its own reasons (design D9).
- The collision «التحليل النحوي» would have had with the collapsible section of «تحليل اللسان»
  is **resolved rather than recorded**: that section becomes «الصرف والإعراب», which is what it
  renders (`SarfiRows` — morphology plus a case-marker hint from the نحوي level).
- **`/qlisan` is removed from the navigation.** The route, its page and its backend
  endpoints stay; the navigation drops from six entries to five. Because the navigation
  is currently the only inbound link to that page, it becomes reachable by direct URL
  only — it is still Arabized, so a deep link does not land on a half-migrated page.
- Document metadata becomes Arabic (`<title>`, description) and the document declares
  `lang="ar"`.
- **Code comments, identifiers, and repo docs stay in English**, per the existing
  project convention.

- Failure messages stop leaning on raw exception text. Twelve sites currently render
  `e?.message || "English fallback"`, so a network error puts the browser's own English
  string on screen; the Arabic sentence becomes the message and the exception text, when
  kept, is demoted to a `dir="ltr" lang="en"` technical detail. The Arabic sentence is chosen
  by failure **kind**, so an actionable backend diagnostic does not become vaguer in Arabic
  than it was in English. Four further sites render a *backend* `message` field as the
  primary sentence and are a separate class; one of them is still English.

**RTL layout**
- Direction is declared **once**, as `dir="rtl"` on `<html>`. Element-level `dir="rtl"`
  attributes that merely restate it are removed; the remaining `dir="ltr"` islands
  (SVG charts, verse references like `2:255`, Latin technical tags) become explicit and
  intentional.
- The navbar moves from the left edge to the **right edge** — sidebar on md+, drawer
  sliding in from the right on mobile — and the main content offset follows it.
- Physical Tailwind utilities are replaced by logical ones, so the layout derives from the
  document direction instead of hard-coding a side. The mapping is **two tables, chosen per
  site by the direction the element resolves to today** (design D12) — `text-right` means
  `text-end` on an LTR-resolving element and `text-start` inside a `dir="rtl"` subtree — and
  the redundant `dir` attributes are deleted *after* the sweep, because they are its input.
- The properties that follow no direction at all are handled by hand and enumerated:
  transforms, gradient direction, inline `style` insets, and the nine directional icon
  glyphs, which are SVG paths and do not mirror.
- Content whose script the interface cannot know — translations, model answers, the user's
  own query — is isolated with `dir="auto"` rather than left to inherit RTL.
- **BREAKING (visual):** the hand-reversed rows in `/qlisan` and `/tahlil` are restored
  to logical DOM order (input first, action button last). Left untouched, document-level
  RTL would flip them and push the button to the *wrong* side.

**Action-button placement**
- In every input row — chat composer, word search, phrase search, verse picker — the
  submit/action button SHALL render on the **left** of its input, which is the trailing
  edge in RTL. This becomes a stated requirement rather than an accident of DOM order.

**Typography**
- A dedicated Arabic UI face — **IBM Plex Sans Arabic**, self-hosted from vendored files —
  is loaded for chrome: navigation, tabs, buttons, labels, captions. **Amiri stays reserved
  for Qurʾānic text**, keeping the revealed text typographically distinct from the app. The
  "or Noto Kufi Arabic" alternative is withdrawn: Noto splits Latin into a separate family,
  so every Western digit, every `2:255` and every `dir="ltr"` detail line would fall through
  to a system fallback — precisely the surfaces the numeral policy exists to stabilise.

**Numerals — unchanged, but not unthreatened.** Arabic-Indic digits (٣١٣) for sūra/āya
numbers, Western digits for statistics and chart axes via the existing `.western-digits`
class. Moving `lang` from `en` to `ar` on `<html>` arms the OpenType `locl` substitution
document-wide — the very mechanism `.western-digits` exists to disable — so the policy is
preserved by inverting that opt-out into an opt-in and by making every reading number
explicit, rather than by leaving it alone (design D22).

## Capabilities

### New Capabilities
- `arabic-ui-locale`: every user-facing string is Arabic and sourced from one typed
  dictionary; covers page names, nav, tabs, buttons, placeholders, ARIA labels, status
  and error messages, document metadata, and the numeral policy.
- `rtl-app-shell`: document-level RTL, navigation on the right (sidebar + mobile drawer),
  logical-property layout, the mandated LTR islands, and the Arabic UI typeface.

### Modified Capabilities
- `verse-study`: the tab-set requirement currently names the three tabs by their English
  labels ("Word in Verses", "Similar Verses", "Find Verse context"). The delta restates
  them as Arabic labels in RTL reading order while keeping the same tab identities,
  ordering guarantee, and state-preservation behaviour. The `similar` label is
  «الآيات القريبة في المعنى» and explicitly **not** «النظائر», which names a different
  discipline that this application already labels «نظيرة» elsewhere (design D21).

## Impact

**Code — `frontend/` only, with one exception. No API, data, retrieval or behaviour change.**
- **One narrow backend edit:** `lisan/lisan_service.py` returns an English paragraph as the
  user-facing explanation when a root cannot be resolved — the most common non-happy path on
  «تحليل اللسان» — and its sibling `madar/madar_service.py` already holds the correct Arabic
  sentence verbatim. Two literals are replaced (that `message` and the `SOURCES`
  attributions). Prose only: no schema, endpoint, retrieval or contract change (design D16).
- New: `src/lib/strings.ts` (the Arabic dictionary), and two vendored OFL font families
  under `src/app/fonts/` declared with `next/font/local` — **not** `next/font/google`, which
  moves the font fetch to build time where an offline failure is fatal rather than silent
  (design D6).
- Rewritten: `src/app/layout.tsx` (dir/lang/metadata/content offset),
  `src/components/Navbar.tsx` (side flip, Arabic labels, `/qlisan` entry removed),
  `src/app/page.tsx` (landing copy, entirely rewritten in Arabic in a scholarly register
  — the current English prose is not translatable line-for-line).
- Touched for strings and/or direction: all 7 route pages plus `surah/[number]` and
  `verse/[surah]/[ayah]` (**nine** routes), and ~21 components — `ChatInterface`,
  `HealthBanner`, `VerseCard`, `VerseContextCard`, `LexicalResult`, `LisanResult`,
  `MadarAslCard`, `SarfiRows`, `TahlilClaim`, `LevelCard`, `FicheRow`, `ScrollToTop`,
  `StatusBadge`, `ArabicText`, and the **seven** `Fassila*` components (Analysis, Bars,
  Comparison, DistributionPie, DiversityLine, Line, Tile).
- Two `src/lib/` modules missing from the first inventory, both user-visible:
  `lib/conversations.ts` writes the English default conversation title `"New conversation"`
  — and **persists** it to `localStorage`, so pre-existing data keeps English titles unless
  mapped on read; and `lib/api.ts` throws 23 English `Error` messages that today *are* the
  on-screen sentence, and which become the subordinate technical detail rather than being
  translated.
- `LevelCard`'s `titleEn` prop is removed: an uppercase Latin gloss beside every Arabic level
  heading is decoration in the wrong script, and it ripples through four call sites, a
  pass-through wrapper, a label map and six test usages.
- `tailwind.config.ts` (UI font family), `src/app/globals.css` (body direction, font
  defaults).

**Tests.** The local-only Vitest suites assert on rendered English text
(`verse-study/page.test.tsx`, `lexical/page.test.tsx`, `LisanResult.test.tsx`,
`LevelCard.test.tsx`, `TahlilClaim.test.tsx`, and `lib/conversations.test.ts`, which was
missing from this list) and will need their expected strings updated to the dictionary
values. One of those assertions is actively deceptive: it mocks `new Error("Verse not
found")` and asserts that same string, so under the new error shape it stays green whether
or not the Arabic sentence was ever wired. Note also that every test file is excluded from
the published repo, so on a clone `npx vitest run` exits 0 by finding nothing — which is why
each new assertion must also exist as a scenario in `specs/` (design D20).

**Constraint — LTR islands must survive, and two of them must first be created.** Archived
specs require Fassila chart X axes to ascend left-to-right and their scrollers to open at the
lowest X value (`fassila-surah-comparison`). Only one of the three charts actually declares
`dir="ltr"` today: `FassilaLine`'s scroll wrapper has none, so on a narrow viewport it
already opens at the highest āya — a defect that pre-dates this change and that a
before/after screenshot comparison cannot see. Chart **tooltips**, by contrast, hold Arabic
prose and stay right-to-left, and a scrollable table keeps the document direction so its first
column is what the reader sees on open. Verse references (`2:255`) do need islands — three of
the five sites have none — and the brackets around them must sit inside, since `(` `)` `[` `]`
are bidi-mirrored.

**Coordination.** The pending `restructure-app-architecture` change also rewrites frontend
internals (one Arabic-text renderer, one verse renderer, a shared fetch hook, removal of
`LexicalResult`). The two changes edit the same files; design.md records the ordering
decision.

**Not in scope.** No backend/LLM answer-language change (answers already follow the
question's language), no route renaming, no new pages, no i18n library or language
switcher — the app becomes deliberately monolingual Arabic.
