// API client for the Quran RAG backend.
import type {
  ChatMessage,
  FeedbackStats,
  HealthStatus,
  QlisanFormResponse,
  QlisanVerseResponse,
  QlisanWordResponse,
  RootLetterResponse,
  RootLettersResponse,
  SearchResponse,
  SurahMeta,
  SurahResponse,
  Verse,
  VerseDetail,
  VerseLookupResponse,
} from "./types";
import type { FassilaOverviewResponse, FassilaResponse } from "./fassilaTypes";
import type { LisanReading } from "./lisanTypes";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * An API failure that carries its HTTP status.
 *
 * The status is what lets a caller pick the Arabic sentence by failure *kind*
 * rather than one generic sentence per call site (design D17) — several backend
 * details are actionable, and collapsing them would satisfy the Arabic-only
 * requirement while making the app less usable.
 *
 * The English `message` is deliberately unchanged and deliberately not
 * translated: under design D10 it is rendered as a subordinate `dir="ltr"
 * lang="en"` technical line, never as the sentence the reader is meant to read.
 */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** The HTTP status of a failure, or `undefined` when the fetch itself rejected. */
export function statusOf(e: unknown): number | undefined {
  return e instanceof ApiError ? e.status : undefined;
}

/** The technical detail of a failure — English, and shown only as a subordinate line. */
export function detailOf(e: unknown): string | undefined {
  return e instanceof Error && e.message ? e.message : undefined;
}

// ── Verse Lookup (exhaustive, vocalized root lookup) ──────────────────
export async function verseLookup(
  word: string,
): Promise<VerseLookupResponse> {
  const res = await fetch(`${API_URL}/verse-lookup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ word }),
  });
  if (!res.ok) throw new ApiError(`Verse lookup failed: ${res.status}`, res.status);
  return res.json();
}

// ── QLisan (per-word four-level analysis) ─────────────────────────────
// The verse with QAC-aligned, individually-selectable token boundaries.
export async function qlisanVerse(
  surah: number,
  ayah: number,
): Promise<QlisanVerseResponse> {
  const res = await fetch(`${API_URL}/qlisan/verse/${surah}/${ayah}`);
  if (res.status === 404) throw new ApiError(`Verse ${surah}:${ayah} not found`, res.status);
  if (!res.ok) throw new ApiError(`QLisan verse failed: ${res.status}`, res.status);
  return res.json();
}

// The four-level fiche (صوتي → صرفي → نحوي → دلالي) for one word.
export async function qlisanWord(
  surah: number,
  ayah: number,
  word: number,
): Promise<QlisanWordResponse> {
  const res = await fetch(`${API_URL}/qlisan/word`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ surah, ayah, word }),
  });
  if (res.status === 404)
    throw new ApiError(`Word ${surah}:${ayah}:${word} not found`, res.status);
  if (!res.ok) throw new ApiError(`QLisan word failed: ${res.status}`, res.status);
  return res.json();
}

// The صرفي level of a word typed with no verse position (Lisan Analysis).
// Always resolves: an unattested word comes back `available:false` with a message,
// so this supplementary section can never break the page that hosts it.
export async function qlisanForm(word: string): Promise<QlisanFormResponse> {
  const res = await fetch(`${API_URL}/qlisan/form`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ word }),
  });
  if (!res.ok) throw new ApiError(`QLisan form failed: ${res.status}`, res.status);
  return res.json();
}

// ── Signed personal readings (/lexical) ───────────────────────────────
// The reader's own reading of a root: a cultural stage in their words and/or the
// alternatives they choose in the Islambouli assembly. Always signed; shown under
// the author's name, never as Islambouli's.
export async function lisanReading(root: string): Promise<LisanReading | null> {
  const res = await fetch(`${API_URL}/lisan/reading/${encodeURIComponent(root)}`);
  if (!res.ok) throw new ApiError(`Reading failed: ${res.status}`, res.status);
  return res.json();
}

export async function saveLisanReading(
  root: string,
  author: string,
  cultural_text: string,
  choices: Record<string, number>,
): Promise<LisanReading> {
  const res = await fetch(`${API_URL}/lisan/reading/${encodeURIComponent(root)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ author, cultural_text, choices }),
  });
  if (!res.ok) throw new ApiError(`Saving the reading failed: ${res.status}`, res.status);
  return res.json();
}

// ── Semantic / hybrid search (find verses close to a phrase) ──────────
export async function searchVerses(
  q: string,
  limit = 20,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  const res = await fetch(`${API_URL}/search?${params.toString()}`);
  if (!res.ok) throw new ApiError(`Search failed: ${res.status}`, res.status);
  return res.json();
}

// ── Verse & surah (deep-linking) ──────────────────────────────────────
export async function getVerse(
  surah: number,
  ayah: number,
  window = 1,
): Promise<VerseDetail> {
  const res = await fetch(
    `${API_URL}/verse/${surah}/${ayah}?window=${window}`,
  );
  if (res.status === 404) throw new ApiError(`Verse ${surah}:${ayah} not found`, res.status);
  if (!res.ok) throw new ApiError(`Verse lookup failed: ${res.status}`, res.status);
  return res.json();
}

export async function getSurah(number: number): Promise<SurahResponse> {
  const res = await fetch(`${API_URL}/surah/${number}`);
  if (res.status === 404) throw new ApiError(`Surah ${number} not found`, res.status);
  if (!res.ok) throw new ApiError(`Surah lookup failed: ${res.status}`, res.status);
  return res.json();
}

export async function getSurahs(): Promise<SurahMeta[]> {
  const res = await fetch(`${API_URL}/surahs`);
  if (!res.ok) throw new ApiError(`Surah list failed: ${res.status}`, res.status);
  return res.json();
}

// ── Intra-surah similarity («داخل سورة») ──────────────────────────────
// Served from a precomputed dataset: no model runs on these routes. Two verses
// are «close» only when they pass BOTH the semantic and the syntactic gate, and
// consecutive verses are never stored — so the client renders what it receives.

/** One group of mutually close verses, verses in ayah order. */
export interface SurahSimilarityGroup {
  ayahs: number[];
  /** Ranking only — never rendered. */
  strength: number;
  verses: Verse[];
}

/** `GET /surah/{n}/similar` — the surah view. */
export interface SurahSimilarityResponse {
  surah_number: number;
  surah_name_ar: string;
  ayah_count: number;
  /** Verses carrying no content word: never compared. */
  unscored: number[];
  /** Strongest first. */
  groups: SurahSimilarityGroup[];
}

/** One close verse of an anchor, with the content roots the two share. */
export interface SimilarNeighbour {
  verse: Verse;
  /** Ranking only — never rendered. */
  score: number;
  roots: string[];
}

/** `GET /surah/{n}/similar?ayah=a` — one verse's close verses, ranked. */
export interface AyahSimilarityResponse {
  surah_number: number;
  surah_name_ar: string;
  ayah_count: number;
  anchor: Verse;
  /** True when the anchor carries no content word (then `neighbours` is empty). */
  unscored: boolean;
  neighbours: SimilarNeighbour[];
}

/**
 * The failure of a similarity request. Its 503 detail is the dataset's rebuild
 * command, so it is kept in the (English, subordinate) message rather than
 * dropped: it is the one actionable line a missing dataset produces.
 */
async function similarityError(res: Response, what: string): Promise<ApiError> {
  let detail = "";
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
  } catch {
    // Not JSON — the status alone is all there is.
  }
  return new ApiError(
    detail ? `${what}: ${res.status} — ${detail}` : `${what}: ${res.status}`,
    res.status,
  );
}

export async function getSurahSimilarity(
  surah: number,
): Promise<SurahSimilarityResponse> {
  const res = await fetch(`${API_URL}/surah/${surah}/similar`);
  if (!res.ok) throw await similarityError(res, `Surah similarity failed`);
  return res.json();
}

export async function getAyahSimilarity(
  surah: number,
  ayah: number,
): Promise<AyahSimilarityResponse> {
  const params = new URLSearchParams({ ayah: String(ayah) });
  const res = await fetch(`${API_URL}/surah/${surah}/similar?${params.toString()}`);
  if (!res.ok) throw await similarityError(res, `Ayah similarity failed`);
  return res.json();
}

// ── Quran-wide similarity («في سائر القرآن») ───────────────────────────
// The same definition of «close» as the intra-surah view, applied across
// surahs: a separate precomputed dataset, so its failure never touches the
// intra view. Every neighbour is in ANOTHER surah, hence its own surah name.

/** `GET /verse/{s}/{a}/similar` — one verse's close verses elsewhere in the Quran, ranked. */
export interface VerseQuranSimilarityResponse {
  anchor: Verse;
  /** True when the anchor carries no content word (then `neighbours` is empty). */
  unscored: boolean;
  neighbours: SimilarNeighbour[];
}

export async function getVerseQuranSimilarity(
  surah: number,
  ayah: number,
): Promise<VerseQuranSimilarityResponse> {
  const res = await fetch(`${API_URL}/verse/${surah}/${ayah}/similar`);
  if (!res.ok) throw await similarityError(res, `Quran-wide similarity failed`);
  return res.json();
}

// ── Surah × surah map («الآيات المتشابهات في سائر القرآن») ──────────────
// The same cross-surah dataset, aggregated per pair of surahs: a cell counts
// the close verse pairs between two surahs. Read at request time, no model.

/** A surah as the matrix names it. */
export interface QuranSimilaritySurah {
  number: number;
  name_ar: string;
}

/** One non-empty cell, `a < b`: its pair count and the verses of each side. */
export interface QuranSimilarityCell {
  a: number;
  b: number;
  pairs: number;
  verses_a: number;
  verses_b: number;
}

/** `GET /quran-similarity/matrix` — all 114 surahs, the non-empty cells only. */
export interface QuranSimilarityMatrix {
  surahs: QuranSimilaritySurah[];
  cells: QuranSimilarityCell[];
  total_pairs: number;
  max_pairs: number;
}

/** One close pair of a cell: `u` in surah `a`, `v` in surah `b`. */
export interface QuranSimilarityPair {
  u: Verse;
  v: Verse;
  /** Ranking only — never rendered. */
  score: number;
  roots: string[];
}

/** `GET /quran-similarity/pairs/{a}/{b}` — one cell's pairs, strongest first. */
export interface QuranSimilarityPairs {
  a: number;
  b: number;
  surah_name_a: string;
  surah_name_b: string;
  /** Distinct verses of each side taking part (0 for an empty cell). */
  verses_a: number;
  verses_b: number;
  pairs: QuranSimilarityPair[];
}

export async function getQuranSimilarityMatrix(): Promise<QuranSimilarityMatrix> {
  const res = await fetch(`${API_URL}/quran-similarity/matrix`);
  if (!res.ok) throw await similarityError(res, `Similarity matrix failed`);
  return res.json();
}

export async function getQuranSimilarityPairs(
  a: number,
  b: number,
): Promise<QuranSimilarityPairs> {
  const res = await fetch(`${API_URL}/quran-similarity/pairs/${a}/${b}`);
  if (!res.ok) throw await similarityError(res, `Similarity pairs failed`);
  return res.json();
}

// ── Root index («فهرس الجذور») ─────────────────────────────────────────
/** The 28 letter groups, in hijāʾī order, each with its number of roots. */
export async function fetchRootLetters(): Promise<RootLettersResponse> {
  const res = await fetch(`${API_URL}/roots`);
  if (!res.ok) throw new ApiError(`Root index failed: ${res.status}`, res.status);
  return res.json();
}

/** One letter group's roots, in full. The backend accepts the group label or
 *  any letter folding into it (ا / ء / إ … → «أ»); an unknown letter is a 404. */
export async function fetchRootsByLetter(
  letter: string,
): Promise<RootLetterResponse> {
  const res = await fetch(`${API_URL}/roots/letter/${encodeURIComponent(letter)}`);
  if (res.status === 404) throw new ApiError(`Unknown root letter: ${letter}`, res.status);
  if (!res.ok) throw new ApiError(`Root letter failed: ${res.status}`, res.status);
  return res.json();
}

// ── Fāṣila (rhyme-letter analysis) ────────────────────────────────────
export async function getFassila(surah: number): Promise<FassilaResponse> {
  const res = await fetch(`${API_URL}/fassila/${surah}`);
  if (res.status === 404) throw new ApiError(`Surah ${surah} not found`, res.status);
  if (!res.ok) throw new ApiError(`Fassila lookup failed: ${res.status}`, res.status);
  return res.json();
}

/** All 114 sūras summarized in one call — the cross-sūra comparison tab's whole payload. */
export async function getFassilaOverview(): Promise<FassilaOverviewResponse> {
  const res = await fetch(`${API_URL}/fassila/overview`);
  if (!res.ok) throw new ApiError(`Fassila overview failed: ${res.status}`, res.status);
  return res.json();
}

// ── Feedback (👍/👎) ──────────────────────────────────────────────────
export async function sendFeedback(payload: {
  session_id: string;
  message_index: number;
  rating: "up" | "down";
  question?: string;
  answer?: string;
}): Promise<{ ok: boolean; stats: FeedbackStats }> {
  const res = await fetch(`${API_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new ApiError(`Feedback failed: ${res.status}`, res.status);
  return res.json();
}

// ── Chat (streaming SSE) ──────────────────────────────────────────────
interface StreamHandlers {
  sessionId?: string;
  onToken?: (token: string) => void;
  onSources?: (sources: Verse[]) => void;
  onDone?: (sessionId?: string) => void;
  signal?: AbortSignal;
}

/**
 * POST /chat/stream and consume the Server-Sent Events stream.
 * Each SSE line is `data: {json}`; payloads are tagged by `type`.
 *
 * `sessionId` is sent so the backend persists the turn under a stable id
 * (the frontend reuses the conversation id), making server-side history and
 * feedback reference the same session.
 */
export async function streamChat(
  messages: ChatMessage[],
  handlers: StreamHandlers = {},
): Promise<void> {
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, session_id: handlers.sessionId }),
    signal: handlers.signal,
  });
  if (!res.ok || !res.body) throw new ApiError(`Chat failed: ${res.status}`, res.status);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by a blank line.
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const evt of events) {
      const line = evt.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      let payload: any;
      try {
        payload = JSON.parse(line.slice(6));
      } catch {
        continue;
      }
      if (payload.type === "token") handlers.onToken?.(payload.content);
      else if (payload.type === "sources") handlers.onSources?.(payload.sources);
      else if (payload.type === "done") handlers.onDone?.(payload.session_id);
    }
  }
}

// ── Health ────────────────────────────────────────────────────────────
export async function health(): Promise<HealthStatus> {
  const res = await fetch(`${API_URL}/health`);
  if (!res.ok) throw new ApiError(`Health check failed: ${res.status}`, res.status);
  return res.json();
}
