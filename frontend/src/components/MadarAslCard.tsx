import StatusBadge from "./StatusBadge";
import type { MaqayisCitation } from "@/lib/madarTypes";
import { toArabicDigits } from "@/lib/arabicDigits";

/**
 * Ibn Fāris' aṣl — the CITED, sourced lexical pivot. Prominence tracks
 * reliability: a real cited aṣl is the brand-highlighted centerpiece;
 * absent/uncertain states render as honest neutral cards that never expose an
 * unverified aṣl as if it were clean.
 *
 * Self-contained and RTL — dropped in standalone in Verse Study → "Word in
 * Verses" (above the occurrences of the resolved root).
 */

/** Honest count word for the aṢl — derived from `asl_count`, NOT from
 *  `asl_text.length` (the store may combine several aṣl into one text). */
function aslCountLabel(n: number): string {
  if (n === 2) return "أصلان";
  if (n === 3) return "ثلاثة أصول";
  if (n >= 4) return `${toArabicDigits(n)} أصول`;
  return "";
}

// Machine ids in the dataset → sober Arabic display strings (fallback: raw id).
const SOURCE_DISPLAY: Record<string, string> = {
  maqayis_openiti: "معجم مقاييس اللغة لابن فارس",
};
const EDITION_DISPLAY: Record<string, string> = {
  Harun_DarAlFikr: "تحقيق عبد السلام هارون (دار الفكر)",
};
function sourceLine(m: MaqayisCitation): string {
  const s = SOURCE_DISPLAY[m.source] || m.source;
  const e = EDITION_DISPLAY[m.edition] || m.edition;
  return e ? `${s} — ${e}` : s;
}

export default function MadarAslCard({
  maqayis,
}: {
  maqayis: MaqayisCitation | null;
}) {
  const hasAsl = maqayis?.asl_status === "has_asl";
  return (
    <section
      dir="rtl"
      className={
        hasAsl
          ? "rounded-lg border-2 border-brand bg-brand-light/40 p-5"
          : "rounded-lg border border-gray-200 bg-white p-4"
      }
    >
      <h3 className="mb-3 flex items-baseline gap-2 font-arabic font-semibold text-gray-800">
        أصل ابن فارس
        {maqayis?.asl_status === "parse_uncertain" && (
          <StatusBadge
            variant="uncertain"
            title="الأصل غير مُتحقَّق من المصدر؛ لا يُعرَض نصُّه."
          >
            غير مُتحقَّق
          </StatusBadge>
        )}
      </h3>
      <AslBody maqayis={maqayis} />
    </section>
  );
}

function AslBody({ maqayis }: { maqayis: MaqayisCitation | null }) {
  // Root outside the Maqāyīs dataset — honest, no invention.
  if (maqayis === null) {
    return (
      <p className="font-arabic text-gray-500">
        لا يوجد أصل مُسجَّل لهذا الجذر في المقاييس.
      </p>
    );
  }
  // Ibn Fāris himself states there is no aṣl.
  if (maqayis.asl_status === "no_asl") {
    return (
      <p className="font-arabic text-lg text-gray-700">لا أصل له عند ابن فارس.</p>
    );
  }
  // Unverified parse → treat as absent; never expose the doubtful text.
  if (maqayis.asl_status !== "has_asl") {
    return (
      <p className="font-arabic text-gray-500">
        الأصل غير مُتحقَّق من المصدر؛ لا يُعرَض نصٌّ غير موثوق.
      </p>
    );
  }
  // has_asl → cite it. Numbered when the store carries several text entries.
  const label = aslCountLabel(maqayis.asl_count);
  return (
    <>
      {maqayis.asl_text.length > 1 ? (
        <ol className="list-decimal space-y-2 pr-5 font-arabic text-lg leading-relaxed text-gray-900">
          {maqayis.asl_text.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ol>
      ) : (
        <p className="font-arabic text-xl leading-loose text-gray-900">
          {maqayis.asl_text[0]}
        </p>
      )}
      {maqayis.asl_count > 1 && label && (
        <p className="mt-2 font-arabic text-sm text-gray-500">
          يذكر ابن فارس {label}.
        </p>
      )}
      <p className="mt-3 font-arabic text-xs text-gray-400">
        {sourceLine(maqayis)}
      </p>
    </>
  );
}
