## MODIFIED Requirements

### Requirement: The witness set is drawn once, published, and never curated against

`data/references/concept_witness_set.json` SHALL hold the frozen holdout: **40 roots**, drawn from
triliteral QAC roots that have a Maqāyīs `has_asl` row (joined through `arabic_text.normalize_root`)
and at least 20 Quranic occurrences, excluding the roots already curated in `root_cores.json` and
the declared development case `ضرب`. The draw SHALL be reproducible from the recorded seed
`20260925` — 29 from the 20–99 occurrence stratum, 11 from the 100+ stratum — and the file SHALL
record the frame size, the strata, the seed and the draw date.

The identity of the witness roots is public, because the set can only be held out if it is known.
What SHALL NOT happen before the primitive table is locked: reading their aṣl, generating their
concepts, or checking any table decision against them.

**This holdout is burned for any further measurement**: its 183 uses have been read. It SHALL stay
frozen as the record of the closed measurement and SHALL NOT be reused as the holdout of another
table. A different letter table SHALL be measured on its **own** holdout, drawn once from the same
frame minus these 40, by the same procedure with its own seed, and recorded in its own file. Such a
draw is a second, independent holdout — **not** a re-roll of this one, which stays as drawn.

#### Scenario: A second holdout is not a re-roll

- **WHEN** a second letter table is measured
- **THEN** `concept_witness_set.json` SHALL be byte-unchanged
- **AND** the second table's holdout SHALL exclude all 40 of its roots

#### Scenario: The draw is reproducible

- **WHEN** the recorded frame and seed are replayed
- **THEN** the 40 roots SHALL be exactly those in the file
- **AND** a test SHALL fail if the file has been edited

#### Scenario: The development case is not a witness

- **WHEN** the witness set is inspected
- **THEN** `ضرب` SHALL be absent
- **AND** the 5 roots already curated in `root_cores.json` SHALL be absent

#### Scenario: `ضرب`'s coverage is published without being a gate

- **WHEN** `ضرب` is confronted like any other root
- **THEN** its five brief-named uses SHALL be recorded and judged
- **AND** the result SHALL be published even when partial
- **AND** it SHALL NOT contribute to `k / 40`, having been used to verify the composition rule

### Requirement: The experiment is closed at its measured result, and is not repaired

The measurement returned **`k / 40 = 0`** — no witness root's concept covers every use frozen for it
— with the declared split at `0 / 25` and `0 / 15`, 7 of 183 uses covered, and misses classing
`imported` 162, `direction` 8, `inert` 6. The engine SHALL be recorded as a **closed experiment**.

The route `POST /lisan/concept` SHALL stay mounted and the concept SHALL stay on screen, labelled as
a closed experiment and carrying its number and its window reservation. A negative result removed
from the product is a result nobody can check.

**No change SHALL be made to recover the number.** Specifically: the feature vocabulary SHALL NOT be
widened, the مخرج zones SHALL NOT be subdivided, and the realised window SHALL NOT be altered. The
reason is in the distribution and not in a preference: 162 of the 176 misses are `imported`, so the
missing notion is absent from the vocabulary rather than mis-ranked by it — the failure is **not
parametric**, and no setting of the existing parameters reaches it. Adding a trait to reach `إدراك`
or `عون` would be adding it *because* the measurement failed, which is the move the table's freeze
exists to forbid.

The pre-registered reopening condition SHALL be treated as answered: collision failures are **1 of
40** failing roots against a threshold of strictly more than half.

The conclusion SHALL be stated at its measured scope and no wider: a root's meaning is not
recoverable from its letters' articulatory properties **under this vocabulary, this composition
rule, this coverage criterion, on these 40 pre-drawn roots**. It SHALL NOT be stated as a refutation
of the معاني الحروف tradition, which proposed no such table.

**Measuring a different, published table is not a repair of this one.** Replacing the input table
wholesale by a third party's published table — transcribed, not curated — and measuring it on a
fresh holdout under the unchanged harness is a new experiment. It SHALL leave this engine's code,
table, lock, holdout, uses, verdicts and number unchanged, and its result SHALL be published beside
`0 / 40`, never in place of it.

#### Scenario: A third-party table is measured beside, not instead

- **WHEN** a change measures a published third-party letter table under this harness
- **THEN** it SHALL NOT be refused as a rescue attempt
- **AND** `k / 40 = 0` and its distribution SHALL still be printed, unchanged, by this engine's
  validator
- **AND** a change to this engine's feature vocabulary, zones or window made under that heading SHALL
  still be refused

#### Scenario: The closed engine stays reachable and labelled

- **WHEN** a reader opens «تحليل اللسان»
- **THEN** the concept panel SHALL be shown, labelled a closed experiment
- **AND** it SHALL carry `k / 40 = 0` and the window reservation
- **AND** it SHALL NOT be presented as an alternative reading, nor either engine as correct

#### Scenario: A rescue attempt is refused

- **WHEN** a change proposes to widen the feature vocabulary, subdivide the حلق, or move the window
  in order to improve `k / 40`
- **THEN** it SHALL be refused on the committed distribution
- **AND** the refusal SHALL cite `imported` 162 of 176 and the 1-of-40 collision count

