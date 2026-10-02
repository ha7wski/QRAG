"use client";

import { S } from "@/lib/strings";
import type { SurahMeta } from "@/lib/types";
import SelectBox from "@/components/SelectBox";

/**
 * The «سور القرآن» page heading and its caption. Shared by the main page and
 * the reading page, so choosing a surah keeps the reader under the same title.
 */
export function SurahsIntro() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-800">{S.reading.heading}</h1>
      <p className="mt-1 text-sm text-gray-500">{S.reading.caption}</p>
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
