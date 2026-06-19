"use client";

import { useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  Loader2,
  MessageSquare,
  Plus,
  RotateCw,
  Send,
  ThumbsDown,
  ThumbsUp,
  Trash2,
} from "lucide-react";
import { sendFeedback, streamChat } from "@/lib/api";
import type { ChatMessage, Verse } from "@/lib/types";
import HealthBanner from "./HealthBanner";
import {
  type ConversationMeta,
  type StoredMessage,
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  saveMessages,
  setActiveId as storeSetActiveId,
} from "@/lib/conversations";
import VerseCard from "./VerseCard";

function relativeTime(ts: number): string {
  const s = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<StoredMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Conversation persistence (localStorage). `activeId` is the open conversation;
  // `activeIdRef` mirrors it so async stream callbacks read the current value.
  const [conversations, setConversations] = useState<ConversationMeta[]>([]);
  const [activeId, setActiveConvId] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const activeIdRef = useRef<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // Thumbs ratings, keyed by `${conversationId}:${messageIndex}`. UI-local;
  // the backend is the durable source of truth for the KPI.
  const [ratings, setRatings] = useState<Record<string, "up" | "down">>({});
  // The last question asked, so a failed/interrupted stream can be retried.
  const lastQuestionRef = useRef<string | null>(null);

  const refreshList = () => setConversations(listConversations());

  // The Chat tab always opens a fresh chat. We only load the saved-conversation
  // list (for the switcher) — the user explicitly picks one to reopen. Runs
  // after hydration since localStorage is unavailable during SSR.
  useEffect(() => {
    setConversations(listConversations());
  }, []);

  // Close the conversation menu on an outside click.
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [menuOpen]);

  const scrollToEnd = () =>
    requestAnimationFrame(() =>
      endRef.current?.scrollIntoView({ behavior: "smooth" }),
    );

  function newConversation() {
    setMessages([]);
    setActiveConvId(null);
    activeIdRef.current = null;
    storeSetActiveId(null);
    setError(null);
    setMenuOpen(false);
  }

  function switchTo(id: string) {
    const conv = getConversation(id);
    if (!conv) return;
    setMessages(conv.messages);
    setActiveConvId(id);
    activeIdRef.current = id;
    storeSetActiveId(id);
    setError(null);
    setMenuOpen(false);
  }

  function removeConversation(id: string) {
    deleteConversation(id);
    refreshList();
    if (id === activeIdRef.current) {
      setMessages([]);
      setActiveConvId(null);
      activeIdRef.current = null;
    }
  }

  // Re-send the last question after a failure. Drops the failed trailing
  // exchange (last user turn onward) so retrying doesn't duplicate it.
  function retry() {
    const q = lastQuestionRef.current;
    if (!q || loading) return;
    const lastUser = messages.map((m) => m.role).lastIndexOf("user");
    const base = lastUser >= 0 ? messages.slice(0, lastUser) : messages;
    send(q, base);
  }

  async function send(explicitQuestion?: string, baseOverride?: StoredMessage[]) {
    const question = (explicitQuestion ?? input).trim();
    if (!question || loading) return;
    setError(null);
    lastQuestionRef.current = question;
    if (explicitQuestion === undefined) setInput("");

    // Ensure there is an active conversation to write into.
    let convId = activeIdRef.current;
    if (!convId) {
      const conv = createConversation();
      convId = conv.id;
      activeIdRef.current = conv.id;
      setActiveConvId(conv.id);
    }

    // Prior conversation this question builds on (retry trims the failed turn).
    const base = baseOverride ?? messages;
    // History for the backend (role/content only — sources are UI-only).
    const history: ChatMessage[] = [
      ...base.map((m) => ({ role: m.role, content: m.content })),
      { role: "user", content: question },
    ];
    // Prior turns (with their sources) + this user turn — the persistence base.
    const priorPlusUser: StoredMessage[] = [
      ...base,
      { role: "user", content: question },
    ];

    // Render the user message + an empty assistant placeholder.
    setMessages([...priorPlusUser, { role: "assistant", content: "" }]);
    setLoading(true);
    scrollToEnd();
    // Persist the user turn immediately so a mid-stream reload keeps the question.
    saveMessages(convId, priorPlusUser);
    refreshList();

    // Accumulate the assistant turn deterministically so persistence never
    // depends on reading async React state.
    let answer = "";
    let sources: Verse[] = [];

    const appendToLast = (token: string) =>
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          ...next[next.length - 1],
          content: next[next.length - 1].content + token,
        };
        return next;
      });

    const setSourcesOnLast = (s: Verse[]) =>
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { ...next[next.length - 1], sources: s };
        return next;
      });

    try {
      await streamChat(history, {
        sessionId: convId,
        onToken: (t) => {
          answer += t;
          appendToLast(t);
          scrollToEnd();
        },
        onSources: (s) => {
          sources = s;
          setSourcesOnLast(s);
        },
        onDone: () => {
          const final: StoredMessage[] = [
            ...priorPlusUser,
            {
              role: "assistant",
              content: answer,
              ...(sources.length ? { sources } : {}),
            },
          ];
          saveMessages(convId!, final);
          refreshList();
          setLoading(false);
        },
      });
    } catch (e: any) {
      setError(e?.message || "Request failed");
      setLoading(false);
      // Persist whatever streamed before the failure so a partial answer (and
      // the question) survive a reload; the user can retry from the banner.
      const partial: StoredMessage[] = [
        ...priorPlusUser,
        ...(answer
          ? [
              {
                role: "assistant" as const,
                content: answer,
                ...(sources.length ? { sources } : {}),
              },
            ]
          : []),
      ];
      saveMessages(convId!, partial);
      refreshList();
    }
  }

  async function rate(messageIndex: number, rating: "up" | "down") {
    // Use the `activeId` state (not the ref) so the optimistic key matches the
    // key the render reads — they must come from the same source.
    const convId = activeId;
    if (!convId) return;
    const key = `${convId}:${messageIndex}`;
    setRatings((r) => ({ ...r, [key]: rating })); // optimistic
    try {
      await sendFeedback({
        session_id: convId,
        message_index: messageIndex,
        rating,
        question: messages[messageIndex - 1]?.content ?? "",
        answer: messages[messageIndex]?.content ?? "",
      });
    } catch {
      // Best-effort: roll back the optimistic mark on failure.
      setRatings((r) => {
        const next = { ...r };
        delete next[key];
        return next;
      });
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <HealthBanner />

      {/* Conversation controls: switcher, with "New" stacked underneath. */}
      <div className="mb-3 flex flex-col items-start gap-2">
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen((o) => !o)}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <MessageSquare className="h-4 w-4" />
            Conversations
            <ChevronDown className="h-4 w-4" />
          </button>
          {menuOpen && (
            <div className="absolute z-10 mt-1 max-h-80 w-72 overflow-y-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
              {conversations.length === 0 ? (
                <p className="px-3 py-2 text-sm text-gray-400">
                  No saved conversations
                </p>
              ) : (
                conversations.map((c) => (
                  <div
                    key={c.id}
                    className={`group flex items-center gap-1 px-1 ${
                      c.id === activeId ? "bg-brand/5" : ""
                    }`}
                  >
                    <button
                      onClick={() => switchTo(c.id)}
                      className="min-w-0 flex-1 rounded px-2 py-2 text-left hover:bg-gray-50"
                    >
                      <span className="block truncate text-sm text-gray-800">
                        {c.title}
                      </span>
                      <span className="block text-xs text-gray-400">
                        {relativeTime(c.updatedAt)}
                      </span>
                    </button>
                    <button
                      onClick={() => removeConversation(c.id)}
                      aria-label="Delete conversation"
                      className="rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        <button
          onClick={newConversation}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-sm text-white hover:opacity-90 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          New
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 && (
          <div className="mt-10 text-center text-gray-500">
            <p className="text-lg">Ask a question about the Quran.</p>
            <p className="mt-1 text-sm">
              e.g. &quot;What does the Quran say about patience?&quot;
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div
              className={
                m.role === "user"
                  ? "inline-block max-w-[85%] rounded-2xl bg-brand px-4 py-2 text-white"
                  : "inline-block max-w-full rounded-2xl bg-gray-100 px-4 py-2 text-gray-900"
              }
            >
              <span className="whitespace-pre-wrap">{m.content}</span>
              {m.role === "assistant" && loading && i === messages.length - 1 && (
                <Loader2 className="ml-1 inline h-4 w-4 animate-spin text-gray-400" />
              )}
            </div>

            {m.sources && m.sources.length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                  Sources
                </p>
                {m.sources.map((v) => (
                  <VerseCard key={v.id} verse={v} />
                ))}
              </div>
            )}

            {/* Per-answer affordances: only on a completed assistant turn. */}
            {m.role === "assistant" &&
              m.content &&
              !(loading && i === messages.length - 1) && (
                <div className="mt-2 flex items-center gap-3">
                  {(!m.sources || m.sources.length === 0) && (
                    <span className="text-xs text-gray-400">
                      No verses matched — general answer.
                    </span>
                  )}
                  <div className="ml-auto flex items-center gap-1">
                    {(["up", "down"] as const).map((r) => {
                      const active = ratings[`${activeId}:${i}`] === r;
                      const Icon = r === "up" ? ThumbsUp : ThumbsDown;
                      return (
                        <button
                          key={r}
                          onClick={() => rate(i, r)}
                          aria-label={r === "up" ? "Helpful" : "Not helpful"}
                          className={`rounded p-1 hover:bg-gray-100 ${
                            active
                              ? r === "up"
                                ? "text-green-600"
                                : "text-red-600"
                              : "text-gray-300 hover:text-gray-500"
                          }`}
                        >
                          <Icon className="h-4 w-4" />
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {error && (
        <div className="mb-2 flex items-center justify-between gap-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          <span>{error}</span>
          {lastQuestionRef.current && !loading && (
            <button
              onClick={retry}
              className="flex shrink-0 items-center gap-1 rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
            >
              <RotateCw className="h-3.5 w-3.5" /> Retry
            </button>
          )}
        </div>
      )}

      <div className="flex items-end gap-2 border-t border-gray-200 pt-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          rows={1}
          placeholder="Type your question..."
          className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 focus:border-brand focus:outline-none"
        />
        <button
          onClick={() => send()}
          disabled={loading || !input.trim()}
          className="flex items-center gap-1 rounded-lg bg-brand px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}
