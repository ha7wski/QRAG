## ADDED Requirements

### Requirement: Corpus-wide fāṣila summary

The system SHALL produce, for all **114** sūras, a summary of the fāṣila analysis already
computed per sūra. The summary SHALL be derived by calling the existing single-sūra
analysis; it SHALL NOT re-implement, duplicate or modify the fāṣila derivation, the pausal
reduction, or the muqaṭṭaʿāt exclusion.

Each sūra's entry SHALL carry: its number, its Arabic name, its total āya count, its
analysed āya count, its excluded āya count, its **number of distinct fawāṣil**, the
**list of those distinct fawāṣil** (`fawasil`), and its **dominant fāṣila** with that
letter's count and percentage.

The `fawasil` list SHALL be ordered by **descending occurrence with ties broken by first
appearance** — the same ordering the single-sūra analysis already applies to its per-fāṣila
counts — so the two endpoints cannot disagree about how a sūra's fawāṣil are ordered. Its
length SHALL equal the entry's distinct-fāṣila count, and its first element SHALL be the
dominant fāṣila. The list SHALL be read from the existing per-sūra computation, not derived
by a second pass over the corpus.

All figures SHALL inherit the existing exclusion rule: distinct counts, dominance and
percentages are computed over **analysed** āyāt, muqaṭṭaʿāt excluded from the denominator.

The computation SHALL be pure, offline and deterministic — no LLM, no network, no state —
and SHALL be memoized so that repeated requests do not re-derive the corpus.

#### Scenario: Every sūra is summarized

- **WHEN** the summary is computed
- **THEN** it holds exactly 114 entries, one per sūra, ordered by sūra number 1 → 114

#### Scenario: Entries agree with the single-sūra analysis

- **WHEN** any sūra's summary entry is compared to the result of analysing that sūra alone
- **THEN** its āya counts, distinct-fāṣila count and dominant fāṣila are identical

#### Scenario: A mono-fāṣila sūra

- **WHEN** sūra 112 (الإخلاص) is summarized
- **THEN** it reports 4 āyāt, 1 distinct fāṣila, and `د` as dominant at 100.0 %

#### Scenario: The most diverse sūra

- **WHEN** sūra 11 (هود) is summarized
- **THEN** it reports 123 āyāt, 12 distinct fawāṣil, and `ن` as dominant with 56
  occurrences at 45.5 %

#### Scenario: The fawāṣil list is ordered and complete

- **WHEN** sūra 11 (هود) is summarized
- **THEN** its `fawasil` list is `ن د ب ر م ط ظ ل ز ذ ق ص` — 12 letters, matching its
  distinct count, in descending-occurrence order, with the dominant `ن` first

#### Scenario: A mono-fāṣila sūra lists one letter

- **WHEN** sūra 112 (الإخلاص) is summarized
- **THEN** its `fawasil` list is exactly `["د"]`

#### Scenario: Exclusions carry through to the summary

- **WHEN** sūra 42 (الشورى) is summarized
- **THEN** it reports 53 total āyāt, 51 analysed, 2 excluded, and 8 distinct fawāṣil

---

### Requirement: Corpus aggregates and distribution buckets

The system SHALL compute, over the 114 per-sūra summaries:

- the **number of sūras** covered;
- the **mean number of distinct fawāṣil per sūra**, rounded to one decimal, matching the
  rounding convention already used for percentages;
- the **count of mono-fāṣila sūras** — those whose distinct-fāṣila count is exactly 1;
- the **maximum distinct-fāṣila count**, together with the sūra or sūras attaining it;
- the **distribution buckets**: for each distinct-fāṣila count, how many sūras have it.

Buckets SHALL span the observed minimum through the observed maximum **contiguously**,
emitting a zero-count bucket for any value with no sūra, so that the distribution can be
plotted as one distribution without the client reconstructing missing steps. Bucket counts
SHALL sum to 114.

#### Scenario: Aggregates over the corpus

- **WHEN** the aggregates are computed
- **THEN** they report 114 sūras, a mean of `3.9` distinct fawāṣil, 18 mono-fāṣila sūras,
  and a maximum of 12 attained by sūra 11 (هود)

#### Scenario: Buckets are contiguous and complete

- **WHEN** the distribution buckets are computed
- **THEN** they run from 1 to 12 with no missing step, and their counts sum to 114

#### Scenario: A bucket counts the sūras at that value

- **WHEN** the bucket for 3 distinct fawāṣil is inspected
- **THEN** it reports 30 sūras — the most populated bucket

#### Scenario: An unobserved value still yields a bucket

- **WHEN** some distinct-fāṣila value between the minimum and the maximum is attained by no
  sūra
- **THEN** a bucket for that value is present with a count of 0, rather than being omitted

---

### Requirement: Fāṣila overview API endpoint

The system SHALL expose a read-only `GET /fassila/overview` endpoint returning the per-sūra
summaries and the corpus aggregates in a **single response**. It SHALL require no
authentication, invoke no LLM, and mutate no state.

The route SHALL be declared **before** `GET /fassila/{surah}`. Because that route's path
parameter is typed as an integer, declaring it first makes a request for
`/fassila/overview` match it, fail integer coercion and return 422 without ever reaching
the overview handler.

The response SHALL carry the sūra summaries, the distribution buckets, and the aggregate
figures, so that the client performs formatting only and derives no statistic itself.

#### Scenario: Overview returns the whole corpus in one call

- **WHEN** `GET /fassila/overview` is requested
- **THEN** the response is 200 and holds 114 sūra summaries, the distribution buckets and
  the aggregate figures

#### Scenario: The literal route wins over the parameterized one

- **WHEN** `GET /fassila/overview` is requested while `GET /fassila/{surah}` is also
  registered
- **THEN** the overview handler answers with 200 — **not** a 422 validation error from the
  integer path parameter

#### Scenario: The per-sūra endpoint is unaffected

- **WHEN** `GET /fassila/12` is requested after the overview route is added
- **THEN** it returns exactly the payload it returned before, unchanged in shape and content

#### Scenario: The client derives no statistic

- **WHEN** the comparison tab renders any tile, bucket or chart value
- **THEN** that value is read from the response, not recomputed from the per-sūra rows

---

### Requirement: Comparison summary tiles

The comparison tab SHALL open with four summary tiles, each showing an Arabic caption and
its value in Western digits:

- the number of sūras covered;
- the mean number of distinct fawāṣil per sūra, to one decimal;
- the number of mono-fāṣila sūras;
- the maximum distinct-fāṣila count, identifying the sūra that attains it.

#### Scenario: Four tiles with the corpus figures

- **WHEN** the comparison tab is displayed
- **THEN** the tiles read `114`, `3.9`, `18` and `12`, each under an Arabic caption

#### Scenario: The maximum names its sūra

- **WHEN** the maximum tile is displayed
- **THEN** it identifies هود as the sūra attaining 12 distinct fawāṣil

---

### Requirement: Comparison tab section order

The comparison tab SHALL lay its sections out in this order: the **summary tiles**, the
**pie chart with its legend**, the **sūra list** with its status line, then the
**length × diversity** line and the **rank × diversity** line.

The list SHALL sit **immediately after the pie**, because the pie's only effect is to
filter that list: a control whose result is several sections below reads as inert. The two
diversity lines come last, being corpus-shape readings that the filter does not touch.

#### Scenario: The list follows the pie directly

- **WHEN** the comparison tab renders
- **THEN** the sūra list is the section immediately after the pie, before either diversity
  line

#### Scenario: Full section order

- **WHEN** the comparison tab renders
- **THEN** the sections read: tiles, pie, list, length × diversity, rank × diversity

---

### Requirement: Distinct-fāṣila distribution pie chart

The comparison tab SHALL render the distribution of sūras per distinct-fāṣila count as a
**pie chart**, one slice per bucket, slices ordered by **ascending bucket value**.

Beside it SHALL sit a **legend**, one row per bucket in the same order, each row carrying
the **distinct-fāṣila count**, the **number of sūras** in that bucket, and the
**percentage** of the 114. The legend is not optional: it is what names each category in
words, and it is the control's reliable hit target — three buckets hold a single sūra and
render as slices of roughly 3°, too thin to click or hover dependably.

#### Scenario: One slice per bucket, ascending

- **WHEN** the pie renders
- **THEN** it has 12 slices, one per bucket, ordered by ascending distinct-fāṣila count
  from 1 to 12

#### Scenario: Slice size follows the sūra count

- **WHEN** the slice for 3 distinct fawāṣil is rendered
- **THEN** it is the largest slice, spanning 30 of 114 sūras — 26.3 % of the circle

#### Scenario: Legend rows carry the numbers

- **WHEN** the legend renders
- **THEN** each row shows its distinct-fāṣila count, its sūra count and its percentage in
  Western digits — the row for 1 reading `1`, `18`, `15.8%`

---

### Requirement: Category selection from slice or legend

Slice and legend row SHALL be two surfaces of **one control**. Activating either SHALL set
that bucket as the active category and filter the sūra list to it; the active slice **and**
its legend row SHALL both be visually distinguished. Activating the already active slice or
its legend row SHALL clear the filter and restore the full list.

Slices SHALL carry a minimum hit area so that the single-sūra buckets remain selectable,
and legend rows SHALL be keyboard-reachable with an Arabic accessible label.

The filter SHALL apply to the sūra list **only**. The two diversity lines SHALL continue to
plot all 114 sūras regardless of the active category, since restricting them to one bucket
would collapse their Y axis to a single value and break their continuity.

#### Scenario: Clicking a slice filters the list

- **WHEN** the user clicks the slice for 1 distinct fāṣila
- **THEN** the sūra list shows exactly the 18 mono-fāṣila sūras, and both that slice and
  its legend row are marked active

#### Scenario: Clicking a legend row does the same

- **WHEN** the user clicks the legend row for 1 distinct fāṣila
- **THEN** the result is identical to clicking its slice

#### Scenario: Clicking the active category clears the filter

- **WHEN** the user activates the slice or the legend row that is already active
- **THEN** the filter is cleared and the list shows all 114 sūras again

#### Scenario: A single-sūra category is still selectable

- **WHEN** the user activates the category for 12 distinct fawāṣil, whose slice spans about
  3° of the circle
- **THEN** the selection succeeds and the list shows sūra 11 (هود)

#### Scenario: The lines ignore the filter

- **WHEN** a category filter is active
- **THEN** both diversity lines still plot all 114 sūras as unbroken polylines

---

### Requirement: Category tooltip lists that category's sūras

Hovering a slice **or** its legend row SHALL show a tooltip listing the **sūras of that
category**, one per line, each line prefixed with `-`. Both surfaces SHALL show the same
tooltip.

#### Scenario: Hovering a slice lists its sūras

- **WHEN** the user hovers the slice for 12 distinct fawāṣil
- **THEN** the tooltip holds one line, `- هود`

#### Scenario: Hovering a legend row shows the same tooltip

- **WHEN** the user hovers the legend row for 12 distinct fawāṣil
- **THEN** the tooltip is identical to the one its slice shows

#### Scenario: A populous category lists every sūra

- **WHEN** the user hovers the category for 1 distinct fāṣila
- **THEN** the tooltip lists all 18 mono-fāṣila sūras, one per line, each prefixed with `-`

---

### Requirement: Ordinal shading of the distribution

The number of distinct fawāṣil is an **ordinal** value — a position in a sequence, whose
reordering would destroy the meaning — so slices SHALL be shaded from a **single-hue
`brand` green ramp with monotone lightness**, light for few fawāṣil through dark for many.
A categorical (multi-hue) palette SHALL NOT be used.

The ramp SHALL satisfy the checks that apply to an ordinal ramp: **monotone lightness**
across the steps, and a **lightest step clearing 2:1 contrast against the card surface**.
`brand.light` (`#e6f4f0`) SHALL NOT be the light end — it sits at 1.13:1 on white and is
effectively invisible.

Because 12 steps cannot all be perceptually separated within a single-hue ramp — the usable
lightness span supports about 6 distinct steps, so adjacent steps at 12 fall well below the
separation floor — **shade SHALL carry direction only, never identity**. Every category
SHALL additionally be named in words on its legend row, in its tooltip and in the list's
status line, so no reading of the chart requires telling two adjacent shades apart.

#### Scenario: Shade increases with the bucket value

- **WHEN** the pie renders
- **THEN** the slice for 1 distinct fāṣila is the lightest and the slice for 12 is the
  darkest, with lightness decreasing monotonically in between

#### Scenario: The light end is visible on the card

- **WHEN** the lightest slice is rendered on the white card
- **THEN** it clears 2:1 contrast against that surface

#### Scenario: The ramp is one hue

- **WHEN** the slice fills are inspected
- **THEN** they are steps of a single green hue, not a multi-hue categorical palette

#### Scenario: Identity survives without colour

- **WHEN** two adjacent slices are indistinguishable in shade
- **THEN** their categories are still unambiguous from the legend row, the tooltip and the
  status line, which name them in digits

---

### Requirement: Length × diversity line

The comparison tab SHALL render a **single continuous line** relating sūra length to fāṣila
diversity: **X = the sūra's āya count**, **Y = its number of distinct fawāṣil**, one vertex
per sūra, X ascending left-to-right.

Sūras SHALL be ordered by āya count ascending, with the **sūra number as tie-break**. The
tie-break is required for determinism: 24 āya-count values are shared by more than one sūra
— two of them by five sūras each — so without a stable secondary key the polyline would
reorder between renders. Sūras sharing an āya count SHALL each keep their own vertex; they
SHALL NOT be collapsed into an averaged point.

The X axis SHALL be **linear** in āya count. Where the chart's natural width would make it
illegible, it SHALL scroll horizontally **within its card**, never forcing the page body to
scroll horizontally.

#### Scenario: One unbroken line across all sūras

- **WHEN** the chart renders
- **THEN** all 114 vertices are joined by a single continuous polyline, with no
  scatter-only rendering

#### Scenario: Length ascends to the right

- **WHEN** the chart renders
- **THEN** the leftmost vertex is the shortest sūra (3 āyāt) and the rightmost is
  al-Baqara (286 āyāt)

#### Scenario: Sūras of equal length are ordered deterministically

- **WHEN** the five sūras of 11 āyāt (62, 63, 93, 100, 101) are plotted
- **THEN** they appear in ascending sūra-number order, each with its own vertex, and the
  order is identical on every render

#### Scenario: Hovering a vertex identifies the sūra

- **WHEN** the user hovers a vertex
- **THEN** a tooltip names the sūra with its āya count and its distinct-fāṣila count

#### Scenario: A wide chart scrolls inside its card

- **WHEN** the chart is too wide for the viewport
- **THEN** the chart's own container scrolls horizontally and the page body does not

---

### Requirement: Rank × diversity line

The comparison tab SHALL render a **single continuous line** relating a sūra's position in
the muṣḥaf to its fāṣila diversity: **X = the sūra number, 1 → 114**, **Y = its number of
distinct fawāṣil**, one vertex per sūra, X ascending left-to-right in muṣḥaf order.

#### Scenario: Rank ascends to the right

- **WHEN** the chart renders
- **THEN** sūra 1 is the leftmost vertex and sūra 114 the rightmost, despite the
  surrounding RTL layout

#### Scenario: One unbroken line across the muṣḥaf

- **WHEN** the chart renders
- **THEN** the 114 vertices are joined by a single continuous polyline, with a visible peak
  at sūra 11 (12 distinct fawāṣil)

#### Scenario: Hovering a vertex identifies the sūra

- **WHEN** the user hovers a vertex
- **THEN** a tooltip names the sūra with its number and its distinct-fāṣila count

---

### Requirement: Filterable sūra list

The comparison tab SHALL render the list of sūras, in muṣḥaf order, each row showing the
sūra number, its Arabic name, its āya count, **its distinct fawāṣil as letters**, and its
**dominant fāṣila** with that letter's percentage.

The fawāṣil column SHALL carry the **letters themselves, not their count**. Under an
active category every row shares the same count, so the number would repeat down the
column while the letters are what actually distinguish the sūras. The letters SHALL appear
in the `fawasil` order — descending occurrence — so the dominant fāṣila reads first, and
SHALL render in the project's Arabic typeface.

The list SHALL respond to the category filter: with a category active it shows only the
sūras in that bucket. With no filter it shows all 114.

#### Scenario: Unfiltered list covers the corpus

- **WHEN** the comparison tab is displayed with no filter active
- **THEN** the list holds 114 rows in muṣḥaf order

#### Scenario: A row lists its fawāṣil as letters

- **WHEN** the row for sūra 11 (هود) is displayed
- **THEN** it reads 123 āyāt, the letters `ن د ب ر م ط ظ ل ز ذ ق ص`, and `ن` as dominant
  at 45.5 % — **not** the number `12`

#### Scenario: A mono-fāṣila row shows its single letter

- **WHEN** the row for sūra 112 (الإخلاص) is displayed
- **THEN** its fawāṣil column reads `د`

#### Scenario: Filtering narrows the list

- **WHEN** the category for 1 distinct fāṣila is active
- **THEN** the list holds exactly the 18 mono-fāṣila sūras

#### Scenario: Letters render in the Quranic face

- **WHEN** any row's fawāṣil or dominant fāṣila are displayed
- **THEN** they render in Amiri via the project's Arabic typeface hooks, while the
  percentage and the āya count render in Western digits

---

### Requirement: Selection status line reads the fawāṣil of the selection

Below the list, a status line SHALL state the active category — how many sūras it holds and
their distinct-fāṣila count — and SHALL then display the **fawāṣil present in that
selection**, enlarged, **between parentheses**.

Those letters SHALL be the union of the selected sūras' `fawasil`, ordered by **descending
occurrence** — the number of sūras **in the selection** carrying that letter — with ties
broken by first appearance scanning the selection in muṣḥaf order, so the order is stable
across renders. Emitting them in that order inside the RTL container places the most
frequent letter at the **right** and the least frequent at the left; no reversal is applied.

The letters count **sūras, not āyāt**, and the presentation SHALL NOT imply otherwise.

#### Scenario: Status line names the category

- **WHEN** the category for 1 distinct fāṣila is active
- **THEN** the status line states that 18 sūras carry 1 distinct fāṣila

#### Scenario: The selection's fawāṣil follow, in parentheses

- **WHEN** the category for 1 distinct fāṣila is active
- **THEN** the status line then shows `( ا ر ه ن ل د س )` — the 7 distinct fawāṣil of those
  18 sūras — enlarged relative to the surrounding text

#### Scenario: Letters are ordered by decreasing occurrence

- **WHEN** the mono-fāṣila selection's letters are ordered
- **THEN** `ا` (8 sūras) comes first, then `ر` (4), then `ه` (2), then the single-sūra
  letters `ن`, `ل`, `د`, `س` — so in the RTL rendering `ا` sits rightmost

#### Scenario: A single-sūra category shows that sūra's fawāṣil

- **WHEN** the category for 12 distinct fawāṣil is active
- **THEN** the status line shows sūra 11's 12 letters, each occurring in one sūra

#### Scenario: Ordering is stable across renders

- **WHEN** the same category is selected twice
- **THEN** the letters appear in the identical order both times
