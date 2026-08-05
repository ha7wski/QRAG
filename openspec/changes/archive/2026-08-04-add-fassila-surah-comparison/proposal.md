## Why

The Fāṣila page answers one question well — *how does **this** sūra rhyme?* — but it cannot
answer the question that follows immediately: *how does this sūra rhyme **compared to the
others**?* Reading the corpus through its rhyme is only half done while the 114 sūras can be
inspected one at a time but never held side by side: today, seeing that Hūd carries 12
distinct fawāṣil while 18 sūras carry exactly one requires stepping through 114 selections
and remembering the numbers.

The derivation needed for that comparison already exists and is already correct
(`analysis/fassila.py`, frozen against a 6236-āya reference fixture). What is missing is an
aggregate reading of it and a place to put that reading.

## What Changes

- The `/fassila` page gains a **two-tab shell**. The existing page — sūra selector, summary
  tiles, distribution bars, the `تتابع الفواصل` sequence line, methodology — moves under
  tab 1 (`تحليل الفواصل`) **unchanged**: same components, same layout, same behavior.
- A second tab (`مقارنة السور`) introduces a **cross-sūra reading**: the 114 sūras
  categorized by their number of distinct fawāṣil, with four summary tiles (sūra total,
  mean distinct-fāṣila count, mono-fāṣila sūra count, maximum), then — **in this order** —
  a pie chart, the sūra list, and two diversity lines.
  - a **pie chart** of the distribution of sūras per distinct-fāṣila count (12 buckets,
    1 → 12), its slices shaded by an **ordinal single-hue brand-green ramp** — light = few
    fawāṣil, dark = many, because the bucket value is ordinal — beside a **clickable
    legend** carrying, per row, the distinct-fāṣila count, the number of sūras and the
    percentage. Clicking a slice **or** a legend row filters the sūra list; clicking the
    active one clears the filter. Hovering either surface shows the **list of that
    category's sūras**, one per line, each prefixed with `-`;
  - the **sūra list**, placed immediately after the pie, whose filter status line names the
    category and then displays the **fawāṣil present in the selection** — enlarged, in
    parentheses, ordered by decreasing occurrence;
  - a **continuous line** `طول × تنوّع` (X = āya count, Y = distinct fawāṣil);
  - a **continuous line** `ترتيب × تنوّع` (X = sūra rank 1 → 114, Y = distinct fawāṣil).
- A new read-only **`GET /fassila/overview`** endpoint returns the per-sūra summaries and
  the corpus-level aggregates for all 114 sūras in one response. It is a pure fan-out over
  the existing `analyse_surah()` — **no fāṣila derivation logic is added, moved or
  modified**. The front-end only formats what it receives. Each summary carries, besides
  the distinct count and the dominant fāṣila, the **list of that sūra's distinct fawāṣil**
  (`fawasil`) — the field the selection reading needs, and the only new data this change
  adds: 4 KB on a 21 KB payload.
- Cross-tab presentation rules are made explicit as requirements rather than left implicit:
  100 % Arabic RTL, Western digits (0–9), every **axed** chart reading left-to-right on an
  ascending X axis — the pie has no axis and falls outside that rule — continuous polylines
  with no scatter-only rendering, no descriptive paragraph under section headings (only the
  page subtitle), and the app's `brand` green.

### Non-goals

- **No dark mode.** The prototype's `data-theme` toggle is deliberately not ported: the
  application is light-only by construction (`color-scheme: light`, a hardcoded `bg-white`
  sidebar, zero `dark:` variants in `frontend/src`), so a page-scoped dark mode would render
  a dark panel inside a permanently light shell. This confirms the existing
  `fassila-analysis` requirement rather than overturning it; app-wide dark mode remains a
  separate change.
- **No change to the fāṣila derivation**, to `GET /fassila/{surah}`, or to its response
  shape. The reference fixture and its regression tests stay valid untouched.

## Capabilities

### New Capabilities

- `fassila-surah-comparison`: the cross-sūra reading of the fāṣila — the aggregate
  `GET /fassila/overview` endpoint (per-sūra summaries including each sūra's distinct
  fawāṣil, distribution buckets, corpus aggregates) and the comparison tab that renders it
  (tiles, the pie chart with its clickable legend and sūra-listing tooltip, the filterable
  sūra list with its selection reading, the two diversity lines).

### Modified Capabilities

- `fassila-analysis`: the page acquires a tabbed shell — the existing single-sūra view
  becomes the first tab and must keep its state across tab switches; and the presentation
  requirement is extended with the cross-tab rules (chart reading direction, continuous
  lines, no section descriptions) that now govern two tabs instead of one.

## Impact

- **Backend** — `analysis/fassila.py`: one new pure aggregation function over the existing
  `analyse_surah()`, reading each sūra's `fawasil` from the `counts` it already returns.
  `api/models/fassila.py`: new response models. `api/routers/fassila.py`: one new route,
  which **must be declared before `/fassila/{surah}`** or FastAPI matches `overview`
  against the `int` path parameter and returns 422.
- **Frontend** — `frontend/src/app/fassila/page.tsx` becomes a tab shell; the current body
  moves into a tab component. New components: the comparison tab, the pie chart with its
  clickable legend, and one reusable diversity-line chart rendered twice.
  `frontend/src/lib/fassilaTypes.ts` and `frontend/src/lib/api.ts` gain the overview types
  and client call.
- **Unchanged** — the derivation, the per-sūra endpoint, `tests/fixtures/fassila_reference.json`,
  `FassilaBars.tsx`, `FassilaLine.tsx`, the navigation entry, and every other page.
- **Tests** (local-only) — new backend cases for the aggregation and for route ordering,
  asserting the corpus-wide figures the page reports.
