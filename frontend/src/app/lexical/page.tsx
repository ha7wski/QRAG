"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2, Type } from "lucide-react";
import { API_URL, qlisanForm } from "@/lib/api";
import type { LisanResponse } from "@/lib/lisanTypes";
import type { QlisanFormResponse } from "@/lib/types";
import { useCachedState } from "@/lib/pageCache";
import LisanResult from "@/components/LisanResult";

/**
 * Lisan Analysis — a single Arabic word read letter-by-letter as an interpretive
 * letter-symbolism reading of the lisān (POST /lisan/analyze). Arabic-only.
 *
 * Two independent lanes per run: the letter reading (the page) and the
 * deterministic morphology behind the «تحليل نحوي» section (POST /qlisan/form).
 * The morphology is supplementary — its failure costs the section, never the
 * reading — so it is fired alongside and its rejection swallowed.
 *
 * `?word=` deep-links into an analysis (Verse Study's «تحليل لساني» button sends
 * the reader here); `useSearchParams` requires the Suspense boundary below.
 */
export default function LexicalPage() {
  return (
    <Suspense fallback={null}>
      <LisanAnalysis />
    </Suspense>
  );
}

function LisanAnalysis() {
  // Cached: leaving for Verse Study and coming back restores the analysis rather
  // than an empty box. `loading` is deliberately NOT cached.
  const [word, setWord] = useCachedState("lexical.word", "");
  const [data, setData] = useCachedState<LisanResponse | null>(
    "lexical.data",
    null,
  );
  const [sarfi, setSarfi] = useCachedState<QlisanFormResponse | null>(
    "lexical.sarfi",
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useCachedState<string | null>("lexical.error", null);

  // Monotonic run id: only the latest run may write state, so two fast Enters
  // can never leave a reading of one word beside the morphology of another.
  const runSeq = useRef(0);

  // Arriving with ?word=: the parameter is an explicit intent, so it wins over
  // whatever the cache holds — but a word already on screen is not re-fetched,
  // so pressing the button twice for the same word costs nothing. The ref stores
  // the VALUE consumed, not a boolean: navigating ?word=A → ?word=B without an
  // unmount must still trigger the second analysis.
  const params = useSearchParams();
  const requested = params.get("word")?.trim() || "";
  const consumed = useRef<string | null>(null);
  useEffect(() => {
    if (!requested || consumed.current === requested) return;
    consumed.current = requested;
    setWord(requested);
    if (data?.word === requested) return; // already analysed and restored
    run(requested);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requested]);

  async function run(explicit?: string) {
    const typed = (explicit ?? word).trim();
    if (!typed || loading) return;
    const seq = ++runSeq.current;
    setLoading(true);
    setError(null);
    setSarfi(null);

    // Fired first so both lanes travel together; awaited last so the reading is
    // never held up by it.
    const morphology = qlisanForm(typed).catch(() => null);

    try {
      // Arabic-only: no `lang` in the body.
      const res = await fetch(`${API_URL}/lisan/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word: typed }),
      });
      if (!res.ok) {
        // 422 carries a FastAPI `detail`; surface it verbatim when present.
        let detail = `Analysis failed (${res.status})`;
        try {
          const body = await res.json();
          if (typeof body?.detail === "string") detail = body.detail;
        } catch {
          /* non-JSON error body — keep the status message */
        }
        throw new Error(detail);
      }
      const payload = await res.json();
      if (seq === runSeq.current) setData(payload);
    } catch (e: any) {
      if (seq === runSeq.current) {
        setData(null);
        setError(e?.message || "Analysis failed");
      }
    } finally {
      if (seq === runSeq.current) setLoading(false);
    }

    const resolved = await morphology;
    if (seq === runSeq.current) setSarfi(resolved);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">Lisan Analysis</h1>
        <p className="mt-1 text-sm text-gray-500">
          Enter an Arabic word to read its root letter-by-letter — an
          interpretive letter-symbolism reading of the lisān.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={word}
          onChange={(e) => setWord(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          dir="rtl"
          placeholder="رحمة"
          className="min-w-[200px] flex-1 rounded-lg border border-gray-300 px-3 py-2 font-arabic text-xl focus:border-brand focus:outline-none"
        />
        <button
          // Wrapped: `onClick={run}` would hand the MouseEvent to `explicit`.
          onClick={() => run()}
          disabled={loading || !word.trim()}
          className="flex items-center gap-1 rounded-lg bg-brand px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Type className="h-4 w-4" />
          )}
          Analyze
        </button>
      </div>

      {error && (
        <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && (
        <p className="text-sm text-gray-500">
          Reading the root… (synthesis may take a moment)
        </p>
      )}

      {data && !loading && <LisanResult data={data} sarfi={sarfi} />}
    </div>
  );
}
