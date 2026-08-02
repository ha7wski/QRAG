## Why

"Find Verse context" is a small, single-purpose page (surah + ayah picker → verse in
context) that lives as its own top-level nav entry, yet it is really the read-a-verse
destination that the two "Verse Study" tabs already link out to. Folding it into Verse
Study as a third tab groups the three verse-exploration tools in one place, trims the
sidebar from four entries to three, and lets a verse clicked in "Word in Verses" or
"Similar Verses" open its context in the same page instead of navigating away.

## What Changes

- Add a third tab **"Find Verse context"** to the Verse Study page, placed **after**
  "Similar Verses". It carries the full existing behaviour of the standalone page: Arabic
  surah picker + ayah number → the chosen verse rendered with the 3 verses before and
  after, vocalized, plus the "Open full Sourate page" link.
- **BREAKING (route removal):** delete the `/verse-context` page. The route no longer
  exists.
- Repoint every internal link that targeted `/verse-context`:
  - The two in-page verse links in Verse Study ("Word in Verses" and "Similar Verses"
    cards) now open the verse in the new **Find Verse context** tab of the same page
    (in-page tab switch + preselected verse) instead of navigating to `/verse-context`.
  - The "← Back to verse context" link on the `/verse/[surah]/[ayah]` error state points
    to the Verse Study page's context tab.
- Remove the **"Find Verse context"** entry from the sidebar nav (`Navbar.tsx`) and the
  matching feature card on the landing page (`app/page.tsx`) — its functionality is now
  reached through Verse Study.
- Preserve deep-linking: entering the context tab with a target verse (via query params)
  still auto-loads that verse, so back-links and shared URLs keep working.

## Capabilities

### New Capabilities
- `verse-study`: The tabbed verse-exploration page — "Word in Verses", "Similar Verses",
  and the newly added "Find Verse context" tab — including how verses selected in one tab
  open in the context tab and how the context tab deep-links to a target verse.

### Modified Capabilities
<!-- No existing OpenSpec specs to modify (openspec/specs/ is empty). -->

## Impact

- **Frontend only. No backend change** — the context tab reuses the existing `getVerse`
  API (`GET /verse/{surah}/{ayah}`) and `getSurahs` (`GET /surahs`); no new endpoints.
- Files touched:
  - `frontend/src/app/verse-study/page.tsx` — add the third tab + context sub-component,
    move logic from the standalone page, in-page verse selection wiring.
  - `frontend/src/app/verse-context/page.tsx` — **deleted** (directory removed).
  - `frontend/src/components/Navbar.tsx` — drop the "Find Verse context" link.
  - `frontend/src/app/page.tsx` — drop the "Find Verse context" feature card.
  - `frontend/src/app/verse/[surah]/[ayah]/page.tsx` — update the back link target.
- Nav order becomes: Talk to Quran · Verse Study · Lisan Analysis (three entries).
- Any external bookmark to `/verse-context` breaks; internal references are all updated.
- Docs note: `CLAUDE.md` (local-only) describes `/search` and `/verse-context` framing;
  it is out of scope for code but should be refreshed separately if desired.
