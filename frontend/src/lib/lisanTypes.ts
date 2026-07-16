// Types for the Lisan Analysis (letter-symbolism) endpoint (POST /lisan/analyze).
// Kept in a dedicated file so the shared lib/types.ts stays untouched.

export interface LisanLetter {
  letter: string;
  name: string;
  makhraj: string;
  sifat: string[];
  meaning: string;
  keywords: string[];
  ibn_jinni_note: string;
  confidence: string; // "verified" | "high" | "summary" | "unknown"
}

export interface SequentialItem {
  index: number;
  letter: string;
  meaning: string;
}

export interface IshtiqaqItem {
  form: string;
  gloss: string;
}

export interface LisanResponse {
  word: string;
  root: string | null;
  root_source: string | null; // "qac" | "fallback" | null
  letters: LisanLetter[];
  sequential_reading: SequentialItem[];
  synthesis: string;
  synthesis_source: string; // "template" — synthesis is deterministic, not LLM
  ishtiqaq_akbar: IshtiqaqItem[];
  disclaimer: string;
  sources: Record<string, string>;
  message: string | null;
}
