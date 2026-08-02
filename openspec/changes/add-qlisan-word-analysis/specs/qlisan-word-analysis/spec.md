## ADDED Requirements

### Requirement: QLisan page and word selection

The system SHALL provide a QLisan page, reachable as a top-level entry in the
sidebar navigation, on which a user picks a verse and selects a single word to
analyse. The page SHALL render the selected verse fully vocalized with each word
token individually selectable, and SHALL highlight the currently selected word.

#### Scenario: Select a word from a verse

- **WHEN** a user opens the QLisan page, loads a verse, and clicks one word token in it
- **THEN** that word is marked as selected and highlighted within the verse
- **AND** a per-word analysis fiche for that word is requested and displayed.

#### Scenario: Change the selected word

- **WHEN** a word is already selected and the user clicks a different word token in the same verse
- **THEN** the newly clicked word becomes the selected word
- **AND** the fiche updates to describe the newly selected word.

### Requirement: Per-word analysis fiche with four ordered levels

The per-word analysis endpoint SHALL accept a word identified by its position
`surah:ayah:word` and SHALL return a fiche organized into exactly four levels in
this fixed order: **صوتي** (phonetic), **صرفي** (morphological), **نحوي**
(syntactic), **دلالي** (semantic). Each level SHALL be individually labelled and
individually renderable, and the ordering SHALL be preserved in both the API
response and the UI.

#### Scenario: Fiche returns four ordered levels

- **WHEN** the analysis endpoint is called for a valid word position
- **THEN** the response contains the four levels صوتي, صرفي, نحوي, دلالي in that order
- **AND** each level is a separately addressable section of the response.

#### Scenario: Word position resolves to a real corpus word

- **WHEN** the endpoint is called with a `surah:ayah:word` position that does not exist in the corpus
- **THEN** the request is rejected with a client error and no fiche is produced.

### Requirement: Strict separation of deterministic facts from sourced interpretation

The fiche SHALL keep the deterministic levels (صرفي, نحوي, صوتي) strictly separate
from the دلالي level. The deterministic levels SHALL be produced without any LLM
and SHALL be labelled as established facts. The دلالي level SHALL be labelled as
sourced lexicon material (verbatim cited entries in the MVP), and SHALL never be
merged into, or styled identically to, the deterministic levels. No level SHALL
fall back to LLM output to fill gaps in the deterministic levels.

#### Scenario: Deterministic levels carry no LLM content

- **WHEN** the fiche is produced for any word
- **THEN** the صرفي, نحوي, and صوتي levels contain only data derived from the deterministic index/rules (no LLM output)
- **AND** a gap in any deterministic level is shown as unavailable, never filled by generated text.

#### Scenario: A failed دلالي level does not corrupt the deterministic levels

- **WHEN** the دلالي level cannot be produced (root has no lexicon entry or the feature is disabled)
- **THEN** the صرفي, نحوي, and صوتي levels are still returned and displayed normally
- **AND** the دلالي level is shown as unavailable rather than being fabricated.

### Requirement: Incremental level availability

The fiche SHALL tolerate levels that are not yet implemented or not yet
available, exposing per-level availability so the UI can render implemented
levels and mark the rest as pending. The morphological and syntactic levels form
the required baseline; the phonetic and semantic levels MAY be absent in earlier
increments.

#### Scenario: Baseline available, later levels pending

- **WHEN** the phonetic or semantic level is not yet available for a word
- **THEN** the صرفي and نحوي levels are still returned with data
- **AND** the absent levels are marked pending/unavailable rather than omitted silently.
