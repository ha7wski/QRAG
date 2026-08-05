"use client";

import { useState } from "react";
import type { FassilaAyah, FassilaCount } from "@/lib/fassilaTypes";

/**
 * The sequence of fawāṣil across a sūra, as one continuous line.
 *
 * Two mappings carry the whole point of this chart and are ported verbatim from
 * the validated prototype — both are easy to "fix" into something wrong:
 *
 *   rowY: the Y axis lists fawāṣil by **order of first appearance, bottom to top**
 *         — not alphabetically, not by frequency. Reading the line then shows the
 *         sūra introducing each new rhyme and returning to earlier ones.
 *   ayaX: the X domain starts at **0**, not at the first data point, so the left
 *         margin is the sūra's opening rather than its first analysed āya.
 *
 * Muqaṭṭaʿāt āyāt contribute no vertex; the polyline simply spans them, staying a
 * single unbroken path.
 */

/** Pick a round tick interval targeting ~6 ticks across the axis. */
function niceStep(n: number): number {
  const nice = [1, 2, 5, 10, 20, 25, 50, 100, 200];
  const raw = Math.max(1, n / 6);
  return nice.reduce((a, b) => (Math.abs(b - raw) < Math.abs(a - raw) ? b : a));
}

function xticks(n: number): number[] {
  const step = niceStep(n);
  const out = [0];
  for (let t = step; t < n - step * 0.4; t += step) out.push(t);
  out.push(n);
  return out;
}

export default function FassilaLine({
  ayahs,
  order,
  counts,
  totalAyahs,
}: {
  ayahs: FassilaAyah[];
  /** Distinct fawāṣil in order of first appearance. */
  order: string[];
  counts: FassilaCount[];
  totalAyahs: number;
}) {
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(
    null,
  );

  const analysed = ayahs.filter((a) => !a.is_muqattaat);
  const nRows = order.length;
  const N = totalAyahs;
  if (!nRows || !N) return null;

  const W = 620;
  const mT = 16;
  const mB = 40;
  const mR = 16;
  const mL = 64;
  const rowGap = 44;
  const plotH = Math.max(rowGap, nRows * rowGap);
  const plotW = W - mL - mR;
  const H = mT + plotH + mB;

  // Row-label geometry. The letter sits at the far left of the margin; its count
  // is centred in the gap between the letter and the Y axis, so it reads as
  // belonging to that row without crowding either the glyph or the axis.
  const letterX = mL - 46;
  const countX = mL - 18;

  // First appearance, bottom to top.
  const rowY = (letter: string) =>
    mT + ((nRows - order.indexOf(letter) - 0.5) / nRows) * plotH;
  // Domain anchored at 0.
  const ayaX = (ayah: number) => mL + (ayah / N) * plotW;

  const countOf = new Map(counts.map((c) => [c.letter, c.count]));
  const points = analysed
    .map((a) => `${ayaX(a.ayah).toFixed(1)},${rowY(a.fasila!).toFixed(1)}`)
    .join(" ");
  const r = N > 160 ? 1.6 : N > 90 ? 2.1 : 2.6;

  return (
    <div className="relative">
      {/* Long sūras scroll the chart, never the page body. */}
      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="block h-auto w-full min-w-[560px]"
          role="img"
          aria-label="تتابع الفواصل عبر الآيات"
        >
          {xticks(N).map((a) => (
            <g key={`x-${a}`}>
              <line
                x1={ayaX(a)}
                y1={mT}
                x2={ayaX(a)}
                y2={mT + plotH}
                className="stroke-gray-200"
                strokeWidth={1}
              />
              <text
                x={ayaX(a)}
                y={mT + plotH + 18}
                textAnchor="middle"
                className="western-digits fill-gray-500 text-[11px]"
              >
                {a}
              </text>
            </g>
          ))}

          {order.map((letter) => (
            <g key={`row-${letter}`}>
              <line
                x1={mL}
                y1={rowY(letter)}
                x2={mL + plotW}
                y2={rowY(letter)}
                className="stroke-gray-200"
                strokeWidth={1}
                strokeDasharray="2 4"
              />
              <text
                x={letterX}
                y={rowY(letter) + 8}
                textAnchor="middle"
                fontSize={22}
                className="fill-gray-900 font-arabic font-bold"
              >
                {letter}
              </text>
              <text
                x={countX}
                y={rowY(letter) + 5}
                textAnchor="middle"
                className="western-digits fill-gray-400 text-[11px]"
              >
                {countOf.get(letter) ?? 0}
              </text>
            </g>
          ))}

          <line
            x1={mL}
            y1={mT}
            x2={mL}
            y2={mT + plotH}
            className="stroke-gray-300"
            strokeWidth={1}
          />

          <polyline
            points={points}
            fill="none"
            className="stroke-brand"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {analysed.map((a) => (
            <circle
              key={a.ayah}
              cx={ayaX(a.ayah)}
              cy={rowY(a.fasila!)}
              r={r}
              className="fill-brand stroke-white hover:fill-brand-dark"
              strokeWidth={1}
              onMouseEnter={(e) =>
                setTip({
                  x: e.clientX,
                  y: e.clientY,
                  text: `آية ${a.ayah} · ${a.fasila} · ${a.word}`,
                })
              }
              onMouseLeave={() => setTip(null)}
            />
          ))}
        </svg>
      </div>

      {tip && (
        <div
          className="western-digits pointer-events-none fixed z-20 whitespace-nowrap rounded-lg bg-gray-900 px-2.5 py-1.5 text-sm text-white shadow-lg"
          style={{ left: Math.min(tip.x + 14, 1200), top: tip.y - 38 }}
        >
          {tip.text}
        </div>
      )}
    </div>
  );
}
