"use client";

import { type Dispatch, type SetStateAction, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronLeft, Loader2, Search } from "lucide-react";
import { madarAnalyze, searchVerses, verseLookup } from "@/lib/api";
import type {
  SearchResponse,
  VerseLookupResponse,
  VerseLookupVerse,
} from "@/lib/types";
import type { MadarResponse } from "@/lib/madarTypes";
import MadarAslCard from "@/components/MadarAslCard";
import ScrollToTop from "@/components/ScrollToTop";

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
}: {
  group: { number: number; name: string; verses: VerseLookupVerse[] };
  open: boolean;
  onToggle: () => void;
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
          <span className="text-gray-400"> ({group.number})</span>
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
              {/* Whole verse is clickable → open it in its context. */}
              <Link
                href={`/verse-context?surah=${v.surah_number}&ayah=${v.aya_number}`}
                title="افتح الآية في سياقها"
                className="block px-4 py-3 transition hover:bg-brand-light/50"
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
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Tab 1 — one Arabic word → its root's verses, by surah (each surah collapsible),
 *  split per lemma when the root carries several. */
function WordInVerses() {
  const [word, setWord] = useState("");
  const [data, setData] = useState<VerseLookupResponse | null>(null);
  // Ibn Fāris' cited aṣl for the resolved root (best-effort enrichment, shown
  // above the occurrences). Null when madār didn't resolve a root (proper noun /
  // out of lexicon) or the call failed.
  const [madar, setMadar] = useState<MadarResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Collapsed sets; empty = all open (as before). Surah key = `${root}:${lemma}:${surah}`.
  const [collapsedSurahs, setCollapsedSurahs] = useState<Set<string>>(new Set());
  const [collapsedLemmas, setCollapsedLemmas] = useState<Set<string>>(new Set());

  async function run() {
    if (!word.trim() || loading) return;
    const w = word.trim();
    setLoading(true);
    setError(null);
    setMadar(null);
    setCollapsedSurahs(new Set());
    setCollapsedLemmas(new Set());
    // verse-lookup drives the occurrences AND the error banner; the madār aṣl is
    // a best-effort enrichment — its failure must never block the occurrences.
    const [lookup, madarRes] = await Promise.allSettled([
      verseLookup(w),
      madarAnalyze(w),
    ]);
    if (lookup.status === "fulfilled") {
      setData(lookup.value);
    } else {
      setData(null);
      setError((lookup.reason as any)?.message || "Lookup failed");
    }
    if (madarRes.status === "fulfilled") setMadar(madarRes.value);
    setLoading(false);
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
              {/* Root bar — sits ABOVE the madār aṣl card. Enlarged root on the
                  right; totals on the left with the found lemmas listed and
                  highlighted after the لفظ count. When the root carries many
                  lemmas (>2), the long lemma list would wrap awkwardly beside the
                  root, so the bar stacks vertically instead: root on top, the
                  results below it. */}
              <div
                className={`gap-2 rounded-lg bg-gray-100 px-4 py-3 ${
                  !data.is_proper_noun && data.lemmas.length > 2
                    ? "flex flex-col-reverse items-end"
                    : "flex flex-wrap items-center justify-between"
                }`}
              >
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
                              title="اذهب إلى مواضع هذا اللفظ"
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
                <span
                  dir="rtl"
                  lang="ar"
                  className="flex items-baseline gap-2 font-arabic"
                >
                  <span className="text-sm text-gray-500">
                    {data.is_proper_noun ? "اسم علم" : "الجذر"}
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
              </div>

              {/* Ibn Fāris' cited aṣl — below the root bar, above the
                  occurrences. Skipped for proper nouns / no madār root. */}
              {madar?.root && <MadarAslCard maqayis={madar.maqayis} />}

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
        Root-aware + keyword search across all 6236 verses, reranked by
        relevance — returns the closest matches (top 20).
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
                  <Link
                    key={v.id}
                    href={`/verse-context?surah=${v.surah_number}&ayah=${v.ayah_number}`}
                    dir="rtl"
                    className="block rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition hover:border-brand hover:shadow-md"
                    title="افتح الآية في سياقها"
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
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
