import VerseCard from "./VerseCard";
import type { LexicalResponse } from "@/lib/types";

/** Renders the result of a root analysis: root, forms, occurrences, analysis. */
export default function LexicalResult({ data }: { data: LexicalResponse }) {
  if (!data.found) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800">
        No occurrences found for &quot;{data.word}&quot;
        {data.root ? ` (root ${data.root})` : ""}.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="text-sm text-gray-500">Root</span>
          <span dir="rtl" className="font-arabic text-2xl text-brand-dark">
            {data.root}
          </span>
          <span className="ml-auto text-sm text-gray-600">
            {data.occurrences_count} occurrences
          </span>
        </div>
        {data.forms.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {data.forms.slice(0, 24).map((f) => (
              <span
                key={f}
                dir="rtl"
                className="rounded bg-brand-light px-2 py-0.5 font-arabic text-base text-brand-dark"
              >
                {f}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="mb-2 font-semibold text-gray-800">Analysis</h3>
        <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-800">
          {data.analysis}
        </div>
      </div>

      {data.key_verses.length > 0 && (
        <div>
          <h3 className="mb-2 font-semibold text-gray-800">Key verses</h3>
          <div className="space-y-3">
            {data.key_verses.map((v) => (
              <VerseCard key={v.id} verse={v} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
