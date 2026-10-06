"use client";

import { useEffect, useRef, useState } from "react";
import {
  type SurahSimilarityResponse,
  detailOf,
  getSurahSimilarity,
  getSurahs,
  statusOf,
} from "@/lib/api";
import type { SurahMeta } from "@/lib/types";
import { useCachedState } from "@/lib/pageCache";
import { S, forStatus } from "@/lib/strings";
import FailureNote, { type Failure } from "@/components/FailureNote";
import SurahPicker from "@/components/SurahPicker";
import { LoadingLine, VerseText } from "@/components/SimilarVerseParts";

/**
 * «داخل سورة» — the intra-surah similarity view of «الآيات المتقاربات».
 *
 * Pick a surah → its groups of mutually close verses, strongest first, each
 * framed in green and numbered (1, 2, 3 …) in a green disc beside it. A group
 * verse opens in «الآية في سياقها». (The picked-verse panel — the verse, then its
 * close verses in the rest of the Quran — was removed at the user's request;
 * the map «في سائر القرآن» is where cross-surah closeness is read.)
 *
 * Everything shown is read from a precomputed dataset (`GET /surah/{n}/similar`):
 * «close» there means the same meaning or subject AND nearly the same syntax,
 * and consecutive verses are never stored. The client therefore filters nothing
 * and computes nothing — and renders NO score: the order carries the ranking.
 *
 * All durable state lives under `verse-study.similar.surah.*`, so coming back to
 * this mode (or to the page) shows the same surah without a request.
 */
export default function SurahSimilarity({
  openInContext,
}: {
  /** Opens a verse in «الآية في سياقها» — the page's own handler. */
  openInContext: (surah: number, ayah: number) => void;
}) {
  // The surah list is shared reference data, cached under the page-neutral key
  // the context tab and the reading page use.
  const [surahs, setSurahs] = useCachedState<SurahMeta[]>("surahs.list", []);
  const [surahsFailed, setSurahsFailed] = useState(false);

  const [surah, setSurah] = useCachedState<number | "">(
    "verse-study.similar.surah.number",
    "",
  );
  const [data, setData] = useCachedState<SurahSimilarityResponse | null>(
    "verse-study.similar.surah.data",
    null,
  );
  const [error, setError] = useCachedState<Failure | null>(
    "verse-study.similar.surah.error",
    null,
  );
  // Transient — never cached (a cached `true` restores a spinner that never stops).
  const [loading, setLoading] = useState(false);
  // Only the latest request applies its answer: picking surah A then B quickly
  // must never end with A's groups under B's name.
  const surahSeq = useRef(0);

  useEffect(() => {
    if (surahs.length) return;
    getSurahs()
      .then(setSurahs)
      .catch(() => setSurahsFailed(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetches surah `n`'s view; only the latest surah request applies its answer.
  async function fetchSurah(n: number) {
    const seq = ++surahSeq.current;
    setLoading(true);
    try {
      const res = await getSurahSimilarity(n);
      if (seq === surahSeq.current) setData(res);
    } catch (e) {
      if (seq === surahSeq.current)
        setError({
          text: forStatus(statusOf(e), "surah"),
          detail: detailOf(e),
        });
    } finally {
      if (seq === surahSeq.current) setLoading(false);
    }
  }

  // A pick is cached before its answer lands, so leaving the page while a request
  // is in flight drops the answer and strands the pick: on return the select shows
  // it, nothing else does, and choosing the same option again fires no change. The
  // stranded request is therefore re-issued on mount.
  useEffect(() => {
    if (surah !== "" && !data && !error) void fetchSurah(surah);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function chooseSurah(n: number) {
    // The surah already on screen is not fetched again.
    if (n === surah && data?.surah_number === n) return;
    setSurah(n);
    setData(null);
    setError(null);
    void fetchSurah(n);
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-500">
        {S.verseStudy.surahSimilar.caption}
      </p>

      <SurahPicker
        surahs={surahs.length ? surahs : null}
        failed={surahsFailed}
        value={surah}
        current={data?.surah_name_ar}
        onChoose={chooseSurah}
      />

      {error && (
        <FailureNote
          failure={error}
          className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
        />
      )}

      {loading && <LoadingLine />}

      {data && !loading && (
        <div className="space-y-6">
          {data.unscored.length > 0 && (
            <p
              data-testid="surah-unscored-note"
              lang="ar"
              className="western-digits font-arabic text-sm text-gray-500"
            >
              {S.verseStudy.surahSimilar.unscoredNote(data.unscored)}
            </p>
          )}

          <section className="space-y-3">
            <h2 className="font-arabic text-xl font-semibold text-gray-800">
              {S.verseStudy.surahSimilar.groupsHeading}
            </h2>
            {data.groups.length === 0 ? (
              <div
                lang="ar"
                className="rounded-lg bg-amber-50 px-4 py-3 font-arabic text-lg text-amber-800"
              >
                {S.verseStudy.surahSimilar.noGroups}
              </div>
            ) : (
              data.groups.map((g, i) => (
                /* The group's number in a green disc on the reading side (right,
                   under the document's RTL), then the green-framed card. */
                <div key={g.ayahs.join(",")} className="flex items-start gap-3">
                  <span
                    data-testid="surah-similar-group-number"
                    aria-hidden="true"
                    className="western-digits mt-3 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand text-sm font-semibold text-white"
                  >
                    {i + 1}
                  </span>
                  <ul
                    data-testid="surah-similar-group"
                    className="min-w-0 flex-1 divide-y divide-gray-100 overflow-hidden rounded-lg border-2 border-brand bg-white"
                  >
                    {g.verses.map((v) => (
                      <li key={v.id}>
                        {/* A group verse opens in «الآية في سياقها». */}
                        <button
                          type="button"
                          onClick={() => openInContext(v.surah_number, v.ayah_number)}
                          title={S.verseStudy.openInContext}
                          className="block w-full px-4 py-3 text-start transition hover:bg-brand-light/50"
                        >
                          <VerseText verse={v} />
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))
            )}
          </section>
        </div>
      )}
    </div>
  );
}
