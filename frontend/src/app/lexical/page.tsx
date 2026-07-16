"use client";

import { useState } from "react";
import { Loader2, Type } from "lucide-react";
import { API_URL } from "@/lib/api";
import type { LisanResponse } from "@/lib/lisanTypes";
import LisanResult from "@/components/LisanResult";

/**
 * Lisan Analysis — a single Arabic word read letter-by-letter as an interpretive
 * letter-symbolism reading of the lisān (POST /lisan/analyze). Arabic-only.
 */
export default function LexicalPage() {
  const [word, setWord] = useState("");
  const [data, setData] = useState<LisanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!word.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      // Arabic-only: no `lang` in the body.
      const res = await fetch(`${API_URL}/lisan/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word: word.trim() }),
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
      setData(await res.json());
    } catch (e: any) {
      setData(null);
      setError(e?.message || "Analysis failed");
    } finally {
      setLoading(false);
    }
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
          onClick={run}
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

      {data && !loading && <LisanResult data={data} />}
    </div>
  );
}
