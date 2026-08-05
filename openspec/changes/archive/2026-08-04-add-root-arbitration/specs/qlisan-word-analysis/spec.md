## ADDED Requirements

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
