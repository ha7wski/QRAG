## ADDED Requirements

### Requirement: Diversity lines are magnifiable

Each of the two diversity lines SHALL offer **discrete magnification** at levels ×1, ×2, ×4
and ×8, through a control above the chart carrying decrease, the current level, increase and
reset. Controls SHALL be disabled at their bounds, carry Arabic accessible labels, and show
the level in Western digits. Each chart SHALL hold its **own** level, independent of the other.

Magnification SHALL stretch the plot **horizontally only**. It SHALL NOT change the X domain,
its linearity, the point ordering, or the chart's height. Every existing requirement on these
charts — one continuous polyline, X ascending left-to-right, deterministic tie-break, scroll
inside the card and never the page body — SHALL hold at every level.

**Label and mark sizes SHALL NOT change with magnification.** Axis labels, stroke widths and
vertex radii render at the same size at ×8 as at ×1; only the geometry spreads.

At ×1 the chart SHALL fill the width of its card, exactly as it did before magnification
existed.

#### Scenario: Four levels, bounded

- **WHEN** the control is displayed at ×1
- **THEN** decrease and reset are disabled, and increase steps through ×2, ×4, ×8, after
  which increase is disabled

#### Scenario: Magnification spreads the crowded region

- **WHEN** the length × diversity chart is set to ×8 and scrolled to the 55–85 āya range
- **THEN** the sūras in that range are drawn far enough apart to be hovered individually

#### Scenario: Type does not grow with the plot

- **WHEN** the chart is magnified from ×1 to ×8
- **THEN** the axis labels, the line thickness and the vertex radii are rendered at the same
  size as at ×1

#### Scenario: The domain is untouched

- **WHEN** any magnification is applied
- **THEN** the X axis still spans 0 to its maximum, still linear, and the polyline is still a
  single unbroken path over all 114 sūras

#### Scenario: The two charts magnify independently

- **WHEN** the length chart is set to ×4
- **THEN** the rank chart remains at its own level

#### Scenario: Reset restores the full view

- **WHEN** reset is activated at any level
- **THEN** the chart returns to ×1, fills its card, and no longer scrolls horizontally

#### Scenario: Magnifying keeps the centre

- **WHEN** the reader magnifies while looking at a region away from the origin
- **THEN** that region remains centred after the change rather than jumping to the origin

---

### Requirement: The Y axis stays readable while magnified

The Y axis and its labels SHALL remain visible at **every horizontal scroll offset**: the axis
SHALL follow the scroll, and the plot SHALL pass beneath it. Without this a magnified chart
shows gridlines with no labels — a shape that cannot be read as values.

The masking behind the pinned axis SHALL stop at the plot floor, so the X tick labels below
remain visible.

**X tick density SHALL scale with magnification**, so a magnified chart is not left with the
handful of ticks that suited its unmagnified width.

#### Scenario: The axis follows the scroll

- **WHEN** the chart is magnified and scrolled away from the origin
- **THEN** the Y axis and its labels are still at the left edge of the visible area, with the
  polyline passing behind them

#### Scenario: X labels survive the mask

- **WHEN** the pinned axis overlaps the plot
- **THEN** the X tick labels below the plot floor remain visible

#### Scenario: Ticks densify with magnification

- **WHEN** the chart is magnified
- **THEN** the number of X ticks increases with the level, keeping a usable reference across
  the widened axis

---

### Requirement: Y axis labels sit clear of the axis

Y-axis labels SHALL be separated from the axis line by a visible gap, so the numbers never
read as touching it.

#### Scenario: A visible gap

- **WHEN** the Y axis renders
- **THEN** each label ends well short of the axis line, rather than abutting it

---

### Requirement: Chart scrolling is direction-independent

The horizontal scroll container of a chart whose X axis reads left-to-right SHALL NOT inherit
the page's RTL direction. An RTL scroll container opens at the right edge and reports
scroll offsets with browser-dependent semantics — both wrong for an axis defined to start at
0 on the left.

#### Scenario: A magnified chart opens at the origin

- **WHEN** a chart is magnified enough to overflow its card
- **THEN** the visible region starts at X = 0, not at the maximum end of the axis
