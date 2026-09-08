/**
 * Where a cursor-anchored chart tooltip should sit.
 *
 * Both Fāṣila charts used to clamp their tooltip with `Math.min(x + 14, 1200)`.
 * 1200 is neither the viewport nor the content area on any particular screen, and
 * after the navigation moved to the inline-start edge it is the wrong bound in a
 * new way: the sidebar is `fixed` and 16rem wide from `md` up (`md:ms-64` in the
 * layout), so the content area now ends 256px before the viewport does — and the
 * tooltips carry `z-20` against the navigation's `z-50`. A `whitespace-nowrap`
 * tooltip opened near a card's trailing edge slid underneath it.
 *
 * Past the middle of the content area the tooltip is anchored by its own far edge
 * instead. `translateX(-100%)` puts its right edge at `left`, which needs no width
 * measurement — the reason for anchoring this way rather than subtracting a
 * guessed tooltip width from the bound.
 */
export function tooltipAnchor(x: number): {
  left: number;
  transform?: string;
} {
  if (typeof window === "undefined") return { left: x + 14 };
  // Mirrors the layout's own breakpoint and offset; keep the two in step.
  const navWidth = window.innerWidth >= 768 ? 256 : 0;
  const contentWidth = window.innerWidth - navWidth;
  return x > contentWidth / 2
    ? { left: x - 14, transform: "translateX(-100%)" }
    : { left: x + 14 };
}
