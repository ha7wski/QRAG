"use client";

import { BookOpen, Highlighter, Layers } from "lucide-react";
import { S } from "@/lib/strings";
import type { SurahMeta } from "@/lib/types";
import SelectBox from "@/components/SelectBox";
import PageIntro, { PageIntroToggle, usePageIntro } from "@/components/PageIntro";

// One icon per `S.intro.surah.features` card, in the same order.
const INTRO_ICONS = [BookOpen, Layers, Highlighter] as const;

/**
 * The «سور القرآن» page heading, its caption and the page introduction. Shared
 * by the main page and the reading page, so choosing a surah keeps the reader
 * under the same title — and the intro's folded state under one id.
 */
export function SurahsIntro() {
  const intro = usePageIntro("surah");
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-gray-800">{S.reading.heading}</h1>
        <PageIntroToggle open={intro.open} onToggle={intro.toggle} controls={intro.regionId} />
      </div>
      <p className="mt-1 text-sm text-gray-500">{S.reading.caption}</p>
      {/* The gap above the intro folds with it, so a folded intro leaves no blank line. */}
      <div
        className={`${intro.open ? "mt-4" : "mt-0"} ${
          intro.ready ? "transition-[margin] duration-200 motion-reduce:transition-none" : ""
        }`}
      >
        <PageIntro
          id="surah"
          summary={S.intro.surah.summary}
          features={S.intro.surah.features.map((f, i) => ({ ...f, icon: INTRO_ICONS[i] }))}
          open={intro.open}
          regionId={intro.regionId}
          ready={intro.ready}
        />
      </div>
    </div>
  );
}

/**
 * The surah picker, one control for both pages (its arrow is `SelectBox`'s).
 *
 * `value` is the open surah, or "" on the main page (a placeholder option is
 * then shown). `current` names the open surah while the list is missing, so
 * the control never reads as empty.
 */
export default function SurahPicker({
  surahs,
  failed,
  value,
  current,
  onChoose,
}: {
  surahs: SurahMeta[] | null;
  failed: boolean;
  value: number | "";
  current?: string;
  onChoose: (n: number) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <label htmlFor="surah-picker" className="text-lg text-gray-700">
        {S.reading.pickerLabel}
      </label>
      <SelectBox
        id="surah-picker"
        value={value}
        disabled={!surahs && value === ""}
        onChange={(e) => e.target.value && onChoose(Number(e.target.value))}
        className={`western-digits w-52 py-1.5 font-arabic text-base ${
          value === "" ? "text-gray-400" : "text-gray-900"
        }`}
      >
        {value === "" && (
          <option value="" disabled>
            {surahs ? S.reading.pickerPlaceholder : S.reading.loadingSurahs}
          </option>
        )}
        {(surahs ?? []).map((s) => (
          <option key={s.number} value={s.number} className="text-gray-900">
            {S.reading.option(s.number, s.name_ar ?? "")}
          </option>
        ))}
        {!surahs && value !== "" && (
          <option value={value}>{S.reading.option(value, current ?? "")}</option>
        )}
      </SelectBox>
      {failed && <span className="text-sm text-red-700">{S.reading.surahsFailed}</span>}
    </div>
  );
}
