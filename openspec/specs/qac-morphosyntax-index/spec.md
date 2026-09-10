# qac-morphosyntax-index Specification

## Purpose
TBD - created by archiving change fix-qlisan-fiche-display. Update Purpose after archive.
## Requirements
### Requirement: نحوي level presents a safely-composed iʿrāب function and case marker

The نحوي level SHALL present, in the «الموقع الإعرابي» field, the iʿrāب **function**
derived from the QAC dependency relation and case — not the word class. The relation
and case are taken verbatim from the treebank, but SHALL be composed **safely**: the
Arabic function SHALL never contain a Latin/Buckwalter token, never repeat the case
word, and never contradict itself. It SHALL present a «العلامة» field with the derived
case marker (as a distinct «الأصل» hint, not under the verified badge), and retain
«المتعلَّق» pointing to the governing word.

Composition rules:
- A relation whose `relation_ar` is a Latin token (the tree-root relation `root`,
  affecting ~12,897 words) SHALL be mapped to an Arabic label (e.g. «عمدة الجملة») and
  SHALL NOT render the token `root`.
- A relation whose `relation_ar` is itself a case word (the `gen` relation → «مجرور»,
  ~10,510 words) SHALL be rendered as the function «اسم مجرور», never as the stutter
  «مجرور مجرور».
- The case word SHALL be appended only when the relation's canonical case matches the
  word's `nominal_case`; on mismatch (e.g. the ~83 words tagged `Subj` yet labelled
  «مفعول به») the relation function SHALL be shown alone, never as «مفعول به مرفوع».
- An indeclinable (مبني) word — pronoun, relative, demonstrative, conditional, or any
  word with no `nominal_case` — SHALL NOT receive a fabricated lafẓī case marker.
- The marker (العلامة) is the standard mapping of the case (ACC→الفتحة, NOM→الضمة,
  GEN→الكسرة) for a **declinable singular triptote** only, and SHALL be omitted for
  dual / plural / diptote-genitive rather than shown wrong.

#### Scenario: Object noun shows function, marker, and governor

- **WHEN** the نحوي level is assembled for السحاب at 13:12:8 (relation Obj, case ACC,
  head = the verb at word 7, i.e. 13:12:7)
- **THEN** «الموقع الإعرابي» = «مفعول به منصوب»
- **AND** «العلامة» = «الفتحة» (rendered as an «الأصل» hint outside the verified badge)
- **AND** «المتعلَّق» links to 13:12:7
- **AND** the word class (اسم) does not occupy the «الموقع الإعرابي» field
- **AND** no separate «العلاقة» row duplicates «مفعول به»

#### Scenario: Tree-root relation never renders the token "root"

- **WHEN** the نحوي level is assembled for a `root`-relation word (e.g. 1:2:1
  ٱلْحَمْدُ, case NOM)
- **THEN** «الموقع الإعرابي» is an Arabic label (e.g. «عمدة الجملة»)
- **AND** the token «root» never appears

#### Scenario: Genitive relation shows «اسم مجرور», not a stutter

- **WHEN** the نحوي level is assembled for a `gen`-relation word (e.g. 1:1:1 بِسْمِ,
  case GEN)
- **THEN** «الموقع الإعرابي» = «اسم مجرور»
- **AND** «مجرور مجرور» never appears

#### Scenario: Source mislabel is not amplified into a contradiction

- **WHEN** the نحوي level is assembled for a word whose relation and case disagree
  (e.g. 2:80:4 ٱلنَّارُ, tagged relation «مفعول به» yet case NOM)
- **THEN** «الموقع الإعرابي» does not read «مفعول به مرفوع»
- **AND** the relation function is shown alone (the mismatched case word is not
  appended)

#### Scenario: Relation without a nominal case shows the relation alone

- **WHEN** the نحوي level is assembled for a word whose relation carries no
  `nominal_case` (e.g. the verb at 13:12:7, relation conj; or a مبني pronoun)
- **THEN** «الموقع الإعرابي» shows the Arabic relation without an appended case word
- **AND** «العلامة» is omitted rather than fabricated

#### Scenario: Unreliable marker omitted for a genitive sound plural

- **WHEN** the نحوي level is assembled for 1:2:4 ٱلْعَٰلَمِينَ (case GEN, number P)
- **THEN** «العلامة» is omitted (not shown as «الكسرة»)

### Requirement: Naẓāʾir are scoped by lemma, not by bare root

Naẓāʾir (root siblings) SHALL be scoped by **lemma** so that homographs sharing a
root but differing in meaning are not presented as related. When same-lemma siblings
are too few, other lemmas MAY be included but SHALL be grouped and labelled by
distinct lemma, never merged into one undifferentiated list.

The root that scopes the search SHALL be the arbitrated root set: a word's siblings are gathered
under its primary root **and** its alternates, so the sibling set of a contested word does not
change with the reading. Where an alternate contributes occurrences, they SHALL be grouped by
lemma under the same rules as the primary, never presented as a separate, unexplained list.

#### Scenario: Homograph excluded from a noun's naẓāʾir

- **WHEN** naẓāʾir are assembled for السحاب at 13:12:8 (lemma = the noun سَحَاب,
  8 same-lemma siblings)
- **THEN** يُسحبون / يسحبون (verb, same root سحب, different lemma) do not appear in the
  same-lemma group
- **AND** if included at all, they are shown under a separate, lemma-labelled group

#### Scenario: Sparse same-lemma set falls back to lemma-grouped display

- **WHEN** naẓāʾir are assembled for a word whose selected lemma has fewer than the
  threshold (default 3) same-lemma siblings
- **THEN** occurrences of other lemmas under the shared root are included
- **AND** each occurrence carries its lemma and the view groups occurrences by distinct
  lemma so no false semantic proximity is implied

#### Scenario: Contested root yields one sibling set, not two

- **WHEN** naẓāʾir are assembled for 2:8:2 ٱلنَّاسِ (primary `أنس`, alternate `نوس`)
- **THEN** the sibling set covers the occurrences of both roots
- **AND** the same set is produced whichever root the caller queried
- **AND** each occurrence is listed once, grouped by lemma

### Requirement: The index serves the arbitrated root in its exact spelling

`qac_words.json` and `root_graph.json` SHALL carry the arbitrated root set produced by the
`root-attribution` capability, not the treebank's raw root column. The `root` field SHALL hold the
exact QAC spelling, any alternate SHALL be exposed alongside it, and the graph SHALL index a word
under its primary **and** its alternates so that no reachability depends on which reading is
believed.

Folding SHALL remain available as a lookup key but SHALL NOT be the stored value. This closes the
gap where the index carried 0 hamzated roots out of 1642, and where a consumer walking root
radicals — `linguistics/analysis/mizan.py` computing the الميزان الصرفي — walked `لالا` instead of `لؤلؤ`.

The fused-compound marker SHALL travel with the index entry, so a consumer can tell a word whose
root covers the whole word from one whose root covers a segment.

#### Scenario: Index exposes the spelled root and its alternate

- **WHEN** the index entry for 2:8:2 ٱلنَّاسِ is read
- **THEN** the root is `أنس`
- **AND** the alternate `نوس` is present on the same entry
- **AND** the word is reachable in the root graph under both

#### Scenario: Compound and real occurrence are separable in the index

- **WHEN** the root graph is read for `أيي`
- **THEN** the 382 آية / ءايات entries carry no fused-compound marker
- **AND** the 155 يَٰٓأَيُّهَا / يَٰٓأَيَّتُهَا entries carry it
- **AND** a consumer can list one group without the other

#### Scenario: Mīzān walks real radicals

- **WHEN** the الميزان الصرفي is computed for 22:23:19 وَلُؤْلُؤًا
- **THEN** the radicals walked are those of `لؤلؤ`
- **AND** not those of `لالا`

