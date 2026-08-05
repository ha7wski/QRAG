## 1. Reference fixture

- [x] 1.1 Extract the validated `SURAS` blob from `~/Downloads/fassila_quran_2.html` (regex `const SURAS = (\[.*?\]);`, then `json.loads`) into `tests/fixtures/fassila_reference.json` — 114 sūras, 6236 āyāt, shape `{n, name, nv, v:[{a, l, w, m?}]}`. This is the golden reference for every check below.
- [x] 1.2 Copy the prototype to `openspec/changes/add-fassila-analysis/reference/fassila_prototype.html` so the behavior/design reference survives independently of `~/Downloads`.
- [x] 1.3 Assert the fixture's own integrity: 114 sūras, 6236 āyāt, exactly 20 `m`-flagged āyāt across 19 sūras, and 25 distinct fāṣila letters over the 6216 analysed āyāt.

## 2. Backend — derivation core (`analysis/fassila.py`)

- [x] 2.1 Anchor paths with `ROOT = Path(__file__).resolve().parents[1]` per the repo convention. **Source words from the QAC treebank (Uthmānī rasm), not `quran_chakl.csv`** — see design.md D2; the vocalized CSV is read only for sūra names.
- [x] 2.2 Implement `strip_marks(text)` — remove tashkīl (U+0610–U+061A, U+064B–U+065F, U+0670 handled separately), tatweel U+0640, and the annotation symbols U+06D6–U+06DC and U+06E9. Verify the range covers U+064C–U+0659 (dammatan, kasratan, fatḥa, ḍamma, kasra, shadda, sukūn, madda, hamza above/below) — a naive two-range regex misses exactly this block.
- [x] 2.3 Implement `qac_ayah_words()` — reconstruct each orthographic word by concatenating its QAC segments in order, folding alif waṣla `ٱ`→`ا` for display. Word indices are then the `s:a:w` spine by construction, and no Basmala stripping is needed (QAC carries none).
- [x] 2.4 Implement `fasila_of(word)` — apply the pausal rules in spec order: drop trailing non-letters → remove tashkīl → neutralize tanwīn (keeping a written alif under fatḥatān) → `ة`→`ه` → `ى`→`ا` and final dagger alif `ٰ`→`ا` → return the last character.
- [x] 2.5 Implement `muqattaat_refs()` — parse `data/raw/quran-morphology.txt` (location `s:a:w:seg`, tab-separated, features in field 4), group segments by word, and return the frozen set of āyāt where **every** word carries `INL`. Cache with `functools.lru_cache`.
- [x] 2.6 Implement `analyse_surah(surah)` — per-āya `{ayah, fasila, word, word_ref, is_muqattaat}` plus aggregates: per-letter counts, percentages over **analysed** āyāt, frequency order (descending count, deterministic tie-break), first-appearance order, and totals (total / analysed / excluded, dominant letter + count + pct). Cache per sūra.
- [x] 2.7 Add a `__main__` smoke test printing sūra 12's summary, matching the pattern used by other modules.

## 3. Backend — tests (local-only, `tests/`)

- [x] 3.1 `test_fassila_reference.py` — assert the derivation reproduces **all 6236** `(surah, ayah) → fāṣila` pairs from the fixture. This is the highest-value test in the change; any divergence must name the failing āyāt.
- [x] 3.2 Assert the muqaṭṭaʿāt set is exactly the 20 frozen references: 2:1, 3:1, 7:1, 19:1, 20:1, 26:1, 28:1, 29:1, 30:1, 31:1, 32:1, 36:1, 40:1, 41:1, 42:1, 42:2, 43:1, 44:1, 45:1, 46:1.
- [x] 3.3 Assert non-exclusion of the continuing openers: 10:1 (الر), 13:1 (المر), 27:1 (طس), 38:1 (ص → fāṣila `ر`), 50:1 (ق), 68:1 (ن).
- [x] 3.4 **Rasm regression:** assert 20:14 → `ا` (the imlāʾī spelling would give `ي`), and spot-check that `2:1` yields the single word `الٓمٓ` at ref `2:1:1` and `1:1` keeps 4 words. (The planned word-count-vs-QAC post-condition is vacuous now that QAC *is* the source — see design.md D2.)
- [x] 3.5 Edge-case unit tests for `fasila_of`: tanwīn-over-alif → `ا`, `ة` → `ه`, `ى` → `ا`, dagger alif → `ا`, and a sajda-terminated āya (one of the 15 carrying `۩`).
- [x] 3.6 Assert percentages are computed over the analysed denominator and sum to 100 % for a sūra with exclusions (e.g. 42, which excludes two āyāt).

## 4. Backend — API surface

- [x] 4.1 `api/models/fassila.py` — Pydantic models: `FassilaAyah` (ayah, fasila, word, word_ref, is_muqattaat), `FassilaCount` (letter, count, percentage), `FassilaResponse` (surah number, Arabic name, total/analysed/excluded counts, dominant, frequency-ordered counts, first-appearance order, ayahs).
- [x] 4.2 `api/routers/fassila.py` — `GET /fassila/{surah}` with `Path(..., ge=1, le=114)`; read-only, no LLM, no state. Excluded āyāt appear in the list flagged and letterless.
- [x] 4.3 Register the router in `api/main.py` (one import + one `include_router`), keeping the existing alphabetical grouping.
- [x] 4.4 Verify: `GET /fassila/12` → 200, 111 entries, 0 excluded; `GET /fassila/42` → āyāt 1 and 2 flagged, letterless; `GET /fassila/0` and `/fassila/115` → 422.

## 5. Frontend — data layer

- [x] 5.1 Add `FassilaResponse` and friends to the frontend types, mirroring the Pydantic models.
- [x] 5.2 Add `getFassila(surah: number)` to `frontend/src/lib/api.ts`, following the existing `getSurah` shape.

## 6. Frontend — charts (ported from the prototype)

- [x] 6.1 `FassilaBars` — one row per fāṣila in descending frequency: letter, bar scaled to `count / max`, and `<count> آية · <pct>%`. Hover tooltip gives letter, count, analysed total, percentage.
- [x] 6.2 `FassilaLine` — hand-rolled SVG over a `viewBox`. Port the two mappings **verbatim** from the prototype, since they encode the two most easily-lost requirements:
  - `rowY(l) = mT + (nR - order.indexOf(l) - 0.5) / nR * plotH` → first-appearance order, bottom to top;
  - `ayaX(a) = mL + (a / N) * plotW` → X domain anchored at **0**, not at the first data point.
- [x] 6.3 Draw a single continuous `<polyline>` over the analysed āyāt (excluded āyāt contribute no vertex and must not break the path), plus per-vertex circles with an adaptive radius (`N>160 ? 1.6 : N>90 ? 2.1 : 2.6`) and a hover tooltip showing āya number, letter and vocalized word.
- [x] 6.4 Port `niceStep` / `xticks` for readable X ticks across sūra lengths from 3 to 286 āyāt; label each Y row with its letter and occurrence count.
- [x] 6.5 Wrap the SVG in an `overflow-x: auto` container so long sūras scroll the chart, never the page body.

## 7. Frontend — page (`/fassila`)

- [x] 7.1 Create `frontend/src/app/fassila/page.tsx` with `dir="rtl"` and 100 % Arabic copy — headings, tile captions, chart notes, tooltips. No English or French strings.
- [x] 7.2 Sūra selector over all 114 entries (`<number> · <Arabic name> — <n> آية`) plus prev/next controls, disabled at sūra 1 and 114 respectively.
- [x] 7.3 Three summary tiles — عدد الآيات · فواصل مميّزة · الفاصلة الغالبة (letter + count + pct) — with tabular figures.
- [x] 7.4 Exclusion note under the tiles, rendered only when the sūra has exclusions: `استُبعدت N آية مقطّعة من التحليل · M آية محلَّلة`.
- [x] 7.5 Collapsed methodology `<details>`: pausal rules, the exclusion scope stated as **20 āyāt in 19 sūras** (not the prototype's erroneous 16), why الر/المر/طس/ص/ق/ن are kept, corpus source, and the per-sūra frequency table.
- [x] 7.6 Loading and error states for the fetch, consistent with the existing pages.

## 8. Frontend — design language and navigation

- [x] 8.1 Style the page with Tailwind utilities in the project's idiom — cards `rounded-xl border border-gray-200 bg-white shadow-sm`, sub-headers `border-b border-gray-100 px-4 py-2`, header `text-2xl font-semibold text-gray-800` over `text-sm text-gray-500`, controls `rounded-lg border border-gray-300 px-3 py-2 focus:border-brand focus:outline-none`. No bespoke CSS custom properties.
- [x] 8.2 Draw both charts in the `brand` teal family (bars, polyline, vertices), with `gray-200` gridlines and `gray-500` axis labels; render Arabic through `.arabic-text` / `font-arabic`. Introduce **no** `dark:` variants, `data-theme` switching or theme toggle — dark mode is deferred app-wide (design.md D6).
- [x] 8.3 Add the nav entry to `frontend/src/components/Navbar.tsx` after `Verse Study`, with a lucide icon consistent with the existing set.

## 9. Verification

- [x] 9.1 Run `python -m pytest -q` — all backend tests green, including the 6236-pair reference check.
- [x] 9.2 Run `cd frontend && npx tsc --noEmit` and `npx next build` — no type or build errors.
- [x] 9.3 Visually diff `/fassila` against the prototype for sūras 12 (no exclusions), 42 (two exclusions), 2 (longest, 286 āyāt) and 108 (shortest, 3 āyāt): both charts, tiles and table must match.
- [x] 9.4 Confirm the two load-bearing chart behaviors by eye: the Y axis is ordered by **first appearance bottom-up** (not alphabetical, not frequency), and the leftmost X tick is **0**.
- [x] 9.5 Confirm the page reads as part of the app — brand teal charts, project card/header idiom, Amiri Arabic — and that there is no horizontal page scroll on a narrow viewport for sūra 2.
- [x] 9.6 Run `openspec validate add-fassila-analysis --type change --strict` and confirm the change is complete.
