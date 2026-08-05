## Why

The comparison tab's two diversity lines are honest but crowded. `طول × تنوّع` plots 114
sūras on a linear āya-count axis where **78 of them sit below 60 āyāt** — roughly
two-thirds of the corpus compressed into the left fifth of the plot. The condensation was
accepted deliberately when the chart was designed (a log axis would stop "X = number of
āyas" reading as a length), but it left no way to *inspect* that region: the vertices
overlap and the polyline reads as a scribble.

Two small legibility faults came with it. The Y-axis numbers sat 8 units from the axis and
read as touching it. And once a chart is wide enough to scroll, the Y axis itself slides out
of view, leaving the gridlines unlabelled.

This change is **retroactive**: the behaviour below is already implemented and verified in
the browser. The change exists so the shipped behaviour is in the contract rather than only
in the component.

## What Changes

- The two diversity lines gain **discrete magnification** — ×1, ×2, ×4, ×8 — through a small
  control above each chart (decrease, current level, increase, reset), each chart holding its
  own level. Magnification stretches the plot **horizontally only**: the X domain is
  unchanged, the axis stays linear, and only the drawing width grows, so the chart scrolls
  inside its card exactly as it already did at its natural width.
- **Type and mark sizes stay constant across levels.** Axis labels, stroke widths and vertex
  radii render at the same size at ×8 as at ×1.
- **The Y axis is pinned**: it follows the horizontal scroll so its labels remain readable at
  every offset, with the plot passing beneath it.
- **X tick density scales with magnification**, so a magnified chart is not left with six
  ticks spread over thousands of pixels.
- Changing magnification **keeps whatever was centred, centred**.
- Y-axis labels are moved clear of the axis (the left margin widens from 34 to 54 units, the
  label sitting 18 units from the axis instead of 8).

### Non-goals

- No change to either chart's data, ordering, domain or scale — magnification is presentation
  only, and the X axis stays linear as decided when the charts were specified.
- No continuous or gesture zoom (pinch, wheel, drag-to-select); discrete levels only.
- No change to tab 1's sequence line, to the pie, or to any endpoint.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `fassila-surah-comparison`: the two diversity lines acquire magnification and a pinned,
  clear-of-the-axis Y axis. Their existing requirements — one continuous polyline, ascending
  X read left-to-right, deterministic ordering, scroll inside the card — are unchanged and
  continue to hold at every magnification.

## Impact

- **Frontend only** — `frontend/src/components/FassilaDiversityLine.tsx`. Both call sites in
  `FassilaComparisonTab.tsx` are untouched: the component's props are unchanged.
- **Nothing else** — no backend, no endpoint, no model, no data, no test fixture. The
  backend suite is unaffected.
