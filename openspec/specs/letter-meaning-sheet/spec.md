# letter-meaning-sheet Specification

## Purpose
«معاني الحروف»: the interpretive per-letter sheet in `data/references/maani_huruf.json` — its registration, the Arabic projection served with a letter of «فهرس الجذور», and the attribution every display of it must keep.
## Requirements
### Requirement: The «معاني الحروف» sheet is a registered reference dataset

The sheet SHALL live at `data/references/maani_huruf.json`, declared by one constant in
`quran_data/paths.py`, described by one `quran_data/manifest.py` entry naming its sources and its
consumers, and read through one cached loader in `quran_data/loaders.py`. No module SHALL open the
file by path. `data/maani-huruf/` SHALL no longer exist.

#### Scenario: Registry and manifest agree

- **WHEN** `tests/test_quran_data.py` runs
- **THEN** the new constant has a manifest entry whose consumers exist, and the test passes

#### Scenario: One parse per process

- **WHEN** the loader is called twice
- **THEN** it returns the same object

### Requirement: The sheet is projected to its Arabic fields

For one letter, the system SHALL expose: `letter`, `name`, `series`, `core_sense` (from
`core_sense_ar`), `drawing`, `structure`, `positions` (exactly three, in the order أول / وسط / آخر,
each with `position`, `divine_name` or null, `sense` from `sense_ar`, `examples`, `origin`),
`sources` (one per key present, in `meta.sources` key order, each with `key` and `reading`) and
`dimensions` (empty when absent). It SHALL NOT expose the French fields, `videos`, `quran_refs`,
`convergence`, `notes` or `discarded_poles`.

#### Scenario: All 28 letters project

- **WHEN** every letter of the sheet is projected
- **THEN** 28 projections are produced, each with three positions and a non-empty `core_sense`

#### Scenario: A substitute word keeps its null

- **WHEN** a position whose `origin` is `substitute_word` is projected
- **THEN** its `divine_name` is null and its `origin` is `substitute_word`

#### Scenario: No French leaks

- **WHEN** the projection of «ر» is read
- **THEN** it contains no `core_sense_fr` nor `sense_fr` value

### Requirement: Attribution is never blurred

Wherever the sheet is displayed, the system SHALL show the badge «تأويلي», the letter's series
(Abu Qaisar's own letter, or one built by generalising his procedure), the origin of each position,
and the named authority of each source reading. A source reading SHALL never be shown without its
authority.

#### Scenario: A generalised letter says so

- **WHEN** the box for «ر» (series `generalise`) is shown
- **THEN** it states that the letter is built by generalising the procedure, not given by Abu Qaisar

#### Scenario: Each source reading names its authority

- **WHEN** the box for «ب» is shown
- **THEN** each of its four readings (AQ, IS, HA, BL) appears beside the name of its authority

