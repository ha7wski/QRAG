## ADDED Requirements

### Requirement: Tabbed page shell

The `/fassila` page SHALL present its content through **two tabs**:

1. `تحليل الفواصل` — the single-sūra analysis: sūra selector, summary tiles, the
   distribution bar chart, the `تتابع الفواصل عبر الآيات` sequence line, and the
   methodology disclosure. Its content, components, layout and behaviour SHALL be
   **unchanged** by the introduction of the shell.
2. `مقارنة السور` — the cross-sūra comparison defined by the `fassila-surah-comparison`
   capability.

The first tab SHALL be selected on load. The active tab SHALL be visually distinguished.
Both tab bodies SHALL remain **mounted** while hidden, so that the sūra selected in tab 1
and the filter applied in tab 2 both survive switching between them — matching the
three-tab idiom already used by the Verse Study page.

The page header — title and one-line subtitle — SHALL sit **above** the tab bar and remain
visible on both tabs.

#### Scenario: Two tabs, the analysis first

- **WHEN** the page loads
- **THEN** a tab bar offers exactly `تحليل الفواصل` and `مقارنة السور`, the first is
  active, and the single-sūra analysis is displayed

#### Scenario: Tab 1 is a relocation, not a rewrite

- **WHEN** the first tab is displayed
- **THEN** it renders the same sūra selector, tiles, bar chart, sequence line and
  methodology section as before, with no change to their appearance or behaviour

#### Scenario: State survives a tab switch

- **WHEN** the user selects sūra 19 in tab 1, switches to tab 2, then returns to tab 1
- **THEN** sūra 19 is still selected and its analysis is still rendered, with no refetch

#### Scenario: Filter survives a tab switch

- **WHEN** the user filters the comparison list in tab 2, switches to tab 1, then returns
- **THEN** the same filter is still applied

#### Scenario: The header spans both tabs

- **WHEN** either tab is active
- **THEN** the page title and its subtitle are visible above the tab bar

---

### Requirement: Comparison data is fetched lazily and once

The comparison tab's data SHALL be requested on the **first activation of that tab**, not
on page load, and SHALL be requested only once per page visit.

#### Scenario: No request until the tab is opened

- **WHEN** the page loads and the user stays on the first tab
- **THEN** no request to the overview endpoint is issued

#### Scenario: One request, reused

- **WHEN** the user opens the second tab, leaves it and returns to it
- **THEN** the overview endpoint was called exactly once and the rendered data is unchanged

---

## MODIFIED Requirements

### Requirement: Arabic RTL interface in the project's design language

The page SHALL be presented entirely in Arabic with `dir="rtl"`, consistent with the
existing Arabic-only study focus. All labels, headings, tab labels, tile captions, chart
annotations and tooltips SHALL be in Arabic. These rules govern **every tab** of the page.

**Numerals SHALL be Western Arabic (0–9), not Arabic-Indic (٠١٢).** Counts, percentages,
āya numbers, sūra numbers and axis ticks all read as `111`, `93`, `83.8%`. Because Quranic
faces such as Amiri carry a `locl` feature that substitutes Arabic-Indic forms for ASCII
digits in an Arabic context, numeric nodes SHALL disable it (`font-feature-settings:
"locl" 0`) so the Western forms survive the RTL surroundings. Numerals SHALL also use
tabular figures so counts align in columns.

**Every chart that has an X axis SHALL read left-to-right on that ascending axis**,
whatever the ambient RTL direction: the leftmost position is the smallest X value and the
axis grows rightward. Charts whose geometry is expressed in SVG coordinates satisfy this by
construction, since SVG `x` is measured from the left edge regardless of `dir`; charts
built from flow layout SHALL NOT be allowed to inherit RTL and grow right-to-left.

This rule is scoped to **axed** charts. A chart with no axis — the comparison tab's pie —
SHALL NOT be forced into it; its ordering is governed by its own requirement instead.

**Series that connect one point per item SHALL be rendered as a single continuous
polyline**, never as a scatter of unconnected points. Vertices MAY be drawn on top of the
line for hover targeting, but the line itself SHALL be unbroken across the plotted domain.

**Colour SHALL never be the only channel carrying a category's identity.** Where a chart
distinguishes categories by shade, the category SHALL also be named in words — in a legend,
a direct label or a tooltip — so a reader who cannot separate two adjacent shades can still
read the chart. Text SHALL wear the project's ink colours, never a series colour.

**Section headings SHALL NOT carry a descriptive paragraph beneath them.** The only
explanatory prose on the page is the one-line subtitle under the page title and the
collapsed methodology section; each chart and list is introduced by its heading alone.

The page SHALL adopt QURAG's established visual language rather than the prototype's
standalone palette: Tailwind utility classes (not bespoke CSS custom properties), the
`brand` green family (`#0e7c66`) for all accent and series colour, the existing card idiom
(`rounded-xl border border-gray-200 bg-white shadow-sm`), the existing page header idiom
(`text-2xl font-semibold text-gray-800` over `text-sm text-gray-500`), and Amiri for Arabic
text via the existing `.arabic-text` / `font-arabic` hooks. The prototype governs
**behavior and layout**; it does **not** govern colour or chrome.

Dark mode remains explicitly **out of scope**: the application is light-only by
construction (`color-scheme: light`, a hardcoded `bg-white` sidebar, and no `dark:` variant
anywhere in `frontend/src`). A page-scoped dark mode would render a dark panel against a
permanently light shell. Dark mode SHALL be addressed app-wide in a separate change, and
neither tab SHALL introduce it locally.

#### Scenario: Page renders right-to-left in Arabic

- **WHEN** either tab is displayed
- **THEN** the document direction is RTL and no interface string is in English or French

#### Scenario: Numbers display in Western digits

- **WHEN** any count, percentage, mean, āya number, sūra number or axis tick is rendered
- **THEN** it reads in 0–9 (e.g. `111`, `93`, `83.8%`, `3.9`), never in Arabic-Indic forms,
  in both the surrounding Arabic prose and inside the SVG charts

#### Scenario: Charts read left-to-right despite RTL

- **WHEN** any chart with an X axis is rendered inside the RTL page
- **THEN** its smallest X value sits at the left edge and the axis increases rightward

#### Scenario: An axis-less chart is out of the reading-direction rule

- **WHEN** the comparison tab's pie is rendered
- **THEN** it is not required to satisfy the left-to-right axis rule, having no axis, and
  its slice ordering is governed by its own requirement

#### Scenario: A category is never identified by shade alone

- **WHEN** a chart shades categories along a single-hue ramp
- **THEN** each category is also named in words in a legend, direct label or tooltip, and
  no text is tinted with the series colour

#### Scenario: Connected series are continuous, not scattered

- **WHEN** a chart plots one point per āya or per sūra across an axis
- **THEN** the points are joined by one unbroken polyline; a rendering of isolated dots
  with no connecting line fails this requirement

#### Scenario: No description under a section heading

- **WHEN** any chart or list section is rendered
- **THEN** its heading is followed directly by the chart or list, with no explanatory
  paragraph between them

#### Scenario: Page uses the project's card and header idiom

- **WHEN** the page renders its sections
- **THEN** each is a `rounded-xl border border-gray-200 bg-white shadow-sm` card, and the
  page header matches the idiom used by the existing QLisan and Verse Study pages

#### Scenario: Charts use the brand palette

- **WHEN** any of the page's charts renders
- **THEN** bars, lines and vertices are drawn in the `brand` green family, not the
  prototype's blue

#### Scenario: Arabic text uses the project typeface

- **WHEN** Arabic verse text, sūra names or fāṣila letters are displayed
- **THEN** they render in Amiri through the existing `.arabic-text` / `font-arabic` hooks

#### Scenario: The page introduces no dark-mode styling

- **WHEN** the implementation is inspected
- **THEN** it contains no `dark:` variants, no `data-theme` switching and no theme toggle,
  on either tab, matching the rest of the application
