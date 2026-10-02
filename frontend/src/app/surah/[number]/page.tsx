"use client";

import SurahReader from "@/components/SurahReader";

/**
 * A surah at its own address — the target of every verse reference emitted
 * elsewhere in the app (`VerseCard`, `VerseContextCard`, `/verse/{s}/{a}`).
 *
 * A thin wrapper on purpose: the reading surface is `SurahReader`; `/surah` is
 * the main page that leads here.
 */
export default function SurahPage({ params }: { params: { number: string } }) {
  return <SurahReader number={Number(params.number)} />;
}
