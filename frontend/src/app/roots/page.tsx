"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import {
  detailOf,
  fetchRootLetters,
  fetchRootsByLetter,
  statusOf,
} from "@/lib/api";
import type { RootLetterResponse, RootLettersResponse } from "@/lib/types";
import { useCachedState } from "@/lib/pageCache";
import { S, forStatus } from "@/lib/strings";
import ArabicText from "@/components/ArabicText";
import FailureNote, { type Failure } from "@/components/FailureNote";
import RootCard from "@/components/RootCard";
import ScrollToTop from "@/components/ScrollToTop";

/**
 * Vertical offsets (px) that put every letter's INK at the same height.
 *
 * The letters share a baseline, which is typographically right and visually
 * wrong here: ج ح خ ع sit their body under the baseline, ث ت ب on it, so in a
 * strip of isolated letters ج reads as lower than ث. Each glyph's ink box is
 * measured with the font actually in use and shifted so its centre lands on the
 * strip's common centre. Empty until the fonts are loaded, and wherever there
 * is no canvas or font API (SSR, jsdom) — the letters then fall back to the
 * shared baseline.
 */
function useInkOffsets(
  letters: string[] | undefined,
  sample: React.RefObject<HTMLElement>,
): Record<string, number> {
  const [offsets, setOffsets] = useState<Record<string, number>>({});
  const key = letters?.join("") ?? "";
  useEffect(() => {
    if (!letters?.length || typeof document === "undefined" || !document.fonts) return;
    let live = true;
    document.fonts.ready.then(() => {
      const el = sample.current;
      const ctx = el && document.createElement("canvas").getContext("2d");
      if (!live || !el || !ctx) return;
      const cs = getComputedStyle(el);
      ctx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
      // Height of each ink box's centre above the baseline.
      const centre = Object.fromEntries(
        letters.map((l) => {
          const m = ctx.measureText(l);
          return [l, (m.actualBoundingBoxAscent - m.actualBoundingBoxDescent) / 2];
        }),
      );
      const values = Object.values(centre);
      const mean = values.reduce((a, b) => a + b, 0) / values.length;
      setOffsets(
        Object.fromEntries(letters.map((l) => [l, Math.round(centre[l] - mean)])),
      );
    });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return offsets;
}

/**
 * «فهرس الجذور» — every Quranic root that is the primary root of at least one
 * word, browsed by first radical (GET /roots, GET /roots/letter/{letter}).
 * Nothing is typed: the reader picks a letter from the strip.
 *
 * The selected letter lives in the URL (`?letter=`), so a letter can be
 * deep-linked. Switching letters PUSHES a history entry, so the browser's Back
 * returns to the previous letter; the page renders from the URL, so that is all
 * Back needs.
 * `useSearchParams` requires the Suspense boundary below.
 *
 * The page renders what the backend sends and decides nothing about it: the
 * figures are `root_forms`, the reading is the mechanical assembly computed
 * with no signed choice. When the letter or وصف table fails its lock the
 * response says so once (`readings_available: false`) and the page shows one
 * notice, not one per card.
 */
export default function RootsPage() {
  return (
    <Suspense fallback={null}>
      <RootIndex />
    </Suspense>
  );
}

function RootIndex() {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("letter")?.trim() || "";

  // Cached: leaving for /lexical from a card and coming back restores the strip
  // and the letter without a refetch. Keyed on the letter as REQUESTED, so a
  // deep link `?letter=ء` is served from the cache once it has been fetched.
  const [letters, setLetters] = useCachedState<RootLettersResponse | null>(
    "roots.letters",
    null,
  );
  const [byLetter, setByLetter] = useCachedState<
    Record<string, RootLetterResponse>
  >("roots.byLetter", {});
  // The last letter the reader opened. The nav link is a bare `/roots`, so
  // without this, leaving for another tab and coming back through the nav
  // landed on an empty index — the search looked lost though its data was
  // still cached.
  const [lastLetter, setLastLetter] = useCachedState<string>("roots.lastLetter", "");
  const [lettersError, setLettersError] = useState<Failure | null>(null);
  const [letterError, setLetterError] = useState<Failure | null>(null);
  const [loading, setLoading] = useState(false);

  const glyphSample = useRef<HTMLSpanElement>(null);
  const inkOffsets = useInkOffsets(
    letters?.letters.map((g) => g.letter),
    glyphSample,
  );

  // Only the latest letter request may write state: two fast clicks must not
  // leave the roots of one letter under the heading of another.
  const runSeq = useRef(0);

  useEffect(() => {
    if (letters) return;
    let live = true;
    fetchRootLetters()
      .then((r) => live && setLetters(r))
      .catch((e) => {
        if (live)
          setLettersError({
            text: forStatus(statusOf(e), "rootIndex"),
            detail: detailOf(e),
          });
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // A bare `/roots` resumes the last letter. `replace`, not `push`: the hop
  // must not sit in the history, or Back would bounce straight back here.
  useEffect(() => {
    if (!requested && lastLetter) {
      router.replace(`/roots?letter=${encodeURIComponent(lastLetter)}`, {
        scroll: false,
      });
    } else if (requested && requested !== lastLetter) {
      setLastLetter(requested);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requested]);

  useEffect(() => {
    setLetterError(null);
    if (!requested || byLetter[requested]) {
      runSeq.current++; // a cached or cleared letter cancels any request in flight
      setLoading(false);
      return;
    }
    const seq = ++runSeq.current;
    setLoading(true);
    fetchRootsByLetter(requested)
      .then((r) => {
        if (seq === runSeq.current)
          setByLetter((prev) => ({ ...prev, [requested]: r }));
      })
      .catch((e) => {
        if (seq === runSeq.current)
          setLetterError({
            text: forStatus(statusOf(e), "rootIndex"),
            detail: detailOf(e),
          });
      })
      .finally(() => {
        if (seq === runSeq.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requested]);

  const data = requested ? byLetter[requested] ?? null : null;

  function select(letter: string) {
    if (letter === requested) return; // no duplicate history entry
    router.push(`/roots?letter=${encodeURIComponent(letter)}`, {
      scroll: false,
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">{S.roots.heading}</h1>
        <p className="mt-1 text-sm text-gray-500">{S.roots.caption}</p>
      </div>

      {lettersError && (
        <FailureNote
          failure={lettersError}
          className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
        />
      )}

      {letters && (
        <section aria-label={S.roots.lettersLabel} className="space-y-3">
          <p className="western-digits text-xs italic text-gray-500">
            {S.roots.total(letters.total)}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {letters.letters.map((g, i) => {
              // Compared on the RESPONSE's label, so `?letter=ء` lights «أ».
              const active = data?.letter === g.letter;
              return (
                <button
                  key={g.letter}
                  type="button"
                  onClick={() => select(g.letter)}
                  aria-pressed={active}
                  aria-label={S.roots.letterButton(g.letter, g.count)}
                  disabled={g.count === 0}
                  className={`flex w-12 flex-col items-center gap-1 rounded-lg border px-1 pb-1 pt-1.5 transition disabled:opacity-40 ${
                    active
                      ? "border-brand bg-brand text-white"
                      : "border-gray-200 bg-white text-gray-700 hover:border-brand hover:text-brand-dark"
                  }`}
                >
                  {/* A box tall enough for any ascender or descender, so no
                      glyph reaches the digit; the glyph inside is shifted by
                      its measured ink offset (see `useInkOffsets`). */}
                  <span
                    ref={i === 0 ? glyphSample : undefined}
                    className="flex h-8 items-center font-arabic text-xl leading-none"
                    style={{ transform: `translateY(${inkOffsets[g.letter] ?? 0}px)` }}
                  >
                    <ArabicText className="!leading-none">{g.letter}</ArabicText>
                  </span>
                  <span
                    className={`western-digits text-[11px] ${
                      active ? "text-white/80" : "text-gray-400"
                    }`}
                  >
                    {g.count}
                  </span>
                </button>
              );
            })}
          </div>
        </section>
      )}

      {!requested && !lastLetter && letters && (
        <p className="text-sm text-gray-500">{S.roots.pickLetter}</p>
      )}

      {letterError && (
        <FailureNote
          failure={letterError}
          className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
        />
      )}

      {loading && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" /> {S.roots.loading}
        </div>
      )}

      {data && !loading && (
        <section aria-labelledby="roots-group" className="space-y-4">
          <h2
            id="roots-group"
            className="western-digits text-lg font-semibold text-gray-800"
          >
            {S.roots.groupHeading(data.letter, data.count)}
          </h2>

          {!data.readings_available && (
            <p
              role="status"
              data-testid="readings-unavailable"
              className="rounded bg-amber-50 px-3 py-2 font-arabic text-sm text-amber-800"
            >
              {S.roots.readingsUnavailable}
            </p>
          )}
          {data.readings_available && data.roots.length > 0 && (
            <p className="font-arabic text-xs text-gray-500">
              {S.lexical.assemblyAlternativesNote}
            </p>
          )}

          {data.roots.length === 0 ? (
            <p className="text-sm text-gray-500">{S.roots.noRoots}</p>
          ) : (
            <div className="space-y-3">
              {data.roots.map((entry) => (
                <RootCard
                  key={entry.root}
                  entry={entry}
                  readingsAvailable={data.readings_available}
                />
              ))}
            </div>
          )}
        </section>
      )}

      <ScrollToTop />
    </div>
  );
}
