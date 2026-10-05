"use client";

import { Loader2 } from "lucide-react";
import type { Verse } from "@/lib/types";
import { S } from "@/lib/strings";
import ArabicText from "@/components/ArabicText";

/**
 * The verse, common-part and root-chip markup the «الآيات المتشابهات» views
 * share: the intra-surah mode (`SurahSimilarity`) and the surah × surah map
 * (`QuranSimilarityMap`) render a close verse — and the part it shares with its
 * pair, `<mark>`ed with its word count — the same way, so the markup lives here
 * once rather than being copied into each. No score is ever rendered — the order
 * of the list carries the ranking.
 */

/** The spinner line under a pending similarity request. */
export function LoadingLine() {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-500">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span lang="ar" className="font-arabic">
        {S.verseStudy.surahSimilar.loading}
      </span>
    </div>
  );
}

/**
 * The vocalized text, with `span` — the common part of a close pair, as
 * half-open CHARACTER offsets into the DISPLAYED `text_ar_tashkil` (Basmala
 * stripped), computed by the build — wrapped in a `<mark>`. The offsets address
 * the vocalized text only: a verse that falls back to `text_ar`, or a span
 * outside the text, is rendered unmarked rather than marked at the wrong place.
 */
function MarkedText({ verse, span }: { verse: Verse; span?: [number, number] | null }) {
  const text = verse.text_ar_tashkil || verse.text_ar;
  if (!span || !verse.text_ar_tashkil) return <>{text}</>;
  const [start, end] = span;
  const valid =
    Number.isInteger(start) &&
    Number.isInteger(end) &&
    start >= 0 &&
    start < end &&
    end <= text.length;
  if (!valid) return <>{text}</>;
  return (
    <>
      {text.slice(0, start)}
      <mark
        data-testid="common-part"
        className="rounded-sm bg-brand-light text-brand-dark"
      >
        {text.slice(start, end)}
      </mark>
      {text.slice(end)}
    </>
  );
}

/** A vocalized verse with its number badge — and its surah's name when the
 *  verse may come from another surah than the one on screen. `span`, when
 *  given, marks the verse's common part with its pair (see `MarkedText`). */
export function VerseText({
  verse,
  withSurah = false,
  span,
}: {
  verse: Verse;
  withSurah?: boolean;
  span?: [number, number] | null;
}) {
  return (
    <ArabicText className="block text-2xl leading-loose text-gray-900">
      <MarkedText verse={verse} span={span} />{" "}
      <span className="western-digits align-middle text-sm text-gray-400">
        ﴿{withSurah ? `${verse.surah_name_ar} ${verse.ayah_number}` : verse.ayah_number}﴾
      </span>
    </ArabicText>
  );
}

/** A whole-verse button that opens it in «الآية في سياقها». */
export function VerseCardButton({
  verse,
  openInContext,
  highlighted = false,
  withSurah = false,
  span,
}: {
  verse: Verse;
  openInContext: (surah: number, ayah: number) => void;
  highlighted?: boolean;
  withSurah?: boolean;
  /** The common part to mark in the verse's vocalized text. */
  span?: [number, number] | null;
}) {
  return (
    <button
      type="button"
      onClick={() => openInContext(verse.surah_number, verse.ayah_number)}
      title={S.verseStudy.openInContext}
      className={`block w-full p-4 text-start transition hover:bg-brand-light/50 ${
        highlighted ? "rounded-lg border border-brand/40 bg-brand-light/40" : ""
      }`}
    >
      <VerseText verse={verse} withSurah={withSurah} span={span} />
    </button>
  );
}

/** «N كلمات مشتركة» — the matched words of a close pair's common part, under
 *  its verse(s). Renders nothing when the pair has no common part. */
export function SharedWords({ words }: { words: number | null | undefined }) {
  if (words == null) return null;
  return (
    <div
      lang="ar"
      data-testid="shared-words"
      className="western-digits border-t border-gray-100 px-4 py-2 font-arabic text-sm text-gray-600"
    >
      {S.verseStudy.surahSimilar.sharedWords(words)}
    </div>
  );
}

/** The content roots two close verses share, as Arabic chips under a label.
 *  Renders nothing when there are none. */
export function RootChips({ roots }: { roots: string[] }) {
  if (roots.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5 border-t border-gray-100 px-4 py-2">
      <span className="font-arabic text-xs text-gray-500">
        {S.verseStudy.surahSimilar.sharedRoots}
      </span>
      {roots.map((r) => (
        <span
          key={r}
          lang="ar"
          className="rounded-full border border-brand/30 bg-brand-light px-2.5 py-0.5 font-arabic text-base tracking-widest text-brand-dark"
        >
          {r}
        </span>
      ))}
    </div>
  );
}
