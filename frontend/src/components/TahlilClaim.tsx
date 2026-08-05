import Link from "next/link";
import type { TahlilClaim as Claim } from "@/lib/tahlilTypes";

/** The five evidence kinds a citation id can carry, parsed off its prefix. */
type CiteKind = "letter" | "nazir" | "sigha" | "contrast" | "maqayis" | "qac";

const KIND_LABEL: Record<CiteKind, string> = {
  letter: "حرف",
  nazir: "نظيرة",
  sigha: "صيغة",
  contrast: "مقابلة",
  maqayis: "مقاييس",
  qac: "إعراب",
};

function kindOf(cite: string): CiteKind | null {
  const kind = cite.split(":", 1)[0];
  return kind in KIND_LABEL ? (kind as CiteKind) : null;
}

/** `nazir:3:114:10` → `/verse/3/114`, so a naẓīra citation is a link to the verse itself.
 *  Returns null for every other kind: a citation that cannot be followed must not look
 *  like one that can. */
function nazirHref(cite: string): string | null {
  const parts = cite.split(":");
  if (parts[0] !== "nazir" || parts.length < 3) return null;
  const [surah, ayah] = [Number(parts[1]), Number(parts[2])];
  if (!Number.isInteger(surah) || !Number.isInteger(ayah)) return null;
  return `/verse/${surah}/${ayah}`;
}

/** Strip the kind prefix for display: `letter:س@p110-113` → `س@p110-113`. */
function body(cite: string): string {
  const at = cite.indexOf(":");
  return at >= 0 ? cite.slice(at + 1) : cite;
}

/** One generated assertion: its text, its badge, and the evidence it stands on.
 *
 * The citation strip is not decoration. `cite-or-omit` means every sentence here resolved
 * to a piece of evidence in code before it was rendered — showing that evidence is what
 * lets a reader check the claim rather than trust it. `sources` carries the human-readable
 * lines the backend built (author + page for a letter, row id + KB version for a form);
 * `cites` carries the ids, and naẓāʾir among them become links to the verse.
 */
export default function TahlilClaim({
  claim,
  badgeLabels,
  badgeTooltips,
}: {
  claim: Claim;
  badgeLabels: Record<string, string>;
  badgeTooltips: Record<string, string>;
}) {
  // Rendered from the payload, never from a local map: a frontend copy of these strings
  // could drift from the module that assigned the badge. Falling back to the raw badge key
  // keeps an unknown badge VISIBLE rather than blank — an unlabelled claim reads as an
  // unqualified one.
  const label = badgeLabels[claim.badge] ?? claim.badge;
  const tooltip = badgeTooltips[claim.badge];

  return (
    <li className="border-t border-gray-100 py-2.5 first:border-t-0 first:pt-0">
      <div dir="rtl" className="flex items-start justify-between gap-3">
        <p lang="ar" className="arabic-text flex-1 text-lg text-gray-800">
          {claim.text_ar}
        </p>
        <span
          title={tooltip}
          className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 font-arabic text-xs text-gray-600"
        >
          {label}
        </span>
      </div>

      {(claim.sources.length > 0 || claim.cites.length > 0) && (
        <div
          dir="rtl"
          className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-500"
        >
          {claim.sources.map((source, i) => (
            <span key={`s${i}`} lang="ar" className="font-arabic">
              {source}
            </span>
          ))}
          {claim.cites.map((cite) => {
            const kind = kindOf(cite);
            const href = nazirHref(cite);
            const text = `${kind ? KIND_LABEL[kind] : "شاهد"} ${body(cite)}`;
            return href ? (
              <Link
                key={cite}
                href={href}
                lang="ar"
                className="rounded bg-gray-50 px-1.5 py-0.5 font-arabic text-brand hover:underline"
              >
                {text}
              </Link>
            ) : (
              <span
                key={cite}
                lang="ar"
                className="rounded bg-gray-50 px-1.5 py-0.5 font-arabic"
              >
                {text}
              </span>
            );
          })}
        </div>
      )}
    </li>
  );
}
