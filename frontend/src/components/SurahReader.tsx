"use client";

import {
  Fragment,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import {
  getSurah,
  getSurahAnnotations,
  getSurahs,
  statusOf,
  detailOf,
  type AyahAnnotation,
  type SurahAnnotations,
} from "@/lib/api";
import { S, forStatus } from "@/lib/strings";
import FailureNote, { type Failure } from "@/components/FailureNote";
import type { SurahMeta, SurahResponse } from "@/lib/types";
import ArabicText from "@/components/ArabicText";
import SurahPicker, { SurahsIntro } from "@/components/SurahPicker";
import { writePosition } from "@/lib/readingPosition";
import {
  isAnnotated,
  markerCue,
  crossSpans,
  readAnnotationsOn,
  splitMarked,
  writeAnnotationsOn,
} from "@/lib/annotations";
import CloseVersesBubble, { BUBBLE_TRIGGER_ATTR } from "@/components/CloseVersesBubble";

/** Āyāt per range tab. A surah longer than this reads one range at a time. */
export const CHUNK_SIZE = 50;

/** The range index holding `ayah`, or 0 when there is none to honour. */
function chunkOf(ayah: number | null, total: number): number {
  if (ayah === null || ayah < 1 || ayah > total) return 0;
  return Math.floor((ayah - 1) / CHUNK_SIZE);
}

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

/** The marker's classes, unannotated — the page as it is with the switch off. */
const MARKER_CLASS =
  "western-digits mx-1.5 align-middle text-xl font-semibold text-brand-dark";

/** Annotations fetched this session, per sūra: turning the switch off and on,
 *  or coming back to a sūra, never refetches. Written only from an effect's
 *  promise, so it is never filled during a server render. */
const annotationCache = new Map<number, SurahAnnotations>();

/** Whether a click ended a text selection rather than meaning «open» — a reader
 *  selecting coloured words must not get a bubble for it. */
function isSelecting(): boolean {
  try {
    const sel = window.getSelection?.();
    return !!sel && !sel.isCollapsed && sel.toString().length > 0;
  } catch {
    return false;
  }
}

/** Set once the document's own navigation has been looked at, so a reload is
 *  acted on at most once per page load — never on a later in-app visit. */
let reloadSeen = false;

/**
 * Whether this mount IS the document load of a hard reload of this page. Only
 * the first `SurahReader` of a page load can be: after any in-app navigation
 * the navigation entry still says «reload» but describes another URL, or has
 * already been consumed. Pure, so it is safe in a state initializer.
 */
function isReloadOfThisPage(): boolean {
  if (reloadSeen || typeof window === "undefined") return false;
  try {
    const nav = performance.getEntriesByType("navigation")[0] as
      | PerformanceNavigationTiming
      | undefined;
    return (
      nav?.type === "reload" &&
      new URL(nav.name).pathname === window.location.pathname
    );
  } catch {
    return false;
  }
}

/**
 * The «سور القرآن» reading surface: a surah picker, and below it one whole surah
 * rendered as a continuous vocalized block.
 *
 * Rendered at `/surah/{n}`, the address every deep link across the app
 * already emits. `/surah` itself is the main page (picker + resume link).
 */
export default function SurahReader({ number }: { number: number }) {
  const router = useRouter();
  // A hard reload of `/surah/{n}` returns to the «سور القرآن» main page rather
  // than reopening the surah. Deep links opened from elsewhere are not reloads.
  const [reloaded] = useState(isReloadOfThisPage);
  const [data, setData] = useState<SurahResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Failure | null>(null);

  // The picker's own data and failure: a failed surah list must not take the
  // surah down with it, so it is tracked separately from `error`.
  const [surahs, setSurahs] = useState<SurahMeta[] | null>(null);
  const [surahsFailed, setSurahsFailed] = useState(false);

  // The range tab on screen. Set with the data, from the URL fragment, so a
  // deep link to āya 200 opens the range that holds it.
  const [chunk, setChunk] = useState(0);

  // The closeness annotations: off by default, the choice remembered per
  // browser. Read after mount so the server render and the first client render
  // agree (both off).
  const [annotationsOn, setAnnotationsOn] = useState(false);
  const [annotations, setAnnotations] = useState<SurahAnnotations | null>(null);
  const [annotationsFailed, setAnnotationsFailed] = useState(false);
  // One open bubble at most: the āya, and the element it is anchored on.
  const [open, setOpen] = useState<{ ayah: number; anchor: HTMLElement } | null>(null);

  const bodyRef = useRef<HTMLDivElement | null>(null);
  const rangesRef = useRef<HTMLDivElement | null>(null);
  // Guards the observer: it is attached only once the restore scroll has landed,
  // or the top of the surah would immediately overwrite the stored position.
  const restoredFor = useRef<number | null>(null);
  // The āya a deep link (or reload) scrolled to, kept until the reader moves:
  // annotations landing after that scroll reflow the text above it (padded
  // markers), so the restore is re-applied once they render.
  const restoredAyah = useRef<number | null>(null);

  useEffect(() => {
    reloadSeen = true;
    if (reloaded) router.replace("/surah");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (reloaded) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    restoredFor.current = null;
    restoredAyah.current = null;
    getSurah(number)
      .then((d) => {
        if (cancelled) return;
        setChunk(chunkOf(ayahFromHash(), d.verses.length));
        setData(d);
      })
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
  }, [number, reloaded]);

  useEffect(() => {
    setAnnotationsOn(readAnnotationsOn());
  }, []);

  // Fetched only while the switch is on; once per sūra per session.
  useEffect(() => {
    setOpen(null);
    if (!annotationsOn || reloaded) return;
    const cached = annotationCache.get(number);
    setAnnotationsFailed(false);
    if (cached) {
      setAnnotations(cached);
      return;
    }
    setAnnotations(null);
    let cancelled = false;
    getSurahAnnotations(number)
      .then((a) => {
        annotationCache.set(number, a);
        if (!cancelled) setAnnotations(a);
      })
      .catch(() => !cancelled && setAnnotationsFailed(true));
    return () => {
      cancelled = true;
    };
  }, [annotationsOn, number, reloaded]);

  // A new range unmounts the anchor of an open bubble.
  useEffect(() => setOpen(null), [chunk]);

  const byAyah = useMemo(() => {
    const m = new Map<number, AyahAnnotation>();
    if (annotationsOn && annotations && annotations.surah === number) {
      for (const e of annotations.ayahs) if (isAnnotated(e)) m.set(e.ayah, e);
    }
    return m;
  }, [annotationsOn, annotations, number]);

  const closeBubble = useCallback(() => setOpen(null), []);

  function toggleAnnotations() {
    const next = !annotationsOn;
    setAnnotationsOn(next);
    writeAnnotationsOn(next);
  }

  // The props that make an annotated marker or word open its bubble: a click
  // (never a mousedown, so a selection drag does not open it) or Enter/Space.
  // A marker is named for what it opens; a word keeps its own text as its name.
  function triggerProps(ayah: number, named: boolean) {
    const activate = (el: HTMLElement) =>
      setOpen((cur) => (cur?.ayah === ayah ? null : { ayah, anchor: el }));
    return {
      role: "button",
      tabIndex: 0,
      "aria-haspopup": "dialog" as const,
      "aria-expanded": open?.ayah === ayah,
      "aria-label": named ? S.reading.annotations.openFor(ayah) : undefined,
      [BUBBLE_TRIGGER_ATTR]: "",
      onClick: (e: ReactMouseEvent<HTMLElement>) => {
        if (isSelecting()) return;
        activate(e.currentTarget);
      },
      onKeyDown: (e: ReactKeyboardEvent<HTMLElement>) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          activate(e.currentTarget);
        }
      },
    };
  }

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
  // Not on the reload being sent back: it would overwrite the aya the reader
  // was at, which the main page offers to resume.
  useEffect(() => {
    if (!reloaded) writePosition(number, 1);
  }, [number, reloaded]);

  // Restore, then observe. A layout effect so the scroll is applied before the
  // browser paints: the reader sees one frame, at the right place.
  useLayoutEffect(() => {
    // Not while the loading line still stands in for the text: the marker is
    // not in the DOM yet, and consuming the restore then would lose it.
    if (!data || loading || restoredFor.current === number) return;
    const wanted = ayahFromHash();
    // Out of range (a hand-edited fragment, or a surah shorter than the stored
    // position) falls back to the top rather than scrolling nowhere.
    if (wanted !== null && wanted >= 1 && wanted <= data.verses.length) {
      document
        .getElementById(`ayah-${wanted}`)
        ?.scrollIntoView({ behavior: "auto", block: "center" });
      restoredAyah.current = wanted;
    }
    restoredFor.current = number;
  }, [data, loading, number]);

  // Once the reader scrolls on their own, the restored āya is theirs to leave.
  useEffect(() => {
    const release = () => {
      restoredAyah.current = null;
    };
    const events = ["wheel", "touchstart", "keydown", "mousedown"] as const;
    for (const e of events) window.addEventListener(e, release, { passive: true });
    return () => {
      for (const e of events) window.removeEventListener(e, release);
    };
  }, []);

  // Annotations rendered after the restore: re-centre the restored āya once.
  useLayoutEffect(() => {
    const wanted = restoredAyah.current;
    if (byAyah.size === 0 || wanted === null || restoredFor.current !== number) return;
    document
      .getElementById(`ayah-${wanted}`)
      ?.scrollIntoView({ behavior: "auto", block: "center" });
    restoredAyah.current = null;
  }, [byAyah, number]);

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
    if (!data || loading || restoredFor.current !== number) return;
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
    // `chunk`: a new range renders new markers, which must be observed.
  }, [data, loading, number, chunk, schedule, flush]);

  function showChunk(i: number) {
    setChunk(i);
    rangesRef.current?.scrollIntoView?.({ behavior: "auto", block: "nearest" });
  }

  // The page heading and the picker stay on screen whatever the surah's state:
  // choosing a surah must not take the reader out from under «سور القرآن».
  const top = (
    <>
      <SurahsIntro />
      <SurahPicker
        surahs={surahs}
        failed={surahsFailed}
        value={number}
        current={data?.surah_name_ar || data?.surah_name_en || ""}
        onChoose={(n) => router.push(`/surah/${n}`)}
      />
    </>
  );

  if (loading) {
    return (
      <div className="space-y-6">
        {top}
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" /> {S.verse.loadingSurah}
        </div>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="space-y-6">
        {top}
        <FailureNote
          failure={error ?? { text: S.errors.surahNotFound }}
          className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
        />
      </div>
    );
  }

  // A surah longer than one range reads one range at a time.
  const chunks = Math.ceil(data.verses.length / CHUNK_SIZE);
  const shown =
    chunks > 1
      ? data.verses.slice(chunk * CHUNK_SIZE, (chunk + 1) * CHUNK_SIZE)
      : data.verses;
  const rangeOf = (i: number) =>
    `${i * CHUNK_SIZE + 1}–${Math.min((i + 1) * CHUNK_SIZE, data.verses.length)}`;

  // Mapped, never rendered raw: the corpus emits `makkiyya` / `madani`.
  const period = data.period
    ? (S.verse.period as Record<string, string | undefined>)[data.period]
    : undefined;

  return (
    <div className="space-y-6">
      {top}

      {/* The name, centred, with the period and the length under it
          («مدنية · 286 آية»), flanked by the stepper: the previous surah on the
          right, the next on the left (document RTL places them). The surah's
          number is already in the picker above. The period goes through the
          same map `VerseCard` uses — an unknown value renders nothing. */}
      <header className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 border-b border-gray-200 pb-3 text-sm">
        <div className="justify-self-start">
          {number > 1 && (
            <Link
              href={`/surah/${number - 1}`}
              className="flex items-center gap-1 text-brand-dark hover:underline"
            >
              <ArrowRight className="h-4 w-4" /> {S.verse.prevSurah}
            </Link>
          )}
        </div>
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-800">
            {data.surah_name_ar || data.surah_name_en}
          </h2>
          <p className="western-digits text-sm text-gray-500">
            {period ? `${period} · ` : ""}
            {S.verse.ayahCount(data.ayah_count)}
          </p>
        </div>
        <div className="justify-self-end">
          {number < 114 && (
            <Link
              href={`/surah/${number + 1}`}
              className="flex items-center gap-1 text-brand-dark hover:underline"
            >
              {S.verse.nextSurah} <ArrowLeft className="h-4 w-4" />
            </Link>
          )}
        </div>
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

      {chunks > 1 && (
        <div
          ref={rangesRef}
          role="tablist"
          aria-label={S.reading.rangesLabel}
          className="flex flex-wrap gap-1.5"
        >
          {Array.from({ length: chunks }, (_, i) => (
            <button
              key={i}
              type="button"
              role="tab"
              aria-selected={i === chunk}
              onClick={() => showChunk(i)}
              className={`western-digits rounded-lg border px-3 py-1 text-sm transition ${
                i === chunk
                  ? "border-brand bg-brand text-white"
                  : "border-gray-200 bg-white text-gray-700 hover:border-brand hover:text-brand-dark"
              }`}
            >
              <span dir="ltr">{rangeOf(i)}</span>
            </button>
          ))}
        </div>
      )}

      {/* The closeness annotations: the switch, and while it is on the legend
          (or why there is nothing to show). */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 font-arabic text-sm text-gray-700">
        <button
          type="button"
          role="switch"
          aria-checked={annotationsOn}
          onClick={toggleAnnotations}
          className="flex items-center gap-2"
        >
          <span
            aria-hidden
            className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition ${
              annotationsOn ? "bg-brand" : "bg-gray-300"
            }`}
          >
            <span
              className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${
                annotationsOn ? "right-0.5" : "right-[1.125rem]"
              }`}
            />
          </span>
          {S.reading.annotations.toggle}
        </button>
        {annotationsOn && !annotationsFailed && (
          <ul aria-label={S.reading.annotations.legendLabel} className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <li className="flex items-center gap-1.5">
              <span aria-hidden className="inline-block h-4 w-6 rounded-sm bg-emerald-100" />
              {S.reading.annotations.legendGroup}
            </li>
            {/* ONE orange cue in two parts: the ringed marker over an orange word. */}
            <li className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="inline-flex h-4 w-6 items-center justify-center rounded-md bg-white ring-2 ring-orange-400"
              >
                <span className="inline-block h-2 w-4 rounded-sm bg-orange-100" />
              </span>
              {S.reading.annotations.legendQuran}
            </li>
          </ul>
        )}
        {annotationsOn && !annotationsFailed && !annotations && (
          <span className="flex items-center gap-1 text-gray-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> {S.reading.annotations.loading}
          </span>
        )}
        {annotationsOn && annotationsFailed && (
          <p role="status" className="rounded bg-amber-50 px-3 py-1 text-amber-800">
            {S.reading.annotations.unavailable}
          </p>
        )}
      </div>

      {/* The surah (or the range on screen) as one continuous block (Arabic only): verses flow
          together, each followed by its ayah number, and the page scrolls to
          the end. */}
      <div
        ref={bodyRef}
        className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
      >
        <ArabicText className="block text-justify text-3xl leading-[2.6] text-gray-900">
          {shown.map((v) => {
            const text = v.text_ar_tashkil || v.text_ar;
            const entry = byAyah.get(v.ayah_number);
            if (!entry) {
              // Unannotated — and, with the switch off, every āya: exactly the
              // page as it is without annotations.
              return (
                <span key={v.id}>
                  {text}
                  {/* The marker carries the aya's address: `id` for the fragment
                      scroll, `data-ayah` for the observer that tracks reading. */}
                  <span
                    id={`ayah-${v.ayah_number}`}
                    data-ayah={v.ayah_number}
                    className={MARKER_CLASS}
                  >
                    ﴿{v.ayah_number}﴾
                  </span>{" "}
                </span>
              );
            }
            // One orange cue: every cross pair rings the marker and colours its
            // common part. Spans address the vocalized text only; on the
            // fallback the marker alone remains.
            const vocalized = !!v.text_ar_tashkil;
            const cue = markerCue(entry);
            const segments = splitMarked(text, crossSpans(entry, vocalized));
            const body = segments.map((seg) =>
                  seg.marked ? (
                    <mark
                      key={seg.start}
                      data-cue="cross"
                      {...triggerProps(v.ayah_number, false)}
                      className="cursor-pointer rounded-sm bg-orange-100 text-inherit focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
                    >
                      {seg.text}
                    </mark>
                  ) : (
                    <Fragment key={seg.start}>{seg.text}</Fragment>
                  ),
            );
            return (
              <span key={v.id}>
                {/* Close inside the sūra: the whole āya text turns green (its
                    orange common-part words, if any, stay orange on top). */}
                {cue.green ? (
                  <span
                    data-cue="group"
                    className="rounded-sm bg-emerald-100 [box-decoration-break:clone] [-webkit-box-decoration-break:clone]"
                  >
                    {body}
                  </span>
                ) : (
                  body
                )}
                <span
                  id={`ayah-${v.ayah_number}`}
                  data-ayah={v.ayah_number}
                  data-cue-group={cue.green || undefined}
                  data-cue-quran={cue.orange || undefined}
                  {...triggerProps(v.ayah_number, true)}
                  className={`${MARKER_CLASS} cursor-pointer rounded-md px-1 focus:outline-none focus-visible:underline ${
                    cue.orange ? "ring-2 ring-orange-400" : ""
                  }`}
                >
                  ﴿{v.ayah_number}﴾
                </span>{" "}
              </span>
            );
          })}
        </ArabicText>
      </div>

      {open && byAyah.get(open.ayah) && annotations && (
        <CloseVersesBubble
          key={open.ayah}
          surah={number}
          entry={byAyah.get(open.ayah)!}
          verses={annotations.verses}
          anchor={open.anchor}
          onClose={closeBubble}
        />
      )}

      {chunks > 1 && chunk < chunks - 1 && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => showChunk(chunk + 1)}
            className="western-digits flex items-center gap-1 text-sm text-brand-dark hover:underline"
          >
            {S.reading.nextRange} <span dir="ltr">({rangeOf(chunk + 1)})</span>
            <ArrowLeft className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
