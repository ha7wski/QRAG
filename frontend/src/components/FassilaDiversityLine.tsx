"use client";

import { useRef, useState } from "react";
import { Minus, Plus, RotateCcw } from "lucide-react";
import { tooltipAnchor } from "@/lib/chartTooltip";
import { count, NOUNS } from "@/lib/strings";

/**
 * One continuous line over the 114 sūras: some ascending X against the number of
 * distinct fawāṣil. Rendered twice — X = āya count, and X = sūra rank.
 *
 * Follows `FassilaLine`'s conventions on purpose (0-anchored X domain, nice tick
 * steps, fixed-position tooltip, scroll inside the card rather than the page).
 *
 * The X axis grows **rightward** even though the page is `dir="rtl"`: SVG `x` is
 * measured from the left edge whatever the ambient direction, which is why these
 * charts are SVG and not flow layout. The scroll wrapper is pinned to `dir="ltr"`
 * for the same reason — an RTL scroll container would start the view at the right
 * edge and give `scrollLeft` browser-dependent semantics, both wrong for an axis
 * that reads from 0 upward.
 *
 * Points arrive **pre-sorted** by the caller. That is not a detail to optimize
 * away: 24 āya-count values are shared by more than one sūra (two of them by five),
 * so the length chart needs a deterministic tie-break or the polyline reorders
 * between renders.
 */

export interface DiversityPoint {
  x: number;
  y: number;
  surah: number;
  name: string;
  ayahs: number;
}

const BASE_W = 620;
const MIN_W = 560;
/** Discrete magnifications. The X domain never changes — only how wide it is drawn. */
const ZOOMS = [1, 2, 4, 8];

/** Round tick interval targeting roughly `target` ticks across the axis. */
function niceStep(n: number, target: number): number {
  const nice = [1, 2, 5, 10, 20, 25, 50, 100, 200];
  const raw = Math.max(1, n / target);
  return nice.reduce((a, b) => (Math.abs(b - raw) < Math.abs(a - raw) ? b : a));
}

function xticks(n: number, target: number): number[] {
  const step = niceStep(n, target);
  const out = [0];
  for (let t = step; t < n - step * 0.4; t += step) out.push(t);
  out.push(n);
  return out;
}

export default function FassilaDiversityLine({
  points,
  xMax,
  ariaLabel,
}: {
  /** Pre-sorted by ascending x, ties broken deterministically by the caller. */
  points: DiversityPoint[];
  xMax: number;
  ariaLabel: string;
}) {
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  const [zoom, setZoom] = useState(1);
  /** How far the plot is scrolled, in viewBox units — pins the Y axis (see below). */
  const [scrolled, setScrolled] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  if (!points.length || !xMax) return null;

  const yMax = Math.max(...points.map((p) => p.y));

  /**
   * Zoom stretches the plot **horizontally only**. The viewBox width grows with
   * the rendered width, so one viewBox unit stays one pixel: the axis labels,
   * stroke widths and vertex radii keep their size while the crowded left of the
   * length chart — 78 of 114 sūras sit below 60 āyāt — spreads out. Scaling the
   * whole SVG instead would magnify the type along with the data.
   */
  const W = BASE_W * zoom;
  const mT = 14;
  const mB = 34;
  const mR = 16;
  // Wide enough that the Y labels sit clear of the axis rather than touching it.
  const mL = 54;
  const plotH = 210;
  const plotW = W - mL - mR;
  const H = mT + plotH + mB;

  // X anchored at 0, growing rightward. Y grows upward from 0.
  const px = (x: number) => mL + (x / xMax) * plotW;
  const py = (y: number) => mT + plotH - (y / yMax) * plotH;

  const path = points.map((p) => `${px(p.x).toFixed(1)},${py(p.y).toFixed(1)}`).join(" ");
  const r = zoom > 2 ? 3 : zoom > 1 ? 2.6 : points.length > 160 ? 1.6 : 2.1;
  // 12 rows would crowd; label every other one past 8 distinct values.
  const yStep = yMax > 8 ? 2 : 1;
  const yRows = [];
  for (let v = yStep; v <= yMax; v += yStep) yRows.push(v);

  const zoomIndex = ZOOMS.indexOf(zoom);

  /**
   * Track the scroll offset in viewBox units so the Y axis can be translated to
   * follow it. Zoomed in, the axis would otherwise slide off the left edge and
   * leave the gridlines unlabelled — you could see the shape but not read a value.
   */
  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    setScrolled(el.scrollWidth ? (el.scrollLeft * W) / el.scrollWidth : 0);
  };

  /** Change magnification while keeping whatever is centred, centred. */
  const changeZoom = (next: number) => {
    const el = scrollRef.current;
    const centre =
      el && el.scrollWidth > 0
        ? (el.scrollLeft + el.clientWidth / 2) / el.scrollWidth
        : 0.5;
    setZoom(next);
    requestAnimationFrame(() => {
      const after = scrollRef.current;
      if (!after) return;
      after.scrollLeft = Math.max(
        0,
        centre * after.scrollWidth - after.clientWidth / 2,
      );
      // Programmatic scroll may not fire onScroll in every browser; sync directly.
      setScrolled(
        after.scrollWidth
          ? (after.scrollLeft * BASE_W * next) / after.scrollWidth
          : 0,
      );
    });
  };

  return (
    <div className="relative">
      {/* Magnification controls — chrome belonging to the card, so they sit
          at its start edge (physically the right, the page being RTL). This
          row used to be a `dir="ltr"` island with `justify-end`, which
          reached the same pixels for the wrong reason and hid a second job:
          the «×2» label needs LTR of its own. Measured — in an RTL run the
          multiplication sign resolves right-to-left and «×2» renders «2×» —
          so the island moved down to the label that needs it (design D7,
          D15). Numbers stay Western digits like everything else. */}
      <div className="mb-2 flex items-center justify-start gap-1">
        <button
          type="button"
          aria-label="تصغير"
          disabled={zoomIndex <= 0}
          onClick={() => changeZoom(ZOOMS[zoomIndex - 1])}
          className="rounded-lg border border-gray-300 p-1.5 text-gray-700 transition hover:bg-gray-50 disabled:opacity-40"
        >
          <Minus className="h-3.5 w-3.5" />
        </button>
        <span
          dir="ltr"
          className="western-digits w-8 text-center text-xs tabular-nums text-gray-500"
        >
          ×{zoom}
        </span>
        <button
          type="button"
          aria-label="تكبير"
          disabled={zoomIndex >= ZOOMS.length - 1}
          onClick={() => changeZoom(ZOOMS[zoomIndex + 1])}
          className="rounded-lg border border-gray-300 p-1.5 text-gray-700 transition hover:bg-gray-50 disabled:opacity-40"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          aria-label="إعادة الضبط"
          disabled={zoom === 1}
          onClick={() => changeZoom(1)}
          className="rounded-lg border border-gray-300 p-1.5 text-gray-700 transition hover:bg-gray-50 disabled:opacity-40"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* The chart scrolls, never the page body. LTR so it opens at x = 0. */}
      <div
        dir="ltr"
        ref={scrollRef}
        onScroll={onScroll}
        className="w-full overflow-x-auto"
      >
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="block h-auto"
          style={{
            // Width and viewBox scale by the same factor, so a viewBox unit keeps
            // the same pixel size at every magnification: no jump in label or
            // stroke size between ×1 and ×2. Percent (not px) so ×1 still fills
            // the card exactly as `w-full` did.
            width: `${zoom * 100}%`,
            minWidth: `${MIN_W * zoom}px`,
          }}
          role="img"
          aria-label={ariaLabel}
        >
          {yRows.map((v) => (
            <line
              key={`y-${v}`}
              x1={mL}
              y1={py(v)}
              x2={mL + plotW}
              y2={py(v)}
              className="stroke-gray-200"
              strokeWidth={1}
              strokeDasharray="2 4"
            />
          ))}

          {xticks(xMax, 6 * zoom).map((v) => (
            <g key={`x-${v}`}>
              <line
                x1={px(v)}
                y1={mT}
                x2={px(v)}
                y2={mT + plotH}
                className="stroke-gray-200"
                strokeWidth={1}
              />
              <text
                x={px(v)}
                y={mT + plotH + 18}
                textAnchor="middle"
                className="western-digits fill-gray-500 text-[11px]"
              >
                {v}
              </text>
            </g>
          ))}

          <polyline
            points={path}
            fill="none"
            className="stroke-brand"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {points.map((p) => (
            <circle
              key={p.surah}
              cx={px(p.x)}
              cy={py(p.y)}
              r={r}
              className="fill-brand stroke-white hover:fill-brand-dark"
              strokeWidth={1}
              onMouseEnter={(e) =>
                setTip({
                  x: e.clientX,
                  y: e.clientY,
                  text: `${p.name} · ${count(p.ayahs, NOUNS.aya)} · ${count(
                    p.y,
                    NOUNS.fasila,
                  )}`,
                })
              }
              onMouseLeave={() => setTip(null)}
            />
          ))}

          {/* Y axis, pinned to the scroll offset and drawn last so the plot slides
              *under* it. The backing rect stops at the plot floor, leaving the X
              tick labels below it visible. */}
          <g transform={`translate(${scrolled},0)`}>
            <rect x={0} y={0} width={mL} height={mT + plotH} fill="#fff" />
            {yRows.map((v) => (
              <text
                key={`ylab-${v}`}
                x={mL - 18}
                y={py(v) + 4}
                textAnchor="end"
                className="western-digits fill-gray-400 text-[11px]"
              >
                {v}
              </text>
            ))}
            <line
              x1={mL}
              y1={mT}
              x2={mL}
              y2={mT + plotH}
              className="stroke-gray-300"
              strokeWidth={1}
            />
          </g>
        </svg>
      </div>

      {tip && (
        <div
          className="western-digits pointer-events-none fixed z-20 whitespace-nowrap rounded-lg bg-gray-900 px-2.5 py-1.5 font-arabic text-sm text-white shadow-lg"
          style={{ ...tooltipAnchor(tip.x), top: tip.y - 38 }}
        >
          {tip.text}
        </div>
      )}
    </div>
  );
}
