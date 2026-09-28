## Why

The physics-first engine closed at `k / 40 = 0`, and its conclusion is scoped to **one
formalisation written by this project** (`documentation/lisan-concept-from-physics.md` §10.2): a
table the project built, every row `hypothesis`. That left the obvious objection standing — *the
project's table failed, not the tradition's*. Samer Islambouli's letter table («علمية اللسان العربي
وعالميته») is a table **published by someone else**, one gloss per letter, that claims exactly what
`k / 40` tests. Measuring it under the **unchanged** harness answers that objection with a second
number that is comparable to the first.

The nature of the risk changes with the source. A table the project curates can be tuned; a table
the project **transcribes** cannot be, without ceasing to cite it. The one risk left is the
accuracy of the copy — and that risk is mechanical, so it is checked mechanically.

This is **not** a rescue of the closed engine. The closed spec refuses widening its feature
vocabulary, subdividing the حلق and moving its window. None of those happens here: the closed
engine's code, table, lock, witness set, verdicts and number stay exactly as committed. What changes
is the **input table**, replaced wholesale by a third party's, measured on a **fresh** holdout.

## What Changes

- **A second witness set, drawn first.** 40 roots from the ~240 of the original 280-root frame not
  already drawn (the first 40 are burned: their 183 uses have been read). Same frame criteria, same
  two strata and per-stratum counts (29 + 11), same generator order, new seed fixed in this note.
  Committed, with its replay, **before a single table row is transcribed**.
- **The Islambouli table, transcribed from the poster** (`data/source/islambouli_letters_poster.png`,
  sha256 `e64906b3…abcac0c`, the original — a truncated first deposit was replaced before any transcription). 29 rows, each carrying the text exactly as printed and a word-separated form
  provably identical to it up to spaces. Every row's status is `transcribed_from_poster`; **no row is
  `attested`**, and no page is recorded, because no page of the book has been read.
- **A system check of the table, before any root.** Each gloss decomposed into (action, intensity,
  ending) using only words the gloss itself contains, against criteria written in this note. The
  resulting grid is published with a verdict — `system`, `partial system` or `list` — and it
  **does not feed the composer** in any case.
- **The table frozen** by digest and lock, with a sourced history — the same freeze discipline as
  `letter_senses.csv` and `physical_primitives.csv`.
- **The harness, shared rather than re-implemented.** The table-agnostic parts of the closed
  engine's harness — draw replay, witness guard, uses record, per-use verdict, strict metric, miss
  classes, computed collision — move to one shared module, gated by a byte-identical replay of the
  closed engine's validator output. Only the composer is new, and it does one thing: it places each
  radical's gloss, verbatim, in its fixed position.
- **The measurement.** Uses frozen for the new 40 after the table is locked and before any reading
  is generated; readings generated blind; each use judged under the committed coverage criterion;
  `k / 40` published beside `0 / 40`, with the inherited reservation, the new reservations, the
  inherited signature-letter split and the miss distribution by class.
- **No route, no page** in this change. The product surface is a separate decision taken after the
  number exists.

## Capabilities

### New Capabilities
- `islambouli-letter-table`: the transcription of the poster — verbatim storage, the
  printed-vs-separated identity check, `transcribed_from_poster` status, the row that carries a
  relation (ء «جزء من صوت (آ)») recorded as text, the freeze, and the prohibition on editing a row
  for any reason but a transcription error proved against the image.
- `letter-table-system-check`: the pre-declared decomposition into (action, intensity, ending), its
  literal-substring constraint, the verdict vocabulary and the rule that the grid never reaches the
  composer.
- `letter-table-measurement`: the second holdout, the composer that places verbatim glosses by
  position, the blindness edge for the new package, the witness guard over the new 40, and the
  publication of `k / 40` beside the closed result.

### Modified Capabilities
- `concept-attestation-protocol`: the witness-set requirement names **one** holdout drawn once;
  it must now admit a second, independent holdout for a different table without that reading as a
  re-roll of the first. The closed-experiment requirement gains an explicit clause that replacing
  the input table by a published third-party table, on a fresh holdout, under the unchanged harness,
  is a new experiment and not one of the refused rescues.

## Impact

- **New data** (`data/references/`): `islambouli_witness_set.json`, `islambouli_letters.csv`,
  `islambouli_letters.lock.json`, `islambouli_letters_grid.json`, `islambouli_attestation.json`.
  Each gets a `quran_data/paths.py` constant and a `manifest.py` entry. The poster stays in
  `data/source/` as the original.
- **New code**: `linguistics/lisan/harness/` (extracted, table-agnostic),
  `linguistics/lisan/islambouli/` (composer + confrontation),
  `scripts/validate_islambouli_datasets.py`, `scripts/record_islambouli_verdicts.py`,
  `scripts/draw_islambouli_witness_set.py`.
- **Touched, behaviour-preserving**: `linguistics/lisan/concept/{confront,witness_guard}.py` and
  `scripts/{validate,record}_concept_*.py` import the extracted pieces; their output must replay
  byte-for-byte.
- **Tests (local-only)**: `test_import_direction.py` gains the new package's blindness edge;
  new tests for the draw, the transcription identity, the lock, the guard and the metric.
- **Docs**: `documentation/lisan-islambouli-table.md` (new, English per the repo rule), a pointer
  from `lisan-concept-from-physics.md` §0, and `CLAUDE.md`'s `linguistics/` section.
- **No API, frontend or served-surface change.**
