## ADDED Requirements

### Requirement: The index serves the arbitrated root in its exact spelling

`qac_words.json` and `root_graph.json` SHALL carry the arbitrated root set produced by the
`root-attribution` capability, not the treebank's raw root column. The `root` field SHALL hold the
exact QAC spelling, any alternate SHALL be exposed alongside it, and the graph SHALL index a word
under its primary **and** its alternates so that no reachability depends on which reading is
believed.

Folding SHALL remain available as a lookup key but SHALL NOT be the stored value. This closes the
gap where the index carried 0 hamzated roots out of 1642, and where a consumer walking root
radicals — `analysis/mizan.py` computing the الميزان الصرفي — walked `لالا` instead of `لؤلؤ`.

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

## MODIFIED Requirements

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
