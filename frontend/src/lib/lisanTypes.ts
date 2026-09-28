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

/**
 * What a stated position claims. `exclusive` («only there») is the only one that
 * makes a sense ineligible; `dominant` — a proportion or a comparison, which is
 * what Ḥasan ʿAbbās almost always gives — ranks and never excludes.
 */
export type PositionKind = "exclusive" | "dominant";

/** Where a letter actually sits in THIS root. Never `any` — a letter has a place. */
export type LetterPosition = "initial" | "medial" | "final";

/** Why a sense won, or that nothing did. */
export type SelectionRule = "axis-match" | "axis-match+position" | "unmatched";

/** The rules that actually SELECT something. A letter whose rule is `unmatched`
 *  renders the stated gap instead of a rule, so the label table is keyed on this
 *  narrower type — a label for `unmatched` would be a string nothing can reach. */
export type MatchedRule = Exclude<SelectionRule, "unmatched">;

/** Why a sense lost. `outranked` was eligible; the other two never were. */
export type DiscardReason =
  | "no-shared-axis"
  | "conflicting-axis"
  /** The authority scopes this sense to another place in the word. */
  | "wrong-position"
  | "outranked";

/** How well sourced a sense is. Ranks verified > high > summary in the backend. */
export type Confidence = "verified" | "high" | "summary";

/**
 * Why a root has no core. Two of the three are OUR gap; only `no_asl_in_source`
 * reports Ibn Fāris' own silence, and the backend sets it only where the dataset
 * positively records that his entry formulates no aṣl. Absence of a row is
 * absence of evidence, so it maps to `not_recorded`, never to his silence.
 */
export type CoreStatus = "not_curated" | "not_recorded" | "no_asl_in_source";

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
  /** A SET: «في الآخر والوسط» is one statement over two positions. */
  position: SensePosition[];
  /** What that position claims. `""` when `position` is `["any"]`. */
  position_kind: PositionKind | "";
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
  /** Senses the authority scopes elsewhere in the word — kept visible, not
   *  dropped, the way `discarded` is on the constrained path. */
  out_of_position: LetterSense[];
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
  /** The ATTESTED layer, published before anything composed from it.
   *
   *  `occurrences` counts the ĀYĀT the root occurs in, `occurrence_words` the
   *  WORDS (رحم: 339 words in 313 āyāt — neither is derivable from the other),
   *  `occurrence_verses` is the exhaustive `"s:a"` list, and `forms` the distinct
   *  ألفاظ — written forms, proclitics stripped, grammatical-tool occurrences
   *  excluded. All four are «الكلمة في الآيات»'s own figures, produced by the one
   *  backend computation both pages read (`VerseLookup.root_forms`); `forms` used
   *  to be `morphology.json`'s vocalized surfaces and listed رَحْمَةً / رَحْمَةٍ / رَحْمَةُ
   *  as three of 43 against that page's 31. The page prints the figures and a
   *  short sample and sends the reader to «دراسة الآية» for the vocalized display
   *  with highlighting — that page's job, not this one's.
   *
   *  They are required, not optional: these facts used to reach the screen only
   *  through the concept engine's confrontation block, which made an attested
   *  datum depend on an experimental route staying up. */
  occurrences: number;
  occurrence_words: number;
  occurrence_verses: string[];
  forms: string[];
  constrained: boolean;
  letters: LetterIdentity[];
  cores: RootCore[];
  readings: Reading[];
  inventory: LetterInventory[];
  /** axis id → Arabic label, for every axis named anywhere in the response. The UI
   *  renders axis NAMES from this map and holds no copy of the vocabulary. */
  axis_labels: Record<string, string>;
  core_status: CoreStatus | null; // set with `warning`, null on every other path
  warning: string | null; // set when `constrained` is false
  synthesis_source: string; // "template" — every synthesis is deterministic, not LLM
  ishtiqaq_akbar: IshtiqaqItem[];
  disclaimer: string;
  sources: Record<string, string>;
  message: string | null; // set when the root could not be resolved
}

/* ── the physics-first engine (POST /lisan/concept) ────────────────────────
 *
 * A SECOND engine, mirroring `api/models/lisan.py`'s lower half field for field.
 * Everything above is CORE-FIRST — the attested aṣl selects among each letter's
 * sourced senses. Everything below is the inverse: the مفهوم is composed from the
 * tajwīd description of the root's letters and from nothing else, and Ibn Fāris
 * arrives afterwards as the TEST. The two are published side by side until the
 * comparison is done, so nothing here is typed as a fallback for anything there.
 *
 * The shapes are flatter than the core-first ones on purpose: there is nothing to
 * select, so there is no `discarded`, no `matched_axes` and no `selection_rule`.
 */

/** The sourcing regime of one primitive, and the page MUST distinguish on it.
 *  `attested` — a named authority with real pages states this mapping.
 *  `hypothesis` — the project asserts it, carrying an uncontested tajwīd fact as
 *  its basis. Most rows are hypotheses, and a screen that rendered both alike
 *  would publish the project's construction with Ibn Jinnī's face on. */
export type PrimitiveStatus = "attested" | "hypothesis";

/** The positional rule, fixed in advance and never adapted to a root: the first
 *  radical opens the action, the second is its body, the third concludes it. The
 *  API sends these English keys and the Arabic wording belongs to the page — the
 *  same division of labour `LetterIdentity.position` already follows. */
export type ConceptPosition = "opens" | "body" | "concludes";

/** Whether the مفهوم covers one attested Quranic sense. `not_judged` is the
 *  mandated intermediate state — uses frozen, verdict not yet written — and not a
 *  third grade between the other two. */
export type UseVerdict = "covered" | "not_covered" | "not_judged";

/** The root-level coverage verdict. It is a COVERAGE VERDICT, so no surface may
 *  print it without `ConceptResponse.metric_reservation` beside it. */
export type ConfrontationVerdict = "covers_all" | "partial" | "not_recorded";

/** Where the concept's sentence came from. The deterministic template is the
 *  ground truth; `phrasing` is the optional LLM pass, off by default and vetoed
 *  by a containment check before it can reach this field. */
export type SentenceSource = "template" | "phrasing";

/** One primitive a letter carries, with the table row that licensed it.
 *
 *  `coverage` is how many of the 28 letters carry this primitive and is the
 *  ordering signal — rarest first; `declaration_index` is the table's own row
 *  order and breaks every tie. Both travel with every hit so a reader can
 *  re-derive the order by hand, which is why the page prints them rather than
 *  presenting the cut as a given. */
export interface PrimitiveHit {
  primitive: string;
  feature: string;
  gloss_ar: string;
  status: PrimitiveStatus;
  coverage: number;
  declaration_index: number;
}

/** One radical read at one fixed slot, with its whole evidence chain.
 *
 *  `letter` is the glyph as the root key spells it and is never rewritten;
 *  `sheet_letter` is the row it was read from, which differs for a hamza seat
 *  (`أ` → `ء`) and is null when the sheet has no row at all.
 *
 *  `ordered` is everything the letter carries, `realised` its first three,
 *  `carried` the remainder. `carried` is PUBLISHED, never hidden: the cut is a
 *  display budget, not a claim that the rest are absent. */
export interface PositionReading {
  position: ConceptPosition;
  letter: string;
  sheet_letter: string | null;
  makhraj_ar: string;
  features: string[];
  ordered: PrimitiveHit[];
  realised: PrimitiveHit[];
  carried: PrimitiveHit[];
  silent: boolean;
  silent_reason: string; // Arabic; says WHOSE gap it is
}

/** A root's composed مفهوم, or a stated refusal to compose one.
 *
 *  `refused` and `partial` are different failures and the page must not merge
 *  them. `refused` — the rule does not cover this root at all (a quadriliteral),
 *  `positions` is empty and `refusal_reason` carries the Arabic statement.
 *  `partial` — the rule applied and one position is silent; the concept exists
 *  and is honestly short by that position.
 *
 *  `sentence` is the ground truth and the thing the metric is measured on. The
 *  page may GROUP `realised` by position for readability, and grouping is all it
 *  may do: the chain is shown verbatim beside the groups, never instead of them. */
export interface Concept {
  root: string;
  refused: boolean;
  refusal_code: string;
  refusal_reason: string;
  positions: PositionReading[];
  realised_primitives: string[];
  sentence: string;
  sentence_source: SentenceSource;
  /** Non-empty in exactly one case: a phrasing was produced and the containment
   *  veto refused it. «the model invented something» and «the model was not
   *  running» must not look the same, so this is empty when the pass is off. */
  phrasing_rejection: string;
  partial: boolean;
  silent_letters: string[];
  lock_version: string; // the table version this concept was produced under
}

/** One Quranic sense frozen for a root BEFORE its concept was generated.
 *  `reason` is required on anything not `covered`, and it is the only thing that
 *  lets a reader who disagrees redo the judgement. */
export interface AttestedUse {
  gloss: string;
  verse: string; // "s:a"
  verdict: UseVerdict;
  reason: string;
}

/** What is attested for the root, set beside the concept — a report only.
 *
 *  The aṣl arrives AFTER the answer, which is the whole reason the engine exists:
 *  the two can disagree, and nothing here feeds back into the concept.
 *
 *  `core_status` says whose silence it is when `cores` is empty, and is `""` when
 *  cores exist. `counts_toward_k` is a published exclusion, never a silence: a
 *  root off the holdout is confronted and shown like any other. */
export interface Confrontation {
  cores: RootCore[];
  core_status: CoreStatus | "";
  occurrences: number;
  verses: string[];
  uses: AttestedUse[];
  verdict: ConfrontationVerdict;
  uses_frozen_at: string;
  concept_recorded_at: string;
  in_witness_set: boolean;
  counts_toward_k: boolean;
}

/** `root: null` with a `message` when nothing resolves — never a 500.
 *
 *  `concept` and `confrontation` are both null on that path and both present
 *  otherwise, INCLUDING when the concept is refused: a refusal is an answer the
 *  page displays, not an empty panel. */
export interface ConceptResponse {
  word: string;
  root: string | null;
  root_source: "qac" | "fallback" | null;
  concept: Concept | null;
  confrontation: Confrontation | null;
  /** The window reservation, carried in the response rather than left to the
   *  page: any surface that prints a coverage verdict must print it WITH the
   *  number, and `Confrontation.verdict` is one. */
  metric_reservation: string;
  disclaimer: string;
  message: string | null;
}
