/**
 * Numeral rendering. The interface uses ONE numeral system — Western digits
 * (0-9) — on every surface, reading pages included; see the numeral policy in
 * `app/globals.css` (`.western-digits`) for how the typefaces are kept from
 * substituting Arabic-Indic forms. A `toArabicDigits()` used to live here for
 * the reading surfaces; it is gone rather than left unused, so re-introducing
 * a second numeral system is a deliberate act, not an import away.
 */

/**
 * Render a percentage to one decimal (e.g. 83.8 → "83.8").
 * `String(n)` won't do: `String(36.0)` is "36", dropping the decimal place.
 */
export function fmtPercent(n: number): string {
  return n.toFixed(1);
}
