"use client";

import { useState } from "react";
import type { FassilaCount } from "@/lib/fassilaTypes";
import { fmtPercent } from "@/lib/numerals";
import { iso, NOUNS } from "@/lib/strings";
import Counted from "./Counted";

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
          // A `title` is text, so the fix there has to be a character:
          // `iso()` wraps the number and its sign in an isolate, which is
          // what a `dir` attribute would do if an attribute could hold one.
          title={`${c.letter} · ${c.count} من ${analysed} (${iso(
            `${fmtPercent(c.percentage)}%`,
          )})`}
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
          <span className="western-digits text-end text-sm tabular-nums text-gray-500">
            {/* «2 آية» and «1 آية» were rendering here before this — the
                count was interpolated in front of a fixed noun (العدد
                والمعدود). Measured on /fassila, 2026-09-08. */}
            <Counted
              n={c.count}
              forms={NOUNS.aya}
              className="text-base text-gray-900"
            />{" "}
            ·{" "}
            {/* «آية» before the number makes bidi rule W2 reclassify it as an
                ARABIC number, and W5 then cannot attach the `%` to it; the
                orphaned terminator resolves right-to-left and lands on the
                wrong side. Visible in production today as «%83.8» (design
                D15). One `dir` is enough — it re-establishes an LTR run in
                which the sign attaches normally. */}
            <span dir="ltr">{fmtPercent(c.percentage)}%</span>
          </span>
        </div>
      ))}
    </div>
  );
}
