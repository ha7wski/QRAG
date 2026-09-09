## Why

The Arabization change (`2026-09-09-arabize-frontend-rtl`, decision D6) split the interface
across two typefaces: **Amiri** for Qurʾānic text, **IBM Plex Sans Arabic** for every piece of
chrome. Seen running, the split does not read as the boundary D6 predicted — it reads as two
applications sharing a window. The heading of `/fassila` (`الفواصل في القرآن الكريم`, Amiri at
`font-semibold`) is the register the whole product should speak in, and the sans chrome around
it is what looks foreign.

The owner's decision, after using the built product: **one Arabic voice everywhere**. Amiri
carries the interface as well as the revealed text; the sans face is demoted from "the chrome
face" to "the face that draws digits and Latin", which is the one job it was measurably better
at and the one the numeral policy depends on.

## What Changes

- **BREAKING (spec-level).** Amiri becomes the document's default typeface — headings, sidebar
  entries, tab strips, buttons, labels, captions, status lines, chart annotations, every Arabic
  string in the application. The rule "chrome is set in the UI face, not in Amiri" is reversed.
- IBM Plex Sans Arabic stays vendored and stays loaded, with a **narrowed role**: Western digits
  (`0–9`), percentages, verse references such as `2:255`, QAC tags, and the French/English
  translation paragraphs. Every number in the application therefore renders exactly as it does
  today — that continuity is a requirement of this change, not a side effect.
- The two faces stop being selected per element and start being selected **per script**: Amiri
  is declared only over the Arabic Unicode ranges, so anything outside them falls through to
  Plex on its own. No component needs a font class to obtain the right face.
- Arabic-Indic digits (`٣١٣`, U+0660–0669) stay inside the Arabic range and therefore stay in
  Amiri — the reading/analysis numeral split of `arabic-ui-locale` is preserved untouched.
- The vendored `amiri-*-latin.woff2` subsets are removed, since Amiri is no longer the face that
  draws Latin characters or digits anywhere.

## Capabilities

### New Capabilities

None. This change re-decides an existing requirement; it introduces no new surface.

### Modified Capabilities

- `rtl-app-shell`: the requirement *"Interface typography is distinct from Qurʾānic typography"*
  is replaced. Its self-hosting requirement and its no-third-party-fetch scenario are kept
  verbatim; its role assignment is inverted (Amiri for all Arabic, the second face for digits
  and Latin) and the guarantee that digits keep their present rendering is made explicit.

## Impact

- `frontend/src/app/globals.css` — the `@font-face` block (drop the two Amiri Latin faces) and
  the `.arabic-text` rule.
- `frontend/src/app/fonts/` — delete `amiri-400-latin.woff2` and `amiri-700-latin.woff2`;
  update `README.md` (provenance table and the two-faces rationale).
- `frontend/tailwind.config.ts` — the `arabic` / `ui` / `sans` font stacks.
- No component file changes. `font-ui` is referenced nowhere in the source, and `font-arabic` /
  `.arabic-text` keep resolving to Amiri, so every existing class keeps its present meaning.
- No backend, API, or data change. No dependency change: both faces are already vendored.
- Unaffected by construction: the `.western-digits` / `tabular-nums` numeral policy, the
  `toArabicDigits()` reading numerals, and the `dir`/bidi rules of `rtl-app-shell`.
