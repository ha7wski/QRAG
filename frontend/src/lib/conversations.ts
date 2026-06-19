// Local persistence for chat conversations (F1).
//
// The backend /chat endpoints are stateless: each request resends the full
// message history. So conversations live entirely in the browser's
// localStorage here — including each assistant turn's cited `sources`, so a
// reload restores the verses too, not just the text. Frontend-only; no backend
// change. All access is SSR-safe (guards `window`) and tolerant of corrupt or
// quota-exceeded storage (best-effort).

import type { Verse } from "./types";

const STORAGE_KEY = "quran-rag.chat.v1";
const TITLE_MAX = 48;

/** A chat message as stored/rendered (assistant turns may carry sources). */
export interface StoredMessage {
  role: "user" | "assistant";
  content: string;
  sources?: Verse[];
}

export interface Conversation {
  id: string;
  title: string;
  messages: StoredMessage[];
  createdAt: number;
  updatedAt: number;
}

/** Lightweight projection for the conversation switcher list. */
export interface ConversationMeta {
  id: string;
  title: string;
  updatedAt: number;
}

interface Store {
  version: 1;
  activeId: string | null;
  conversations: Conversation[];
}

const emptyStore = (): Store => ({
  version: 1,
  activeId: null,
  conversations: [],
});

function newId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `c_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function loadStore(): Store {
  if (typeof window === "undefined") return emptyStore();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyStore();
    const parsed = JSON.parse(raw);
    if (
      !parsed ||
      parsed.version !== 1 ||
      !Array.isArray(parsed.conversations)
    ) {
      return emptyStore();
    }
    return parsed as Store;
  } catch {
    return emptyStore();
  }
}

function saveStore(store: Store): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    // Storage disabled or over quota — persistence is best-effort.
  }
}

/** Derive a conversation title from its first non-empty user message. */
export function deriveTitle(messages: StoredMessage[]): string {
  const firstUser = messages.find(
    (m) => m.role === "user" && m.content.trim(),
  );
  if (!firstUser) return "New conversation";
  const text = firstUser.content.trim().replace(/\s+/g, " ");
  return text.length > TITLE_MAX
    ? `${text.slice(0, TITLE_MAX).trimEnd()}…`
    : text;
}

/** Conversations as metadata, most recently updated first. */
export function listConversations(store?: Store): ConversationMeta[] {
  const s = store ?? loadStore();
  return [...s.conversations]
    .sort((a, b) => b.updatedAt - a.updatedAt || b.createdAt - a.createdAt)
    .map(({ id, title, updatedAt }) => ({ id, title, updatedAt }));
}

export function getActiveId(): string | null {
  return loadStore().activeId;
}

export function setActiveId(id: string | null): void {
  const s = loadStore();
  s.activeId = id;
  saveStore(s);
}

export function getConversation(id: string): Conversation | null {
  return loadStore().conversations.find((c) => c.id === id) ?? null;
}

/** Create an empty conversation and mark it active. */
export function createConversation(): Conversation {
  const now = Date.now();
  const conv: Conversation = {
    id: newId(),
    title: "New conversation",
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
  const s = loadStore();
  s.conversations.push(conv);
  s.activeId = conv.id;
  saveStore(s);
  return conv;
}

/** Replace a conversation's messages, refresh its title and timestamp. */
export function saveMessages(id: string, messages: StoredMessage[]): void {
  const s = loadStore();
  const conv = s.conversations.find((c) => c.id === id);
  if (!conv) return;
  conv.messages = messages;
  conv.title = deriveTitle(messages);
  conv.updatedAt = Date.now();
  s.activeId = id;
  saveStore(s);
}

export function deleteConversation(id: string): void {
  const s = loadStore();
  s.conversations = s.conversations.filter((c) => c.id !== id);
  if (s.activeId === id) s.activeId = null;
  saveStore(s);
}
