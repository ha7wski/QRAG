## Context

Two chains derive roots independently and neither is wrong on purpose:

- **Chain A** — `data/raw/quran-morphology.txt` → `ingestion/qac_morphology.py` →
  `morphology.json`, `qac_resolution.json`. Feeds retrieval (`lexical_retriever`, `verse_lookup`,
  the root channel).
- **Chain B** — `data/raw/eqtb/quranic-treebank.csv` → `ingestion/qac_treebank.py` →
  `qac_words.json`, `root_graph.json`. Feeds analysis (QLisan, mīzān, fassila, tahlīl, naẓāʾir).

Measured facts this design must accommodate (`eval/roots/`):

- The `surah:ayah:word` join between the two is exact: 77 429 words, 0 orphans either way.
- They agree on 49 584 words (98.50 %) and disagree on 757 (1.50 %), across **30 families**. Six
  families cover 651 of those words, so the manual work is bounded.
- The reference source carries **139 hamzated roots**; the treebank carries **0** out of 1642 —
  that is a convention of the resource, and it makes the treebank structurally unable to spell a
  hamzated root.
- Both chains currently persist a folded form. `morphology.json` keeps 1 hamzated root out of
  1651 (`normalize_root` folds carriers); the treebank ships `لالا` for `لؤلؤ`. The correct
  spelling exists nowhere under `data/processed/`.
- Disagreement classes: 447 words where one side abstains, 243 where both name a root and at
  least one lives elsewhere in the corpus, 66 pure spelling variants, 7 known bugs.

Constraint: the treebank remains the **only** source of syntax (`qac_syntax.json`), so
"just drop chain B" is not available.

## Goals / Non-Goals

**Goals:**
- One root set per word, identical on both sides of the product.
- The stored root is the real spelling; folding survives only as a lookup key.
- Contested roots stay contested — ranked, not silently resolved — so no verse becomes
  unreachable under either reading.
- Every deviation from the reference source is traceable to a cited authority.
- The 757 disagreements become a finite, monitored budget that trends to zero.

**Non-Goals:**
- Re-deriving roots with a stemmer or a model. The legacy tashaphyne path stays off.
- Changing the syntax source, the iʿrāb composition, or anything in `qac_syntax.json`.
- Adding a third root resource. Measured earlier: cross-checking more sources adds nothing.
- Rewriting `analysis/mizan.py`'s template logic — it inherits correct radicals and is otherwise
  the subject of `harden-mizan-irregular-roots`.

## Decisions

### One resolver upstream of both chains

A new ingestion step resolves roots **before** either chain writes, and emits a single artifact
(word ref → primary, alternates, deciding rule, authority). Both `qac_morphology.py` and
`qac_treebank.py` consume it instead of each deciding for itself.

*Alternatives considered.* Patching each chain separately: rejected — it recreates two truths, and
nothing would prevent them drifting again. Dropping chain B's roots and keeping only its syntax:
tempting, but the treebank sometimes corrects the reference source (ٱلْمَاعُون), so a blanket
preference would import known errors.

### Source of truth per field, not per resource

The reference source for **root spelling** is chain A, because it is the only one carrying the
information (139 vs 0). The reference for **syntax** stays chain B. "Which resource is better" is
the wrong question; "which resource is authoritative for this field" is answerable.

### Exact spelling as the stored value and as the graph key

`root` holds the exact spelling; the fold is computed on demand for lookups. Root graph keys
become exact spellings, and every root query goes through the resolver, which folds the query and
maps it to the canonical root.

*Alternative considered:* keep folded keys and add an exact `root_display` beside them. Rejected —
that is exactly today's arrangement (`root` + `root_display` already exist in `qac_words.json`, and
measurement shows they are identical for all 1642 roots, so the display field silently decayed into
a copy of the folded key). Two forms in circulation with no enforced direction is what produced the
defect; one stored form plus an explicit resolver is what prevents it.

*Consequence:* **BREAKING** for any consumer that indexes `root_graph.json` with a folded string.
The resolver is the migration path and the permanent access point.

### Arbitration file keyed by family, with per-word escape hatch

`data/references/root_arbitration.json`, versioned with the other reference tables. Default entry
granularity is the **root family** (the `root_A × root_B` pair), because 30 entries cover all 757
words; a per-word entry overrides the family when a single occurrence genuinely differs. Each entry
carries chosen primary, alternates, deciding rule, and authority (lexicon + entry, or corpus
evidence). `eval/roots/ambiguities.tsv` — already produced, ranked by family size, with an empty
`verdict` column — is the working input to this file.

### Alternates are indexed for reach, excluded from counts

A word is reachable under its primary and its alternates. Family **counts** (occurrence tallies,
IDF weights in `similar_verses.py`, mīzān and fassila statistics) count a word only under its
primary root. Otherwise ٱلنَّاس would inflate two families by 241 each and distort every
frequency-weighted ranking.

### Rule 3 outranks rule 4

The lexicon decides before corpus frequency. ٱلْمَاعُون is the proof case: `عون` occurs 11 times
elsewhere and `معن` never, so a frequency-first cascade picks the root the brief already identified
as the error. Frequency is retained as a tie-breaker and as a suspicion signal, not as an authority.

### Lexical disagreement keeps both — decided as a principle, not built as machinery

When two lexica file a word under different roots, both roots are kept, Maqāyīs primary and the
other alternate. Crowning one dictionary permanently would be dishonest: they follow different
methods and neither is wrong, so a lexicon-vs-lexicon conflict is a scholarly disagreement, which
is exactly what rule 5 exists for. Maqāyīs ranks first because its core-meaning method is already
the project's.

Practically, only Maqāyīs is on disk, so this conflict cannot arise yet. The rule is fixed now and
**no multi-lexicon aggregation is implemented** — rule 3 reads the single available lexicon. This
keeps the cascade honest without paying for a case that does not exist.

### Contested roots are shown, not hidden

QLisan renders an alternate reading as a note outside the «معطى محقّق» badge. A study tool that
silently picks one of two scholarly readings is misleading precisely where it should be
informative; and the badge means *verbatim from the corpus*, which an arbitrated root is not.

### Treebank-only additions accepted by default, weak ones flagged

The 73 roots the treebank supplies where the reference abstains are kept under rule 2 — naming a
root beats saying nothing. Requiring a citation for all 73 would bury the few doubtful cases
(`اني` on the interrogative أَنَّىٰ, 28 words) under 45 obvious ones. The cascade flags the weak
ones for review instead of gating the block.

### Fused compounds: enumerate, do not predicate

A word is marked when showing its bare root would mislead about the word's origin. The list is
**enumerated by lemma in the arbitration file** — 3 lemmas, 225 words today — not computed by a
rule over segments.

This is not caution about a hard predicate; the predicate is impossible. Measured over vocative
compounds that carry a root:

| form | root | words | marked |
|---|---|---:|---|
| يَٰٓأَيُّهَا | `أيي` — آية's root | 153 | yes |
| يَٰقَوْمِ | `قوم` | 15 | no |
| يَٰٓأَهْلَ | `اهل` | 12 | no |
| يَٰبَنِيَّ | `بني` | 10 | no |
| يَٰٓأُو۟لِى | `اول` | 5 | no |

Same shape — vocative particle welded to a rooted stem — opposite verdicts, because what separates
them is semantic, not structural: `قوم` describes يَٰقَوْمِ, while `أيي` sends the reader to آية. The
opposite failure is just as concrete: a "≥2 stem segments" rule marks 563 words (إنما 113, مما 111,
عما 47, ألا 45) that carry no root at all, and still misses يَٰٓأَيُّهَا, whose يَٰٓ is a prefix and
whose هَا is an attached pronoun — one stem, structurally unremarkable.

The decision rule for the list is a usage test, applied once per lemma by a human: *if the bare
root is displayed, will the reader be wrong about where the word comes from?* It settles the
borderline cases (يَٰٓأَيُّهَا yes, بِسْمِ no) without ever having to define "a real lexical unit".
The list is short enough to eyeball, and every addition is recorded with its reason.

### Proper nouns keep a flagged root

74 words. Storing the root plus `is_proper_noun` is recoverable in both directions; nulling the
root is not. Consumers that must exclude proper nouns filter on the flag.

## Risks / Trade-offs

- **The classical lexica may not resolve every family** → rule 5 (keep both, ranked) is the safe
  default. The cascade never forces a choice it cannot justify; an unresolved family stays
  multi-root rather than becoming a guess.
- **Alternates add retrieval noise** → dedup per word, and ranking independent of which root
  matched. Quantify with `tests/eval/evaluate.py` and `tests/eval/search_eval.py` before/after;
  the root channel is on by default, so any regression is measurable rather than theoretical.
- **Changing graph keys breaks callers silently** → the resolver becomes the only access path, the
  regression gate fails on unarbitrated divergence, and a full pipeline rebuild is mandatory
  rather than incremental.
- **Manual arbitration is human work** → bounded: 30 families, of which 6 cover 651 words. The TSV
  is pre-sorted by impact so the highest-value verdicts come first.
- **Restoring hamza changes strings the mīzān walks** → intended (it currently walks `لالا`), but
  it shifts the باب/وزن distribution. Re-measure the اجتهادي rate from
  `harden-mizan-irregular-roots` after the rebuild so the two changes are not confounded.
- **`root` semantics change under consumers that never asked** → the field goes from folded to
  exact. Any code doing `root_graph[word["root"]]` must move to the resolver; this is the one
  mechanical sweep the change requires.

## Migration Plan

1. Freeze the baseline: `eval/roots/{unified_roots.json,ambiguities.tsv,ambiguities_summary.md}`
   are the before-state, with per-type counts.
2. Fill the verdict column family by family, highest impact first, citing an authority per line;
   generate `data/references/root_arbitration.json` from it.
3. Add the resolver and its artifact. It is a no-op when the arbitration file is empty except for
   spelling restoration, so it can land and be inspected before any consumer moves.
4. Move chain A onto the resolver, rebuild, re-run retrieval evals.
5. Move chain B onto the resolver, rebuild, re-check QLisan / mīzān / naẓāʾir.
6. Turn the regression gate on in the pipeline once the unarbitrated count reaches 0.

*Rollback:* every processed artifact is regenerable. An empty arbitration file plus the resolver
reproduces today's roots except for spelling, so the change can be backed out in one rebuild.

## Open Questions

All questions this design opened are settled: lexical disagreement keeps both with no machinery
built yet; alternates are shown in QLisan; treebank-only additions are accepted with the weak ones
flagged; fused compounds are marked from an enumerated lemma list decided by the usage test.

Nothing blocks implementation. Two items are deferred by choice, not by uncertainty:

- Which lexicon to add as a second authority later. Until then rule 3 reads Maqāyīs alone and
  rule 5 cannot fire from a lexical conflict.
- The exact Arabic wording of the two QLisan notes (contested root, fused compound). Copy, not
  behaviour — the spec fixes where they render and what they must not claim.
