// Where the reader left off in «سور القرآن» — one {surah, ayah} pair.
//
// Persisted in localStorage, on the pattern `lib/conversations.ts` establishes:
// SSR-guarded (`window` may be absent), and tolerant of a storage that refuses
// to answer (private mode, blocked site data) or answers with a corrupt value.
// Nothing on the reading page depends on the position existing.
//
// NOT `lib/pageCache.ts`: its Map is scoped to the tab's JS session and is
// dropped by a hard reload, so a position stored there would not survive F5.
//
// The unit is the AYA, never a scroll offset. The reading block reflows with
// viewport width and font size, so a stored pixel offset lands somewhere
// arbitrary after either changes — while an aya survives both, is what a reader
// actually resumes at, and is expressible in the URL as `#ayah-{n}`.

const STORAGE_KEY = "quran-rag.reading.v1";

/** Where the navigation entry lands when nothing usable is stored. */
export const FALLBACK_SURAH = 1;

export interface ReadingPosition {
  surah: number;
  ayah: number;
}

const isSurah = (n: unknown): n is number =>
  typeof n === "number" && Number.isInteger(n) && n >= 1 && n <= 114;

const isAyah = (n: unknown): n is number =>
  typeof n === "number" && Number.isInteger(n) && n >= 1;

/**
 * The stored position, or null when there is none to trust.
 *
 * A value outside 1…114, a non-integer aya, an unparsable string and a storage
 * that throws all resolve to null — the caller falls back rather than acting on
 * a half-read position. The aya is NOT validated against the surah's length
 * here: that length is only known once the surah is loaded, so the reading page
 * clamps it (see `SurahReader`).
 */
export function readPosition(): ReadingPosition | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || !isSurah(parsed.surah) || !isAyah(parsed.ayah)) return null;
    return { surah: parsed.surah, ayah: parsed.ayah };
  } catch {
    // Unparsable value, or a getter that throws on blocked site data.
    return null;
  }
}

/**
 * Remember `surah`:`ayah`. Out-of-range input is dropped rather than stored, so
 * a bad write cannot make the next read fall back for the wrong reason.
 */
export function writePosition(surah: number, ayah: number): void {
  if (typeof window === "undefined") return;
  if (!isSurah(surah) || !isAyah(ayah)) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ surah, ayah }));
  } catch {
    // Storage disabled or over quota — persistence is best-effort.
  }
}

/** The address the navigation entry resumes at. */
export function resumeHref(pos: ReadingPosition | null): string {
  if (!pos) return `/surah/${FALLBACK_SURAH}`;
  // Ayah 1 needs no fragment: it is where the page already opens.
  return pos.ayah > 1
    ? `/surah/${pos.surah}#ayah-${pos.ayah}`
    : `/surah/${pos.surah}`;
}
