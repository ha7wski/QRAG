"use client";

import { useState } from "react";
import { ChartLine, ChartPie } from "lucide-react";
import FassilaAnalysisTab from "@/components/FassilaAnalysisTab";
import FassilaComparisonTab from "@/components/FassilaComparisonTab";
import PageIntro, { PageIntroToggle, usePageIntro } from "@/components/PageIntro";
import { S } from "@/lib/strings";

type Tab = "analysis" | "comparison";

const TABS: [Tab, string][] = [
  ["analysis", S.fassila.tabs.analysis],
  ["comparison", S.fassila.tabs.comparison],
];

// One icon per `S.intro.fassila.features` card, in the same order.
const INTRO_ICONS = [ChartLine, ChartPie] as const;

/**
 * «فواصل الآيات والسور» — the pausal rhyme-letter of the Qurʾān, read at two scales:
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
  const intro = usePageIntro("fassila");
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
        <div className="flex items-center justify-between gap-3">
          <h1 className="font-arabic text-2xl font-semibold text-gray-800">
            {S.nav.fassila}
          </h1>
          <PageIntroToggle open={intro.open} onToggle={intro.toggle} controls={intro.regionId} />
        </div>
        <p className="western-digits mt-1 text-sm text-gray-500">
          {S.fassila.caption}
        </p>
        {/* The gap above the intro folds with it, so a folded intro leaves no blank line. */}
        <div
          className={`${intro.open ? "mt-4" : "mt-0"} ${
            intro.ready ? "transition-[margin] duration-200 motion-reduce:transition-none" : ""
          }`}
        >
          <PageIntro
            id="fassila"
            summary={S.intro.fassila.summary}
            features={S.intro.fassila.features.map((f, i) => ({ ...f, icon: INTRO_ICONS[i] }))}
            open={intro.open}
            regionId={intro.regionId}
            ready={intro.ready}
          />
        </div>
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
