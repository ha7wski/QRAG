## ADDED Requirements

### Requirement: The verse synthesis is composed from the verse's own word analyses, never from the verse text

The verse-level analysis SHALL be produced by running the word pipeline over the verse's tokens and
generating one synthesis whose evidence bundle is **the resulting word claims**. The generator
SHALL NOT be given the verse text as a source of meaning, and SHALL NOT be asked what the verse
says.

Every verse-level claim SHALL cite the word claims it composes, identified by `surah:ayah:word`.

#### Scenario: The verse synthesis cites word claims

- **WHEN** `POST /tahlil/verse {"surah": 23, "ayah": 61}` is called
- **THEN** each claim in the synthesis cites at least one word-level claim by its word ref
- **AND** a claim citing no word-level claim is dropped with reason `verse-claim-unanchored`.

#### Scenario: The verse synthesis asserts nothing the words do not

- **WHEN** the synthesis is validated
- **THEN** no claim asserts a morphological, syntactic or semantic fact absent from the word
  analyses of that verse.

### Requirement: Verse synthesis reuses cached word analyses and states what it covered

The verse path SHALL reuse cached word analyses where present and cache its own result under the
same version-derived key scheme. It SHALL state in its output how many words it analysed and which
it skipped.

Rootless words carry no letters, no naẓāʾir and no lexical anchor; the synthesis SHALL be built on
the verse's rooted words and SHALL say so. Long verses (measured: mean 12.4 words, max 128) SHALL
be capped, and the cap SHALL be stated in the output and recorded in the coverage log — a silent
truncation would read as full coverage.

#### Scenario: Coverage is stated, not implied

- **WHEN** a verse synthesis is produced
- **THEN** the response reports the number of words analysed and the number skipped with reasons
- **AND** the UI shows that count.

#### Scenario: A long verse states its cap

- **WHEN** a verse exceeding the word cap is analysed (e.g. 2:282)
- **THEN** the response states that the synthesis covers a capped subset
- **AND** the coverage log records `verse-word-cap` with the counts.

#### Scenario: Cached word analyses are reused

- **WHEN** a verse synthesis is requested for a verse whose words were already analysed at the
  current versions
- **THEN** no word-level LLM call is repeated
- **AND** the word claims used are the cached ones.

### Requirement: Verse synthesis is subject to the same badges, citation gate and review state

Every verse-level claim SHALL be badged (مُولَّد / تأويلي), SHALL pass the same citation validator
as word claims, SHALL never be badged محقّق, and SHALL carry the same `reviewed` state semantics.

#### Scenario: An unbadged or uncited verse claim is dropped

- **WHEN** a verse-level claim returns without a badge or with an unresolvable citation
- **THEN** it is dropped
- **AND** the coverage log records the reason.

### Requirement: The verse-level Zero pyramid view is explicitly out of scope

This capability SHALL NOT produce a pyramid or graph view of the verse's Zero relations. It
produces prose composed from word analyses only.

#### Scenario: No pyramid is produced

- **WHEN** a verse synthesis is produced for a verse whose words carry Zero relations
- **THEN** the output contains no pyramid, graph, or tree rendering of those relations
- **AND** the relations appear only inside the word-level claims that cite them.
