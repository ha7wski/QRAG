"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, Loader2, Search } from "lucide-react";
import {
  getSurahs,
  qlisanVerse,
  tahlilReview,
  tahlilWord,
} from "@/lib/api";
import LevelCard, { type LevelTone } from "@/components/LevelCard";
import TahlilClaim from "@/components/TahlilClaim";
import type { QlisanVerseResponse, SurahMeta } from "@/lib/types";
import type { TahlilBlock, TahlilWordResponse } from "@/lib/tahlilTypes";
import { S } from "@/lib/strings";

/** English sub-labels for the five blocks. The Arabic titles come from the API — they are
 *  the block's name, not a UI string — and only the latin gloss lives here. */
const BLOCK_EN: Record<string, string> = {
  huruf: "Letters",
  sarfi: "Morphological",
  nahwi: "Syntactic",
  dalali: "Semantic",
  tarkib: "Synthesis",
};

/** The badge a card announces: the WEAKEST provenance among its claims.
 *
 * `badges` arrives from the API in caution order (محقّق → مُولَّد → تأويلي), so «weakest» is
 * simply the highest index present. Weakest-link rather than commonest or first: a card
 * holding four corpus facts and one interpretive reading is one the reader must approach as
 * interpretive, and a summary that averaged would announce the opposite.
 *
 * The order is read off the payload rather than guessed from a mapping's iteration order —
 * the page holds no Arabic badge strings of its own, and none of its behaviour depends on
 * the order a JSON object happened to serialise in.
 */
function weakestBadge(block: TahlilBlock, badges: string[]): string {
  const fallback = badges[0] ?? "";
  if (!block.available || block.claims.length === 0) return fallback;
  let worst = 0;
  for (const claim of block.claims) {
    const rank = badges.indexOf(claim.badge);
    if (rank > worst) worst = rank;
  }
  return badges[worst] ?? fallback;
}

const TONE_BY_RANK: LevelTone[] = ["fact", "generated", "interpretive"];

function toneOf(block: TahlilBlock, badges: string[]): LevelTone {
  if (!block.available) return "pending";
  const rank = badges.indexOf(weakestBadge(block, badges));
  return TONE_BY_RANK[rank] ?? "fact";
}

export default function TahlilPage() {
  const [surahs, setSurahs] = useState<SurahMeta[]>([]);
  const [surah, setSurah] = useState(23);
  const [ayah, setAyah] = useState(61);

  const [verse, setVerse] = useState<QlisanVerseResponse | null>(null);
  const [verseLoading, setVerseLoading] = useState(false);
  const [verseError, setVerseError] = useState<string | null>(null);

  const [selectedWord, setSelectedWord] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<TahlilWordResponse | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState(false);

  // Monotonic request ids, the QLisan idiom: a slow response for an abandoned selection
  // must not overwrite a newer one.
  const verseSeq = useRef(0);
  const wordSeq = useRef(0);

  useEffect(() => {
    getSurahs()
      .then(setSurahs)
      .catch(() => setSurahs([]));
  }, []);

  const maxAyah = useMemo(
    () => surahs.find((s) => s.number === surah)?.ayah_count ?? 286,
    [surahs, surah],
  );

  function onSurahChange(next: number) {
    setSurah(next);
    const cap = surahs.find((s) => s.number === next)?.ayah_count ?? 286;
    if (ayah > cap) setAyah(1);
  }

  async function loadVerse() {
    const seq = ++verseSeq.current;
    setVerseLoading(true);
    setVerseError(null);
    setSelectedWord(null);
    setAnalysis(null);
    wordSeq.current++; // abandon any analysis in flight for the previous verse
    try {
      const data = await qlisanVerse(surah, ayah);
      if (seq === verseSeq.current) setVerse(data);
    } catch (e) {
      if (seq === verseSeq.current) {
        setVerse(null);
        setVerseError(e instanceof Error ? e.message : "Failed to load verse");
      }
    } finally {
      if (seq === verseSeq.current) setVerseLoading(false);
    }
  }

  async function selectWord(word: number) {
    const seq = ++wordSeq.current;
    setSelectedWord(word);
    setAnalysisLoading(true);
    setAnalysisError(null);
    try {
      const data = await tahlilWord(surah, ayah, word);
      if (seq === wordSeq.current) setAnalysis(data);
    } catch (e) {
      if (seq === wordSeq.current) {
        setAnalysis(null);
        setAnalysisError(e instanceof Error ? e.message : "Analysis failed");
      }
    } finally {
      if (seq === wordSeq.current) setAnalysisLoading(false);
    }
  }

  async function markReviewed() {
    if (!analysis) return;
    setReviewing(true);
    try {
      const res = await tahlilReview(analysis.ref);
      // Trust the STORED flag, never a local toggle: the mention must not disappear on a
      // page that only thinks it was reviewed.
      setAnalysis({ ...analysis, reviewed: res.reviewed });
    } catch {
      /* the mention simply stays — a failed review must not read as a successful one */
    } finally {
      setReviewing(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">
          {S.tahlil.heading}
        </h1>
        <p className="mt-1 text-sm text-gray-500">{S.tahlil.caption}</p>
      </div>

      {/* Verse picker. Source order is logical — sūra select, āya box, load
          button — and the document's RTL direction is what makes it read
          right-to-left with the button at the left end (design D4). */}
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={surah}
          onChange={(e) => onSurahChange(Number(e.target.value))}
          aria-label={S.verse.surah}
          className="min-w-[220px] rounded-lg border border-gray-300 px-3 py-2 text-lg focus:border-brand focus:outline-none"
        >
          {surahs.map((s) => (
            <option key={s.number} value={s.number}>
              {s.number}. {s.name_ar}
            </option>
          ))}
        </select>
        <div className="flex items-center gap-1">
          <input
            value={ayah}
            onChange={(e) =>
              setAyah(Math.min(maxAyah, Math.max(1, Number(e.target.value) || 1)))
            }
            onKeyDown={(e) => e.key === "Enter" && loadVerse()}
            type="number"
            min={1}
            max={maxAyah}
            aria-label={S.verse.ayahNumber}
            className="w-24 rounded-lg border border-gray-300 px-3 py-2 text-center focus:border-brand focus:outline-none"
          />
          <span className="western-digits text-sm text-gray-400">
            <span dir="ltr">/ {maxAyah}</span>
          </span>
        </div>

        <button
          onClick={() => loadVerse()}
          disabled={verseLoading || surahs.length === 0}
          className="flex items-center gap-1 rounded-lg bg-brand px-4 py-2 text-white disabled:opacity-50"
        >
          {verseLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          {S.tahlil.loadVerse}
        </button>

      </div>

      {verseError && (
        <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {verseError}
        </div>
      )}

      {verse && !verseLoading && (
        <VerseTokens
          verse={verse}
          selectedWord={selectedWord}
          onSelect={selectWord}
        />
      )}

      {selectedWord !== null && (
        <div className="space-y-4">
          {analysisLoading && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span lang="ar">جارٍ التحليل…</span>
            </div>
          )}
          {analysisError && (
            <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
              {analysisError}
            </div>
          )}
          {analysis && !analysisLoading && (
            <Analysis
              data={analysis}
              onReview={markReviewed}
              reviewing={reviewing}
            />
          )}
        </div>
      )}
    </div>
  );
}

/** The vocalized verse with individually-selectable tokens, sliced by the QAC-aligned
 *  `[char_start, char_end)` spans so nothing between tokens is lost. */
function VerseTokens({
  verse,
  selectedWord,
  onSelect,
}: {
  verse: QlisanVerseResponse;
  selectedWord: number | null;
  onSelect: (word: number) => void;
}) {
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  const ordered = [...verse.tokens].sort((a, b) => a.char_start - b.char_start);
  for (const token of ordered) {
    if (token.char_start > cursor) {
      parts.push(
        <span key={`gap${cursor}`}>
          {verse.text.slice(cursor, token.char_start)}
        </span>,
      );
    }
    const selected = token.word === selectedWord;
    parts.push(
      <button
        key={`w${token.word}`}
        onClick={() => onSelect(token.word)}
        title={`${verse.surah}:${verse.ayah}:${token.word}`}
        className={`rounded px-0.5 transition-colors ${
          selected
            ? "bg-brand/20 text-brand-dark ring-1 ring-brand/50"
            : "hover:bg-gray-100"
        } ${token.aligned ? "" : "underline decoration-dotted decoration-amber-400 underline-offset-4"}`}
      >
        {verse.text.slice(token.char_start, token.char_end)}
      </button>,
    );
    cursor = Math.max(cursor, token.char_end);
  }
  if (cursor < verse.text.length) {
    parts.push(<span key="tail">{verse.text.slice(cursor)}</span>);
  }

  return (
    <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <header
        className="flex items-baseline justify-between border-b border-gray-100 px-4 py-2 text-sm text-gray-500"
      >
        <span lang="ar" className="font-arabic text-base text-gray-700">
          {verse.surah_name_ar}
        </span>
        <span dir="ltr">
          {verse.surah}:{verse.ayah}
        </span>
      </header>
      <div lang="ar" className="arabic-text px-5 py-5 text-3xl leading-loose">
        {parts}
      </div>
      <footer
        lang="ar"
        className="border-t border-gray-100 px-4 py-2 font-arabic text-xs text-gray-400"
      >
        اضغط على أي كلمة لعرض تحليلها.
      </footer>
    </section>
  );
}

/** The five blocks, in the order the API served them. */
function Analysis({
  data,
  onReview,
  reviewing,
}: {
  data: TahlilWordResponse;
  onReview: () => void;
  reviewing: boolean;
}) {
  // The badge keys in caution order, served by the API. `badges[0]` is the corpus-fact
  // badge — the only one that is not «generated» in the sense the review flag is about.
  const badges = data.badges;
  const verified = badges[0] ?? "";

  const anyGenerated = data.blocks_order.some((id) =>
    (data.blocks[id]?.claims ?? []).some((c) => c.badge !== verified),
  );

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between gap-3">
        <span lang="ar" className="arabic-text text-2xl text-gray-800">
          {data.word_vocalized}
        </span>
        <span dir="ltr" className="text-xs text-gray-400">
          {data.ref}
        </span>
      </header>

      {/* The un-reviewed banner: shown whenever anything on this page was generated and
          no expert has signed it off. It states the fact IN WORDS, not as a tint. */}
      {anyGenerated && !data.reviewed && (
        <div
          className="flex items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2"
        >
          <span lang="ar" className="font-arabic text-sm text-amber-800">
            {data.unverified_mention} — لم يُراجِع هذا التحليلَ مختصٌّ بعد.
          </span>
          <button
            onClick={onReview}
            disabled={reviewing}
            className="flex items-center gap-1 rounded-lg border border-amber-300 bg-white px-3 py-1 text-xs text-amber-800 disabled:opacity-50"
          >
            {reviewing ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <CheckCircle2 className="h-3 w-3" />
            )}
            <span lang="ar" className="font-arabic">
              وسمه بالمراجَعة
            </span>
          </button>
        </div>
      )}

      {data.blocks_order.map((id) => {
        const block = data.blocks[id];
        if (!block) return null;
        const tone = toneOf(block, badges);
        const unreviewed =
          block.available &&
          !data.reviewed &&
          block.claims.some((c) => c.badge !== verified);
        return (
          <LevelCard
            key={id}
            titleAr={block.title_ar}
            titleEn={BLOCK_EN[id] ?? id}
            badge={data.badge_labels[weakestBadge(block, badges)] ?? "—"}
            badgeTitle={data.badge_tooltips[weakestBadge(block, badges)]}
            note={unreviewed ? data.unverified_mention : undefined}
            tone={tone}
          >
            {block.message && (
              <p
                lang="ar"
                className="mb-2 font-arabic text-sm text-gray-500"
              >
                {block.message}
              </p>
            )}
            {block.claims.length > 0 && (
              <ul className="space-y-0">
                {block.claims.map((claim, i) => (
                  <TahlilClaim
                    key={`${id}-${i}`}
                    claim={claim}
                    badgeLabels={data.badge_labels}
                    badgeTooltips={data.badge_tooltips}
                  />
                ))}
              </ul>
            )}
            {block.attribution && (
              <div
                lang="ar"
                className="mt-3 border-t border-gray-100 pt-2 font-arabic text-xs text-gray-500"
              >
                <p>
                  {block.attribution.source.author} —{" "}
                  {block.attribution.source.title}
                </p>
                <p className="mt-1 text-gray-400">
                  {block.attribution.disclaimer}
                </p>
              </div>
            )}
          </LevelCard>
        );
      })}
    </div>
  );
}
