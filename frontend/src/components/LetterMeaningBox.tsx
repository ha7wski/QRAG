import type { LetterMeaning } from "@/lib/types";
import { S } from "@/lib/strings";
import ArabicText from "@/components/ArabicText";

/**
 * The selected letter's box on «فهرس الجذور», read from the «معاني الحروف»
 * sheet (`GET /roots/letter/{letter}` → `maani`).
 *
 * Interpretive, and labelled so. Attribution is never blurred: the header says
 * whether the letter is Abu Qaisar's own or built by generalising his procedure,
 * each position says how it was obtained, and each source reading sits beside
 * its authority's name. An unknown code renders as itself rather than as a
 * guessed name.
 */
export default function LetterMeaningBox({ maani }: { maani: LetterMeaning }) {
  const t = S.roots.maani;

  return (
    <section
      aria-labelledby="letter-meaning"
      data-testid="letter-meaning"
      className="space-y-4 rounded-lg border border-brand/30 bg-white p-4"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h3 id="letter-meaning" className="font-arabic text-lg font-semibold text-gray-800">
          <ArabicText>{t.heading(maani.letter, maani.name)}</ArabicText>
        </h3>
        <span
          title={t.badgeTitle}
          className="rounded-full bg-amber-50 px-2 py-0.5 font-arabic text-xs text-amber-800"
        >
          {t.badge}
        </span>
        <span data-testid="letter-meaning-series" className="font-arabic text-xs text-gray-500">
          {t.series[maani.series] ?? maani.series}
        </span>
      </div>

      <div>
        <p className="font-arabic text-xs text-gray-500">{t.coreSense}</p>
        <p data-testid="letter-meaning-core" className="font-arabic text-base text-gray-800">
          <ArabicText>{maani.core_sense}</ArabicText>
        </p>
      </div>

      <div className="space-y-2">
        <p className="font-arabic text-xs text-gray-500">{t.positionsLabel}</p>
        <div className="grid gap-2 sm:grid-cols-3">
          {maani.positions.map((p) => (
            <div
              key={p.position}
              data-testid={`letter-meaning-${p.position}`}
              className="space-y-1 rounded border border-gray-200 bg-gray-50 p-3"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-1">
                <span className="font-arabic text-sm font-semibold text-gray-700">
                  {t.position[p.position] ?? p.position}
                </span>
                <span className="font-arabic text-[11px] text-gray-400">
                  {t.origin[p.origin] ?? p.origin}
                </span>
              </div>
              {p.divine_name && (
                <p className="font-arabic text-sm text-brand-dark">
                  <ArabicText>{p.divine_name}</ArabicText>
                </p>
              )}
              <p className="font-arabic text-sm text-gray-800">
                <ArabicText>{p.sense}</ArabicText>
              </p>
              {p.examples.length > 0 && (
                <p className="font-arabic text-xs text-gray-500">
                  {t.examples} <ArabicText>{p.examples.join("، ")}</ArabicText>
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {maani.sources.length > 0 && (
        <div className="space-y-1">
          <p className="font-arabic text-xs text-gray-500">{t.sourcesLabel}</p>
          <ul className="space-y-1">
            {maani.sources.map((s) => (
              <li key={s.key} data-testid={`letter-meaning-source-${s.key}`} className="font-arabic text-sm">
                <span className="font-semibold text-gray-700">{t.authority[s.key] ?? s.key}</span>
                {" : "}
                <ArabicText className="text-gray-800">{s.reading}</ArabicText>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(maani.drawing || maani.structure || maani.dimensions.length > 0) && (
        <div className="space-y-1 font-arabic text-sm text-gray-700">
          {maani.drawing && (
            <p>
              <span className="text-gray-500">{t.drawing}</span>{" "}
              {/* Some drawings are stored in French («resh = tête»): shown as is. */}
              <span dir="auto">{maani.drawing}</span>
            </p>
          )}
          {maani.structure && (
            <p>
              <span className="text-gray-500">{t.structure}</span>{" "}
              <ArabicText>{maani.structure}</ArabicText>
            </p>
          )}
          {maani.dimensions.length > 0 && (
            <div>
              <p className="text-gray-500">{t.dimensions}</p>
              <ul className="space-y-0.5">
                {maani.dimensions.map((d) => (
                  <li key={d.letter}>
                    <ArabicText>
                      <span className="font-semibold">{d.letter}</span> : {d.sense}
                    </ArabicText>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
