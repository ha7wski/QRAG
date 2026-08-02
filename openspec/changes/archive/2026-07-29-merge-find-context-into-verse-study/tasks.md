## 1. Add the Find Verse context tab to Verse Study

- [x] 1.1 In `frontend/src/app/verse-study/page.tsx`, extend `type Tab` to
  `"word" | "similar" | "context"` and append `["context", "Find Verse context"]` to the
  `tabs` array (last, after "Similar Verses").
- [x] 1.2 Add page-level state: `contextTarget` (`{ surah, ayah, nonce } | null`) and an
  `openInContext(surah, ayah)` callback that increments the nonce, sets the target, and
  sets `tab` to `"context"`.
- [x] 1.3 Add a `FindVerseContext` sub-component that ports the standalone page's logic
  (surah picker via `getSurahs`, ayah input with clamping, `lookup` via
  `getVerse(surah, ayah, 3)`, highlighted verse + ±3 context rendering, "Open full Sourate
  page" link). Keep it mounted alongside the other two tabs (hidden via `className`).
- [x] 1.4 Wire `FindVerseContext` to react to `contextTarget`: a `useEffect` keyed on
  `contextTarget?.nonce` loads the target verse and syncs the picker's surah/ayah.
- [x] 1.5 Add deep-linking: wrap the page in `<Suspense>`, read `?surah=&ayah=` with
  `useSearchParams`, and on mount select the `"context"` tab and auto-load that verse.

## 2. Route verse clicks into the context tab (in-page)

- [x] 2.1 Pass `openInContext` down to `WordInVerses` and `SimilarVerses`.
- [x] 2.2 In `SurahCard` (Word in Verses), replace the
  `<Link href="/verse-context?surah=..&ayah=..">` around each verse with a clickable
  element calling `openInContext(v.surah_number, v.aya_number)`, preserving the current
  Arabic `title` and hover styling.
- [x] 2.3 In the Similar Verses result cards, replace the
  `<Link href="/verse-context?...">` with a clickable element calling
  `openInContext(v.surah_number, v.ayah_number)`, preserving styling.

## 3. Remove the standalone route and stale references

- [x] 3.1 Delete `frontend/src/app/verse-context/` (the `page.tsx` and its directory).
- [x] 3.2 Remove the `{ href: "/verse-context", label: "Find Verse context", ... }` entry
  from `links` in `frontend/src/components/Navbar.tsx`.
- [x] 3.3 Remove the "Find Verse context" feature object from `features` in
  `frontend/src/app/page.tsx`.
- [x] 3.4 Update the "← Back to verse context" link in
  `frontend/src/app/verse/[surah]/[ayah]/page.tsx` to point at `/verse-study`.
- [x] 3.5 Grep the frontend for any remaining `verse-context` reference and confirm none
  remain (`grep -rn "verse-context" frontend/src`).

## 4. Verify

- [x] 4.1 `cd frontend && npx tsc --noEmit` (or `next build`) passes with no type errors.
- [x] 4.2 Manual check: Verse Study shows three tabs in order; the context tab looks up a
  verse in context; clicking a verse in "Word in Verses" and "Similar Verses" switches to
  the context tab and loads it (including clicking the same verse twice); a
  `/verse-study?surah=X&ayah=Y` deep link opens the context tab pre-loaded; the sidebar and
  landing page no longer show "Find Verse context".
