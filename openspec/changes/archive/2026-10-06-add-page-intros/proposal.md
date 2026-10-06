## Why

Every page of the app opens on a heading and a one-line caption, then straight onto its controls.
The caption says what to type, not what the page *does*: «دراسة الآيات» hides three tabs and three
similarity modes behind one sentence about a single word, «سور القرآن» never mentions its closeness
switch, and «فهرس الجذور» never says a card unfolds. A first-time
reader has to discover each feature by clicking. A short, well-proportioned introduction under each
heading — what the page is for, its features, and in one line how each works — makes the app
legible without making it heavier.

## What Changes

- A **page introduction block** under the heading of each feature page: one summary sentence, then a
  compact grid of feature cards (icon · feature name · one sentence on how it works).
- The block is **collapsible**: open on a reader's first visit to the page, remembered closed once the
  reader folds it, so a returning reader keeps the page as dense as today. The heading line carries a
  small «عن هذه الصفحة» toggle to reopen it.
- Pages covered (6): «سور القرآن» (`/surah`, `/surah/[number]`),
  «دراسة الآيات» (`/verse-study`), «فهرس الجذور» (`/roots`), «تحليل لساني عربي» (`/lexical`),
  «فواصل الآيات والسور» (`/fassila`), «بطاقة الكلمة» (`/qlisan`).
- Not covered: the landing page `/` (it *is* already a presentation of the features), the
  deep-link page `/verse/[surah]/[ayah]` (a single verse, no features to explain), and «محاورة القرآن»
  (`/chat`) — its layout is left untouched for now and will be revisited in a later change.
- All introduction copy is Arabic and lives in `lib/strings.ts`, under one `S.intro` namespace.
- No backend change, no route change, no data change.

## Capabilities

### New Capabilities
- `page-introductions`: every feature page shows, under its heading, a collapsible introduction —
  summary + feature cards — with bounded size, Arabic copy from the strings dictionary, and a
  per-page remembered open/closed state.

### Modified Capabilities
<!-- None: the introductions add to the pages without changing any existing requirement. The
     arabic-ui-locale and rtl-app-shell requirements (strings in one dictionary, logical
     properties, Amiri, direction-isolation) are complied with, not changed. -->

## Impact

- **Frontend only**: one new component (`components/PageIntro.tsx`), new `S.intro.*` strings in
  `lib/strings.ts`, one insertion per page (`components/SurahPicker.tsx` — shared by both
  reading routes —, `app/verse-study`, `app/roots`, `app/lexical`, `app/fassila`, `app/qlisan`).
- `/chat` and `ChatInterface.tsx` are not touched.
- Tests (local-only): a Vitest file for `PageIntro`; `test_frontend_reachability.py` sees the new
  component reached from the pages.
- No API, dataset, or dependency change (icons come from the existing `lucide-react`).
