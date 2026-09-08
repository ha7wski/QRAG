import React from "react";

/** The tone of a level card's frame and badge pill.
 *
 * `fact` / `sourced` / `pending` are QLisan's original three and keep their exact class
 * strings, so extracting this component out of `qlisan/page.tsx` changed nothing there.
 *
 * `generated` and `interpretive` are added for Tahlil, whose badges are a **provenance**
 * vocabulary, not a quality one. They are visually distinct from `fact` on purpose — but
 * the distinction that carries the guarantee is the LABEL TEXT, not the tone: a reader in
 * greyscale, a colour-blind reader, or anyone looking at a screenshot must still be able to
 * tell «معطى محقّق» from «تأويلي». Tone is decoration; the label is contract.
 */
export type LevelTone =
  | "fact"
  | "sourced"
  | "pending"
  | "generated"
  | "interpretive";

const RING: Record<LevelTone, string> = {
  fact: "border-brand/30",
  sourced: "border-emerald-300",
  pending: "border-dashed border-gray-300",
  generated: "border-sky-300",
  interpretive: "border-amber-300",
};

const PILL: Record<LevelTone, string> = {
  fact: "bg-brand-light text-brand-dark",
  sourced: "bg-emerald-50 text-emerald-700",
  pending: "bg-gray-100 text-gray-500",
  generated: "bg-sky-50 text-sky-700",
  interpretive: "bg-amber-50 text-amber-700",
};

/** Card shell with an Arabic level label and a provenance badge. */
export default function LevelCard({
  titleAr,
  titleEn,
  badge,
  tone,
  badgeTitle,
  note,
  children,
}: {
  titleAr: string;
  titleEn: string;
  badge: string;
  tone: LevelTone;
  /** Native-title tooltip for the badge pill — the repo's established mechanism. */
  badgeTitle?: string;
  /** A short mention rendered beside the badge IN WORDS (e.g. «غير مُحقَّق»). */
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={`overflow-hidden rounded-xl border bg-white ${RING[tone]}`}>
      {/* RTL header: the Arabic title sits on the RIGHT (main title), the English
          label to its left, and the badge on the far left. */}
      <header
        className="flex items-center justify-between gap-2 border-b border-gray-100 px-4 py-2.5"
      >
        <span className="flex items-baseline gap-2">
          <span lang="ar" className="font-arabic text-xl font-semibold text-gray-800">
            {titleAr}
          </span>
          <span dir="ltr" className="text-xs uppercase tracking-wide text-gray-400">
            {titleEn}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          {/* The mention is rendered as TEXT, never as a tone: «this has not been
              verified» must survive a greyscale print. */}
          {note && (
            <span
              lang="ar"
              className="rounded bg-amber-50 px-1.5 py-0.5 font-arabic text-xs text-amber-700"
            >
              {note}
            </span>
          )}
          <span
            title={badgeTitle}
            className={`rounded-full px-2 py-0.5 text-xs ${PILL[tone]}`}
          >
            {badge}
          </span>
        </span>
      </header>
      <div className="px-4 py-3">{children}</div>
    </section>
  );
}
