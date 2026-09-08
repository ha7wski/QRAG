"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, Loader2, Search } from "lucide-react";
import { getSurahs, qlisanVerse, qlisanWord } from "@/lib/api";
import { useCachedState } from "@/lib/pageCache";
import { S } from "@/lib/strings";
import FicheRow from "@/components/FicheRow";
import LevelCard from "@/components/LevelCard";
import SarfiRows from "@/components/SarfiRows";
import type {
  QlisanNahwi,
  QlisanSarfi,
  QlisanStubLevel,
  QlisanToken,
  QlisanVerseResponse,
  QlisanWordResponse,
  SurahMeta,
} from "@/lib/types";

/**
 * QLisan — per-word, four-level analysis of a single Quran word.
 *
 * Flow: pick a surah + ayah → load the vocalized verse with QAC-aligned token
 * boundaries (from the alignment spine, NOT a whitespace split) → click any word
 * token → request + render its four-level fiche in the fixed order صوتي → صرفي →
 * نحوي → دلالي. The deterministic levels (صرفي/نحوي) are shown as established
 * facts; the صوتي/دلالي stubs are shown visibly as pending, never blank.
 */
export default function QlisanPage() {
  // Cached across navigation: the loaded verse, the selected word and its fiche
  // survive a trip to another page. The two `*Loading` flags never are — a cached
  // `true` would restore a spinner that never stops.
  const [surahs, setSurahs] = useCachedState<SurahMeta[]>("surahs.list", []);
  const [surah, setSurah] = useCachedState("qlisan.surah", 1);
  const [ayah, setAyah] = useCachedState("qlisan.ayah", 1);

  const [verse, setVerse] = useCachedState<QlisanVerseResponse | null>(
    "qlisan.verse",
    null,
  );
  const [verseLoading, setVerseLoading] = useState(false);
  const [verseError, setVerseError] = useCachedState<string | null>(
    "qlisan.verseError",
    null,
  );

  const [selectedWord, setSelectedWord] = useCachedState<number | null>(
    "qlisan.selectedWord",
    null,
  );
  const [fiche, setFiche] = useCachedState<QlisanWordResponse | null>(
    "qlisan.fiche",
    null,
  );
  const [ficheLoading, setFicheLoading] = useState(false);
  const [ficheError, setFicheError] = useCachedState<string | null>(
    "qlisan.ficheError",
    null,
  );

  // Monotonic request ids — only the latest response for each lane applies, so a
  // fast re-click / re-load never loses to a stale response.
  const verseSeq = useRef(0);
  const ficheSeq = useRef(0);

  // Load the surah list (Arabic names) for the picker — skipped when the shared
  // cache already holds it (Verse Study fetches the same list).
  useEffect(() => {
    if (surahs.length) return;
    getSurahs()
      .then(setSurahs)
      .catch((e) => setVerseError(e?.message || "Failed to load surah list"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const maxAyah = useMemo(
    () => surahs.find((s) => s.number === surah)?.ayah_count ?? 286,
    [surahs, surah],
  );

  function onSurahChange(n: number) {
    setSurah(n);
    const count = surahs.find((s) => s.number === n)?.ayah_count ?? 286;
    if (ayah > count) setAyah(count); // keep the ayah within the new surah
  }

  async function loadVerse(s = surah, a = ayah) {
    const seq = ++verseSeq.current;
    setVerseLoading(true);
    setVerseError(null);
    setVerse(null);
    // A new verse invalidates any prior selection / fiche.
    setSelectedWord(null);
    setFiche(null);
    setFicheError(null);
    ficheSeq.current++;
    try {
      const res = await qlisanVerse(s, a);
      if (seq === verseSeq.current) setVerse(res);
    } catch (e: any) {
      if (seq === verseSeq.current)
        setVerseError(e?.message || "Verse not found");
    } finally {
      if (seq === verseSeq.current) setVerseLoading(false);
    }
  }

  async function selectWord(word: number) {
    if (!verse) return;
    setSelectedWord(word);
    const seq = ++ficheSeq.current;
    setFicheLoading(true);
    setFicheError(null);
    setFiche(null);
    try {
      const res = await qlisanWord(verse.surah, verse.ayah, word);
      if (seq === ficheSeq.current) setFiche(res);
    } catch (e: any) {
      if (seq === ficheSeq.current)
        setFicheError(e?.message || "Word analysis failed");
    } finally {
      if (seq === ficheSeq.current) setFicheLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">
          {S.qlisan.heading}
        </h1>
        <p className="mt-1 text-sm text-gray-500">{S.qlisan.caption}</p>
      </div>

      {/* Verse picker. Source order is logical — sūra select, āya box, load
          button — and the document's RTL direction is what makes it read
          right-to-left with the button at the left end. This row used to be
          hand-reversed inside `justify-end`, which document RTL would have
          flipped a second time (design D4). */}
      <div className="flex flex-wrap items-center gap-2">
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
        <div className="flex items-center gap-1">
          <input
            value={ayah}
            onChange={(e) =>
              setAyah(
                Math.min(maxAyah, Math.max(1, Number(e.target.value) || 1)),
              )
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
          {S.qlisan.loadVerse}
        </button>

      </div>

      {verseError && (
        <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {verseError}
        </div>
      )}

      {/* The verse with individually-selectable tokens. */}
      {verse && !verseLoading && (
        <VerseTokens
          verse={verse}
          selectedWord={selectedWord}
          onSelect={selectWord}
        />
      )}

      {/* The four-level fiche for the selected word. */}
      {selectedWord !== null && (
        <div className="space-y-4">
          {ficheLoading && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>جارٍ التحليل…</span>
            </div>
          )}
          {ficheError && (
            <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
              {ficheError}
            </div>
          )}
          {fiche && !ficheLoading && <Fiche data={fiche} />}
        </div>
      )}
    </div>
  );
}

/** Render the vocalized verse using the spine char-spans: each token is a
 *  clickable <button> sliced out of `text` by [char_start, char_end); the
 *  gaps between spans (spaces / ornaments) are rendered inert so nothing is
 *  lost. A token with `aligned:false` gets a subtle dashed marker. */
function VerseTokens({
  verse,
  selectedWord,
  onSelect,
}: {
  verse: QlisanVerseResponse;
  selectedWord: number | null;
  onSelect: (word: number) => void;
}) {
  const { text } = verse;

  // Walk the text once, interleaving token slices with the inert gaps between
  // them (tokens sorted by start; overlaps are clamped defensively).
  type Piece =
    | { kind: "gap"; text: string; key: string }
    | { kind: "token"; token: QlisanToken; text: string; key: string };
  const pieces: Piece[] = [];
  const sorted = [...verse.tokens].sort((a, b) => a.char_start - b.char_start);
  let cursor = 0;
  for (const t of sorted) {
    const start = Math.max(cursor, t.char_start);
    if (t.char_start > cursor) {
      pieces.push({
        kind: "gap",
        text: text.slice(cursor, t.char_start),
        key: `gap-${cursor}`,
      });
    }
    if (t.char_end > start) {
      pieces.push({
        kind: "token",
        token: t,
        text: text.slice(start, t.char_end),
        key: `tok-${t.word}`,
      });
      cursor = t.char_end;
    }
  }
  if (cursor < text.length) {
    pieces.push({ kind: "gap", text: text.slice(cursor), key: `gap-${cursor}` });
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Logical order: the sūra name first, then the reference. RTL reads it
          name-then-reference from the right; `justify-end` would now mean the
          left edge, so it is gone. */}
      <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-2 text-sm text-gray-500">
        <span className="font-medium text-gray-700">{verse.surah_name_ar}</span>
        <span dir="ltr">
          {verse.surah}:{verse.ayah}
        </span>
      </div>
      <div
        dir="rtl"
        lang="ar"
        className="arabic-text px-5 py-5 text-3xl leading-loose text-gray-900"
      >
        {pieces.map((p) =>
          p.kind === "gap" ? (
            <span key={p.key}>{p.text}</span>
          ) : (
            <button
              key={p.key}
              type="button"
              onClick={() => onSelect(p.token.word)}
              title={
                p.token.aligned
                  ? `الكلمة ${p.token.word}`
                  : `الكلمة ${p.token.word} — محاذاة تقريبية`
              }
              className={`box-decoration-clone rounded-md px-1 transition ${
                selectedWord === p.token.word
                  ? "bg-brand/20 text-brand-dark ring-1 ring-brand/50"
                  : "hover:bg-brand-light"
              } ${
                p.token.aligned
                  ? ""
                  : "underline decoration-dotted decoration-amber-400 underline-offset-4"
              }`}
            >
              {p.text}
            </button>
          ),
        )}
      </div>
      <div className="border-t border-gray-100 px-4 py-2 text-xs text-gray-400">
        اضغط على أي كلمة لعرض تحليلها.
      </div>
    </div>
  );
}

/** The full four-level fiche, always in the fixed order صوتي → صرفي → نحوي →
 *  دلالي (driven by `levels_order` so the API owns the ordering). */
function Fiche({ data }: { data: QlisanWordResponse }) {
  const renderers: Record<string, () => JSX.Element> = {
    sawti: () => <StubLevel titleAr="صوتي" titleEn="Phonetic" level={data.sawti} />,
    sarfi: () => (
      <SarfiLevel level={data.sarfi} marker={data.nahwi?.marker_ar ?? null} />
    ),
    nahwi: () => <NahwiLevel level={data.nahwi} />,
    dalali: () => (
      <StubLevel
        titleAr="دلالي"
        titleEn="Semantic"
        level={data.dalali}
        sourced
      />
    ),
  };

  return (
    <div className="space-y-4">
      {data.levels_order.map((key) => (
        <div key={key}>{renderers[key]?.() ?? null}</div>
      ))}
    </div>
  );
}

/** صوتي / دلالي — pending or sourced stub. Shows the explanatory message
 *  visibly rather than a blank section. */
function StubLevel({
  titleAr,
  titleEn,
  level,
  sourced = false,
}: {
  titleAr: string;
  titleEn: string;
  level: QlisanStubLevel;
  sourced?: boolean;
}) {
  return (
    <LevelCard
      titleAr={titleAr}
      titleEn={titleEn}
      badge={level.available ? "متاح" : "قيد الإعداد"}
      tone={level.available ? (sourced ? "sourced" : "fact") : "pending"}
    >
      <p dir="rtl" lang="ar" className="font-arabic text-base text-gray-500">
        {level.message || "غير متاح بعد."}
      </p>
    </LevelCard>
  );
}

/** صرفي — deterministic morphology from the treebank. `marker` (العلامة) is the
 *  derived case-marker hint from the نحوي level, shown under البنية الصرفية.
 *  The rows live in the shared `SarfiRows`, which the «تحليل نحوي» section of
 *  Lisan Analysis renders too (there without a `marker`, having no verse position). */
function SarfiLevel({
  level,
  marker,
}: {
  level: QlisanSarfi;
  marker?: string | null;
}) {
  if (!level.available) {
    return (
      <LevelCard titleAr="صرفي" titleEn="Morphological" badge="غير متاح" tone="pending">
        <p dir="rtl" lang="ar" className="font-arabic text-base text-gray-500">
          لا يوجد تحليل صرفي لهذه الكلمة.
        </p>
      </LevelCard>
    );
  }

  return (
    <LevelCard titleAr="صرفي" titleEn="Morphological" badge="معطى محقّق" tone="fact">
      <SarfiRows level={level} marker={marker} />
    </LevelCard>
  );
}

/** نحوي — deterministic syntax from the dependency treebank. */
function NahwiLevel({ level }: { level: QlisanNahwi }) {
  if (!level.available) {
    return (
      <LevelCard titleAr="نحوي" titleEn="Syntactic" badge="غير متاح" tone="pending">
        <p dir="rtl" lang="ar" className="font-arabic text-base text-gray-500">
          {level.message || "لا يوجد إعراب محقّق لهذه الكلمة."}
        </p>
      </LevelCard>
    );
  }
  return (
    /* Verbatim treebank fields carry the «معطى محقّق» badge. `iraab_ar`
       (relation function [+ case word]) subsumes the old «العلاقة» row, and the
       raw `relation`/`relation_ar` codes are never rendered. The العلامة marker is
       rendered in the صرفي card (under البنية الصرفية), not here. */
    <LevelCard titleAr="نحوي" titleEn="Syntactic" badge="معطى محقّق" tone="fact">
      <dl className="space-y-3" dir="rtl">
        {level.iraab_ar && (
          <FicheRow label="الموقع الإعرابي">
            <span className="font-arabic text-lg text-gray-800">
              {level.iraab_ar}
            </span>
          </FicheRow>
        )}
        {level.head_ref && (
          <FicheRow label="المتعلَّق">
            {(() => {
              const [s, a] = level.head_ref.split(":");
              return (
                <Link
                  href={`/verse/${s}/${a}`}
                  className="inline-flex items-center gap-1 font-arabic text-lg text-brand-dark hover:underline"
                  title={level.head_ref}
                >
                  {level.head_ref}
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              );
            })()}
          </FicheRow>
        )}
      </dl>
    </LevelCard>
  );
}
