## ADDED Requirements

### Requirement: The تركيب is one thesis that names the levels it composes

The fifth block SHALL state, as a single coherent thesis in Arabic, what the four preceding levels
produce **together** that none produces alone — the القيمة الزائدة. It SHALL explicitly name the
levels it is composing (the letters/صوت, the صيغة, the نحو, the دلالة) and SHALL cite, for each
named level, at least one claim from that level of the same analysis.

A تركيب that introduces a new fact not present in any of the four levels SHALL be dropped.

#### Scenario: The pinned word's تركيب composes all four levels

- **WHEN** the تركيب is generated for 23:61:2
- **THEN** it joins the phonetic extension of the مدّ, the مغالبة of the مفاعلة form, and the
  تجدّد of the مضارع into one reading of a believer perpetually contending to be foremost in
  الخيرات
- **AND** it cites at least one claim from each of the four levels
- **AND** it is badged مُولَّد.

#### Scenario: A تركيب introducing a new fact is dropped

- **WHEN** a generated تركيب asserts a morphological, syntactic or semantic fact absent from the
  four levels of the same analysis
- **THEN** the claim is dropped
- **AND** the coverage log records reason `tarkib-unsupported-by-levels`.

### Requirement: The contrastive clause of the تركيب is anchored on attested usage or on verified absence

The تركيب MAY close with a contrastive clause of the form «يتعذّر بلوغه لو قيل X». That clause
SHALL be anchored the same way the صرفي contrast is: either X is attested in the Quran and the
clause cites its ref, or X is verified absent from the corpus and the clause says so. An
unanchored contrastive clause SHALL be dropped.

#### Scenario: The exemplar's closing contrast is anchored

- **WHEN** the تركيب for 23:61:2 closes with a contrast against a plainer expression of doing good
- **THEN** the alternative is checked against the corpus
- **AND** the clause states whether it occurs in the Quran
- **AND** the clause is badged تأويلي.

#### Scenario: An unanchored contrast is dropped, the thesis survives

- **WHEN** the contrastive clause names an alternative that was never checked
- **THEN** only the clause is dropped
- **AND** the rest of the تركيب still renders.

### Requirement: The تركيب is omitted rather than weakened when the levels beneath it are thin

The تركيب SHALL be produced only when at least two of the four levels carry surviving claims. With
fewer, the block SHALL render as unavailable with a stated reason. The system SHALL NOT emit a
generic thesis, a restatement of one level, or a paraphrase of the verse.

#### Scenario: Fewer than two grounded levels yields no تركيب

- **WHEN** only the صرفي level carries surviving claims for a word
- **THEN** the تركيب block is unavailable with a stated reason
- **AND** the coverage log records reason `insufficient-levels`.

#### Scenario: A تركيب that restates a single level is dropped

- **WHEN** the generated تركيب cites claims from only one level
- **THEN** it is dropped
- **AND** the coverage log records reason `tarkib-single-level`.

### Requirement: The تركيب is never badged محقّق and is separable from the rest of the analysis

The تركيب is the most interpretive output of the page. It SHALL always be badged مُولَّد (or
تأويلي where it rests on letter-symbolism claims), SHALL always be marked un-reviewed until an
expert reviews it, and its failure SHALL NOT affect the four levels beneath it.

#### Scenario: A failed تركيب leaves the four levels intact

- **WHEN** the تركيب generation fails or every تركيب claim is dropped
- **THEN** the four preceding blocks render unchanged
- **AND** only the تركيب block reports its unavailability.

#### Scenario: The تركيب can be disabled independently

- **WHEN** the تركيب is disabled by configuration while the per-level تعليل stays enabled
- **THEN** the four levels still render with their تعليل
- **AND** the تركيب block is absent with a stated reason.
