/**
 * A summary tile, shared by both Fāṣila tabs so the two never drift apart.
 * Markup and classes are exactly those tab 1 used before the tab shell existed.
 */
export default function FassilaTile({
  label,
  value,
  arabicValue,
  hint,
}: {
  label: string;
  value: string;
  /** Render the value in the Quranic face (a fāṣila letter, not a number). */
  arabicValue?: boolean;
  /** Optional qualifier under the value — e.g. which sūra attains a maximum. */
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
      <p className="text-xs text-gray-500">{label}</p>
      <div className="mt-1">
        <span
          className={`text-2xl font-bold text-gray-900 ${
            arabicValue ? "font-arabic" : "western-digits tabular-nums"
          }`}
        >
          {value}
        </span>
        {hint && <span className="mr-2 font-arabic text-sm text-gray-500">{hint}</span>}
      </div>
    </div>
  );
}
