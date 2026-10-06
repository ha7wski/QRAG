## 1. Prerequisite

- [ ] 1.1 Commit the pending working-tree work on the similarity routers/frontend (quarantined per-verse route) so this change starts from a clean base

## 2. Backend route

- [x] 2.1 Add `api/models/surah_annotations.py` (āya entry: `group`, `whole[]`, `passage[]` with `ref`, `score`, `span_self`, `span_other`; response with `surah`, `ayahs`, `verses`)
- [x] 2.2 Add `api/routers/surah_annotations.py`: read the sūra's groups from `surah_similarity.json` and its pairs from `quran_close_verses.json` via the existing readers; classify each pair (`similarity` in `from` → whole, `from == ["passage"]` → passage); orient spans to the āya's side; collect partner records through `verse_from_record`
- [x] 2.3 Errors: 422 outside 1..114, 503 with rebuild command on missing/malformed dataset or a span outside its verse's text; 200 with empty `ayahs` when nothing applies
- [x] 2.4 Mount the router in `api/main.py`
- [x] 2.5 Route tests: 3:10/3:116 group; 1:2 whole; 28:20 passage span starts «وَجَاءَ», ends «قَالَ»; empty sūra; missing dataset 503; payload size measured on sūra 2

## 3. Frontend data

- [x] 3.1 Add the client `getSurahAnnotations(n)` and its types to `lib/api.ts`
- [x] 3.2 Add Arabic strings (switch label, legend «آية قريبة داخل السورة» / «جزء مشترك في سائر القرآن» / «آية قريبة في سائر القرآن», bubble section titles «داخل السورة» / «في سائر القرآن», unavailable notice) to `lib/strings.ts`
- [x] 3.3 Pure helper: merge an āya's passage spans into disjoint runs and split its text into plain/marked segments; Vitest on overlap merging and on 28:20

## 4. Reading page

- [x] 4.1 Switch (default off, persisted in `localStorage` with try/catch) and legend in `SurahReader.tsx`; fetch annotations only while on, cached per sūra
- [x] 4.2 Marker cues: green fill (group), orange ring (whole pair), both; keep `id`/`data-ayah` intact
- [x] 4.3 Orange words for passage-only pairs on `text_ar_tashkil`; fall back to the orange marker when rendering `text_ar`
- [x] 4.4 On 503 / fetch failure: render the sūra unannotated with the Arabic notice
- [x] 4.5 Verify switch off renders exactly as before (no request, no extra markup)

## 5. Bubble

- [x] 5.1 `components/CloseVersesBubble.tsx`: anchored popover, `role="dialog"`, two sections (group partners in mushaf order; cross partners by score with sūra name, āya number, text, common part marked), no links
- [x] 5.2 Open on click/keyboard activation of an annotated marker or orange word only; close on Escape, outside click, or opening another āya; restore focus
- [x] 5.3 Reuse `SimilarVerseParts.tsx` text rendering without its «الآية في سياقها» link (extract a link-free variant if needed)
- [x] 5.4 Confirm opening/closing changes neither URL nor scroll position

## 6. Guards and docs

- [x] 6.1 Update `tests/test_served_surface.py`: new route mounted and called by `SurahReader`; per-verse route still unmounted
- [x] 6.2 `tests/test_frontend_reachability.py` and `npx tsc --noEmit -p tsconfig.test.json` pass
- [x] 6.3 Run `python -m pytest -q` and `npx vitest run`
- [x] 6.4 Check visually in the browser on sūras 1, 3 and 28 (colours, double cue, bubble), then settle the shades
- [x] 6.5 Update CLAUDE.md (served routes, reading page description) and the `surah-reading` spec purpose wording on archive
