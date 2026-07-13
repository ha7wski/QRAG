import { ChevronDown, Info } from "lucide-react";
import type { LisanResponse } from "@/lib/lisanTypes";

/**
 * Renders a Lisan Analysis result: root, per-letter breakdown, the ordered
 * "sequential reading" chain, the synthesized paragraph, an optional Ibn Jinni
 * (ishtiqaq al-akbar) section, and a persistent interpretive disclaimer.
 *
 * `lang` drives text direction: Arabic content (lang="ar") renders RTL/Amiri;
 * fr/en source text renders LTR (French prose comes from the synthesis step).
 */
const CONFIDENCE_STYLES: Record<string, string> = {
  verified: "bg-brand-light text-brand-dark",
  high: "bg-blue-50 text-blue-700",
  summary: "bg-amber-50 text-amber-700",
  unknown: "bg-gray-100 text-gray-500",
};

export default function LisanResult({
  data,
  lang,
}: {
  data: LisanResponse;
  lang: string;
}) {
  const isArabic = lang === "ar";
  const textDir = isArabic ? "rtl" : "ltr";

  // No root resolved → helpful message, still carrying the disclaimer.
  if (!data.root) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800">
          {data.message || `No root found for "${data.word}".`}
        </div>
        <Disclaimer text={data.disclaimer} sources={data.sources} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1 — Root + fallback badge */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="text-sm text-gray-500">Root</span>
          <span dir="rtl" className="font-arabic text-3xl text-brand-dark">
            {data.root}
          </span>
          {data.root_source === "fallback" && (
            <span
              title="Resolved by the heuristic stemmer, not the verified QAC corpus."
              className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
            >
              heuristic root
            </span>
          )}
          <span className="ml-auto font-arabic text-2xl text-gray-700" dir="rtl">
            {data.word}
          </span>
        </div>
      </div>

      {/* 2 — Letter breakdown */}
      <div>
        <h3 className="mb-2 font-semibold text-gray-800">Letter breakdown</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.letters.map((l, i) => (
            <div
              key={`${l.letter}-${i}`}
              className="rounded-lg border border-gray-200 bg-white p-3"
            >
              <div className="flex items-center gap-3">
                <span
                  dir="rtl"
                  className="font-arabic text-4xl leading-none text-brand"
                >
                  {l.letter}
                </span>
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-gray-800">
                    {l.name}
                  </div>
                  <div className="text-xs text-gray-500">{l.makhraj}</div>
                </div>
                <span
                  className={`ml-auto rounded px-1.5 py-0.5 text-[10px] font-medium ${
                    CONFIDENCE_STYLES[l.confidence] || CONFIDENCE_STYLES.unknown
                  }`}
                >
                  {l.confidence}
                </span>
              </div>
              {l.sifat.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1" dir={textDir}>
                  {l.sifat.map((s) => (
                    <span
                      key={s}
                      className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-600"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
              {l.meaning && (
                <p
                  dir={textDir}
                  className={`mt-2 text-sm leading-relaxed text-gray-700 ${
                    isArabic ? "font-arabic text-base" : ""
                  }`}
                >
                  {l.meaning}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 3 — Sequential reading (the ordered chain) */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="mb-3 font-semibold text-gray-800">Sequential reading</h3>
        <div className="flex flex-wrap items-stretch gap-2">
          {data.sequential_reading.map((s, i) => (
            <div key={s.index} className="flex items-stretch gap-2">
              <div className="flex max-w-[240px] flex-col rounded-lg bg-brand-light p-3">
                <span
                  dir="rtl"
                  className="font-arabic text-2xl leading-none text-brand-dark"
                >
                  {s.letter}
                </span>
                {s.meaning && (
                  <span
                    dir={textDir}
                    className={`mt-1 text-xs leading-snug text-gray-600 ${
                      isArabic ? "font-arabic text-sm" : ""
                    }`}
                  >
                    {s.meaning}
                  </span>
                )}
              </div>
              {i < data.sequential_reading.length - 1 && (
                <span className="self-center text-gray-400">→</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 4 — Synthesis (the main answer) */}
      {data.synthesis && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h3 className="mb-2 font-semibold text-gray-800">Lisan reading</h3>
          <p
            dir={textDir}
            className={`whitespace-pre-wrap leading-relaxed text-gray-800 ${
              isArabic ? "font-arabic text-lg" : "text-sm"
            }`}
          >
            {data.synthesis}
          </p>
        </div>
      )}

      {/* 5 — Ibn Jinni: ishtiqaq al-akbar (collapsible, interpretive) */}
      {data.ishtiqaq_akbar.length > 0 && (
        <details className="group rounded-lg border border-gray-200 bg-white p-4">
          <summary className="flex cursor-pointer items-center gap-2 font-semibold text-gray-800">
            <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
            Ibn Jinnī — ishtiqāq al-akbar
            <span className="text-xs font-normal text-gray-400">
              (permutations · interpretive)
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
                dir="rtl"
              >
                {p.form}
              </span>
            ))}
          </div>
          <p className="mt-2 text-xs text-gray-400">
            Highlighted forms are attested roots in the Quranic corpus.
          </p>
        </details>
      )}

      <Disclaimer text={data.disclaimer} sources={data.sources} />
    </div>
  );
}

/** Persistent low-key disclaimer with a hover "Sources" tooltip. */
function Disclaimer({
  text,
  sources,
}: {
  text: string;
  sources: Record<string, string>;
}) {
  const entries = Object.entries(sources || {});
  return (
    <div className="flex items-center gap-1.5 text-xs text-gray-400">
      <Info className="h-3.5 w-3.5 shrink-0" />
      <span>{text}</span>
      {entries.length > 0 && (
        <span className="group relative ml-1">
          <button
            type="button"
            className="cursor-help underline decoration-dotted underline-offset-2"
          >
            Sources
          </button>
          <span className="pointer-events-none absolute bottom-full left-0 z-10 mb-1 hidden w-72 rounded-lg border border-gray-200 bg-white p-3 text-left text-gray-600 shadow-lg group-hover:block">
            {entries.map(([k, v]) => (
              <span key={k} className="mb-1 block last:mb-0">
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
