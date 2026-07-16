/**
 * Strict TypeScript mirror of the backend `POST /madar/analyze` contract
 * (`api/models/madar.py`). The response keeps three epistemic layers apart:
 *   - `maqayis`         → CITED (Ibn Fāris' aṣl, with source + edition),
 *   - `occurrences`     → PROOF (the root's Quranic occurrences),
 *   - `madar_synthesis` → GENERATED (optional LLM pivot, flagged + disclaimed).
 * The UI must never blur these; the field split enforces it.
 */

/** Ibn Fāris' aṣl — a verified citation, never a paraphrase. */
export interface MaqayisCitation {
  /** [] when asl_status === "no_asl". Exposed as a list (multi-aṣl ready), but
   *  the store currently emits at most one combined entry — do NOT assume
   *  `asl_text.length === asl_count`. */
  asl_text: string[];
  asl_count: number;
  asl_status: "has_asl" | "no_asl" | "parse_uncertain";
  source: string;
  edition: string;
}

/** One Quranic occurrence of the root (surah/ayah may be null). */
export interface Occurrence {
  surface: string;
  surah: number | null;
  ayah: number | null;
  /** The verse text — short grounding context. */
  context: string;
}

export interface MadarResponse {
  word: string;
  root: string | null;
  root_source: string | null; // "qac" | "fallback" | null
  maqayis: MaqayisCitation | null; // CITED
  occurrences: Occurrence[]; // PROOF (sample)
  occurrences_count: number; // true total
  verse_ids: string[]; // all refs "s:a" (proof)
  madar_synthesis: string | null; // GENERATED (or null — the default)
  synthesis_source: string;
  synthesis_disclaimer: string;
  convergence_note: string | null; // optional lisan bridge
  /** Status line (root present) or "root not found" help (root null). Never an
   *  error when `root` is present; mutually exclusive with `madar_synthesis`. */
  message: string | null;
}
