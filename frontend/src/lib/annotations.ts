// The closeness annotations of the «سور القرآن» reading page — the pure part.
//
// Everything here is computation over the `GET /surah/{n}/annotations` payload
// (and one stored on/off flag): which cue an āya's marker carries, which of its
// characters are marked, and what its bubble lists. No React, no fetch, so the
// rules the spec states are pinned by plain unit tests (`annotations.test.ts`).

import type { AnnotationPartner, AyahAnnotation } from "./api";

/** A half-open CHARACTER span `[start, end)`. */
export type Span = [number, number];

/** One cut of a text: a plain run, or a run inside a common part. */
export interface Segment {
  text: string;
  marked: boolean;
  /** Offset of the run in the text it was cut from (a stable React key). */
  start: number;
}

/**
 * `spans` as disjoint runs, ascending. Overlapping AND touching spans become one
 * run, so a union of several passages is marked once, continuously. A span that
 * is not a valid half-open range inside a text of `length` characters is dropped
 * rather than clamped: an offset outside the text means the text is not the one
 * the span was computed against, and marking it anyway would mark the wrong words.
 *
 * The offsets were computed by the build in Python code points; the reading text
 * is BMP-only Arabic, where code points and the UTF-16 indices JS slices by
 * coincide (pinned on 28:20 by the test).
 */
export function mergeSpans(spans: readonly Span[], length: number): Span[] {
  const valid = spans
    .filter(
      ([start, end]) =>
        Number.isInteger(start) &&
        Number.isInteger(end) &&
        start >= 0 &&
        start < end &&
        end <= length,
    )
    .map(([start, end]): Span => [start, end]) // copies: the inputs stay untouched
    .sort((x, y) => x[0] - y[0] || x[1] - y[1]);
  const merged: Span[] = [];
  for (const [start, end] of valid) {
    const last = merged[merged.length - 1];
    if (last && start <= last[1]) last[1] = Math.max(last[1], end);
    else merged.push([start, end]);
  }
  return merged;
}

/** `text` cut into plain and marked runs by the union of `spans`. Their
 *  concatenation is `text`, and no run is empty. */
export function splitMarked(text: string, spans: readonly Span[]): Segment[] {
  const out: Segment[] = [];
  let at = 0;
  for (const [start, end] of mergeSpans(spans, text.length)) {
    if (start > at) out.push({ text: text.slice(at, start), marked: false, start: at });
    out.push({ text: text.slice(start, end), marked: true, start });
    at = end;
  }
  if (at < text.length || out.length === 0) {
    out.push({ text: text.slice(at), marked: false, start: at });
  }
  return out;
}

/** The two cues of an āya's `﴿n﴾` marker. Both may hold at once. */
export interface MarkerCue {
  /** A member of one of its sūra's groups. */
  green: boolean;
  /** A whole-verse pair in another sūra — or a passage-only pair whose span
   *  cannot be applied because the āya is rendered from its undiacritized
   *  fallback. */
  orange: boolean;
}

export function markerCue(entry: AyahAnnotation, vocalized: boolean): MarkerCue {
  return {
    green: entry.group.length > 0,
    orange: entry.whole.length > 0 || (!vocalized && entry.passage.length > 0),
  };
}

/** The spans to mark in the āya's own text: every span of its passage-only
 *  pairs' side of the common part (a pair may colour several runs), and only on
 *  the vocalized text the spans address. Whole-verse pairs never colour words,
 *  even when they carry a common part. Not merged here: `splitMarked` unions. */
export function passageSpans(entry: AyahAnnotation, vocalized: boolean): Span[] {
  if (!vocalized) return [];
  return entry.passage.flatMap((p) => p.spans_self ?? []);
}

/** Whether an entry carries anything at all — only such an āya is clickable. */
export function isAnnotated(entry: AyahAnnotation | undefined): entry is AyahAnnotation {
  return (
    !!entry && (entry.group.length > 0 || entry.whole.length > 0 || entry.passage.length > 0)
  );
}

/** `"s:a"` as numbers, for mushaf ordering. */
function refKey(ref: string): [number, number] {
  const [s, a] = ref.split(":").map(Number);
  return [s, a];
}

/** Mushaf order over `"s:a"` references. */
export function compareRefs(x: string, y: string): number {
  const [sx, ax] = refKey(x);
  const [sy, ay] = refKey(y);
  return sx - sy || ax - ay;
}

/** The bubble's «في سائر القرآن» list: whole-verse and passage-only partners
 *  together, score descending, ties in mushaf order. */
export function crossPartners(entry: AyahAnnotation): AnnotationPartner[] {
  return [...entry.whole, ...entry.passage].sort(
    (x, y) => y.score - x.score || compareRefs(x.ref, y.ref),
  );
}

/** The bubble's «داخل السورة» list: the āya's group partners, mushaf order. */
export function groupPartners(entry: AyahAnnotation): number[] {
  return [...entry.group].sort((x, y) => x - y);
}

// ── The switch, remembered per browser ─────────────────────────────────
// Not `lib/pageCache.ts`: the reader's choice must survive a reload. Every
// storage access is guarded — a browser that refuses to store leaves the
// annotations off, which is the page as it has always been.

export const ANNOTATIONS_KEY = "surah.annotations.on";

export function readAnnotationsOn(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(ANNOTATIONS_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeAnnotationsOn(on: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (on) window.localStorage.setItem(ANNOTATIONS_KEY, "1");
    else window.localStorage.removeItem(ANNOTATIONS_KEY);
  } catch {
    // Blocked site data: the choice holds for this visit only.
  }
}
