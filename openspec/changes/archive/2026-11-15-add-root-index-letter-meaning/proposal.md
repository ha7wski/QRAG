## Why

«فهرس الجذور» lets the reader pick a first radical and lists its roots, but says nothing about the
letter itself. A compiled «معاني الحروف» sheet now exists (`data/maani-huruf/maani_huruf.json`: 28
letters, a core sense, a reading per position, the readings of six named authorities, drawing,
structure), and the root index is the natural place to read it: the reader has just chosen a letter.

## What Changes

- Selecting a letter on `/roots` shows ONE box describing that letter, placed right after the letter
  strip's selection and **before** the list of roots beginning with it. The strip itself is unchanged
  (no text under the buttons).
- The box shows, in Arabic only:
  - the letter, its name, the badge «تأويلي», and which series it comes from (Abu Qaisar's own
    letters vs. the 18 built by the generalised procedure) — the attribution is never blurred;
  - the core sense (`core_sense_ar`);
  - the three positions (أول / وسط / آخر): divine name or substitute word, sense, examples, with
    how that position was obtained (author / inferred from the author / rule / substitute word);
  - the readings per source, each attributed to its named authority (Abu Qaisar, سامر إسلامبولي,
    حسن عباس, البلوشي, منال نجار, السامرائي);
  - drawing, structure and, when present, the dimensions (ء / ي / و).
- Not shown: French fields, `videos`, `quran_refs`, `convergence`, `notes`, `discarded_poles`.
- The dataset moves to `data/references/maani_huruf.json` (curated scholarship carrying a human
  decision), gets a `paths.py` constant, a `manifest.py` entry and one cached loader.
- `GET /roots/letter/{letter}` gains an optional `maani` object (the letter's sheet, Arabic fields
  only), `null` when the sheet holds no entry or fails to load — never a 500. The «أ» group reads
  the entry of `ا`.

## Capabilities

### New Capabilities
- `letter-meaning-sheet`: the «معاني الحروف» dataset — its home, its loader, the shape served and
  the attribution rules the display must keep.

### Modified Capabilities
- `root-index`: `GET /roots/letter/{letter}` carries `maani`; the `/roots` page shows the letter box
  between the strip and the root list.

## Impact

- Data: `data/maani-huruf/maani_huruf.json` → `data/references/maani_huruf.json`; `quran_data/paths.py`,
  `manifest.py`, `loaders.py`.
- Backend: `api/routers/roots.py` (`build_letter` joins the sheet), `api/models/roots.py`
  (`LetterMeaning` model, `RootLetterResponse.maani`). No model, no LLM, no new route.
- Frontend: new `components/LetterMeaningBox.tsx`, `app/roots/page.tsx`, `lib/types.ts`,
  `lib/strings.ts`.
- Tests (local-only): `test_quran_data.py` stays green through the manifest entry; route test for
  `maani`; Vitest for the box and its position on the page.
