# letter-physical-primitives Specification

## Purpose

Define the input layer of the physics-first concept engine: which columns of the letter sheet
are in scope and which are banned, how the raw مخرج / صفات strings reduce to a closed feature
vocabulary, the marked/unmarked rule, the capped primitive table, its sourcing gate and its
sha256 freeze.

**The engine this serves is a CLOSED EXPERIMENT** (`k / 40 = 0`, see
`concept-attestation-protocol`). The table stays frozen and shipped; it is not to be widened to
improve the number.

## Requirements

### Requirement: The input layer is the tajwīd description, and nothing interpretive

The physical profile of a letter SHALL be read from `arabic_letters_dataset.csv`'s `makhraj_ar` and
`sifat` columns only. The `ibn_jinni_note` and `ibn_jinni_note_ar` columns of the same file SHALL
NOT be read by any module on this path: they are one frozen interpretive gloss per letter, which is
the defect the whole `/lexical` history exists to remove.

No row of `arabic_letters_dataset.csv` SHALL be added, edited or removed by this capability. The
sheet is read-only input.

#### Scenario: The banned columns cannot be reached

- **WHEN** the source of every module under `linguistics/lisan/concept/` is read statically
- **THEN** none SHALL mention `ibn_jinni_note` or `ibn_jinni_note_ar`
- **AND** a test SHALL assert this so the ban survives a refactor

#### Scenario: The profile is complete for every letter

- **WHEN** the physical profile is requested for each of the 28 letters
- **THEN** each SHALL return its `makhraj_ar` and its parsed `sifat` list
- **AND** no letter SHALL return an empty `sifat` list

### Requirement: Only the marked member of an opposition yields a primitive

The raw `sifat` strings SHALL be reduced to a declared, closed feature vocabulary by a rule stated
over the vocabulary, never over a letter:

- A **privative** opposition, whose one member is defined as the absence of the other — `انفتاح`
  against `إطباق`, `استفال` against `استعلاء` — SHALL yield a feature for the present member only.
  `munfatiha` and `mustafila` therefore yield nothing.
- An **equipollent** opposition, whose members are each a positive articulatory state — `شدة` /
  `توسط` / `رخاوة`, and `جهر` / `همس` — SHALL yield a feature for every member.
- A **صفة لا ضد لها** SHALL yield a feature.
- A value recording a scholarly dispute SHALL yield nothing.

#### Scenario: A near-universal feature is excluded by rule, not by convenience

- **WHEN** the feature vocabulary is derived from the sheet
- **THEN** `munfatiha` (24 of 28 letters) and `mustafila` (21 of 28) SHALL yield no feature
- **AND** the reason recorded SHALL be that each is the absent member of a privative opposition

#### Scenario: A disputed value asserts nothing

- **WHEN** `ء`'s `sifat` is reduced, carrying `mahmusa/majhura (debated)`
- **THEN** that value SHALL yield no feature
- **AND** `ء` SHALL retain `shadida` and therefore exactly one primitive

### Requirement: مخرج is reduced to the five classical zones, and those zones are mapped

The sheet's 18 distinct `makhraj_ar` strings SHALL be reduced to the **five classical zones** —
حلق · أقصى اللسان · وسط اللسان · طرف اللسان · شفتان — and each zone SHALL yield exactly one
primitive. A table keyed on the raw strings would be a per-letter glossary reached by arithmetic;
the reduction is what makes the مخرج a feature rather than a name.

The five zone primitives SHALL assert **position on the inner→outer articulation axis** and nothing
else, each carrying its uncontested locus as `physical_basis`. Reading a meaning off a place is the
banned interpretive layer wearing anatomy.

`حافة اللسان` (`ض`, `ل`) SHALL be grouped with `طرف اللسان`, the front-of-tongue region taken whole.
A sixth zone SHALL NOT be added to separate them, and `الحلق` SHALL NOT be split into its three
classical sub-positions: either move would be choosing the granularity by its result.

Every letter SHALL map to exactly one zone.

#### Scenario: Each letter carries exactly one zone

- **WHEN** the physical profile is requested for each of the 28 letters
- **THEN** each SHALL carry exactly one of the five zone features
- **AND** the spread SHALL be حلق 6 · أقصى اللسان 2 · وسط اللسان 3 · طرف اللسان 13 · شفتان 4

#### Scenario: Two letters the zones cannot separate are reported, not patched

- **WHEN** `ح` and `ه` are composed
- **THEN** they SHALL yield the same primitives, both sitting in `حلق` with the same ṣifāt
- **AND** this SHALL be recorded as an accepted cost of the five-zone cut
- **AND** no sixth zone or sub-position split SHALL be introduced to separate them

### Requirement: The primitive vocabulary is closed and capped at 20

`physical_primitives.csv` SHALL hold one row per (physical feature, primitive). The set of distinct
primitives it declares SHALL NOT exceed **20**.

The cap was 15 while the table mapped ṣifāt alone. It was raised by **exactly five** to admit the
five classical مخرج zones — a closed classical partition, not five free parameters — after the
collision probe proved a ṣifāt-only table cannot distinguish `ب` from `ج` from `د`. Raising the
ceiling by the size of a named partition is not the same as removing it, and the cap SHALL NOT be
raised again to accommodate a root that reads badly.

The table SHALL be keyed on the feature vocabulary alone. It SHALL contain no root, no root key and
no per-root exception, and there SHALL be no mechanism by which a root can override it.

#### Scenario: The cap is enforced

- **WHEN** a 21st distinct primitive is introduced
- **THEN** validation SHALL fail
- **AND** the message SHALL state that a richer table explains everything and therefore nothing

#### Scenario: No root can reach the table

- **WHEN** the table's columns and the loader's signature are inspected
- **THEN** neither SHALL accept or carry a root key

### Requirement: Every row declares whether it is attested or the project's own hypothesis

Each row of `physical_primitives.csv` SHALL carry a `status` of exactly `attested` or `hypothesis`.

- `attested` SHALL carry an `authority` and real `pages`, checked against the same authority index
  the lock's `history[].source` is checked against. It asserts that a named scholar states this
  quality-to-notion mapping.
- `hypothesis` SHALL carry a `physical_basis` — the uncontested tajwīd definition of the feature —
  and MAY carry `support` citations. A `support` citation SHALL NOT be presented as authority, in
  the data, in the API response or on screen.

The validator SHALL accept a row carrying real pages **or** an explicit `hypothesis`. It SHALL
reject an empty field, and it SHALL reject an approximate or unverifiable page reference.

The table SHALL NOT claim an authority it does not have. No known source tabulates the صفات into a
general quality-to-notion mapping: Ibn Jinnī states the principle and illustrates it on particular
cases, and Ḥasan ʿAbbās gives senses per letter rather than per صفة. Most rows are therefore the
project's own construction, and declaring that is what allows `k / 40` to falsify them — a row
wearing a borrowed citation could always blame its failure on the source.

#### Scenario: A row with neither pages nor an owned hypothesis fails the build

- **WHEN** a row carries an empty `authority`, an empty `pages` and no `hypothesis` status
- **THEN** `scripts/validate_concept_datasets.py` SHALL exit non-zero
- **AND** it SHALL name the offending row

#### Scenario: A hypothesis row ships without a semantic authority

- **WHEN** a row declares `status: hypothesis`
- **THEN** validation SHALL pass with `physical_basis` present and `authority`/`pages` empty
- **AND** any `support` citation SHALL be rendered as support, never as the row's authority

#### Scenario: An approximate page is rejected

- **WHEN** an `attested` row carries a page reference that is not resolvable in the authority index
- **THEN** validation SHALL fail
- **AND** the row SHALL NOT be silently downgraded to `hypothesis`

#### Scenario: The response says which rows are the project's own

- **WHEN** a concept is returned
- **THEN** each realised primitive SHALL carry the `status` of the row that produced it
- **AND** the `/lexical` page SHALL distinguish an attested mapping from a project hypothesis

### Requirement: The table is frozen by digest before the first root is composed

`physical_primitives.lock.json` SHALL record `version`, `frozen_on`, `target`, the `sha256` of the
table's bytes, the row count, and a `history[]` whose every entry carries `version`, `date`,
`sha256`, a `reason` and a `source` of `{authority, pages}` checked against the same authority index
the row citations use.

The table SHALL change only through a new lock version justified by a **feature-level** authority.
A root that reads badly SHALL NOT be a reason to change it — that is back-fitting, and the recorded
outcome of such a root is a result, not a defect.

#### Scenario: A silent edit is caught

- **WHEN** `physical_primitives.csv` is modified without a lock bump
- **THEN** validation SHALL fail on the digest mismatch
- **AND** it SHALL report the expected and actual sha256

#### Scenario: The seed script can never write the frozen table

- **WHEN** `scripts/build_physical_primitives_seed.py` is run
- **THEN** it SHALL NOT write to `physical_primitives.csv`
- **AND** a test SHALL read its source to assert the target path is absent from it
- **AND** a second test SHALL assert the lock digest survives the run

#### Scenario: A history entry cannot cite a source that does not exist

- **WHEN** a `history[]` entry names an authority or a page range absent from the authority index
- **THEN** validation SHALL fail
