import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import ArabicText from "@/components/ArabicText";
import { toArabicDigits } from "@/lib/arabicDigits";
import type { VerseDetail } from "@/lib/types";
import { S } from "@/lib/strings";

/**
 * A verse shown in its context: the surrounding āyāt of the same surah, Arabic
 * only, with the chosen verse highlighted and its number badged.
 *
 * Extracted verbatim from the "Find Verse context" tab so an expanded "Similar
 * Verses" card shows the SAME block — one rendering, two callers, no drift.
 *
 * `surahNameAr` is an override for the caller that has a better name to hand
 * (Find Verse context resolves it from the loaded surah list); otherwise the
 * verse's own `surah_name_ar` is used.
 */
export default function VerseContextCard({
  result,
  surahNameAr,
}: {
  result: VerseDetail;
  surahNameAr?: string;
}) {
  const main = result.verse;
  const name = surahNameAr || main.surah_name_ar || "";

  return (
    <div className="space-y-3">
      {/* Condensed box: Arabic only, the chosen verse highlighted, with
          up to 3 verses of context on each side. */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2 text-sm text-gray-500">
          <span className="font-medium text-gray-700">
            {name}
          </span>
          <span dir="ltr">
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
                    isMain ? "bg-brand text-white" : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {toArabicDigits(v.ayah_number)}
                </span>
                <ArabicText
                  className={`block flex-1 text-start text-2xl leading-loose ${
                    isMain ? "font-bold text-gray-900" : "text-gray-800"
                  }`}
                >
                  {v.text_ar_tashkil || v.text_ar}
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
        {S.verse.openSurah}
        <ArrowLeft className="h-4 w-4" />
      </Link>
    </div>
  );
}
