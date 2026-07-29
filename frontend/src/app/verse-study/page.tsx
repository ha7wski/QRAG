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
  ArrowRight,
  ChevronDown,
  ChevronLeft,
  Loader2,
  Search,
} from "lucide-react";
import { getSurahs, getVerse, madarAnalyze, searchVerses, verseLookup } from "@/lib/api";
import type {
  SearchResponse,
  SurahMeta,
  VerseDetail,
  VerseLookupResponse,
  VerseLookupVerse,
} from "@/lib/types";
import type { MadarResponse } from "@/lib/madarTypes";
import ArabicText from "@/components/ArabicText";
import MadarAslCard from "@/components/MadarAslCard";
import ScrollToTop from "@/components/ScrollToTop";

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
  const [tab, setTab] = useState<Tab>("word");
  // The verse (if any) requested for the context tab from another tab or a deep link.
  const [contextTarget, setContextTarget] = useState<ContextTarget | null>(null);

  const tabs: [Tab, string][] = [
    ["word", "Word in Verses"],
    ["similar", "Similar Verses"],
    ["context", "Find Verse context"],
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

      {/* All three stay mounted so switching tabs preserves each one's results. */}
      <div className={tab === "word" ? "" : "hidden"}>
        <WordInVerses openInContext={openInContext} />
      </div>
      <div className={tab === "similar" ? "" : "hidden"}>
        <SimilarVerses openInContext={openInContext} />
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
              {/* Whole verse is clickable → open it in the context tab in-page. */}
              <button
                type="button"
                onClick={() => openInContext(v.surah_number, v.aya_number)}
                title="افتح الآية في سياقها"
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
function SimilarVerses({
  openInContext,
}: {
  openInContext: (surah: number, ayah: number) => void;
}) {
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
                  <button
                    key={v.id}
                    type="button"
                    onClick={() => openInContext(v.surah_number, v.ayah_number)}
                    dir="rtl"
                    className="block w-full rounded-lg border border-gray-200 bg-white p-4 text-right shadow-sm transition hover:border-brand hover:shadow-md"
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
                  </button>
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
function FindVerseContext({ target }: { target: ContextTarget | null }) {
  const [surahs, setSurahs] = useState<SurahMeta[]>([]);
  const [surah, setSurah] = useState(1);
  const [ayah, setAyah] = useState(1);
  const [result, setResult] = useState<VerseDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Monotonic request id — only the latest lookup applies its result, so a
  // target arriving mid-fetch (or button-spam) never loses to a stale response.
  const reqSeq = useRef(0);

  // Load the surah list (Arabic names) for the picker.
  useEffect(() => {
    getSurahs()
      .then(setSurahs)
      .catch((e) => setError(e?.message || "Failed to load surah list"));
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
    } catch (e: any) {
      if (seq === reqSeq.current) setError(e?.message || "Verse not found");
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
      <p className="text-sm text-gray-500">
        Pick a surah and an ayah to read that verse in context — shown with the
        three verses before and after it.
      </p>

      <div className="flex flex-wrap items-center gap-2">
        {/* Surah picker — Arabic names. */}
        <select
          value={surah}
          onChange={(e) => onSurahChange(Number(e.target.value))}
          dir="rtl"
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
          aria-label="Ayah number"
          className="w-28 rounded-lg border border-gray-300 px-3 py-2 focus:border-brand focus:outline-none"
        />
        <span className="text-sm text-gray-400">/ {maxAyah}</span>

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
          Show verse
        </button>
      </div>

      {error && (
        <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {main && result && (
        <div className="space-y-3">
          {/* Condensed box: Arabic only, the chosen verse highlighted, with
              up to 3 verses of context on each side. */}
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2 text-sm text-gray-500">
              <span className="font-medium text-gray-700" dir="rtl">
                {surahNameAr}
              </span>
              <span>
                {main.surah_number}:{main.ayah_number}
              </span>
            </div>

            <div className="divide-y divide-gray-100">
              {result.context.map((v) => {
                const isMain = v.id === main.id;
                return (
                  <div
                    key={v.id}
                    className={`flex items-start gap-3 px-4 py-3 ${
                      isMain ? "bg-brand-light" : ""
                    }`}
                  >
                    <span
                      className={`mt-2 shrink-0 rounded-full px-2 py-0.5 text-xs ${
                        isMain
                          ? "bg-brand text-white"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {v.ayah_number}
                    </span>
                    <ArabicText
                      className={`block flex-1 text-right text-2xl leading-loose ${
                        isMain ? "font-bold text-gray-900" : "text-gray-800"
                      }`}
                    >
                      {v.text_ar_tashkil || v.text_ar}
                    </ArabicText>
                  </div>
                );
              })}
            </div>
          </div>

          <Link
            href={`/surah/${main.surah_number}`}
            className="inline-flex items-center gap-1 text-sm font-medium text-brand-dark hover:underline"
          >
            Open full Sourate page
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}
    </div>
  );
}
