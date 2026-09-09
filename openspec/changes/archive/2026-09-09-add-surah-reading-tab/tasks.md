## 1. The Basmala display helper

- [x] 1.1 In `indexing/corpus.py`, add a module-level diacritic character class written
  with explicit `\u` escapes only (harakat U+0610–U+061A, U+064B–U+065F, U+0670, waqf marks
  U+06D6–U+06ED, tatweel U+0640), with an inline comment naming each range and stating why
  a literal Arabic class is forbidden.
- [x] 1.2 Add `_bare(text)` (strip that class) and `basmala_text()` — the vocalized Basmala
  read from `chakl_by_ref()[(1, 1)]["text"]`, cached, never a source literal.
- [x] 1.3 Add `strip_leading_basmala(surah, ayah, text)`: return `text` unchanged when
  `ayah != 1` or `surah == 1`; otherwise, when `_bare(text)` starts with the bare Basmala,
  walk the raw string counting non-diacritic characters until the bare length is consumed,
  absorb the trailing marks on the last consumed letter and the following whitespace, and
  return the remainder.
- [x] 1.4 Add `surah_basmala(surah)`: the vocalized Basmala for sūras that open with one,
  `""` for sūra 1 and sūra 9.
- [x] 1.5 Extend the `chakl_by_ref()` docstring with the offset contract — the rows are
  sliced by `chakl_char_start`/`chakl_char_end` from `analysis/qlisan_data.word_index()`,
  so the Basmala must not be stripped here.

## 2. Tests for the helper (write before wiring it in)

- [x] 2.1 `tests/test_basmala_strip.py`: `2:1` → `الم`; `1:1`, `9:1` and `27:30` returned
  unchanged; the strip is a no-op for every `ayah != 1`.
- [x] 2.2 Sweep all 114 first āyāt: exactly 113 are detected as Basmala-prefixed (all but
  sūra 9), and none still carries the prefix after stripping.
- [x] 2.3 Guard the character class: `_bare()` on a fixture āya preserves every Arabic
  letter and removes only marks, waqf signs and tatweel — this is the test that catches a
  literal class being re-introduced.
- [x] 2.4 Guard the loader: `chakl_by_ref()[(2, 1)]["text"]` still begins with the Basmala,
  and slicing it with the stored offsets for `2:1:1` still yields `الٓمٓ`.
- [x] 2.5 `surah_basmala`: non-empty for 2 and 114, empty for 1 and 9.

## 3. Wire the strip into every API surface

- [x] 3.1 `api/models/verse.py` — apply `strip_leading_basmala` in `verse_from_record` when
  auto-filling `text_ar_tashkil`. An explicitly passed `text_ar_tashkil` stays an override
  and is not touched.
- [x] 3.2 `retrieval/verse_lookup.py` — strip in `_verse_row` **before** calling
  `_match_indices`, so the highlight offsets are computed against the text actually emitted.
- [x] 3.3 `api/models/verse.py` — add `basmala: str = ""` to `SurahResponse`, with a comment
  saying it is the sūra's opening Basmala and empty for sūras 1 and 9.
- [x] 3.4 `api/routers/verse.py` — fill `basmala` from `surah_basmala(number)` in
  `get_surah`.
- [x] 3.5 Confirm `/qlisan` and `analysis/mizan` are untouched: neither goes through
  `verse_from_record`, and both keep reading `chakl_by_ref()` directly.

## 4. Tests for the API surfaces

- [x] 4.1 `GET /surah/2` — first verse's `text_ar_tashkil` is `الم`, `basmala` is non-empty.
- [x] 4.2 `GET /surah/1` — `basmala` is `""` and the first verse is still the Basmala.
- [x] 4.3 `GET /surah/9` — `basmala` is `""` and the first verse is unchanged.
- [x] 4.4 `GET /verse/2/1` — subject and neighbours carry the stripped text.
- [x] 4.5 Verse Study word lookup — a row for an āya 1 carries the stripped text, and its
  `match_indices` still land on the matched word in that text.

## 5. Frontend — the reading page

- [x] 5.1 Extract the current `/surah/[number]/page.tsx` body into a shared client component
  (e.g. `components/SurahReader.tsx`) taking the sūra number as its prop.
- [x] 5.2 Add the sūra picker above the reading area: a `<select>` over `getSurahs()`,
  listing «number · Arabic name» with Arabic-Indic numbers, matching the pickers in
  `FassilaAnalysisTab` and `/qlisan`; choosing an entry navigates to `/surah/{n}`.
- [x] 5.3 Render `data.basmala` as a centred, unnumbered heading between the header and the
  text block when non-empty; render nothing when empty. No test on the sūra number.
- [x] 5.4 Keep the existing header (Arabic name · number · period · āya count, Arabic-Indic
  digits) and the continuous vocalized text block with `﴿n﴾` markers.
- [x] 5.5 Keep the previous/next sūra pagination row as it stands — it already satisfies
  the RTL icon rules (previous at the right pointing right, next at the left pointing left)
  and is hidden at sūra 1 and sūra 114.
- [x] 5.6 Give each āya marker a stable DOM id (`ayah-{n}`) so a position inside the sūra
  is addressable and the resume scroll has a target.
- [x] 5.7 Reduce `app/surah/[number]/page.tsx` to a wrapper around the shared component.
- [x] 5.8 `lib/types.ts` — add `basmala?: string` to `SurahResponse`.

## 6. Frontend — the reading position

- [x] 6.1 Add `lib/readingPosition.ts` — `read()` / `write(surah, ayah)` over one
  `localStorage` key, on the pattern of `lib/conversations.ts`: `window` guard for SSR,
  try/catch around both, and validation (sūra in `1…114`, āya a positive integer) so a
  corrupt or hand-edited value is discarded rather than trusted.
- [x] 6.2 Add `app/surah/page.tsx` as a **client** component: read the stored position and
  `router.replace` to `/surah/{n}#ayah-{a}`, falling back to `/surah/1`. Render only a
  neutral loading state — never a sūra — so no wrong sūra is painted before the hop.
- [x] 6.3 In the shared component, apply the incoming āya fragment in a layout effect once
  the verses are in the DOM, scrolling with `behavior: "auto"`; clamp the āya to the loaded
  sūra's length and fall back to the top when it is out of range.
- [x] 6.4 Track the first āya marker visible in the viewport with an `IntersectionObserver`,
  attached **only after** the restore scroll has been applied, so the observer cannot
  overwrite the stored position with the top of the sūra.
- [x] 6.5 Persist the tracked position on a debounce (~500 ms) and on `pagehide`, never on
  every scroll event — `localStorage` writes are synchronous.
- [x] 6.6 Write the sūra on mount for every entry path (picker, stepper, deep link, direct
  URL), so any way of reaching a sūra updates the remembered one.
- [x] 6.7 Confirm a deep link opens at the top: the fragment is absent, so no restore runs.

## 7. Tests for the reading position

- [x] 7.1 `lib/readingPosition.test.ts` — round-trip; absent key → fallback; unparsable
  value → fallback, no throw; sūra 0 / 115 / non-numeric → fallback; a write that throws
  (quota) is swallowed and does not propagate.
- [x] 7.2 A `localStorage` getter that throws (blocked site data) is tolerated on read.
- [x] 7.3 Component test: with a stored position, `/surah` replaces to that sūra's address
  carrying the āya fragment; with none, it replaces to `/surah/1`.
- [x] 7.4 Component test: an āya beyond the loaded sūra's length does not scroll and does
  not throw.

## 8. Frontend — navigation and strings

- [x] 8.1 `lib/strings.ts` — add `S.nav.surahs = "سور القرآن"` and the picker's label and
  failure strings.
- [x] 8.2 `components/Navbar.tsx` — insert the `/surah` entry and reorder to: `/chat`,
  `/surah`, `/verse-study`, `/lexical`, `/tahlil`, `/fassila`.
- [x] 8.3 Give the new entry an icon that is neither `BookOpen` (brand + «التحليل النحوي»)
  nor any other entry's icon.
- [x] 8.4 Confirm `isActive` highlights the entry on `/surah` and on `/surah/{n}` — it
  already uses `pathname.startsWith(href)`.

## 9. Verification

- [x] 9.1 `python -m pytest -q` — the new tests pass and nothing regresses, in particular
  the QLisan and mīzān suites that slice by character offset.
- [ ] 9.2 `cd frontend && npx vitest run` — `verse-study/page.test.tsx` still asserts
  `href="/surah/29"` and still passes.
  **Left open, and not by this change.** The suite has 14 pre-existing failures across
  `conversations.test.ts`, `LisanResult.test.tsx` and `verse-study/page.test.tsx` —
  reproduced identically at HEAD with this change stashed. They are tests left in English
  by the Arabization commit `7cd3104` ("New conversation" vs «محادثة جديدة», the
  "Similar Verses" tab name, a «تحليل نحوي» section since removed); the files are
  git-excluded, so no CI caught the rot. `test_madar.py` has the same flavour of failure
  on the backend, also reproduced at HEAD.
  What this task actually protects — the deep-link contract — was verified another way:
  `VerseCard`, `VerseContextCard` and `/verse/{s}/{a}` all still emit `/surah/{n}`, the new
  route serves them, and following such a link was checked in the running app. The failing
  assertion is on the link's English *name*, not on its `href`. Refreshing those 14 tests
  is separate work, on features this change does not touch.
- [x] 9.3 `cd frontend && npx tsc --noEmit` (or `next build`) — types are clean.
- [x] 9.4 Run the app and read, in order: al-Fātiḥa (Basmala as āya `﴿١﴾`, no heading),
  al-Baqara (heading + body opening `الم ﴿١﴾`), at-Tawba (no Basmala anywhere), an-Nās
  (heading + `قل أعوذ برب الناس ﴿١﴾`).
- [x] 9.5 Check the correction reached the other surfaces: ask the chat something answered
  from an āya 1, and open «الكلمة في الآيات» on a word occurring in an āya 1 — neither shows
  the Basmala glued to the āya, and the word highlight is still on the right word.
- [x] 9.6 Open `/qlisan` on `2:1` and confirm the word fiche still resolves `الم` — the
  offset path is deliberately unchanged.
- [x] 9.7 Reading position by hand: scroll into al-Baqara, leave for the chat, return
  through «سور القرآن» — al-Baqara reopens where it was left. Then hard-reload and re-enter:
  the position is still there. Then Back from the resumed sūra — it returns to the previous
  page, not to `/surah`.
- [x] 9.8 Reading position in a private window (storage blocked): the page renders, reading
  works, nothing is thrown, and the entry falls back to al-Fātiḥa.
- [x] 9.9 Read the last āyāt of al-Baqara, follow the next-sūra link into Āl ʿImrān, then
  re-enter through the navigation — Āl ʿImrān is the remembered sūra.
- [x] 9.10 Update `CLAUDE.md`: the navigation order, the new `/surah` page with its reading
  position, and the `text_ar_tashkil` contract with its QLisan/mīzān exception.
