"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronLeft, Loader2, Search } from "lucide-react";
import { searchVerses, verseLookup } from "@/lib/api";
import type {
  SearchResponse,
  VerseLookupResponse,
  VerseLookupVerse,
} from "@/lib/types";

/** Render a vocalized verse, highlighting the matched-root tokens in place. */
function HighlightedVerse({
  text,
  indices,
}: {
  text: string;
  indices: number[];
}) {
  const set = new Set(indices);
  const tokens = text.trim().split(/\s+/);
  return (
    <>
      {tokens.map((tok, i) => (
        <span key={i}>
          {set.has(i) ? (
            <span className="rounded-md bg-brand/15 px-1 text-brand-dark ring-1 ring-brand/40 box-decoration-clone">
              {tok}
            </span>
          ) : (
            tok
          )}
          {i < tokens.length - 1 ? " " : ""}
        </span>
      ))}
    </>
  );
}

type Tab = "word" | "similar";

export default function VerseStudyPage() {
  const [tab, setTab] = useState<Tab>("word");

  const tabs: [Tab, string][] = [
    ["word", "Word in Verses"],
    ["similar", "Similar Verses"],
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">Verse Study</h1>
        <p className="mt-1 text-sm text-gray-500">
          Type a single Arabic word — see every verse where its root appears,
          fully vocalized.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-6 border-b border-gray-200">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`-mb-px border-b-2 px-1 py-2 text-sm font-medium transition ${
              tab === key
                ? "border-brand text-brand-dark"
                : "border-transparent text-gray-500 hover:text-gray-800"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Both stay mounted so switching tabs preserves each one's results. */}
      <div className={tab === "word" ? "" : "hidden"}>
        <WordInVerses />
      </div>
      <div className={tab === "similar" ? "" : "hidden"}>
        <SimilarVerses />
      </div>
    </div>
  );
}

/** Tab 1 — one Arabic word → every verse of its root, grouped by surah. */
function WordInVerses() {
  const [word, setWord] = useState("");
  const [data, setData] = useState<VerseLookupResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Surah numbers whose section is collapsed.
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());

  async function run() {
    if (!word.trim() || loading) return;
    setLoading(true);
    setError(null);
    setCollapsed(new Set());
    try {
      setData(await verseLookup(word.trim()));
    } catch (e: any) {
      setError(e?.message || "Lookup failed");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  // Group verses by surah, preserving canonical order (backend already sorted).
  const groups = useMemo(() => {
    const out: { number: number; name: string; verses: VerseLookupVerse[] }[] = [];
    const byNum = new Map<number, number>(); // surah number -> index in out
    for (const v of data?.verses ?? []) {
      if (!byNum.has(v.surah_number)) {
        byNum.set(v.surah_number, out.length);
        out.push({ number: v.surah_number, name: v.surah_name, verses: [] });
      }
      out[byNum.get(v.surah_number)!].verses.push(v);
    }
    return out;
  }, [data]);

  function toggle(num: number) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.has(num) ? next.delete(num) : next.add(num);
      return next;
    });
  }

  return (
    <div className="space-y-6">
      {/* Live, non-editable Arabic question (RTL). */}
      <div dir="rtl" className="font-arabic text-xl text-gray-800" lang="ar">
        {word.trim() ? (
          <>
            ما هي الآيات والسور التي وردت فيها{" "}
            <span className="font-bold text-brand-dark">
              &laquo;{word.trim()}&raquo;
            </span>{" "}
            ؟
          </>
        ) : (
          <span className="text-gray-400">
            ما هي الآيات والسور التي وردت فيها «…» ؟
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={word}
          onChange={(e) => setWord(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          dir="rtl"
          placeholder="اكتب كلمة عربية"
          className="min-w-[200px] flex-1 rounded-lg border border-gray-300 px-3 py-2 font-arabic text-xl focus:border-brand focus:outline-none"
        />
        <button
          onClick={run}
          disabled={loading || !word.trim()}
          className="flex items-center gap-1.5 rounded-lg bg-brand px-5 py-2 font-arabic text-lg text-white disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          بحث
        </button>
      </div>

      {error && (
        <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>جارٍ البحث…</span>
        </div>
      )}

      {data && !loading && (
        <div className="space-y-4">
          {!data.root_found ? (
            <div
              dir="rtl"
              lang="ar"
              className="rounded-lg bg-amber-50 px-4 py-3 font-arabic text-lg text-amber-800"
            >
              لم يُعثر على هذه الكلمة في الجذور المعروفة
            </div>
          ) : (
            <>
              {/* Summary + root */}
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-gray-100 px-4 py-3">
                <span
                  dir="rtl"
                  lang="ar"
                  className="font-arabic text-lg text-gray-800"
                >
                  {data.total} آية في {groups.length} سورة
                </span>
                <span dir="rtl" lang="ar" className="font-arabic text-gray-600">
                  الجذر:{" "}
                  <span className="font-bold tracking-widest">{data.root}</span>
                </span>
              </div>

              {/* Collapsible surah groups */}
              {groups.map((g) => {
                const isCollapsed = collapsed.has(g.number);
                return (
                  <div
                    key={g.number}
                    className="overflow-hidden rounded-lg border border-gray-200"
                  >
                    <button
                      onClick={() => toggle(g.number)}
                      dir="rtl"
                      className="flex w-full items-center justify-between bg-gray-50 px-4 py-2.5 text-right hover:bg-gray-100"
                    >
                      <span
                        dir="rtl"
                        className="flex items-baseline gap-2 font-arabic text-lg"
                      >
                        <span className="text-gray-600">
                          {g.verses.length} آية
                        </span>
                        <span className="font-semibold text-gray-800">
                          {g.name}
                        </span>
                        <span className="text-sm text-gray-400">{g.number}</span>
                      </span>
                      {isCollapsed ? (
                        <ChevronLeft className="h-4 w-4 text-gray-400" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-gray-400" />
                      )}
                    </button>

                    {!isCollapsed && (
                      <ul className="divide-y divide-gray-100">
                        {g.verses.map((v) => (
                          <li key={v.aya_number} className="px-4 py-3">
                            <div
                              dir="rtl"
                              lang="ar"
                              className="arabic-text text-2xl text-gray-900"
                            >
                              <HighlightedVerse
                                text={v.text}
                                indices={v.match_indices}
                              />{" "}
                              <span className="align-middle text-sm text-gray-400">
                                ﴿{v.aya_number}﴾
                              </span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </>
          )}
        </div>
      )}
    </div>
  );
}

/** Tab 2 — an Arabic phrase (even a partial verse) → semantically closest verses. */
function SimilarVerses() {
  const [query, setQuery] = useState("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      setData(await searchVerses(query.trim(), 20));
    } catch (e: any) {
      setError(e?.message || "Search failed");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Live, non-editable Arabic question (RTL). */}
      <div dir="rtl" className="font-arabic text-xl text-gray-800" lang="ar">
        {query.trim() ? (
          <>
            ما هي الآيات القريبة في المعنى من{" "}
            <span className="font-bold text-brand-dark">
              &laquo;{query.trim()}&raquo;
            </span>{" "}
            ؟
          </>
        ) : (
          <span className="text-gray-400">
            ما هي الآيات القريبة في المعنى من «…» ؟
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          dir="rtl"
          placeholder="اكتب آية أو عبارة"
          className="min-w-[200px] flex-1 rounded-lg border border-gray-300 px-3 py-2 font-arabic text-xl focus:border-brand focus:outline-none"
        />
        <button
          onClick={run}
          disabled={loading || !query.trim()}
          className="flex items-center gap-1.5 rounded-lg bg-brand px-5 py-2 font-arabic text-lg text-white disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          بحث
        </button>
      </div>

      <p className="text-xs text-gray-400">
        Hybrid semantic + keyword search across all 6236 verses — returns the
        closest matches, ranked (top 20).
      </p>

      {error && (
        <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>جارٍ البحث…</span>
        </div>
      )}

      {data && !loading && (
        <div className="space-y-4">
          {data.results.length === 0 ? (
            <div
              dir="rtl"
              lang="ar"
              className="rounded-lg bg-amber-50 px-4 py-3 font-arabic text-lg text-amber-800"
            >
              لم يُعثر على آيات قريبة
            </div>
          ) : (
            <>
              <div dir="rtl" className="rounded-lg bg-gray-100 px-4 py-3 text-right">
                <span lang="ar" className="font-arabic text-lg text-gray-800">
                  أقرب {data.results.length} آية
                </span>
              </div>
              <div className="space-y-3">
                {data.results.map((v) => (
                  <article
                    key={v.id}
                    dir="rtl"
                    className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
                  >
                    {/* Surah name (Arabic) on the right + reference; no translations. */}
                    <header className="mb-2 flex items-center justify-between gap-2">
                      <span className="flex items-baseline gap-2 font-arabic text-lg">
                        <span className="font-semibold text-gray-800">
                          {v.surah_name_ar}
                        </span>
                        <span className="text-sm text-gray-400">
                          {v.surah_number}:{v.ayah_number}
                        </span>
                      </span>
                      {typeof v.relevance_score === "number" && (
                        <span dir="ltr" className="text-xs text-gray-300">
                          {v.relevance_score.toFixed(3)}
                        </span>
                      )}
                    </header>
                    <div
                      dir="rtl"
                      lang="ar"
                      className="arabic-text text-2xl leading-loose text-gray-900"
                    >
                      {v.text_ar_tashkil || v.text_ar}{" "}
                      <span className="align-middle text-sm text-gray-400">
                        ﴿{v.ayah_number}﴾
                      </span>
                    </div>
                  </article>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
