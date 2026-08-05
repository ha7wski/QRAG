// ── Tahlil (per-word five-block analysis: الحروف → صرفي → نحوي → دلالي → تركيب) ──
//
// Mirrors `api/models/tahlil.py`. Two things here are contract rather than convenience,
// and both exist because the badges bound **provenance, never truth**:
//
//  1. `badge`, `badgeLabels` and `badgeTooltips` are carried BY THE PAYLOAD. This module
//     deliberately declares no map of Arabic badge strings: a copy here could drift from
//     the module that assigns the badge, and it would drift in the one direction that
//     matters — a stale tooltip reading «verified» over a generated claim is exactly the
//     misreading the badges exist to prevent.
//  2. `cites`/`sources` sit on the CLAIM, not on the block. A block-level citation list
//     would let one anchored sentence lend its provenance to an unanchored neighbour.

/** A provenance badge as the gate assigns it: «محقّق» | «مُولَّد» | «تأويلي». */
export type TahlilBadge = string;

export interface TahlilClaim {
  text_ar: string;
  /** The LICENSED badge — never the one a generator asked for. */
  badge: TahlilBadge;
  /** Machine-readable evidence ids: `letter:…`, `nazir:…`, `sigha:…`, `maqayis:…`, `qac:…`. */
  cites: string[];
  /** Human-readable citation-strip lines (author + page, KB row id + version, treebank). */
  sources: string[];
}

export interface TahlilAttribution {
  source: {
    author: string;
    title: string;
    publisher?: string;
    year?: string;
    scope?: string;
  };
  /** The framework disclaimer, in Arabic, owned by the module that owns the dataset. */
  disclaimer: string;
}

export interface TahlilBlock {
  id: string;
  title_ar: string;
  /** `false` is a first-class outcome, not an error — `message` then says why, in Arabic. */
  available: boolean;
  message?: string | null;
  claims: TahlilClaim[];
  /** Present on الحروف: a corpus fact and a contested framework share that card, and the
   *  disclaimer is what stops the first from lending its authority to the second. */
  attribution?: TahlilAttribution | null;
}

export type TahlilBlockKey = "huruf" | "sarfi" | "nahwi" | "dalali" | "tarkib";

export interface TahlilWordResponse {
  ref: string;
  surah: number;
  ayah: number;
  word: number;
  /** From the chakl corpus — never the QAC `uthmani` field. */
  word_vocalized: string;
  /** Presentation contract: the API owns the order, the page never re-sorts. */
  blocks_order: string[];
  blocks: Record<string, TahlilBlock>;
  reviewed: boolean;
  generation_enabled: boolean;
  /** badge → the label to print. Served, not hardcoded — see the note above. */
  badge_labels: Record<string, string>;
  /** badge → the tooltip to print. Served, not hardcoded. */
  badge_tooltips: Record<string, string>;
  /** The mention that rides on every un-reviewed generated block: «غير مُحقَّق». */
  unverified_mention: string;
  /** The closed badge set in CAUTION order: محقّق → مُولَّد → تأويلي. A card summarising a
   *  mixed block announces the weakest provenance it contains, so «weakest» is the highest
   *  index present — read off the payload, never guessed from object key order. */
  badges: string[];
}

export interface TahlilReviewResponse {
  ref: string;
  reviewed: boolean;
  reviewer: string;
  note: string;
  reviewed_at: number | null;
}
