import { ChevronDown, Info } from "lucide-react";
import type { LisanResponse } from "@/lib/lisanTypes";

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

export default function LisanResult({ data }: { data: LisanResponse }) {
  // No root resolved → helpful message, still carrying the disclaimer.
  if (!data.root) {
    return (
      <div className="space-y-4" dir="rtl">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 font-arabic text-amber-800">
          {data.message || `No root found for "${data.word}".`}
        </div>
        <Disclaimer text={data.disclaimer} sources={data.sources} />
      </div>
    );
  }

  return (
    <div className="space-y-6" dir="rtl">
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
          <span className="mr-auto font-arabic text-2xl text-gray-700">
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
                  className={`mr-auto rounded px-1.5 py-0.5 font-arabic text-[11px] font-medium ${
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
              {i < data.sequential_reading.length - 1 && (
                <span className="self-center text-gray-400">←</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 4 — Synthesis (the main reading) — deterministically composed */}
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

      {/* 5 — Ibn Jinni: ishtiqaq al-akbar (collapsible, interpretive) */}
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
        <span className="group relative mr-1">
          <button
            type="button"
            className="cursor-help underline decoration-dotted underline-offset-2"
          >
            المصادر
          </button>
          <span className="pointer-events-none absolute bottom-full right-0 z-10 mb-1 hidden w-72 rounded-lg border border-gray-200 bg-white p-3 text-right text-gray-600 shadow-lg group-hover:block">
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
