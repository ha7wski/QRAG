# constrained-letter-reading Specification

## Purpose
TBD - created by archiving change constrain-lisan-by-root-core. Update Purpose after archive.
## Requirements
### Requirement: The reading is built root-first, core-first

The Lisan pipeline SHALL run in this order: **word → root → attested core(s) → per-letter sense
selection constrained by the core → synthesis**. The letter senses SHALL be read only after a core
is in hand, and the synthesis SHALL be composed only from senses that a core selected.

No step SHALL compose a meaning from letter data alone. That composition — one frozen gloss per
letter, concatenated — is the defect this capability replaces: on `خ-ي-ر` it yields
«القذارة والخشونة والخواء … فساد» against the cited aṣl «أصله العطف والميل».

#### Scenario: The core is fetched before the letters are read
- **WHEN** `خير` is analysed
- **THEN** the cores of the root are resolved first
- **AND** the sense chosen for each of خ, ي and ر is one that the core admits

#### Scenario: The unconstrained concatenation no longer exists
- **WHEN** the codebase is searched after the change
- **THEN** no code path composes a synthesis paragraph from letter glosses without a core
- **AND** no environment variable, flag or fallback restores that path

### Requirement: Selection is deterministic, auditable and LLM-free

For each root letter, given the letter's senses and one core, selection SHALL proceed as:

1. **Eligibility** — keep the senses whose `axes` share at least one axis id with the core's `axes`
   and share **no** axis declared as the `antonym` of a core axis.
2. **Ranking** — order the eligible senses by the fixed tuple, highest first:
   `(number of shared axes, position fit, source confidence rank, −declaration index)`
   where *position fit* is 1 when the sense's `position` matches the letter's position in the root
   (`initial` / `medial` / `final`) or is `any`, else 0; and confidence ranks
   `verified` > `high` > `summary`.
3. **Outcome** — the first sense wins. The tuple is total, so the result is reproducible.

Selection SHALL NOT call a language model, an embedding model, or any network service. The Lisan
synthesis was already de-LLM'd once because a local model produced fluent prose contradicting the
attested sense; re-introducing a model in the *selection* step would rebuild that failure one layer
down, where it is harder to see.

#### Scenario: The same input always yields the same reading
- **WHEN** the same word is analysed twice in the same process, and again in a fresh process
- **THEN** the selected sense for every letter is identical
- **AND** the ranking is decided without reading the clock, the environment or a random source

#### Scenario: The reading explains itself
- **WHEN** a sense is selected
- **THEN** the response carries the axis ids it shared with the core
- **AND** the rule that selected it (`axis-match`, or `axis-match+position`)

#### Scenario: An opposed sense is never eligible
- **WHEN** a letter sense carries an axis declared as the antonym of one of the core's axes
- **THEN** that sense is not eligible, whatever its other overlaps
- **AND** it appears among the discarded senses with reason `conflicting-axis`

### Requirement: A letter with no eligible sense asserts nothing

When no sense of a letter is eligible for the core, the reading SHALL mark that letter `unmatched`,
SHALL select no sense for it, and the synthesis SHALL NOT attribute any meaning to it. The pipeline
SHALL NOT fall back to the letter's first, most-confident or most-frequent sense.

A reading in which some letters are unmatched is still returned — partially constrained and marked
as such — because the honest partial reading is the product, and silently filling the gap is the
behaviour being removed.

#### Scenario: The gap is shown, not filled
- **WHEN** a letter has senses but none shares an axis with the core
- **THEN** its `selection_rule` is `unmatched` and its selected sense is null
- **AND** all its senses appear as discarded, with reason `no-shared-axis`
- **AND** the synthesis paragraph does not name a meaning for that letter

### Requirement: Discarded senses are shown with their reason

Every sense not selected SHALL be returned alongside the selected one, each carrying why it was
dropped: `no-shared-axis`, `conflicting-axis`, or `outranked` (eligible but beaten by the ranking).
The `/lexical` page SHALL render them under each letter, collapsed by default, labelled in Arabic as
senses of the letter not adopted for this root.

The bundle is the whole point of the change; hiding the rejected members would leave the user with a
single gloss again, only a different one.

#### Scenario: A rejected sense stays visible
- **WHEN** `خير` is analysed
- **THEN** the negative خشونة/خواء sense of `خ` appears among the discarded senses of `خ`
- **AND** it is marked `no-shared-axis` or `conflicting-axis` against that core
- **AND** it is reachable in the UI without leaving the page

#### Scenario: Outranked is distinguished from rejected
- **WHEN** two senses are both eligible and one wins the ranking
- **THEN** the loser's reason is `outranked`, not `no-shared-axis`

### Requirement: One reading per core, never a blend

When a root has several cores, the response SHALL carry one complete reading per core, in the
dataset's order, each with its own selections, discarded senses, synthesis and guard verdict. Axes
SHALL NOT be pooled across cores, and the readings SHALL NOT be merged into one paragraph.

#### Scenario: Two aṣl give two readings
- **WHEN** `ظلم` is analysed
- **THEN** two readings are returned, one per cited aṣl
- **AND** each names the core it was built from, with that core's verbatim text
- **AND** no reading mixes axes from both

### Requirement: No core means no constrained reading, and it is said out loud

When the resolved root has no entry in `root_cores.json`, the response SHALL set `constrained` to
false, SHALL carry an Arabic `warning` stating that no attested aṣl is on record for this root, and
SHALL produce **no synthesis paragraph**.

The letter senses MAY still be returned as an inventory — the full bundle, none selected, labelled
unconstrained — because listing sourced senses is informative. Composing them into an assertive
reading is not, and SHALL NOT happen.

At most 1 149 of the 1 656 QAC roots can ever have a Maqāyīs core, and the curated set begins
smaller: this path is a normal outcome for a large minority of roots, not an edge case, and it is
preferred over restoring the reading that produced the `خ-ي-ر` bug.

#### Scenario: An uncovered root degrades visibly
- **WHEN** a root absent from `root_cores.json` is analysed
- **THEN** `constrained` is false and a `warning` is present
- **AND** `synthesis` is empty
- **AND** the letter senses are returned with none selected

#### Scenario: The old behaviour is not the fallback
- **WHEN** a root has no core
- **THEN** no concatenated letter-gloss paragraph is produced under any setting

#### Scenario: Coverage is measurable
- **WHEN** the dataset validator runs
- **THEN** it reports how many QAC roots have at least one curated core
- **AND** that figure is reproducible from the shipped files alone

### Requirement: The divergence guard detects, and never corrects

After selection, the reading's aggregate polarity SHALL be compared with the core's `polarity`. When
they contradict — the selected senses are predominantly `negative` against a `positive` core, or the
reverse — the reading SHALL carry a `divergence` object naming the core polarity, the reading
polarity, and the letters responsible, and the UI SHALL display it.

The guard SHALL NOT re-run selection, re-rank, drop or substitute a sense to remove the divergence.
A guard that silences itself by editing the reading would manufacture agreement, which is a worse
failure than the one it exists to catch: the tool would then always appear to confirm the aṣl.

A firing guard is a signal that the letter senses, the core's axes or its polarity are miscurated,
and it is addressed by curating the data, not by weakening the check.

A guard that NEVER fires is the opposite signal, and it SHALL be reported as one. Because the guard
detects and never corrects, sustained silence over a large curated set means the letter senses agree
with every core they meet — the shape that curating letters to fit the roots would leave. The
dataset validator SHALL therefore print an unmatched rate and a divergence rate, computed by running
the production selection step over the curated set, and a verdict that states when those numbers can
still be believed.

#### Scenario: A contradiction is reported
- **WHEN** the selected senses of a root are predominantly negative and its core polarity is positive
- **THEN** the reading carries a `divergence` object naming both polarities and the letters concerned
- **AND** the selected senses are exactly those the ranking chose, unchanged

#### Scenario: The guard cannot rewrite the reading
- **WHEN** a divergence is detected
- **THEN** the number of selected senses, and which they are, is identical to the pre-guard result

#### Scenario: A neutral core does not force agreement
- **WHEN** the core polarity is `neutral`
- **THEN** no divergence is raised on polarity grounds alone

#### Scenario: A guard that never fires is reported as a warning, not a pass
- **WHEN** the validator runs with at least 50 curated roots and the guard has never fired
- **THEN** the verdict states the method is not falsifiable and points at the letter senses
- **AND** below that threshold the verdict states the probe is not yet testable, rather than passing

#### Scenario: The rates are measured by the shipped selection step
- **WHEN** the unmatched and divergence rates are computed
- **THEN** they come from the production selection module, not a second implementation

### Requirement: `POST /lisan/analyze` publishes the constraint, not just the conclusion

The endpoint SHALL return, in addition to the word and root: the resolved `cores` (each with gloss,
verbatim, axes, polarity, source), `constrained`, one entry in `readings` per core — each holding
per-letter `selected` / `discarded` / `selection_rule` / `matched_axes`, its `synthesis`, and its
`divergence` — plus `warning` and the existing interpretive `disclaimer`.

**BREAKING**: `sequential_reading` is removed, and `letters[].meaning` no longer exists as a single
gloss. The route stays mounted at the same path and the frontend moves with it in the same change.

Input validation is unchanged: empty or non-Arabic input SHALL still be rejected with 422, and an
unresolvable root SHALL still return 200 with `root: null` and an Arabic `message`.

#### Scenario: The response carries the evidence
- **WHEN** a covered root is analysed
- **THEN** the response contains the core's verbatim aṣl text
- **AND** each letter carries its selected sense, its matched axes and its discarded senses

#### Scenario: The served surface is unchanged
- **WHEN** `tests/test_served_surface.py` runs
- **THEN** `POST /lisan/analyze` is mounted and called by the frontend
- **AND** no route is added or removed by this change

#### Scenario: A rootless word still answers 200
- **WHEN** a word with no resolvable QAC root is analysed
- **THEN** the status is 200 with `root: null` and an Arabic `message`
- **AND** `constrained` is false

### Requirement: خ-ي-ر and its minimal pair are permanent regression tests

The repository SHALL carry tests that fail if the reported defect returns.

- **`خ-ي-ر`** — the reading SHALL be built on «أصله العطف والميل», SHALL select for `خ` a sense on
  the ميل/انعطاف axes, and SHALL NOT contain قذارة, خشونة, خواء or فساد in its synthesis.
- **`خ-ب-ث`** — the reading SHALL be built on «خلاف الطيب» and SHALL select for `خ` a negative-pole
  sense. Together with `خ-ي-ر` this is the decisive test: the **same letter**, two cores, two
  different senses. A mechanism that cannot produce both has not fixed the defect, only relabelled it.
- **`ك-ف-ر`** — the core is descriptive («الستر والتغطية»), so the reading SHALL land on
  ستر/تغطية/إخفاء, SHALL NOT be forced positive by the constraint, and SHALL NOT be forced negative
  by the root's Quranic connotation. This is the test that the constraint follows the citation rather
  than a sentiment prior.
- **`ظلم`** — two readings, one per aṣl.
- **an uncovered root** — `constrained` false, warning present, synthesis empty.

#### Scenario: The reported bug fails the build
- **WHEN** the synthesis for `خير` contains any of قذارة, خشونة, خواء, فساد
- **THEN** the test suite fails

#### Scenario: The same letter reads differently under two cores
- **WHEN** `خير` and `خبث` are analysed
- **THEN** the sense selected for `خ` differs between them
- **AND** each selected sense shares an axis with its own root's core

#### Scenario: The constraint does not launder a negative root
- **WHEN** `كفر` is analysed
- **THEN** the selected senses express ستر/تغطية
- **AND** the synthesis asserts no positive evaluation of the root

#### Scenario: The guard is exercised, not assumed
- **WHEN** a synthetic core and sense set built to contradict each other is analysed
- **THEN** the divergence guard fires
- **AND** the selection is unchanged by it

