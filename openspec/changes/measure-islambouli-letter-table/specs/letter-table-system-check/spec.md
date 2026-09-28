## ADDED Requirements

### Requirement: The table is decomposed under criteria fixed before the grid exists

`data/references/islambouli_letters_grid.json` SHALL record, for each of the 29 rows, its
decomposition into alternatives (split on «،» and «أو») and, per alternative, the slots **action**,
**intensity** (closed scale `خفيف · وسط · شديد · شديد جداً`) and **ending** (any other qualifier,
vocabulary taken from the table). The formula «صوت يدل على» is not decomposed; row 0's «خفيف»
qualifying «صوت» SHALL be recorded as such. A qualifier SHALL attach to the nearest noun, uniformly.

#### Scenario: The grid contains only the poster's words

- **WHEN** the validator checks every slot value
- **THEN** each SHALL be a substring of its row's `text`
- **AND** a value that is not SHALL fail validation

#### Scenario: Nearest-noun attachment is applied uniformly

- **WHEN** row 20 «قطع، أو وقف شديد» is decomposed
- **THEN** «شديد» SHALL qualify «وقف» only
- **AND** the same rule SHALL apply to every row with a trailing qualifier

### Requirement: The grid reports four criteria and four series hypotheses

The grid SHALL report: **C1** literal (every slot value in its row's text); **C2** exhaustive (every
content word in exactly one slot, the rest named as `residue`); **C3** no word form in two different
slots across the table (root-level reuse reported as an observation, not a contradiction); **C4** no
two letters with the same full decomposition. It SHALL evaluate the hypotheses **H2**, the one with
phonetic support (the emphatic sits one intensity step above its plain counterpart, over the phonetic
plain/emphatic pairs: `ت→ط`, `ذ→ظ`, `د→ض`); **H1**, admissible as a pattern without phonetic
grounding (`ت/ث`, `ط/ذ`, `د/ظ` at equal intensity differing only by `متوقف`/`ملتصق`, `ض` alone at
`شديد جداً` — these are not plain/emphatic pairs); **H3** (`س/ص` differ
only by ending) and **H4** (`ح/هـ` differ only by intensity), each as holds / fails with the rows
that decide it.

#### Scenario: Each hypothesis is decided from the grid

- **WHEN** the grid is published
- **THEN** H1–H4 SHALL each carry `holds` or `fails` and the rows that decide it
- **AND** no hypothesis SHALL be added, removed or reworded after the grid exists

### Requirement: The verdict follows a rule fixed in advance, and changes only what the number means

The verdict SHALL be `system` when C1–C4 hold with no residue and H1 or H2 holds in full;
`partial system` when C1, C3 and C4 hold, with the rows outside the scheme named and counted; `list`
when C3 or C4 fails, or fewer than 15 of 29 rows decompose into two or more slots. The verdict SHALL
be published with `k / 40`. It SHALL NOT alter the table, the composer, the uses or the judgement.

#### Scenario: The verdict is computed, not chosen

- **WHEN** the validator reads the grid
- **THEN** it SHALL recompute the verdict from C1–C4 and H1–H2 and fail if the recorded one differs

#### Scenario: The verdict is printed with the number

- **WHEN** `k / 40` for this table is printed
- **THEN** the grid verdict SHALL be printed with it, with the sentence stating what it implies for
  the reading of a miss

### Requirement: The grid never reaches a composing path

No module under `linguistics/lisan/islambouli/` — `confront.py` included — SHALL import a reader
of, or name, `islambouli_letters_grid`. Only the validator reads it. The grid is an analysis of the
table, not an input to any reading or any judgement.

#### Scenario: Naming the grid in the composer fails the build

- **WHEN** a composer module contains the string `islambouli_letters_grid`
- **THEN** `tests/test_import_direction.py` SHALL fail, naming the file
