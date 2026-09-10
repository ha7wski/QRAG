"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Loader2, BookOpen } from "lucide-react";
import { getVerse, statusOf, detailOf } from "@/lib/api";
import { S, forStatus } from "@/lib/strings";
import FailureNote, { type Failure } from "@/components/FailureNote";
import type { VerseDetail } from "@/lib/types";
import VerseCard from "@/components/VerseCard";

export default function VersePage({
  params,
}: {
  params: { surah: string; ayah: string };
}) {
  const surah = Number(params.surah);
  const ayah = Number(params.ayah);
  const [data, setData] = useState<VerseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Failure | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    getVerse(surah, ayah)
      .then((d) => !cancelled && setData(d))
      .catch(
        (e) =>
          !cancelled &&
          setError({
            text: forStatus(statusOf(e), "verse"),
            detail: detailOf(e),
          }),
      )
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [surah, ayah]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" /> {S.verse.loadingVerse}
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="space-y-3">
        <FailureNote
          failure={error ?? { text: S.errors.verseNotFound }}
          className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
        />
        <Link
          href={`/verse-study?surah=${surah}&ayah=${ayah}`}
          className="flex items-center gap-1 text-sm text-brand-dark hover:underline"
        >
          <ArrowRight className="h-4 w-4" /> {S.verse.backToStudy}
        </Link>
      </div>
    );
  }

  const { verse, context, prev_id, next_id } = data;
  // The same reversal `VerseCard` needed: the Arabic name is the required
  // field and the transliteration the optional one, yet this led with the
  // transliteration — so a deep link opened in Latin.
  const surahName = verse.surah_name_ar || verse.surah_name_en;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <Link
          href={`/surah/${verse.surah_number}`}
          className="flex items-center gap-1.5 text-sm text-brand-dark hover:underline"
        >
          <BookOpen className="h-4 w-4" />
          {surahName}{" "}
          {/* The reference style the cards already use. The brackets are
              bidi-mirrored, so the numeric part is isolated rather than left
              to resolve against whichever script precedes it. */}
          <span dir="ltr">({verse.surah_number})</span>
        </Link>
        {/* Western digits, matching the reference beside it rather than the
            Arabic-Indic of a reading context: this header is chrome about a
            verse, not the verse (task 3.4c). */}
        <span className="western-digits text-sm text-gray-400">
          {S.verse.ayahLabel(verse.ayah_number)}
        </span>
      </div>

      <VerseCard verse={verse} linkable={false} />

      {context.length > 1 && (
        <section className="space-y-2">
          <h2 className="text-xs font-medium uppercase tracking-wide text-gray-400">
            In context
          </h2>
          {context.map((v) => (
            <div
              key={v.id}
              className={v.id === verse.id ? "ring-2 ring-brand/30 rounded-lg" : ""}
            >
              <VerseCard verse={v} linkable={v.id !== verse.id} />
            </div>
          ))}
        </section>
      )}

      <nav className="flex items-center justify-between border-t border-gray-200 pt-3 text-sm">
        {prev_id ? (
          <Link
            href={`/verse/${prev_id.replace(":", "/")}`}
            className="flex items-center gap-1 text-brand-dark hover:underline"
          >
            <ArrowRight className="h-4 w-4" />{" "}
            <span dir="ltr">{prev_id}</span>
          </Link>
        ) : (
          <span />
        )}
        {next_id ? (
          <Link
            href={`/verse/${next_id.replace(":", "/")}`}
            className="flex items-center gap-1 text-brand-dark hover:underline"
          >
            <span dir="ltr">{next_id}</span>{" "}
            <ArrowLeft className="h-4 w-4" />
          </Link>
        ) : (
          <span />
        )}
      </nav>
    </div>
  );
}
