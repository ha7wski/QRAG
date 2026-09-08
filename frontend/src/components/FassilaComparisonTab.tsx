"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { getFassilaOverview } from "@/lib/api";
import type {
  FassilaOverviewResponse,
  FassilaSurahSummary,
} from "@/lib/fassilaTypes";
import { fmtPercent } from "@/lib/arabicDigits";
import FassilaTile from "@/components/FassilaTile";
import FassilaDistributionPie from "@/components/FassilaDistributionPie";
import FassilaDiversityLine, {
  type DiversityPoint,
} from "@/components/FassilaDiversityLine";

/**
 * Tab 2 — "مقارنة السور": the 114 sūras categorized by how many distinct fawāṣil
 * they carry, from `GET /fassila/overview`.
 *
 * The component is only mounted on the first visit to this tab (see
 * `app/fassila/page.tsx`), so this mount effect *is* the "fetch once, lazily".
 *
 * Section order is deliberate — tiles, pie, list, then the two lines. The list
 * sits directly under the pie because filtering it is the pie's only effect: a
 * control whose result is three sections below reads as inert. The lines come
 * last precisely because the filter does **not** touch them.
 */
export default function FassilaComparisonTab() {
  const [data, setData] = useState<FassilaOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  /** Distinct-fāṣila count of the active category, or null when unfiltered. */
  const [active, setActive] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    getFassilaOverview()
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setError("تعذّر تحميل مقارنة السور"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const surahs = data?.surahs ?? [];

  const selection = useMemo(
    () =>
      active === null ? surahs : surahs.filter((s) => s.distinct_count === active),
    [surahs, active],
  );

  const selectionFawasil = useMemo(() => orderFawasil(selection), [selection]);

  // Length × diversity: ascending āya count, sūra number as tie-break. The
  // tie-break is required — 24 āya-count values are shared by more than one sūra,
  // two of them by five — or the polyline reorders between renders.
  const lengthPoints: DiversityPoint[] = useMemo(
    () =>
      [...surahs]
        .sort((a, b) => a.total_ayahs - b.total_ayahs || a.surah - b.surah)
        .map(toPoint((s) => s.total_ayahs)),
    [surahs],
  );

  // Rank × diversity: muṣḥaf order, 1 → 114.
  const rankPoints: DiversityPoint[] = useMemo(
    () => surahs.map(toPoint((s) => s.surah)),
    [surahs],
  );

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
        جارٍ التحميل…
      </div>
    );
  }

  if (error) {
    return <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
  }

  if (!data) return null;

  const maxSurahNames = data.max_distinct_surahs
    .map((n) => surahs.find((s) => s.surah === n)?.surah_name ?? "")
    .filter(Boolean)
    .join(" · ");

  const maxAyahs = Math.max(...surahs.map((s) => s.total_ayahs));

  return (
    <div className="space-y-6">
      {/* Tiles */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <FassilaTile label="عدد السور" value={String(data.surah_count)} />
        <FassilaTile
          label="متوسط الفواصل المميّزة"
          value={fmtPercent(data.mean_distinct)}
        />
        <FassilaTile label="سور بفاصلة واحدة" value={String(data.mono_fasila_count)} />
        <FassilaTile
          label="أقصى عدد فواصل"
          value={String(data.max_distinct)}
          hint={maxSurahNames}
        />
      </div>

      {/* Distribution */}
      <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-5 py-3">
          <h2 className="font-arabic text-lg font-semibold text-gray-800">
            توزّع السور حسب عدد الفواصل المميّزة
          </h2>
        </div>
        <div className="px-5 py-4">
          <FassilaDistributionPie
            buckets={data.buckets}
            surahs={surahs}
            active={active}
            onSelect={(d) => setActive((cur) => (cur === d ? null : d))}
          />
        </div>
      </section>

      {/* The list the pie filters — directly under it, on purpose. */}
      <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-5 py-3">
          <h2 className="font-arabic text-lg font-semibold text-gray-800">السور</h2>
        </div>

        {/* Scrolls in both axes inside the card — 114 rows vertically, and four
            columns horizontally on a narrow screen — so the page body never
            scrolls sideways. */}
        <div className="max-h-[26rem] overflow-x-auto overflow-y-auto px-5 py-2">
          <table className="w-full min-w-[26rem] border-collapse text-sm">
            <thead>
              <tr className="text-gray-500">
                {["السورة", "الآيات", "فواصل مميّزة", "الفاصلة الغالبة"].map((h) => (
                  <th
                    key={h}
                    className="border-b border-gray-200 px-3 py-1.5 text-start font-medium"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {selection.map((s) => (
                <tr key={s.surah}>
                  <td className="border-b border-gray-100 px-3 py-1.5">
                    <span className="western-digits tabular-nums text-gray-400">
                      {s.surah}
                    </span>{" "}
                    <span className="font-arabic text-base text-gray-900">
                      {s.surah_name}
                    </span>
                  </td>
                  <td className="western-digits border-b border-gray-100 px-3 py-1.5 tabular-nums text-gray-600">
                    {s.total_ayahs}
                  </td>
                  {/* The letters themselves, not their count: filtered by category
                      every row would otherwise repeat the same number, while the
                      letters are what actually differ. Order is `fawasil`'s own —
                      descending occurrence — so the dominant one reads first. */}
                  <td className="border-b border-gray-100 px-3 py-1.5">
                    <span className="font-arabic text-lg leading-none text-gray-900">
                      {s.fawasil.join(" ")}
                    </span>
                  </td>
                  <td className="border-b border-gray-100 px-3 py-1.5">
                    <span className="font-arabic text-lg font-bold text-gray-900">
                      {s.dominant?.letter ?? "—"}
                    </span>{" "}
                    <span className="western-digits tabular-nums text-gray-500">
                      {s.dominant ? `${fmtPercent(s.dominant.percentage)}%` : ""}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Status line: the category, then the fawāṣil the selection covers.
            The letters are emitted most-frequent first, which in this RTL box
            puts the most frequent on the RIGHT — no reversal anywhere. */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-gray-100 px-5 py-3 text-sm text-gray-600">
          <span className="western-digits tabular-nums">
            {active === null ? (
              <>
                <b className="text-gray-900">{selection.length}</b> سورة · جميع الفئات
              </>
            ) : (
              <>
                <b className="text-gray-900">{selection.length}</b> سورة بها{" "}
                <b className="text-gray-900">{active}</b> فاصلة مميّزة
              </>
            )}
          </span>
          {selectionFawasil.length > 0 && (
            <span className="font-arabic text-2xl leading-none text-gray-900">
              ( {selectionFawasil.join(" ")} )
            </span>
          )}
        </div>
      </section>

      {/* Length × diversity */}
      <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-5 py-3">
          <h2 className="font-arabic text-lg font-semibold text-gray-800">
            طول السورة × تنوّع الفواصل
          </h2>
        </div>
        <div className="px-5 py-4">
          <FassilaDiversityLine
            points={lengthPoints}
            xMax={maxAyahs}
            ariaLabel="طول السورة × تنوّع الفواصل"
          />
        </div>
      </section>

      {/* Rank × diversity */}
      <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-5 py-3">
          <h2 className="font-arabic text-lg font-semibold text-gray-800">
            ترتيب السورة × تنوّع الفواصل
          </h2>
        </div>
        <div className="px-5 py-4">
          <FassilaDiversityLine
            points={rankPoints}
            xMax={data.surah_count}
            ariaLabel="ترتيب السورة × تنوّع الفواصل"
          />
        </div>
      </section>
    </div>
  );
}

const toPoint =
  (x: (s: FassilaSurahSummary) => number) =>
  (s: FassilaSurahSummary): DiversityPoint => ({
    x: x(s),
    y: s.distinct_count,
    surah: s.surah,
    name: s.surah_name,
    ayahs: s.total_ayahs,
  });

/**
 * The fawāṣil a selection of sūras covers, most frequent first.
 *
 * "Frequent" counts **sūras**, not āyāt: `ا(8)` means eight of these sūras rhyme
 * on `ا` — the only reading `fawasil` (a list of letters, no per-letter tallies)
 * can support. Ties break on first appearance scanning the selection in muṣḥaf
 * order, mirroring `analyse_surah`'s own `first_appearance` tie-break, so the
 * order is stable across renders.
 */
function orderFawasil(selection: FassilaSurahSummary[]): string[] {
  const tally = new Map<string, number>();
  const first = new Map<string, number>();
  for (const s of selection) {
    for (const letter of s.fawasil) {
      tally.set(letter, (tally.get(letter) ?? 0) + 1);
      if (!first.has(letter)) first.set(letter, s.surah);
    }
  }
  return [...tally.keys()].sort(
    (a, b) => tally.get(b)! - tally.get(a)! || first.get(a)! - first.get(b)!,
  );
}
