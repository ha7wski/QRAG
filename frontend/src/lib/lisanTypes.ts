// Types for the Lisan Analysis (letter-symbolism) endpoint (POST /lisan/analyze).
// Kept in a dedicated file so the shared lib/types.ts stays untouched.
//
// This mirrors `api/models/lisan.py` field for field. The response publishes the
// CONSTRAINT, not just the conclusion: a letter holds a BUNDLE of sourced senses,
// which member applies depends on the root's attested aṣl, so the payload carries
// the core it was built from, the axes each selected sense shared with it, and
// every sense it dropped with the reason.
//
// GONE, and deliberately not replaced: `sequential_reading` and the single
// `letters[].meaning` / `letters[].keywords`. Concatenating one frozen gloss per
// letter is what made خ-ي-ر read «القذارة والخشونة والخواء» against Ibn Fāris'
// «أصله العطف والميل» — there must be no type here that lets that be rebuilt.
//
// Closed backend enums are string-literal unions rather than `string`: that is what
// turns an unhandled case in the UI into a compile error instead of a blank badge.

/** A semantic charge, of an aṣl (`RootCore.polarity`) or of a sense (`LetterSense.pole`).
 *  `neutral` is a real verdict, not a missing one — ك-ف-ر's «الستر والتغطية» is
 *  descriptive, and its negative charge is usage, not the cited aṣl. */
export type Polarity = "positive" | "negative" | "neutral";

/** Where in a root a sense applies. `any` = position-independent. */
export type SensePosition = "initial" | "medial" | "final" | "any";

/** Where a letter actually sits in THIS root. Never `any` — a letter has a place. */
export type LetterPosition = "initial" | "medial" | "final";

/** Why a sense won, or that nothing did. */
export type SelectionRule = "axis-match" | "axis-match+position" | "unmatched";

/** The rules that actually SELECT something. A letter whose rule is `unmatched`
 *  renders the stated gap instead of a rule, so the label table is keyed on this
 *  narrower type — a label for `unmatched` would be a string nothing can reach. */
export type MatchedRule = Exclude<SelectionRule, "unmatched">;

/** Why a sense lost. `outranked` was eligible; the other two never were. */
export type DiscardReason = "no-shared-axis" | "conflicting-axis" | "outranked";

/** How well sourced a sense is. Ranks verified > high > summary in the backend. */
export type Confidence = "verified" | "high" | "summary";

/** One aṣl of the root, as Ibn Fāris states it. `verbatim` is his own words,
 *  byte-identical to the shipped Maqāyīs segment; `gloss`, `axes` and `polarity`
 *  are curated beside it, never instead of it. */
export interface RootCore {
  gloss: string;
  verbatim: string;
  axes: string[];
  polarity: Polarity;
  source: string;
  edition: string;
}

/** One member of a letter's sense bundle, with the citation that admits it. */
export interface LetterSense {
  sense_id: string;
  gloss_ar: string;
  pole: Polarity;
  axes: string[];
  position: SensePosition;
  gesture_ar: string;
  source: string;
  page: string;
  confidence: Confidence;
}

/** A root letter's phonetics — stable across every core, so it is published once
 *  at the top level rather than repeated inside each reading.
 *
 *  It carries NO gloss, and the backend no longer sends one. The dataset's Ibn
 *  Jinnī sound-imitation note was the last one: for خ it reads «يوحي بالأشياء
 *  الخشنة الكريهة الجوفاء» — the same reading this change exists to keep off
 *  خ-ي-ر, in inflected form, which a substring guard on «خشونة»/«خواء» would
 *  never have caught. Meaning belongs to a reading, and a reading to a core. */
export interface LetterIdentity {
  index: number; // 1-based position in the root
  letter: string;
  name: string;
  makhraj: string;
  sifat: string[];
  position: LetterPosition;
  sense_count: number;
}

/** A sense the core did not admit, kept visible with why it was dropped. */
export interface DiscardedSense {
  sense: LetterSense;
  reason: DiscardReason;
}

/** What ONE core made of ONE letter. `selected` is null when nothing was eligible —
 *  the gap is shown, never filled with the letter's first or most-confident sense. */
export interface LetterReading {
  index: number;
  letter: string;
  selected: LetterSense | null;
  matched_axes: string[];
  selection_rule: SelectionRule;
  discarded: DiscardedSense[];
}

/** The reading's aggregate pole contradicts its own core's polarity. A DETECTOR:
 *  it reports and changes nothing, so the UI renders it as a finding, never as an
 *  error and never as something the tool corrected. */
export interface Divergence {
  core_polarity: Polarity;
  reading_polarity: Polarity;
  letters: string[];
  message: string; // Arabic, shown as its own banner
}

/** One complete reading, built from ONE core. Never a blend: a root with two aṣl
 *  gets two readings, and their axes are never pooled. */
export interface Reading {
  core: RootCore;
  letters: LetterReading[];
  synthesis: string;
  divergence: Divergence | null;
}

/** The unconstrained path: a letter's whole bundle, nothing selected. */
export interface LetterInventory {
  index: number;
  letter: string;
  senses: LetterSense[];
}

export interface IshtiqaqItem {
  form: string;
  gloss: string;
}

/**
 * `constrained` is the fork.
 *
 * true  → `readings` holds one entry per core, each with its own selections and
 *         its own synthesis; `inventory` is empty.
 * false → `readings` is empty, `warning` says why in Arabic, and `inventory` lists
 *         the letters' senses with none selected. There is no synthesis on that
 *         path and no setting that restores one.
 */
export interface LisanResponse {
  word: string;
  root: string | null;
  /** Closed, like every other backend enum here: the page compares against
   *  `"fallback"` to decide the جذر تقديري badge, and a typo in that comparison
   *  has to be a compile error rather than a badge that silently never shows. */
  root_source: "qac" | "fallback" | null;
  constrained: boolean;
  letters: LetterIdentity[];
  cores: RootCore[];
  readings: Reading[];
  inventory: LetterInventory[];
  /** axis id → Arabic label, for every axis named anywhere in the response. The UI
   *  renders axis NAMES from this map and holds no copy of the vocabulary. */
  axis_labels: Record<string, string>;
  warning: string | null; // set when `constrained` is false
  synthesis_source: string; // "template" — every synthesis is deterministic, not LLM
  ishtiqaq_akbar: IshtiqaqItem[];
  disclaimer: string;
  sources: Record<string, string>;
  message: string | null; // set when the root could not be resolved
}
