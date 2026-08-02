## Context

QRAG today operates at the **verse** granularity: Qdrant points (`quran_verses`,
one 1024-dim E5 vector per verse), BM25 docs, RRF fusion, and every API `Verse`
model are verse-scoped. QLisan needs the opposite granularity — given one word at
`surah:ayah:word`, return a four-level fiche (صوتي → صرفي → نحوي → دلالي), three
levels deterministic and one sourced.

A design review against the actual repository (three adversarial passes, each run
against the real files/code) reshaped the original plan:

- **The gold data is already on disk.** `data/raw/eqtb/quranic-treebank.csv` (33 MB)
  is one QAC-derived source keyed `chapter:verse:word:token` that supplies **both**
  morphology (`root_ar`, `lemma_ar`, `pos`, `features`, case/mood/pgn, prefix/suffix)
  **and** the dependency treebank (`rel_label`, head reference, constituents) from
  the same rows — so صرفي and نحوي share keys by construction. `RelLabels.csv` is the
  relation dictionary. Ibn Fāris's *Maqāyīs* is already parsed by Madār
  (`scripts/build_maqayis_dataset.py` → `data/references/maqayis_asl.csv`, read by
  `madar/maqayis_store.py`). The socle needs **no new acquisition**.
- **There are only two tokenizations, not three.** The treebank and the legacy
  `data/raw/quran-morphology.txt` are byte-identical segmentations (verified: 0
  mismatches across 6236 verses). The real reconciliation is QAC-canonical vs the
  displayed vocalized rasm (`quran_chakl.csv`), which mismatches on ~46% of verses
  — but **strictly additively** (the display only ever over-segments; 0 verses where
  it has fewer tokens). So alignment is merge-only.
- **The local 7B is a proven-unreliable synthesizer.** Madār already keeps LLM
  synthesis off by default, and the same lexicons are root-organized (a key lookup,
  not a similarity search). So generative دلالī is the wrong default.

**Stakeholder decisions carried into this design:** distribution is **private /
local only** (licensing becomes provenance hygiene, not a compliance project); the
دلالī MVP is **extractive-first** (verbatim cited lexicon via root-key lookup, no LLM).

Conventions reused verbatim: backend `api/routers/<f>.py` + `api/models/<f>.py` +
lazy `_service(request)` (lisan/madar) + `verse_from_record` + `chakl_by_ref()`;
Madār's `MaqayisStore` root-key lookup and its CITED/PROOF/GENERATED separation
model; frontend filesystem route + `Navbar.tsx` links array + verse-study
keep-mounted tabs + `HighlightedVerse` token split + `ArabicText` + `lib/api.ts`.

## Goals / Non-Goals

**Goals:**
- A per-word fiche with four ordered, independently-labelled levels.
- صرفي and نحوي served 100% deterministically from the on-disk treebank (no LLM).
- A token-alignment spine built **first**, since every level keys off it.
- صوتي computed from vocalized rasm by explicit rules, with school-attributed
  articulation tables and verse-level handling of cross-word tajwīd.
- دلالي extractive-first: verbatim cited lexicon entries via root-key lookup, no
  LLM; unavailable rather than fabricated when a root has no entry.
- Strict, visible separation of deterministic fact vs sourced material; no LLM
  fallback anywhere on the deterministic path.
- An MVP shipped in increments; each increment independently useful.
- Zero behavioural change to existing chat/search over `quran_verses`.

**Non-Goals:**
- Re-embedding the Quran at word granularity for dense retrieval.
- Any new Qdrant collection in the MVP (extractive دلالī is a keyed lookup).
- Generative دلالī synthesis in the MVP (deferred, off by default).
- Modifying `HybridSearch`, `QueryProcessor`, HyDE, reranker, or the chat pipeline.
- Cross-verse syntactic parsing or re-deriving iʿrāb — نحوي is served from the treebank as-is.
- Audio synthesis/recitation for صوتي (text description only).

## Decisions

### D1 — Per-word index as a keyed data artifact, sourced from the on-disk treebank
Parse `data/raw/eqtb/quranic-treebank.csv` into `data/processed/qac_words.json`
(`"surah:ayah:word"` → `{form, segments[], root, lemma, pos, features{}}`) and
`qac_syntax.json` (`{role, head_position, relation, dependents[]}`), plus
`root_graph.json` (root → derived forms → occurrence positions). Loaded via an
`@lru_cache` loader in the `indexing/corpus.py` style. **Why:** exact position
lookup, not similarity — a dict is O(1), deterministic, offline, testable; and one
source for morphology+syntax removes any cross-source key drift. Cross-check a
sample against the legacy `morphology.json` (mustafa0x) and CAMeL; the treebank is
source of truth. **Alternative rejected:** a per-word vector collection (pure cost,
no benefit for an exact key lookup, 6× the point count).

### D2 — Token-alignment spine, built first, as the hard core (was under-scoped)
`data/processed/word_index.json`: `"surah:ayah:word"` → `{uthmani, imlaai,
chakl_char_span, tok_ids[], drop_reason?}`. QAC `word_id` is canonical; the
displayed rasm is aligned onto it, merge-only (`chakl-token → word_id | DROP`).
Rule cascade: strip mark-only tokens (waqf U+06D6–U+06DC, sajda U+06E9, hizb
U+06DE) → strip prepended basmala on the 112 verse-1s → merge bare vocative يَا →
hand-curated `overrides.json` (~15–30 residual verses). Count words as
`max(word_id) WHERE location != '_'` (exclude 4484 `(*)` elided heads + 6673
parenthesized pro-drop pronouns at `word_id=0`). **Concatenate treebank segments
per `word_id`** before span-matching (segment ≠ word). Build a normalized copy
(fold ٱ U+0671 / superscript alif U+0670 → ا U+0627, strip tashkīl) **with an index
map back to raw offsets**. Gate = "every displayed content-token maps + every QAC
word covered," NOT equal counts; emit an audit report. **Why first:** this is ~80%
of QLisan's risk, and every downstream level mis-keys if it is wrong.
**Alternative rejected:** naïve whitespace tokenization of the display verse — mis-
selects words on 46% of verses and silently mis-highlights ornate ones.

### D3 — One `/qlisan/word` endpoint returning a four-level fiche with per-level availability
`POST /qlisan/word {surah, ayah, word}` → `QlisanResponse{sawti, sarfi, nahwi,
dalali}`, each level `{available: bool, ...}` (mirrors Madār's field-per-layer
shape). Deterministic levels assembled synchronously from the indexes; `dalali`
from the extractive store or `{available:false, message}`. A companion path
supplies the selectable verse with **QAC-aligned token boundaries** (from
`word_index.json`) so UI token index == QAC word index by construction.
**Alternative rejected:** four endpoints (more round trips; client re-stitches order).

### D4 — دلالی is extractive-first via root-key lookup; RAG is deferred
Baseline دلالی = a deterministic root→entry lookup returning **verbatim** lexicon
text, reusing the `MaqayisStore` pattern (`normalize_root` key + geminate fallback,
offline). Extend `scripts/build_maqayis_dataset.py` from aṣl-only to full-entry
chunks; add a parallel Mufradāt store (public-domain-provenance text). The citation
**is** the source text. **No LLM, no Qdrant collection in the MVP.** A generative
layer over a dedicated `qlisan_lexicon` collection is deferred, off by default.
**Why:** the lexicons are root-organized (a key lookup is exact); Madār already
proved generation here is unreliable; extractive honors "citations mandatory,
uncited rejected" by construction. **Alternative rejected:** RAG-generate the MVP —
inverts the project's own hard-won lesson and re-indexes root-keyed data into a
lossy similarity search.

### D5 — If generation is later added, ground per-claim by entailment, not id-membership
An id-membership gate (drop claims whose cited id ∉ retrieved set) is orthogonal to
faithfulness: it passes a real id attached to a misrepresentation, and true-but-
parametric claims wearing a plausible citation. The deferred generative layer SHALL
instead verify each claim by entailment against a retrieved passage **plus** a
verbatim supporting span; failing claims are dropped; if none survive, the
extractive view remains shown. **Why:** converts "cited" into "actually supported."

### D6 — Phonetic engine: deterministic, attributed, verse-aware
`analysis/phonetics.py` + `analysis/tajwid.py`: G2P + syllabation from the vocalized
rasm (NOT the treebank `phonetic` column — ~44% empty, Latin romanization, verse-
position-baked). makhārij/ṣifāt from a static table **attributed to a named school**
(they differ: 17 vs 16 vs 14 makhārij). Tajwīd from the CC-BY **data** of
`quran-tajweed` with its rule logic reimplemented (its code is unlicensed);
cross-word rules (idghām/iqlāb/sun-letter lām) computed at verse level and anchored
to the selected word. **Why last in the MVP:** independent of QAC/lexicons, so it
slots in after the socle without blocking it.

### D7 — MVP increments
0. Alignment spine (`word_index.json` + overrides + offset map). 1.
`qac-morphosyntax-index` + `qlisan-word-analysis` (صرفي + نحوي + page/word-select).
2. `phonetic-analysis` (صوتي). 3. `dalali-rag` extractive (دلالی lookup). Each ships
a usable fiche with later levels marked `available:false`.

## Risks / Trade-offs

- **Silent char-span offset drift (the biggest under-estimated hazard)** — ٱ/
  superscript-alif vs plain ا, and segment≠word, make byte offsets into the tashkīl
  string drift, mis-highlighting exactly the ornate verses users inspect → Normalize
  with an index map back to raw offsets (D2); spot-check highlighting in-browser on
  2:2 (with ۛ), a basmala-prefixed verse-1, and 2:255.
- **~46% chakl/QAC token mismatch** → Merge-only alignment + rule cascade +
  `overrides.json`; gate on coverage, not equal counts (D2). It is tractable because
  the mismatch is strictly additive.
- **Local 7B unreliability** → Extractive-first دلالی (D4); no LLM on the
  deterministic path; generation deferred and entailment-gated (D5).
- **Treebank pseudo-tokens inflate word counts** → count `max(word_id) WHERE
  location != '_'`; never count rows.
- **Presenting one makhārij table as universal fact is itself a hidden
  interpretation** → attribute to a school (D6).
- **Cross-word tajwīd doesn't fit a per-word fiche** → compute at verse level,
  anchor to the word (D6).
- **Licensing (private/local posture)** → No conveyance ⇒ no GPL/CC obligations
  now. Cheap hygiene only: use `quran-tajweed` data not code; record sources +
  licenses in `data/SOURCES.md`; avoid ingesting any NC source (OpenITI MAKHZAN,
  NC QUL resources) so a future open/commercial pivot stays cheap; confirm the
  `quran.csv`/`quran_chakl.csv` provenance (Tanzil is CC-BY-3.0, not NC — but the
  origin is unconfirmed).
- **Scope creep into a full grammar engine** → نحوي served from the treebank as-is.

## Migration Plan

Additive only — no migration of existing data or routes.
1. New ingestion stage writes `word_index.json` (+ `overrides.json`),
   `qac_words.json`, `qac_syntax.json`, `root_graph.json`; run alongside the
   existing pipeline (existing root-level artifacts unchanged).
2. Increment 1: deterministic assembler + `api/models/qlisan.py` +
   `api/routers/qlisan.py` (lazy `_service`) + `src/app/qlisan/page.tsx` + Navbar
   link + `lib/api.ts` wrappers. صرفي/نحوی live; صوتي/دلالی `available:false`.
3. Increment 2: `analysis/phonetics.py` + `analysis/tajwid.py`; flip صوتي on.
4. Increment 3: extractive دلالی store (extend Maqāyīs, add Mufradāt); flip دلالی on.
Rollback: remove the Navbar link and/or the `include_router` line; no data
migration to undo (all new artifacts are independent of `quran_verses`).

## Open Questions

- What is the exact provenance/license of `quran.csv` / `quran_chakl.csv` (Tanzil
  CC-BY-3.0, or a stricter King-Fahd/QUL Uthmani script)? Needed before any pivot.
- Which public-domain-provenance edition of *Mufradāt* al-Rāghib to ingest (avoid
  NC/share-alike digital editions), and at what chunk granularity (per-root entry)?
- Which recitation school/authority should the makhārij/ṣifāt tables follow by
  default (and should the UI let the user switch)?
- Reuse `GET /verse/{surah}/{ayah}` for the selectable verse, or add a QLisan verse
  endpoint that returns QAC-aligned token boundaries from `word_index.json`?
