"use client";

import SurahReader from "@/components/SurahReader";

/**
 * A surah at its own address — the target of every verse reference emitted
 * elsewhere in the app (`VerseCard`, `VerseContextCard`, `/verse/{s}/{a}`).
 *
 * A thin wrapper on purpose: `/surah` and `/surah/{n}` render the SAME
 * component, so the resumed and the addressed reading surfaces cannot drift.
 */
export default function SurahPage({ params }: { params: { number: string } }) {
  return <SurahReader number={Number(params.number)} />;
}
