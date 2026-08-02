## ADDED Requirements

### Requirement: Extractive semantic layer via root-key lexicon lookup

The semantic (دلالī) level SHALL, in its baseline form, be produced by a
deterministic root→entry lookup over classical lexicons (al-Rāghib's *Mufradāt*,
Ibn Fāris's *Maqāyīs al-Lugha*), returning the lexicon's **verbatim** entry text
for the selected word's root. It SHALL NOT use an LLM in this baseline. The lookup
SHALL reuse the project's existing root-key store pattern (exact `normalize_root`
key with geminate fallback, offline), since the lexicons are root-organized and a
key lookup is exact where a similarity search would not be.

#### Scenario: Verbatim entry returned for an attested root

- **WHEN** the دلالī level is requested for a word whose root has a lexicon entry
- **THEN** the verbatim lexicon entry text is returned for that root
- **AND** it is produced by a deterministic key lookup with no LLM.

#### Scenario: No entry for the root

- **WHEN** the word's root has no entry in any indexed lexicon
- **THEN** the دلالī level is returned as unavailable with an explanatory message, and nothing is generated in its place.

### Requirement: Citation is the source itself

Every fragment shown in the extractive دلالī level SHALL be the source text
itself, presented with its citation (lexicon, root entry, and locator). Because
the displayed text is verbatim, the citation and the claim are inseparable: there
SHALL be no unsourced or paraphrased content in the baseline level.

#### Scenario: Displayed text is attributable verbatim

- **WHEN** the دلالī level is displayed for a word
- **THEN** each shown fragment is verbatim source text carrying its lexicon citation and locator
- **AND** no paraphrased or model-generated statement appears in the baseline level.

### Requirement: Semantic layer labelled as sourced and kept separate

The دلالī level SHALL be visibly labelled as sourced lexicon material, distinct
from the deterministic صرفي/نحوي/صوتي levels, and SHALL never be merged into or
styled identically to them.

#### Scenario: Sourced material is visibly distinct

- **WHEN** the دلالī level is displayed
- **THEN** it is presented as cited lexicon material with its sources shown
- **AND** it is never rendered inside, or styled identically to, the deterministic levels.

### Requirement: Generative synthesis is deferred and grounded when built

Generative RAG synthesis of the دلالī level SHALL NOT be part of the baseline and
SHALL be off by default. If a later increment adds it, it SHALL retrieve over a
Qdrant collection dedicated to the lexicon/tafsīr corpus (separate from
`quran_verses`, reusing the existing embedder/BM25/reranker), and each generated
claim SHALL be verified by per-claim entailment against a retrieved passage plus a
verbatim supporting span. A citation-id membership check alone SHALL NOT be
accepted as sufficient grounding. Any claim failing entailment SHALL be dropped;
if none survives, the generated view SHALL be unavailable and the extractive view
SHALL remain the shown content.

#### Scenario: Generation off by default

- **WHEN** the MVP دلالī level is served
- **THEN** it is the extractive lookup result and no generation runs.

#### Scenario: Generated claim without entailment is rejected

- **WHEN** the deferred generative layer is enabled and produces a claim not entailed by any retrieved passage (even one that cites a real passage id)
- **THEN** that claim is dropped and never displayed as fact
- **AND** if no claim survives entailment, the extractive lexicon view is shown instead.

#### Scenario: Semantic corpus isolated from the verse collection

- **WHEN** the deferred generative layer indexes and retrieves lexicon/tafsīr passages
- **THEN** it uses a dedicated Qdrant collection separate from `quran_verses`
- **AND** existing chat and verse-search behaviour over `quran_verses` is unchanged.
