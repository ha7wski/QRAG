"use client";

import { useState } from "react";
import type { FassilaCount } from "@/lib/fassilaTypes";
import { fmtPercent } from "@/lib/arabicDigits";

/**
 * Āya count per distinct fāṣila, in descending frequency. Bars are scaled against
 * the most frequent letter (not against the āya total), so the shape of the
 * distribution stays readable even when one letter dominates — which, for most
 * sūras, it does.
 *
 * Percentages come from the backend and are already computed over *analysed*
 * āyāt, muqaṭṭaʿāt excluded from the denominator.
 */
export default function FassilaBars({
  counts,
  analysed,
}: {
  counts: FassilaCount[];
  analysed: number;
}) {
  const [hovered, setHovered] = useState<string | null>(null);
  const max = counts.length ? Math.max(...counts.map((c) => c.count)) : 1;

  return (
    <div>
      {counts.map((c) => (
        <div
          key={c.letter}
          onMouseEnter={() => setHovered(c.letter)}
          onMouseLeave={() => setHovered(null)}
          title={`${c.letter} · ${c.count} من ${analysed} (${fmtPercent(
            c.percentage,
          )}%)`}
          className="grid grid-cols-[2.5rem_1fr_7.5rem] items-center gap-3 border-b border-gray-100 py-2 last:border-b-0"
        >
          <span className="font-arabic text-2xl font-bold leading-none text-gray-900">
            {c.letter}
          </span>
          <div className="h-5">
            <div
              className={`h-5 rounded transition-all duration-500 ${
                hovered === c.letter ? "bg-brand-dark" : "bg-brand"
              }`}
              style={{ width: `${(c.count / max) * 100}%` }}
            />
          </div>
          <span className="western-digits text-left text-sm tabular-nums text-gray-500">
            <b className="text-base text-gray-900">{c.count}</b> آية ·{" "}
            {fmtPercent(c.percentage)}%
          </span>
        </div>
      ))}
    </div>
  );
}
