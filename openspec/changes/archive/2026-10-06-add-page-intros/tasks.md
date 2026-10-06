## 1. Copy

- [x] 1.1 Verify every feature claim of design D7 against the code (reading position, chunk size, root-card unfold, qlisan levels) and correct the drafts
- [x] 1.2 Add `S.intro` to `lib/strings.ts`: `toggle`, `region`, and one `{ summary, features[] }` entry per page (surah, verseStudy, roots, lexical, fassila, qlisan), referencing existing strings for feature titles
- [x] 1.3 Move the inline Fassila caption literal to `S.fassila.caption`
- [x] 1.4 Check every summary ≤ 30 words and every card sentence ≤ 25 words

## 2. Component

- [x] 2.1 Create `components/PageIntro.tsx`: tinted region, summary, responsive card grid (1/2/3 columns; 2 × 2 for four cards), decorative icons, logical properties only
- [x] 2.2 Add the heading-line toggle «عن هذه الصفحة» (`aria-expanded`, `aria-controls`, keyboard), fold animation honouring `prefers-reduced-motion`
- [x] 2.3 Persist the folded state under `intro.<id>.folded` in `localStorage`, every access in try/catch, server render open, no animation on the first client read

## 3. Pages

- [x] 3.1 `/surah` + `/surah/[number]`: add the intro to `SurahPicker`'s heading block (one id for both routes)
- [x] 3.2 `/verse-study`: intro under heading and caption, above the tabs
- [x] 3.3 `/roots`: intro above the letter strip
- [x] 3.4 `/lexical`: intro above the word input
- [x] 3.5 `/fassila`: intro above the tabs
- [x] 3.6 `/qlisan`: intro above the verse picker

## 4. Verification

- [x] 4.1 Vitest for `PageIntro`: open by default, fold persists per id, storage throwing degrades to open, toggle exposes `aria-expanded`
- [x] 4.2 Vitest: each page's card titles are strings that page renders (catches a renamed tab)
- [x] 4.3 `npx tsc --noEmit -p tsconfig.test.json`, `npx vitest run`, `python -m pytest -q` (reachability test) pass
- [x] 4.4 Visual check in the browser at 360 px, 768 px and 1280 px on all six pages; confirm `/chat` is unchanged: no horizontal scroll, open intro ≤ about a third of the desktop viewport, folded intro one line
