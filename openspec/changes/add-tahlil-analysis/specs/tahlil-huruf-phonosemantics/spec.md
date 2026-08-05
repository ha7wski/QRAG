## ADDED Requirements

### Requirement: The letters dataset is loaded through one key-normalizing loader that fails loudly

The الحروف block SHALL read `data/references/arabic_letter_semantics_hasan_abbas.json` through a
single cached loader that normalizes lookup keys before matching: the dataset's `هـ` entry (letter
plus tatweel) SHALL resolve for the bare `ه` used in root keys, and hamza carriers (أ إ ؤ ئ آ ٱ)
SHALL resolve to the bare `ء` entry.

A root letter that cannot be resolved SHALL raise, and SHALL NOT be skipped. Measured on the
corpus, the unnormalized keys silently drop a root letter for 4 698 words (9.4 % of rooted words)
with no error — the synthesis is then composed from two letters instead of three, which no
coverage rate can detect.

**The decomposed root SHALL be the unfolded (raw QAC) root, not the normalized index key.** The
processed corpus stores roots hamza-folded onto alif — `qac_words` gives `اله`, `امن`, `شيا`, and
`root_display` is identical to `root` for all 49 967 rooted words, so the seat is not recoverable
from the processed artifacts. The letters dataset carries **ء (الهمزة)** and **ا (الألف اللينة)**
as two distinct entries with distinct meanings and distinct pages, so reading a folded root would
attribute الألف اللينة's meaning, and its page, to a hamza radical — for **133 of the 1 642 roots
and 9 780 of the 49 967 rooted words (19.6 %)**, silently. That is twice the hāʾ truncation above
and the same failure class. (The raw morphology carries **139** hamza-bearing roots; **6** of them —
أدم، أون، سبأ، طمأن، لؤلؤ، هاء — have no counterpart key in the treebank-derived root graph, leaving
**133** over the population actually served: 139 − 6 = 133. Both figures and their relation SHALL be
pinned by the sweep, so neither can drift into the other.)

The unfolded root SHALL be recovered from the raw QAC morphology source, whose `ROOT:` field
preserves the seat (`أله`, `أمن`, `شيأ`). Measured: the normalized→raw mapping is **unambiguous —
zero collisions across all 1 651 raw roots** — so the recovery is deterministic and lossless.

**Known limit, measured and observable.** Five corpus roots — نوس, ندو, طمن, لالا, معن (314 words,
0.63 %) — are rooted differently by the treebank than by the morphology file (treebank `طمن` vs
`ROOT:طمأن`, `لالا` vs `ROOT:لؤلؤ`, `نوس` vs `ROOT:أنس`), and two of them differ in **length**, so
seat-folding cannot recover them without changing the letter count. For these the block reads the
folded letters — `لالا` renders ل-ا-ل-ا, i.e. the very failure this requirement fixes, unrecovered.
The system SHALL expose them through an `unresolved_roots()` accessor and count them in the
coverage log, so the gap is stated rather than silent. It SHALL record only genuine corpus roots
there — a caller-supplied non-root is not a coverage miss, and counting it would make the log
over-report. A treebank-root → QAC-root alias table is deferred, not forgotten.

#### Scenario: An unrecoverable root is observable, never silent

- **WHEN** the block is assembled for a word whose root is one of the five (e.g. `لالا`)
- **THEN** the letters render from the folded root
- **AND** the root appears in `unresolved_roots()` and in the coverage log
- **AND** a caller-supplied non-root never appears there.

#### Scenario: A hamza radical is read as الهمزة, not as الألف اللينة

- **WHEN** the block is assembled for a word whose processed root is `امن` (raw QAC root `أمن`)
- **THEN** the first letter resolves to the dataset's **ء (الهمزة)** entry with its own page
  citation
- **AND** it does not resolve to the **ا (الألف اللينة)** entry
- **AND** the same holds for a hamza in medial or final position (e.g. `شيا` → `شيأ`).

The duplicate copy of the dataset under `data/processed/` SHALL be removed so there is exactly one
source of truth.

#### Scenario: A hāʾ root resolves all three letters

- **WHEN** the الحروف block is assembled for a word whose root contains `ه` (e.g. root `فهم`)
- **THEN** all three letters resolve to dataset entries
- **AND** the decomposition contains three letters, not two.

#### Scenario: An unresolvable letter raises rather than skipping

- **WHEN** the loader is asked for a letter with no dataset entry and no normalization to one
- **THEN** it raises
- **AND** no partial decomposition is produced.

#### Scenario: Corpus sweep shows full letter coverage

- **WHEN** every rooted word in the corpus is passed through the decomposition
- **THEN** 100 % of them resolve every root letter
- **AND** any word that does not is reported as a failure, not omitted quietly.

### Requirement: Each letter is presented as a fact row and an interpretation row, never fused

For each root letter the block SHALL present, separately:

- **صفات (fact, badge محقّق)** — المخرج, جهر/همس, شدّة/رخاوة/توسّط, إطباق/استعلاء and the
  distinguishing صفات (صفير, تكرير, انحراف, …), from the dataset's phonetic fields.
- **دلالة (interpretation, badge تأويلي)** — the meaning per Hasan Abbas, cited with the author,
  the work, and the page number carried in the dataset.

The dataset's own honesty flag — that the دلالة is a transcribed but contested theoretical
framework and must never be badged محقّق — SHALL be surfaced in the UI **in Arabic**. The dataset
stores its `honesty_flags` and part of its `source` block in French; those strings SHALL NOT be
rendered, both because the page is Arabic-only and because the Latin-purity gate would void any
block carrying them. The module SHALL therefore own an Arabic disclaimer string of its own and
cite the source in Arabic. The two rows SHALL NOT be merged into one sentence or one badge.

#### Scenario: The pinned word's letters render both rows

- **WHEN** the block is assembled for root `سرع`
- **THEN** س shows «مهموسة، رخوة، فيها صفير» badged محقّق and its دلالة badged تأويلي with a page
  citation
- **AND** ر shows «مجهورة، متوسطة، فيها تكرير وانحراف» badged محقّق and its دلالة separately.

#### Scenario: The framework disclaimer is visible

- **WHEN** the الحروف block renders any دلالة row
- **THEN** the source (author, work, year) and the interpretive-framework disclaimer are visible in
  the block.

### Requirement: Position claims are made only for letters that carry position notes

The دلالة of a letter varies with its position in the word (أول / وسط / آخر) in this framework.
The system SHALL state a position-specific reading only for letters whose dataset entry carries
`position_notes`, and SHALL omit the position line for the letters that do not — measured: د, ذ
and ط carry none, and 16.7 % of rooted words contain one of them.

A position reading SHALL NOT be generalized, inferred, or copied from another letter.

#### Scenario: A letter without position notes gets no position claim

- **WHEN** the block is assembled for a root containing د, ذ or ط
- **THEN** no أول/وسط/آخر claim is emitted for that letter
- **AND** the omission is recorded in the coverage log with reason `no-position-notes`
- **AND** the other letters of the root still receive theirs.

#### Scenario: A letter with position notes states its position explicitly

- **WHEN** the block is assembled for a letter carrying `position_notes`
- **THEN** the claim names the letter's position in the root (أول / وسط / آخر)
- **AND** cites the dataset entry and page.

### Requirement: The root's core sense is synthesized from the letters in order and marked تأويلي

The block SHALL compose the per-letter دلالة into one core-sense synthesis for the root, reading
the letters **in their root order**, and SHALL badge the synthesis تأويلي. The synthesis SHALL cite
every letter entry it composes.

#### Scenario: The synthesis cites every letter it composes

- **WHEN** the core sense is synthesized for a triliteral root
- **THEN** the claim cites all three letter entries
- **AND** it is badged تأويلي
- **AND** a synthesis citing fewer letters than the root has is dropped by the validator.

### Requirement: The synthesis is validated against Quranic usage and marked weak when it fails

The synthesized core sense SHALL be checked against the root's actual Quranic usage before it is
presented: the system SHALL compare it with the root's attested occurrences and, where available,
with the Maqāyīs aṣl for the same root. When the synthesis is not supported by usage, it SHALL be
marked weak, SHALL say so in the output, and SHALL be recorded in the coverage log. It SHALL NOT
be silently presented as if corroborated, and it SHALL NOT be silently deleted.

#### Scenario: A corroborated synthesis is shown as corroborated

- **WHEN** the synthesis for `سرع` (a sense of swift continuous motion) is checked against the
  root's 23 occurrences and against the aṣl «أصل صحيح يدل على خلاف البطء»
- **THEN** the block states that the synthesis agrees with the attested usage
- **AND** cites the aṣl and at least one naẓīr.

#### Scenario: An uncorroborated synthesis is marked weak

- **WHEN** the synthesis is not supported by the root's attested usage
- **THEN** it is presented as weak/تأويلي with an explicit statement that usage does not
  corroborate it
- **AND** the coverage log records reason `synthesis-unvalidated`.

### Requirement: The block covers only rooted words and says so for the rest

Rootless words (حروف, ضمائر, أسماء إشارة, most أعلام — 35.5 % of the corpus) have no root to
decompose. For them the block SHALL render as unavailable with a stated reason, and SHALL NOT
decompose the surface form's letters as a substitute.

#### Scenario: A particle gets no letter decomposition

- **WHEN** the الحروف block is assembled for 23:61:3 `فِى` (a حرف جر with no root)
- **THEN** the block is unavailable with a reason stating the word has no root
- **AND** no letter-by-letter reading of the surface form is produced.
