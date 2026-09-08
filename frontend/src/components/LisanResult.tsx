import { ArrowLeft, ChevronDown, Info } from "lucide-react";
import SarfiRows from "@/components/SarfiRows";
import type { LisanResponse } from "@/lib/lisanTypes";
import type { QlisanFormResponse } from "@/lib/types";
import { S } from "@/lib/strings";

/**
 * Renders a Lisan Analysis result: root, per-letter breakdown, the ordered
 * "sequential reading" chain, the deterministically-composed reading, an
 * optional Ibn Jinni (ishtiqaq al-akbar) section, and a persistent interpretive
 * disclaimer.
 *
 * The feature is Arabic-only: the whole panel renders RTL in Arabic (Amiri).
 * The synthesis is generated from the letter meanings by a template (never a
 * model), flagged by the muted "auto-generated" label under the reading.
 */
const CONFIDENCE_STYLES: Record<string, string> = {
  verified: "bg-brand-light text-brand-dark",
  high: "bg-blue-50 text-blue-700",
  summary: "bg-amber-50 text-amber-700",
  unknown: "bg-gray-100 text-gray-500",
};

// Confidence labels in Arabic.
const CONFIDENCE_LABELS: Record<string, string> = {
  verified: "مُحقَّق",
  high: "مُرجَّح",
  summary: "مُلخَّص",
  unknown: "غير مُحدَّد",
};

export default function LisanResult({
  data,
  sarfi = null,
}: {
  data: LisanResponse;
  /** Position-free morphology (POST /qlisan/form). Optional and independently
   *  fetched: the letter reading must not depend on it. */
  sarfi?: QlisanFormResponse | null;
}) {
  // No root resolved → helpful message, still carrying the disclaimer. The
  // grammar section still renders: a function word (مِن, الذي) is rootless in QAC
  // yet fully analysed morphologically, so there is real content to show here.
  if (!data.root) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 font-arabic text-amber-800">
          {data.message || S.lexical.noRoot(data.word)}
        </div>
        <GrammarSection sarfi={sarfi} />
        <Disclaimer text={data.disclaimer} sources={data.sources} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1 — Root + fallback badge */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="font-arabic text-sm text-gray-500">الجذر</span>
          <span className="font-arabic text-3xl text-brand-dark">
            {data.root}
          </span>
          {data.root_source === "fallback" && (
            <span
              title="جذر تقديري من المُجذِّر الحدسي، لا من مدونة QAC المُحقَّقة."
              className="rounded bg-amber-100 px-2 py-0.5 font-arabic text-xs font-medium text-amber-800"
            >
              جذر تقديري
            </span>
          )}
          <span className="ms-auto font-arabic text-2xl text-gray-700">
            {data.word}
          </span>
        </div>
      </div>

      {/* 2 — Letter breakdown */}
      <div>
        <h3 className="mb-2 font-arabic font-semibold text-gray-800">
          تحليل الحروف
        </h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.letters.map((l, i) => (
            <div
              key={`${l.letter}-${i}`}
              className="rounded-lg border border-gray-200 bg-white p-3"
            >
              <div className="flex items-center gap-3">
                <span className="font-arabic text-4xl leading-none text-brand">
                  {l.letter}
                </span>
                <div className="min-w-0">
                  <div className="truncate font-arabic text-sm font-medium text-gray-800">
                    {l.name}
                  </div>
                  <div className="font-arabic text-xs text-gray-500">
                    {l.makhraj}
                  </div>
                </div>
                <span
                  className={`ms-auto rounded px-1.5 py-0.5 font-arabic text-[11px] font-medium ${
                    CONFIDENCE_STYLES[l.confidence] || CONFIDENCE_STYLES.unknown
                  }`}
                >
                  {CONFIDENCE_LABELS[l.confidence] || CONFIDENCE_LABELS.unknown}
                </span>
              </div>
              {l.sifat.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {l.sifat.map((s) => (
                    <span
                      key={s}
                      className="rounded bg-gray-100 px-1.5 py-0.5 font-arabic text-[11px] text-gray-600"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
              {l.meaning && (
                <p className="mt-2 font-arabic text-base leading-relaxed text-gray-700">
                  {l.meaning}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 3 — Sequential reading (the ordered chain) */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="mb-3 font-arabic font-semibold text-gray-800">
          القراءة التتابعية
        </h3>
        <div className="flex flex-wrap items-stretch gap-2">
          {data.sequential_reading.map((s, i) => (
            <div key={s.index} className="flex items-stretch gap-2">
              <div className="flex max-w-[240px] flex-col rounded-lg bg-brand-light p-3">
                <span className="font-arabic text-2xl leading-none text-brand-dark">
                  {s.letter}
                </span>
                {s.meaning && (
                  <span className="mt-1 font-arabic text-sm leading-snug text-gray-600">
                    {s.meaning}
                  </span>
                )}
              </div>
              {/* The chain separator. A literal `←` is Bidi_Mirrored, so its
                  orientation inside an RTL run is engine-dependent — that
                  delegates a directional decision to the renderer. An SVG never
                  mirrors, and this row lays out right-to-left (design D14). */}
              {i < data.sequential_reading.length - 1 && (
                <ArrowLeft
                  aria-hidden
                  className="h-4 w-4 shrink-0 self-center text-gray-400"
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 4 — الصرف والإعراب: deterministic morphology (collapsible) — the established
          facts about the word come before the interpretive reading of its letters. */}
      <GrammarSection sarfi={sarfi} />

      {/* 5 — Synthesis (the main reading) — deterministically composed */}
      {data.synthesis && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-2 flex flex-wrap items-baseline gap-2">
            <h3 className="font-arabic font-semibold text-gray-800">
              قراءة اللسان
            </h3>
            <span className="font-arabic text-xs text-gray-400">
              مُولَّد آليًّا من دلالات الحروف
            </span>
          </div>
          <p className="whitespace-pre-wrap font-arabic text-lg leading-relaxed text-gray-800">
            {data.synthesis}
          </p>
        </div>
      )}

      {/* 6 — Ibn Jinni: ishtiqaq al-akbar (collapsible, interpretive) */}
      {data.ishtiqaq_akbar.length > 0 && (
        <details className="group rounded-lg border border-gray-200 bg-white p-4">
          <summary className="flex cursor-pointer items-center gap-2 font-arabic font-semibold text-gray-800">
            <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
            ابن جنّي — الاشتقاق الأكبر
            <span className="font-arabic text-xs font-normal text-gray-400">
              (تقاليب · تأويلي)
            </span>
          </summary>
          <div className="mt-3 flex flex-wrap gap-2">
            {data.ishtiqaq_akbar.map((p) => (
              <span
                key={p.form}
                title={p.gloss || undefined}
                className={`rounded px-2 py-1 font-arabic text-lg ${
                  p.gloss
                    ? "bg-brand-light text-brand-dark"
                    : "bg-gray-50 text-gray-500"
                }`}
              >
                {p.form}
              </span>
            ))}
          </div>
          <p className="mt-2 font-arabic text-xs text-gray-400">
            الصيغ المُظلَّلة جذورٌ مُثبَتة في المصحف.
          </p>
        </details>
      )}

      <Disclaimer text={data.disclaimer} sources={data.sources} />
    </div>
  );
}

/** «الصرف والإعراب» — the deterministic morphology of the typed word, collapsed by
 *  default (same `<details>` grammar as the ابن جنّي section below it).
 *
 * The reader typed a bare word, so there is no verse position — and QAC annotates
 * tokens IN CONTEXT, with no form→morphology lexicon. The backend therefore reads
 * the fiche from the word's FIRST occurrence and strips everything that belongs to
 * that occurrence rather than to the form (الحالة الإعرابية, حالة الفعل, العلامة).
 * النظائر stays: root and lemma decide it, so it holds for the form wherever it
 * occurs. Only rows that are true of the form are rendered, so the card carries no
 * provenance line — the response still names the occurrence in `ref` for callers
 * that want it.
 *
 * Renders nothing at all while the request is in flight or if it failed — the
 * letter reading is the page, this only supplements it.
 */
function GrammarSection({ sarfi }: { sarfi: QlisanFormResponse | null }) {
  if (!sarfi) return null;

  return (
    <details className="group rounded-lg border border-gray-200 bg-white p-4">
      <summary className="flex cursor-pointer items-center gap-2 font-arabic font-semibold text-gray-800">
        <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
        {S.lexical.sarfiSection}
        {sarfi.available && (
          <span className="ms-auto rounded-full bg-brand-light px-2 py-0.5 font-arabic text-xs text-brand-dark">
            معطى محقّق
          </span>
        )}
      </summary>

      <div className="mt-3">
        {sarfi.available ? (
          <SarfiRows level={sarfi.sarfi} />
        ) : (
          <p className="font-arabic text-base text-gray-500">
            {sarfi.message || "لا يوجد تحليل صرفي لهذه الكلمة."}
          </p>
        )}
      </div>
    </details>
  );
}


/** Persistent low-key disclaimer with a hover "sources" tooltip. */
function Disclaimer({
  text,
  sources,
}: {
  text: string;
  sources: Record<string, string>;
}) {
  const entries = Object.entries(sources || {});
  return (
    <div className="flex items-center gap-1.5 font-arabic text-xs text-gray-400">
      <Info className="h-3.5 w-3.5 shrink-0" />
      <span>{text}</span>
      {entries.length > 0 && (
        <span className="group relative ms-1">
          <button
            type="button"
            className="cursor-help underline decoration-dotted underline-offset-2"
          >
            المصادر
          </button>
          <span className="pointer-events-none absolute bottom-full start-0 z-10 mb-1 hidden w-72 rounded-lg border border-gray-200 bg-white p-3 text-start text-gray-600 shadow-lg group-hover:block">
            {entries.map(([k, v]) => (
              <span key={k} className="mb-1 block last:mb-0" dir="ltr">
                <span className="font-medium capitalize text-gray-700">
                  {k.replace("_", " ")}:
                </span>{" "}
                {v}
              </span>
            ))}
          </span>
        </span>
      )}
    </div>
  );
}
