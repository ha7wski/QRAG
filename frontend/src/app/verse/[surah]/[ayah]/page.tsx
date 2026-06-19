"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Loader2, BookOpen } from "lucide-react";
import { getVerse } from "@/lib/api";
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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    getVerse(surah, ayah)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e?.message || "Failed to load verse"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [surah, ayah]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading verse…
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="space-y-3">
        <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error || "Verse not found."}
        </p>
        <Link href="/search" className="text-sm text-brand-dark hover:underline">
          ← Back to search
        </Link>
      </div>
    );
  }

  const { verse, context, prev_id, next_id } = data;
  const surahName = verse.surah_name_en || verse.surah_name_ar;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <Link
          href={`/surah/${verse.surah_number}`}
          className="flex items-center gap-1.5 text-sm text-brand-dark hover:underline"
        >
          <BookOpen className="h-4 w-4" />
          {surahName} (Surah {verse.surah_number})
        </Link>
        <span className="text-sm text-gray-400">Verse {verse.ayah_number}</span>
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
            <ArrowLeft className="h-4 w-4" /> {prev_id}
          </Link>
        ) : (
          <span />
        )}
        {next_id ? (
          <Link
            href={`/verse/${next_id.replace(":", "/")}`}
            className="flex items-center gap-1 text-brand-dark hover:underline"
          >
            {next_id} <ArrowRight className="h-4 w-4" />
          </Link>
        ) : (
          <span />
        )}
      </nav>
    </div>
  );
}
