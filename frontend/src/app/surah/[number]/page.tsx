"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { getSurah } from "@/lib/api";
import type { SurahResponse } from "@/lib/types";
import ArabicText from "@/components/ArabicText";

// Render an integer with Arabic-Indic digits (٠-٩) for the in-text ayah markers.
const toArabicDigits = (n: number) =>
  String(n).replace(/\d/g, (d) => "٠١٢٣٤٥٦٧٨٩"[Number(d)]);

export default function SurahPage({
  params,
}: {
  params: { number: string };
}) {
  const number = Number(params.number);
  const [data, setData] = useState<SurahResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    getSurah(number)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e?.message || "Failed to load surah"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [number]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading surah…
      </div>
    );
  }
  if (error || !data) {
    return (
      <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
        {error || "Surah not found."}
      </p>
    );
  }

  return (
    <div className="space-y-5">
      <header className="space-y-1 border-b border-gray-200 pb-3">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold text-gray-800" dir="rtl">
            {data.surah_name_ar || data.surah_name_en}
          </h1>
          <span className="text-gray-400">Surah {data.surah_number}</span>
        </div>
        <p className="text-sm text-gray-500">
          {data.surah_name_en}
          {data.surah_name_fr ? ` · ${data.surah_name_fr}` : ""} · {data.ayah_count}{" "}
          verses
          {data.period ? ` · ${data.period}` : ""}
        </p>
      </header>

      {/* The whole surah as one continuous block (Arabic only): verses flow
          together, each followed by its ayah number, and the page scrolls to
          the end. */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <ArabicText className="block text-justify text-3xl leading-[2.6] text-gray-900">
          {data.verses.map((v) => (
            <span key={v.id}>
              {v.text_ar_tashkil || v.text_ar}
              <span className="mx-1.5 align-middle text-xl font-semibold text-brand-dark">
                ﴿{toArabicDigits(v.ayah_number)}﴾
              </span>{" "}
            </span>
          ))}
        </ArabicText>
      </div>

      <nav className="flex items-center justify-between border-t border-gray-200 pt-3 text-sm">
        {number > 1 ? (
          <Link
            href={`/surah/${number - 1}`}
            className="flex items-center gap-1 text-brand-dark hover:underline"
          >
            <ArrowLeft className="h-4 w-4" /> Surah {number - 1}
          </Link>
        ) : (
          <span />
        )}
        {number < 114 ? (
          <Link
            href={`/surah/${number + 1}`}
            className="flex items-center gap-1 text-brand-dark hover:underline"
          >
            Surah {number + 1} <ArrowRight className="h-4 w-4" />
          </Link>
        ) : (
          <span />
        )}
      </nav>
    </div>
  );
}
