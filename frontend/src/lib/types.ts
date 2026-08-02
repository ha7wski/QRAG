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

export interface VerseLookupLemma {
  root: string; // the root this lemma belongs to
  lemma: string; // normalized lemma key
  lemma_display: string; // diacritized lemma label for display
  count: number; // number of verses under this lemma
  verses: VerseLookupVerse[];
}
export interface VerseLookupResponse {
  word: string;
  root: string; // " / "-joined root(s)
  roots: string[]; // every matched root (homographs → several)
  root_found: boolean; // true also for a resolved proper noun
  is_proper_noun?: boolean; // rootless name (لوط …): lemmas has one group
  total: number; // distinct verses across all lemma groups
  lemmas: VerseLookupLemma[];
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

// ── QLisan (per-word four-level analysis) ─────────────────────────────
// One selectable token in a verse. `char_start`/`char_end` are offsets into
// the vocalized `text` string (end exclusive); `aligned:false` marks a span
// derived by best-effort fallback rather than the QAC spine.
export interface QlisanToken {
  word: number; // 1-based QAC word_id
  uthmani: string;
  imlaai: string;
  char_start: number;
  char_end: number; // exclusive
  aligned: boolean;
}

export interface QlisanVerseResponse {
  surah: number;
  ayah: number;
  surah_name_ar: string;
  text: string; // vocalized chakl aya string, rendered as-is (RTL)
  tokens: QlisanToken[];
}

// A root sibling (naẓīr) sharing the selected word's root. Lemma-scoped so the
// UI can group the strip by lemma (never mixing homographic senses).
export interface QlisanNazair {
  ref: string; // "surah:ayah:word"
  word_uthmani: string;
  lemma?: string | null;
  lemma_display?: string | null;
}

// One morphology feature row, fully Arabic (label + value), never a raw code.
export interface QlisanSarfiFeature {
  label_ar: string;
  value_ar: string;
}

// One morphological segment: its vocalized surface text + Arabic type label
// (بادئة/جذع/لاحقة). Order is reading order (prefix → stem → suffix, right → left).
export interface QlisanSarfiSegment {
  text: string;
  type_ar: string;
}

// الميزان الصرفي — root projected onto ف-ع-ل. `verified` mirrors the level badge:
// true = exact projection («معطى محقّق»); false = hollow/geminate/irregular surface,
// shown as an heuristic «اجتهادي» hint outside the badge. `bab` is the verb-form
// pattern (فَعَلَ/فَعَّلَ/…) for verbs, else null.
export interface QlisanMizan {
  available: boolean;
  wazn: string | null;
  verified: boolean;
  bab: string | null;
}

// صوتي / دلالي — stubs in this increment (available:false + message). Typed
// with `available: boolean` so later increments can flip them on without a
// type change; the fiche renders the message when unavailable.
export interface QlisanStubLevel {
  available: boolean;
  message?: string | null;
}

// صرفي (morphological) — deterministic, from the parsed treebank.
export interface QlisanSarfi {
  available: boolean;
  root: string | null;
  root_display: string | null;
  lemma: string | null;
  lemma_display: string | null;
  pos: string; // raw QAC code, kept as data (not rendered)
  pos_ar: string;
  features: QlisanSarfiFeature[]; // ordered Arabic {label_ar, value_ar}
  segments: QlisanSarfiSegment[]; // per-segment vocalized text + Arabic type
  mizan: QlisanMizan; // الميزان الصرفي (root projected onto ف-ع-ل)
  is_proper_noun: boolean;
  nazair: QlisanNazair[];
}

// نحوي (syntactic) — deterministic, from the dependency treebank.
// `iraab_ar` is the composed «الموقع الإعرابي» (relation function [+ case word]);
// `marker_ar` is the derived العلامة (الأصل) hint, present only where reliable.
// `role_ar` is kept for shape-compat but no longer populated; raw
// `relation`/`relation_ar` stay in the payload as data (not rendered).
export interface QlisanNahwi {
  available: boolean;
  role_ar: string | null; // deprecated: no longer populated
  relation: string | null; // raw QAC code, kept as data (not rendered)
  relation_ar: string | null; // raw source label, kept as data (not rendered)
  iraab_ar: string | null;
  marker_ar: string | null;
  head_ref: string | null;
  message: string | null;
}

export type QlisanLevelKey = "sawti" | "sarfi" | "nahwi" | "dalali";

export interface QlisanWordResponse {
  ref: string; // "surah:ayah:word"
  surah: number;
  ayah: number;
  word: number;
  word_uthmani: string;
  word_imlaai: string;
  levels_order: QlisanLevelKey[];
  sawti: QlisanStubLevel;
  sarfi: QlisanSarfi;
  nahwi: QlisanNahwi;
  dalali: QlisanStubLevel;
}

export interface FeedbackStats {
  up: number;
  down: number;
  total: number;
}
