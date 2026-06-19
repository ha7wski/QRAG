"use client";

import { useState } from "react";
import { Loader2, Type } from "lucide-react";
import { lexical } from "@/lib/api";
import type { LexicalResponse } from "@/lib/types";
import LexicalResult from "@/components/LexicalResult";

export default function LexicalPage() {
  const [word, setWord] = useState("");
  const [language, setLanguage] = useState("en");
  const [data, setData] = useState<LexicalResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!word.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      setData(await lexical(word.trim(), language));
    } catch (e: any) {
      setError(e?.message || "Lookup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">
          Lexical analysis
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Enter an Arabic word to analyze its root across the whole Quran.
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
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 focus:border-brand focus:outline-none"
        >
          <option value="en">English</option>
          <option value="fr">Français</option>
          <option value="ar">العربية</option>
        </select>
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
          Analyzing… (the LLM may take a moment)
        </p>
      )}

      {data && !loading && <LexicalResult data={data} />}
    </div>
  );
}
