# qlisan-word-analysis Specification

## Purpose
TBD - created by archiving change fix-qlisan-fiche-display. Update Purpose after archive.
## Requirements
### Requirement: Fiche labels and values are Arabic-only for every word in the corpus

The QLisan per-word fiche SHALL render every label and every value in Arabic. No
Latin/Buckwalter/QAC code SHALL be visible in the rendered fiche for **any** word in
the corpus. A single deterministic tag→Arabic mapping SHALL be the source of truth,
covering **every feature key present in the corpus** — `nominal_case`, `gender`,
`number`, `nominal_state`, `person`, `pgn`, `verb_aspect`, `verb_form`, `verb_mood`,
`verb_voice`, `derived_nouns`, `special_group` — both the key (its Arabic row label)
and its values, plus the segment codes. An unmapped code SHALL cause a test failure
and SHALL NOT be rendered as a raw passthrough. Part of speech SHALL be shown from the
already-populated `pos_ar` (no separate POS table).

#### Scenario: No Latin token in any rendered level, swept corpus-wide

- **WHEN** the صرفي and نحوي levels are assembled for every word in the corpus
- **THEN** no display field contains an ASCII-letter tag from the QAC feature set
  (no `N`/`PN`/`V`/`ADJ`/`P`, no `NOM`/`ACC`/`GEN`, no `M`/`F`/`S`/`D`/`P`,
  no `DEF`/`INDEF`, no `pgn`, no `IMPF`/`PERF`/`IMPV`, no `(II)`…`(XII)`,
  no `MOOD:JUS`/`MOOD:SUBJ`, no `PASS`, no `ACT_PCPL`/`PASS_PCPL`/`VN`,
  no `SP:`-prefixed Buckwalter)
- **AND** the part of speech shows only its Arabic form (e.g. اسم, not «اسم N»)

#### Scenario: Verb feature columns are shown in Arabic

- **WHEN** the صرفي level is assembled for a verb carrying `verb_aspect`, `verb_form`,
  `verb_mood`, or `verb_voice` (e.g. 13:12:7 ويُنشئُ: aspect IMPF, form (IV))
- **THEN** each such value is displayed via its Arabic mapping (IMPF→مضارع,
  (IV)→الوزن الرابع, MOOD:JUS→مجزوم, PASS→مبني للمجهول)
- **AND** no verb feature code appears untranslated

#### Scenario: special_group Buckwalter is stripped and translated

- **WHEN** the صرفي level is assembled for a word carrying `special_group`
  (e.g. SP:kaAn / SP:<in~ / SP:kaAd)
- **THEN** the value is shown in Arabic (من أخوات كان / من أخوات إنّ / من أخوات كاد)
- **AND** no `SP:`-prefixed Buckwalter string is visible

#### Scenario: Feature row labels are Arabic, not the raw key

- **WHEN** any feature row is rendered
- **THEN** the row label is the Arabic key label (e.g. الحالة الإعرابية, الجنس,
  العدد, الزمن), never the raw key (`nominal_case`, `gender`, `pgn`, …)

#### Scenario: Every enumerated feature value maps to Arabic

- **WHEN** the fiche is assembled for a word carrying a `nominal_case`, `gender`,
  `number`, or `state` feature
- **THEN** each such value is displayed via its Arabic mapping
  (NOM→مرفوع / ACC→منصوب / GEN→مجرور; M→مذكّر / F→مؤنّث; S→مفرد / D→مثنّى / P→جمع;
  DEF→معرفة / INDEF→نكرة)
- **AND** no enumerated code appears untranslated

#### Scenario: person-gender-number is decomposed, not shown raw

- **WHEN** a word record carries a `pgn` feature (any of its 25 forms, including
  gender-only `M`/`F`, number-only `P`, or person-prefixed `2D`/`3MS`)
- **THEN** it is decomposed by character set into readable Arabic person/gender/number
  fields
- **AND** «pgn: …» never appears as a raw chip
- **AND** a value already present as a standalone gender/number/person feature is not
  duplicated

### Requirement: Morphological structure row is labelled البنية الصرفية

The row that lists morphological segments (STEM / PREFIX / SUFFIX) SHALL be labelled
«البنية الصرفية» (not «المقاطع»), and its values SHALL be shown in Arabic
(STEM→جذع, PREFIX→بادئة, SUFFIX→لاحقة). The term «مقاطع» SHALL be reserved for the
future صوتي (phonetic) syllable level and SHALL NOT label morphological segments.

#### Scenario: Segments shown under the correct Arabic label

- **WHEN** the صرفي level of a segmented word (e.g. السحاب at 13:12:8, PREFIX+STEM) is
  rendered
- **THEN** the segments row is labelled «البنية الصرفية»
- **AND** its values read بادئة / جذع (not PREFIX / STEM)
- **AND** the label «المقاطع» does not appear on the صرفي level

### Requirement: The verified badge covers only verbatim fields

The صرفي and نحوي levels SHALL display the «معطى محقّق» (verified) badge only over
data taken verbatim from the parsed corpus (morphology fields, the relation function
name, the case name), served deterministically with no LLM on the path. A **derived**
field — specifically the case marker (العلامة), which is a heuristic mapping and is
wrong for sound-plural / dual / diptote classes — SHALL NOT be covered by the badge; it
SHALL be presented as a distinct «الأصل» hint and SHALL be omitted (never fabricated)
where the primary marker is unreliable.

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

### Requirement: A contested root is shown as a note, outside the verified badge

The صرفي level SHALL display, for a word whose arbitrated root set carries an alternate, a readable
note naming both readings — e.g. «الجذر الأساسي: أنس، ويُقرأ أيضًا: نوس». A study tool surfaces a
scholarly dispute rather than hiding it behind a silent pick.

The note SHALL sit **outside** the «معطى محقّق» badge: an arbitrated root is a decision between two
resources, not a field taken verbatim from one. A word whose root is uncontested SHALL show no
note and SHALL keep the badge over its root, as today.

The note SHALL NOT replace or demote the primary root in the fiche: the primary stays the
displayed root, the alternate is additional information.

#### Scenario: Contested root shows both readings

- **WHEN** the صرفي level is rendered for 2:8:2 ٱلنَّاسِ (primary `أنس`, alternate `نوس`)
- **THEN** the displayed root is `أنس`
- **AND** a note names `نوس` as the alternate reading
- **AND** the note is rendered outside the «معطى محقّق» badge

#### Scenario: Uncontested root shows no note

- **WHEN** the صرفي level is rendered for 1:1:1 بِسْمِ (root `سمو`, no alternate)
- **THEN** no alternate-reading note appears
- **AND** the root keeps the «معطى محقّق» badge

#### Scenario: Restored spelling is what the fiche shows

- **WHEN** the صرفي level is rendered for 22:23:19 وَلُؤْلُؤًا
- **THEN** the displayed root is `لؤلؤ`
- **AND** neither `لالا` nor `لولو` appears anywhere in the fiche

### Requirement: A fused compound says so on the صرفي level

The صرفي level SHALL indicate, for a word carrying the fused-compound marker, that the root belongs
to one segment of a welded form rather than to the whole word — e.g. «كلمة مركّبة: الجذر يخصّ
المقطع أيّ». The indication SHALL be consistent with the البنية الصرفية segment row already
rendered, and SHALL sit outside the «معطى محقّق» badge, being a derived reading of the segment
structure rather than a verbatim field.

A word with no marker SHALL show no such indication.

#### Scenario: Fused vocative is announced

- **WHEN** the صرفي level is rendered for 2:21:1 يَٰٓأَيُّهَا (root `أيي` borne by the segment أَيُّ)
- **THEN** the fiche states that the word is a compound and that the root belongs to that segment
- **AND** the statement sits outside the «معطى محقّق» badge

#### Scenario: Ordinary word carries no compound notice

- **WHEN** the صرفي level is rendered for a آية / ءايات occurrence (same root `أيي`, single unit)
- **THEN** no compound notice appears
- **AND** the root is presented as covering the whole word

#### Scenario: A correctly-rooted vocative compound carries no notice

- **WHEN** the صرفي level is rendered for يَٰقَوْمِ (root `قوم`, the same welded shape as يَٰٓأَيُّهَا
  but not on the marker list)
- **THEN** no compound notice appears
- **AND** the root `قوم` is presented as the word's own root

