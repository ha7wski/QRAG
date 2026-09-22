## ADDED Requirements

### Requirement: A root's semantic core is cited, never inferred

`data/references/root_cores.json` SHALL record, per root, the **attested** semantic core(s) of that
root as stated by Ibn Fāris in *Muʿjam Maqāyīs al-Lugha*. Each core SHALL carry:

- `gloss` — a short Arabic label for the aṣl (curated, may be a condensation);
- `verbatim` — Ibn Fāris' own words, byte-identical to the corresponding segment of
  `data/references/maqayis_asl.csv`, never paraphrased and never rewritten;
- `axes` — one or more axis ids from the closed vocabulary;
- `polarity` — `positive` | `negative` | `neutral`;
- `source` — at minimum the work and the edition already carried by the Maqāyīs row.

A core SHALL NOT be created for a root that has no cited aṣl. A root whose Maqāyīs row is
`asl_status: "no_asl"` or `"parse_uncertain"` SHALL be absent from the dataset rather than present
with an invented core.

#### Scenario: A cited aṣl becomes a core
- **WHEN** the entry for the root `خير` is read
- **THEN** it contains exactly one core
- **AND** that core's `verbatim` is «الخاء والياء والراء أصله العطف والميل، ثم يحمل عليه»
- **AND** its `axes` include the axes for عطف and ميل
- **AND** its `polarity` is `neutral`

#### Scenario: An unparsed root is absent, not guessed
- **WHEN** the root `فسد` (Maqāyīs `asl_status: "parse_uncertain"`) is looked up
- **THEN** no entry is returned
- **AND** no core with an inferred gloss exists for it in the dataset

### Requirement: Polarity describes the aṣl, not the root's usage

`polarity` SHALL express the evaluative charge of the aṣl **as cited**, and SHALL be `neutral`
whenever the aṣl is descriptive — a movement, a shape, an action — rather than evaluative. The
connotation a root acquires in Quranic usage SHALL NOT be back-projected onto its aṣl.

This is what stops the constrained reading from becoming a sentiment classifier: the polarity is a
property of a citation, so it can be checked against the citation.

#### Scenario: A descriptive aṣl of a negatively-used root stays neutral
- **WHEN** the core of `كفر` («الكاف والفاء والراء أصل صحيح يدل على معنى واحد، وهو الستر والتغطية»)
  is read
- **THEN** its `polarity` is `neutral`
- **AND** its axes are those of ستر and تغطية, with no axis expressing blame or disbelief

#### Scenario: An evaluative aṣl carries its charge
- **WHEN** the core of `خبث` («الخاء والباء والثاء أصل واحد يدل على خلاف الطيب») is read
- **THEN** its `polarity` is `negative`

### Requirement: A root may hold several cores, kept apart

The value for a root SHALL be an ordered **list** of cores, because Ibn Fāris states more than one
aṣl for some roots. Cores SHALL NOT be merged, and their axes SHALL NOT be pooled: each core is a
separate reading hypothesis, and pooling them reproduces the undifferentiated blend this change
exists to remove.

#### Scenario: Two aṣl stay two cores
- **WHEN** the entry for `ظلم` is read
- **THEN** it contains two cores
- **AND** the first is «خلاف الضياء والنور» and the second «وضع الشيء غير موضعه تعديا»
- **AND** no third entry merging their axes exists

### Requirement: Cores are keyed on the canonical root key

Keys SHALL be the **canonical QAC root key** — the exact, hamza-bearing spelling that
`retrieval.lexical_retriever.LexicalRetriever._canon` returns — and every lookup SHALL canonicalize
its input through `_canon` before indexing the map.

Keys SHALL NOT be the hamza-folded `normalize_root` form on which `maqayis_asl.csv` is keyed. The
seed script MAY fold a key to *find* the Maqāyīs row, but SHALL store the canonical spelling. A
curated list keyed on the fold matches nothing once roots are stored in exact spelling, and it fails
silently — the reading simply stops being constrained.

#### Scenario: A hamzated root is stored and found in exact spelling
- **WHEN** the dataset is validated
- **THEN** every key is a root key present in the QAC morphology index
- **AND** a hamza-bearing root such as `أنس` is stored as `أنس`, not as its folded form
- **AND** looking it up from any spelling that `_canon` maps to `أنس` returns its cores

#### Scenario: The fold trap is caught at validation, not in production
- **WHEN** a key is added that is not a canonical QAC root key
- **THEN** validation fails naming that key
- **AND** the dataset is not accepted

### Requirement: Axes come from one closed vocabulary

`data/references/semantic_axes.json` SHALL define the **complete** set of semantic axes. Each axis
SHALL carry a stable id, an Arabic label, and MAY carry an `antonym` naming another axis id. Both
`root_cores.json` and `letter_senses.csv` SHALL reference axes only by id, and validation SHALL fail
on any unknown id.

The vocabulary is closed because the selection step matches the two sides by set intersection: with
free-text axes, agreement is an accident of wording. The `antonym` link is what allows a later step
to distinguish "no shared axis" from "an opposed axis".

#### Scenario: An unknown axis is rejected
- **WHEN** a core or a letter sense references an axis id absent from `semantic_axes.json`
- **THEN** validation fails naming the file, the entry and the unknown id

#### Scenario: Opposition is declared, not guessed
- **WHEN** an axis declares an `antonym`
- **THEN** the named axis exists and declares the first one back
- **AND** validation fails on a one-sided antonym declaration

### Requirement: The dataset is seeded by script and completed by a human

`scripts/build_root_cores_seed.py` SHALL emit a seed of `root_cores.json` from
`data/references/maqayis_asl.csv`, filling `verbatim`, `source` and the canonical key, and leaving
`axes` empty and `polarity` null. It SHALL NOT invent axes or polarity.

The file SHALL be recorded in `quran_data/manifest.py` as **not regenerable**, naming the seed
script as producer, because re-running the script SHALL NOT overwrite curated axes or polarity.

#### Scenario: Re-seeding preserves curation
- **WHEN** the seed script runs against an existing curated `root_cores.json`
- **THEN** entries already carrying axes and polarity keep them
- **AND** only missing entries are added

#### Scenario: An incomplete entry never reaches the product
- **WHEN** an entry has an empty `axes` list or a null `polarity`
- **THEN** validation fails naming that root
- **AND** the loader SHALL treat the file as unusable rather than serve a half-curated core

### Requirement: The dataset registers like every other dataset

The three new files SHALL each have a constant in `quran_data/paths.py`, a cached loader in
`quran_data/loaders.py`, and an entry in `quran_data/manifest.py` naming their real consumers. No
module SHALL build their paths by hand.

#### Scenario: The registry stays consistent
- **WHEN** `tests/test_quran_data.py` runs
- **THEN** every new path constant has a manifest entry
- **AND** every new manifest entry names a real constant and real consumers

#### Scenario: A missing core dataset fails with its own instructions
- **WHEN** `root_cores.json` is absent and the loader is called
- **THEN** `DatasetMissing` is raised carrying the rebuild command read from the manifest
