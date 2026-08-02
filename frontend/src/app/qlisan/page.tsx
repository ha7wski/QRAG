"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, Loader2, Search } from "lucide-react";
import { getSurahs, qlisanVerse, qlisanWord } from "@/lib/api";
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
  const [surahs, setSurahs] = useState<SurahMeta[]>([]);
  const [surah, setSurah] = useState(1);
  const [ayah, setAyah] = useState(1);

  const [verse, setVerse] = useState<QlisanVerseResponse | null>(null);
  const [verseLoading, setVerseLoading] = useState(false);
  const [verseError, setVerseError] = useState<string | null>(null);

  const [selectedWord, setSelectedWord] = useState<number | null>(null);
  const [fiche, setFiche] = useState<QlisanWordResponse | null>(null);
  const [ficheLoading, setFicheLoading] = useState(false);
  const [ficheError, setFicheError] = useState<string | null>(null);

  // Monotonic request ids — only the latest response for each lane applies, so a
  // fast re-click / re-load never loses to a stale response.
  const verseSeq = useRef(0);
  const ficheSeq = useRef(0);

  // Load the surah list (Arabic names) for the picker.
  useEffect(() => {
    getSurahs()
      .then(setSurahs)
      .catch((e) => setVerseError(e?.message || "Failed to load surah list"));
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
        <h1 className="text-2xl font-semibold text-gray-800">QLisan</h1>
        <p className="mt-1 text-sm text-gray-500">
          Pick a verse, then click a single word to see its four-level analysis
          — صوتي, صرفي, نحوي, دلالي. Morphology and syntax are served
          deterministically from the parsed corpus (no LLM).
        </p>
      </div>

      {/* Verse picker — surah select + ayah number. */}
      <div className="flex flex-wrap items-center gap-2">
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
          aria-label="Ayah number"
          className="w-28 rounded-lg border border-gray-300 px-3 py-2 focus:border-brand focus:outline-none"
        />
        <span className="text-sm text-gray-400">/ {maxAyah}</span>

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
          Load verse
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
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2 text-sm text-gray-500">
        <span className="font-medium text-gray-700" dir="rtl">
          {verse.surah_name_ar}
        </span>
        <span>
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
    sarfi: () => <SarfiLevel level={data.sarfi} />,
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
      {/* Selected word header. */}
      <div className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg bg-gray-100 px-4 py-3">
        <span dir="rtl" lang="ar" className="arabic-text text-3xl text-brand-dark">
          {data.word_uthmani}
        </span>
        <span dir="ltr" className="text-xs text-gray-500">
          {data.ref}
        </span>
      </div>

      {data.levels_order.map((key) => (
        <div key={key}>{renderers[key]?.() ?? null}</div>
      ))}
    </div>
  );
}

/** Card shell with an Arabic level label and a "fact vs sourced/pending" badge. */
function LevelCard({
  titleAr,
  titleEn,
  badge,
  tone,
  children,
}: {
  titleAr: string;
  titleEn: string;
  badge: string;
  // "fact" = deterministic (established), "sourced" = cited lexicon,
  // "pending" = not yet available.
  tone: "fact" | "sourced" | "pending";
  children: React.ReactNode;
}) {
  const ring =
    tone === "fact"
      ? "border-brand/30"
      : tone === "sourced"
        ? "border-emerald-300"
        : "border-dashed border-gray-300";
  const badgeCls =
    tone === "fact"
      ? "bg-brand-light text-brand-dark"
      : tone === "sourced"
        ? "bg-emerald-50 text-emerald-700"
        : "bg-gray-100 text-gray-500";
  return (
    <section className={`overflow-hidden rounded-xl border bg-white ${ring}`}>
      <header className="flex items-center justify-between gap-2 border-b border-gray-100 px-4 py-2.5">
        <span className="flex items-baseline gap-2">
          <span
            dir="rtl"
            lang="ar"
            className="font-arabic text-xl font-semibold text-gray-800"
          >
            {titleAr}
          </span>
          <span className="text-xs uppercase tracking-wide text-gray-400">
            {titleEn}
          </span>
        </span>
        <span className={`rounded-full px-2 py-0.5 text-xs ${badgeCls}`}>
          {badge}
        </span>
      </header>
      <div className="px-4 py-3">{children}</div>
    </section>
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

/** صرفي — deterministic morphology from the treebank. */
function SarfiLevel({ level }: { level: QlisanSarfi }) {
  if (!level.available) {
    return (
      <LevelCard titleAr="صرفي" titleEn="Morphological" badge="غير متاح" tone="pending">
        <p dir="rtl" lang="ar" className="font-arabic text-base text-gray-500">
          لا يوجد تحليل صرفي لهذه الكلمة.
        </p>
      </LevelCard>
    );
  }

  const featureEntries = Object.entries(level.features || {}).filter(
    ([, v]) => v !== null && v !== undefined && v !== "",
  );

  return (
    <LevelCard titleAr="صرفي" titleEn="Morphological" badge="معطى محقّق" tone="fact">
      <dl className="space-y-3" dir="rtl">
        {/* Part of speech. */}
        <Row label="القسم">
          <span className="font-arabic text-lg text-gray-800">
            {level.pos_ar || "—"}
          </span>
          {level.pos && (
            <span dir="ltr" className="ml-2 text-xs text-gray-400">
              {level.pos}
            </span>
          )}
        </Row>

        {/* Root (or proper-noun marker). */}
        <Row label={level.is_proper_noun ? "اسم علم" : "الجذر"}>
          {level.is_proper_noun ? (
            <span className="font-arabic text-lg text-gray-800">
              {level.lemma_display || level.root_display || "—"}
            </span>
          ) : (
            <span className="font-arabic text-2xl tracking-widest text-brand-dark">
              {level.root_display || level.root || "—"}
            </span>
          )}
        </Row>

        {/* Lemma. */}
        {(level.lemma_display || level.lemma) && (
          <Row label="اللفظ">
            <span className="font-arabic text-lg text-gray-800">
              {level.lemma_display || level.lemma}
            </span>
          </Row>
        )}

        {/* Segments. */}
        {level.segments && level.segments.length > 0 && (
          <Row label="المقاطع">
            <span className="flex flex-wrap gap-1.5">
              {level.segments.map((seg, i) => (
                <span
                  key={i}
                  className="rounded bg-gray-100 px-1.5 py-0.5 font-arabic text-base text-gray-700"
                >
                  {seg}
                </span>
              ))}
            </span>
          </Row>
        )}

        {/* Grammatical features. */}
        {featureEntries.length > 0 && (
          <Row label="الخصائص">
            <span className="flex flex-wrap gap-1.5">
              {featureEntries.map(([k, v]) => (
                <span
                  key={k}
                  dir="ltr"
                  className="rounded bg-brand-light px-1.5 py-0.5 text-xs text-brand-dark"
                >
                  {k}: {String(v)}
                </span>
              ))}
            </span>
          </Row>
        )}

        {/* Root siblings (naẓāʾir) → deep-links to their verses. */}
        {level.nazair && level.nazair.length > 0 && (
          <Row label="النظائر">
            <span className="flex flex-wrap gap-1.5">
              {level.nazair.map((n) => {
                const [s, a] = n.ref.split(":");
                return (
                  <Link
                    key={n.ref}
                    href={`/verse/${s}/${a}`}
                    title={n.ref}
                    className="rounded-md bg-gray-50 px-2 py-0.5 font-arabic text-base text-gray-700 ring-1 ring-gray-200 transition hover:bg-brand-light hover:text-brand-dark"
                  >
                    {n.word_uthmani}
                  </Link>
                );
              })}
            </span>
          </Row>
        )}
      </dl>
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
    <LevelCard titleAr="نحوي" titleEn="Syntactic" badge="معطى محقّق" tone="fact">
      <dl className="space-y-3" dir="rtl">
        {level.role_ar && (
          <Row label="الموقع الإعرابي">
            <span className="font-arabic text-lg text-gray-800">
              {level.role_ar}
            </span>
          </Row>
        )}
        {(level.relation_ar || level.relation) && (
          <Row label="العلاقة">
            <span className="font-arabic text-lg text-gray-800">
              {level.relation_ar || level.relation}
            </span>
            {level.relation && level.relation_ar && (
              <span dir="ltr" className="ml-2 text-xs text-gray-400">
                {level.relation}
              </span>
            )}
          </Row>
        )}
        {level.head_ref && (
          <Row label="المتعلَّق">
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
          </Row>
        )}
      </dl>
    </LevelCard>
  );
}

/** One right-aligned label/value row inside a fiche level. */
function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <dt className="min-w-[6rem] shrink-0 font-arabic text-sm text-gray-400">
        {label}
      </dt>
      <dd className="flex-1">{children}</dd>
    </div>
  );
}
