// API client for the Quran RAG backend.
import type {
  ChatMessage,
  FeedbackStats,
  HealthStatus,
  LexicalResponse,
  SearchResponse,
  SurahMeta,
  SurahResponse,
  Verse,
  VerseDetail,
  VerseLookupResponse,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Lexical ───────────────────────────────────────────────────────────
export async function lexical(
  word: string,
  language: string = "en",
): Promise<LexicalResponse> {
  const res = await fetch(`${API_URL}/lexical`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ word, language }),
  });
  if (!res.ok) throw new Error(`Lexical lookup failed: ${res.status}`);
  return res.json();
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
  if (!res.ok) throw new Error(`Verse lookup failed: ${res.status}`);
  return res.json();
}

// ── Semantic / hybrid search (find verses close to a phrase) ──────────
export async function searchVerses(
  q: string,
  limit = 20,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  const res = await fetch(`${API_URL}/search?${params.toString()}`);
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
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
  if (res.status === 404) throw new Error(`Verse ${surah}:${ayah} not found`);
  if (!res.ok) throw new Error(`Verse lookup failed: ${res.status}`);
  return res.json();
}

export async function getSurah(number: number): Promise<SurahResponse> {
  const res = await fetch(`${API_URL}/surah/${number}`);
  if (res.status === 404) throw new Error(`Surah ${number} not found`);
  if (!res.ok) throw new Error(`Surah lookup failed: ${res.status}`);
  return res.json();
}

export async function getSurahs(): Promise<SurahMeta[]> {
  const res = await fetch(`${API_URL}/surahs`);
  if (!res.ok) throw new Error(`Surah list failed: ${res.status}`);
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
  if (!res.ok) throw new Error(`Feedback failed: ${res.status}`);
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
  if (!res.ok || !res.body) throw new Error(`Chat failed: ${res.status}`);

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
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
