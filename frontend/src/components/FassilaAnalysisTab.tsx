"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { getFassila, getSurahs } from "@/lib/api";
import type { FassilaResponse } from "@/lib/fassilaTypes";
import type { SurahMeta } from "@/lib/types";
import { fmtPercent } from "@/lib/numerals";
import { count, NOUNS } from "@/lib/strings";
import FassilaBars from "@/components/FassilaBars";
import FassilaLine from "@/components/FassilaLine";
import FassilaTile from "@/components/FassilaTile";

/**
 * Tab 1 — "تحليل الفواصل": one sūra's fawāṣil read two ways, a frequency
 * distribution (bars) and a sequence across the sūra (line).
 *
 * Lifted verbatim out of `app/fassila/page.tsx` when the page gained its tab
 * shell; the page header now lives in the shell, everything else is unchanged.
 * Derivation lives server-side in `analysis/fassila.py`; this only renders
 * `GET /fassila/{surah}`.
 */
export default function FassilaAnalysisTab() {
  const [surahs, setSurahs] = useState<SurahMeta[]>([]);
  const [surah, setSurah] = useState(12); // Yūsuf — a clean, exclusion-free default
  const [data, setData] = useState<FassilaResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getSurahs()
      .then(setSurahs)
      .catch(() => setError("تعذّر تحميل قائمة السور"));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getFassila(surah)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setError("تعذّر تحميل تحليل الفواصل"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [surah]);

  return (
    <div className="space-y-6">
      {/* Sūra picker */}
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="surah" className="text-sm text-gray-500">
          السورة :
        </label>
        <button
          type="button"
          aria-label="السورة السابقة"
          disabled={surah <= 1}
          onClick={() => setSurah((s) => Math.max(1, s - 1))}
          className="rounded-lg border border-gray-300 p-2 text-gray-700 disabled:opacity-40"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <select
          id="surah"
          value={surah}
          onChange={(e) => setSurah(Number(e.target.value))}
          className="min-w-[240px] rounded-lg border border-gray-300 px-3 py-2 font-arabic text-base focus:border-brand focus:outline-none"
        >
          {surahs.map((s) => (
            <option key={s.number} value={s.number}>
              {s.number} · {s.name_ar} — {count(s.ayah_count, NOUNS.aya)}
            </option>
          ))}
        </select>
        <button
          type="button"
          aria-label="السورة التالية"
          disabled={surah >= 114}
          onClick={() => setSurah((s) => Math.min(114, s + 1))}
          className="rounded-lg border border-gray-300 p-2 text-gray-700 disabled:opacity-40"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        {loading && <Loader2 className="h-4 w-4 animate-spin text-gray-400" />}
      </div>

      {error && (
        <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {data && (
        <>
          {/* Summary tiles */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <FassilaTile label="عدد الآيات" value={String(data.total_ayahs)} />
            <FassilaTile label="فواصل مميّزة" value={String(data.distinct_count)} />
            {/* Letter only — its count and share are right below, in the bars. */}
            <FassilaTile
              label="الفاصلة الغالبة"
              value={data.dominant?.letter ?? "—"}
              arabicValue
            />
          </div>

          {data.excluded_ayahs > 0 && (
            <p className="text-sm text-gray-500">
              استُبعدت من التحليل{" "}
              <span className="western-digits">
                {count(data.excluded_ayahs, NOUNS.aya)}
              </span>{" "}
              من الحروف المقطّعة ·{" "}
              <span className="western-digits">
                {count(data.analysed_ayahs, NOUNS.ayaMuhallala)}
              </span>
            </p>
          )}

          {/* Distribution */}
          <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="border-b border-gray-100 px-5 py-3">
              <h2 className="font-arabic text-lg font-semibold text-gray-800">
                عدد الآيات لكل فاصلة
              </h2>
            </div>
            <div className="px-5 py-3">
              <FassilaBars counts={data.counts} analysed={data.analysed_ayahs} />
            </div>
          </section>

          {/* Sequence */}
          <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="border-b border-gray-100 px-5 py-3">
              <h2 className="font-arabic text-lg font-semibold text-gray-800">
                تتابع الفواصل عبر الآيات
              </h2>
            </div>
            <div className="px-5 py-4">
              <FassilaLine
                ayahs={data.ayahs}
                order={data.first_appearance}
                counts={data.counts}
                totalAyahs={data.total_ayahs}
              />
            </div>
          </section>

          {/* Methodology */}
          <details className="rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
            <summary className="cursor-pointer font-arabic font-semibold text-gray-800">
              المنهجية والمصادر
            </summary>
            <div className="western-digits mt-3 space-y-3 text-sm leading-relaxed text-gray-600">
              <p>
                الفاصلة هي آخر حرف من آخر كلمة في كل آية، بصيغة الوقف: تُحذف
                الحركات، ويُهمَل التنوين، وتُقلب ة ← ه و ى ← ا، وتُقرأ الألف
                الخنجرية ٰ ← ا. يعرض المحور العمودي الفواصل المميّزة حسب ترتيب أول
                ظهور لها (الأول في الأسفل)، ويبدأ المحور الأفقي من 0.
              </p>
              <p>
                تُستبعَد الآيات المكوّنة من حروف مقطّعة فقط (الم، المص، كهيعص، طه،
                طسم، يس، حم، عسق) من التحليل: 20 آية في 19 سورة. أمّا الر، المر،
                طس، ص، ق، ن فلا تُستبعَد لأنّ آيتها تستمرّ بكلمات أخرى فتحمل فاصلة
                حقيقية.
              </p>
              <p>
                المصدر: الرسم العثماني كما في مدوّنة القرآن الصرفية (QAC) · 6236
                آية · 6216 آية محلَّلة.
              </p>

              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="text-gray-500">
                    <th className="border-b border-gray-200 px-3 py-1.5 text-start font-medium">
                      الفاصلة
                    </th>
                    <th className="border-b border-gray-200 px-3 py-1.5 text-start font-medium">
                      عدد الآيات
                    </th>
                    <th className="border-b border-gray-200 px-3 py-1.5 text-start font-medium">
                      النسبة
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.counts.map((c) => (
                    <tr key={c.letter}>
                      <td className="border-b border-gray-100 px-3 py-1.5 font-arabic text-lg font-bold text-gray-900">
                        {c.letter}
                      </td>
                      <td className="western-digits border-b border-gray-100 px-3 py-1.5 tabular-nums">
                        {c.count}
                      </td>
                      <td className="western-digits border-b border-gray-100 px-3 py-1.5 tabular-nums">
                        {fmtPercent(c.percentage)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </div>
  );
}
