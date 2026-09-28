## ADDED Requirements

### Requirement: The second holdout is drawn before any row is transcribed

`data/references/islambouli_witness_set.json` SHALL hold 40 triliteral roots drawn from the original
frame minus the 40 roots of `concept_witness_set.json`. The frame SHALL be rebuilt with the recorded
criteria and the recorded exclusions (`خبث خير رحم ظلم كفر`, `ضرب`) as pinned constants, and the draw
SHALL assert, before sampling, that the frame reproduces **280 = 205 + 75** and that seed `20260925`
reproduces the burned 40. It SHALL then draw 29 from the remaining 20–99 stratum and 11 from the
remaining 100+ stratum on one `random.Random(20260928)`, lower stratum first, each from a sorted list.
The file SHALL record the seed, its rationale, the draw date, the frame and strata sizes, the
procedure, and — as structure, never acted on — the weak-radical, hamza-carrier and bare-alef counts
and the overlap with the 7 probe roots, the 130-pair widening and `ضرب`.

The draw SHALL be committed before `islambouli_letters.csv` exists in any commit.

#### Scenario: The draw is reproducible

- **WHEN** the validator replays the recorded procedure
- **THEN** it SHALL obtain exactly the 40 roots in the file
- **AND** it SHALL fail if the frame no longer reproduces 280, or if seed `20260925` no longer
  reproduces the burned 40

#### Scenario: The burned roots cannot be drawn

- **WHEN** the new set is inspected
- **THEN** none of its roots SHALL belong to `concept_witness_set.json`, nor be `ضرب` or a root
  curated at the first draw

#### Scenario: The draw precedes the transcription in history

- **WHEN** the git history is inspected
- **THEN** the commit adding `islambouli_witness_set.json` SHALL be an ancestor of the first commit
  adding `islambouli_letters.csv`

#### Scenario: The set is never re-drawn

- **WHEN** a drawn root proves awkward to judge
- **THEN** it SHALL be measured and classed like any other
- **AND** the file SHALL NOT be regenerated with another seed

### Requirement: The harness is shared with the closed engine and proven unchanged by the sharing

The table-agnostic harness — draw replay, witness guard, uses reading, per-use and per-root verdicts,
`counts_toward_k`, the four miss classes, the strict metric and its signature-letter split — SHALL
live in `linguistics/lisan/harness/` and be imported by both engines. The closed engine's validator
output and verdict worksheet SHALL be byte-identical before and after the extraction.

#### Scenario: The closed record replays byte for byte

- **WHEN** `scripts/validate_concept_datasets.py` and `scripts/record_concept_verdicts.py worksheet`
  run after the extraction
- **THEN** their output SHALL equal the output captured before it, byte for byte
- **AND** `k / 40 = 0` with `imported` 162 · `direction` 8 · `inert` 6 SHALL still be printed

### Requirement: The reading places each radical's verbatim gloss in its fixed position

`linguistics/lisan/islambouli/compose.py` SHALL return, for a triliteral root, the table version and
digest and three positions (opens · body · concludes), each with the root letter, the poster row and
that row's `text` verbatim. It SHALL produce no sentence, connective, template text or LLM output.
Root-key letters SHALL map to rows by: the 28 consonants to their own row (`ه` → `هـ`); `أ ؤ ئ ء` to
row `ء` through the closed harness's explicit carrier table; bare `ا` to row `آ - ى`; `و` and `ي`
with no exception. Quadriliteral roots SHALL receive no reading, with the reason stated. An unmapped
character SHALL make the position silent and the reading partial, never fall back.

#### Scenario: A gloss reaches the reader unaltered

- **WHEN** a root is composed
- **THEN** each position's text SHALL be byte-identical to its row's `text`
- **AND** a gloss with «أو» SHALL be returned whole, not split

#### Scenario: Every QAC root-key character is mapped

- **WHEN** every triliteral QAC root is composed
- **THEN** no reading SHALL be partial on today's data
- **AND** the partial path SHALL remain and be tested on a synthetic key

#### Scenario: The bare alef reaches the آ row

- **WHEN** `اول` is composed
- **THEN** its opening position SHALL be row 26 («آ - ى»)

### Requirement: The reading is blind, by import edge

No module under `linguistics/lisan/islambouli/` except `confront.py` SHALL import — directly or
transitively — or name `root_cores`, `maqayis_asl`, `letter_senses`, `semantic_axes`,
`arabic_letter_semantics_hasan_abbas`, `concept_attestation`, `islambouli_attestation`,
`physical_primitives`, `arabic_letters_dataset`, or `linguistics/lisan/harness/verdicts.py`.
`confront.py` SHALL import the reading result and SHALL NOT be imported by any other module of the
package. The rule SHALL be written into `tests/test_import_direction.py` before the package exists.

#### Scenario: A composer reaching the meaning layer fails the build

- **WHEN** a composer module imports or names a banned dataset or module
- **THEN** the import-direction test SHALL fail, naming the path of the edge

### Requirement: A test may not compose a root of the second holdout

Under a test runner, `islambouli/compose.py` SHALL raise `WitnessRootComposed` from its first line
for any root of `islambouli_witness_set.json`, with no warning mode and no flag. The recording
script SHALL take the sanctioned context explicitly. The closed engine's guard SHALL keep guarding
its own 40.

#### Scenario: A test composing a new witness fails

- **WHEN** a test composes a root of the second holdout
- **THEN** `WitnessRootComposed` SHALL be raised

#### Scenario: An empty holdout disarms nothing

- **WHEN** the holdout file is empty or unreadable under a test runner
- **THEN** the guard SHALL raise rather than let every root through

### Requirement: Uses are frozen after the table and before any reading

`data/references/islambouli_attestation.json` SHALL hold, for each root of the second holdout and
for `ضرب`, `uses[]` written from `morphology.json`'s occurrence list and the Maqāyīs `verbatim` only —
one gloss and one verse reference per use, the verse checked to belong to the root — committed with
every verdict `not_judged`, after the table's lock and before any reading of these roots is
generated. `ضرب`'s uses SHALL be copied unchanged from `concept_attestation.json`.

The 40 roots' uses SHALL be written by a sub-agent that has not seen the poster. Its prompt carries
all of its input inline (procedure, roots, occurrences, Maqāyīs verbatim) and tells it to use no tool.
The meta SHALL record the prompt verbatim, the raw output, and the fact that the tool restriction is
by instruction and not enforced. In the same prompt the agent SHALL also write `ضرب`'s uses. These
are stored as `uses_blind` next to the reference copy and count in no `k`.

#### Scenario: A reading recorded before its uses is refused

- **WHEN** a root's `reading_recorded_at` precedes its `uses_frozen_at`, or a reading exists in the
  commit that froze its uses
- **THEN** the validator SHALL refuse to print the metric and name the root

#### Scenario: The blind calibration is published and concordance follows a fixed rule

- **WHEN** `ضرب`'s `uses_blind` are recorded
- **THEN** each reference use SHALL be matched to at most one blind use, with a one-line reason,
  before any reading of `ضرب` is looked at
- **AND** the output SHALL print reference count, blind count, matched and unmatched on each side,
  and the verdict: `concordant` if ≥ 4 of 5 are matched and ≤ 2 blind uses are unmatched,
  `strong divergence` if < 3 of 5 are matched, `partial` otherwise
- **AND** a `strong divergence` SHALL be reported as bearing on the published `0 / 40` too,
  without re-freezing, re-judging or adjusting either number

#### Scenario: The development case has identical uses under both tables

- **WHEN** `ضرب`'s uses are compared across the two attestation files
- **THEN** they SHALL be identical
- **AND** `ضرب` SHALL count toward neither half of `k`

### Requirement: Coverage is judged under the inherited criterion

Each use SHALL be judged `covered` or `not_covered` under the committed criterion of the closed
engine, verbatim: nothing imported, not merely inert, direction holds, and no use of knowledge of the
root to build the bridge. «أو» in a gloss SHALL be read disjunctively — a position says a notion when
either alternative says it — and the whole text of a row, qualifiers and row 0's clause included,
SHALL count as said. Every miss SHALL name its class first — `imported`, `inert`, `direction`,
`collision` — and `collision` SHALL be computed after the verdicts, as two triliteral roots with
identical realised row sequences.

#### Scenario: An unclassed miss is refused

- **WHEN** a `not_covered` verdict's reason does not begin with one of the four classes
- **THEN** the validator SHALL refuse it

### Requirement: `k / 40` is published beside `0 / 40`, with every reservation attached

The validator, the documentation and any summary SHALL print, together: `k / 40` for this table
(`k` = roots whose every use is covered, no partial credit); `0 / 40` read from the closed record at
run time; covered-use counts; the miss distribution by class for both; the inherited signature-letter
split labelled as inherited; the system-check verdict and what it implies; and the reservations R1
(the inherited window reservation, stated as non-binding here and not dropped), R2 (poster, no
R2 (poster, not the book; title and author printed on it and transcribed; no page; origin
unrecorded; row 12's unread mark), R3 (the positional rule is the harness's, not Islambouli's
method), R4 (one judge; audit possible, not performed), R5 (blind uses writer: a difference in nature
is not excluded, with the `ضرب` calibration figures printed) and R6 (two independent samples from one
frame; `ضرب` the only paired root).

#### Scenario: The number never travels alone

- **WHEN** `k / 40` for this table is printed anywhere
- **THEN** `0 / 40`, the class distributions and R1–R6 SHALL be in the same output

#### Scenario: The closed number is read, not typed

- **WHEN** the validator prints `0 / 40`
- **THEN** it SHALL compute it from `concept_attestation.json`
- **AND** no literal `0 / 40` SHALL appear in the validator's source

#### Scenario: The scope is stated

- **WHEN** the result is published, whatever `k` is
- **THEN** it SHALL be stated as the result of this table, transcribed from this poster, under this
  positional rule and this criterion, on these 40 roots
- **AND** it SHALL NOT be stated as a verdict on Islambouli's method or on the معاني الحروف tradition
