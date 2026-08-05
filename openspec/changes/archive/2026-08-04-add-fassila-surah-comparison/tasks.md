## 1. Backend — corpus aggregation

- [x] 1.1 In `analysis/fassila.py`, add a comment at `analyse_surah`'s
      `@lru_cache(maxsize=128)` recording that the bound is **load-bearing** for
      `overview()`: 128 ≥ 114, so the fan-out is memoized end-to-end; lowering it below 114
      turns every overview request into a full re-derivation.
- [x] 1.2 Add `surah_summary(surah)` (or an inline reshape) returning the compact per-sūra
      record — number, Arabic name, total / analysed / excluded āya counts, distinct count,
      **`fawasil` (the distinct letters, read off `counts` so they keep its
      descending-occurrence order)**, and dominant — all read **from `analyse_surah(surah)`**,
      with no derivation logic duplicated and no second pass over the corpus.
- [x] 1.3 Add `overview()`, `@lru_cache(maxsize=1)`, fanning out over sūras 1 → 114 and
      returning the summaries in sūra order plus the aggregates: sūra count, mean distinct
      count rounded to one decimal (reuse the module's existing rounding convention),
      mono-fāṣila count, maximum distinct count with the sūra(s) attaining it.
- [x] 1.4 Add the distribution buckets to `overview()`: one entry per distinct-fāṣila value
      from the observed minimum to the observed maximum, **contiguous** — emit a zero-count
      bucket for any gap — with the bucket counts summing to 114.
- [x] 1.5 Extend the module's `__main__` smoke test to print the aggregates and the buckets,
      matching the existing print style.
- [x] 1.6 Verify by hand: `python analysis/fassila.py` still prints the sūra-12 analysis, and
      the new output reads 114 sūras, mean `3.9`, 18 mono-fāṣila, maximum 12 (هود), with
      Hūd's `fawasil` reading `ن د ب ر م ط ظ ل ز ذ ق ص`.

## 2. Backend — API models and route

- [x] 2.1 In `api/models/fassila.py`, add `FassilaSurahSummary` (including
      `fawasil: list[str]`), `FassilaBucket`, and `FassilaOverviewResponse` (summaries +
      buckets + aggregates), documented in the module's existing docstring style — including
      why the aggregates are server-computed and why `fawasil` cannot be reconstructed from
      `distinct_count` and `dominant`.
- [x] 2.2 In `api/routers/fassila.py`, add `GET /fassila/overview` returning
      `FassilaOverviewResponse` from `analysis.fassila.overview()`.
- [x] 2.3 Declare that route **above** the existing `/fassila/{surah}` handler, with a
      comment stating the hazard: FastAPI matches in declaration order, `{surah}` is typed
      `int`, so a later declaration makes `/fassila/overview` fail integer coercion and
      return 422 without reaching the handler.
- [x] 2.4 Confirm `GET /fassila/{surah}` is untouched — same handler body, same response
      model, same 404/422 behaviour.

## 3. Backend — tests (local-only)

- [x] 3.1 Add tests asserting the aggregates on the real corpus: 114 summaries in sūra
      order, mean `3.9`, 18 mono-fāṣila sūras, maximum 12 attained by sūra 11.
- [x] 3.2 Add a test asserting the buckets run 1 → 12 contiguously, that the bucket for 3
      holds 30 sūras, and that the counts sum to 114.
- [x] 3.3 Add a test asserting each summary agrees field-by-field with `analyse_surah()` for
      a sample of sūras including 112 (4 āyāt, 1 distinct, `د` 100.0 %), 11 (123 āyāt, 12
      distinct, `ن` 56 at 45.5 %) and 42 (53 total / 51 analysed / 2 excluded, 8 distinct).
- [x] 3.4 Add a test for `fawasil` across all 114 sūras: its length equals `distinct_count`,
      its first element is the dominant letter, its order matches that sūra's `counts`, and
      sūra 112's list is exactly `["د"]`.
- [x] 3.5 Add the **route-ordering regression test**: build a bare `FastAPI()` with only the
      fassila router (the `pytest.importorskip("fastapi")` + `TestClient` idiom already used
      in `tests/test_madar.py`), assert `GET /fassila/overview` returns 200 with 114
      summaries — not 422 — and that `GET /fassila/12` still returns its per-sūra payload.
- [x] 3.6 Run `python -m pytest -q tests/test_fassila.py` (plus the new file) and confirm the
      pre-existing fāṣila tests and the reference fixture still pass unchanged.

## 4. Frontend — types and client

- [x] 4.1 In `frontend/src/lib/fassilaTypes.ts`, mirror the new backend models:
      `FassilaSurahSummary` (with `fawasil: string[]`), `FassilaBucket`,
      `FassilaOverviewResponse`, keeping the file's existing comment style and the
      "mirrors api/models/fassila.py" contract.
- [x] 4.2 In `frontend/src/lib/api.ts`, add `getFassilaOverview()` calling
      `GET /fassila/overview`, following the shape of the existing `getFassila()`.

## 5. Frontend — tab shell and tab 1 relocation

- [x] 5.1 Create `frontend/src/components/FassilaAnalysisTab.tsx` and move the **entire
      current body** of `app/fassila/page.tsx` into it — sūra selector, tiles, `FassilaBars`,
      `FassilaLine`, methodology, and the local `Tile` helper — with no change to markup,
      classes or behaviour.
- [x] 5.2 Rewrite `app/fassila/page.tsx` as the shell: the page header (title + one-line
      subtitle) above a tab bar offering `تحليل الفواصل` and `مقارنة السور`, first tab
      active on load, active tab visually distinguished.
- [x] 5.3 Keep both tab bodies **mounted**, toggled with a `hidden` class — the idiom in
      `app/verse-study/page.tsx` — so the sūra selected in tab 1 and the filter in tab 2
      survive switching.
- [x] 5.4 Fetch the overview on the **first activation** of tab 2 only, once per visit; show
      the page's existing loading and error idioms while it resolves.
- [x] 5.5 Verify tab 1 renders identically to the page before this change (same tiles, same
      bars, same sequence line, same methodology), and that selecting sūra 19, switching
      tabs and returning preserves the selection with no refetch.

## 6. Frontend — comparison tab: tiles, layout, list

- [x] 6.1 Create `frontend/src/components/FassilaComparisonTab.tsx` holding the tab's
      sections in the project's card idiom (`rounded-xl border border-gray-200 bg-white
      shadow-sm`), laid out in this order: **tiles → pie → sūra list → length × diversity →
      rank × diversity**. The list sits directly after the pie because the pie's only effect
      is to filter it.
- [x] 6.2 Render the four tiles — عدد السور, متوسط الفواصل المميّزة, سور بفاصلة واحدة,
      أقصى عدد فواصل — reading their values from the response, with the maximum tile naming
      هود. Reuse the tile idiom from tab 1 rather than inventing a second one.
- [x] 6.3 Hold the active category in one piece of state shared by the pie, its legend and
      the list; activating the already active category clears it.
- [x] 6.4 Render the sūra list in muṣḥaf order: number, Arabic name, āya count, distinct
      count, and the dominant fāṣila with its percentage — the letter in the Arabic face,
      every number in Western digits with tabular figures.
- [x] 6.5 Wire the category filter into the list: with a category active, show only its
      sūras; with none, all 114.
- [x] 6.6 Render the status line below the list: the category (how many sūras, how many
      distinct fawāṣil), then the **fawāṣil of the selection between parentheses**,
      enlarged, in the Arabic face.
- [x] 6.7 Compute those letters as the union of the selection's `fawasil`, ordered by
      **descending number of selected sūras carrying each letter**, ties broken by first
      appearance scanning the selection in muṣḥaf order. Verify the mono-fāṣila category
      yields `ا ر ه ن ل د س` and that emitting them in that order places `ا` rightmost in
      the RTL container — with **no** manual reversal.

## 7. Frontend — the distribution pie

- [x] 7.1 Create `frontend/src/components/FassilaDistributionPie.tsx` — an SVG pie, one
      slice per bucket, slices ordered by **ascending** distinct-fāṣila count.
- [x] 7.2 Build the ordinal fill ramp: interpolate 12 steps across the **validated
      anchor ramp** of design decision 9 — `#84c4ab · #6dad94 · #57967e · #407f69 · #296954
      · #0e5440` — light for few fawāṣil, dark for many. Do **not** use `brand.light`
      (`#e6f4f0`) as the light end: it is 1.13:1 on white.
- [x] 7.3 Verify the ramp with the checks that apply to an **ordinal** ramp — monotone
      lightness and a lightest step ≥ 2:1 against the white card. Do **not** run a
      categorical-palette validator on it: it fails a correct sequential ramp by design.
- [x] 7.4 Render the legend beside the pie, one row per bucket in the same ascending order,
      each carrying the distinct-fāṣila count, the sūra count and the percentage in Western
      digits, with a swatch in that bucket's fill.
- [x] 7.5 Make slice and legend row one control: activating either sets the category and
      marks **both** active; activating the active one clears it. Give legend rows keyboard
      focus and an Arabic accessible label.
- [x] 7.6 Give slices a minimum hit area so the three single-sūra buckets (9, 11, 12 — about
      3° each) stay selectable, and confirm by activating the bucket for 12 and getting هود.
- [x] 7.7 Show, on hover of a slice **or** its legend row, the same tooltip: the sūras of
      that category, one per line, each prefixed with `-`. Reuse the fixed-position tooltip
      pattern from `FassilaLine`.

## 8. Frontend — the two diversity lines

- [x] 8.1 Create `frontend/src/components/FassilaDiversityLine.tsx` — a reusable SVG line
      chart taking pre-sorted points plus axis metadata, drawing **one continuous polyline**
      with hoverable vertices on top, in the `brand` green family, following `FassilaLine`'s
      tick/tooltip/`overflow-x-auto` conventions.
- [x] 8.2 Render `طول السورة × تنوّع الفواصل` with it: X = āya count on a **linear** axis
      ascending left-to-right, Y = distinct count, sūras sorted by `(āya count asc, sūra
      number asc)` — the tie-break is required, 24 āya-count values are shared and two of
      them by five sūras each.
- [x] 8.3 Render `ترتيب السورة × تنوّع الفواصل` with the same component: X = sūra number
      1 → 114 ascending left-to-right, Y = distinct count.
- [x] 8.4 Confirm both lines keep plotting all 114 sūras while a category filter is active —
      the filter reaches the list only.
- [x] 8.5 Give each vertex a tooltip naming the sūra with its āya count and distinct count.

## 9. Cross-tab presentation check

- [x] 9.1 Confirm every **axed** chart on both tabs reads left-to-right on an ascending X
      axis inside the `dir="rtl"` page, and that no new axed chart is built from flow layout
      that would inherit RTL and grow right-to-left. The pie has no axis and is out of this
      rule's scope.
- [x] 9.2 Confirm no category is identified by shade alone: every pie category is also named
      in digits on its legend row, in its tooltip and in the status line, and no text is
      tinted with a series colour.
- [x] 9.3 Confirm every numeric node carries the `western-digits` class (and tabular figures
      where it sits in a column), including inside the SVGs — `114`, `3.9`, `18`, `15.8%`.
- [x] 9.4 Confirm no section heading is followed by a descriptive paragraph; the only prose
      is the page subtitle, tab 1's collapsed methodology, and the list's status line.
- [x] 9.5 Confirm the new code contains **no `dark:` variant, no `data-theme` switching and
      no theme toggle**, and that all accent and series colour is `brand` / `brand-dark` or
      a step of the green ordinal ramp.
- [x] 9.6 Confirm every interface string on both tabs is Arabic — tab labels, tile captions,
      chart headings, legend rows, tooltips, status line, empty and error states.

## 10. Verification

- [x] 10.1 Run `cd frontend && npx tsc --noEmit` (or `next build`) and confirm the new types
      and components compile clean.
- [x] 10.2 Start the app and exercise `/fassila`: both tabs, a few sūras in tab 1, then in
      tab 2 — select a category from a slice, from a legend row, clear it by re-activating,
      hover a slice and its legend row to compare tooltips, and read the status line's
      fawāṣil for several categories.
- [ ] 10.3 Check a narrow viewport: the pie and legend reflow, the lines scroll inside their
      card, and the page body never scrolls horizontally.
      **Not confirmed visually** — the browser resize reported success but the rendered
      viewport never changed, so this was not observed at a narrow width. The mechanisms are
      in place and were added deliberately: pie/legend stack via `flex-col md:flex-row`, both
      lines keep `FassilaLine`'s `overflow-x-auto` + `min-w-[560px]`, and the sūra table was
      given its own `overflow-x-auto` with a `min-w` so four columns scroll inside the card
      rather than pushing the page body sideways. Re-check by hand on a phone-width window.
- [x] 10.4 Confirm `GET /fassila/overview` answers 200 in the running app (not 422), carries
      `fawasil` on every summary, and that `GET /fassila/12` is byte-identical to its
      pre-change response.
- [x] 10.5 Run `python -m pytest -q` and confirm the whole local suite passes.
