import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createConversation,
  deleteConversation,
  deriveTitle,
  getActiveId,
  getConversation,
  listConversations,
  loadStore,
  saveMessages,
  setActiveId,
  type StoredMessage,
} from "./conversations";

// localStorage is cleared after every test by vitest.setup.ts, so each test
// starts from empty storage. We only restore timers locally where used.

const verse = {
  id: "2:153",
  surah_number: 2,
  ayah_number: 153,
  surah_name_ar: "البقرة",
  surah_name_en: "Al-Baqarah",
  text_ar: "يا أيها الذين آمنوا استعينوا بالصبر",
};

describe("conversations storage", () => {
  it("starts empty", () => {
    expect(loadStore().conversations).toHaveLength(0);
    expect(getActiveId()).toBeNull();
    expect(listConversations()).toHaveLength(0);
  });

  it("createConversation creates and marks it active", () => {
    const c = createConversation();
    expect(getActiveId()).toBe(c.id);
    expect(listConversations()).toHaveLength(1);
    expect(loadStore().conversations[0].messages).toHaveLength(0);
  });

  it("saveMessages persists user + assistant turns with sources", () => {
    const c = createConversation();
    const messages: StoredMessage[] = [
      { role: "user", content: "patience?" },
      { role: "assistant", content: "See 2:153.", sources: [verse] },
    ];
    saveMessages(c.id, messages);

    const restored = getConversation(c.id);
    expect(restored?.messages).toHaveLength(2);
    expect(restored?.messages[1].sources?.[0].id).toBe("2:153");
  });

  it("saveMessages derives the title from the first user message", () => {
    const c = createConversation();
    saveMessages(c.id, [{ role: "user", content: "What is rahma?" }]);
    expect(listConversations()[0].title).toBe("What is rahma?");
  });

  it("saveMessages on an unknown id is a no-op (no throw)", () => {
    expect(() => saveMessages("nope", [])).not.toThrow();
    expect(listConversations()).toHaveLength(0);
  });

  it("sorts conversations by most recently updated first", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(1000));
    const a = createConversation();
    saveMessages(a.id, [{ role: "user", content: "A" }]);
    vi.setSystemTime(new Date(5000));
    const b = createConversation();
    saveMessages(b.id, [{ role: "user", content: "B" }]);
    vi.useRealTimers();

    const list = listConversations();
    expect(list.map((c) => c.id)).toEqual([b.id, a.id]);
  });

  it("setActiveId / getActiveId switch the active conversation", () => {
    const a = createConversation();
    const b = createConversation();
    expect(getActiveId()).toBe(b.id);
    setActiveId(a.id);
    expect(getActiveId()).toBe(a.id);
  });

  it("deleting the ACTIVE conversation clears the active id", () => {
    const a = createConversation();
    saveMessages(a.id, [{ role: "user", content: "A" }]);
    deleteConversation(a.id);
    expect(listConversations()).toHaveLength(0);
    expect(getActiveId()).toBeNull();
  });

  it("deleting a NON-active conversation leaves the active id untouched", () => {
    const a = createConversation();
    const b = createConversation(); // b is now active
    deleteConversation(a.id);
    expect(getActiveId()).toBe(b.id);
    expect(listConversations()).toHaveLength(1);
  });

  it("getConversation returns null for an unknown id", () => {
    expect(getConversation("missing")).toBeNull();
  });
});

describe("deriveTitle", () => {
  it("uses the first non-empty user message", () => {
    expect(
      deriveTitle([
        { role: "assistant", content: "hi" },
        { role: "user", content: "real question" },
      ]),
    ).toBe("real question");
  });

  it("truncates titles longer than 48 chars with an ellipsis", () => {
    const long = "a".repeat(80);
    const title = deriveTitle([{ role: "user", content: long }]);
    expect(title.endsWith("…")).toBe(true);
    expect(title.length).toBeLessThanOrEqual(49); // 48 chars + ellipsis
  });

  it("collapses whitespace", () => {
    expect(deriveTitle([{ role: "user", content: "  a   b  " }])).toBe("a b");
  });

  it("falls back when there is no user message", () => {
    expect(deriveTitle([])).toBe("New conversation");
    expect(deriveTitle([{ role: "assistant", content: "x" }])).toBe(
      "New conversation",
    );
  });
});

describe("resilience", () => {
  it("recovers from corrupt JSON in storage", () => {
    localStorage.setItem("quran-rag.chat.v1", "{ not json");
    expect(loadStore().conversations).toHaveLength(0);
    expect(listConversations()).toHaveLength(0);
  });

  it("recovers from an unknown schema version", () => {
    localStorage.setItem(
      "quran-rag.chat.v1",
      JSON.stringify({ version: 99, conversations: [] }),
    );
    expect(loadStore().conversations).toHaveLength(0);
  });

  it("tolerates a full quota (setItem throws) without crashing", () => {
    const c = createConversation();
    const spy = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("QuotaExceededError");
      });
    expect(() => saveMessages(c.id, [{ role: "user", content: "x" }])).not.toThrow();
    expect(() => createConversation()).not.toThrow();
    spy.mockRestore();
  });
});

afterEach(() => {
  vi.useRealTimers();
});
