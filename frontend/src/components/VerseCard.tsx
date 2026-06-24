import Link from "next/link";
import { BookOpen } from "lucide-react";
import ArabicText from "./ArabicText";
import type { Verse } from "@/lib/types";

/**
 * Displays a single verse with its reference, Arabic text, and metadata.
 * The surah name links to the full surah and the reference to the single-verse
 * page (deep-linking). Pass `linkable={false}` to render plain text — used on
 * the verse page itself, where self-links would be noise.
 */
export default function VerseCard({
  verse,
  linkable = true,
}: {
  verse: Verse;
  linkable?: boolean;
}) {
  const surahName = verse.surah_name_en || verse.surah_name_ar;
  return (
    <article className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <header className="mb-2 flex flex-wrap items-center gap-2 text-sm text-gray-600">
        <BookOpen className="h-4 w-4 text-brand" />
        {linkable ? (
          <Link
            href={`/surah/${verse.surah_number}`}
            className="font-medium text-gray-800 hover:text-brand-dark hover:underline"
          >
            {surahName} ({verse.surah_number}):{verse.ayah_number}
          </Link>
        ) : (
          <span className="font-medium text-gray-800">
            {surahName} ({verse.surah_number}):{verse.ayah_number}
          </span>
        )}
        {linkable ? (
          <Link
            href={`/verse/${verse.surah_number}/${verse.ayah_number}`}
            className="text-gray-400 hover:text-brand-dark hover:underline"
          >
            [{verse.id}]
          </Link>
        ) : (
          <span className="text-gray-400">[{verse.id}]</span>
        )}
        {verse.period && (
          <span className="rounded bg-brand-light px-2 py-0.5 text-xs text-brand-dark">
            {verse.period}
          </span>
        )}
        {verse.juz ? (
          <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
            Juz {verse.juz}
          </span>
        ) : null}
        {typeof verse.relevance_score === "number" && (
          <span className="ml-auto text-xs text-gray-400">
            score {verse.relevance_score.toFixed(4)}
          </span>
        )}
      </header>

      <ArabicText className="block text-right text-2xl leading-loose text-gray-900">
        {verse.text_ar_tashkil || verse.text_ar}
      </ArabicText>

      {verse.translation_fr && (
        <p className="mt-2 text-sm text-gray-700">{verse.translation_fr}</p>
      )}
      {verse.translation_en && (
        <p className="mt-1 text-sm text-gray-500">{verse.translation_en}</p>
      )}
    </article>
  );
}
