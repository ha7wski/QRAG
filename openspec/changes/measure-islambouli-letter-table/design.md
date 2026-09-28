## Context

The physics-first engine (`linguistics/lisan/concept/`) is closed at **`k / 40 = 0`** — 7 of 183
uses covered, misses `imported` 162 · `direction` 8 · `inert` 6. Its conclusion is scoped, in
`documentation/lisan-concept-from-physics.md` §10.1–10.2, to *this vocabulary, this rule, this
criterion, these 40 roots* — and the vocabulary was the project's own, every row `hypothesis`.

Samer Islambouli publishes a letter table (كتاب «علمية اللسان العربي وعالميته»): one gloss per
letter, phrased as a claim about what the sound *indicates* («صوت يدل على …»). Measuring it under
the harness that measured the closed engine gives a second number, comparable to the first
**because only the input table differs**.

What is on disk:

| Asset | State | Role here |
|---|---|---|
| `data/source/islambouli_letters_poster.png` — 1132×1646, sha256 `e64906b3b351539cc600f1bff88c9156b703142f740df5a691fac56feabcac0c` | supplied by the user | **the only witness of the table** |
| `concept_witness_set.json` — 40 roots, seed `20260925`, frame 280 (205 + 75) | frozen, **burned** (183 uses read) | frame and procedure reused; roots excluded |
| `concept_attestation.json` — uses, verdicts, criterion | frozen | criterion inherited verbatim; `ضرب`'s uses reused |
| `linguistics/lisan/concept/{confront,witness_guard}.py`, `scripts/{validate,record}_concept_*.py` | closed | table-agnostic parts extracted (D8), behaviour pinned byte-for-byte |

Two facts about the image govern the transcription status:

- **The first deposit was truncated, and the witness was replaced by the original before any
  transcription.** The image first placed at `data/source/islambouli_letters_poster.png` was a crop
  of the poster, ending at row 28. On that crop no title, author or book was visible, so a first
  draft of this note rested the attribution on the user's statement. The user then supplied the
  original (1132×1646, sha256 `e64906b3…abcac0c`), which replaced the crop before any row was
  transcribed. **This is why the attribution changes basis**: the original prints the book and the
  author, and they are transcribed from it.
- **The witness names the book and the author.** Read at 3× on the original, it carries four
  printed texts besides the table:
  - an orange **title band** above the table: «دلالة أصوات الأحرف العربية فيزيائياً», set with kashida
    stretching;
  - a red **banner** below it, on two lines: «من كتاب : علمية اللسان العربي وعالميته» /
    «للأستاذ سامر إسلامبولي»;
  - a yellow **footer**: «الإسلام الان - القراءة المعاصرة .... طريق الى الله»;
  - along the top edge, a line of white text cut off by the frame, which **cannot be read** and is
    not transcribed.

  Three details differ from the user's citation, and the image wins each time. First, the banner
  carries **no dash** between title and author: they sit on two lines. Second, the footer continues
  with «.... طريق الى الله», printed in red. Third, the alef in «الان» carries a mark that cannot
  be told apart as hamza or madda at this resolution, so the alef is transcribed bare, with a note
  — the same policy as row 12. The kashida in the title is not transcribed: the image cannot show
  whether it is typed tatweel or justification.
- **Origin of the image:** supplied by the user, origin unrecorded. The transcribed banner tells us
  which book it cites. It does not tell us where the image came from.
- **No page of the book has been read.** So no row can be `attested` with a page, and none will be.

### The user's reading, checked against the image

First checked on the truncated deposit, then **re-read row by row at 3× on the original** before transcription (task 2.2). The two reads agree on every row. The original added the two details marked for rows 0 and 28, which the first pass had missed.

Every row was read against the image, and the doubtful ones at 3× crops. **All 29 rows agree
letter for letter with the user's reading**, with these differences — the image wins in every case,
and the user's reading is not stored:

| row | letter | the image | the user's reading |
|---|---|---|---|
| 0 | ء | «ظهورمتوقف» and «وهوجزء» printed **fused**; a **period**, not a comma, after «متوقف»; «صوت(آ)» with no space; madda visible on آ; no final period | spaced, «،» after متوقف |
| 28 | ي | a space before the final period: «زمانياً .» | no space |
| 4, 5, 6 | ج ح خ | «أوشدة», «أوسعة», «أوطراوة» printed fused | spaced |
| 12 | ش | «وتفش.» — **no shadda visible**; a small mark below the line under ش could be a kasra/tanween or row 13's descender, and cannot be decided at this resolution | «وتفشٍّ» |
| 18, 20, 21, 24 | غ ق ك ن | a **comma before «أو»**: «غموض، أو غياب», «قطع، أو وقف شديد», «وقف، أو ضغط خفيف», «ستر، أو اختباء» | no comma |
| 26 | آ - ى | label printed «آ - ى»; «إثارة و امتداد» with a space after و; **«إثارة» confirmed** (one tooth under the three dots — ث, not ش) | «آ/ى», «وامتداد» |

The commas are not cosmetic: «قطع، أو وقف شديد» decides whether شديد qualifies قطع — see D11.

## Goals / Non-Goals

**Goals:**

- A second holdout of 40, drawn from the untouched remainder of the original frame by the original
  procedure, committed before any row is transcribed.
- A transcription whose only possible error — a wrong copy — is checked mechanically against a
  stored as-printed form.
- A published verdict on whether the table is a *system* (a few dimensions crossed) or a *list*
  (29 independent glosses), reached under criteria written here, before the grid exists.
- `k / 40` for the Islambouli table under the unchanged harness, printed beside `0 / 40`, with its
  reservations and its miss distribution.

**Non-Goals:**

- **No change to the closed engine's behaviour, data or number.** D8's extraction is gated on a
  byte-identical replay.
- **No interpretation of any row.** The composer places the verbatim text; the grid (D11) is an
  analysis artifact that no composing path may read.
- **No reconstruction of Islambouli's own reading method.** The positional rule is the harness's.
  What is measured is *this table under this rule* (R3).
- **No route, no page, no LLM phrasing.** The product surface is decided after the number exists.
- **No re-draw, no reserve list, no substitution.** A drawn root that turns out awkward is measured.

## Decisions

### D1 — The order is the protocol, and each step is its own commit

```
0  extract the harness (D8)      pure refactor, gated byte-for-byte; touches no data
1  draw the 40 (D2)              committed with its replay                ← before any row
2  transcribe the table (D3–D5)  committed with the identity check
3  decompose it (D11)            grid + verdict committed
4  freeze it (D6)                lock + digest + sourced history
5  freeze the uses (D7)          uses[] for the 40 + ضرب, no reading generated
6  generate, then judge          readings recorded; per-use verdicts; collision computed after
7  publish (D12)                 k / 40 beside 0 / 40, reservations attached
```

Step 0 precedes the draw so that the draw runs through **the same replay code** that reproduces the
closed holdout — "same method" as a fact of the call graph, not a claim. It reads and writes no
dataset.

A note on what has already happened: the poster was read during the writing of this note, to check
the user's reading. The draw cannot have been influenced by it — its frame, strata, order and seed
are all fixed below, before any draw runs.

### D2 — The second holdout: same frame, same strata, new seed fixed here

The frame is rebuilt with the **recorded** procedure and the **recorded** exclusions — the 5 roots
curated at the first draw (`خبث خير رحم ظلم كفر`) and `ضرب` — pinned as constants, not read from
today's `root_cores.json` (a growing curated set would silently move the frame). Preconditions,
asserted before sampling:

- the frame reproduces **280 = 205 + 75**;
- seed `20260925` over it reproduces the burned 40 exactly.

Then the burned 40 are removed: **176 + 64 = 240** remain. Draw:

```
rng = random.Random(20260928)
drawn_lower = sorted(rng.sample(sorted(lower_remaining), 29))
drawn_upper = sorted(rng.sample(sorted(upper_remaining), 11))   # same generator, lower first
```

**The seed is `20260928`**, fixed in this note before any draw. The per-stratum counts are the
original ones (29 / 11), which is also the proportional allocation of 40 over 176 / 64 after
rounding.

Recorded **after** the draw, as structure, never acted on: weak-radical count, hamza-carrier count,
bare-alef count (see D5), and overlap with every root the closed run exposed in any form — the 7
probe roots, the 130-pair widening (whose aṣl were published verbatim), and `ضرب`.

*Alternative rejected:* excluding those exposed roots from the frame. What the user defines as burned
is having read a root's **uses**; a probe root's aṣl was read, its uses never written. Excluding them
changes the frame, and the frame is part of what makes the two numbers comparable. The overlap is
published instead.

### D3 — Transcription: as printed, and a separated form provably equal to it

`data/references/islambouli_letters.csv`, one row per poster row:

| column | content |
|---|---|
| `row` | the poster's own index, 0–28 |
| `label_as_printed` | `ء`, `ب`, …, `هـ`, `آ - ى` |
| `text_as_printed` | the gloss exactly as the image shows it — fused words, commas, final period, diacritics that are legible (`بُعد`, `جداً`, `مكانياً`, `زمانياً`, the madda of `(آ)`) |
| `text` | the same, with spaces restored between fused words and nothing else |
| `status` | `transcribed_from_poster` — the only value this change admits |
| `reading_note` | empty, or what could not be read (row 12's mark) |

**Identity check** (validator, per row): `text` with all whitespace removed is byte-identical to
`text_as_printed` with all whitespace removed. So `text` can differ from the image **only in
spacing**, and that is proven rather than asserted.

**An unreadable mark is not transcribed.** Row 12 is stored as «انتشار وتفش.» with a `reading_note`;
the user's «وتفشٍّ» is not adopted, because the shadda is not on the image.

*Alternative rejected:* storing only a normalised text. Then the only evidence of what the poster
says would be our normalisation of it, and the one remaining risk — a wrong copy — would be
uncheckable.

### D4 — The ء row's relation is text, and stays text

«وهو جزء من صوت (آ)» is stored inside `text` and nowhere else. There is **no** structured field
(`part_of: آ`), no edge between rows, and the composer does not split the clause off: the reading of
a root with a hamza shows the row's full text. Structuring it would be interpreting it.

### D5 — Root-key letters to rows

| root-key character | row | basis |
|---|---|---|
| the 28 consonants | their own row (`ه` → `هـ`) | 1:1 |
| `أ ؤ ئ ء` | `ء` | the closed harness's explicit carrier table, reused unchanged (never `fold_carrier`, which deletes the hamza) |
| `ا` (bare) | `آ - ى` | **the user's decision**, adopted as stated |
| `و`, `ي` as radicals | `و`, `ي` | no exception — same as the closed harness |

Stated once, as a consequence: `آ` and `ى` occur in **0 of 1656** QAC root keys. The row is
reachable only through a bare `ا`, i.e. through exactly four roots (`اني اول هاء هات`), and in those
keys `ا` stands for a radical QAC spells without its hamza (`اول` is أول). The poster labels the row
with the vowel of length and the alef maqṣūra; mapping the bare radical onto it is a harness
decision, taken here before the draw. It fixes the four product-side partial readings; it reaches
the measurement only if one of the four is drawn, which D2 records.

With this table every character of every QAC root key maps to a row, so no triliteral reading can
be `partial`. The partial path stays in code, unreachable on today's data, and is tested.

### D6 — The freeze

`islambouli_letters.lock.json`: `version` `1.0.0`, `frozen_on`, `sha256` of the CSV bytes, and
`history[]` whose first entry's `source` is:

```json
{ "authority": "سامر إسلامبولي، «علمية اللسان العربي وعالميته»",
  "witness": "data/source/islambouli_letters_poster.png",
  "witness_sha256": "e64906b3b351539cc600f1bff88c9156b703142f740df5a691fac56feabcac0c",
  "witness_origin": "supplied by the user, origin unrecorded",
  "witness_imprint": [
    { "position": "title band",  "text_as_printed": "…", "text": "…", "reading_note": "…" },
    { "position": "banner",      "text_as_printed": "…", "text": "…", "reading_note": "" },
    { "position": "footer",      "text_as_printed": "…", "text": "…", "reading_note": "…" },
    { "position": "top edge",    "text_as_printed": "",  "text": "",  "reading_note": "cut off by the frame; unreadable" }
  ],
  "pages": [],
  "attribution_basis": "title and author printed on the witness, transcribed in witness_imprint; the witness was supplied by the user as a reproduction of the book's table" }
```

`witness_imprint` is held to the same rules as the table rows: legible marks only, and a
whitespace-stripped identity check between `text_as_printed` and `text`. It lives in the lock and not
in the CSV, because the CSV's rows are letters and the composer loads them. The validator requires
`attribution_basis` to name `witness_imprint`, requires the `banner` entry to be non-empty, and
accepts an empty text only together with a `reading_note` saying why (the top edge). `pages` stays empty: no page of the book has been read.

The validator refuses: a row status other than `transcribed_from_poster`; any non-empty `pages`
while that is so; a digest mismatch. **A row changes only to correct a transcription error proved
against the image**, through a new lock version whose reason names the row and the crop. Reading the
book later is a new version with pages — and any row whose book text differs from the poster is
recorded as that difference, with the measurement staying attached to the lock it ran on.

### D7 — The uses: same procedure, same freeze, same criterion

For each of the 40 new roots, `uses[]` is written from `morphology.json`'s occurrence list and the
Maqāyīs `verbatim`, and nothing else — one gloss and one verse reference per use, the verse
mechanically checked to belong to the root. Committed with every verdict `not_judged` and no reading
generated. `ضرب` stays the development case: its five uses are **copied** from
`concept_attestation.json` unchanged, it is confronted and published, and it counts toward neither
half of `k`. It is the one root measured under both tables against identical uses.

The coverage criterion is inherited **verbatim** (`ec3a807`): a use is covered when a reader given
only the realised readings in positional order, told nothing of the root, would recognise its notion
as something the reading says — nothing imported, not merely inert, direction holds; and the judge
may not use knowledge of the root to build the bridge. Two applications are fixed now, because the
unit changed from primitives to glosses:

- **«أو» is disjunctive.** A notion is said by a position when either alternative of that row's
  gloss says it. That is what the source's أو means; reading it conjunctively would require both.
- **The whole text counts.** Qualifiers («في الزمان والمكان», «في الشيء») and row 0's clause are part
  of what the reading says.

Miss classes unchanged — `imported`, `inert`, `direction`, `collision` — with `collision` computed
after the verdicts: two triliteral roots whose realised row sequences are identical. Under D5 that
is possible only through the hamza table, so the class is expected to be near-empty, and the closed
engine's reopening condition (مخرج granularity) has no analogue here. Said now, not discovered.

### D8 — The harness is extracted, not copied, and the extraction is proven inert

`linguistics/lisan/harness/` receives the table-agnostic parts, split by what they are allowed to
read:

| module | contents | may a composer import it? |
|---|---|---|
| `draw.py` | frame construction, replay, `sample` order | yes — root spellings and counts only |
| `guard.py` | `WitnessRootComposed`, runner detection, sanctioned recording context — parametrised by a holdout loader | yes — root spellings only |
| `verdicts.py` | uses reading, `verdict_for`, `counts_toward_k`, miss classes, the strict metric and its split | **no** — it reads glossed uses |

`concept/confront.py`, `concept/witness_guard.py` and the two `*_concept_*` scripts import from it.
**Gate:** the closed validator's full stdout and `record_concept_verdicts.py worksheet`'s output are
captured before the extraction and must be byte-identical after it, and every closed test passes
unchanged. If either replay differs, the extraction is reverted, not adjusted.

*Alternatives rejected:* copying the code into the new package — two copies drift, and "same method"
becomes a sentence; importing `concept/confront.py` from the new package — it imports the closed
composer and reads the aṣl, and `concept/witness_guard.py` hard-codes its holdout.

### D9 — The composer, and its blindness edge

`linguistics/lisan/islambouli/compose.py` returns, for a triliteral root:

```
Reading(root, table_version, table_sha256,
        positions = [ (opens|body|concludes, root letter, poster row, text) × 3 ])
```

Nothing else: **no sentence, no connective, no template, no LLM.** The closed engine licensed each
word of its sentence from a primitive's declared lemmas; here the only licensed words are
Islambouli's, and any connective the project wrote between his glosses would be the project speaking
in his name. The judge is given the three texts in positional order — which is exactly what the
criterion says the reader is given.

The inherited composition constants apply and are **non-binding**: positions fixed (opens · body ·
concludes); within a position, rarity ordering and a window of 3 operate on a list that here has
exactly one member. The quadriliteral refusal is inherited unchanged.

**Blindness is an import edge**, written into `tests/test_import_direction.py` before the package
exists. No module under `islambouli/` but `confront.py` may reach or **name**: `root_cores`,
`maqayis_asl`, `letter_senses`, `semantic_axes`, `arabic_letter_semantics_hasan_abbas`,
`concept_attestation`, `islambouli_attestation`, `physical_primitives`, `arabic_letters_dataset`,
nor `harness/verdicts.py`. **`islambouli_letters_grid` is banned from every module of the package,
`confront.py` included** — only the validator reads it. Those two bans are what make "the grid never
feeds a reading" and "the composer never sees a use" facts of the build. The composer reads
one dataset: the table and its lock, digest-checked at load.

### D10 — The guard covers the new 40

Under a test runner, `islambouli/compose.py` raises `WitnessRootComposed` for any of the new 40 from
its first line — no warning mode, no flag. The closed engine's guard over the burned 40 stays as it
is. `scripts/record_islambouli_verdicts.py` takes the sanctioned context explicitly. Tests that need
a triliteral root use one off both holdouts.

### D11 — The system check: criteria before grid

**Parsing.** The formula «صوت يدل على» (row 0: «صوت خفيف يدل على») is the table's frame and is not
decomposed. After it, each gloss is split on «،» and «أو» into alternatives; within an alternative,
content words are assigned to three slots:

- **action** — the head noun of the alternative;
- **intensity** — from the closed scale `خفيف · وسط · شديد · شديد جداً`;
- **ending** — any other qualifier. Its vocabulary is **whatever the table contains**, not a list
  written beforehand (the table has `منضبط`, `منضم`, `ثقيلة`, `لازمة`, `مكانياً`, `زمانياً`, which the
  initial list did not).

A qualifier attaches to the **nearest** noun: «قطع، أو وقف شديد» is `قطع | وقف·شديد`, not
`قطع·شديد | وقف·شديد`. Uniform, fixed now, never chosen per row. Row 0's «خفيف» qualifies «صوت», not
the action, and is recorded as such.

**Criteria**, each reported:

- **C1 Literal.** Every slot value is a substring of that row's `text` — checked mechanically. The
  grid cannot contain a word the poster does not.
- **C2 Exhaustive.** Every content word lands in exactly one slot; anything left is `residue`, named.
- **C3 No same-form contradiction.** One word form never occupies two different slots across the
  table. Cross-slot reuse at the **root** level (`شدة`/`شديد`, `وقف`/`متوقف`, `ضم`/`منضم`) is reported
  as an observation, not a contradiction.
- **C4 Discrimination.** No two letters share a full decomposition.
- **Series hypotheses**, declared now, evaluated on the grid:
  - **H2 — the hypothesis with phonetic support.** Each emphatic sits one intensity step above
    its plain counterpart: `ت→ط`, `ذ→ظ`, `د→ض`. These are the phonetic plain/emphatic pairs
    (`ت/ط`, `د/ض`, `ذ/ظ`, and `س/ص` for H3), so if the table encodes emphasis, this is the shape it
    should take.
  - **H1 — admissible as a pattern, without phonetic grounding.** The دفع rows pair at equal
    intensity and differ only by ending `متوقف`/`ملتصق`: `ت/ث` خفيف · `ط/ذ` وسط · `د/ظ` شديد, with
    `ض` alone at شديد جداً. The regularity can be checked, but these pairs are **not**
    plain/emphatic pairs (`ت/ث` are both plain; `ط/ذ` differ in emphasis *and* manner), and no
    phonetic motivation for them is claimed here.
  - The grid decides whether the table encodes either pattern, both, or neither.
  - **H3**: `س/ص` differ only by ending. **H4**: `ح/هـ` differ only by intensity.

**Found while applying the rule (recorded, not resolved by preference).** «split on «،» and «أو»»
was written with the «، أو» of rows 5, 18, 20, 21 and 24 in view. Row 14 («دفع شديد جداً، متوقف»)
carries a «،» with no «أو» after it. Read literally, the rule splits it, and «متوقف» becomes an
alternative with no action. The grid records the literal reading as primary and the «، أو» reading
beside it, and the validator computes the verdict under both. They agree (`partial system`), so
the ambiguity does not decide anything. Had they disagreed, both would have been published.

**Verdict**, by a rule fixed now:

- `system` — C1–C4 hold with no residue, and H1 or H2 holds in full;
- `partial system` — C1, C3, C4 hold; the rows outside the scheme are named and counted;
- `list` — C3 or C4 fails, **or** fewer than 15 of 29 rows decompose into two or more slots.

**What the verdict changes is stated now.** It changes what a result means, never how it is
obtained. Under `system`, a miss bears on a generative principle; under `list`, `k / 40` measures 29
independent glosses and nothing more. The verdict is printed with the number.

### D12 — Publication

`scripts/validate_islambouli_datasets.py` prints, in one block: `k / 40` for this table; `0 / 40`
**read from the closed record at run time**, never typed; per-use coverage; the miss distribution by
class for both; the inherited signature-letter split (`ر ش ض ل ص ز س`), labelled as inherited for
comparability — its rationale was rarity ordering, which is non-binding here; the D11 verdict; and
the reservations, **with the number and not by reference**:

- **R1 (inherited).** The harness's window was set after a measurement on `ضرب`. Under this table
  it is non-binding — one gloss per position — and that is stated, not used to drop R1.
- **R2 (source).** Transcribed from a poster, not from the book. Title and author are printed on
  the poster and transcribed. No page of the book has been read. The poster's origin is not recorded.
  Row 12 carries a mark that could not be read.
- **R3 (method).** The positional rule is the harness's, not Islambouli's. A miss refutes *this table
  under this rule*, not his reading method, which the book may state differently and which was not
  read.
- **R4 (judge).** One judge. Audit possible, not performed.
- **R5 (uses writer).** The closed run's uses were written by a curator who knew its table. This
  run's uses are written by an agent that never saw the poster (D13). Blind writing may produce uses
  that differ in **nature** — granularity, which senses are split, what counts as a distinct use — and
  not only in severity. So the claim "this can only lower `k`" is plausible but **not demonstrated**.
  The `ضرب` calibration is the only measurement of that difference, and its figures are printed here:
  reference uses, blind uses, matched, unmatched on each side, and the concordance verdict.
- **R6 (samples).** The two numbers share a frame and a method, not a sample: they are two
  independent draws of 40. `ضرب` is the only root judged against identical uses under both.

`documentation/lisan-islambouli-table.md` carries the same block, the grid and the verdict, in
English. `lisan-concept-from-physics.md` §0 gains one line pointing at it.

## Risks / Trade-offs

- **[The table is short enough to compose in one's head]** → Whoever writes the uses after reading
  the poster can see each root's reading before it is generated; the closed run's 21-trait, 20-primitive
  table with rarity ordering did not allow that. The uses-before-generation order therefore protects
  less than it did. → The uses are written blind (D13), and the change of writer is carried as R5
  with its calibration figures.
- **[The poster is a copy of a copy]** → A typesetting error on the poster becomes ours. Mitigation:
  R2, and the lock's upgrade path when the book is read; the measurement stays attached to the lock
  it ran on.
- **[The extraction breaks the closed record]** → byte-identical replay gate; revert on any diff.
- **[A tempting row edit]** → A row changes only against the image (D6). Any other change means the
  table is no longer Islambouli's, and the validator's identity check plus the lock make it loud.
- **[The grid becomes an input]** → Banned by name from the composer (D9).
- **[A drawn root is awkward]** → No re-draw. It is measured and, if it misses, classed.
- **[`k > 0` is read as vindication]** → R3 and the D11 verdict are printed with it; one table under
  one rule on 40 roots.

## Migration Plan

Additive. Step 0 is the only edit to existing code, and it is reverted on any output difference. No
schema, route or frontend change; nothing to roll back in production.

### D13 — The uses are written blind, and the writer is calibrated on `ضرب`

**Writer.** The `uses[]` of the 40 are written by a fresh sub-agent that has never seen the poster.
Its prompt carries, **inline**, everything it may use: the procedure (D7), the root list, each root's
`morphology.json` occurrences and its Maqāyīs `verbatim`. It is told to use no tool, so no file of
the repository — the Islambouli files, and `concept_attestation.json` in particular — can enter its
context. That restriction is **by instruction**; the harness does not enforce it, and the meta says
so. The prompt goes into `islambouli_attestation.json`'s meta verbatim, and so does the returned
output before any editing. Editing that output is limited to checking that each verse belongs to its
root; a failed check is recorded, not repaired by hand.

**Calibration, in the same pass.** The same agent, in the same prompt, also writes `ضرب`'s uses.
They are stored as `ضرب` / `uses_blind`, next to the reference `uses` copied unchanged from the
closed record. The reference copy remains the reference, and `uses_blind` counts in **no** `k`.
Both versions are published side by side:

- **Matching.** Each reference use is matched to at most one blind use naming the same notion.
  Matching is done before any reading of `ضرب` is looked at, and each match gets a one-line reason.
- **Figures.** Reference uses (5), blind uses (n), matched, unmatched on each side.
- **Verdict, rule fixed now.** `concordant` if at least 4 of 5 reference uses are matched and at
  most 2 blind uses are unmatched. `strong divergence` if fewer than 3 of 5 are matched.
  `partial` otherwise.
- **Coverage.** The blind version is also judged against this table's reading of `ضرب`, published,
  and counted nowhere.

**If the verdict is `strong divergence`**, the result also bears on the published `0 / 40`, whose uses
were written the non-blind way. It is reported in both documents **as such, and not resolved**: no
re-freeze, no re-judging of the closed 40, no adjustment of either number.

## Resolved Questions

1. **Who writes the uses?** A blind sub-agent (D13), carried as R5 together with the `ضرب`
   calibration.
2. **The poster's origin.** "Supplied by the user, origin unrecorded", in the lock's
   `witness_origin`. The book it cites is known from the transcribed banner.

## Resolved blocker

- The truncated first deposit was replaced by the original before step 2 (see Context). No row had
  been transcribed at that point.
