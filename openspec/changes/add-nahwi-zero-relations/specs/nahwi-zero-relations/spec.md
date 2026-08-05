## ADDED Requirements

### Requirement: Every word's Zero relation is one of exactly four, derived from the treebank

The نحوي level SHALL expose, for each word it can derive one for, a **relation** drawn from
exactly four values — إسناد / تخصيص / إضافة / توضيح — derived deterministically (no LLM, no
network, no precomputed file) from the QAC role already stored in `qac_syntax.json` together with
the word's morphology in `qac_words.json`. The derivation SHALL happen on the fly in the assembler,
and SHALL NOT modify, re-ingest, or extend the QAC artifacts on disk.

The relation SHALL be decided by **case family**, not by a per-label table: رفع → إسناد,
نصب → تخصيص, جر → إضافة. The case family SHALL be obtained from
`qac_labels.relation_canonical_case`, so that اسم/خبر of the كان-family and the إنّ-family resolve
by family (اسم كان مرفوع → إسناد، خبر كان منصوب → تخصيص، اسم إنّ منصوب → تخصيص، خبر إنّ مرفوع →
إسناد) rather than from a duplicated role list.

#### Scenario: A مرفوع relatum maps to إسناد

- **WHEN** the fiche is assembled for 2:7:2 ٱللَّهُ (QAC «فاعل», `nominal_case` NOM)
- **THEN** the relation is «إسناد»
- **AND** the same holds for a مبتدأ, a نائب فاعل, an اسم كان, and a خبر إنّ.

#### Scenario: A منصوب relatum maps to تخصيص

- **WHEN** the fiche is assembled for 1:6:2 ٱلصِّرَٰطَ (QAC «مفعول به», `nominal_case` ACC)
- **THEN** the relation is «تخصيص»
- **AND** a حال, a تمييز, a مفعول مطلق, a مستثنى, an اسم إنّ and a خبر كان map to «تخصيص» likewise.

#### Scenario: A مجرور relatum maps to إضافة

- **WHEN** the fiche is assembled for 1:1:2 ٱللَّهِ (QAC «مضاف إليه») or for 1:2:2 لِلَّهِ
  (QAC relation `gen`)
- **THEN** the relation is «إضافة» in both cases.

#### Scenario: Case family, not a role table, resolves كان vs إنّ

- **WHEN** the fiche is assembled for 10:19:3 ٱلنَّاسُ (QAC «اسم كان», NOM) and for
  10:19:5 أُمَّةً (QAC «خبر كان», ACC)
- **THEN** ٱلنَّاسُ is «إسناد» and أُمَّةً is «تخصيص»
- **AND** the two verdicts come from the canonical case of each role, not from a hardcoded mapping
  of the strings «اسم كان» / «خبر كان».

### Requirement: تبعية maps to توضيح by relation, never by case

A تابع inherits its متبوع's case, so its case family SHALL NOT decide its relation. QAC relations
`Adj` (نعت/صفة), `App` (بدل), `conj` (عطف نسق) and `emph` (توكيد) SHALL be matched **before** the
case-family lookup and SHALL map to «توضيح» with the role «تابع».

#### Scenario: A genitive نعت is توضيح, not إضافة

- **WHEN** the fiche is assembled for 1:1:3 ٱلرَّحْمَٰنِ (QAC «صفة», `nominal_case` GEN, agreeing
  with the مجرور it qualifies)
- **THEN** the relation is «توضيح» and the role is «تابع»
- **AND** it is not «إضافة», despite the genitive case.

#### Scenario: توكيد and بدل are توضيح

- **WHEN** the fiche is assembled for a word tagged `emph` («توكيد») or `App` («بدل»),
  e.g. 1:2:3 رَبِّ (بدل)
- **THEN** the relation is «توضيح» and the role is «تابع».

### Requirement: Verbs and particles are markers of a relation, not relata

A verb SHALL be presented as **مسند**, the pole of الإسناد, carrying no case. A حرف جر SHALL be
presented as **أداة الإضافة** and a حرف نصب as **أداة التخصيص**. These SHALL receive a relation and
a role but SHALL NOT receive a السبب line, because they bear no case mark to explain, and the
system SHALL NOT fabricate a reason in its place.

The verb rule SHALL key on the part of speech (`V`), not on the QAC relation `root` — QAC's `root`
marks the first element of the sentence, and only 4 751 of its 12 879 occurrences are verbs.

#### Scenario: A verb is مسند whatever its QAC relation

- **WHEN** the fiche is assembled for 10:19:7 فَٱخْتَلَفُوا۟ (POS `V`, QAC relation `root`)
- **THEN** the relation is «إسناد» and the role is «مسند»
- **AND** the same verdict is produced for a verb whose QAC relation is `صلة`, `معطوف`, `شرط` or
  `نفي` — e.g. 2:3:2 يُؤْمِنُونَ (`صلة`) is also «إسناد / مسند»
- **AND** no السبب line is emitted for either.

#### Scenario: A حرف جر is displayed as أداة الإضافة, not as a relatum

- **WHEN** the fiche is assembled for 2:2:5 فِيهِ (POS `P`, QAC «متعلق»)
- **THEN** the relation is «إضافة» and the role is «أداة الإضافة»
- **AND** no السبب is emitted
- **AND** the word is never given a relatum role such as «مضاف إليه».

#### Scenario: A حرف نصب marks التخصيص

- **WHEN** the fiche is assembled for 2:6:1 إِنَّ (POS `ACC`)
- **THEN** the relation is «تخصيص» and the role is «أداة التخصيص»
- **AND** no السبب is emitted.

### Requirement: الدور preserves the classical function under the relation

The role SHALL be one of مسند / مسند إليه / مخصِّص / مضاف إليه / مجرور بأداة الإضافة / تابع /
أداة الإضافة / أداة التخصيص / أداة العطف, derived from the QAC role. Under إضافة the role SHALL
distinguish the two forms the theory itself names: a QAC `Poss` relation SHALL yield «مضاف إليه»
(الإضافة المباشرة) and any other genitive SHALL yield «مجرور بأداة الإضافة» (الإضافة بواسطة أدوات
الإضافة). Under إسناد, a role whose name begins with «خبر» SHALL yield «مسند» and every other
SHALL yield «مسند إليه».

#### Scenario: Direct إضافة and إضافة by particle are distinguished

- **WHEN** the fiche is assembled for 1:1:2 ٱللَّهِ (QAC `Poss`) and for 1:2:2 لِلَّهِ (QAC `gen`)
- **THEN** ٱللَّهِ has role «مضاف إليه» and لِلَّهِ has role «مجرور بأداة الإضافة»
- **AND** the two are never collapsed onto the same role.

#### Scenario: خبر is مسند, فاعل is مسند إليه

- **WHEN** the fiche is assembled for 2:5:8 ٱلْمُفْلِحُونَ (QAC «خبر») and for 2:7:2 ٱللَّهُ
  (QAC «فاعل»)
- **THEN** ٱلْمُفْلِحُونَ has role «مسند» and ٱللَّهُ has role «مسند إليه»
- **AND** both carry the relation «إسناد».

### Requirement: The السبب line states why the word carries its mark

For a relatum, the system SHALL emit a single السبب line naming the case, the relation, and the
classical fine role, in one of exactly two forms:

- **معرب** (the word has a `nominal_case`): `{case_word} لأنه {relation} ({fine_role})` —
  e.g. «منصوب لأنه تخصيص (مفعول به)».
- **مبني** (no `nominal_case`): `في محلّ {case_noun} لأنه {relation} ({fine_role})` —
  e.g. «في محلّ نصب لأنه تخصيص (مفعول به)».

`{fine_role}` SHALL be the existing display form of the QAC role
(`qac_labels.relation_ar_display`), so the classical i'rāb function is preserved verbatim inside
the theory sentence. The العلامة SHALL NOT be duplicated into the نحوي card and SHALL NOT be
re-worded; it stays in the صرفي card as it is today.

#### Scenario: A معرب word gets the case-word form

- **WHEN** the fiche is assembled for 1:6:2 ٱلصِّرَٰطَ (QAC «مفعول به», ACC)
- **THEN** the السبب reads «منصوب لأنه تخصيص (مفعول به)».

#### Scenario: A مبني word gets the في محلّ form

- **WHEN** the fiche is assembled for 1:5:1 إِيَّاكَ (QAC «مفعول به», a مبني pronoun with no
  `nominal_case`)
- **THEN** the السبب reads «في محلّ نصب لأنه تخصيص (مفعول به)»
- **AND** no lafẓī case word is asserted for it.

#### Scenario: A marker gets no السبب

- **WHEN** the fiche is assembled for a verb, a حرف جر or a حرف نصب
- **THEN** the السبب field is absent
- **AND** no placeholder reason is emitted in its place.

### Requirement: A relation that does not derive cleanly is omitted and logged, never invented

The system SHALL NOT emit a relation it cannot derive. Specifically:

1. **A relatum must be able to bear a case** — its POS SHALL be in {N, PN, ADJ, PRON, REL, DEM, T,
   LOC} or it SHALL carry a `nominal_case`. A حرف SHALL NEVER be made a relatum.
2. **A case conflict SHALL omit** — when the role's canonical case disagrees with the word's actual
   `nominal_case`, the relation, role and reason SHALL all be omitted (the same guard
   `_compose_iraab` already applies to the case word).
3. **A حرف جر carrying a nominal-slot relation SHALL omit** — a `P` tagged `Subj`, `Pass`, `Pred`,
   `Obj`, `Poss`, `Spec`, `circ` or an إنّ/أن family relation heads a شبه جملة filling that slot and
   SHALL NOT be labelled a bare أداة الإضافة.

Every omitted word SHALL be recorded in a coverage log carrying at least the ref, the word, the QAC
`relation`, the QAC `relation_ar`, and the reason for omission, so the omitted set can be triaged.

#### Scenario: A negation particle tagged حال is not made a relatum

- **WHEN** the fiche is assembled for 2:2:3 لَا (POS `NEG`, QAC relation `circ`/«حال»)
- **THEN** no relation, role or السبب is emitted
- **AND** the word appears in the coverage log with reason `non-nominal-pos`
- **AND** it is never shown as «تخصيص / مخصِّص».

#### Scenario: A QAC case conflict omits rather than resolving

- **WHEN** the word's QAC role is «مفعول به» (canonical ACC) but its `nominal_case` is NOM
- **THEN** no Zero relation is emitted
- **AND** the word is logged with reason `case-conflict`
- **AND** the existing `iraab_ar` still renders the function name alone, unchanged.

#### Scenario: A preposition in a nominal slot omits

- **WHEN** the fiche is assembled for 1:7:7 عَلَيْهِمْ (POS `P`, QAC «نائب فاعل»)
- **THEN** no Zero relation is emitted
- **AND** the word is logged with reason `prep-in-nominal-slot`.

#### Scenario: Omission never removes the existing i'rāb

- **WHEN** any word's Zero relation is omitted
- **THEN** the نحوي level still renders its existing الموقع الإعرابي and المتعلَّق
- **AND** `available` is unchanged by the Zero layer.

### Requirement: Standalone عطف particles get a minted marker that is not «معطى محقّق»

The 754 standalone CONJ words absent from `qac_syntax.json` SHALL receive a minted marker row —
relation «توضيح», role «أداة العطف», no السبب — so a reader selecting a و or ف is not shown an
empty level. Because no QAC role backs this assertion, the row SHALL be visibly distinguished from
verified data and SHALL NOT carry the «معطى محقّق» badge, and it SHALL be enumerated in the
coverage log.

A و/ف that is a **fused prefix** of a word SHALL NOT produce a second relation row on that word's
fiche; the word keeps only its own relation.

#### Scenario: A standalone conjunction shows a non-verified marker row

- **WHEN** the fiche is assembled for a standalone CONJ word absent from the treebank
- **THEN** the relation is «توضيح» and the role is «أداة العطف»
- **AND** the row is flagged as not verified
- **AND** the word is enumerated in the coverage log.

#### Scenario: A fused و prefix adds no second relation

- **WHEN** the fiche is assembled for 2:4:10 وَبِٱلْءَاخِرَةِ (a word whose بادئة includes و and ب)
- **THEN** exactly one relation is emitted, the word's own («إضافة»)
- **AND** no additional عطف relation row is added.

### Requirement: The deterministic mapper carries no LLM on its path

The Zero layer SHALL be computed with pure stdlib, importable and testable without fastapi,
pydantic, Qdrant, or network access. No tier of this capability SHALL call an LLM: an ambiguous or
unmapped edge SHALL be omitted and logged rather than resolved by a model.

#### Scenario: Mapper is importable in isolation

- **WHEN** the mapper module is imported in a bare Python process with no service running
- **THEN** it imports and produces relations for given word/syntax records
- **AND** it makes no network call.

### Requirement: Coverage is measured per relation, not only in aggregate

Acceptance SHALL include inspecting a sample of outputs **for each of the four relations
separately**, in addition to the aggregate coverage rate, because a relation that is confidently
wrong is complete-looking and therefore invisible in the rate. The corpus sweep SHALL report the
coverage split (relatum / marker / minted / omitted), the distribution across the four relations,
and the omission reasons with counts.

#### Scenario: Sweep reports the split and the per-relation distribution

- **WHEN** the corpus-wide coverage sweep is run over all 77 429 words
- **THEN** it reports counts for relatum, marker, minted and omitted buckets
- **AND** it reports how many words fall under each of the four relations
- **AND** it enumerates every omitted word with its reason.

#### Scenario: Per-relation samples are inspected before acceptance

- **WHEN** the coverage results are reviewed
- **THEN** samples are drawn and read for each of إسناد, تخصيص, إضافة and توضيح separately
- **AND** acceptance is not granted on the aggregate rate alone.
