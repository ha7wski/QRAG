## 1. Pure shaping logic (offline, tested first)

- [x] 1.1 Write failing tests for root selection: only `morphology.json` keys with `count > 0` are
  listed; `نوس` and `طمن` are absent; `أنس` and `طمأن` appear once; the total equals the `count > 0`
  key count (spec: *The index lists every root…*).
- [x] 1.2 Write failing tests for grouping: there are 28 groups in hijāʾī order; `اول`, `اني` and
  `أبب` fall in «أ»; there is no «ا» group; `ا`, `أ` and `ء` all resolve to «أ»; in-group order is
  total and stable across two runs (design D2).
- [x] 1.3 Implement the grouping key (first radical → `arabic_text.fold_carrier` → «أ» mapping) and
  the in-group sort key (carrier-folded hijāʾī order, exact spelling as tie-break). Read the root keys
  through `quran_data.loaders.morphology()`, never by path.
- [x] 1.4 Write failing tests for per-root figures: for رحم, words / āyāt / refs equal
  `VerseLookup.root_forms("رحم")`; كيف reports 3 words; sūras are distinct, carry Arabic names and
  never exceed 114.
- [x] 1.5 Implement the per-root entry builder: call `root_forms`, derive the distinct sūras from
  `verse_ids`, and attach the sūra names from the existing sūra metadata.
- [x] 1.6 Write failing tests for the reading: ضرب gives «دفع شديد جداً، متوقف مكرر منتهٍ بجمع مستقر»;
  كتب keeps both alternatives bracketed even when a signed reading exists in a temp `APP_DB_PATH`;
  زلزل carries a refusal reason and no sentence; a patched lock failure yields figures without
  readings plus one notice.
- [x] 1.7 Implement the reading attachment: lazily import `assemble`, always call it without
  `SignedChoices`, map a refusal to `reading_refusal`, and catch `TableNotFrozen` / `WasfNotFrozen`
  once per letter.

## 2. API

- [x] 2.1 Add `api/models/roots.py`: the letter-group summary, the root entry (`root`, `words`,
  `ayat`, `surahs`, `verse_ids`, `surah_list`, `reading` | `reading_refusal`) and the letter response
  (with an optional `reading_notice`).
- [x] 2.2 Add `api/routers/roots.py` with `GET /roots` and `GET /roots/letter/{letter}` (404 for an
  unknown letter), reading `app.state.verse_lookup` only and memoising each letter's payload in
  process (design D3, D4).
- [x] 2.3 Mount the router in `api/main.py` with one `include_router` line.
- [x] 2.4 Route tests: the counts in `GET /roots` sum to the listed total; `/roots/letter/ء` equals
  `/roots/letter/أ`; after both calls `GET /health` still reports the embedder and the reranker as
  not loaded.
- [x] 2.5 Update `tests/test_served_surface.py` with the two new routes and their consumer, and keep
  `test_import_direction.py` and `test_module_root_depth.py` green.

## 3. Frontend

- [x] 3.1 Add the types and client functions (`fetchRootLetters`, `fetchRootsByLetter`) to
  `lib/api.ts` / `lib/types.ts`.
- [x] 3.2 Add the strings to `lib/strings.ts`: `nav.roots` «فهرس الجذور», the count labels and the
  refusal and notice texts. Reuse the existing assembly label constant instead of retyping it.
- [x] 3.3 Build `app/roots/page.tsx`: the letter strip with counts; `?letter=` through
  `useSearchParams` under Suspense, with `router.replace` on change; per-root cards (counts, reading
  with label or refusal, sūra chips → `/surah/{n}`, collapsed āya links → `/verse/{s}/{a}` with their
  count, links to `/lexical?word=` and `/verse-study?word=`); all Arabic through `ArabicText`.
- [x] 3.4 Add the Navbar entry after «تحليل اللسان», with an icon unused elsewhere.
- [x] 3.5 Vitest: the page lists a mocked letter's roots; āyāt are collapsed until expanded; the label
  is present; Islambouli's published sentence is never rendered; the navigation shows seven entries
  in spec order with unique icons.
- [x] 3.6 Run `npx tsc --noEmit -p tsconfig.test.json` and confirm `test_frontend_reachability.py`
  finds no orphan.

## 4. Verification and docs

- [x] 4.1 Run `python -m pytest -q` and `cd frontend && npx vitest run`; all green.
- [x] 4.2 Launch the app, open `/roots?letter=ض` and `/roots?letter=أ`, and check ضرب's sentence and
  label, the bracketed alternatives of كتب (under «ك»), a refused quadriliteral, and the working deep
  links.
- [x] 4.3 Update CLAUDE.md (served routes, frontend pages, the seven-entry nav order) and the root
  README's page list if it enumerates pages.

## 5. Adjustments after review of the running page

- [x] 5.1 Write the refusal reasons of `compose()` and `assemble()` in Arabic (D7); `roots.py` stops
  falling back to `refusal_code`; tests assert no Latin letter in any reason over every root.
- [x] 5.2 Add `forms` (from `root_forms`) to each root entry, model and frontend type.
- [x] 5.3 Fold each root card behind its header (root + counts always visible).
- [x] 5.4 Add «النظائر» right after «السور», listing `forms`.
- [x] 5.5 Label āya links «<sūra name> <āya>» instead of `s:a`.
- [x] 5.6 Switch letter selection to `router.push` so Back returns to the previous letter.
- [x] 5.7 Update backend and Vitest tests; run pytest, vitest, both tsc; check the page in a browser.
- [x] 5.8 Drop the card's āya list and «تحليل اللسان» link; keep one green «الكلمة في الآيات»
  button; rename «النظائر» to «المواضع».
- [x] 5.9 Restore «تحليل اللسان» as a green button to the left of «الكلمة في الآيات».

## 6. Tab names and «التحليل النحوي»

- [x] 6.1 Rename tabs and their page headings: «دراسة الآيات»، «تحليل لساني عربي»، «فواصل الآيات والسور».
- [x] 6.2 Remove «التحليل النحوي»: nav entry, `/tahlil` page, `TahlilClaim`, `tahlilTypes`, client
  functions; quarantine `/tahlil/word` + `/tahlil/review` (imported, not mounted) and pin them unmounted.
- [x] 6.3 Move «فهرس الجذور» before «تحليل لساني عربي» in the navigation.
