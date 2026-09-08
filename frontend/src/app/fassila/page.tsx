"use client";

import { useState } from "react";
import FassilaAnalysisTab from "@/components/FassilaAnalysisTab";
import FassilaComparisonTab from "@/components/FassilaComparisonTab";

type Tab = "analysis" | "comparison";

const TABS: [Tab, string][] = [
  ["analysis", "تحليل الفواصل"],
  ["comparison", "مقارنة السور"],
];

/**
 * "الفواصل" — the pausal rhyme-letter of the Qurʾān, read at two scales:
 * within one sūra (tab 1) and across all 114 (tab 2).
 *
 * The page is entirely in Arabic and RTL. Derivation lives server-side in
 * `analysis/fassila.py`; the tabs only render what the API returns.
 *
 * Two mounting rules, and they pull in opposite directions:
 *
 *   - the comparison tab is **not mounted until first activated**, so a visitor
 *     who only wants one sūra never pays for `GET /fassila/overview`;
 *   - once mounted, **both tabs stay mounted** (hidden, not unmounted), so the
 *     sūra selected in tab 1 and the category filtered in tab 2 survive every
 *     later switch. Same idiom as `app/verse-study/page.tsx`.
 */
export default function FassilaPage() {
  const [tab, setTab] = useState<Tab>("analysis");
  // Latches on the first visit to tab 2 and never resets — that single visit is
  // what mounts the comparison tab, and its mount is what fetches the overview.
  const [comparisonOpened, setComparisonOpened] = useState(false);

  const select = (key: Tab) => {
    setTab(key);
    if (key === "comparison") setComparisonOpened(true);
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-arabic text-2xl font-semibold text-gray-800">
          الفواصل في القرآن الكريم
        </h1>
        <p className="western-digits mt-1 text-sm text-gray-500">
          الفاصلة: آخر حرف من كل آية وقفًا · مع استبعاد الحروف المقطّعة · 114 سورة
        </p>
      </header>

      {/* Tabs */}
      <div className="flex gap-6 border-b border-gray-200">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => select(key)}
            className={`-mb-px border-b-2 px-1 py-2 font-arabic text-base font-medium transition ${
              tab === key
                ? "border-brand text-brand-dark"
                : "border-transparent text-gray-500 hover:text-gray-800"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className={tab === "analysis" ? "" : "hidden"}>
        <FassilaAnalysisTab />
      </div>
      {comparisonOpened && (
        <div className={tab === "comparison" ? "" : "hidden"}>
          <FassilaComparisonTab />
        </div>
      )}
    </div>
  );
}
