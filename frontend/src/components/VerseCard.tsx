import Link from "next/link";
import { BookOpen } from "lucide-react";
import ArabicText from "./ArabicText";
import type { Verse } from "@/lib/types";
import { S } from "@/lib/strings";

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
  // The Arabic name is the required field and the Latin transliteration the
  // optional one, yet this preferred the transliteration — so the most-rendered
  // component in the product led with Latin. Reversed.
  const surahName = verse.surah_name_ar || verse.surah_name_en;

  // `(2):255` — the brackets are bidi-mirrored, so the numeric part is isolated
  // rather than left to resolve against whichever script precedes it.
  const reference = (
    <>
      {surahName}{" "}
      <span dir="ltr">
        ({verse.surah_number}):{verse.ayah_number}
      </span>
    </>
  );

  // Mapped, never rendered raw: the corpus emits the transliterations
  // `makkiyya` / `madani`, which are machine ids as far as the reader is
  // concerned. An unknown value renders nothing rather than leaking the id.
  const period = verse.period
    ? (S.verse.period as Record<string, string | undefined>)[verse.period]
    : undefined;

  return (
    <article className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <header className="mb-2 flex flex-wrap items-center gap-2 text-sm text-gray-600">
        <BookOpen className="h-4 w-4 text-brand" />
        {linkable ? (
          <Link
            href={`/surah/${verse.surah_number}`}
            className="font-medium text-gray-800 hover:text-brand-dark hover:underline"
          >
            {reference}
          </Link>
        ) : (
          <span className="font-medium text-gray-800">{reference}</span>
        )}
        {linkable ? (
          <Link
            href={`/verse/${verse.surah_number}/${verse.ayah_number}`}
            dir="ltr"
            className="text-gray-400 hover:text-brand-dark hover:underline"
          >
            [{verse.id}]
          </Link>
        ) : (
          <span dir="ltr" className="text-gray-400">
            [{verse.id}]
          </span>
        )}
        {period && (
          <span className="rounded bg-brand-light px-2 py-0.5 font-arabic text-xs text-brand-dark">
            {period}
          </span>
        )}
        {verse.juz ? (
          <span className="western-digits rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
            {S.verse.juz(String(verse.juz))}
          </span>
        ) : null}
        {typeof verse.relevance_score === "number" && (
          <span className="western-digits me-auto text-xs text-gray-400">
            {S.verse.score} {verse.relevance_score.toFixed(4)}
          </span>
        )}
      </header>

      <ArabicText className="block text-start text-2xl leading-loose text-gray-900">
        {verse.text_ar_tashkil || verse.text_ar}
      </ArabicText>

      {/* Translations are content whose script is not ours to know. `dir="auto"`
          lets the bidi algorithm derive the run from its first strong character
          instead of inheriting RTL, and `lang` keeps a screen reader from
          reading French or English with an Arabic voice (design D19). */}
      {verse.translation_fr && (
        <p dir="auto" lang="fr" className="mt-2 text-sm text-gray-700">
          {verse.translation_fr}
        </p>
      )}
      {verse.translation_en && (
        <p dir="auto" lang="en" className="mt-1 text-sm text-gray-500">
          {verse.translation_en}
        </p>
      )}
    </article>
  );
}
