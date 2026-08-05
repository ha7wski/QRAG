## MODIFIED Requirements

### Requirement: The verified badge covers only verbatim fields

The صرفي and نحوي levels SHALL display the «معطى محقّق» (verified) badge only over
data taken verbatim from the parsed corpus (morphology fields, the relation function
name, the case name), **or deterministically derived from such a field with no LLM on the path**,
served deterministically with no LLM on the path. A **derived** field — specifically the case
marker (العلامة), which is a heuristic mapping and is
wrong for sound-plural / dual / diptote classes — SHALL NOT be covered by the badge; it
SHALL be presented as a distinct «الأصل» hint and SHALL be omitted (never fabricated)
where the primary marker is unreliable.

The badge SHALL further distinguish **derived from a verbatim field** from **asserted without
one**. A Zero relation computed from a QAC role present in `qac_syntax.json` is derived and SHALL
carry the badge. A relation **minted** for a word that has no QAC role at all — the standalone عطف
particles absent from the treebank — is asserted from the part of speech alone and SHALL NOT carry
the badge, SHALL be visibly distinguished from verified rows, and SHALL be enumerated in the
coverage log.

#### Scenario: Verified badge preserved on verbatim fields

- **WHEN** the صرفي or نحوي level is rendered for a word with treebank data
- **THEN** the verbatim fields (morphology, relation function, case name) carry the
  «معطى محقّق» badge
- **AND** no field under the badge originates from an LLM

#### Scenario: Derived marker rendered outside the badge

- **WHEN** the case marker (العلامة) is shown for a word (e.g. السحاب 13:12:8 → الفتحة)
- **THEN** it is presented as a derived «الأصل» hint outside the «معطى محقّق» badge
- **AND** for a word where the primary marker is unreliable (e.g. 1:2:4 ٱلْعَٰلَمِينَ,
  a genitive sound plural) the marker is omitted rather than shown wrong

#### Scenario: A Zero relation derived from a QAC role keeps the badge

- **WHEN** the نحوي level renders العلاقة / الدور / السبب for a word whose QAC role is present in
  the treebank (e.g. 1:6:2 ٱلصِّرَٰطَ → «منصوب لأنه تخصيص (مفعول به)»)
- **THEN** those rows are covered by the «معطى محقّق» badge
- **AND** the derivation used no LLM and no network call

#### Scenario: A minted relation is shown outside the badge

- **WHEN** the نحوي level renders a marker row for a standalone عطف particle that has no record in
  `qac_syntax.json`
- **THEN** the row is visibly distinguished from verified data and is not covered by the
  «معطى محقّق» badge
- **AND** the word is enumerated in the coverage log

## ADDED Requirements

### Requirement: The نحوي card presents the relation above the classical i'rāb, additively

The نحوي card SHALL render the Zero layer as additional rows — العلاقة, الدور, السبب — placed above
the existing الموقع الإعرابي and المتعلَّق, reading from theory down to detail. No existing row
SHALL be removed, reworded, or reordered by this change, and the four levels
صوتي → صرفي → نحوي → دلالي SHALL keep their fixed order and their current contents. The
المتعلَّق row SHALL be reused as the pole of the relation rather than duplicated.

This SHALL be delivered as rows inside the existing card: **no new view, no new route, and no
verse-level graph**.

#### Scenario: The card gains three rows and loses none

- **WHEN** the نحوي card is rendered for a word with a derived relation
- **THEN** العلاقة, الدور and السبب appear above الموقع الإعرابي and المتعلَّق
- **AND** الموقع الإعرابي, العلامة and المتعلَّق render exactly as they did before this change

#### Scenario: A word with no derived relation renders as before

- **WHEN** the نحوي card is rendered for a word whose Zero relation was omitted
- **THEN** the العلاقة / الدور / السبب rows are absent
- **AND** the card still shows الموقع الإعرابي and المتعلَّق unchanged

### Requirement: The Zero fields are additive on the API contract

`NahwiLevel` SHALL gain only optional fields for the Zero layer, defaulting to absent. No existing
field SHALL be removed, renamed, or have its meaning changed — `iraab_ar`, `marker_ar`, `head_ref`,
`relation`, `relation_ar` and the deprecated `role_ar` SHALL keep their exact current semantics, so
a client that ignores the new fields renders precisely what it renders today.

#### Scenario: Existing clients are unaffected

- **WHEN** a client that does not read the Zero fields requests a fiche
- **THEN** every field it already consumed is present with unchanged meaning
- **AND** the response validates against the model with the new fields absent
