"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import {
  type QuranSimilarityCell,
  type QuranSimilarityMatrix,
  type QuranSimilarityPairs,
  detailOf,
  getQuranSimilarityMatrix,
  getQuranSimilarityPairs,
  statusOf,
} from "@/lib/api";
import { useCachedState } from "@/lib/pageCache";
import { S, forStatus } from "@/lib/strings";
import FailureNote, { type Failure } from "@/components/FailureNote";
import {
  LoadingLine,
  RootChips,
  SharedWords,
  VerseCardButton,
} from "@/components/SimilarVerseParts";

/**
 * «الآيات المتشابهات في سائر القرآن» — the surah × surah map.
 *
 * Every cell (A, B) counts the close verse PAIRS between surah A and surah B
 * in the unified close-verses dataset (`GET /quran-similarity/matrix`); picking
 * a cell lists those pairs below the chart (`GET /quran-similarity/pairs/{a}/{b}`),
 * each verse opening «الآية في سياقها». Load-bearing choices, easy to "tidy" into wrong ones:
 *
 *   the axes are DERIVED: only the surahs that appear in at least one cell get a
 *       row and a column (about a hundred), in mushaf order. The route
 *       still sends all 114 names; it is the chart that drops the empty ones, so a
 *       rebuilt dataset re-derives its axes and nothing here is hard-coded.
 *   the square is MIRRORED: (A, B) and (B, A) are both drawn, so a pair is found
 *       starting from either surah. The diagonal is a neutral, inert cell —
 *       intra-surah closeness is the other mode's question and another population.
 *   the ORIGIN is BOTTOM-LEFT, as the user asked: al-Fatiha is the first column
 *       on the left and the first row at the bottom; the x-axis reads left to
 *       right, the y-axis bottom to top. Column names sit along the bottom, row
 *       names on the left, and the box opens scrolled to that corner.
 *   the scale is LOG-BINNED (1, 2, 3–4, 5–8, 9–16, 17+): the darkest cells
 *       hold dozens of pairs and most hold 1–2, so a linear scale would wash every small cell into the
 *       background. Colour carries magnitude only — the tooltip and the list
 *       heading give the exact count. An EMPTY cell is the card's background, not
 *       the lightest step: «no pair» must not read as «few pairs».
 *   no score is rendered anywhere: the order of the list carries the ranking.
 *
 * ONE relation, the unified close verses: a pair is in it when its verses are
 * close in meaning and syntax OR share a passage of wording (there is no
 * relation switch any more). A listed pair shows its COMMON PART `<mark>`ed in
 * both verses (character spans from the route) with «N كلمات مشتركة» under it,
 * and the plain verses when it has none.
 *
 * Durable state lives under `verse-study.similar.quran.*` (matrix, cell,
 * cells), so leaving the mode or the page and coming back shows the same cell
 * with no request.
 */

/**
 * The ramp, validated with the `dataviz` skill's `validate_palette.js --ordinal`
 * (the bins are ORDERED steps, so the ordinal check applies: monotone lightness,
 * adjacent ΔL ≥ 0.06, the step nearest the surface clearing 2:1, one hue).
 *
 *   light, on the white card (#ffffff): #84c4ab #6dad94 #57967e #407f69 #296954
 *       #0e5440 — ALL CHECKS PASS, light end 2.01:1, hue spread 1°. It is the
 *       Fassila pie's ramp (FassilaDistributionPie), on purpose: one green scale
 *       across the app's charts.
 *   dark, on #111827 (anchor flipped — few pairs dark, many pairs bright):
 *       #2f7a63 #3f8f76 #52a489 #69b99d #84cdb2 #a3e0c8 — ALL CHECKS PASS, near end
 *       3.45:1, hue spread 2°. Recorded, NOT wired: the app is light-only
 *       (`color-scheme: light` in globals.css, no `dark:` variant anywhere), so
 *       the card stays white under a dark OS theme and the light ramp is the one
 *       that is correct on it. Wire this one if a dark theme is ever added.
 */
const RAMP = ["#84c4ab", "#6dad94", "#57967e", "#407f69", "#296954", "#0e5440"];
/** Lower edge of each log bin; the last bin is open-ended. */
const BIN_FLOORS = [1, 2, 3, 5, 9, 17];
/** The inert diagonal: a neutral grey, never on the ramp. */
const DIAGONAL = "#e5e7eb";

/** Cell side, in px. ~100 surahs × 12 px ≈ 1 200 px: wider than the page, hence
 *  the chart's own scroll container. */
const C = 12;
/** Room for a surah name: the row-label column and the column-label band. */
const LABEL = 96;

/** The bin of a positive pair count: 1 → 0, 2 → 1, 3–4 → 2, 5–8 → 3, 9–16 → 4, 17+ → 5. */
export function binOf(pairs: number): number {
  let bin = 0;
  for (let i = 0; i < BIN_FLOORS.length; i++) if (pairs >= BIN_FLOORS[i]) bin = i;
  return bin;
}

/** The key a cell is cached under: lower surah first. */
const keyOf = (a: number, b: number) => `${Math.min(a, b)}:${Math.max(a, b)}`;

type CellRef = { a: number; b: number };

const LIST_ID = "quran-map-pairs";

export default function QuranSimilarityMap({
  openInContext,
}: {
  /** Opens a verse in «الآية في سياقها» — the page's own handler. */
  openInContext: (surah: number, ayah: number) => void;
}) {
  const [matrix, setMatrix] = useCachedState<QuranSimilarityMatrix | null>(
    "verse-study.similar.quran.matrix",
    null,
  );
  // The selected cell, `a < b`.
  const [selected, setSelected] = useCachedState<CellRef | null>(
    "verse-study.similar.quran.cell",
    null,
  );
  // Fetched cells, keyed "a:b" with a < b.
  const [cells, setCells] = useCachedState<Record<string, QuranSimilarityPairs>>(
    "verse-study.similar.quran.cells",
    {},
  );
  // Transient — never cached (a cached `true` restores a spinner that never stops).
  // The failures too: a cached one would keep the mode failed after the dataset
  // is rebuilt, since a remount re-issues only what is neither in hand nor failed.
  const [matrixError, setMatrixError] = useState<Failure | null>(null);
  const [cellError, setCellError] = useState<Failure | null>(null);
  const [matrixLoading, setMatrixLoading] = useState(false);
  const [cellLoading, setCellLoading] = useState(false);
  // One counter per request kind: picking cell X then Y must end on Y, and a
  // cell request must never cancel the matrix one.
  const matrixSeq = useRef(0);
  const cellSeq = useRef(0);

  async function fetchMatrix() {
    const seq = ++matrixSeq.current;
    setMatrixError(null);
    setMatrixLoading(true);
    try {
      const res = await getQuranSimilarityMatrix();
      if (seq === matrixSeq.current) setMatrix(res);
    } catch (e) {
      if (seq === matrixSeq.current)
        setMatrixError({ text: forStatus(statusOf(e)), detail: detailOf(e) });
    } finally {
      if (seq === matrixSeq.current) setMatrixLoading(false);
    }
  }

  async function fetchCell(a: number, b: number) {
    const seq = ++cellSeq.current;
    setCellLoading(true);
    try {
      const res = await getQuranSimilarityPairs(a, b);
      if (seq === cellSeq.current)
        setCells((prev) => ({ ...prev, [keyOf(a, b)]: res }));
    } catch (e) {
      if (seq === cellSeq.current)
        setCellError({ text: forStatus(statusOf(e)), detail: detailOf(e) });
    } finally {
      if (seq === cellSeq.current) setCellLoading(false);
    }
  }

  // The matrix is requested once, when the mode is first shown (this component
  // mounts then). A selection cached before its answer landed — the page was
  // left mid-request, or its request failed — is re-issued, as `SurahSimilarity`
  // does.
  useEffect(() => {
    if (!matrix) void fetchMatrix();
    if (selected && !cells[keyOf(selected.a, selected.b)])
      void fetchCell(selected.a, selected.b);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function choose(x: number, y: number) {
    const a = Math.min(x, y);
    const b = Math.max(x, y);
    // Already selected AND answered (or in flight): nothing to do. A selected
    // cell whose request failed falls through — picking it again retries.
    if (selected?.a === a && selected?.b === b && (cells[keyOf(a, b)] || cellLoading))
      return;
    setSelected({ a, b });
    setCellError(null);
    const list = document.getElementById(LIST_ID);
    if (list && typeof list.scrollIntoView === "function")
      list.scrollIntoView({ behavior: "smooth", block: "start" });
    if (cells[keyOf(a, b)]) {
      cellSeq.current++; // a cell still in flight must not replace this one
      setCellLoading(false);
    } else void fetchCell(a, b);
  }

  const names = useMemo(
    () => new Map((matrix?.surahs ?? []).map((s) => [s.number, s.name_ar])),
    [matrix],
  );
  const selectedCell =
    selected && matrix
      ? matrix.cells.find((c) => c.a === selected.a && c.b === selected.b)
      : undefined;
  const pairs = selected ? cells[keyOf(selected.a, selected.b)] : undefined;

  return (
    <div className="space-y-6">
      {matrixError && (
        <FailureNote
          failure={matrixError}
          className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          <button
            type="button"
            lang="ar"
            data-testid="quran-map-retry"
            onClick={() => void fetchMatrix()}
            className="shrink-0 rounded border border-red-200 bg-white px-2 py-0.5 font-arabic text-red-700 hover:bg-red-100"
          >
            {S.verseStudy.quranMap.retry}
          </button>
        </FailureNote>
      )}

      {matrixLoading && <LoadingLine />}

      {matrix && !matrixLoading && (
        <>
          {matrix.cells.length === 0 ? (
            <div
              role="status"
              lang="ar"
              data-testid="quran-map-empty"
              className="rounded-lg bg-amber-50 px-4 py-3 font-arabic text-lg text-amber-800"
            >
              {S.verseStudy.quranMap.noPairs}
            </div>
          ) : (
            <Heatmap matrix={matrix} names={names} selected={selected} onChoose={choose} />
          )}
        </>
      )}

      <section id={LIST_ID} className="scroll-mt-4 space-y-3">
        {selected && (
          <h3
            lang="ar"
            data-testid="quran-map-pairs-heading"
            className="western-digits font-arabic text-lg font-semibold text-gray-800"
          >
            {S.verseStudy.quranMap.pairsHeading}
            {" — "}
            {S.verseStudy.quranMap.cell(
              pairs?.surah_name_a ?? names.get(selected.a) ?? String(selected.a),
              pairs?.surah_name_b ?? names.get(selected.b) ?? String(selected.b),
              selectedCell?.pairs ?? pairs?.pairs.length ?? 0,
              selectedCell?.verses_a ?? new Set(pairs?.pairs.map((p) => p.u.id)).size,
              selectedCell?.verses_b ?? new Set(pairs?.pairs.map((p) => p.v.id)).size,
            )}
          </h3>
        )}

        {selected && cellError && (
          <FailureNote
            failure={cellError}
            className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
          />
        )}

        {selected && cellLoading && <LoadingLine />}

        {pairs &&
          !cellLoading &&
          (pairs.pairs.length === 0 ? (
            <div
              role="status"
              lang="ar"
              data-testid="quran-map-cell-empty"
              className="rounded-lg bg-amber-50 px-4 py-3 font-arabic text-lg text-amber-800"
            >
              {S.verseStudy.quranMap.noCellPairs}
            </div>
          ) : (
            <ol className="space-y-3">
              {pairs.pairs.map((p) => (
                <li
                  key={`${p.u.id}|${p.v.id}`}
                  data-testid="quran-map-pair"
                  className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition hover:border-brand"
                >
                  {/* Both verses, each with the common part marked when the pair
                      has one (spans into `text_ar_tashkil`, from the route), then
                      its word count, then the shared roots. */}
                  <VerseCardButton
                    verse={p.u}
                    openInContext={openInContext}
                    withSurah
                    span={p.span_u}
                  />
                  <div className="border-t border-dashed border-gray-200">
                    <VerseCardButton
                      verse={p.v}
                      openInContext={openInContext}
                      withSurah
                      span={p.span_v}
                    />
                  </div>
                  <SharedWords words={p.words} />
                  <RootChips roots={p.roots} />
                </li>
              ))}
            </ol>
          ))}
      </section>
    </div>
  );
}

/** One drawn cell instance: (row surah, column surah) — each cell is drawn twice. */
type Drawn = { row: number; col: number; cell: QuranSimilarityCell };

/**
 * The heatmap itself: caption, legend, then the scroll container holding the
 * sticky column band, the sticky row labels and the matrix.
 */
function Heatmap({
  matrix,
  names,
  selected,
  onChoose,
}: {
  matrix: QuranSimilarityMatrix;
  names: Map<number, string>;
  selected: CellRef | null;
  onChoose: (a: number, b: number) => void;
}) {
  // The axes: every surah of at least one cell, in mushaf order.
  const axes = useMemo(() => {
    const set = new Set<number>();
    for (const c of matrix.cells) {
      set.add(c.a);
      set.add(c.b);
    }
    return Array.from(set).sort((x, y) => x - y);
  }, [matrix]);
  const index = useMemo(() => new Map(axes.map((s, i) => [s, i])), [axes]);
  // Both instances of every cell, in row order then column order: the DOM
  // order IS the tab order, so the keyboard walks the matrix row by row, each
  // row from its lowest surah (at the left) — through the
  // upper triangle only, one stop per cell, not two.
  const drawn = useMemo(() => {
    const out: Drawn[] = [];
    for (const cell of matrix.cells) {
      out.push({ row: cell.a, col: cell.b, cell });
      out.push({ row: cell.b, col: cell.a, cell });
    }
    return out.sort((p, q) => p.row - q.row || p.col - q.col);
  }, [matrix]);

  // The cell under the pointer, and the one holding keyboard focus — kept apart,
  // so the pointer can neither move nor clear the focus ring. The bands and the
  // tooltip follow the pointer, and fall back to the focused cell.
  const [hover, setHover] = useState<Drawn | null>(null);
  const [focused, setFocused] = useState<Drawn | null>(null);
  const hot = hover ?? focused;
  const scrollRef = useRef<HTMLDivElement>(null);
  const matrixRef = useRef<HTMLDivElement>(null);
  // Open at the origin, bottom-left, where al-Fatiha's row and column meet.
  useEffect(() => {
    const box = scrollRef.current;
    if (!box) return;
    box.scrollLeft = 0;
    box.scrollTop = box.scrollHeight;
  }, []);

  const N = axes.length;
  const size = N * C;
  // Origin bottom-left: column 0 at the left, row 0 at the bottom.
  const xOf = (col: number) => (index.get(col) ?? 0) * C;
  const yOf = (row: number) => (N - 1 - (index.get(row) ?? 0)) * C;
  const nameOf = (n: number) => names.get(n) ?? String(n);
  const label = (d: Drawn) =>
    S.verseStudy.quranMap.cell(
      nameOf(d.row),
      nameOf(d.col),
      d.cell.pairs,
      d.row === d.cell.a ? d.cell.verses_a : d.cell.verses_b,
      d.row === d.cell.a ? d.cell.verses_b : d.cell.verses_a,
    );
  const isSelected = (d: Drawn) =>
    selected !== null && selected.a === d.cell.a && selected.b === d.cell.b;

  function onKey(e: KeyboardEvent<SVGRectElement>, d: Drawn) {
    if (e.key !== "Enter" && e.key !== " ") return;
    e.preventDefault();
    onChoose(d.row, d.col);
  }

  const hotRow = hot ? index.get(hot.row) : undefined;
  const hotCol = hot ? index.get(hot.col) : undefined;

  return (
    <div className="space-y-3">
      <p lang="ar" data-testid="quran-map-caption" className="western-digits text-sm text-gray-600">
        {S.verseStudy.quranMap.caption(matrix.cells.length, matrix.total_pairs, N)}
      </p>

      <Legend />

      <p lang="ar" className="text-xs text-gray-500">
        {S.verseStudy.quranMap.hint}
      </p>

      {/* The chart's own scroll box: it scrolls both ways inside the card and
          never pushes the page sideways. Laid out LTR on purpose (the page is
          RTL): row names in the left column, column names in the bottom row,
          both sticky. It opens scrolled to the origin, bottom-left. */}
      <div
        ref={scrollRef}
        data-testid="quran-map-scroll"
        className="max-h-[75vh] max-w-full overflow-auto rounded-lg border border-gray-200 bg-white"
        style={{ direction: "ltr" }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `${LABEL}px ${size}px`,
            gridTemplateRows: `${size}px ${LABEL}px`,
            width: LABEL + size,
          }}
        >
          {/* Row names, pinned to the left while scrolling across. */}
          <svg
            aria-hidden="true"
            width={LABEL}
            height={size}
            className="z-10 bg-white"
            style={{ position: "sticky", left: 0, gridColumn: 1, gridRow: 1 }}
          >
            {axes.map((s, i) => (
              <text
                key={s}
                data-testid="quran-map-row-label"
                x={LABEL - 6}
                y={(N - 1 - i) * C + C / 2}
                textAnchor="end"
                dominantBaseline="central"
                fontSize={10}
                fill={hotRow === i ? "#0a5c4c" : "#4b5563"}
                fontWeight={hotRow === i ? 700 : 400}
              >
                {nameOf(s)}
              </text>
            ))}
          </svg>

          {/* Corner: stays put under both sticky bands. */}
          <div
            className="z-30 bg-white"
            style={{ position: "sticky", bottom: 0, left: 0, gridColumn: 1, gridRow: 2 }}
          />

          {/* Column names, rotated, pinned to the bottom while scrolling down. */}
          <svg
            aria-hidden="true"
            width={size}
            height={LABEL}
            className="z-20 bg-white"
            style={{ position: "sticky", bottom: 0, gridColumn: 2, gridRow: 2 }}
          >
            {axes.map((s, j) => (
              <text
                key={s}
                data-testid="quran-map-col-label"
                transform={`translate(${j * C + C / 2},4) rotate(-90)`}
                textAnchor="end"
                dominantBaseline="central"
                fontSize={10}
                fill={hotCol === j ? "#0a5c4c" : "#4b5563"}
                fontWeight={hotCol === j ? 700 : 400}
              >
                {nameOf(s)}
              </text>
            ))}
          </svg>

          <div
            ref={matrixRef}
            className="relative"
            style={{ gridColumn: 2, gridRow: 1 }}
            onMouseLeave={() => setHover(null)}
          >
            <svg
              role="group"
              aria-label={S.verseStudy.quranMap.chartLabel}
              width={size}
              height={size}
              style={{ display: "block" }}
            >
              {/* The hovered row and column, as faint bands: on a ~100 × 100 grid
                  the eye needs a guide back to both names. */}
              {hot && hotRow !== undefined && hotCol !== undefined && (
                <g aria-hidden="true" pointerEvents="none">
                  <rect x={0} y={(N - 1 - hotRow) * C} width={size} height={C} fill="#e6f4f0" />
                  <rect x={hotCol * C} y={0} width={C} height={size} fill="#e6f4f0" />
                </g>
              )}

              {/* The diagonal: neutral and inert — no handler, no tab stop. */}
              <g aria-hidden="true">
                {axes.map((s, i) => (
                  <rect
                    key={s}
                    data-testid="quran-map-diagonal"
                    x={i * C + 1}
                    y={(N - 1 - i) * C + 1}
                    width={C - 2}
                    height={C - 2}
                    rx={2}
                    fill={DIAGONAL}
                  />
                ))}
              </g>

              {drawn.map((d) => (
                <rect
                  key={`${d.row}:${d.col}`}
                  data-testid="quran-map-cell"
                  data-row={d.row}
                  data-col={d.col}
                  data-bin={binOf(d.cell.pairs)}
                  role="button"
                  // One tab stop per cell, not per instance: the upper-triangle
                  // copy takes it, its mirror stays clickable only.
                  tabIndex={d.row < d.col ? 0 : -1}
                  aria-label={label(d)}
                  aria-pressed={isSelected(d)}
                  x={xOf(d.col) + 1}
                  y={yOf(d.row) + 1}
                  width={C - 2}
                  height={C - 2}
                  rx={2}
                  fill={RAMP[binOf(d.cell.pairs)]}
                  className="cursor-pointer outline-none"
                  onClick={() => onChoose(d.row, d.col)}
                  onKeyDown={(e) => onKey(e, d)}
                  onMouseEnter={() => setHover(d)}
                  onMouseLeave={() => setHover(null)}
                  onFocus={() => setFocused(d)}
                  onBlur={() => setFocused(null)}
                />
              ))}

              {/* Outlines on top: the selected cell (both instances), the hovered
                  one, then the keyboard focus ring — its own state, so the
                  pointer never moves it. */}
              <g aria-hidden="true" pointerEvents="none" fill="none">
                {drawn.filter(isSelected).map((d) => (
                  <rect
                    key={`sel-${d.row}:${d.col}`}
                    data-testid="quran-map-selected"
                    x={xOf(d.col)}
                    y={yOf(d.row)}
                    width={C}
                    height={C}
                    rx={2}
                    stroke="#111827"
                    strokeWidth={2}
                  />
                ))}
                {hover && (
                  <rect
                    x={xOf(hover.col) - 1}
                    y={yOf(hover.row) - 1}
                    width={C + 2}
                    height={C + 2}
                    rx={3}
                    stroke="#0a5c4c"
                    strokeWidth={1.5}
                  />
                )}
                {focused && (
                  <rect
                    data-testid="quran-map-focus"
                    x={xOf(focused.col) - 2}
                    y={yOf(focused.row) - 2}
                    width={C + 4}
                    height={C + 4}
                    rx={3}
                    stroke="#111827"
                    strokeWidth={2}
                    strokeDasharray="3 2"
                  />
                )}
              </g>
            </svg>

            {hot && (
              <Tooltip
                x={xOf(hot.col)}
                y={yOf(hot.row)}
                size={size}
                text={label(hot)}
                scrollBox={scrollRef.current}
                matrixBox={matrixRef.current}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** The hovered/focused cell, named in full. Placed beside the cell, on the side
 *  with more room IN THE VISIBLE PART of the scroll box — at phone width the box
 *  shows a fraction of the matrix, so the cell's place in the whole matrix says
 *  nothing about where the tooltip would be cut off. The sticky label bands
 *  (row names on the left, column names at the bottom) cover part of that box
 *  and are not room. With no layout to read (no box
 *  yet, or a renderer that measures nothing), it falls back to the matrix. */
function Tooltip({
  x,
  y,
  size,
  text,
  scrollBox,
  matrixBox,
}: {
  x: number;
  y: number;
  size: number;
  text: string;
  scrollBox: HTMLElement | null;
  matrixBox: HTMLElement | null;
}) {
  let right = x < size / 2; // room on the right of the cell
  let below = y < size / 2;
  const view = scrollBox?.getBoundingClientRect();
  const grid = matrixBox?.getBoundingClientRect();
  if (view && grid && view.width > 0 && view.height > 0) {
    const left = grid.left + x; // the cell's edges, in viewport coordinates
    const top = grid.top + y;
    right = view.right - (left + C) > left - (view.left + LABEL);
    below = view.bottom - LABEL - (top + C) > top - view.top;
  }
  return (
    <div
      role="tooltip"
      lang="ar"
      data-testid="quran-map-tooltip"
      className="western-digits pointer-events-none absolute z-40 whitespace-nowrap rounded-md border border-gray-200 bg-white px-2.5 py-1.5 font-arabic text-sm text-gray-800 shadow-md"
      style={{
        left: right ? x + C + 6 : x - 6,
        top: below ? y + C + 6 : y - 6,
        transform: `translate(${right ? "0" : "-100%"}, ${below ? "0" : "-100%"})`,
      }}
    >
      {text}
    </div>
  );
}

/** The bins, in digits, with the empty swatch first: «no pair» is the card's
 *  own background, and the legend says so. */
function Legend() {
  const labels = BIN_FLOORS.map((lo, i) => {
    if (i === BIN_FLOORS.length - 1) return S.verseStudy.quranMap.legendAtLeast(lo);
    const hi = BIN_FLOORS[i + 1] - 1;
    return lo === hi ? String(lo) : `${lo}–${hi}`;
  });
  return (
    <div
      data-testid="quran-map-legend"
      className="western-digits flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-600"
    >
      <span lang="ar" className="font-arabic">
        {S.verseStudy.quranMap.legendTitle}
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="inline-block h-3 w-3 rounded-sm border border-gray-300 bg-white" />
        <span lang="ar">{S.verseStudy.quranMap.legendEmpty}</span>
      </span>
      {labels.map((text, i) => (
        <span key={text} className="inline-flex items-center gap-1">
          <span
            className="inline-block h-3 w-3 rounded-sm"
            style={{ backgroundColor: RAMP[i] }}
          />
          {/* A range keeps its digits in reading order («3–4», not «4–3»);
              the open-ended last bin is an Arabic phrase. */}
          <span dir={i === BIN_FLOORS.length - 1 ? undefined : "ltr"}>{text}</span>
        </span>
      ))}
    </div>
  );
}
