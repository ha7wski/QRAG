## MODIFIED Requirements

### Requirement: The verified badge covers only verbatim fields

The صرفي and نحوي levels SHALL display the «معطى محقّق» (verified) badge only over
data taken verbatim from the parsed corpus (morphology fields, the relation function
name, the case name), served deterministically with no LLM on the path. A **derived**
field — specifically the case marker (العلامة), which is a heuristic mapping and is
wrong for sound-plural / dual / diptote classes — SHALL NOT be covered by the badge; it
SHALL be presented as a distinct «الأصل» hint and SHALL be omitted (never fabricated)
where the primary marker is unreliable.

This badge is now the top of a **three-badge taxonomy** shared with the Tahlil page, and the
taxonomy SHALL be consistent across both:

- **محقّق** — verbatim from the corpus, or a deterministic derivation of a verbatim field
  (the mīzān, the باب, the composed iʿrāb, the verb-mood marker). No LLM on the path.
- **مُولَّد** — generated content whose every assertion resolves to a cited naẓīr, form-KB row,
  or lexicon entry; and, where the cited row offers several senses, whose citations also include a
  corpus disambiguator for the sense selected.
- **تأويلي** — interpretive content: letter phono-semantics, any contrastive «أبلغ من X», and any
  sense selection made from a multi-sense row without a corpus disambiguator.

**No content produced by a generation path SHALL ever carry «محقّق»**, in either page, regardless
of how well it is cited. A system that would emit such a claim SHALL drop it and log the attempt
rather than re-badge it.

Each badge SHALL carry a fixed label and tooltip, identical in both pages, stating what the badge
does and does not guarantee — the badges bound **provenance**, never correctness:

| badge | label | tooltip |
|---|---|---|
| محقّق | «معطى محقّق» | «معطى محقّق من الإعراب/الصرف» |
| مُولَّد | «مُولَّد» | «مُولَّد ومُسنَد إلى شواهد، غير مُحقَّق» |
| تأويلي | «تأويلي» | «تأويلي: إطار نظري مُختلَف فيه (دلالة الحروف / المقارنة البلاغية)» |

A تأويلي claim SHALL NOT be visually confusable with a محقّق one: the two SHALL differ in **label
text**, not only in colour or tone, so the distinction survives greyscale rendering and
colour-blindness. Any generated block that has not been reviewed SHALL additionally display the
«غير مُحقَّق» mention.

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

#### Scenario: A generated claim can never carry محقّق

- **WHEN** any generated claim is produced for a word, in any page of the product
- **THEN** it carries either «مُولَّد» or «تأويلي»
- **AND** never «معطى محقّق», irrespective of its citations

#### Scenario: A fact and an interpretation about the same item stay separate

- **WHEN** an item carries both an established fact and an interpretive reading (e.g. a letter's
  صفات and its دلالة)
- **THEN** they are rendered as two claims with two badges
- **AND** they are never merged into one sentence under one badge

#### Scenario: The three badges state what they do and do not guarantee

- **WHEN** any badge is rendered in either page
- **THEN** it shows its specified label and tooltip
- **AND** the مُولَّد tooltip states «غير مُحقَّق»
- **AND** the تأويلي tooltip names the interpretive framework
- **AND** the three labels and the three tooltips are pairwise distinct

#### Scenario: تأويلي is distinguishable from محقّق without colour

- **WHEN** a تأويلي claim and a محقّق claim are rendered in the same view
- **THEN** their badge label texts differ
- **AND** the distinction does not depend on colour or tone alone

#### Scenario: An un-reviewed generated block says it is unverified

- **WHEN** a generated block has not been reviewed
- **THEN** the «غير مُحقَّق» mention is displayed on that block

## ADDED Requirements

### Requirement: The fiche fields consumed by Tahlil are a stability contract

The per-word fiche is now a composition source for a second page. The fields `mizan` (with `wazn`,
`bab`, `verified`, `root_class`, `rules`), `root`, `lemma`, `features`, `segments`, `iraab_ar`,
`marker_ar`, `head_ref` and `nazair` SHALL keep their names, types and semantics. They MAY be
extended with additive optional fields; they SHALL NOT be renamed, re-typed, or given a different
meaning without a delta spec recording the change.

A consumer SHALL be able to obtain these fields by calling the existing per-word assembler, and the
assembler SHALL NOT require an LLM, a network call, or a running service to produce them.

#### Scenario: Field shape is stable across the change

- **WHEN** the per-word fiche is assembled before and after a change to a consuming page
- **THEN** the listed fields keep their names and types
- **AND** any addition is optional with a safe default

#### Scenario: The assembler stays importable without a service

- **WHEN** the per-word assembler is imported in a bare Python process
- **THEN** it produces the fiche for a given word with no network access and no model loaded
