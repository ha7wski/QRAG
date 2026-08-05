> **Retroactive change.** The work below was implemented and verified in the browser before
> this change was written; the tasks record what was done so the spec matches the code. All
> edits are confined to `frontend/src/components/FassilaDiversityLine.tsx`.

## 1. Axis legibility

- [x] 1.1 Widen the left margin from 34 to 54 units and move the Y label from `mL − 8` to
      `mL − 18`, so the numbers no longer read as touching the axis.

## 2. Magnification

- [x] 2.1 Add discrete zoom state with levels ×1, ×2, ×4, ×8, held per chart instance.
- [x] 2.2 Derive the viewBox width as `620 × zoom` and render the SVG at
      `width: ${zoom * 100}%` — the two scaling together are what keeps one viewBox unit at a
      constant pixel size, so labels and marks do not grow with the plot. Use a **percentage**,
      not a pixel width, or ×1 stops filling the card.
- [x] 2.3 Scale `min-width` by the zoom level too, preserving the narrow-screen floor.
- [x] 2.4 Render the control row above the chart — decrease, `×N`, increase, reset — disabled
      at the bounds, with Arabic `aria-label`s and the level in Western digits.
- [x] 2.5 Preserve the visible centre across a level change: capture it as a fraction of the
      scroll width before, restore it after the re-render.
- [x] 2.6 Scale X tick density with the level (target `6 × zoom` ticks) and enlarge the vertex
      radius modestly at higher levels.

## 3. Pinned Y axis

- [x] 3.1 Track the scroll offset in viewBox units via an `onScroll` handler on the scroll
      container, and sync it after a programmatic scroll as well.
- [x] 3.2 Move the Y labels and the axis line out of the gridline loop into one group
      translated by that offset, **drawn last** so the plot passes beneath it.
- [x] 3.3 Back that group with a white rect whose height stops at the plot floor, so the X
      tick labels below stay visible.
- [x] 3.4 Pin the scroll container to `dir="ltr"` so a magnified chart opens at X = 0 and the
      offset arithmetic is browser-independent.

## 4. Verification

- [x] 4.1 `npx tsc --noEmit` clean.
- [x] 4.2 In the browser: ×1 fills the card with no scrollbar; ×2/×4/×8 scroll; label and mark
      sizes identical across levels; ticks densify; the centre is preserved across changes.
- [x] 4.3 In the browser: at ×8 scrolled to the 55–85 āya range, points are individually
      separated and the pinned Y axis stays labelled at the left edge.
- [x] 4.4 In the browser: reset returns to ×1 at full card width with the scrollbar gone, and
      the two charts magnify independently.
- [x] 4.5 Confirm no backend, endpoint, model or test-fixture change was required.
