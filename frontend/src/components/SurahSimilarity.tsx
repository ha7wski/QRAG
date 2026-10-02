"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  type AyahSimilarityResponse,
  type SurahSimilarityResponse,
  detailOf,
  getAyahSimilarity,
  getSurahSimilarity,
  getSurahs,
  statusOf,
} from "@/lib/api";
import type { SurahMeta, Verse } from "@/lib/types";
import { useCachedState } from "@/lib/pageCache";
import { S, forStatus } from "@/lib/strings";
import ArabicText from "@/components/ArabicText";
import FailureNote, { type Failure } from "@/components/FailureNote";
import SurahPicker from "@/components/SurahPicker";

/** The anchor panel's id — a group verse scrolls it into view when picked. */
const ANCHOR_PANEL_ID = "surah-similar-anchor";

/**
 * «داخل سورة» — the intra-surah similarity view of «الآيات المتشابهات».
 *
 * Pick a surah → its groups of mutually close verses, strongest first, each
 * framed in green and numbered (1, 2, 3 …) in a green disc beside it. Pick a verse of a group → its close verses in the
 * same surah, ranked, each with the content roots it shares with it.
 *
 * Everything shown is read from a precomputed dataset (`GET /surah/{n}/similar`):
 * «close» there means the same meaning or subject AND nearly the same syntax,
 * and consecutive verses are never stored. The client therefore filters nothing
 * and computes nothing — and renders NO score: the order carries the ranking.
 *
 * All durable state lives under `verse-study.similar.surah.*`, so coming back to
 * this mode (or to the page) shows the same surah and verse without a request.
 * Each fetched verse is kept in `anchors`, so revisiting one costs nothing either.
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
  const [ayah, setAyah] = useCachedState<number | null>(
    "verse-study.similar.surah.ayah",
    null,
  );
  // Fetched anchors of the CURRENT surah, keyed by ayah number.
  const [anchors, setAnchors] = useCachedState<
    Record<number, AyahSimilarityResponse>
  >("verse-study.similar.surah.anchors", {});
  const [ayahError, setAyahError] = useCachedState<Failure | null>(
    "verse-study.similar.surah.ayahError",
    null,
  );
  // Transient — never cached (a cached `true` restores a spinner that never stops).
  const [loading, setLoading] = useState(false);
  const [ayahLoading, setAyahLoading] = useState(false);
  // Only the latest request applies its answer: picking surah A then B quickly
  // must never end with A's groups under B's name.
  const surahSeq = useRef(0);
  const ayahSeq = useRef(0);

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

  // Fetches verse `a` of surah `s`; only the latest verse request applies its answer.
  async function fetchAyah(s: number, a: number) {
    const seq = ++ayahSeq.current;
    setAyahLoading(true);
    try {
      const res = await getAyahSimilarity(s, a);
      if (seq === ayahSeq.current)
        setAnchors((prev) => ({ ...prev, [a]: res }));
    } catch (e) {
      if (seq === ayahSeq.current)
        setAyahError({
          text: forStatus(statusOf(e), "verse"),
          detail: detailOf(e),
        });
    } finally {
      if (seq === ayahSeq.current) setAyahLoading(false);
    }
  }

  // A pick is cached before its answer lands, so leaving the page while a request
  // is in flight drops the answer and strands the pick: on return the select shows
  // it, nothing else does, and choosing the same option again fires no change. The
  // stranded request is therefore re-issued on mount.
  useEffect(() => {
    if (surah !== "" && !data && !error) void fetchSurah(surah);
    else if (data && ayah !== null && !anchors[ayah] && !ayahError)
      void fetchAyah(data.surah_number, ayah);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function chooseSurah(n: number) {
    // The surah already on screen is not fetched again.
    if (n === surah && data?.surah_number === n) return;
    ayahSeq.current++; // any verse still in flight belongs to the old surah
    setSurah(n);
    setData(null);
    setError(null);
    setAyah(null);
    setAnchors({});
    setAyahError(null);
    setAyahLoading(false);
    void fetchSurah(n);
  }

  function chooseAyah(a: number, scroll = false) {
    if (!data) return;
    setAyah(a);
    setAyahError(null);
    if (scroll) {
      const el = document.getElementById(ANCHOR_PANEL_ID);
      if (el && typeof el.scrollIntoView === "function")
        el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (anchors[a]) {
      ayahSeq.current++; // a verse still in flight must not replace this one
      setAyahLoading(false);
      return; // already fetched — switching verses is local
    }
    void fetchAyah(data.surah_number, a);
  }

  const anchor = ayah !== null ? anchors[ayah] : undefined;

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
                        {/* A group verse SELECTS that verse — its close verses
                          then open in the panel below. */}
                        <button
                          type="button"
                          onClick={() => chooseAyah(v.ayah_number, true)}
                          aria-pressed={ayah === v.ayah_number}
                          title={S.verseStudy.surahSimilar.selectAyah}
                          className={`block w-full px-4 py-3 text-start transition hover:bg-brand-light/50 ${
                            ayah === v.ayah_number ? "bg-brand-light/60" : ""
                          }`}
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

          {/* The verse panel, after the groups (D11: groups render first): the
              verse picked in a group, then its close verses. Picking scrolls
              down to it. */}
          <section id={ANCHOR_PANEL_ID} className="scroll-mt-4 space-y-4">
            {ayahError && (
              <FailureNote
                failure={ayahError}
                className="rounded bg-red-50 px-3 py-2 text-sm text-red-700"
              />
            )}

            {ayahLoading && <LoadingLine />}

            {anchor && !ayahLoading && (
              <AnchorPanel result={anchor} openInContext={openInContext} />
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function LoadingLine() {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-500">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span lang="ar" className="font-arabic">
        {S.verseStudy.surahSimilar.loading}
      </span>
    </div>
  );
}

/** A vocalized verse with its number badge. */
function VerseText({ verse }: { verse: Verse }) {
  return (
    <ArabicText className="block text-2xl leading-loose text-gray-900">
      {verse.text_ar_tashkil || verse.text_ar}{" "}
      <span className="western-digits align-middle text-sm text-gray-400">
        ﴿{verse.ayah_number}﴾
      </span>
    </ArabicText>
  );
}

/** The selected verse, then its close verses or the sentence saying why there
 *  are none. The two empty cases are worded apart on purpose: «not compared»
 *  (no content word) is not «compared, and nothing is close». */
function AnchorPanel({
  result,
  openInContext,
}: {
  result: AyahSimilarityResponse;
  openInContext: (surah: number, ayah: number) => void;
}) {
  const a = result.anchor;
  return (
    <div className="space-y-4">
      <VerseCardButton verse={a} openInContext={openInContext} highlighted />

      {result.unscored ? (
        <div
          role="status"
          lang="ar"
          className="rounded-lg bg-amber-50 px-4 py-3 font-arabic text-lg text-amber-800"
        >
          {S.verseStudy.surahSimilar.unscoredAnchor}
        </div>
      ) : result.neighbours.length === 0 ? (
        <div
          role="status"
          lang="ar"
          className="rounded-lg bg-amber-50 px-4 py-3 font-arabic text-lg text-amber-800"
        >
          {S.verseStudy.surahSimilar.noClose}
        </div>
      ) : (
        <div className="space-y-3">
          <h3 className="font-arabic text-lg font-semibold text-gray-800">
            {S.verseStudy.surahSimilar.closeHeading}
          </h3>
          <ol className="space-y-3">
            {result.neighbours.map((n) => (
              <li
                key={n.verse.id}
                data-testid="surah-similar-neighbour"
                className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition hover:border-brand"
              >
                <VerseCardButton
                  verse={n.verse}
                  openInContext={openInContext}
                />
                {n.roots.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 border-t border-gray-100 px-4 py-2">
                    <span className="font-arabic text-xs text-gray-500">
                      {S.verseStudy.surahSimilar.sharedRoots}
                    </span>
                    {n.roots.map((r) => (
                      <span
                        key={r}
                        lang="ar"
                        className="rounded-full border border-brand/30 bg-brand-light px-2.5 py-0.5 font-arabic text-base tracking-widest text-brand-dark"
                      >
                        {r}
                      </span>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

/** A whole-verse button that opens it in «الآية في سياقها». */
function VerseCardButton({
  verse,
  openInContext,
  highlighted = false,
}: {
  verse: Verse;
  openInContext: (surah: number, ayah: number) => void;
  highlighted?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => openInContext(verse.surah_number, verse.ayah_number)}
      title={S.verseStudy.openInContext}
      className={`block w-full p-4 text-start transition hover:bg-brand-light/50 ${
        highlighted ? "rounded-lg border border-brand/40 bg-brand-light/40" : ""
      }`}
    >
      <VerseText verse={verse} />
    </button>
  );
}
