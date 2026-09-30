# islambouli-physical-assembly Specification

## Purpose
The project's mechanical junction of a root's three Islambouli rows, shown beside what Islambouli himself published. It is not his physical stage: his two published stages (ضرب, كتب) carry per-root editorial decisions (which words count, how rows join) that no fixed template reproduces, so the gap is pinned and displayed rather than closed. «أو» alternatives are never chosen automatically.
## Requirements
### Requirement: The physical stage is assembled by a fixed template, with no model
The system SHALL assemble a trilateral root's physical stage as `<seg(pos1)> <wasf(seg(pos2))> منتهٍ ب<seg(pos3)>`.
In it, `seg` is the row's meaning segment: the text after «يدل على», up to the first sentence-ending full stop, verbatim.
The only material added SHALL be:
- the constant «منتهٍ ب»;
- single spaces;
- the alternative brackets «( )».

No word SHALL be dropped, reordered or added. There SHALL be no per-root or per-letter rule.
The assembly module SHALL NOT import `llm_client`, `random` or any scoring module.

#### Scenario: ضرب is assembled from rows ض ر ب
- **WHEN** the root ضرب is assembled with no personal reading
- **THEN** the sentence is exactly «دفع شديد جداً، متوقف مكرر منتهٍ بجمع مستقر»

#### Scenario: كتب is assembled with both alternatives
- **WHEN** the root كتب is assembled with no personal reading
- **THEN** the sentence is exactly «(وقف، أو ضغط خفيف) دفع خفيف متوقف منتهٍ بجمع مستقر»

#### Scenario: A non-trilateral root or a silent position gives no assembly
- **WHEN** a root has other than three radicals, or one of its letters has no row
- **THEN** no sentence is produced, and the refusal code and reason from `compose()` are returned

### Requirement: The gap to Islambouli's published sentences is recorded, not closed
The published physical stages of ضرب and كتب SHALL be kept as a fixture beside the template's output, together with the exact word-level diff (design §D1).
A change that alters that diff SHALL fail a test.
ضرب and كتب SHALL be declared development cases.
They SHALL be disjoint from both witness sets and SHALL enter no measurement.

#### Scenario: The diff is pinned
- **WHEN** the acceptance test runs
- **THEN** the ضرب diff is exactly the extra «جداً، متوقف»
- **AND** the كتب diff is exactly the four gaps (a)–(d) of design §D1

#### Scenario: A development case cannot enter a holdout
- **WHEN** the development cases are compared with `concept_witness_set.json` and `islambouli_witness_set.json`
- **THEN** the intersection is empty

### Requirement: A closed, frozen مصدر → وصف table
Position 2's alternative head words SHALL be replaced only through `data/references/islambouli_wasf.csv`.
That file SHALL be frozen by a sha256 lock with version history, SHALL be verified at load, and SHALL be capped at 20 entries.
Every entry SHALL be the مصدر of a derived form whose اسم الفاعل and اسم المفعول share one unvocalized spelling, and SHALL carry that justification.
A word with no entry SHALL stay as written.
A lock mismatch SHALL suppress the assembly.

#### Scenario: تكرار becomes مكرر
- **WHEN** row ر stands in position 2
- **THEN** its segment renders as «مكرر»

#### Scenario: A form I مصدر is left as written
- **WHEN** row ت stands in position 2
- **THEN** its segment renders as «دفع خفيف متوقف»

#### Scenario: Tampered table
- **WHEN** the CSV's sha256 differs from its lock
- **THEN** loading raises and `POST /lisan/analyze` omits `islambouli_assembly`

### Requirement: No automatic path selects an alternative
A segment split at «أو» (with its optional preceding «،») SHALL form an alternative group.
Without a signed personal reading, every group SHALL be rendered whole and verbatim inside «( )».
A single alternative SHALL be rendered only from a stored personal reading's `choices`.
It SHALL be labelled on screen with that reading's author as an interpretation.
No request field, default, environment variable, heuristic, score or model SHALL supply a choice.

#### Scenario: Every alternative survives by default
- **WHEN** every row is assembled at every position with no personal reading
- **THEN** every alternative of every group appears in the sentence

#### Scenario: A choice in the request body is not honoured
- **WHEN** `POST /lisan/analyze` is called with a choice in its body
- **THEN** the returned sentence still contains every alternative

#### Scenario: A signed choice is shown as such
- **WHEN** a personal reading by author A chooses alternative 2 of position 1 for كتب
- **THEN** the sentence is «ضغط خفيف دفع خفيف متوقف منتهٍ بجمع مستقر»
- **AND** `choice.author` is A
- **AND** the screen marks it as A's interpretation

### Requirement: The assembled sentence is labelled as the project's, not Islambouli's
The `/lexical` page SHALL show the assembled sentence after the letter cards.
Its label SHALL be exactly «تركيبٌ آليٌّ للأسطر الثلاثة، من صنع هذا التطبيق — لا تعريفٌ، ولا قولُ إسلامبولي».
The alternative groups SHALL be visibly bracketed.

#### Scenario: Label present
- **WHEN** a trilateral root with three rows is analysed
- **THEN** the assembly block renders after the letter cards, with that exact label

### Requirement: Islambouli's own physical sentence is shown beside the assembly, with the gap named
When a physical-stage citation exists for the root, the page SHALL show:
- that sentence verbatim, above the assembly, under its label as printed, with labels not unified;
- the gap: the words present in one sentence and absent from the other, computed from the two texts.

#### Scenario: ضرب shows the gap
- **WHEN** ضرب is analysed
- **THEN** the page shows «دفع شديد مكرر منتهٍ بجمع مستقر» under «الحالة الفيزيائية»
- **AND** it shows the assembly under its label
- **AND** it shows «جداً» and «متوقف» as the words only the assembly has

#### Scenario: كتب keeps its printed label
- **WHEN** كتب is analysed
- **THEN** Islambouli's sentence is shown under «مفهوم», not «الحالة الفيزيائية»

#### Scenario: No citation, no comparison
- **WHEN** a root has no physical citation
- **THEN** only the assembly is shown, with no gap block

### Requirement: Segment notes record ambiguities without creating rules
`islambouli_wasf.lock.json` SHALL carry `segment_notes` for rows ء, ع and ض (design §D2).
`islambouli_letters.csv` and its digest SHALL be unchanged.

#### Scenario: The letter table is untouched
- **WHEN** the change is applied
- **THEN** `islambouli_letters.csv` still hashes to the digest cited by `islambouli_attestation.json`

