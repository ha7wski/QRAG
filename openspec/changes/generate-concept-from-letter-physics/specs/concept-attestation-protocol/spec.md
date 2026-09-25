## ADDED Requirements

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

### Requirement: The attested uses are frozen before the concept exists

For each witness root, `data/references/concept_attestation.json` SHALL carry a `uses[]` list — each
use a gloss and one verse reference — recorded and committed **before** that root's concept is
generated. Each entry SHALL carry the timestamp or commit at which `uses[]` was frozen and the one
at which the concept was recorded.

If the attested uses are written after the concept is read, "does the concept cover them" is
elastic: the list shapes itself around the sentence. The ordering is the protocol.

#### Scenario: An out-of-order record invalidates the metric

- **WHEN** any witness root's `uses[]` was frozen after its concept was recorded
- **THEN** `scripts/validate_concept_datasets.py` SHALL refuse to print the metric
- **AND** it SHALL name the offending roots

#### Scenario: A use carries its evidence

- **WHEN** a `uses[]` entry is validated
- **THEN** it SHALL carry a gloss and a verse reference that exists in the corpus

### Requirement: A test may not compose a witness root

The test suite SHALL NOT be able to compose any root in the holdout. Calling the composer — directly
or through the confrontation module — on a witness root while running under a test runner SHALL
raise. There SHALL be no warning mode, no `strict=False` and no environment variable that relaxes
it.

Two callers are exempt and both are named. The **shipped route** composes whatever root a reader
asks for; a reader does not know the holdout exists and the guard SHALL be inert outside a test
runner. The **recording path** composes all 40 by definition — that is the generation step — and
SHALL take an explicit, named sanction rather than a silent exemption.

The reason the rule is scoped to tests rather than to everything: a test PINS what it composes. An
assertion over a witness root's realised primitives is an expectation derived from that root's
concept, living in the repository, and after it exists nobody can extend or re-freeze that root's
`uses[]` without having read what the engine says about it. A prose note in the record file does not
prevent this — one was written, and thirteen tests were composing holdout roots when the guard was
first installed, none of them deliberately.

#### Scenario: A test composing a witness root fails hard

- **WHEN** a test composes any of the 40 witness roots
- **THEN** the call SHALL raise
- **AND** the message SHALL name the root and the sanctioned path
- **AND** no configuration SHALL downgrade it to a warning

#### Scenario: The recording path is let through, and only inside its own block

- **WHEN** the generation step composes the holdout inside the declared sanction
- **THEN** the composition SHALL proceed
- **AND** the sanction SHALL close on exit, including when the block raises

#### Scenario: An unreadable holdout refuses rather than disarms

- **WHEN** the witness set reads back empty under a test runner
- **THEN** the guard SHALL raise rather than let every root through
- **AND** this SHALL be the opposite failure direction from the metric reader, which fails open
  because there an empty set can only shrink what is claimed

### Requirement: Coverage is judged against a criterion fixed before the first concept is read

What makes a use `covered` SHALL be written down and committed **before** any witness root's concept
is generated. A judge with no written criterion applies one anyway and discovers it while judging,
which is the same defect as writing the `uses[]` after reading the sentence — one layer further in.

The criterion SHALL be: a use is covered when a reader given only the realised primitives, in their
positional order, and told nothing about the root, would recognise that use's notion as something
the reading says. Three tests, all necessary — **nothing imported** (every content notion of the
gloss traces to a realised primitive), **not merely inert** (at least one realised primitive carries
the gloss's central notion; compatibility is not coverage), and **the direction holds** (the
positional rule is part of the claim). The judge SHALL NOT use knowledge of what the root means to
bridge from the primitives to the gloss.

Every miss SHALL name its class in its `reason`, from a vocabulary fixed with the criterion:
`imported`, `inert`, `direction`, `collision`. The classes exist so that §D3's reopening condition —
collision failures strictly more than half of failing roots — is measurable against reasons that
were classified when they were written rather than re-read afterwards.

`collision` SHALL be derived mechanically, from whether another root with a divergent aṣl composes
to the same realised primitives, and SHALL be derived **after** the verdicts are written, so that
knowing a root collides cannot shape the reading of its uses.

#### Scenario: The criterion is committed before the concepts

- **WHEN** the history is read
- **THEN** the commit declaring the coverage criterion SHALL precede the commit recording any
  witness root's concept
- **AND** no verdict SHALL exist in the tree at that commit

#### Scenario: Every miss is classified

- **WHEN** a use is recorded `not_covered`
- **THEN** its `reason` SHALL open with one of the four declared classes
- **AND** the reason SHALL name the notion that was missing, imported, or contradicted

#### Scenario: Compatibility is not coverage

- **WHEN** a concept neither contradicts a use nor says anything about it
- **THEN** the use SHALL be recorded `not_covered` with class `inert`
- **AND** it SHALL NOT be recorded covered on the ground that nothing conflicts

### Requirement: Disagreement is recorded, never repaired

A root whose generated concept fails to cover an attested use SHALL be recorded as a miss, with one
line of reason. That record SHALL NOT be a reason to add a table row, change a primitive's gloss,
re-order the rarity rule, or add any exception. The table changes only through a lock version
justified by a feature-level authority.

Agreement with Ibn Fāris' aṣl is **attestation**, not calibration: the aṣl SHALL never re-enter the
generation path.

#### Scenario: A miss stays a miss

- **WHEN** a witness root's concept contradicts its recorded aṣl
- **THEN** the verdict SHALL be recorded as a miss with its reason
- **AND** no dataset under this capability SHALL change in the same commit

#### Scenario: The engine remains able to disagree

- **WHEN** the confrontation runs
- **THEN** it SHALL compare and report only
- **AND** it SHALL have no path that re-ranks, re-selects or re-phrases the concept

### Requirement: One metric is reported, and it is the strict one

The reported measure SHALL be **k / 40** — the number of witness roots whose concept covers **all**
of that root's frozen uses. Partial credit, per-letter match rates, averaged coverage and any figure
computed over a subset of the witness set SHALL NOT be reported as the result.

Per-root verdicts and reasons SHALL be published alongside the number.

**One breakdown SHALL accompany it**, declared here before the measurement so it cannot be chosen
afterwards for being flattering: `k / 40` split by whether the root contains a **signature letter**
— `ر ش ض ل ص ز س`, the seven letters owning a صفة no other letter carries. Rarity ordering makes
those letters always lead with their own signature while profile-identical letters always lead with
something generic, so the method is expected to read sharply on one group and flatly on the other.
The split exposes that; the headline number hides it. The bias SHALL be measured, never corrected —
correcting it would mean weighting the order by something other than the table.

**Every surface that publishes `k / 40` SHALL publish, with it and not elsewhere, the reservation
that the composition rule is not entirely pre-registered**: the realised window was declared at two
and widened to three after a negative measurement on `ضرب`, the declared development case. The
positions, the rarity ordering and the tie-break were fixed before they were checked; the window was
not. The reservation SHALL name what contains the exposure — the holdout was never read when the
window changed, and `ضرب` is excluded from `k` — and SHALL NOT present that containment as erasing
it: one free parameter of the rule was set by looking at an outcome.

The reservation SHALL appear wherever the number appears: the validator's metric output, the
documentation, and any summary of the result. It SHALL NOT be deferred to the design note on the
grounds that the change is explained there. A reader meeting the number is owed its provenance at
that moment; a caveat a reader has to go and find is a caveat the publisher has kept.

**Audit SHALL be claimed as possible, not as performed.** There is no second judge. The frozen
`uses[]`, the generated concept, the verdict and its reason SHALL all be committed for all 40 roots,
so that a reader who clones the repository can redo the judgement and disagree. No text SHALL imply
that an independent review took place.

#### Scenario: The window reservation is printed with the number

- **WHEN** `k / 40` is printed by the validator, written in the documentation, or summarised anywhere
- **THEN** the same output SHALL state that the realised window was fixed after the fact on the
  development case
- **AND** it SHALL state that the holdout was not read when the window changed and that `ضرب` is
  excluded from `k`
- **AND** the number SHALL NOT be printed with the reservation available only by reference

#### Scenario: The residual collision is not repaired to improve the number

- **WHEN** witness roots fail because another root composes to their exact realised primitives
- **THEN** the مخرج granularity SHALL NOT be changed on that evidence alone
- **AND** a granularity change SHALL require that such collision failures be **strictly more than
  half** of all failing roots, classified on the per-root reasons already committed, with the
  colliding root identified by the probe's own `identical` criterion and an aṣl divergence under the
  set rule
- **AND** the change SHALL then be a lock version bump justified by a feature-level authority, never
  a row edited to rescue a root

#### Scenario: The bias split is reported with the number

- **WHEN** `k / 40` is published
- **THEN** it SHALL be accompanied by the signature-letter split
- **AND** neither half SHALL be reported alone as the result

#### Scenario: Audit is described accurately

- **WHEN** the metric and its records are published
- **THEN** the wording SHALL state that the judgement can be redone from the committed records
- **AND** it SHALL NOT describe the verdicts as independently reviewed

#### Scenario: A flattering variant is not substituted

- **WHEN** the validator prints the result
- **THEN** it SHALL print `k / 40` where `k` counts roots with every use covered
- **AND** a root with any uncovered use SHALL NOT contribute to `k`

#### Scenario: The number is auditable

- **WHEN** the result is published
- **THEN** each of the 40 roots SHALL appear with its concept, its frozen uses, its per-use verdict
  and its reason

### Requirement: The confrontation view shows both engines on the same root

The `/lexical` comparison SHALL display, for one root: the generated مفهوم, Ibn Fāris' aṣl
`verbatim`, the root's Quranic occurrences, the recorded verdict where one exists, and the
core-first engine's reading of the same root.

#### Scenario: Both readings are visible together

- **WHEN** a root covered by both engines is displayed
- **THEN** the physics-first مفهوم and the core-first reading SHALL both be shown
- **AND** neither SHALL be labelled correct by the page

#### Scenario: A root with no aṣl still shows its concept

- **WHEN** a root absent from `root_cores.json` is requested
- **THEN** the concept SHALL be generated and shown
- **AND** the confrontation panel SHALL state that no attested aṣl is on file, distinguishing the
  project's gap from Ibn Fāris' silence

### Requirement: The collision probe gates the curation and can redirect the design

The table maps 28 letters onto 18 distinct profiles, so `ب`/`ج`/`د`, `ث`/`ح`/`ف`/`ه`, `ط`/`ق`,
`ظ`/`غ`, `م`/`ن`, `و`/`ي` and `ت`/`ك` are indistinguishable to it. Whether that is a cost or the
dominant failure mode SHALL be settled **before any witness root is curated**, not after.

The probe SHALL run as soon as a minimal generation path exists — feature extraction, the table
store and the rarity ordering — and SHALL NOT require the sentence template, the LLM pass, the route
or the page. It compares realised primitives and reads attested aṣl from `maqayis_asl.csv`, so it
needs no curated dataset.

Probe roots SHALL be real QAC root keys differing by exactly one profile-identical letter:
`حرب`/`حرج`/`حرد` for `ب`/`ج`/`د`, `تبر`/`كبر` for `ت`/`ك`, and `كود`/`كيد` for `و`/`ي`. Probe roots
SHALL NOT be witness roots and SHALL NOT be added to the witness set.

#### Scenario: The probe precedes curation

- **WHEN** the change is implemented
- **THEN** the probe SHALL run before any witness root's `uses[]` is frozen
- **AND** no witness root's concept SHALL have been generated at that point

#### Scenario: A named probe root that is not a root key is rejected

- **WHEN** a probe pair names a form that is not a QAC root key — as `ريح` is not, being a derivative
  of `ر-و-ح`
- **THEN** the probe SHALL fail loudly rather than compare nothing
- **AND** a real minimal pair SHALL be substituted and recorded

### Requirement: The comparison criterion is fixed before the probe runs

Two concepts SHALL be compared on their **realised primitives**, never on their sentences, and the
comparison SHALL yield exactly one of three outcomes:

| Outcome | Definition |
|---|---|
| `identical` | the same multiset of realised primitives, at the same positions, in the same order |
| `order-distinct` | the same primitives, at different positions or in a different order |
| `distinct` | different realised primitives |

`order-distinct` SHALL be counted and reported as a **partial collision**. It SHALL NOT be reported
as a pass, grouped with `distinct`, or omitted from the summary: two concepts built from one set of
primitives shuffled are separated by the composition rule alone, not by anything the table knows
about their letters.

On the aṣl side, a pair SHALL count as **aṣl-divergent** only when no aṣl of one root matches any
aṣl of the other. Several probe roots carry more than one aṣl — `حرب` three, `حرد` three, `تبر` two
— and comparing whole sets rather than a chosen primary makes divergence harder to establish, so the
rule cannot inflate a collision verdict.

#### Scenario: A shuffled concept is not counted as a success

- **WHEN** two probe roots realise the same primitives in a different order or at different positions
- **THEN** the outcome SHALL be recorded as `order-distinct`
- **AND** it SHALL appear in the report as a partial collision

#### Scenario: A multi-aṣl root is judged on its whole set

- **WHEN** a probe root carries several attested aṣl
- **THEN** divergence SHALL be established only if none of them matches any aṣl of the other root
- **AND** no single aṣl SHALL be selected as the root's primary for this purpose

### Requirement: A qualification table is committed before the probe runs

For every pair in the mandated classes, the aṣl sets of both roots and a `qualifying` /
`non-qualifying` verdict under the set-based divergence rule SHALL be written out and **committed
before any concept is composed**.

The probe's size SHALL be reported **in roots, never in pairs**: 7 roots over 3 classes
(3 + 2 + 2). The three comparisons within the `ب`/`ج`/`د` triple share their roots and are
correlated, so counting them as three independent tests would inflate the probe's own `n` by
counting the same evidence more than once.

Publishing the table first fixes the test's denominator before its result is known; discovering
afterwards that a class held one usable comparison, or none, would make the real size of the test
unstatable in good faith.

The probe roots SHALL NOT be changed once the table is published. A sample swapped because the aṣl
turned out awkward would be a sample chosen by looking at the data, which is the same defect as a
table edited to make a root work.

#### Scenario: The table precedes the first composition

- **WHEN** the probe is run
- **THEN** the qualification table SHALL already be committed
- **AND** no probe concept SHALL have been composed before it

#### Scenario: The size is reported in roots

- **WHEN** the probe's scope or result is reported
- **THEN** it SHALL be stated as roots over classes, not as a pair count
- **AND** the correlation among the `ب`/`ج`/`د` comparisons SHALL be stated with it

#### Scenario: A secondary class empties without stopping the probe

- **WHEN** `ت`/`ك` or `و`/`ي` has no qualifying comparison but `ب`/`ج`/`د` qualifies
- **THEN** the probe SHALL run on what qualifies
- **AND** it SHALL report the reduced size
- **AND** no root SHALL be substituted or added to compensate

#### Scenario: The carrying class empties and the probe stops

- **WHEN** `ب`/`ج`/`د` has no qualifying comparison
- **THEN** the probe SHALL stop and report, being unable to decide
- **AND** alternates SHALL be examined only after that report
- **AND** the report SHALL state that the substitution followed an **empty sample**, distinguishing
  it from a substitution made after seeing a result

#### Scenario: The sample is not revised after the table is seen

- **WHEN** the qualification table reveals an awkward or reduced class
- **THEN** the probe roots SHALL NOT be substituted on that ground
- **AND** any alternate considered SHALL be recorded as rejected, with its reason

### Requirement: Widening the probe is conditional, and a confirmed collision ends it

The probe SHALL run the three classes `ب`/`ج`/`د`, `ت`/`ك` and `و`/`ي`, and SHALL stop there.

- If **any one** class returns `identical` where the aṣl diverge, the collision SHALL be treated as
  confirmed. The probe SHALL NOT be widened, the result SHALL be reported before further work, and
  mapping the five classical مخرج zones SHALL become **v1.0.0** of the table rather than a later
  lock version.
- Only if **all three** classes discriminate SHALL the probe extend to the four remaining classes
  (`ط`/`ق`, `ث`/`ح`/`ف`/`ه`, `م`/`ن`) before any conclusion is drawn.
- `ظ`/`غ` SHALL be excluded in every case. Its only real minimal pair runs through `ظلم`, already
  curated in `root_cores.json` and therefore contaminated as evidence in either direction.

#### Scenario: One confirmed collision stops the probe

- **WHEN** a single class returns `identical` on an aṣl-divergent pair
- **THEN** the probe SHALL NOT proceed to further classes
- **AND** the مخرج zone mapping SHALL be built as table v1.0.0, not deferred

#### Scenario: Widening happens only after a clean sweep

- **WHEN** all three mandated classes return `distinct` on aṣl-divergent pairs
- **THEN** and only then SHALL the four remaining classes be probed
- **AND** `ظ`/`غ` SHALL still be excluded

#### Scenario: The probe output is published either way

- **WHEN** the probe completes
- **THEN** its roots, their realised primitives, their attested aṣl, the per-pair outcome and the
  verdict SHALL be committed
- **AND** the outcome SHALL be stated in the documentation whether or not it confirmed the collision
