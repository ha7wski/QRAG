"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  type SurahGroupCount,
  detailOf,
  getSurahSimilarityOverview,
  statusOf,
} from "@/lib/api";
import { useCachedState } from "@/lib/pageCache";
import { S, forStatus } from "@/lib/strings";
import FailureNote, { type Failure } from "@/components/FailureNote";
import { LoadingLine } from "@/components/SimilarVerseParts";

/**
 * The foldable chart above the «داخل السورة» picker: one vertical bar per surah
 * holding at least one group of close verses, in mushaf order (al-Baqara first —
 * al-Fatiha holds none), its height the surah's GROUP count. Clicking a bar picks
 * that surah exactly as the picker would.
 *
 * Origin on the left, like the surah × surah map, so the two charts of the tab
 * read the mushaf in the same direction.
 *
 * Folded by default; the fold is remembered in localStorage (SSR-guarded, every
 * access in try/catch, on the `PageIntro` pattern). The overview is fetched on
 * the first unfold only, then cached under `verse-study.similar.surah.*`.
 */

const OPEN_KEY = "verse-study.similar.surah.chart.open";

function readOpen(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(OPEN_KEY) === "1";
  } catch {
    return false;
  }
}

function writeOpen(open: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (open) window.localStorage.setItem(OPEN_KEY, "1");
    else window.localStorage.removeItem(OPEN_KEY);
  } catch {
    // Blocked storage: the fold still applies for this visit.
  }
}

// Geometry, in SVG units (1 unit = 1 CSS px at the natural width).
const BAR = 26; // slot per surah
const GAP = 6; // empty part of a slot
const PLOT_H = 180;
const TOP = 18; // room for the value above the tallest bar
const LABEL_H = 92; // rotated surah names
const AXIS_W = 28; // y ticks

export default function SurahSimilarityChart({
  selected,
  onChoose,
}: {
  /** The surah on screen, drawn darker. */
  selected: number | "";
  /** Picks a surah, as the picker would. */
  onChoose: (surah: number) => void;
}) {
  // Server renders folded; the stored value is read after mount.
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(readOpen()), []);

  const [rows, setRows] = useCachedState<SurahGroupCount[] | null>(
    "verse-study.similar.surah.overview",
    null,
  );
  const [error, setError] = useState<Failure | null>(null);
  const [loading, setLoading] = useState(false);
  const requested = useRef(false);

  useEffect(() => {
    if (!open || rows || requested.current) return;
    requested.current = true;
    setLoading(true);
    getSurahSimilarityOverview()
      .then((res) => setRows(res.surahs))
      .catch((e) => {
        requested.current = false;
        setError({ text: forStatus(statusOf(e), "surah"), detail: detailOf(e) });
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, rows]);

  function toggle() {
    const next = !open;
    setOpen(next);
    writeOpen(next);
    if (next) setError(null);
  }

  const t = S.verseStudy.surahSimilar;

  return (
    <section
      data-testid="surah-similarity-chart"
      className="rounded-lg border border-gray-200 bg-white"
    >
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        aria-controls="surah-similarity-chart-body"
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-start font-arabic text-lg font-semibold text-gray-800 hover:bg-gray-50"
      >
        <span>{t.chartToggle}</span>
        <ChevronDown
          aria-hidden="true"
          className={`h-5 w-5 shrink-0 text-gray-500 transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <div
          id="surah-similarity-chart-body"
          className="space-y-3 border-t border-gray-100 px-4 py-3"
        >
          {error && (
            <FailureNote
              failure={error}
              className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
            />
          )}
          {loading && <LoadingLine />}
          {rows && rows.length === 0 && (
            <p lang="ar" className="font-arabic text-amber-800">
              {t.chartEmpty}
            </p>
          )}
          {rows && rows.length > 0 && (
            <>
              <p lang="ar" className="text-xs text-gray-500">
                {t.chartHint}
              </p>
              <Bars rows={rows} selected={selected} onChoose={onChoose} />
            </>
          )}
        </div>
      )}
    </section>
  );
}

function Bars({
  rows,
  selected,
  onChoose,
}: {
  rows: SurahGroupCount[];
  selected: number | "";
  onChoose: (surah: number) => void;
}) {
  const [hot, setHot] = useState<number | null>(null);
  const max = Math.max(...rows.map((r) => r.groups));
  const width = AXIS_W + rows.length * BAR + 8;
  const height = TOP + PLOT_H + LABEL_H;
  const y = (v: number) => TOP + PLOT_H - (v / max) * PLOT_H;
  // Integer ticks only — a group count has no fractions. At most ~5 lines.
  const step = Math.max(1, Math.ceil(max / 5));
  const ticks: number[] = [];
  for (let v = 0; v <= max; v += step) ticks.push(v);

  return (
    <div dir="ltr" className="max-w-full overflow-x-auto">
      <svg
        role="group"
        aria-label={S.verseStudy.surahSimilar.chartLabel}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="western-digits block"
      >
        {ticks.map((v) => (
          <g key={v} aria-hidden="true">
            <line
              x1={AXIS_W}
              x2={width}
              y1={y(v)}
              y2={y(v)}
              stroke={v === 0 ? "#9ca3af" : "#e5e7eb"}
            />
            <text
              x={AXIS_W - 6}
              y={y(v)}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize={11}
              fill="#6b7280"
            >
              {v}
            </text>
          </g>
        ))}

        {rows.map((r, i) => {
          const x = AXIS_W + i * BAR + GAP / 2;
          const w = BAR - GAP;
          const cx = x + w / 2;
          const isSel = r.surah_number === selected;
          const isHot = r.surah_number === hot;
          const label = S.verseStudy.surahSimilar.chartBar(r.surah_name_ar, r.groups);
          return (
            <g
              key={r.surah_number}
              role="button"
              tabIndex={0}
              aria-label={label}
              aria-pressed={isSel}
              data-testid="surah-similarity-bar"
              onClick={() => onChoose(r.surah_number)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onChoose(r.surah_number);
                }
              }}
              onMouseEnter={() => setHot(r.surah_number)}
              onMouseLeave={() => setHot(null)}
              onFocus={() => setHot(r.surah_number)}
              onBlur={() => setHot(null)}
              className="cursor-pointer outline-none"
            >
              <title>{label}</title>
              {/* The whole slot is the hit area, not just the bar. */}
              <rect
                x={AXIS_W + i * BAR}
                y={TOP}
                width={BAR}
                height={PLOT_H + LABEL_H}
                fill={isHot ? "#e6f4f0" : "transparent"}
              />
              <rect
                x={x}
                y={y(r.groups)}
                width={w}
                height={TOP + PLOT_H - y(r.groups)}
                rx={2}
                fill={isSel || isHot ? "#0a5c4c" : "#0e7c66"}
              />
              <text
                x={cx}
                y={y(r.groups) - 4}
                textAnchor="middle"
                fontSize={11}
                fill="#374151"
              >
                {r.groups}
              </text>
              <text
                x={cx}
                y={TOP + PLOT_H + 8}
                transform={`rotate(-60 ${cx} ${TOP + PLOT_H + 8})`}
                textAnchor="end"
                dominantBaseline="middle"
                fontSize={13}
                fontWeight={isSel ? 700 : 400}
                fill={isSel || isHot ? "#0a5c4c" : "#4b5563"}
                className="font-arabic"
              >
                {r.surah_name_ar}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
