import React from "react";

/**
 * One right-aligned label/value row inside an analysis fiche.
 *
 * Extracted from `qlisan/page.tsx` (where it served both the صرفي and نحوي cards)
 * so the Lisan Analysis «تحليل نحوي» section shares the exact same row geometry.
 * The fixed `min-w-[6rem]` label column is the whole point: it is what keeps the
 * value column aligned down a card, so the two pages cannot drift apart.
 */
export default function FicheRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <dt className="min-w-[6rem] shrink-0 font-arabic text-sm text-gray-400">
        {label}
      </dt>
      <dd className="flex-1">{children}</dd>
    </div>
  );
}
