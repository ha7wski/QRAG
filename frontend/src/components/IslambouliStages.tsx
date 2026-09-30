"use client";

import { useEffect, useState } from "react";
import { lisanReading, saveLisanReading } from "@/lib/api";
import type {
  CitedStatement,
  CulturalStage as CulturalStageData,
  IslambouliAssembly,
  LisanReading,
} from "@/lib/lisanTypes";
import { S } from "@/lib/strings";

/**
 * Islambouli on the «تحليل اللسان» page — two authors, kept visibly apart.
 *
 *   his own sentence for the root (when he published one), under its label AS
 *   PRINTED → the PROJECT's mechanical junction of his three rows, labelled as the
 *   project's → the gap between them, word by word → the cultural stage, only
 *   when it is cited or signed.
 *
 * The assembly is not his physical stage: his two published stages keep and drop
 * words, and join the rows, in ways no fixed template reproduces. So the gap is
 * shown rather than hidden — it IS the result.
 *
 * «أو» is never decided by the page: every alternative stays in the sentence
 * inside «( )», until a reader SIGNS a choice. The choice is stored with the
 * author's name and shown as that person's interpretation.
 */

const AUTHOR_KEY = "lisan.author";

function rememberedAuthor(): string {
  try {
    return window.localStorage.getItem(AUTHOR_KEY) || "";
  } catch {
    return "";
  }
}

function rememberAuthor(author: string) {
  try {
    window.localStorage.setItem(AUTHOR_KEY, author);
  } catch {
    /* a convenience only */
  }
}

export default function IslambouliStages({
  root,
  assembly,
  cultural,
  onSaved,
}: {
  root: string;
  assembly: IslambouliAssembly | null | undefined;
  cultural: CulturalStageData | null | undefined;
  /** Re-run the analysis after a signed reading is stored. */
  onSaved?: () => void;
}) {
  const [reading, setReading] = useState<LisanReading | null>(null);
  const [author, setAuthor] = useState("");
  const [text, setText] = useState("");
  const [status, setStatus] = useState<"idle" | "saved" | "failed">("idle");

  useEffect(() => {
    setAuthor(rememberedAuthor());
    let live = true;
    lisanReading(root)
      .then((r) => {
        if (!live) return;
        setReading(r);
        setText(r?.cultural_text ?? "");
        if (r?.author) setAuthor((a) => a || r.author);
      })
      .catch(() => live && setReading(null));
    return () => {
      live = false;
    };
  }, [root]);

  async function save(choices: Record<string, number>, culturalText: string) {
    const name = author.trim();
    if (!name) return;
    rememberAuthor(name);
    try {
      const stored = await saveLisanReading(root, name, culturalText, choices);
      setReading(stored);
      setStatus("saved");
      onSaved?.();
    } catch {
      setStatus("failed");
    }
  }

  function choose(position: number, alternative: number | null) {
    const choices = { ...(reading?.choices ?? {}) };
    if (alternative === null) delete choices[String(position)];
    else choices[String(position)] = alternative;
    save(choices, reading?.cultural_text ?? "");
  }

  return (
    <>
      {assembly && <AssemblyBlock assembly={assembly} canChoose={!!author.trim()} onChoose={choose} />}
      {cultural && <CulturalBlock cultural={cultural} />}

      <details className="rounded-lg border border-gray-200 bg-white p-4">
        <summary className="cursor-pointer font-arabic text-sm font-medium text-gray-700">
          {S.lexical.readingSummary}
        </summary>
        <div className="mt-3 space-y-2">
          <label className="block font-arabic text-xs text-gray-500">
            {S.lexical.readingAuthor}
            <input
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              aria-label={S.lexical.readingAuthor}
              className="mt-1 block w-full rounded border border-gray-300 px-2 py-1 font-arabic text-base"
            />
          </label>
          {!author.trim() && (
            <p className="font-arabic text-xs text-amber-700">{S.lexical.readingAuthorRequired}</p>
          )}
          <label className="block font-arabic text-xs text-gray-500">
            {S.lexical.readingText}
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              aria-label={S.lexical.readingText}
              rows={2}
              className="mt-1 block w-full rounded border border-gray-300 px-2 py-1 font-arabic text-base"
            />
          </label>
          <div className="flex items-center gap-2">
            <button
              onClick={() => save(reading?.choices ?? {}, text)}
              disabled={!author.trim()}
              className="rounded bg-brand px-3 py-1 font-arabic text-sm text-white disabled:opacity-50"
            >
              {S.lexical.readingSave}
            </button>
            {status === "saved" && (
              <span className="font-arabic text-xs text-gray-500">{S.lexical.readingSaved}</span>
            )}
            {status === "failed" && (
              <span className="font-arabic text-xs text-red-700">{S.lexical.readingFailed}</span>
            )}
          </div>
        </div>
      </details>
    </>
  );
}

function Cited({ cited }: { cited: CitedStatement }) {
  return (
    <div data-testid="islambouli-cited" className="rounded border-s-4 border-brand bg-brand-light/40 p-3">
      <div className="font-arabic text-xs font-semibold text-brand-dark">{cited.label}</div>
      <p className="mt-1 font-arabic text-xl leading-relaxed text-gray-900">{cited.text}</p>
      <p className="mt-1 font-arabic text-xs text-gray-500">{S.lexical.citedAttribution}</p>
      {cited.stage === "physical" && cited.label !== "الحالة الفيزيائية" && (
        <p className="mt-1 font-arabic text-xs text-gray-500">{S.lexical.citedClassification}</p>
      )}
    </div>
  );
}

function AssemblyBlock({
  assembly,
  canChoose,
  onChoose,
}: {
  assembly: IslambouliAssembly;
  canChoose: boolean;
  onChoose: (position: number, alternative: number | null) => void;
}) {
  const groups = assembly.positions
    .map((p, i) => ({ p, i }))
    .filter(({ p }) => p.alternatives.length > 1);

  return (
    <section aria-labelledby="lisan-assembly" className="space-y-3 rounded-lg border border-gray-200 bg-white p-4">
      <h2 id="lisan-assembly" className="font-arabic font-semibold text-gray-800">
        {S.lexical.assemblyHeading}
      </h2>

      {assembly.cited && (
        <div>
          <div className="mb-1 font-arabic text-xs text-gray-500">{S.lexical.citedHeading}</div>
          <Cited cited={assembly.cited} />
        </div>
      )}

      {assembly.refused ? (
        <p className="font-arabic text-gray-600">
          {S.lexical.assemblyRefused} {assembly.refusal_reason}
        </p>
      ) : (
        <div data-testid="islambouli-assembly" className="rounded border border-dashed border-gray-300 p-3">
          <div className="font-arabic text-xs font-semibold text-gray-600">{S.lexical.assemblyLabel}</div>
          <p className="mt-1 font-arabic text-xl leading-relaxed text-gray-800">{assembly.sentence}</p>
          {assembly.author ? (
            <p className="mt-1 font-arabic text-xs text-amber-800">{S.lexical.assemblyChoiceBy(assembly.author)}</p>
          ) : (
            groups.length > 0 && (
              <p className="mt-1 font-arabic text-xs text-gray-500">{S.lexical.assemblyAlternativesNote}</p>
            )
          )}
          {groups.map(({ p, i }) => (
            <div key={p.position} className="mt-2 flex flex-wrap items-center gap-1.5">
              <span className="font-arabic text-xs text-gray-500">
                {S.lexical.chooseLabel(S.lexical.assemblyPosition[p.position])}
              </span>
              {p.alternatives.map((alt, j) => (
                <button
                  key={alt}
                  disabled={!canChoose}
                  onClick={() => onChoose(i, j)}
                  aria-pressed={p.chosen === j}
                  className="rounded border border-gray-300 px-2 py-0.5 font-arabic text-sm aria-pressed:bg-amber-100 disabled:opacity-50"
                >
                  {alt}
                </button>
              ))}
              <button
                disabled={!canChoose}
                onClick={() => onChoose(i, null)}
                aria-pressed={p.chosen === null}
                className="rounded border border-gray-300 px-2 py-0.5 font-arabic text-sm aria-pressed:bg-gray-100 disabled:opacity-50"
              >
                {S.lexical.chooseAll}
              </button>
            </div>
          ))}
        </div>
      )}

      {assembly.gap && (
        <div data-testid="islambouli-gap" className="font-arabic text-sm text-gray-700">
          <div className="text-xs font-semibold text-gray-600">{S.lexical.gapHeading}</div>
          <p>
            {S.lexical.gapOnlyAssembly} {assembly.gap.only_assembly.join("، ") || S.lexical.gapNone}
          </p>
          <p>
            {S.lexical.gapOnlyCited} {assembly.gap.only_cited.join("، ") || S.lexical.gapNone}
          </p>
        </div>
      )}
    </section>
  );
}

function CulturalBlock({ cultural }: { cultural: CulturalStageData }) {
  if (cultural.citations.length === 0 && !cultural.personal) return null;
  return (
    <section
      aria-labelledby="lisan-cultural"
      data-testid="cultural-stage"
      className="space-y-2 rounded-lg border border-gray-200 bg-white p-4"
    >
      <h2 id="lisan-cultural" className="font-arabic font-semibold text-gray-800">
        {S.lexical.culturalHeading}
      </h2>
      {cultural.citations.map((c) => (
        <div key={c.id}>
          <p className="font-arabic text-xl leading-relaxed text-gray-900">{c.text}</p>
          <p className="font-arabic text-xs text-gray-500">{S.lexical.culturalCited}</p>
        </div>
      ))}
      {cultural.personal && (
        <div>
          <p className="font-arabic text-lg leading-relaxed text-gray-800">{cultural.personal.text}</p>
          <p className="font-arabic text-xs text-amber-800">
            {S.lexical.culturalPersonal(cultural.personal.author)}
          </p>
        </div>
      )}
    </section>
  );
}
