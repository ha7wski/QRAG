// Shared types mirroring the FastAPI backend response models.

export interface Verse {
  id: string;
  surah_number: number;
  surah_name_ar: string;
  surah_name_en?: string;
  surah_name_fr?: string;
  ayah_number: number;
  text_ar: string;
  text_ar_tashkil?: string; // fully vocalized (harakat) — for display
  text_ar_clean?: string;
  translation_fr?: string;
  translation_en?: string;
  period?: string;
  juz?: number;
  relevance_score?: number | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface LexicalResponse {
  word: string;
  root: string;
  forms: string[];
  occurrences_count: number;
  analysis: string;
  key_verses: Verse[];
  found: boolean;
}

export interface VerseLookupVerse {
  surah_number: number;
  surah_name: string;
  aya_number: number;
  text: string; // vocalized (with full diacritics)
  match_indices: number[]; // token indices in `text` to highlight
}

export interface VerseLookupResponse {
  word: string;
  root: string;
  root_found: boolean;
  total: number;
  verses: VerseLookupVerse[];
}

export interface SearchResponse {
  query: string;
  results: Verse[]; // ranked by hybrid relevance (dense + BM25)
  total: number;
}

export interface VerseDetail {
  verse: Verse;
  context: Verse[];
  prev_id: string | null;
  next_id: string | null;
}

export interface SurahResponse {
  surah_number: number;
  surah_name_ar?: string;
  surah_name_en?: string;
  surah_name_fr?: string;
  period?: string;
  ayah_count: number;
  verses: Verse[];
}

export interface SurahMeta {
  number: number;
  name_ar?: string;
  name_en?: string;
  name_fr?: string;
  ayah_count: number;
}

export interface HealthStatus {
  status: "ok" | "degraded" | "starting";
  qdrant: boolean;
  llm: boolean;
}

export interface FeedbackStats {
  up: number;
  down: number;
  total: number;
}
