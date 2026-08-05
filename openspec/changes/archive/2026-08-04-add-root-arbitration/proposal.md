## Why

The project answers «what is the root of this word?» **twice, differently**, and neither answer
preserves how the root is spelled.

Two independent chains feed two halves of the product:

| chain | source file | produces | consumed by |
|---|---|---|---|
| **A** | `data/raw/quran-morphology.txt` (mustafa0x QAC fork) | `morphology.json`, `qac_resolution.json` | `retrieval/verse_lookup.py`, `retrieval/lexical_retriever.py`, root channel — i.e. Verse Study & search |
| **B** | `data/raw/eqtb/quranic-treebank.csv` (eQTB treebank) | `qac_words.json`, `root_graph.json` | `analysis/{qlisan_data,mizan,fassila,word_analysis,qac_labels}.py`, `api/routers/tahlil.py` — i.e. QLisan, mīzān, naẓāʾir, tahlīl |

Measured over all 77 429 words (the `surah:ayah:word` join is exact — 0 orphans on either side):

| | words | share |
|---|---:|---:|
| both chains agree on a root | 49 584 | 98.50 % |
| **the two chains disagree** | **757** | **1.50 %** |
| both give no root | 27 088 | — |

757 words across **30 families** is small, finite, and fully enumerated — but it is not harmless,
because the disagreement is invisible to the user and lands on high-frequency words. ٱلنَّاس is
filed under `انس` in Verse Study and under `نوس` in QLisan — 241 words, the most frequent noun in
the Quran after the divine name. Search one, and the other half of the product cannot find it.

The second defect is worse because it is silent and irreversible: **both chains store a folded
root, not the real one.** `normalize_root` is used simultaneously as a comparison key *and* as the
stored form, and the treebank ships roots that were already stripped upstream:

| word | source A (raw) | chain A stores | chain B stores |
|---|---|---|---|
| لُؤْلُؤ | `لؤلؤ` | `لولو` | `لالا` |
| ٱلنَّاس | `أنس` | `انس` | `نوس` |
| لِّيَطْمَئِنَّ | `طمأن` | `طمان` | `طمن` |
| ٱلْمَاعُون | `عون` | `عون` | `معن` |

Of the **139 hamzated roots** present in the raw source, exactly **1** survives in
`morphology.json` and **0** in the treebank (which carries 0 hamzated roots out of 1642 — a
convention of that resource, not a bug in our code). The correct spelling `لؤلؤ` exists nowhere
under `data/processed/`. Folding is fine for matching and cannot be undone for display: `لالا`
can never be turned back into `لؤلؤ`, while the reverse is trivial. Every downstream consumer that
reasons on root letters inherits the damage — `analysis/mizan.py` computes the الميزان الصرفي by
walking root radicals, so it walks `لالا`.

Nothing here is a code bug to patch. It is a missing decision: the project has never stated which
root is authoritative, in which spelling, and what to do when the two resources genuinely disagree.

## What Changes

- **One arbitrated root per word, shared by both chains.** A single resolution step decides the
  root for each of the 77 429 words; chain A and chain B stop publishing rival answers.
- **Separate the stored form from the comparison key. BREAKING** — the stored root becomes the
  exact QAC spelling (`لؤلؤ`, `أنس`), while folding stays where it belongs: in lookup keys and
  index entries. Root keys in `morphology.json` and `root_graph.json` change spelling for the 139
  hamzated roots, so every consumer keyed on the folded string must go through the resolver.
- **A deterministic arbitration cascade**, applied in order, first rule that answers wins:
  0. a recorded human verdict wins over every rule below;
  1. equal under either fold → not a disagreement, keep source A's spelling;
  2. exactly one side proposes a root → take it (silence carries no claim);
  3. the classical lexicon (Maqāyīs al-Lugha, on disk at `data/raw/maqayis`) arbitrates — the
     entry a lexicographer filed the word under outranks any corpus heuristic;
  4. attestation elsewhere in the Quran breaks a tie the lexicon leaves open;
  5. two lexica disagree → **keep both**, ranked primary/alternate.

  Rule 3 must outrank rule 4, not the reverse: ٱلْمَاعُون is filed under مَعَنَ although `معن`
  occurs nowhere else in the Quran while `عون` occurs 11 times. A frequency-first cascade would
  confidently pick the wrong root here.

  Rule 5 is decided as a principle, not built as machinery: only Maqāyīs is on disk today, so a
  lexicon-vs-lexicon conflict cannot yet arise. When a second lexicon is added, a disagreement
  between them is a scholarly disagreement — crowning one dictionary permanently would be
  dishonest, since they follow different methods and neither is wrong. Maqāyīs ranks primary
  (its core-meaning method is already the project's), the other becomes the alternate.
- **Multi-root words become first-class**, not a defect. ٱلنَّاس carries primary `أنس` and alternate
  `نوس`; retrieval matches either, so no verse is unreachable under either reading. QLisan
  **shows** the contested reading as a note («ناس: الجذر الأساسي أنس، ويُقرأ أيضًا نوس») — a study
  tool surfaces a scholarly dispute rather than hiding it behind a silent pick.
- **Misleading fused compounds are marked, from an enumerated lemma list** — `ايها` (153),
  `ايتها` (2), `يوميذ` (70) — not from a structural rule. The root family `أيي` currently mixes
  382 آية/ءايات with 155 يَٰٓأَيُّهَا under one bare root, so a search for آية returns يا أيها. The
  inclusion test is semantic: *shown bare, does this root mislead about the word's origin?*
  It has to be, because structure cannot decide — يَٰقَوْمِ (`قوم`, 15), يَٰٓأَهْلَ (`اهل`, 12),
  يَٰبَنِيَّ (`بني`, 10) have the same shape as يَٰٓأَيُّهَا and are correctly rooted, so they stay
  unmarked; while a "≥2 stem segments" rule would mark 563 rootless particles (إنما, مما, عما, ألا)
  and still miss يَٰٓأَيُّهَا.
- **Proper nouns keep their root plus the `is_proper_noun` flag** instead of being nulled — a
  displayed root can be filtered, an erased one cannot be recovered. Settles 74 words at once.
- **Roots the treebank adds where the reference abstains are accepted by default** (73 words):
  naming a root beats saying nothing. The weak ones are flagged for a citation rather than
  requiring 73 mandatory citations — `اني` for the interrogative أنّى is the case to check, not
  the whole block.
- **A versioned arbitration file** — one line per decision (`word or root → chosen, alternate,
  reason, authority`) — is the only place where a root may deviate from source A. No implicit
  transformation anywhere in the pipeline.
- **A regression gate**: after any rebuild, a disagreement absent from the arbitration file fails
  the check. Today's budget is 757 words; the target is 0 unarbitrated.

Out of scope: changing which resource supplies syntax (the treebank stays the only source for
`qac_syntax.json`), and re-deriving roots with a stemmer.

## Capabilities

### New Capabilities
- `root-attribution`: the canonical root of every Quran word — arbitration between the two
  resources, the exact-spelling storage rule, primary/alternate ranking, the arbitration file
  format, and the regression gate that keeps unarbitrated disagreements out.

### Modified Capabilities
- `qac-morphosyntax-index`: the root exposed per word becomes the arbitrated root in its exact
  spelling, and may carry an alternate plus a fused-compound marker. Naẓāʾir — currently scoped by
  lemma under a bare root — SHALL follow the arbitrated root and cover the alternate reading, so
  ٱلنَّاس siblings are the same set regardless of which root the reader believes in.
- `qlisan-word-analysis`: the صرفي level SHALL surface a contested root as a readable note and mark
  a fused compound, both outside the verified badge — an arbitrated root is a decision, not a
  verbatim source field.

## Impact

- **Data**: `data/processed/{morphology,qac_resolution,qac_words,root_graph}.json` change root
  spelling and gain alternates. A new arbitration file under `data/references/`. Full pipeline
  rebuild required.
- **Ingestion**: `ingestion/qac_morphology.py`, `ingestion/qac_treebank.py`,
  `ingestion/root_normalize.py` (fold demoted to key-only use), `ingestion/run_pipeline.py`.
- **Retrieval**: `retrieval/lexical_retriever.py`, `retrieval/verse_lookup.py`,
  `retrieval/root_channel.py`, `retrieval/similar_verses.py` — root lookup must accept an
  alternate without duplicating hits.
- **Analysis**: `analysis/mizan.py` gains correct radicals for hamzated roots (it currently walks
  `لالا`), plus `qlisan_data.py`, `fassila.py`, `word_analysis.py`, `qac_labels.py`,
  `api/routers/tahlil.py`.
- **Evidence already on disk**: `eval/roots/unified_roots.json` (root → all its words, with both
  answers per word), `eval/roots/ambiguities.tsv` (the 757 disagreements, typed and ranked, with an
  empty `verdict` column) and `eval/roots/ambiguities_summary.md`. The TSV is the input to the
  arbitration file, not a throwaway.
- **No new dependency, no network, no model.** The arbitration is a finite table plus a
  deterministic cascade.
