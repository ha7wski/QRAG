"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getSurahs } from "@/lib/api";
import type { SurahMeta } from "@/lib/types";
import SurahPicker, { SurahsIntro } from "@/components/SurahPicker";

/**
 * The «سور القرآن» main page: a heading, what the page is for, and the surah
 * picker. It never navigates by itself — a reload of `/surah/{n}` lands here
 * (see `SurahReader`), so an automatic resume would make it unreachable.
 */
export default function SurahIndexPage() {
  const router = useRouter();
  const [surahs, setSurahs] = useState<SurahMeta[] | null>(null);
  const [surahsFailed, setSurahsFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getSurahs()
      .then((list) => !cancelled && setSurahs(list))
      .catch(() => !cancelled && setSurahsFailed(true));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <SurahsIntro />

      <SurahPicker
        surahs={surahs}
        failed={surahsFailed}
        value=""
        onChoose={(n) => router.push(`/surah/${n}`)}
      />
    </div>
  );
}
