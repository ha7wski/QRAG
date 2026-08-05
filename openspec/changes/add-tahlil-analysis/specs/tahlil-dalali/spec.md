## ADDED Requirements

### Requirement: No tafsīr, no أسباب النزول, and no external commentary enters the دلالي block

The دلالي reading SHALL be built exclusively from: the letters of the root, the Quran's own usage
(the word's naẓāʾir and their contexts), the verse's own syntactic context, and purely linguistic
core-sense lexicons (Ibn Fāris' Maqāyīs as shipped). The system SHALL NOT ingest, index, retrieve
from, or prompt with any tafsīr, commentary, أسباب النزول, or translation as evidence of meaning.

No Qdrant collection of tafsīr SHALL exist. The generator SHALL be given the assembled evidence
bundle only, and SHALL NOT be asked what a verse means.

#### Scenario: No commentary source is reachable from the دلالي path

- **WHEN** the evidence bundle for any word is assembled
- **THEN** every evidence item is one of: a letter entry, a naẓīr occurrence, a form-KB row, a
  Maqāyīs aṣl, or a field of the word's own QAC record
- **AND** no item originates from a commentary, a tafsīr, or a translation.

#### Scenario: The prompt carries no verse interpretation

- **WHEN** the generation prompt is built
- **THEN** it contains the evidence bundle and the output contract only
- **AND** it does not ask the model what the verse means or invite it to recall an interpretation.

### Requirement: The core sense is stated from the lexical anchor and the letters, with its anchors named

The block SHALL state the root's core sense (المعنى المحوري) built from the Maqāyīs aṣl where one
exists and from the letters synthesis, and SHALL name which anchors it had. Measured: Maqāyīs
covers 1 142 of 1 642 corpus roots — 75.7 % of rooted words. Where no aṣl exists, the block SHALL
say the core sense rests on the letters and usage alone, and the claim SHALL be badged تأويلي
rather than مُولَّد.

The cited aṣl text itself SHALL be reproduced verbatim and badged محقّق; the reading built on it is
مُولَّد.

#### Scenario: The pinned root has a lexical anchor

- **WHEN** the دلالي block is assembled for root `سرع`
- **THEN** the aṣl «السين والراء والعين أصل صحيح يدل على خلاف البطء» is shown verbatim, badged
  محقّق, cited to Maqāyīs
- **AND** the core-sense reading built on it is badged مُولَّد.

#### Scenario: A root with no aṣl says so

- **WHEN** the block is assembled for a root absent from the Maqāyīs store
- **THEN** the block states that no lexical anchor was available
- **AND** the core sense is badged تأويلي
- **AND** the coverage log records reason `no-lexical-anchor`.

### Requirement: The contextual sense is inferred from the Quran alone and cites its naẓāʾir

The contextual (سياقي) sense SHALL be inferred from the verse's own context and from the word's
naẓāʾir — occurrences of the same lemma, and of the same root when the lemma set is thin. Every
contextual claim SHALL cite at least one naẓīr ref, and those refs SHALL resolve to real
occurrences in the corpus.

Naẓāʾir SHALL be lemma-scoped first, so homographic senses under one root are never mixed; when
fewer than three same-lemma siblings exist (measured: 3.5 % of rooted words have none, 8.2 % have
fewer than three), other lemmas of the root MAY be used but SHALL be labelled as such.

#### Scenario: A contextual claim cites resolvable naẓāʾir

- **WHEN** the contextual sense is generated for 23:61:2
- **THEN** it cites at least one naẓīr among the 8 same-lemma siblings (including 3:114:10)
- **AND** every cited ref exists in the corpus
- **AND** a claim citing no naẓīr is dropped.

#### Scenario: Cross-lemma evidence is labelled

- **WHEN** the naẓāʾir set falls back to other lemmas of the same root
- **THEN** those entries are labelled with their lemma
- **AND** the claim states that the evidence is root-level, not lemma-level.

#### Scenario: A word with no naẓīr gets no contextual claim

- **WHEN** the word has no same-lemma and no same-root sibling (measured: 453 rooted words have
  neither an aṣl nor a naẓīr)
- **THEN** no contextual sense is asserted
- **AND** the block states that the Quran attests this word only here.

### Requirement: The حقل دلالي is derived from Quranic co-occurrence and badged مُولَّد

The semantic field SHALL be derived from the Quran's own text — the roots and lemmas that recur
around this root's occurrences — and SHALL cite the occurrences it was derived from. It SHALL be
badged مُولَّد.

The QAC concept ontology assumed by the original checklist **does not exist in this repository**
(verified: no ontology artifact and no loader). The system SHALL NOT claim an ontology source it
does not have, and SHALL NOT fabricate ontology categories. Importing an external ontology is out
of scope for this capability.

#### Scenario: The field cites the occurrences it was derived from

- **WHEN** the حقل دلالي is produced for a root
- **THEN** it names co-occurring roots/lemmas and cites the occurrence refs supporting each
- **AND** it is badged مُولَّد
- **AND** it does not name an ontology category or an external taxonomy.

#### Scenario: A thin occurrence set yields no field

- **WHEN** the root's occurrence set is too small to derive a field
- **THEN** the field is omitted with a stated reason
- **AND** no field is asserted from the model's own knowledge.

### Requirement: Synonymy and antonymy claims come from Quranic usage or are omitted

Any ترادف / تضاد claim SHALL be supported by Quranic occurrences showing the relation in use, and
SHALL cite them. A relation asserted from general lexical knowledge SHALL be dropped.

#### Scenario: An uncited synonymy claim is dropped

- **WHEN** a generated claim asserts that two roots are synonymous without citing occurrences
- **THEN** the claim is dropped
- **AND** the coverage log records reason `unsupported-lexical-relation`.
