"use client";

import {
  type Dispatch,
  type SetStateAction,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ChevronDown,
  ChevronLeft,
  Loader2,
  Search,
  Type,
} from "lucide-react";
import {
  detailOf,
  getSurahs,
  getVerse,
  searchVerses,
  statusOf,
  verseLookup,
} from "@/lib/api";
import type {
  SearchResponse,
  SurahMeta,
  Verse,
  VerseDetail,
  VerseLookupResponse,
  VerseLookupVerse,
} from "@/lib/types";
import { useCachedState } from "@/lib/pageCache";
import { S, forStatus } from "@/lib/strings";
import FailureNote, { type Failure } from "@/components/FailureNote";
import ScrollToTop from "@/components/ScrollToTop";
import VerseContextCard from "@/components/VerseContextCard";

// Context shown around the chosen verse in the "Find Verse context" tab:
// 3 before + 3 after (same surah).
const CONTEXT_WINDOW = 3;

/** A verse targeted for the context tab. `nonce` monotonically increases on every
 *  open request so clicking the SAME verse twice still re-triggers a load (we never
 *  rely on value-equality of surah/ayah). */
type ContextTarget = { surah: number; ayah: number; nonce: number };

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

type Tab = "word" | "similar" | "context";

// useSearchParams() must sit under a Suspense boundary (App Router requirement).
export default function VerseStudyPage() {
  return (
    <Suspense fallback={null}>
      <VerseStudy />
    </Suspense>
  );
}

function VerseStudy() {
  // Cached: coming back from Lisan Analysis lands on the tab you left, not on
  // "Word in Verses". The context TARGET is deliberately not cached — it is a
  // one-shot "open this verse" signal, and FindVerseContext restores its own
  // result directly.
  const [tab, setTab] = useCachedState<Tab>("verse-study.tab", "word");
  // The verse (if any) requested for the context tab from another tab or a deep link.
  const [contextTarget, setContextTarget] = useState<ContextTarget | null>(null);

  // Identities stay `word` / `similar` / `context`; only the labels are Arabic.
  // They read right-to-left in this order, so `word` is the rightmost tab.
  const tabs: [Tab, string][] = [
    ["word", S.verseStudy.tabs.word],
    ["similar", S.verseStudy.tabs.similar],
    ["context", S.verseStudy.tabs.context],
  ];

  // Open a verse in the context tab. Bump the nonce via a functional update so
  // re-clicking the same verse always re-triggers a load in FindVerseContext.
  function openInContext(surah: number, ayah: number) {
    setContextTarget((prev) => ({
      surah,
      ayah,
      nonce: (prev?.nonce ?? 0) + 1,
    }));
    setTab("context");
  }

  // Deep-link: ?surah=&ayah= selects the context tab and auto-loads that verse.
  const params = useSearchParams();
  useEffect(() => {
    const s = Number(params.get("surah"));
    const a = Number(params.get("ayah"));
    if (s && a) {
      setContextTarget({ surah: s, ayah: a, nonce: 1 });
      setTab("context");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">
          {S.verseStudy.heading}
        </h1>
        <p className="mt-1 text-sm text-gray-500">{S.verseStudy.caption}</p>
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

      {/* All three stay mounted so switching tabs preserves each one's results. */}
      <div className={tab === "word" ? "" : "hidden"}>
        <WordInVerses openInContext={openInContext} />
      </div>
      <div className={tab === "similar" ? "" : "hidden"}>
        <SimilarVerses />
      </div>
      <div className={tab === "context" ? "" : "hidden"}>
        <FindVerseContext target={contextTarget} />
      </div>

      <ScrollToTop />
    </div>
  );
}

/** Group a lemma's verses by surah, preserving canonical order (backend sorted). */
function groupBySurah(verses: VerseLookupVerse[]) {
  const out: { number: number; name: string; verses: VerseLookupVerse[] }[] = [];
  const byNum = new Map<number, number>(); // surah number -> index in out
  for (const v of verses) {
    if (!byNum.has(v.surah_number)) {
      byNum.set(v.surah_number, out.length);
      out.push({ number: v.surah_number, name: v.surah_name, verses: [] });
    }
    out[byNum.get(v.surah_number)!].verses.push(v);
  }
  return out;
}

/** One surah's verses, independently collapsible (default open). */
function SurahCard({
  group,
  open,
  onToggle,
  openInContext,
}: {
  group: { number: number; name: string; verses: VerseLookupVerse[] };
  open: boolean;
  onToggle: () => void;
  openInContext: (surah: number, ayah: number) => void;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <button
        onClick={onToggle}
        dir="rtl"
        className="flex w-full items-center justify-between bg-gray-50 px-4 py-2.5 text-right hover:bg-gray-100"
      >
        {/* Format: «اسم السورة (رقم)، عدد الآيات : N» */}
        <span dir="rtl" className="font-arabic text-lg">
          <span className="font-semibold text-gray-800">{group.name}</span>
          <span className="text-gray-400">
            {" "}
            <span dir="ltr">({group.number})</span>
          </span>
          <span className="text-gray-600">
            ، عدد الآيات : {group.verses.length}
          </span>
        </span>
        {open ? (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronLeft className="h-4 w-4 text-gray-400" />
        )}
      </button>
      {open && (
        <ul className="divide-y divide-gray-100">
          {group.verses.map((v) => (
            <li key={v.aya_number}>
              {/* Whole verse is clickable → open it in the context tab in-page. */}
              <button
                type="button"
                onClick={() => openInContext(v.surah_number, v.aya_number)}
                title={S.verseStudy.openInContext}
                className="block w-full px-4 py-3 text-right transition hover:bg-brand-light/50"
              >
                <div
                  dir="rtl"
                  lang="ar"
                  className="arabic-text text-2xl text-gray-900"
                >
                  <HighlightedVerse text={v.text} indices={v.match_indices} />{" "}
                  <span className="align-middle text-sm text-gray-400">
                    ﴿{v.aya_number}﴾
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Tab 1 — one Arabic word → its root's verses, by surah (each surah collapsible),
 *  split per lemma when the root carries several. */
function WordInVerses({
  openInContext,
}: {
  openInContext: (surah: number, ayah: number) => void;
}) {
  // Everything durable is cached — the search, its verses, the error banner and
  // which sections the reader had folded away. `loading` stays plain state: a
  // cached `true` would restore a spinner that never stops.
  const [word, setWord] = useCachedState("verse-study.word.query", "");
  const [data, setData] = useCachedState<VerseLookupResponse | null>(
    "verse-study.word.data",
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useCachedState<Failure | null>(
    "verse-study.word.error",
    null,
  );
  // Collapsed sets; empty = all open (as before). Surah key = `${root}:${lemma}:${surah}`.
  const [collapsedSurahs, setCollapsedSurahs] = useCachedState<Set<string>>(
    "verse-study.word.collapsedSurahs",
    new Set(),
  );
  const [collapsedLemmas, setCollapsedLemmas] = useCachedState<Set<string>>(
    "verse-study.word.collapsedLemmas",
    new Set(),
  );

  async function run() {
    if (!word.trim() || loading) return;
    const w = word.trim();
    setLoading(true);
    setError(null);
    setCollapsedSurahs(new Set());
    setCollapsedLemmas(new Set());
    try {
      setData(await verseLookup(w));
    } catch (e) {
      setData(null);
      setError({ text: forStatus(statusOf(e), "search"), detail: detailOf(e) });
    } finally {
      setLoading(false);
    }
  }

  function toggleIn(
    setter: Dispatch<SetStateAction<Set<string>>>,
    key: string,
  ) {
    setter((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  // Jump from a lemma chip (root bar) to that lemma's result block: expand it if
  // collapsed, then smooth-scroll it into view.
  function goToLemma(idx: number, lkey: string) {
    setCollapsedLemmas((prev) => {
      if (!prev.has(lkey)) return prev;
      const next = new Set(prev);
      next.delete(lkey);
      return next;
    });
    document
      .getElementById(`lemma-block-${idx}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // KPI totals are ADDITIVE over the lemma cards (the header tallies the cards,
  // it does not de-duplicate). A verse or surah that hosts two lemmas of the same
  // root — e.g. روح: 34:12 (ريح+رواح), 56:89 (روح+ريحان) — is counted once per
  // lemma, so `sum(card) === header`. Each term mirrors exactly what its card
  // shows: آية = lemma.count, سورة = distinct surahs within that lemma.
  const ayaCount = data
    ? data.lemmas.reduce((sum, l) => sum + l.count, 0)
    : 0;
  const surahCount = data
    ? data.lemmas.reduce(
        (sum, l) => sum + new Set(l.verses.map((v) => v.surah_number)).size,
        0,
      )
    : 0;

  return (
    <div className="space-y-6">
      {/* Live, non-editable Arabic question (RTL). */}
      <div dir="rtl" className="font-arabic text-xl text-gray-800" lang="ar">
        {word.trim() ? (
          <>
            ما هي الآيات والسور التي وردت فيها{" "}
            <span dir="auto" className="font-bold text-brand-dark">
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
          placeholder={S.verseStudy.wordPlaceholder}
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
        <FailureNote
          failure={error}
          className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
        />
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
              {/* Root bar — sits ABOVE the madār aṣl card. Enlarged root on the
                  right; totals on the left with the found lemmas listed and
                  highlighted after the لفظ count. When the root carries many
                  lemmas (>2), the long lemma list would wrap awkwardly beside the
                  root, so the bar stacks vertically instead: root on top, the
                  results below it.

                  Source order is logical — root first, totals second — and the
                  document's RTL direction is what puts the root on the right.
                  This row used to be hand-reversed, which the root flip would
                  have inverted. Note the coupling: `flex-col` (not `-reverse`)
                  is what keeps the root on top now that it comes first, the
                  block axis being direction-independent. */}
              <div
                className={`gap-2 rounded-lg bg-gray-100 px-4 py-3 ${
                  !data.is_proper_noun && data.lemmas.length > 2
                    ? "flex flex-col items-start"
                    : "flex flex-wrap items-center justify-between"
                }`}
              >
                <span
                  dir="rtl"
                  lang="ar"
                  className="flex items-baseline gap-2 font-arabic"
                >
                  <span className="text-sm text-gray-500">
                    {data.is_proper_noun
                      ? S.verseStudy.properNoun
                      : S.verseStudy.root}
                  </span>
                  <span
                    className={`text-3xl text-brand-dark ${
                      data.is_proper_noun ? "" : "tracking-widest"
                    }`}
                  >
                    {data.is_proper_noun
                      ? data.lemmas[0]?.lemma_display
                      : data.root}
                  </span>
                </span>
                <span
                  dir="rtl"
                  lang="ar"
                  className="font-arabic text-lg text-gray-800"
                >
                  {data.is_proper_noun ? (
                    `عدد الآيات : ${ayaCount} · عدد السور : ${surahCount}`
                  ) : (
                    <>
                      عدد الآيات : {ayaCount} · عدد السور : {surahCount} · عدد
                      الألفاظ : {data.lemmas.length} (
                      {data.lemmas.map((lg, i) => {
                        const lkey = `${lg.root}:${lg.lemma}`;
                        return (
                          <span key={lkey}>
                            <button
                              type="button"
                              onClick={() => goToLemma(i, lkey)}
                              title={S.verseStudy.lemmaJump}
                              className="cursor-pointer rounded bg-brand/15 px-1 font-semibold text-brand-dark hover:bg-brand/25"
                            >
                              {lg.lemma_display}
                            </button>
                            {i < data.lemmas.length - 1 ? "، " : ""}
                          </span>
                        );
                      })}
                      )
                    </>
                  )}
                </span>
              </div>

              {/* Hand the SEARCHED word (never the live input, which the reader
                  may already be retyping) to Lisan Analysis, which runs it on
                  arrival. Left-aligned under the root bar: this wrapper is LTR —
                  only the Arabic runs inside the bar above are RTL. */}
              <div className="flex">
                <Link
                  href={`/lexical?word=${encodeURIComponent(data.word)}`}
                  className="flex items-center gap-1.5 rounded-lg bg-brand px-5 py-2 font-arabic text-lg text-white transition hover:bg-brand-dark"
                >
                  <Type className="h-4 w-4" />
                  تحليل لساني
                </Link>
              </div>

              {/* Verses by surah — each surah independently collapsible (open by
                  default), in order of appearance. A word with several lemmas
                  nests its surah groups under a collapsible section per lemma. */}
              {data.lemmas.map((lg, idx) => {
                const lkey = `${lg.root}:${lg.lemma}`;
                const blockId = `lemma-block-${idx}`;
                const surahs = groupBySurah(lg.verses);
                const surahCards = (
                  <div className="space-y-3">
                    {surahs.map((g) => {
                      const skey = `${lkey}:${g.number}`;
                      return (
                        <SurahCard
                          key={skey}
                          group={g}
                          open={!collapsedSurahs.has(skey)}
                          onToggle={() => toggleIn(setCollapsedSurahs, skey)}
                          openInContext={openInContext}
                        />
                      );
                    })}
                  </div>
                );

                // Single lemma (incl. proper nouns): surah list directly, no wrapper.
                if (data.lemmas.length === 1) {
                  return (
                    <div key={lkey} id={blockId} className="scroll-mt-4">
                      {surahCards}
                    </div>
                  );
                }

                // Several lemmas: collapsible section per lemma (open by default).
                const lopen = !collapsedLemmas.has(lkey);
                return (
                  <div
                    key={lkey}
                    id={blockId}
                    className="scroll-mt-4 overflow-hidden rounded-lg border border-gray-300"
                  >
                    <button
                      onClick={() => toggleIn(setCollapsedLemmas, lkey)}
                      dir="rtl"
                      className="flex w-full items-center justify-between bg-brand-light px-4 py-2.5 text-right hover:brightness-95"
                    >
                      {/* Format: «اللفظ، عدد السور : M، عدد الآيات : N» */}
                      <span dir="rtl" className="font-arabic">
                        <span className="text-xl font-bold text-brand-dark">
                          {lg.lemma_display}
                        </span>
                        <span className="text-sm text-gray-500">
                          ، عدد السور : {surahs.length}، عدد الآيات : {lg.count}
                        </span>
                      </span>
                      {lopen ? (
                        <ChevronDown className="h-4 w-4 text-gray-400" />
                      ) : (
                        <ChevronLeft className="h-4 w-4 text-gray-400" />
                      )}
                    </button>
                    {lopen && <div className="space-y-3 p-3">{surahCards}</div>}
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

/** Tab 2 — an Arabic phrase (even a partial verse) → closest verses by root + keyword,
 *  reranked by a cross-encoder (no dense/semantic branch; see api/routers/search.py). */
function SimilarVerses() {
  const [query, setQuery] = useCachedState("verse-study.similar.query", "");
  const [data, setData] = useCachedState<SearchResponse | null>(
    "verse-study.similar.data",
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useCachedState<Failure | null>(
    "verse-study.similar.error",
    null,
  );

  // Which result cards are open, and the context each one loaded. Both cached, so
  // a trip to another page brings the reader back to the same opened cards
  // without re-fetching. `ctxLoading` is transient and must never be.
  const [expanded, setExpanded] = useCachedState<Set<string>>(
    "verse-study.similar.expanded",
    new Set(),
  );
  const [contexts, setContexts] = useCachedState<Record<string, VerseDetail>>(
    "verse-study.similar.contexts",
    {},
  );
  const [ctxError, setCtxError] = useCachedState<Record<string, Failure>>(
    "verse-study.similar.contextErrors",
    {},
  );
  const [ctxLoading, setCtxLoading] = useState<Set<string>>(new Set());

  /** Load one verse's surrounding āyāt. Lazy by design: fetching all 20 up front
   *  would be 20 requests for context the reader probably will not open. */
  async function loadContext(v: Verse) {
    if (contexts[v.id] || ctxLoading.has(v.id)) return;
    setCtxLoading((prev) => new Set(prev).add(v.id));
    try {
      const res = await getVerse(v.surah_number, v.ayah_number, CONTEXT_WINDOW);
      setContexts((prev) => ({ ...prev, [v.id]: res }));
      setCtxError((prev) => {
        if (!prev[v.id]) return prev;
        const next = { ...prev };
        delete next[v.id];
        return next;
      });
    } catch (e) {
      setCtxError((prev) => ({
        ...prev,
        [v.id]: {
          text: forStatus(statusOf(e), "verse"),
          detail: detailOf(e),
        },
      }));
    } finally {
      setCtxLoading((prev) => {
        const next = new Set(prev);
        next.delete(v.id);
        return next;
      });
    }
  }

  function toggle(v: Verse) {
    const isOpen = expanded.has(v.id);
    setExpanded((prev) => {
      const next = new Set(prev);
      isOpen ? next.delete(v.id) : next.add(v.id);
      return next;
    });
    if (!isOpen) loadContext(v);
  }

  // A card left open when the reader navigated away comes back open. If its fetch
  // was still in flight at that moment the context never landed (`ctxLoading` is
  // not cached), so re-request it — otherwise the card would stay open and empty.
  useEffect(() => {
    for (const v of data?.results ?? []) {
      if (expanded.has(v.id) && !contexts[v.id] && !ctxError[v.id]) loadContext(v);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run() {
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    // A new search invalidates every open card and its loaded context.
    setExpanded(new Set());
    setContexts({});
    setCtxError({});
    try {
      setData(await searchVerses(query.trim(), 20));
    } catch (e) {
      setError({ text: forStatus(statusOf(e), "search"), detail: detailOf(e) });
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
            <span dir="auto" className="font-bold text-brand-dark">
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
          placeholder={S.verseStudy.phrasePlaceholder}
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

      <p className="text-xs text-gray-400">{S.verseStudy.similarNote}</p>

      {error && (
        <FailureNote
          failure={error}
          className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
        />
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
              {S.verseStudy.noneFound}
            </div>
          ) : (
            <>
              <div dir="rtl" className="rounded-lg bg-gray-100 px-4 py-3 text-right">
                <span lang="ar" className="font-arabic text-lg text-gray-800">
                  {S.verseStudy.nearest(data.results.length)}
                </span>
              </div>
              <div className="space-y-3">
                {data.results.map((v) => (
                  <SimilarVerseCard
                    key={v.id}
                    verse={v}
                    open={expanded.has(v.id)}
                    context={contexts[v.id]}
                    error={ctxError[v.id]}
                    onToggle={() => toggle(v)}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

/** Tab 3 — pick a surah + ayah → that verse rendered with 3 verses of context on each
 *  side (same surah), the chosen one highlighted. This is the "Find Verse context" tab.
 *  Reacts to `target` (from in-page clicks / deep links). */
/** One "Similar Verses" result: the verse, and — once opened — the surrounding
 *  āyāt of its surah, rendered by the very same `VerseContextCard` the
 *  "Find Verse context" tab uses.
 *
 *  The whole header is the toggle. It used to jump to that tab instead; showing
 *  the context in place makes the hop unnecessary, and the expanded body keeps
 *  the "Open full Sourate page" link for the full reading.
 *
 *  No `loading` prop: "open, no error, no context yet" IS the loading state, so
 *  there is no second flag that could disagree with the first. */
function SimilarVerseCard({
  verse,
  open,
  context,
  error,
  onToggle,
}: {
  verse: Verse;
  open: boolean;
  context?: VerseDetail;
  error?: Failure;
  onToggle: () => void;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition hover:border-brand">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        dir="rtl"
        className="block w-full p-4 text-right"
        title={open ? "أخفِ السياق" : "اعرض الآية في سياقها"}
      >
        {/* Format: «اسم السورة (رقم)» — the same reference style the surah cards
            of "Word in Verses" use. The āya number is not repeated here: it is
            already badged at the end of the verse itself (﴿44﴾). */}
        <header className="mb-2 flex items-center justify-between gap-2">
          <span dir="rtl" className="font-arabic text-lg">
            <span className="font-semibold text-gray-800">
              {verse.surah_name_ar}
            </span>
            <span className="text-gray-400"> ({verse.surah_number})</span>
          </span>
          <span className="flex items-center gap-2">
            {typeof verse.relevance_score === "number" && (
              <span dir="ltr" className="text-xs text-gray-300">
                {verse.relevance_score.toFixed(3)}
              </span>
            )}
            <ChevronDown
              className={`h-4 w-4 shrink-0 text-gray-400 transition-transform ${
                open ? "rotate-180" : ""
              }`}
            />
          </span>
        </header>
        <div
          dir="rtl"
          lang="ar"
          className="arabic-text text-2xl leading-loose text-gray-900"
        >
          {verse.text_ar_tashkil || verse.text_ar}{" "}
          <span className="align-middle text-sm text-gray-400">
            ﴿{verse.ayah_number}﴾
          </span>
        </div>
      </button>

      {open && (
        <div className="border-t border-gray-100 bg-gray-50/60 p-4">
          {error ? (
            <FailureNote
              failure={error}
              className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
            />
          ) : context ? (
            <VerseContextCard result={context} />
          ) : (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span lang="ar" className="font-arabic">
                جارٍ تحميل السياق…
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function FindVerseContext({ target }: { target: ContextTarget | null }) {
  // The surah list is static reference data shared with QLisan — cached under a
  // page-neutral key so it is fetched once per tab session, not once per mount.
  const [surahs, setSurahs] = useCachedState<SurahMeta[]>("surahs.list", []);
  const [surah, setSurah] = useCachedState("verse-study.context.surah", 1);
  const [ayah, setAyah] = useCachedState("verse-study.context.ayah", 1);
  const [result, setResult] = useCachedState<VerseDetail | null>(
    "verse-study.context.result",
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useCachedState<Failure | null>(
    "verse-study.context.error",
    null,
  );
  // Monotonic request id — only the latest lookup applies its result, so a
  // target arriving mid-fetch (or button-spam) never loses to a stale response.
  const reqSeq = useRef(0);

  // Load the surah list (Arabic names) for the picker — skipped when the cache
  // already holds it.
  useEffect(() => {
    if (surahs.length) return;
    getSurahs()
      .then(setSurahs)
      .catch((e) =>
        setError({ text: forStatus(statusOf(e), "surahList"), detail: detailOf(e) }),
      );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // React to a target verse (in-page click or deep link): sync the picker and load it.
  // Keyed on the nonce so re-clicking the same verse still re-triggers a load.
  useEffect(() => {
    if (!target) return;
    setSurah(target.surah);
    setAyah(target.ayah);
    lookup(target.surah, target.ayah);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target?.nonce]);

  const maxAyah = useMemo(
    () => surahs.find((s) => s.number === surah)?.ayah_count ?? 286,
    [surahs, surah],
  );

  function onSurahChange(n: number) {
    setSurah(n);
    const count = surahs.find((s) => s.number === n)?.ayah_count ?? 286;
    if (ayah > count) setAyah(count); // keep the ayah within the new surah
  }

  async function lookup(s = surah, a = ayah) {
    const seq = ++reqSeq.current;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await getVerse(s, a, CONTEXT_WINDOW);
      if (seq === reqSeq.current) setResult(res); // ignore superseded responses
    } catch (e) {
      if (seq === reqSeq.current)
        setError({ text: forStatus(statusOf(e), "verse"), detail: detailOf(e) });
    } finally {
      if (seq === reqSeq.current) setLoading(false);
    }
  }

  const main = result?.verse;
  const surahNameAr =
    surahs.find((s) => s.number === main?.surah_number)?.name_ar ??
    main?.surah_name_ar ??
    "";

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-500">{S.verseStudy.contextCaption}</p>

      <div className="flex flex-wrap items-center gap-2">
        {/* Surah picker — Arabic names. */}
        <select
          value={surah}
          onChange={(e) => onSurahChange(Number(e.target.value))}
          dir="rtl"
          aria-label={S.verse.surah}
          className="min-w-[220px] rounded-lg border border-gray-300 px-3 py-2 text-lg focus:border-brand focus:outline-none"
        >
          {surahs.map((s) => (
            <option key={s.number} value={s.number}>
              {s.number}. {s.name_ar}
            </option>
          ))}
        </select>

        {/* Ayah number. */}
        <input
          value={ayah}
          onChange={(e) => setAyah(Math.max(1, Number(e.target.value) || 1))}
          onKeyDown={(e) => e.key === "Enter" && lookup()}
          type="number"
          min={1}
          max={maxAyah}
          aria-label={S.verse.ayahNumber}
          className="w-28 rounded-lg border border-gray-300 px-3 py-2 focus:border-brand focus:outline-none"
        />
        <span className="western-digits text-sm text-gray-400">
          <span dir="ltr">/ {maxAyah}</span>
        </span>

        <button
          onClick={() => lookup()}
          disabled={loading || surahs.length === 0}
          className="flex items-center gap-1 rounded-lg bg-brand px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          {S.verseStudy.showVerse}
        </button>
      </div>

      {error && (
        <FailureNote
          failure={error}
          className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
        />
      )}

      {main && result && (
        <VerseContextCard result={result} surahNameAr={surahNameAr} />
      )}
    </div>
  );
}
