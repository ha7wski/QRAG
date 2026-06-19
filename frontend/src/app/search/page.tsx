"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Loader2, Search as SearchIcon } from "lucide-react";
import { getSurahs, getVerse } from "@/lib/api";
import type { SurahMeta, VerseDetail } from "@/lib/types";
import ArabicText from "@/components/ArabicText";

// Context shown around the chosen verse: 3 before + 3 after (same surah).
const CONTEXT_WINDOW = 3;

export default function SearchPage() {
  const [surahs, setSurahs] = useState<SurahMeta[]>([]);
  const [surah, setSurah] = useState(1);
  const [ayah, setAyah] = useState(1);
  const [result, setResult] = useState<VerseDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load the surah list (Arabic names) for the picker.
  useEffect(() => {
    getSurahs()
      .then(setSurahs)
      .catch((e) => setError(e?.message || "Failed to load surah list"));
  }, []);

  const maxAyah = useMemo(
    () => surahs.find((s) => s.number === surah)?.ayah_count ?? 286,
    [surahs, surah],
  );

  function onSurahChange(n: number) {
    setSurah(n);
    const count = surahs.find((s) => s.number === n)?.ayah_count ?? 286;
    if (ayah > count) setAyah(count); // keep the ayah within the new surah
  }

  async function lookup() {
    if (loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await getVerse(surah, ayah, CONTEXT_WINDOW));
    } catch (e: any) {
      setError(e?.message || "Verse not found");
    } finally {
      setLoading(false);
    }
  }

  const main = result?.verse;
  const surahNameAr =
    surahs.find((s) => s.number === main?.surah_number)?.name_ar ??
    main?.surah_name_ar ??
    "";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-800">Look up a verse</h1>

      <div className="flex flex-wrap items-center gap-2">
        {/* Surah picker — Arabic names. */}
        <select
          value={surah}
          onChange={(e) => onSurahChange(Number(e.target.value))}
          dir="rtl"
          className="min-w-[220px] rounded-lg border border-gray-300 px-3 py-2 text-lg focus:border-brand focus:outline-none"
        >
          {surahs.map((s) => (
            <option key={s.number} value={s.number}>
              {s.number}. {s.name_ar}
            </option>
          ))}
        </select>

        {/* Ayah number. */}
        <input
          value={ayah}
          onChange={(e) => setAyah(Math.max(1, Number(e.target.value) || 1))}
          onKeyDown={(e) => e.key === "Enter" && lookup()}
          type="number"
          min={1}
          max={maxAyah}
          aria-label="Ayah number"
          className="w-28 rounded-lg border border-gray-300 px-3 py-2 focus:border-brand focus:outline-none"
        />
        <span className="text-sm text-gray-400">/ {maxAyah}</span>

        <button
          onClick={lookup}
          disabled={loading || surahs.length === 0}
          className="flex items-center gap-1 rounded-lg bg-brand px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <SearchIcon className="h-4 w-4" />
          )}
          Show verse
        </button>
      </div>

      {error && (
        <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {main && result && (
        <div className="space-y-3">
          {/* Condensed box: Arabic only, the chosen verse highlighted, with
              up to 3 verses of context on each side. */}
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2 text-sm text-gray-500">
              <span className="font-medium text-gray-700" dir="rtl">
                {surahNameAr}
              </span>
              <span>
                {main.surah_number}:{main.ayah_number}
              </span>
            </div>

            <div className="divide-y divide-gray-100">
              {result.context.map((v) => {
                const isMain = v.id === main.id;
                return (
                  <div
                    key={v.id}
                    className={`flex items-start gap-3 px-4 py-3 ${
                      isMain ? "bg-brand-light" : ""
                    }`}
                  >
                    <span
                      className={`mt-2 shrink-0 rounded-full px-2 py-0.5 text-xs ${
                        isMain
                          ? "bg-brand text-white"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {v.ayah_number}
                    </span>
                    <ArabicText
                      className={`block flex-1 text-right text-2xl leading-loose ${
                        isMain ? "font-bold text-gray-900" : "text-gray-800"
                      }`}
                    >
                      {v.text_ar}
                    </ArabicText>
                  </div>
                );
              })}
            </div>
          </div>

          <Link
            href={`/surah/${main.surah_number}`}
            className="inline-flex items-center gap-1 text-sm font-medium text-brand-dark hover:underline"
          >
            Open full Sourate page
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}
    </div>
  );
}
