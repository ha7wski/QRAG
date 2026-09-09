"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { getSurah, getSurahs, statusOf, detailOf } from "@/lib/api";
import { S, forStatus } from "@/lib/strings";
import FailureNote, { type Failure } from "@/components/FailureNote";
import type { SurahMeta, SurahResponse } from "@/lib/types";
import ArabicText from "@/components/ArabicText";
import { toArabicDigits } from "@/lib/arabicDigits";
import { writePosition } from "@/lib/readingPosition";

/** How long the scroll must rest before the position is written (ms). */
const PERSIST_DEBOUNCE_MS = 500;

/** The aya named by the URL fragment (`#ayah-200`), or null. */
function ayahFromHash(): number | null {
  if (typeof window === "undefined") return null;
  const m = /^#ayah-(\d+)$/.exec(window.location.hash);
  if (!m) return null;
  const n = Number(m[1]);
  return Number.isInteger(n) && n >= 1 ? n : null;
}

/**
 * The «سور القرآن» reading surface: a surah picker, and below it one whole surah
 * rendered as a continuous vocalized block.
 *
 * ONE component for both `/surah` (resumed) and `/surah/{n}` (addressed), so the
 * two routes cannot drift apart and every deep link already emitted across the
 * app keeps landing on the same page.
 */
export default function SurahReader({ number }: { number: number }) {
  const router = useRouter();
  const [data, setData] = useState<SurahResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Failure | null>(null);

  // The picker's own data and failure: a failed surah list must not take the
  // surah down with it, so it is tracked separately from `error`.
  const [surahs, setSurahs] = useState<SurahMeta[] | null>(null);
  const [surahsFailed, setSurahsFailed] = useState(false);

  const bodyRef = useRef<HTMLDivElement | null>(null);
  // Guards the observer: it is attached only once the restore scroll has landed,
  // or the top of the surah would immediately overwrite the stored position.
  const restoredFor = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    restoredFor.current = null;
    getSurah(number)
      .then((d) => !cancelled && setData(d))
      .catch(
        (e) =>
          !cancelled &&
          setError({
            text: forStatus(statusOf(e), "surah"),
            detail: detailOf(e),
          }),
      )
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [number]);

  // The picker's list, fetched once — it is the same 114 rows for every surah.
  useEffect(() => {
    let cancelled = false;
    getSurahs()
      .then((list) => !cancelled && setSurahs(list))
      .catch(() => !cancelled && setSurahsFailed(true));
    return () => {
      cancelled = true;
    };
  }, []);

  // Every way of reaching a surah — picker, stepper, deep link, direct URL —
  // makes it the remembered one. The aya starts at 1 and is refined by the
  // observer as the reader scrolls.
  useEffect(() => {
    writePosition(number, 1);
  }, [number]);

  // Restore, then observe. A layout effect so the scroll is applied before the
  // browser paints: the reader sees one frame, at the right place.
  useLayoutEffect(() => {
    if (!data || restoredFor.current === number) return;
    const wanted = ayahFromHash();
    // Out of range (a hand-edited fragment, or a surah shorter than the stored
    // position) falls back to the top rather than scrolling nowhere.
    if (wanted !== null && wanted >= 1 && wanted <= data.verses.length) {
      document
        .getElementById(`ayah-${wanted}`)
        ?.scrollIntoView({ behavior: "auto", block: "center" });
    }
    restoredFor.current = number;
  }, [data, number]);

  // The position is persisted on a debounce, never on every intersection:
  // `localStorage` writes are synchronous and would otherwise land in the
  // scroll path. `pagehide` and unmount flush whatever the timer still holds.
  const pending = useRef<number | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flush = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    if (pending.current !== null) {
      writePosition(number, pending.current);
      pending.current = null;
    }
  }, [number]);

  const schedule = useCallback(
    (ayah: number) => {
      pending.current = ayah;
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(flush, PERSIST_DEBOUNCE_MS);
    },
    [flush],
  );

  // Track the first aya marker visible in the viewport. Attached only once the
  // restore scroll has landed — an observer firing during the restore would
  // report the top of the surah and overwrite the position being restored.
  useEffect(() => {
    if (!data || restoredFor.current !== number) return;
    const markers = Array.from(
      bodyRef.current?.querySelectorAll<HTMLElement>("[data-ayah]") ?? [],
    );
    if (markers.length === 0 || typeof IntersectionObserver === "undefined") {
      return;
    }

    let current = 0;
    const visible = new Set<number>();

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const n = Number(entry.target.getAttribute("data-ayah"));
          if (!Number.isInteger(n)) continue;
          if (entry.isIntersecting) visible.add(n);
          else visible.delete(n);
        }
        if (visible.size === 0) return;
        const first = Math.min(...visible);
        if (first !== current) {
          current = first;
          schedule(first);
        }
      },
      // Only the upper 40% of the viewport counts as "being read", so the aya
      // remembered is the one under the reader's eye, not the last one that
      // happens to be on screen.
      { rootMargin: "0px 0px -60% 0px" },
    );
    markers.forEach((m) => observer.observe(m));

    window.addEventListener("pagehide", flush);
    return () => {
      observer.disconnect();
      window.removeEventListener("pagehide", flush);
      flush();
    };
  }, [data, number, schedule, flush]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" /> {S.verse.loadingSurah}
      </div>
    );
  }
  if (error || !data) {
    return (
      <FailureNote
        failure={error ?? { text: S.errors.surahNotFound }}
        className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
      />
    );
  }

  // Mapped, never rendered raw: the corpus emits `makkiyya` / `madani`.
  const period = data.period
    ? (S.verse.period as Record<string, string | undefined>)[data.period]
    : undefined;

  return (
    <div className="space-y-5">
      {/* The picker: jumping to a surah. The stepper at the foot of the page is
          its complement — continuing from the one just finished. Choosing here
          navigates, so what is on screen always has a shareable address. */}
      <div className="flex items-center gap-3">
        <label htmlFor="surah-picker" className="text-sm text-gray-600">
          {S.reading.pickerLabel}
        </label>
        <select
          id="surah-picker"
          value={number}
          onChange={(e) => router.push(`/surah/${e.target.value}`)}
          className="min-w-[240px] rounded-lg border border-gray-300 px-3 py-2 font-arabic text-base focus:border-brand focus:outline-none"
        >
          {(surahs ?? []).map((s) => (
            <option key={s.number} value={s.number}>
              {S.reading.option(toArabicDigits(s.number), s.name_ar ?? "")}
            </option>
          ))}
          {/* Until the list arrives (or when it failed), the select still has to
              show the surah it is on, or it would read as an empty control. */}
          {!surahs && (
            <option value={number}>
              {S.reading.option(
                toArabicDigits(number),
                data.surah_name_ar || data.surah_name_en || "",
              )}
            </option>
          )}
        </select>
        {surahsFailed && (
          <span className="text-sm text-red-700">{S.reading.surahsFailed}</span>
        )}
      </div>

      <header className="space-y-1 border-b border-gray-200 pb-3">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold text-gray-800">
            {data.surah_name_ar || data.surah_name_en}
          </h1>
          <span className="text-gray-400">
            {S.verse.surahNumber(toArabicDigits(data.surah_number))}
          </span>
        </div>
        {/* This line used to read «The Cow · La Vache · 286 verses · madani».
            The translated names are dropped rather than translated — the page
            reads a sūra in Arabic — and the period goes through the same map
            `VerseCard` uses, an unknown value rendering nothing rather than
            leaking the machine id. Digits are Arabic-Indic to match the sūra
            number above them, this being a reading context and not an
            analytical one. */}
        <p className="text-sm text-gray-500">
          {period ? `${period} · ` : ""}
          {S.verse.ayahCount(data.ayah_count, toArabicDigits(data.ayah_count))}
        </p>
      </header>

      {/* The Basmala, once, as an opening rather than as part of ayah 1. The
          backend decides: the field is empty for al-Fātiḥa (where it IS ayah 1,
          already in the body) and for at-Tawba (which has none), so there is no
          test on the sūra number here and no scripture rule in TypeScript. */}
      {data.basmala && (
        <ArabicText className="block text-center text-2xl leading-loose text-brand-dark">
          {data.basmala}
        </ArabicText>
      )}

      {/* The whole surah as one continuous block (Arabic only): verses flow
          together, each followed by its ayah number, and the page scrolls to
          the end. */}
      <div
        ref={bodyRef}
        className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
      >
        <ArabicText className="block text-justify text-3xl leading-[2.6] text-gray-900">
          {data.verses.map((v) => (
            <span key={v.id}>
              {v.text_ar_tashkil || v.text_ar}
              {/* The marker carries the aya's address: `id` for the fragment
                  scroll, `data-ayah` for the observer that tracks reading. */}
              <span
                id={`ayah-${v.ayah_number}`}
                data-ayah={v.ayah_number}
                className="mx-1.5 align-middle text-xl font-semibold text-brand-dark"
              >
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
            <ArrowRight className="h-4 w-4" /> {S.verse.prevSurah}
          </Link>
        ) : (
          <span />
        )}
        {number < 114 ? (
          <Link
            href={`/surah/${number + 1}`}
            className="flex items-center gap-1 text-brand-dark hover:underline"
          >
            {S.verse.nextSurah} <ArrowLeft className="h-4 w-4" />
          </Link>
        ) : (
          <span />
        )}
      </nav>
    </div>
  );
}
