## 1. Give Amiri the Arabic ranges only

- [x] 1.1 Delete the two Amiri Latin `@font-face` blocks (400 and 700) from
      `frontend/src/app/globals.css`, so no Amiri face claims U+0000–00FF any more.
- [x] 1.2 Delete `frontend/src/app/fonts/amiri-400-latin.woff2` and
      `amiri-700-latin.woff2`.
- [x] 1.3 Rewrite the stylesheet's header comment: the two faces are no longer "two roles"
      by element but one face per script — Amiri draws Arabic, Plex draws everything else.

## 2. Make Amiri the default and Plex the fallthrough

- [x] 2.1 In `frontend/tailwind.config.ts`, set `fontFamily.arabic` and `fontFamily.sans` to
      `["Amiri", "IBM Plex Sans Arabic", "Segoe UI", "system-ui", "serif"]`; leave
      `fontFamily.ui` Plex-first as the named opt-out. Drop `"Scheherazade New"` (design D3).
- [x] 2.2 In `globals.css`, replace the hard-coded stack in `.arabic-text` with
      `@apply font-arabic`, keeping `direction: rtl` and `line-height: 2.2`.
- [x] 2.3 Re-comment `.western-digits` — the `locl` guard now protects against a re-added
      Amiri Latin subset rather than against today's rendering (design D3, Risks).
- [x] 2.4 Prepend `U+0020, U+00A0` to the two Amiri Arabic `unicode-range` declarations, so
      the word space inside an Arabic sentence stays Amiri's (found by task 4.2; design D2,
      amended). No file is re-vendored — the glyph is already in the Arabic subset.

## 3. Update the vendoring documentation

- [x] 3.1 In `frontend/src/app/fonts/README.md`, rewrite the "two faces, two roles" opening
      to the per-script rule, and record why the Amiri Latin subsets were dropped (D2).
- [x] 3.2 Update the provenance table: remove the two Amiri Latin rows and correct the file
      count and total size.
- [x] 3.3 Keep `OFL-Amiri.txt` — the face is still shipped, only two of its subsets are not.

## 4. Verify on the running application

- [x] 4.1 Rebuild the frontend and confirm every vendored woff2 still resolves (no 404 for a
      deleted Amiri Latin file) and that no page requests a font from a third-party host.
- [x] 4.2 Measure, on `/fassila` and `/chat`, that a chrome label (sidebar entry, tab strip)
      now renders in Amiri, using the canvas-width comparison against both faces.
- [x] 4.3 Measure that `93`, `111` and `83.8%` still render in IBM Plex Sans Arabic with the
      same widths as before the change.
- [x] 4.4 Confirm an āya number produced by `toArabicDigits()` stays Arabic-Indic and renders
      in Amiri, and that a `VerseCard` translation paragraph still renders in Plex.
- [x] 4.5 Visual pass at the smallest chrome sizes for legibility and clipping (design
      Risks): `text-xs` badges in `VerseCard`, the 11 px chart annotations on `/fassila`,
      the sidebar entries and the tab strip. Report anything that crowds or clips.

## 5. Close the change

- [x] 5.1 Run `openspec validate amiri-interface-typeface`.
- [x] 5.2 Run the frontend unit tests (`cd frontend && npx vitest run`) — they must be
      unaffected. Note: 14 of 77 fail on this branch *before* the change too (LisanResult
      sections, Verse Study cards, `deriveTitle`); verified identical with the change
      stashed, so they are pre-existing and out of scope here.
