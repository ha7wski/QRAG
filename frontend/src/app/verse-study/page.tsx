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
  VerseLookupForm,
  VerseLookupResponse,
  VerseLookupVerse,
} from "@/lib/types";
import { useCachedState } from "@/lib/pageCache";
import { S, forStatus } from "@/lib/strings";
// Explicit conversion, never the font's `locl`: design D22 measured that Amiri
// renders 0-9 identically under `lang="ar"`, so a badge left to the font stays
// Western while the surah page's converts — the two pages disagreed on screen.
import FailureNote, { type Failure } from "@/components/FailureNote";
import ScrollToTop from "@/components/ScrollToTop";
import VerseContextCard from "@/components/VerseContextCard";
import SelectBox from "@/components/SelectBox";
import SurahSimilarity from "@/components/SurahSimilarity";
import QuranSimilarityMap from "@/components/QuranSimilarityMap";

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
  //
  // ?word= is the other direction of the same traffic: Lisan Analysis publishes
  // the root's occurrence figures and sends the reader here for the exhaustive
  // vocalized display, which is this tab's job and not that page's. A verse
  // target still wins — the two parameters name different destinations, and the
  // one that opens a specific āya is the more specific request.
  const params = useSearchParams();
  const requestedWord = params.get("word")?.trim() || "";
  useEffect(() => {
    const s = Number(params.get("surah"));
    const a = Number(params.get("ayah"));
    if (s && a) {
      setContextTarget({ surah: s, ayah: a, nonce: 1 });
      setTab("context");
    } else if (requestedWord) {
      // The cached tab may be «الآيات القريبة»; an explicit word overrides it.
      setTab("word");
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
        <WordInVerses openInContext={openInContext} requested={requestedWord} />
      </div>
      <div className={tab === "similar" ? "" : "hidden"}>
        <SimilarTab openInContext={openInContext} />
      </div>
      <div className={tab === "context" ? "" : "hidden"}>
        <FindVerseContext target={contextTarget} />
      </div>

      <ScrollToTop />
    </div>
  );
}

/** Group a لفظ's verses by surah, preserving canonical order (backend sorted). */
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

/** How the results are ordered — BOTH levels, under one selection: the لفظ
 *  blocks and the surah cards inside them. `mushaf` is the backend's own order
 *  at each level (blocks by first occurrence, verses in recitation order). */
type ResultOrder = "mushaf" | "desc" | "asc";

/**
 * Reorder a لفظ's surah cards by how many āyāt of that surah hold the root —
 * the very number each card prints, so the ranking is checkable on screen.
 *
 * Ties are broken by the HIGHER surah number, in both directions (owner's call):
 * «الآيات» puts الأعراف (7) ahead of الأنعام (6), both at 27. This is an explicit
 * second key, not the stability of `Array.prototype.sort` — leaving ties to the
 * stable sort would have kept the mushaf order, i.e. the opposite. The
 * consequence to know is that ascending mode does NOT mirror it: its ties also
 * read 7 before 6, which is what was asked for.
 *
 * The copy is deliberate — sorting `groups` in place would mutate the array a
 * later render reuses.
 */
function sortSurahs<T extends { number: number; verses: unknown[] }>(
  groups: T[],
  order: ResultOrder,
): T[] {
  if (order === "mushaf") return groups;
  const sign = order === "desc" ? -1 : 1;
  return [...groups].sort(
    (a, b) => sign * (a.verses.length - b.verses.length) || b.number - a.number,
  );
}

/**
 * Reorder the لفظ blocks by `count` — the block's DISTINCT-āya figure, which is
 * the number its own header prints, exactly as `sortSurahs` ranks on the number
 * the card prints.
 *
 * Ties go to the EARLIER first occurrence, in both directions. The backend emits
 * the blocks in first-occurrence order, so a block's index in `forms` IS that
 * position and there is nothing to recompute from the verses.
 *
 * Note the tie-break differs from `sortSurahs`, which prefers the HIGHER surah
 * number: there the explicit key REVERSES what a stable sort would have done,
 * here it AGREES with it. It is still written out rather than left to stability,
 * for the same reason: a tie-break that depends on the backend's emission order
 * surviving `sort()` is one that changes silently the day either of them moves.
 *
 * The copy is deliberate — sorting `forms` in place would mutate the response
 * object a later render reuses, and with it the header's chip order.
 */
function sortForms(
  forms: VerseLookupForm[],
  order: ResultOrder,
): VerseLookupForm[] {
  if (order === "mushaf") return forms;
  const sign = order === "desc" ? -1 : 1;
  // Keyed on object identity: `forms` holds the response's own block objects,
  // and the rank has to be read BEFORE the copy is reordered.
  const firstOccurrence = new Map(forms.map((f, i) => [f, i] as const));
  return [...forms].sort(
    (a, b) =>
      sign * (a.count - b.count) ||
      firstOccurrence.get(a)! - firstOccurrence.get(b)!,
  );
}

/** The three-way ordering control shown above the results. A radio group, not
 *  three loose buttons: the options are exclusive, and `aria-checked` is what
 *  tells a screen reader which one is in force.
 *
 *  ONE control for both levels, deliberately: a second picker for the blocks
 *  would let the page show ألفاظ ranked by frequency above surah cards still in
 *  mushaf order, two answers to the same question on one screen. */
function ResultOrderPicker({
  value,
  onChange,
}: {
  value: ResultOrder;
  onChange: (order: ResultOrder) => void;
}) {
  const options: [ResultOrder, string][] = [
    ["mushaf", S.verseStudy.sortMushaf],
    ["desc", S.verseStudy.sortDesc],
    ["asc", S.verseStudy.sortAsc],
  ];
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span lang="ar" className="font-arabic text-sm text-gray-500">
        {S.verseStudy.sortLabel}
      </span>
      {/* A padded track with a raised pill on the selected option — no dividers
          between the buttons, deliberately: a `divide-x` rule is physical and
          under `dir="rtl"` would draw its line on the wrong side of each item. */}
      <div
        role="radiogroup"
        aria-label={S.verseStudy.sortGroupLabel}
        className="flex items-center gap-1 rounded-lg bg-gray-100 p-1"
      >
        {options.map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="radio"
            aria-checked={value === key}
            onClick={() => onChange(key)}
            className={`rounded-md px-3 py-1 font-arabic text-sm transition ${
              value === key
                ? "bg-white font-semibold text-brand-dark shadow-sm"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
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
        className="flex w-full items-center justify-between bg-gray-50 px-4 py-2.5 text-start hover:bg-gray-100"
      >
        {/* Format: «اسم السورة (رقم)، عدد الآيات : N» */}
        <span className="font-arabic text-lg">
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
                className="block w-full px-4 py-3 text-start transition hover:bg-brand-light/50"
              >
                <div
                  lang="ar"
                  className="arabic-text text-2xl text-gray-900"
                >
                  <HighlightedVerse text={v.text} indices={v.match_indices} />{" "}
                  <span className="western-digits align-middle text-sm text-gray-400">
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

/** Tab 1 — one Arabic word → its root's verses, split into one collapsible block
 *  per لفظ (the WRITTEN form: آيات، آياتنا، آياته …), each block holding its surah
 *  cards, each card holding its verses. The lemma this used to group by does not
 *  reach the screen in any form — `/qlisan` is where per-word morphology lives. */
function WordInVerses({
  openInContext,
  requested = "",
}: {
  openInContext: (surah: number, ayah: number) => void;
  /** A word handed over by `?word=` — Lisan Analysis' «اعرض المواضع كاملةً» link.
   *  Empty when the tab was reached any other way. */
  requested?: string;
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
  // Set when the box holds more than one word: the lookup takes ONE word, and
  // sending a phrase only came back as «not found», which blamed the word.
  const [multiWord, setMultiWord] = useCachedState(
    "verse-study.word.multiWord",
    false,
  );
  // Collapsed sets; empty = all open (as before). A block is keyed
  // `${root}:${form}` and a surah card `${root}:${form}:${surah}` — the root is
  // part of the key because homographs can spell one لفظ under two roots, which
  // is also why the backend keys its blocks on the pair.
  const [collapsedSurahs, setCollapsedSurahs] = useCachedState<Set<string>>(
    "verse-study.word.collapsedSurahs",
    new Set(),
  );
  const [collapsedForms, setCollapsedForms] = useCachedState<Set<string>>(
    "verse-study.word.collapsedForms",
    new Set(),
  );
  // A reading preference, not per-result state: unlike the collapsed sets below,
  // `run()` deliberately does NOT reset it — a reader who ranked one root by
  // frequency wants the next one ranked the same way.
  const [order, setOrder] = useCachedState<ResultOrder>(
    "verse-study.word.order",
    "mushaf",
  );

  // `explicit` is the deep-linked word: the effect below has to search a word
  // that is not in `word` yet, since a state update it just queued is not
  // readable here.
  async function run(explicit?: string) {
    const w = (explicit ?? word).trim();
    if (!w || loading) return;
    if (/\s/.test(w)) {
      setData(null);
      setError(null);
      setMultiWord(true);
      return;
    }
    setMultiWord(false);
    setLoading(true);
    setError(null);
    setCollapsedSurahs(new Set());
    setCollapsedForms(new Set());
    try {
      setData(await verseLookup(w));
    } catch (e) {
      setData(null);
      setError({ text: forStatus(statusOf(e), "search"), detail: detailOf(e) });
    } finally {
      setLoading(false);
    }
  }

  // Arriving with ?word=: the parameter is an explicit intent, so it wins over
  // whatever the cache holds — but a word already on screen is not re-fetched,
  // so coming back from Lisan Analysis costs nothing. The ref stores the VALUE
  // consumed, not a boolean: ?word=A → ?word=B without an unmount must still
  // trigger the second search. Same idiom as `app/lexical/page.tsx`.
  const consumed = useRef<string | null>(null);
  useEffect(() => {
    if (!requested || consumed.current === requested) return;
    consumed.current = requested;
    setWord(requested);
    if (data?.word === requested) return; // already searched and restored
    run(requested);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requested]);

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

  // Jump from a لفظ chip (root bar) to that لفظ's block: expand it if collapsed,
  // then smooth-scroll it into view. The index is the position in the ORDERED
  // list, which is what the block ids are built from — so the chips keep landing
  // on the right block after the ordering control is used.
  function goToForm(idx: number, fkey: string) {
    setCollapsedForms((prev) => {
      if (!prev.has(fkey)) return prev;
      const next = new Set(prev);
      next.delete(fkey);
      return next;
    });
    document
      .getElementById(`form-block-${idx}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // The blocks, in the order the reader asked for. The header's chip list and
  // the blocks below it walk this SAME array, so chip order == block order and
  // `form-block-${idx}` addresses the same block on both sides.
  const forms = data?.forms ?? [];
  const orderedForms = sortForms(forms, order);

  // All four header totals are DISTINCT counts over the same filtered set — the
  // occurrences the blocks below actually display.
  //   مواضع — WORDS, not verses: 7:22 holds الشَّجَرَةَ twice, so شجر is 27 مواضع in
  //           26 آيات. 0 for a rootless proper noun, and then omitted rather than
  //           printed as a zero.
  //   آيات  — DISTINCT over the whole root (the backend's own `total`), so an āya
  //           holding two ألفاظ counts once even though it is listed in two blocks.
  //   سور   — DISTINCT too: one Set over every block's verses. This reverses the
  //           old rule, which summed the cards so the header would "add up"
  //           against what was on screen. Summing survived a handful of lemma
  //           sections; with one block per لفظ it announces 154 sūras for أيي and
  //           330 for قوم, past the 114 that exist — a figure that reads as a bug
  //           whatever it is adding up. The cost of the reversal is that the
  //           header no longer equals the sum of the block headers, which is
  //           correct: an āya's sūra is counted once however many ألفاظ it holds.
  //   ألفاظ — the number of blocks, every one of them listed after the figure.
  const occCount = data?.occurrences ?? 0;
  const ayaCount = data?.total ?? 0;
  const surahCount = new Set(
    forms.flatMap((f) => f.verses.map((v) => v.surah_number)),
  ).size;
  // Nothing to order when there is a single block holding a single card; either
  // axis having more than one member brings the control back.
  const canOrder = forms.length > 1 || surahCount > 1;

  return (
    <div className="space-y-6">
      {/* Live, non-editable Arabic question (RTL). */}
      <div className="font-arabic text-xl text-gray-800" lang="ar">
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
          placeholder={S.verseStudy.wordPlaceholder}
          aria-label={S.verseStudy.wordLabel}
          className="min-w-[200px] flex-1 rounded-lg border border-gray-300 px-3 py-2 font-arabic text-xl focus:border-brand focus:outline-none"
        />
        <button
          // Wrapped: `onClick={run}` would hand the MouseEvent to `explicit`.
          onClick={() => run()}
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

      {multiWord && (
        <div
          role="status"
          lang="ar"
          className="rounded-lg bg-amber-50 px-4 py-3 font-arabic text-lg text-amber-800"
        >
          {S.verseStudy.oneWordOnly}
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
              lang="ar"
              className="space-y-2 rounded-lg bg-amber-50 px-4 py-3 font-arabic text-lg text-amber-800"
            >
              <p>{S.verseStudy.notFound}</p>
              {/* A suggestion is offered, never followed: searching it is the
                  reader's choice, so a real typo is never silently papered over. */}
              {(data.suggestions?.length ?? 0) > 0 && (
                <p className="flex flex-wrap items-center gap-2">
                  <span>{S.verseStudy.didYouMean}</span>
                  {data.suggestions!.map((sug) => (
                    <button
                      key={sug}
                      type="button"
                      onClick={() => {
                        setWord(sug);
                        run(sug);
                      }}
                      className="rounded-lg border border-amber-300 bg-white px-3 py-0.5 text-brand-dark hover:border-brand"
                    >
                      {sug}
                    </button>
                  ))}
                </p>
              )}
            </div>
          ) : (
            <>
              {/* Root bar — sits ABOVE the madār aṣl card. Enlarged root on the
                  right; totals on the left with every لفظ found listed and
                  highlighted after the لفظ count. Past 2 ألفاظ the list would
                  wrap awkwardly beside the root, so the bar stacks vertically
                  instead: root on top, the results below it. With a median root
                  at 3 ألفاظ — and أتي at 150 — that is now the normal shape
                  rather than the exception, which is intended: the list is
                  complete by decision, never truncated behind a "show more".

                  Source order is logical — root first, totals second — and the
                  document's RTL direction is what puts the root on the right.
                  This row used to be hand-reversed, which the root flip would
                  have inverted. Note the coupling: `flex-col` (not `-reverse`)
                  is what keeps the root on top now that it comes first, the
                  block axis being direction-independent. */}
              <div
                className={`gap-2 rounded-lg bg-gray-100 px-4 py-3 ${
                  forms.length > 2
                    ? "flex flex-col items-start"
                    : "flex flex-wrap items-center justify-between"
                }`}
              >
                <span
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
                    {/* A name has no root to print, so the response carries its
                        vocalized spelling as its own field — it used to be read
                        off the first lemma group, which no longer exists. */}
                    {data.is_proper_noun
                      ? data.proper_noun_display
                      : data.root}
                  </span>
                </span>
                <span
                  lang="ar"
                  className="font-arabic text-lg text-gray-800"
                >
                  {/* مواضع leads, and is omitted rather than printed as a zero.
                      The ألفاظ list is shown for a name too: لوط is written both
                      لوط and لوطا, and hiding that was never a property of names,
                      only of the lemma grouping this replaced. */}
                  {occCount > 0 ? `عدد المواضع : ${occCount} · ` : ""}
                  عدد الآيات : {ayaCount} · عدد السور : {surahCount} · عدد
                  الألفاظ : {forms.length} (
                  {orderedForms.map((fg, i) => {
                    const fkey = `${fg.root}:${fg.form}`;
                    return (
                      <span key={fkey}>
                        <button
                          type="button"
                          onClick={() => goToForm(i, fkey)}
                          title={S.verseStudy.formJump}
                          className="cursor-pointer rounded bg-brand/15 px-1 font-semibold text-brand-dark hover:bg-brand/25"
                        >
                          {fg.form}
                        </button>
                        {i < orderedForms.length - 1 ? "، " : ""}
                      </span>
                    );
                  })}
                  )
                </span>
              </div>

              {/* The band between the root bar and the results: the ordering
                  control reads first (so, under the document's `dir="rtl"`, it
                  sits on the right, directly above the cards it reorders) and
                  the Lisan Analysis link is pushed to the far end — the left.

                  `ms-auto` on the link, not `justify-between` on the row: with
                  the picker hidden (one لفظ in one sūra) `justify-between`
                  would drop its one remaining child back at the start, i.e. the
                  right. An auto inline-start margin pins the link to the end
                  whether or not the picker is there. Source order stays
                  logical and the row is never hand-reversed — same rule as the
                  root bar above.

                  The link hands Lisan Analysis the SEARCHED word, never the
                  live input, which the reader may already be retyping. */}
              <div className="flex flex-wrap items-center gap-3">
                {canOrder && (
                  <ResultOrderPicker value={order} onChange={setOrder} />
                )}
                <Link
                  href={`/lexical?word=${encodeURIComponent(data.word)}`}
                  className="ms-auto flex items-center gap-1.5 rounded-lg bg-brand px-5 py-2 font-arabic text-lg text-white transition hover:bg-brand-dark"
                >
                  <Type className="h-4 w-4" />
                  تحليل لساني
                </Link>
              </div>

              {/* One collapsible block per لفظ (open by default), each holding
                  its surah cards, each card holding its verses — the two levels
                  below the block are unchanged.

                  The wrapper is rendered even for a SINGLE لفظ, where the lemma
                  sections it replaces used to drop it and show the surah list
                  bare. Three reasons: the لفظ is the identity of the group and
                  the only place the derived spelling is shown as a title (a
                  reader who typed «الآيات» learns the لفظ is «آيات»); the header
                  chip has to land on something labelled; and the structure the
                  spec states has no n=1 case, so a DOM that grows a level at 2
                  is a special case nothing asked for. The cost, accepted: a
                  one-لفظ result prints its سور/آيات figures twice — «موسى، عدد
                  السور : 34، عدد الآيات : 136» a line under the root bar that
                  just said the same. */}
              {orderedForms.map((fg, idx) => {
                const fkey = `${fg.root}:${fg.form}`;
                const surahs = sortSurahs(groupBySurah(fg.verses), order);
                const fopen = !collapsedForms.has(fkey);
                return (
                  <div
                    key={fkey}
                    id={`form-block-${idx}`}
                    className="scroll-mt-4 overflow-hidden rounded-lg border border-gray-300"
                  >
                    <button
                      onClick={() => toggleIn(setCollapsedForms, fkey)}
                      className="flex w-full items-center justify-between bg-brand-light px-4 py-2.5 text-start hover:brightness-95"
                    >
                      {/* Format: «اللفظ، عدد السور : M، عدد الآيات : N» — the
                          shape the lemma sections used, on the form instead.
                          Both figures are local to the block: M is its own card
                          count and N its distinct āyāt, so neither has to agree
                          with the header's distinct totals above. */}
                      <span className="font-arabic">
                        <span className="text-xl font-bold text-brand-dark">
                          {fg.form}
                        </span>
                        <span className="text-sm text-gray-500">
                          ، عدد السور : {surahs.length}، عدد الآيات : {fg.count}
                        </span>
                      </span>
                      {fopen ? (
                        <ChevronDown className="h-4 w-4 text-gray-400" />
                      ) : (
                        <ChevronLeft className="h-4 w-4 text-gray-400" />
                      )}
                    </button>
                    {fopen && (
                      <div className="space-y-3 p-3">
                        {surahs.map((g) => {
                          const skey = `${fkey}:${g.number}`;
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

/** The three modes of the similar tab: the phrase search over the whole Quran,
 *  the precomputed closeness of the verses of one surah, and the surah × surah
 *  map of the close verse pairs across surahs. */
type SimilarMode = "phrase" | "surah" | "quran";

/** Tab 2's shell — a three-way switch over the modes. The phrase panel is
 *  rendered exactly as before, only wrapped. Every panel stays mounted once
 *  shown (hidden with CSS, like the tabs), so a switch keeps each one's state;
 *  their durable state is cached as well, so it survives leaving the page. The
 *  surah and map panels mount on first use, so a reader who never opens one
 *  pays nothing — and the map's matrix is requested only then. */
function SimilarTab({
  openInContext,
}: {
  openInContext: (surah: number, ayah: number) => void;
}) {
  const [mode, setMode] = useCachedState<SimilarMode>(
    "verse-study.similar.mode",
    "phrase",
  );
  const [surahMounted, setSurahMounted] = useState(mode === "surah");
  const [quranMounted, setQuranMounted] = useState(mode === "quran");

  function choose(m: SimilarMode) {
    if (m === "surah") setSurahMounted(true);
    if (m === "quran") setQuranMounted(true);
    setMode(m);
  }

  // Reading order: داخل السورة · في سائر القرآن · من عبارة.
  const options: [SimilarMode, string][] = [
    ["surah", S.verseStudy.similarModes.surah],
    ["quran", S.verseStudy.similarModes.quran],
    ["phrase", S.verseStudy.similarModes.phrase],
  ];

  return (
    <div className="space-y-6">
      {/* Same track-and-pill radio group as the ordering control: the modes are
          exclusive, and `aria-checked` tells a screen reader which is in force.
          Radio keyboard model: one Tab stop (the checked mode), and the arrow
          keys move AND select, wrapping at the ends. Under the document's RTL
          the next mode sits to the LEFT, so Left/Down step forward and
          Right/Up step back. */}
      <div
        role="radiogroup"
        aria-label={S.verseStudy.similarModes.groupLabel}
        className="inline-flex flex-wrap items-center gap-1 rounded-lg bg-gray-100 p-1"
      >
        {options.map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="radio"
            aria-checked={mode === key}
            tabIndex={mode === key ? 0 : -1}
            onClick={() => choose(key)}
            onKeyDown={(e) => {
              const step =
                e.key === "ArrowLeft" || e.key === "ArrowDown"
                  ? 1
                  : e.key === "ArrowRight" || e.key === "ArrowUp"
                    ? -1
                    : 0;
              if (step === 0) return;
              e.preventDefault();
              const at = options.findIndex(([k]) => k === mode);
              const next = (at + step + options.length) % options.length;
              choose(options[next][0]);
              const radios = e.currentTarget.parentElement?.querySelectorAll<HTMLElement>(
                '[role="radio"]',
              );
              radios?.[next]?.focus();
            }}
            className={`rounded-md px-4 py-1 font-arabic text-base transition ${
              mode === key
                ? "bg-white font-semibold text-brand-dark shadow-sm"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className={mode === "phrase" ? "" : "hidden"}>
        <SimilarVerses />
      </div>
      {surahMounted && (
        <div className={mode === "surah" ? "" : "hidden"}>
          <SurahSimilarity openInContext={openInContext} />
        </div>
      )}
      {quranMounted && (
        <div className={mode === "quran" ? "" : "hidden"}>
          <QuranSimilarityMap openInContext={openInContext} />
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
      <div className="font-arabic text-xl text-gray-800" lang="ar">
        {query.trim() ? (
          <>
            ما هي الآيات القريبة في المعنى والتركيب اللغوي من{" "}
            <span dir="auto" className="font-bold text-brand-dark">
              &laquo;{query.trim()}&raquo;
            </span>{" "}
            ؟
          </>
        ) : (
          <span className="text-gray-400">
            ما هي الآيات القريبة في المعنى والتركيب اللغوي من «…» ؟
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder={S.verseStudy.phrasePlaceholder}
          aria-label={S.verseStudy.phraseLabel}
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
              lang="ar"
              className="rounded-lg bg-amber-50 px-4 py-3 font-arabic text-lg text-amber-800"
            >
              {S.verseStudy.noneFound}
            </div>
          ) : (
            <>
              <div className="rounded-lg bg-gray-100 px-4 py-3 text-start">
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
        className="block w-full p-4 text-start"
        title={open ? "أخفِ السياق" : "اعرض الآية في سياقها"}
      >
        {/* Format: «اسم السورة (رقم)» — the same reference style the surah cards
            of "Word in Verses" use. The āya number is not repeated here: it is
            already badged at the end of the verse itself (﴿44﴾). */}
        <header className="mb-2 flex items-center justify-between gap-2">
          <span className="font-arabic text-lg">
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
          lang="ar"
          className="arabic-text text-2xl leading-loose text-gray-900"
        >
          {verse.text_ar_tashkil || verse.text_ar}{" "}
          <span className="western-digits align-middle text-sm text-gray-400">
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
  // What the āya box HOLDS. Empty by default: the 1 is only a grey placeholder,
  // gone as soon as the box is focused, and an empty box searches āya 1. `ayah`
  // is never empty; the box is set explicitly wherever `ayah` changes from
  // outside it (a target verse, a shorter surah).
  const showAyah = (n: number) => (n === 1 ? "" : String(n));
  const [ayahText, setAyahText] = useState(() => showAyah(ayah));
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
    setAyahText(showAyah(target.ayah));
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
    if (ayah > count) {
      setAyah(count); // keep the ayah within the new surah
      setAyahText(showAyah(count));
    }
  }

  function onAyahInput(text: string) {
    const digits = text.replace(/\D/g, "");
    if (!digits) {
      setAyahText("");
      setAyah(1);
      return;
    }
    const n = Math.min(maxAyah, Math.max(1, Number(digits)));
    setAyahText(String(n));
    setAyah(n);
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
        <SelectBox
          value={surah}
          onChange={(e) => onSurahChange(Number(e.target.value))}
          aria-label={S.verse.surah}
          className="min-w-[220px] py-2 text-lg"
        >
          {surahs.map((s) => (
            <option key={s.number} value={s.number}>
              {s.number}. {s.name_ar}
            </option>
          ))}
        </SelectBox>

        {/* The surah's length, then the āya box at the left end (RTL). */}
        <span className="western-digits text-sm text-gray-400">
          <span dir="ltr">/ {maxAyah}</span>
        </span>
        <input
          value={ayahText}
          onChange={(e) => onAyahInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && lookup()}
          inputMode="numeric"
          placeholder="1"
          aria-label={S.verse.ayahNumber}
          className="western-digits w-16 rounded-lg border border-gray-300 px-2 py-2 text-center placeholder:text-gray-400 focus:border-brand focus:outline-none focus:placeholder:text-transparent"
        />

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
