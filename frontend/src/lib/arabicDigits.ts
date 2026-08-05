const AR_DIGITS = "٠١٢٣٤٥٦٧٨٩";

/** Render a number with Arabic-Indic digits (e.g. 313 → ٣١٣). */
export function toArabicDigits(n: number): string {
  return String(n).replace(/\d/g, (d) => AR_DIGITS[Number(d)]);
}

/**
 * Render a percentage to one decimal in Western digits (e.g. 83.8 → "83.8").
 * `String(n)` won't do: `String(36.0)` is "36", dropping the decimal place.
 */
export function fmtPercent(n: number): string {
  return n.toFixed(1);
}
