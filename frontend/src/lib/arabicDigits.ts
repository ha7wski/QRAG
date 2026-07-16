const AR_DIGITS = "٠١٢٣٤٥٦٧٨٩";

/** Render a number with Arabic-Indic digits (e.g. 313 → ٣١٣). */
export function toArabicDigits(n: number): string {
  return String(n).replace(/\d/g, (d) => AR_DIGITS[Number(d)]);
}
