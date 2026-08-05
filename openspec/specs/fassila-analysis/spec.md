# fassila-analysis Specification

## Purpose
TBD - created by archiving change add-fassila-analysis. Update Purpose after archive.
## Requirements
### Requirement: Pausal-form fāṣila derivation

The system SHALL derive, for every āya of the Qurʾān, the **fāṣila**: the final letter of
the āya's final word rendered in pausal form (صيغة الوقف). Derivation SHALL operate on the
**Uthmānī rasm** as carried by the QAC treebank (`data/raw/quran-morphology.txt`), whose
per-word surface forms concatenate back to the orthographic word, and SHALL be
deterministic, offline, and free of any ML model or LLM call.

The pausal reduction SHALL apply these rules to the final word, in order:

1. Discard trailing non-letter annotation characters — sajda marks (`۩` U+06E9), waqf
   marks (`ۚ` U+06DA and the U+06D6–U+06DC range), and any other non-letter symbol.
2. Remove all tashkīl (combining marks U+064B–U+0652, U+0653–U+0655, U+0656–U+065F,
   U+0610–U+061A) and the tatweel `ـ` (U+0640).
3. Neutralize tanwīn: a word ending in `ً` / `ٌ` / `ٍ` loses that mark; where fatḥatān sits
   on a written alif (e.g. `عِلْمًا`), the alif SHALL remain and the fāṣila is `ا`.
4. Fold `ة` → `ه` (tāʾ marbūṭa is pronounced `h` in pause).
5. Fold `ى` (alif maqṣūra U+0649) → `ا`, and fold the dagger alif `ٰ` (U+0670) → `ا` when
   it is the final letter-bearing character.

The fāṣila is then the last remaining character.

#### Scenario: Ordinary vocalized ending

- **WHEN** the final word is `ٱلرَّحِيمِ` (1:3)
- **THEN** the fāṣila is `م`

#### Scenario: Tanwīn on a written alif

- **WHEN** the final word ends in fatḥatān over an alif, e.g. `عِلْمًا`
- **THEN** the tanwīn is dropped, the alif is retained, and the fāṣila is `ا`

#### Scenario: Tāʾ marbūṭa in pause

- **WHEN** the final word ends in `ة` (with or without tanwīn), e.g. `خَاشِعَةٌ`
- **THEN** the fāṣila is `ه`

#### Scenario: Alif maqṣūra and dagger alif fold to alif

- **WHEN** the final word ends in `ى` (e.g. `ٱلْهُدَىٰ`) or in a dagger alif `ٰ`
- **THEN** the fāṣila is `ا`

#### Scenario: Verse-final sajda mark is not the fāṣila

- **WHEN** the āya text ends with the sajda symbol `۩` (U+06E9), as in the 15 āyāt that
  carry it
- **THEN** the symbol is discarded and the fāṣila is taken from the last actual word

#### Scenario: Derivation covers the whole corpus

- **WHEN** the derivation is run over all 114 sūras
- **THEN** every one of the 6236 āyāt yields exactly one fāṣila character, and the
  25 distinct fāṣila letters observed across the analysed āyāt are
  `ن ا م ر د ه ب ل ق ت ظ ع ط ء ز س ج ص ك ف ذ ث ش ض ح`

---

### Requirement: Derivation uses the Uthmānī rasm, not the imlāʾī corpus

The fāṣila is a property of the **Uthmānī rasm**. `data/raw/quran_chakl.csv` stores the
**imlāʾī** (modern plene) orthography, which differs from the rasm precisely word-finally,
where the rhyme lives: it writes `فَاعْبُدْنِي` where the rasm has `فَٱعْبُدْنِى`. Deriving from
the plene text yields `ي` where the fāṣila is `ا`, corrupting 43 āyāt — most of Sūrat Ṭā-Hā,
whose whole rhyme is the final `ى`.

The system SHALL therefore derive words from the QAC treebank, reconstructing each
orthographic word by concatenating its morphological segments in order. `quran_chakl.csv`
MAY still be read for sūra names, which QAC does not carry.

Because the QAC word index *is* the `s:a:w` spine, word references are aligned by
construction, and the Basmala that `quran_chakl.csv` prepends to āya 1 of 113 sūras is
absent from the source and requires no stripping.

#### Scenario: Rasm-sensitive endings resolve correctly

- **WHEN** āya 20:14 is analysed, whose final word is `فَٱعْبُدْنِى` in the rasm
- **THEN** the fāṣila is `ا`, **not** the `ي` that the imlāʾī spelling would yield

#### Scenario: Word references need no realignment

- **WHEN** any āya's final word reference is produced
- **THEN** its word index is the QAC word index for that word, with no offset correction

#### Scenario: Āya 1 carries no Basmala

- **WHEN** āya 2:1 is processed
- **THEN** the source yields the single word `الٓمٓ` at reference `2:1:1`, with no prefix to
  strip

#### Scenario: Sūra names still resolve

- **WHEN** any sūra is analysed
- **THEN** its Arabic name is present in the result, sourced from the vocalized CSV

---

### Requirement: Muqaṭṭaʿāt āyāt are excluded from analysis

Āyāt composed **only** of disconnected letters (الحروف المقطّعة) carry no fāṣila in the
rhetorical sense and SHALL be excluded from every count, percentage and plotted point.

Detection SHALL use the QAC treebank (`data/raw/quran-morphology.txt`): an āya is
muqaṭṭaʿāt-only **iff every one of its words carries the `INL` tag**. This method is
self-maintaining and requires no hardcoded string list.

The result SHALL be exactly **20 āyāt across 19 sūras**: 2:1, 3:1, 7:1, 19:1, 20:1, 26:1,
28:1, 29:1, 30:1, 31:1, 32:1, 36:1, 40:1, 41:1, 42:1, 42:2, 43:1, 44:1, 45:1, 46:1. This
frozen list SHALL be asserted in a test as a regression guard.

Āyāt opening with الر, المر, طس, ص, ق or ن SHALL **not** be excluded: those āyāt continue
with ordinary words, so they carry a genuine fāṣila.

#### Scenario: A standalone muqaṭṭaʿāt āya is excluded

- **WHEN** āya 2:1 (`الٓمٓ`) is analysed
- **THEN** it is flagged as muqaṭṭaʿāt, contributes to no fāṣila count, and is absent from
  both charts

#### Scenario: A muqaṭṭaʿāt opening followed by words is kept

- **WHEN** āya 38:1 (`صٓ ۚ وَٱلْقُرْءَانِ ذِى ٱلذِّكْرِ`) is analysed
- **THEN** it is **not** excluded and its fāṣila is `ر`, from `ٱلذِّكْرِ`

#### Scenario: Sūra 42 excludes two consecutive āyāt

- **WHEN** Sūrat ash-Shūrā is analysed
- **THEN** both 42:1 (`حمٓ`) and 42:2 (`عٓسٓقٓ`) are excluded, and the sūra reports 2
  excluded āyāt

#### Scenario: Exclusion count is stable corpus-wide

- **WHEN** the whole corpus is analysed
- **THEN** exactly 20 āyāt are excluded, leaving 6216 analysed āyāt

---

### Requirement: Per-sūra aggregation

For a selected sūra the system SHALL compute, over its **analysed** āyāt only:

- the count of āyāt per distinct fāṣila;
- the percentage per distinct fāṣila, using the **analysed** āya count as denominator (not
  the sūra's total āya count);
- a **frequency ordering** — fawāṣil sorted by descending count, ties broken by a stable
  deterministic rule — used to order the bar chart and the methodology table;
- a **first-appearance ordering** — fawāṣil in the order their first analysed occurrence
  appears in the sūra — used for the line chart's Y axis;
- summary figures: total āya count, distinct-fāṣila count, the dominant fāṣila with its
  count and percentage, and the excluded-āya count.

#### Scenario: Percentages use the analysed denominator

- **WHEN** a sūra has 53 āyāt of which 1 is muqaṭṭaʿāt
- **THEN** percentages are computed over 52 analysed āyāt, and they sum to 100 %

#### Scenario: Frequency ordering is deterministic

- **WHEN** two fawāṣil occur the same number of times
- **THEN** their relative order is stable across repeated requests for the same sūra

#### Scenario: First-appearance ordering follows the sūra

- **WHEN** a sūra's first analysed āyāt end in `م`, then `ن`, then `م` again, then `ر`
- **THEN** the first-appearance order is `م`, `ن`, `ر`

#### Scenario: Summary reports exclusions

- **WHEN** Sūrat Maryam (19) is requested, whose āya 1 is muqaṭṭaʿāt
- **THEN** the response reports 98 total āyāt, 1 excluded and 97 analysed

---

### Requirement: Fāṣila API endpoint

The system SHALL expose a read-only `GET /fassila/{surah}` endpoint, where `surah` is
constrained to 1–114, returning the computation for that sūra. It SHALL require no
authentication, invoke no LLM, and mutate no state.

The response SHALL carry: sūra number, Arabic sūra name, total / analysed / excluded āya
counts, the per-fāṣila aggregate in frequency order (letter, count, percentage), the
first-appearance ordering, and a per-āya list. Each per-āya entry SHALL carry the āya
number, the fāṣila letter, the final word **as vocalized in the corpus**, that word's
`s:a:w` reference aligned with the existing QAC token spine, and a boolean muqaṭṭaʿāt flag.

Excluded āyāt SHALL be present in the per-āya list with the flag set — so the client can
account for them — but SHALL carry no fāṣila letter.

#### Scenario: Valid sūra returns a complete payload

- **WHEN** `GET /fassila/12` is requested
- **THEN** the response is 200 with 111 per-āya entries, 0 excluded, and aggregate
  percentages over 111 analysed āyāt

#### Scenario: Word reference aligns with the QAC spine

- **WHEN** any āya's entry is inspected
- **THEN** its `word_ref` is `"{surah}:{ayah}:{word}"` and resolves to the same final word
  in the existing QAC word index

#### Scenario: Out-of-range sūra is rejected

- **WHEN** `GET /fassila/0` or `GET /fassila/115` is requested
- **THEN** the response is a 422 validation error

#### Scenario: Excluded āyāt appear flagged and letterless

- **WHEN** `GET /fassila/42` is requested
- **THEN** entries for āyāt 1 and 2 carry the muqaṭṭaʿāt flag set and no fāṣila letter

---

### Requirement: Fāṣila distribution bar chart

The page SHALL render a bar chart of āya count per distinct fāṣila for the selected sūra,
in descending frequency order. Each row SHALL show the fāṣila letter, a bar whose length is
proportional to that letter's count relative to the most frequent letter, and a label giving
the absolute count and the percentage to one decimal place.

#### Scenario: Bars are scaled to the maximum

- **WHEN** the most frequent fāṣila occurs 40 times and another occurs 10 times
- **THEN** the second bar renders at 25 % of the first bar's length

#### Scenario: Row shows count and percentage

- **WHEN** a fāṣila closes 40 of 111 analysed āyāt
- **THEN** its row reads `40` āyāt and `36.0%`

#### Scenario: Hovering a row explains it

- **WHEN** the user hovers a bar row
- **THEN** a tooltip shows the letter, its count, the analysed total and the percentage

---

### Requirement: Fāṣila sequence line chart

The page SHALL render the sequence of fawāṣil across the sūra as a **single continuous
line** connecting one point per analysed āya, in āya order.

- The **Y axis** SHALL list the distinct fawāṣil in **order of first appearance, from
  bottom to top** — the first-appearing fāṣila occupies the bottom row. Each row SHALL be
  labelled with its letter and its occurrence count, the count **centred in the gap between
  the letter and the axis** so it reads as belonging to that row without crowding either.
- The **X axis** SHALL carry the āya number and SHALL **start at 0**, extending to the
  sūra's total āya count, with readable tick intervals chosen for the sūra's length.
- Each vertex SHALL be individually hoverable.

#### Scenario: Y axis is ordered by first appearance, bottom-up

- **WHEN** a sūra's fawāṣil first appear in the order `م`, `ن`, `ر`
- **THEN** `م` is the bottom row, `ن` the middle, `ر` the top — **not** alphabetical or
  frequency order

#### Scenario: Row counts never collide with their letter or the axis

- **WHEN** a row carries the widest count in the corpus (Sūrat al-Baqara's `ن`, 193)
- **THEN** the count sits clear of both the letter glyph and the Y axis, centred in the gap
  between them

#### Scenario: X axis starts at zero

- **WHEN** any sūra is rendered
- **THEN** the leftmost X tick is `0` and the axis extends to the sūra's total āya count

#### Scenario: The line is continuous across excluded āyāt

- **WHEN** a sūra's āya 1 is muqaṭṭaʿāt
- **THEN** no vertex is drawn for it and the line begins at the first analysed āya,
  remaining a single unbroken path

#### Scenario: Hovering a vertex identifies the āya

- **WHEN** the user hovers a vertex
- **THEN** a tooltip shows the āya number, the fāṣila letter and the vocalized final word

#### Scenario: Chart adapts to sūra length

- **WHEN** a long sūra (e.g. al-Baqara, 286 āyāt) is rendered
- **THEN** vertex radius and X tick spacing adapt so the plot stays legible, and the chart
  scrolls horizontally rather than forcing the page to scroll horizontally

---

### Requirement: Sūra selector

The page SHALL provide a selector covering all 114 sūras, each entry showing the sūra
number, its Arabic name and its āya count. Previous / next controls SHALL step through
sūras in order and SHALL be disabled at the two ends. Changing the selection SHALL update
the tiles, both charts and the methodology table.

#### Scenario: Selector lists every sūra

- **WHEN** the page loads
- **THEN** the selector holds 114 entries, each showing number, Arabic name and āya count

#### Scenario: Navigation steps between sūras

- **WHEN** the user presses "next" while sūra 12 is selected
- **THEN** sūra 13 is selected and the whole view re-renders

#### Scenario: Navigation is bounded

- **WHEN** sūra 1 is selected
- **THEN** the "previous" control is disabled; at sūra 114 the "next" control is disabled

---

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

### Requirement: Methodology disclosure

The page SHALL present a collapsed, expandable methodology section stating: the pausal-form
rules applied, the muqaṭṭaʿāt exclusion together with its exact scope (20 āyāt in 19 sūras)
and the reason الر / المر / طس / ص / ق / ن are not excluded, the corpus source, and a table
of every distinct fāṣila for the selected sūra with its count and percentage.

#### Scenario: Methodology is collapsed by default

- **WHEN** the page loads
- **THEN** the methodology section is present but collapsed, and expands on activation

#### Scenario: Exclusion scope is stated accurately

- **WHEN** the methodology section is expanded
- **THEN** it states that 20 āyāt across 19 sūras are excluded

#### Scenario: Table tracks the selected sūra

- **WHEN** the user selects a different sūra
- **THEN** the methodology table re-renders for that sūra in frequency order

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

