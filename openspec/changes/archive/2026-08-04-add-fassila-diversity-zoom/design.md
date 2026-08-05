## Context

`FassilaDiversityLine` renders one SVG with a `viewBox` of `620 × H`, sized `w-full
min-w-[560px]` inside an `overflow-x-auto` card. It is used twice — X = āya count, X = sūra
rank. The crowding it needed to solve is measured: **78 of 114 sūras have ≤ 60 āyāt**, so on
a linear 0 → 286 axis two-thirds of the data occupies the left fifth.

The chart is inside a `dir="rtl"` page, and its X axis is required to read left-to-right.

## Goals / Non-Goals

**Goals:**

- Let the reader spread the condensed region far enough apart to inspect individual sūras.
- Keep the X domain and its linearity untouched — magnify the drawing, not the scale.
- Keep every existing requirement true at every magnification.
- Change one component; leave both call sites and all props alone.

**Non-Goals:**

- Continuous zoom, pinch, wheel or drag-to-select.
- Any change to the pie, tab 1, or the backend.

## Decisions

### 1. Scale the `viewBox` width and the rendered width by the same factor

This is the decision the whole feature turns on. An `<svg>` with a `viewBox` preserves its
aspect ratio: doubling the rendered width doubles the rendered height **and the type size**
with it. Magnifying that way would give a chart whose axis labels grow to absurd sizes at ×8.

Instead, `viewBox` width and rendered width move together — `viewBox="0 0 ${620 * zoom} ${H}"`
against `width: ${zoom * 100}%`. One viewBox unit then maps to the same number of pixels at
every level, so **labels, stroke widths and vertex radii keep their exact size** while the
plot geometry stretches and the height stays put.

The width is a **percentage, not a pixel count**: at ×1 that reproduces `w-full` exactly, so
the chart still fills its card on a wide screen and still honours `min-width` on a narrow
one. A pixel width would have pinned the chart to 620 px and left the card half empty.

*Alternatives considered:* a CSS `transform: scaleX()` — rejected, it scales stroke widths
and skews the type horizontally. Re-deriving the X domain to a sub-range (true viewport
zoom) — rejected as a larger feature; it would need pan controls, a domain indicator, and
would put the "linear over the full range" requirement at risk.

### 2. Discrete levels ×1 ×2 ×4 ×8, per chart

Powers of two, four steps. ×8 puts about 5 000 px behind a 114-point series, which is where
the densest cluster becomes individually clickable; beyond that the scroll distance costs
more than the detail is worth. Discrete levels also make the control trivially operable by
keyboard and touch, where a wheel or pinch gesture is not.

Each chart owns its level: the two charts answer different questions and are crowded
differently — the rank chart is evenly spread and rarely needs magnifying at all.

### 3. The Y axis is pinned to the scroll offset

Once magnified, the plot scrolls, and the Y axis — drawn at the left of the SVG — leaves the
viewport. The gridlines remain but carry no labels: the reader can see the shape and not
read a value.

The axis group is therefore translated by the current scroll offset, converted from pixels to
viewBox units (`scrollLeft * W / scrollWidth`), and **drawn last** so the plot passes beneath
it, over a white backing rect. The rect stops at the plot floor rather than spanning the full
height, so the X tick labels underneath stay visible.

*Alternative considered:* splitting the axis into a separate fixed-width SVG gutter beside the
scrolling one. Rejected — the two SVGs would resolve their units-per-pixel differently, so
the gutter's type would not match the plot's.

### 4. The scroll container is `dir="ltr"`

The page is RTL, but an RTL scroll container opens the view at the **right** edge and gives
`scrollLeft` semantics that differ between browser versions — both wrong for an axis defined
to start at 0 on the left. Pinning the wrapper to `ltr` makes the initial view the origin and
the offset arithmetic conventional. Nothing inside is direction-sensitive: the SVG carries
digits and marks, and its own left-to-right reading is a requirement, not an inheritance.

### 5. Tick density follows magnification

The tick chooser targets `6 * zoom` ticks instead of a fixed 6. At ×8 a fixed count would
leave six labels spread across thousands of pixels — a magnified chart with no usable
reference.

### 6. Magnifying preserves the centre

Before changing level, the visible centre is captured as a fraction of the scroll width and
restored after the re-render. Without it, magnifying would jump the reader to the origin and
lose the region they were looking at — the region that motivated magnifying.

## Risks / Trade-offs

- **A future edit sets the rendered width in pixels** (it reads more natural than `%`) and
  the chart stops filling its card at ×1 → decision 1 states why it is a percentage; this was
  caught in review once already.
- **Someone "simplifies" the pinned axis back into the normal draw order** and it disappears
  on scroll again → the axis group's comment says it must stay last.
- **Vertices under the pinned gutter are not hoverable** while scrolled → accepted; that
  strip is axis furniture, and scrolling a little reveals the points.
- **×8 is a long scroll** (~5 000 px) for a reader who wanted a small nudge → the ×2 and ×4
  steps exist for exactly that, and reset is one click.

## Migration Plan

One component, additive, no props changed and no call site touched. Rollback is reverting the
file; both charts return to their previous fixed-width rendering.

## Open Questions

None.
