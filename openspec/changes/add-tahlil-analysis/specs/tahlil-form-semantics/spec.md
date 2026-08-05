## ADDED Requirements

### Requirement: A versioned دلالة الصيغة knowledge base supplies the morphological and temporal readings

The system SHALL ship a versioned, curated knowledge base mapping form features to their
grammatical sense, keyed on the deterministic values already present in the corpus:

- **الباب / الوزن** — e.g. المفاعلة → المشاركة، المبالغة، طلب الفعل; الاستفعال → الطلب، التحوّل
  والصيرورة، اعتقاد الصفة; التفعيل → التكثير; الافتعال → الاتخاذ والمطاوعة; الانفعال → المطاوعة
  (the one genuinely single-sense باب among these, and therefore the spec's single-sense example).
- **الزمن والصيغة النحوية** — المضارع → التجدّد والاستمرار; الماضي → الثبوت والتحقّق; الأمر →
  الطلب.
- **الصيغة الصرفية المشتقّة** — اسم الفاعل → الحدوث; صيغة المبالغة → الكثرة; المصدر → الحدث
  المجرّد.

Every row SHALL carry a stable id, a named صرف/نحو/بلاغة provenance, and the file SHALL carry a
version string that participates in the analysis cache key. A row SHALL NOT ship without a
provenance, and a KB file without a version SHALL fail to load.

Because a row can list several senses for one form, the KB SHALL express them as alternatives to be
selected in context, not as a single asserted meaning.

#### Scenario: The pinned word matches a باب row

- **WHEN** the صرفي block is assembled for 23:61:2 (باب `فَاعَلَ`, form III)
- **THEN** the المفاعلة row is matched
- **AND** the resulting claim cites that row id and the KB version
- **AND** the claim is badged مُولَّد, never محقّق.

#### Scenario: A KB row without provenance fails the load

- **WHEN** the KB contains a row with no provenance field
- **THEN** the loader raises
- **AND** no analysis is produced from that KB.

#### Scenario: Nominal words are served by the same KB

- **WHEN** the صرفي block is assembled for a noun with no باب (e.g. `سَرِيع`, صيغة مبالغة/صفة
  مشبهة)
- **THEN** the KB is consulted on the mīzān and the derived-noun feature instead of the باب
- **AND** a claim is produced or the block states that no form row matched.

### Requirement: The contextual sense of the form is selected, and the selection is justified

Where a form carries several possible senses, the generated تعليل SHALL state which one holds in
this verse and SHALL cite the evidence for the selection — a naẓīr showing the same form used the
same way, or a syntactic fact of the verse's own context. A تعليل that lists the KB alternatives
without selecting one SHALL be treated as unselected and SHALL be logged.

#### Scenario: An unselected reading is logged

- **WHEN** a generated form تعليل enumerates KB senses without committing to one
- **THEN** the coverage log records reason `form-sense-unselected`.

### Requirement: Selecting one sense from a multi-sense row is مُولَّد only when a corpus disambiguator is cited

Citing a KB row proves that a sense **exists in the knowledge base**; it never proves that **this**
sense holds in **this** verse. Selecting one alternative from a multi-sense row is therefore an
interpretive act, and the badge SHALL reflect how the selection is anchored:

- a **single-sense** row ⇒ **مُولَّد** (the citation settles the claim; nothing is chosen);
- a **multi-sense** row whose claim also cites a **corpus disambiguator** — a naẓīr of the same
  lemma showing the form used the same way, or a syntactic fact of this verse's context ⇒
  **مُولَّد**;
- a **multi-sense** row with **no** disambiguator among the citations ⇒ **downgraded to تأويلي**,
  and logged with reason `sense-selection-unanchored`.

The unanchored case SHALL be **downgraded, not dropped** — the reading may well be right and is
worth showing, but it SHALL NOT carry the badge of a corpus-anchored claim. This is the only
downgrade in the citation gate; every other failed check drops the claim.

#### Scenario: المفاعلة is read as المبالغة with a corpus disambiguator

- **WHEN** the صرفي تعليل for 23:61:2 states that the مفاعلة here is not on its base sense of
  المشاركة but conveys المبالغة/التكلّف in seeking precedence, citing the multi-sense المفاعلة row
  **and** at least one naẓīr of the same lemma (or a syntactic fact of the verse)
- **THEN** the claim is badged مُولَّد
- **AND** no `sense-selection-unanchored` entry is logged for it.

#### Scenario: The same selection without a disambiguator is downgraded, not dropped

- **WHEN** the same claim cites only the multi-sense المفاعلة row
- **THEN** the claim is still rendered
- **AND** it is badged تأويلي, not مُولَّد
- **AND** the coverage log records reason `sense-selection-unanchored`.

#### Scenario: A single-sense row needs no disambiguator

- **WHEN** a claim cites a KB row carrying exactly one sense (e.g. الانفعال → المطاوعة)
- **THEN** it is badged مُولَّد with no disambiguator required
- **AND** the example is deliberately not الاستفعال, which is genuinely multi-sense
  (الطلب / التحوّل والصيرورة / اعتقاد الصفة) and therefore SHALL ship as a multi-sense row.

### Requirement: The contrastive «أبلغ من X» is licensed in exactly two flavours, both machine-checked

A contrast SHALL be drawn only from a versioned contrast table of opposed أبواب/صيغ for the same
root (e.g. فاعَلَ ↔ أفعَلَ ↔ فعَّلَ), and its attestation status SHALL be computed by the system,
never asserted by the generator.

**Attestation SHALL be computed at the granularity of the candidate — the `(lemma, POS/باب)` pair —
and SHALL NOT be computed at the granularity of the root.** A candidate counts as attested **iff
the corpus contains a word of that lemma *and* of that باب/POS**. A noun, an elative, or a
participle sharing the root SHALL NEVER count as attesting a verb of a given باب, and a verb SHALL
never count as attesting a nominal form. A root-level check would invert the verdict on the pinned
word and turn a true claim into a false one.

1. **Attested contrast** — a word of that lemma and that باب/POS occurs in the Quran. The claim
   SHALL cite the occurrence ref.
2. **Unattested contrast** — the alternative is a well-formed form of the same root with no word of
   that باب/POS in the corpus. The claim SHALL say so explicitly **at the same granularity** —
   naming the باب/POS that is missing, not merely the root — and the absence SHALL be verified
   against the corpus lemma index together with the POS/باب of each occurrence.

A contrast form that appears in a generated claim without having been produced by the contrast
table and checked for attestation SHALL be dropped. Both flavours SHALL be badged تأويلي.

**The absence sentence SHALL be verified by exact containment, not by pattern-matching Arabic.**
The evidence layer computes the correct sentence for each candidate («ولم ترد صيغة أَفْعَلَ فعلاً
من هذا الجذر»); the gate SHALL require that exact text to be present in the claim, and SHALL NOT
accept a generic absence marker. A marker denylist is defeated two ways, both demonstrated against
the shipped gate: a claim may state the absence at the **wrong granularity** («ولم ترد أفعَلَ من
هذا الجذر» — false for سرع, since أَسْرَع exists as an اسم تفضيل), or it may **deny** the absence
and still match the marker («لا يصحّ أن يقال إنّ صيغة أفعَلَ لم ترد، فقد وردت»). Requiring the
computed sentence verbatim removes both, and removes natural-language matching from the trust path
entirely.

**Each contrast candidate SHALL be independently citable.** An id covering several targets cannot
carry one honest attestation boolean, because their verdicts differ.

#### Scenario: An absence stated at the wrong granularity is dropped

- **WHEN** a claim cites an unattested contrast candidate and states «ولم ترد أفعَلَ من هذا الجذر»
  (naming the root, not the باب/POS)
- **THEN** the claim is dropped with reason `unchecked-contrast`
- **AND** it is kept only when it contains the candidate's own computed absence sentence.

#### Scenario: A claim denying the absence cannot satisfy the check

- **WHEN** a claim contains an absence marker inside a sentence that asserts the form DOES occur
- **THEN** the claim is dropped
- **AND** the gate's verdict does not depend on interpreting the Arabic.

#### Scenario: A mixed contrast item cannot license a false absence

- **WHEN** a root's contrast candidates have differing verdicts (measured: 6 992 of 19 356 verbs),
  e.g. root عبد where فَعَّلَ is attested at 26:22:6 and أَفْعَلَ is not
- **THEN** each candidate is a separate citable item with its own verdict and its own absence
  sentence
- **AND** a claim citing the attested candidate cannot state that it is absent.

#### Scenario: A same-root elative does not attest the verb of that باب

- **WHEN** the contrast is generated for 23:61:2 against the أفعَلَ **verb** (يُسرِعون), and the
  corpus contains أَسْرَع of the same root as an **اسم تفضيل** (6:62 «أَسْرَعُ الْحَاسِبِينَ»)
- **THEN** the candidate's attestation is `False`
- **AND** the presence of the elative does not flip it to attested
- **AND** the claim's «verified-absent» condition holds.

#### Scenario: The pinned word's contrast states the absence at the right granularity

- **WHEN** that same unattested contrast is rendered
- **THEN** the claim states that the أفعَلَ form does not occur **as a verb** of this root
  («ولم ترد صيغة أفعَلَ فعلاً من هذا الجذر»)
- **AND** it does not claim that أفعَلَ is absent from the root outright, which would be false
- **AND** the claim is badged تأويلي.

#### Scenario: An attested contrast cites its occurrence

- **WHEN** a word of the contrast candidate's lemma and باب/POS does occur in the Quran
- **THEN** the claim cites at least one occurrence ref
- **AND** the ref resolves in the corpus
- **AND** the cited occurrence carries that same باب/POS.

#### Scenario: An unchecked contrast form is dropped

- **WHEN** a generated claim names a contrast form that is not in the contrast table for this root
- **THEN** the claim is dropped
- **AND** the coverage log records reason `unchecked-contrast`.

#### Scenario: No contrast candidate means no contrastive clause

- **WHEN** the root has no contrast candidate at all (measured: 5 386 rooted words have no other
  attested lemma)
- **THEN** no contrastive clause is emitted
- **AND** the rest of the صرفي block is unaffected.

### Requirement: The verb-mood marker is derived deterministically and badged محقّق

The system SHALL derive العلامة for verbs from the corpus, extending the existing nominal case
marker without altering it:

- an imperfect verb with no `verb_mood` tag is **مرفوع**, and when its person-gender-number is one
  of الأفعال الخمسة the marker is **ثبوت النون**;
- `MOOD:JUS` is **مجزوم**, marked **بحذف النون** for الأفعال الخمسة;
- `MOOD:SUBJ` is **منصوب**, marked **بحذف النون** for الأفعال الخمسة.

Measured: 5 582 imperfect verbs untagged (مرفوع), 1 418 `MOOD:JUS`, 1 330 `MOOD:SUBJ`; **3 569**
carry an أفعال خمسة pgn, of which **2 594** are مرفوع (corrected from 3 567/2 593, which omitted
the `2FD` pgn — 55:50:3 «عَيْنَانِ تَجْرِيَانِ» and 66:4:9 «وَإِن تَظَٰهَرَا», both ألف الاثنين).
Where the marker does not derive cleanly it SHALL be omitted, never guessed. This is a
deterministic derivation and SHALL be badged محقّق.

Omission is **required**, not optional, wherever the mood tag alone would yield a confident wrong
answer. The system SHALL omit rather than assert for: a verb carrying نون النسوة (مبني على السكون,
though QAC tags a *maḥallī* mood on some); a verb carrying نون التوكيد (مبني, its نون الرفع
deleted, so an أفعال خمسة pgn would wrongly yield «ثبوت النون»); a معتلّ الآخر jussive (marked by
حذف حرف العلة, not السكون); and any word whose QAC mood tag contradicts its own surface. Every such
omission SHALL be counted, and the emitted-marker total SHALL reconcile with the corpus total minus
the guarded words, so the gap is auditable rather than assumed.

#### Scenario: A verb whose surface contradicts its mood tag is omitted

- **WHEN** the marker is derived for an أفعال خمسة verb tagged `MOOD:JUS` whose نون is still
  present on the surface (e.g. 2:272:28 تُظْلَمُونَ)
- **THEN** no marker is emitted
- **AND** the word is counted in the guarded set, so the emitted total reconciles with the corpus
  total minus the guards.

#### Scenario: The pinned word gets ثبوت النون

- **WHEN** the نحوي block is assembled for 23:61:2 (imperfect, no `verb_mood`, pgn 3MP)
- **THEN** العلامة reads «مرفوع وعلامته ثبوت النون»
- **AND** it is badged محقّق
- **AND** it is produced without any LLM call.

#### Scenario: A jussive verb of الأفعال الخمسة is مجزوم بحذف النون

- **WHEN** the block is assembled for an imperfect verb tagged `MOOD:JUS` with an أفعال خمسة pgn
- **THEN** العلامة states مجزوم وعلامته حذف النون.

#### Scenario: The nominal case marker is unchanged

- **WHEN** the marker is computed for any nominal word
- **THEN** the value is identical to the one the existing case-marker path produced before this
  change.

### Requirement: The نحوي reading consumes the Zero relation layer and omits it when absent

Where the Zero-theory fields (relation among إسناد/تخصيص/إضافة/توضيح, role, and السبب) are present
on the word, the نحوي block SHALL present them and SHALL build its تعليل on top of them, preserving
their own verification flag: a relation flagged unverified SHALL NOT be presented as محقّق. Where
they are absent, the block SHALL omit the relation line, log it, and still render the iʿrāب,
العلامة and المتعلَّق.

#### Scenario: The relation renders when the layer is present

- **WHEN** the word carries a verified Zero relation and السبب
- **THEN** both are rendered, badged محقّق
- **AND** the generated تعليل may cite them.

#### Scenario: The block still works when the layer is absent

- **WHEN** the Zero fields are absent from the word's fiche
- **THEN** the نحوي block still renders الموقع الإعرابي, العلامة and المتعلَّق
- **AND** no relation is fabricated
- **AND** the coverage log records reason `zero-layer-absent`.

#### Scenario: An unverified relation is not badged محقّق

- **WHEN** the word carries a Zero relation flagged unverified (a minted marker)
- **THEN** it is rendered with a non-محقّق treatment.
