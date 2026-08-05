"use client";

import { useState } from "react";
import type { FassilaBucket, FassilaSurahSummary } from "@/lib/fassilaTypes";
import { fmtPercent } from "@/lib/arabicDigits";

/**
 * How the 114 sūras distribute over their number of distinct fawāṣil, as a pie
 * with a clickable legend.
 *
 * Three things here are load-bearing and easy to "tidy" into something wrong:
 *
 *   ordinal ramp: the bucket value is a *position in a sequence*, so the fills are
 *       one hue with monotone lightness (light = few fawāṣil → dark = many), never a
 *       categorical multi-hue palette. `brand.light` (#e6f4f0) is deliberately NOT
 *       the light end — it sits at 1.13:1 on a white card, effectively invisible; the
 *       anchors below start at 2.01:1.
 *   colour ≠ identity: a single-hue ramp supports about 6 perceptually distinct
 *       steps on white. Spread over 12 buckets adjacent steps fall to ΔL ≈ 0.037
 *       against a 0.06 floor, so buckets 9 and 10 are NOT tellable apart by eye.
 *       That is fine only because the legend, the tooltip and the list's status line
 *       all name the category in digits. Shade carries direction; never identity.
 *   the legend is the real control: three buckets hold one sūra each and render as
 *       ~3.2° wedges (about 9 px of arc). Their legend row is a full-size target, and
 *       the wedges get a radially-extended hit area on top.
 */

/** Validated 6-step ordinal ramp: monotone lightness, ΔL ≥ 0.06, light end 2.01:1 on white. */
const RAMP_ANCHORS = [
  "#84c4ab",
  "#6dad94",
  "#57967e",
  "#407f69",
  "#296954",
  "#0e5440",
];

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** Interpolate the anchors at `t` ∈ [0,1] — 0 lightest (few fawāṣil), 1 darkest. */
function rampColor(t: number): string {
  const segments = RAMP_ANCHORS.length - 1;
  const x = Math.min(Math.max(t, 0), 1) * segments;
  const i = Math.min(Math.floor(x), segments - 1);
  const f = x - i;
  const a = hexToRgb(RAMP_ANCHORS[i]);
  const b = hexToRgb(RAMP_ANCHORS[i + 1]);
  const mix = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `#${mix.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

const CX = 130;
const CY = 130;
const R = 116;
/** Hit paths run past the rim: it widens thin wedges without stealing a neighbour's sector. */
const R_HIT = R + 16;
/**
 * The viewBox is padded by the hit ring's overhang. Without this the outermost
 * `svg` clips at its own viewport, cutting the extended hit area away exactly at
 * 12/3/6/9 o'clock — and 12 o'clock is where the three single-sūra buckets sit,
 * so the very wedges the ring exists to rescue would be the ones losing it.
 */
const PAD = R_HIT - R;
const VIEW_BOX = `${-PAD} ${-PAD} ${CX * 2 + PAD * 2} ${CY * 2 + PAD * 2}`;

/** Sector path from `start` to `end`, degrees clockwise from 12 o'clock. */
function sector(radius: number, start: number, end: number): string {
  const pt = (deg: number) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)];
  };
  const [x1, y1] = pt(start);
  const [x2, y2] = pt(end);
  const large = end - start > 180 ? 1 : 0;
  // A lone bucket would span 360° and collapse to a point; draw it as a full disc.
  if (end - start >= 359.999) {
    return `M ${CX} ${CY - radius} A ${radius} ${radius} 0 1 1 ${CX - 0.01} ${
      CY - radius
    } Z`;
  }
  return `M ${CX} ${CY} L ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2} Z`;
}

export default function FassilaDistributionPie({
  buckets,
  surahs,
  active,
  onSelect,
}: {
  buckets: FassilaBucket[];
  surahs: FassilaSurahSummary[];
  /** Distinct-fāṣila count of the active category, or null when unfiltered. */
  active: number | null;
  /** Called with a bucket value; the parent clears when it equals `active`. */
  onSelect: (distinct: number) => void;
}) {
  const [tip, setTip] = useState<{ x: number; y: number; distinct: number } | null>(
    null,
  );

  const total = buckets.reduce((sum, b) => sum + b.surah_count, 0);
  if (!total) return null;

  const n = buckets.length;
  const colorOf = (i: number) => rampColor(n > 1 ? i / (n - 1) : 0);

  // Ascending bucket order, clockwise from the top.
  let cursor = 0;
  const slices = buckets.map((b, i) => {
    const start = cursor;
    const end = start + (b.surah_count / total) * 360;
    cursor = end;
    return { bucket: b, start, end, fill: colorOf(i) };
  });

  const surahsOf = (distinct: number) =>
    surahs.filter((s) => s.distinct_count === distinct);

  const show = (e: React.MouseEvent, distinct: number) =>
    setTip({ x: e.clientX, y: e.clientY, distinct });

  return (
    <div className="relative flex flex-col items-center gap-6 md:flex-row md:items-start md:justify-center md:gap-10">
      <svg
        viewBox={VIEW_BOX}
        className="h-auto w-full max-w-[280px] shrink-0"
        role="img"
        aria-label="توزّع السور حسب عدد الفواصل المميّزة"
      >
        {slices.map(({ bucket, start, end, fill }) => (
          <path
            key={`slice-${bucket.distinct}`}
            d={sector(R, start, end)}
            fill={fill}
            stroke="#fff"
            strokeWidth={2}
            className={active === bucket.distinct ? "" : "opacity-100"}
            opacity={active !== null && active !== bucket.distinct ? 0.35 : 1}
          />
        ))}

        {/* Active ring — a second channel on top of the shade, which cannot carry it. */}
        {slices
          .filter((s) => s.bucket.distinct === active)
          .map(({ bucket, start, end }) => (
            <path
              key={`ring-${bucket.distinct}`}
              d={sector(R + 5, start, end)}
              fill="none"
              stroke="#0a5c4c"
              strokeWidth={2.5}
              strokeLinejoin="round"
            />
          ))}

        {/* Hit layer, drawn last so it takes the pointer. */}
        {slices.map(({ bucket, start, end }) => (
          <path
            key={`hit-${bucket.distinct}`}
            d={sector(R_HIT, start, end)}
            fill="transparent"
            className="cursor-pointer"
            onClick={() => onSelect(bucket.distinct)}
            onMouseEnter={(e) => show(e, bucket.distinct)}
            onMouseMove={(e) => show(e, bucket.distinct)}
            onMouseLeave={() => setTip(null)}
          />
        ))}
      </svg>

      {/* Legend — same order as the slices, and the reliable hit target. */}
      <ul className="w-full min-w-0 flex-1 md:max-w-sm">
        {slices.map(({ bucket, fill }) => {
          const on = active === bucket.distinct;
          return (
            <li key={`legend-${bucket.distinct}`}>
              <button
                type="button"
                onClick={() => onSelect(bucket.distinct)}
                onMouseEnter={(e) => show(e, bucket.distinct)}
                onMouseMove={(e) => show(e, bucket.distinct)}
                onMouseLeave={() => setTip(null)}
                aria-pressed={on}
                aria-label={`${bucket.distinct} فاصلة مميّزة — ${bucket.surah_count} سورة`}
                className={`flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-right transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                  on ? "bg-brand-light" : "hover:bg-gray-50"
                }`}
              >
                <span
                  aria-hidden
                  className="h-3.5 w-3.5 shrink-0 rounded-sm"
                  style={{ backgroundColor: fill }}
                />
                <span
                  className={`western-digits w-16 shrink-0 whitespace-nowrap tabular-nums text-sm ${
                    on ? "font-semibold text-brand-dark" : "text-gray-800"
                  }`}
                >
                  {bucket.distinct} فاصلة
                </span>
                <span className="western-digits w-20 shrink-0 whitespace-nowrap tabular-nums text-sm text-gray-600">
                  {bucket.surah_count} سورة
                </span>
                <span className="western-digits tabular-nums text-sm text-gray-400">
                  {fmtPercent(bucket.percentage)}%
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {tip && <CategoryTooltip x={tip.x} y={tip.y} surahs={surahsOf(tip.distinct)} />}
    </div>
  );
}

/**
 * The sūras of one category, one per line, each prefixed with `-`.
 *
 * Long categories (the 30 sūras of bucket 3) would overflow a single column, so
 * past 16 entries it flows into two — each sūra still occupies its own line. The
 * card flips above the pointer in the lower half of the viewport so a tall list
 * stays on screen.
 */
function CategoryTooltip({
  x,
  y,
  surahs,
}: {
  x: number;
  y: number;
  surahs: FassilaSurahSummary[];
}) {
  const below = typeof window !== "undefined" && y < window.innerHeight / 2;
  return (
    <div
      className="pointer-events-none fixed z-30 max-h-[70vh] rounded-lg bg-gray-900 px-3 py-2 text-white shadow-lg"
      style={{
        left: Math.max(8, x - 120),
        top: below ? y + 18 : undefined,
        bottom: below ? undefined : `calc(100vh - ${y - 18}px)`,
      }}
    >
      <ul
        className={`font-arabic text-xs leading-snug ${
          surahs.length > 16 ? "columns-2 gap-4" : ""
        }`}
      >
        {surahs.map((s) => (
          <li key={s.surah} className="whitespace-nowrap">
            - {s.surah_name}
          </li>
        ))}
      </ul>
    </div>
  );
}
