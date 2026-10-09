import type { LetterIdentity } from "@/lib/lisanTypes";
import { S } from "@/lib/strings";

/**
 * One card per radical: the letter, its name and مخرج, its position in the root,
 * and Samer Islambouli's gloss for it, verbatim. Shared by «تحليل اللسان», which
 * puts its section heading above it, and «فهرس الجذور», which shows the cards
 * alone inside an unfolded root.
 */
export default function LetterCards({ letters }: { letters: LetterIdentity[] }) {
  if (letters.length === 0) return null;

  return (
    <div data-testid="letter-cards" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {letters.map((l) => (
        <div key={l.index} className="rounded-lg border border-gray-200 bg-white p-3">
          <div className="flex items-center gap-3">
            <span className="font-arabic text-4xl leading-none text-brand">{l.letter}</span>
            <div className="min-w-0">
              <div className="truncate font-arabic text-sm font-medium text-gray-800">
                {l.name}
              </div>
              <div className="font-arabic text-xs text-gray-500">{l.makhraj}</div>
            </div>
            <span
              title={S.lexical.positionLabel}
              className="ms-auto rounded bg-gray-100 px-1.5 py-0.5 font-arabic text-[11px] text-gray-600"
            >
              {S.lexical.position[l.position]}
            </span>
          </div>

          {l.islambouli ? (
            <p className="mt-2 font-arabic text-base leading-relaxed text-gray-800">
              {l.islambouli}
            </p>
          ) : (
            <p className="mt-2 font-arabic text-sm text-gray-400">
              {S.lexical.islambouliMissing}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
