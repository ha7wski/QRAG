## ADDED Requirements

### Requirement: A letter holds several senses, not one gloss

`data/references/letter_senses.csv` SHALL hold **one row per (letter, sense)**, so that a letter
carries the bundle of senses the framework actually attributes to it. Each row SHALL carry:

| column | meaning |
|---|---|
| `letter` | the base letter glyph (hamza seats fold to `ء`) |
| `sense_id` | stable id, unique within the letter |
| `gloss_ar` | the sense, in Arabic |
| `pole` | `positive` \| `negative` \| `neutral` |
| `axes` | `;`-separated axis ids from the closed vocabulary |
| `position` | `initial` \| `medial` \| `final` \| `any` — where in the root the sense applies |
| `gesture_ar` | the articulatory gesture the sense is read from |
| `source` | the cited authority |
| `page` | the page or locus in that authority |
| `confidence` | `verified` \| `high` \| `summary` |

A letter SHALL have at least one sense. The `;` list convention is the one the existing dataset
already uses for `sifat_ar` and keywords.

#### Scenario: The letter خ carries opposed senses side by side
- **WHEN** the senses of `خ` are read
- **THEN** at least one sense expresses خشونة/خواء with `pole: negative`
- **AND** at least one sense expresses انعطاف/ميل with a non-negative pole
- **AND** both are present simultaneously, each with its own axes and source

#### Scenario: Every letter is readable
- **WHEN** the dataset is validated
- **THEN** each of the 28 base letters has at least one sense row
- **AND** every `sense_id` is unique within its letter

### Requirement: A sense with no cited source is refused

Every sense row SHALL name a `source` and a `page`. Validation SHALL fail on an empty `source` or an
empty `page`.

The Tahlīl engine already refuses to publish generated prose it cannot cite
(`linguistics/tahlil/citations.py`); curated scholarship is held to the same gate. Without it, the
selection step becomes a machine for producing whichever sense makes the root work — which is the
present bug with more steps.

#### Scenario: An uncited sense is rejected
- **WHEN** a sense row has an empty `source` or `page`
- **THEN** validation fails naming the letter and the `sense_id`

#### Scenario: A sense is not authored to fit a root
- **WHEN** a sense is added to the dataset
- **THEN** its source is a letter-level authority (Ḥasan ʿAbbās, Ibn Jinnī) cited at a page
- **AND** it is not justified by the root the curator was looking at

### Requirement: The phonetic sheet and the sense sheet are separate files

`data/references/arabic_letters_dataset.csv` SHALL keep exactly the letter-level identity and
phonetic columns (`letter`, `name_ar`, `name_translit`, `translit`, `makhraj_*`, `sifat_*`) for its
28 rows, and SHALL lose `abbas_meaning*` and `abbas_keywords*`. Sense data SHALL live only in
`letter_senses.csv`, joined on `letter`.

#### Scenario: The phonetic sheet stays one row per letter
- **WHEN** `arabic_letters_dataset.csv` is read after the change
- **THEN** it holds 28 rows, one per base letter
- **AND** it holds no meaning or keyword column

#### Scenario: The other letter dataset is untouched
- **WHEN** `linguistics/tahlil/huruf.py` runs after the change
- **THEN** it still reads `arabic_letter_semantics_hasan_abbas.json` unchanged
- **AND** its behaviour is unaffected

### Requirement: The lexicon exposes the whole bundle, and never picks for the caller

`linguistics/lisan/letter_lexicon.py` SHALL expose the senses of a letter as a list, in declaration
order, joined to that letter's phonetic row. It SHALL NOT choose among them, rank them, or return a
"default" sense — selection is the caller's step and depends on a root's core, which the lexicon
does not know.

Hamza seats (`أ إ ؤ ئ آ ٱ`) SHALL continue to fold to the base `ء` entry, and a letter absent from
the dataset SHALL continue to yield a neutral placeholder rather than raise.

#### Scenario: The bundle is returned whole
- **WHEN** the lexicon is asked for `خ`
- **THEN** every sense of `خ` is returned, in declaration order
- **AND** none is marked selected or preferred

#### Scenario: A hamza seat resolves to the base letter
- **WHEN** the lexicon is asked for `أ`
- **THEN** the senses of `ء` are returned

#### Scenario: An absent letter does not break a reading
- **WHEN** the lexicon is asked for the bare alif `ا`, which is not a base consonant in the framework
- **THEN** a placeholder with an empty sense list is returned
- **AND** no exception is raised
