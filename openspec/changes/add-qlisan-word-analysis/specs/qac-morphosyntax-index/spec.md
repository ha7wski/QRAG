## ADDED Requirements

### Requirement: Token-alignment spine

The ingestion SHALL first build a token-alignment spine that reconciles the QAC
per-word keys (canonical `surah:ayah:word`) onto the displayed vocalized rasm,
because every analysis level keys off this mapping. The QAC word segmentation
(identical between the treebank and the legacy morphology source) SHALL be the
canonical spine; the displayed rasm SHALL be aligned **onto** it. Alignment SHALL
be treated as merge-only: each displayed content-token maps to exactly one QAC
`surah:ayah:word` or is classified as droppable (annotation marks, prepended
basmala), never split. Word counts SHALL be computed from the maximum word index
of real word rows, excluding treebank pseudo-tokens (elided heads and
parenthesized pro-drop pronouns).

#### Scenario: Every displayed content-token maps to a QAC word

- **WHEN** the spine is built over all 6236 verses
- **THEN** every displayed content-token maps to exactly one QAC `surah:ayah:word`, or is classified with an explicit drop reason (waqf/sajda/hizb mark, prepended basmala, mergeable clitic)
- **AND** every QAC word position is covered by the mapping.

#### Scenario: Residual mismatches are curated, not silently dropped

- **WHEN** the automatic alignment rules leave a residual set of verses whose tokens do not reconcile
- **THEN** those verses are resolved by an explicit, auditable override set rather than being silently truncated
- **AND** the build emits an audit report listing every override and every dropped token with its reason.

#### Scenario: Character spans survive orthographic divergence

- **WHEN** a QAC word is mapped to its span in the displayed rasm and the two differ orthographically (e.g. alif-waṣla ٱ or superscript alif versus plain ا, or multiple QAC segments composing one displayed word)
- **THEN** the mapping yields character offsets into the raw displayed text that select the correct glyphs
- **AND** highlighting the word in the UI lands on the intended characters, not shifted ones.

### Requirement: Per-word morpho-syntactic index keyed by position

The ingestion pipeline SHALL produce a per-word index keyed by the position
`surah:ayah:word`, built deterministically and offline from the Quranic Arabic
Corpus treebank export (`data/raw/eqtb/quranic-treebank.csv`), which supplies
morphology and syntax from the same rows. Each entry SHALL carry the word's
surface form, its segments, root, lemma, part-of-speech, and morphological
features. Root and lemma keys SHALL be produced with the root-safe normalization
(`normalize_root`) already used by the project, never the hamza-deleting
`normalize_text`.

#### Scenario: Every corpus word has an index entry

- **WHEN** the index is built from the QAC treebank source
- **THEN** each word position `surah:ayah:word` in the corpus resolves to an entry with its form, segments, root (when attested), lemma, POS, and features
- **AND** words without an attested root (e.g. proper nouns) are still represented, marked as rootless rather than dropped.

#### Scenario: Root keys use root-safe normalization

- **WHEN** a word's root is recorded in the index
- **THEN** the root key is normalized with `normalize_root` (hamza carriers folded, bare hamza preserved, never deleted).

### Requirement: Morphological level served deterministically

The morphological (صرفي) level of a word SHALL be served entirely from the
per-word index, with no LLM involvement. It SHALL expose the word's root, lemma,
part-of-speech, and morphological features.

#### Scenario: Morphological level is deterministic

- **WHEN** the صرفي level is requested for a word position
- **THEN** its root, lemma, POS, and features come directly from the per-word index
- **AND** the same word position always yields the same صرفي data.

### Requirement: Syntactic level from the dependency treebank

The syntactic (نحوي) level SHALL be served from the ingested QAC dependency
treebank (the `rel_label` / head-reference / constituent columns of the same
treebank export), keyed to the same `surah:ayah:word` positions, with no LLM
involvement. It SHALL expose the word's grammatical role and its dependency
relation(s) to other words in the verse, resolved against the relation-label
dictionary.

#### Scenario: Syntactic level is deterministic

- **WHEN** the نحوي level is requested for a word position that exists in the treebank
- **THEN** its grammatical role and dependency relation(s) come directly from the ingested treebank
- **AND** no LLM is used to produce them.

#### Scenario: Word absent from the treebank

- **WHEN** a word position has no treebank annotation
- **THEN** the نحوي level is reported as unavailable for that word rather than being inferred or fabricated.

### Requirement: Root graph of derivatives and occurrences

The ingestion SHALL build a root graph linking each root to its derived
lemmas/forms and to their occurrences (naẓāʾir) across the corpus, so a fiche can
list sibling words that share the selected word's root. The graph SHALL be
derived deterministically from the per-word index.

#### Scenario: Fiche links to root siblings

- **WHEN** a word with an attested root is analysed
- **THEN** the fiche can list other words in the corpus sharing that root, each with its occurrence position(s)
- **AND** these come from the deterministic root graph, not from generation.
