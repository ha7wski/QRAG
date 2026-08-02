## Why

QRAG lets users retrieve and study verses, but it cannot yet explain a single
word the way a lisānī (Arabic linguistic) analysis does: sound, form, syntax,
and meaning as four ordered, disciplined layers. Today "Lisan Analysis" gives an
LLM-written root reading with no deterministic morpho-syntactic ground truth and
no per-word treebank. We want a study surface where a user clicks a word inside a
verse and gets a rigorous fiche across the four levels — with the deterministic
facts (form/syntax) provably separated from any generated interpretation.

A design review against the actual repository sharpened this: the required gold
data is **already on disk** (`data/raw/eqtb/quranic-treebank.csv` carries per-word
root, lemma, POS, full features **and** the dependency treebank; Ibn Fāris's
*Maqāyīs* is already parsed by the Madār feature), and the project has already
learned that its local 7B model is an unreliable synthesizer (Madār keeps LLM
synthesis off by default). So QLisan's effort concentrates on token alignment,
phonetic rules, and an **extractive** semantic layer — not on re-acquiring data or
trusting generation.

## What Changes

- Add a new **QLisan** page/tab: the user picks a verse, selects one word, and
  receives a per-word fiche organized into four ordered levels — **صوتي**
  (phonetic) → **صرفي** (morphological) → **نحوي** (syntactic) → **دلالي**
  (semantic).
- Add a **token-alignment spine** as the foundational step: reconcile the QAC
  per-word keys (canonical, `surah:ayah:word`) onto the displayed vocalized rasm
  **before** any level is built, since every level keys off it. This is a
  merge-only alignment (the display text only ever over-segments) with a small
  hand-curated override set and a character-span map for reliable highlighting.
- Add a **per-word deterministic index** keyed `surah:ayah:word`, parsed from the
  already-present `data/raw/eqtb/quranic-treebank.csv` — a single source that
  supplies **both** morphology (root, lemma, POS, features) and the **dependency
  treebank** (iʿrāb relations) from the same rows, so صرفي and نحوي share identical
  keys by construction. The صرفي and نحوي levels are served **entirely from this
  index — no LLM**.
- Add a **phonetic engine** producing G2P transcription, per-letter makhārij/ṣifāt
  (explicitly attributed to a recitation school, not presented as unmarked fact),
  applicable tajwīd rules (from the CC-BY-licensed **data** of `quran-tajweed`, its
  rule logic reimplemented — its code is unlicensed), and syllabation — all
  computed deterministically from the vocalized text. Cross-word tajwīd rules are
  reported at verse level, anchored to the selected word.
- Add an **extractive دلالī (semantic) layer**: a deterministic root→entry lookup
  returning **verbatim** classical-lexicon entries (al-Rāghib's *Mufradāt*, Ibn
  Fāris's *Maqāyīs al-Lugha*), where the citation **is** the source text. No LLM in
  the MVP. Any word whose root has no lexicon entry returns the level as
  unavailable, never fabricated. Generative RAG synthesis is **explicitly
  deferred** to a later, off-by-default increment, and if built must use per-claim
  entailment + verbatim-span grounding, not a citation-id membership check.
- Add a **root graph**: root ↔ derivatives ↔ occurrences (naẓāʾir), derived
  trivially from the per-word index, so a fiche links out to sibling words sharing
  the root across the corpus.
- Add new backend endpoint(s) for per-word analysis and a new frontend route/tab
  wired into the existing sidebar navigation.
- **Non-goal:** replacing or changing the existing chat/retrieval behaviour. The
  existing hybrid retriever, reranker, and Qwen generation are **reused** only if
  and when generative دلالī is built later; the MVP does not touch them. QLisan
  stays decoupled from the RAG chat path.

## Capabilities

### New Capabilities

- `qlisan-word-analysis`: the QLisan page/tab and per-word analysis endpoint —
  word selection within a verse, the four-level fiche model, and the load-bearing
  invariant that deterministic levels (صرفي/نحوي/صوتي) and the sourced-extractive
  دلالي level are produced and labelled separately, with no LLM on the
  deterministic path.
- `qac-morphosyntax-index`: the **token-alignment spine** (reconciling QAC word
  keys onto the displayed rasm) plus ingestion of the QAC morphology + dependency
  treebank from `data/raw/eqtb/quranic-treebank.csv` into a per-word index keyed
  `surah:ayah:word`, plus the root↔derivatives↔occurrences (naẓāʾir) graph; the
  deterministic data source for the صرفي and نحوي levels.
- `phonetic-analysis`: the صوتي engine — G2P, school-attributed makhārij/ṣifāt,
  tajwīd rules (word-level and verse-level cross-word), and syllabation for a
  selected vocalized word.
- `dalali-rag`: the دلالي semantic layer — **extractive-first** (verbatim cited
  lexicon entries via root-key lookup, no LLM in the MVP), with generative RAG
  synthesis deferred as an optional, entailment-grounded later increment.

### Modified Capabilities

<!-- None. QLisan is additive and stays decoupled from existing retrieval/chat capabilities. -->

## Impact

- **Ingestion**: new stage parses the already-present
  `data/raw/eqtb/quranic-treebank.csv` into `data/processed/word_index.json`
  (the alignment spine + overrides), `qac_words.json` (صرفي), `qac_syntax.json`
  (نحوي), and `root_graph.json` (naẓāʾir). No new corpus download for the socle.
- **Indexing / Qdrant**: **unchanged for the MVP** — extractive دلالī is a keyed
  lookup, not a vector search, so no new collection is created. A dedicated
  `qlisan_lexicon` collection is introduced **only** if the deferred generative
  layer is later built, and would stay separate from `quran_verses`.
- **Backend**: new FastAPI router(s) and Pydantic models for the per-word fiche;
  follows the existing router/service and error conventions; reuses the Madār
  `MaqayisStore` root-key lookup pattern for the extractive دلالī.
- **Frontend**: new route/tab added to the sidebar nav; reuses `VerseCard`,
  `ArabicText`, the surah picker, and the `lib/api.ts` client pattern; word
  selection is driven by the spine's character-span map, not a naïve whitespace split.
- **External dependencies / licensing** (distribution posture: **private / local
  only** for now): QAC morphology + treebank (already present, GPL-labeled);
  `quran-tajweed` **data** only (CC-BY-4.0; its code is unlicensed — reimplement
  rule logic); public-domain-provenance lexicon editions (avoid NC/share-alike
  digital editions such as OpenITI MAKHZAN). Record every source + license in a
  provenance note and confirm the `quran.csv`/`quran_chakl.csv` origin to keep a
  future open/commercial pivot cheap. No compliance engineering in the MVP.
- **Decoupling**: QLisan does not alter the chat retrieval path; the MVP shares no
  runtime retrieval pieces with chat (only UI primitives and the Madār lookup pattern).
