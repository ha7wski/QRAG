"use client";

import Link from "next/link";
import { ChevronDown, ChevronUp, ListTree, Type } from "lucide-react";
import type { RootIndexEntry } from "@/lib/types";
import { NOUNS, S } from "@/lib/strings";
import { useCachedState } from "@/lib/pageCache";
import ArabicText from "./ArabicText";
import Counted from "./Counted";

/**
 * One root of «فهرس الجذور». The root and its three distinct counts are always
 * visible; the rest is folded behind the header, because a letter renders ~100
 * cards and the reader scans roots before reading one. Unfolded: the project's
 * mechanical letter reading (or why there is none) → «السور» → «المواضع» (the
 * root's distinct written forms) → two green links: «الكلمة في الآيات», which
 * lists every āya of the root in full, and «تحليل لساني» to its left.
 *
 * Every figure is the backend's `root_forms` output, rendered as-is: the card
 * counts nothing itself, so it cannot disagree with «الكلمة في الآيات» or
 * «تحليل اللسان» for the same root.
 *
 * The reading is shown under `S.lexical.assemblyLabel`, the label `/lexical`
 * already puts on the same assembly, and nothing else of Islambouli's is
 * rendered here — not his published sentence, not the cultural stage. When
 * `readingsAvailable` is false the page carries one notice and the card shows
 * no reading block at all, so a lock failure is never mistaken for a refusal.
 */
export default function RootCard({
  entry,
  readingsAvailable,
}: {
  entry: RootIndexEntry;
  readingsAvailable: boolean;
}) {
  // Cached per root, so a card the reader unfolded is still unfolded when they
  // come back to the index from another tab.
  const [open, setOpen] = useCachedState(`roots.card.open.${entry.root}`, false);
  const word = encodeURIComponent(entry.root);
  const detailsId = `root-details-${entry.root}`;

  return (
    <article
      data-testid="root-card"
      className="rounded-lg border border-gray-200 bg-white shadow-sm"
    >
      {/* A heading holding the fold button, not the reverse: a button's content
          is phrasing only, so the root stays a real heading for navigation. */}
      <h3>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-controls={detailsId}
          aria-label={open ? S.roots.collapseCard(entry.root) : S.roots.expandCard(entry.root)}
          className="flex w-full flex-wrap items-center justify-between gap-x-4 gap-y-1 p-4 text-start"
        >
          <span className="flex items-center gap-2">
            {open ? (
              <ChevronUp className="h-5 w-5 text-gray-400" />
            ) : (
              <ChevronDown className="h-5 w-5 text-gray-400" />
            )}
            <span className="text-2xl font-semibold text-brand-dark">
              <ArabicText>{entry.root}</ArabicText>
            </span>
          </span>
          <span className="western-digits text-sm font-normal text-gray-600">
            <Counted n={entry.words} forms={NOUNS.mawdi} /> ·{" "}
            <Counted n={entry.ayat} forms={NOUNS.aya} /> ·{" "}
            <Counted n={entry.surahs} forms={NOUNS.surah} />
          </span>
        </button>
      </h3>

      {open && (
        <div id={detailsId} className="space-y-3 px-4 pb-4">
          {readingsAvailable &&
            (entry.reading ? (
              <div
                data-testid="root-reading"
                className="rounded border border-dashed border-gray-300 p-3"
              >
                <div className="font-arabic text-xs font-semibold text-gray-600">
                  {S.lexical.assemblyLabel}
                </div>
                <p className="mt-1 text-lg leading-relaxed text-gray-800">
                  <ArabicText>{entry.reading}</ArabicText>
                </p>
              </div>
            ) : entry.reading_refusal ? (
              <p data-testid="root-refusal" className="font-arabic text-sm text-gray-600">
                {S.lexical.assemblyRefused} {entry.reading_refusal}
              </p>
            ) : null)}

          <div data-testid="root-surahs" className="flex flex-wrap items-center gap-1.5">
            <span className="font-arabic text-xs text-gray-500">{S.roots.surahsLabel}</span>
            {entry.surah_list.map((s) => (
              <Link
                key={s.number}
                href={`/surah/${s.number}`}
                className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-sm text-gray-700 hover:border-brand hover:text-brand-dark"
              >
                <ArabicText>{s.name_ar}</ArabicText>
              </Link>
            ))}
          </div>

          <div data-testid="root-forms" className="flex flex-wrap items-center gap-1.5">
            <span className="font-arabic text-xs text-gray-500">{S.roots.formsLabel}</span>
            {entry.forms.map((f) => (
              <span
                key={f}
                className="rounded border border-gray-200 px-2 py-0.5 text-base text-gray-800"
              >
                <ArabicText>{f}</ArabicText>
              </span>
            ))}
          </div>

          <footer className="flex flex-wrap gap-2 border-t border-gray-100 pt-3">
            <Link
              href={`/verse-study?word=${word}`}
              className="flex items-center gap-1 rounded-lg bg-brand px-3 py-1 font-arabic text-sm text-white hover:bg-brand-dark"
            >
              <ListTree className="h-4 w-4" />
              {S.roots.openVerseStudy}
            </Link>
            {/* Second in source order, so it sits to the LEFT under RTL. */}
            <Link
              href={`/lexical?word=${word}`}
              className="flex items-center gap-1 rounded-lg bg-brand px-3 py-1 font-arabic text-sm text-white hover:bg-brand-dark"
            >
              <Type className="h-4 w-4" />
              {S.roots.openLexical}
            </Link>
          </footer>
        </div>
      )}
    </article>
  );
}
