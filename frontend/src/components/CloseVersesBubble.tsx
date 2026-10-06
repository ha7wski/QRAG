"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import type { AyahAnnotation } from "@/lib/api";
import type { Verse } from "@/lib/types";
import { S } from "@/lib/strings";
import { crossPartners, groupPartners } from "@/lib/annotations";
import { SharedWords, VerseText } from "@/components/SimilarVerseParts";

/** Marks an element that opens a bubble: a click on one is never «outside». */
export const BUBBLE_TRIGGER_ATTR = "data-close-verses-trigger";

/** Gap between the anchor and the bubble, and the viewport gutter (px). */
const GAP = 8;
const GUTTER = 16;

/**
 * The close verses of one āya, in a popover anchored under the marker or word
 * the reader activated on the «سور القرآن» page.
 *
 * Reading, not navigation: nothing in it is a link, nothing changes the URL,
 * and focus moves without scrolling (`preventScroll`), so opening and closing
 * it leaves the page exactly where the reader was. Intra-sūra partners in
 * another range of a long sūra are listed by their text, never scrolled to.
 *
 * Rendered into `document.body`, positioned in page coordinates, so it scrolls
 * with the text it is anchored on and adds nothing inside the reading block.
 * Closes on Escape, on a click outside it, and — through the parent, which
 * holds a single open āya — when another āya's bubble is opened.
 */
export default function CloseVersesBubble({
  surah,
  entry,
  verses,
  anchor,
  onClose,
}: {
  surah: number;
  entry: AyahAnnotation;
  verses: Record<string, Verse>;
  /** The marker or word that opened it: the position, and where focus returns. */
  anchor: HTMLElement;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const titleId = `close-verses-${surah}-${entry.ayah}`;

  // Under the anchor, centred on it, clamped inside the viewport's width.
  useLayoutEffect(() => {
    function place() {
      const el = ref.current;
      if (!el) return;
      const r = anchor.getBoundingClientRect();
      const width = el.offsetWidth;
      const viewport = document.documentElement.clientWidth || window.innerWidth;
      const centred = r.left + r.width / 2 - width / 2;
      const left = Math.max(GUTTER, Math.min(centred, viewport - width - GUTTER));
      setPos({ top: r.bottom + window.scrollY + GAP, left: left + window.scrollX });
    }
    place();
    window.addEventListener("resize", place);
    return () => window.removeEventListener("resize", place);
  }, [anchor, entry]);

  // Focus in on open; back to the anchor on close — neither may scroll. Only
  // after Escape or the close button: a click outside has already put focus on
  // whatever the reader clicked (the picker's select, say), and taking it back
  // would collapse that control as it opens.
  const returnFocus = useRef(false);
  useEffect(() => {
    ref.current?.focus({ preventScroll: true });
    return () => {
      if (returnFocus.current && anchor.isConnected) anchor.focus({ preventScroll: true });
    };
  }, [anchor]);

  const closeAndReturn = useCallback(() => {
    returnFocus.current = true;
    onClose();
  }, [onClose]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        closeAndReturn();
      }
    }
    function onClick(e: MouseEvent) {
      const target = e.target;
      if (!(target instanceof Node)) return;
      if (ref.current?.contains(target)) return;
      // Another (or the same) trigger: its own handler decides — open another
      // āya, or toggle this one shut. Closing here first would undo it.
      if (target instanceof Element && target.closest(`[${BUBBLE_TRIGGER_ATTR}]`)) return;
      onClose();
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("click", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("click", onClick);
    };
  }, [onClose, closeAndReturn]);

  const inside = groupPartners(entry)
    .map((a) => verses[`${surah}:${a}`])
    .filter((v): v is Verse => !!v);
  const cross = crossPartners(entry).flatMap((p) => {
    const verse = verses[p.ref];
    return verse ? [{ partner: p, verse }] : [];
  });

  return createPortal(
    <div
      ref={ref}
      role="dialog"
      aria-labelledby={titleId}
      tabIndex={-1}
      dir="rtl"
      lang="ar"
      style={{
        position: "absolute",
        top: pos?.top ?? 0,
        left: pos?.left ?? 0,
        visibility: pos ? "visible" : "hidden",
      }}
      className="z-50 max-h-[60vh] w-[min(32rem,calc(100vw-2rem))] overflow-y-auto rounded-xl border border-gray-200 bg-white font-arabic shadow-lg focus:outline-none"
    >
      <div className="sticky top-0 flex items-center justify-between gap-2 border-b border-gray-100 bg-white px-4 py-2">
        <h3 id={titleId} className="western-digits text-base font-semibold text-gray-800">
          {S.reading.annotations.bubbleTitle(entry.ayah)}
        </h3>
        <button
          type="button"
          onClick={closeAndReturn}
          aria-label={S.reading.annotations.close}
          className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-800"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {inside.length > 0 && (
        <section aria-label={S.reading.annotations.insideSurah}>
          <h4 className="px-4 pt-3 text-sm font-semibold text-brand-dark">
            {S.reading.annotations.insideSurah}
          </h4>
          <ul className="divide-y divide-gray-100">
            {inside.map((v) => (
              <li key={v.id} className="px-4 py-3">
                <VerseText verse={v} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {cross.length > 0 && (
        <section aria-label={S.reading.annotations.otherSurahs}>
          <h4 className="px-4 pt-3 text-sm font-semibold text-orange-700">
            {S.reading.annotations.otherSurahs}
          </h4>
          <ul className="divide-y divide-gray-100">
            {cross.map(({ partner, verse }) => (
              <li key={partner.ref}>
                <div className="px-4 py-3">
                  <VerseText verse={verse} withSurah spans={partner.spans_other ?? []} />
                </div>
                <SharedWords words={partner.words} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>,
    document.body,
  );
}
