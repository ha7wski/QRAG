# Islambouli's letter table, transcribed and measured

This document records the measurement of a **published** letter table under the harness that
closed the physics-first engine at `k / 40 = 0`
([`lisan-concept-from-physics.md`](lisan-concept-from-physics.md)). The table is Samer
Islambouli's (سامر إسلامبولي، «علمية اللسان العربي وعالميته»), transcribed from a poster that
reproduces it. That engine's table was the project's own construction, so its failure left one
objection open: *the project's table failed, not the tradition's*. This table was written by
someone else. The project transcribed it and could not tune it, because changing a row would
mean no longer citing Islambouli.

---

## 0. The result, first

> ## **k / 40 = 0**, beside the closed engine's **k / 40 = 0**
>
> None of the 40 roots of the second holdout has a reading that covers **every** use frozen
> for it.

| | Islambouli table | closed physics table |
|---|---|---|
| `k / 40` | **0** | **0** |
| uses covered | 28 / 379 | 7 / 183 |
| misses: `imported` | 348 | 162 |
| misses: `direction` | 3 | 8 |
| misses: `inert` | 0 | 6 |
| misses: `collision` | 0 | 0 (1 failing root collides, computed separately) |
| signature-letter split (inherited) | 0 / 19 · 0 / 21 | 0 / 25 · 0 / 15 |

`python scripts/validate_islambouli_datasets.py` prints this block. It reads the closed figures
from `concept_attestation.json` at run time and never types them.

**The reservations travel with the number.**

- **R1 (inherited).** The harness's composition window was set after a measurement on the
  closed run's development case. Under this table it is non-binding (one gloss per position),
  and it is stated here rather than dropped.
- **R2 (source).** The table is transcribed from a poster, not from the book. Title and author
  are printed on the poster and transcribed. No page of the book has been read. The poster's
  origin is unrecorded. Row 12 carries a mark that could not be read.
- **R3 (method).** The positional rule is the harness's, not Islambouli's. A miss refutes
  *this table under this rule*, not his reading method, which the book may state differently
  and which was not read.
- **R4 (judge).** There is one judge. The committed records make the judgement redoable, and
  no independent review took place.
- **R5 (uses writer).** Agents blind to the table wrote these uses. The closed run's uses were
  written by a curator who knew that run's table. Blind writing may differ in nature, not only
  in severity. **Measured:** 379 blind uses against 183, so the blind lists are about twice as
  fine. On `ضرب`, all 5 reference uses have a blind match and the blind writer adds 4, which is
  `partial` under the rule fixed in advance. Under a metric with no partial credit, a finer list
  is harder to cover, so this `k` was measured on harder lists than the closed one was.
- **R6 (samples).** The two numbers share a frame and a method, not a sample: they come from
  two independent draws of 40. `ضرب` is the only root judged against identical uses under both
  tables, and it covers 1 of 5 under both.

**What the distribution says.** Once again the misses are overwhelmingly `imported`: the use
needs a notion the three row texts do not carry. Coverage lands where the table's own words
happen to name the use's notion:

- **time**, carried by `ي` («جهد ممتد زمانياً»): حين covers 7 of 8 uses, and misses only
  «لات حين مناص», where escape is imported;
- **cutting**, carried by `ق`: row ق is «قطع، أو وقف شديد», so for the witness root قطع the
  reading contains the root's own word, and 9 of the 28 covered uses are قطع's;
- **gathering** (`م` in جمع), **enclosure** (`ح` + `و` in حول), **pressure that sticks**
  (أذي).

The same boundary the closed run drew shows up again here. Once a gloss names God, a person,
knowledge, speech, affect, law or an object kind, that domain is imported and the use falls.

**Scope.** This is the result of *this table, transcribed from this poster, under this
positional rule and this criterion, on these 40 roots*. It is not a verdict on Islambouli's
method, which the book may state differently, nor on the معاني الحروف tradition.

---

## 1. The witness, and why the attribution rests on what it prints

The only witness is `data/source/islambouli_letters_poster.png`: 1132×1646, sha256
`e64906b3b351539cc600f1bff88c9156b703142f740df5a691fac56feabcac0c`.

**The first deposit was truncated.** It ended at row 28 and showed neither the book nor the
author. It was replaced by the original before any row was transcribed. That replacement is why
the attribution rests on the poster's own imprint rather than on anyone's statement. Read at 3×,
the imprint says:

| position | as printed | note |
|---|---|---|
| title band | دلالة أصوات الأحرف العربية فيزيائياً | kashida stretching not transcribed |
| banner | من كتاب : علمية اللسان العربي وعالميته / للأستاذ سامر إسلامبولي | two lines, no dash |
| footer | الإسلام الان - القراءة المعاصرة .... طريق الى الله | the mark on the alef of الان is unreadable |
| top edge | — | cut off by the frame, unreadable |

The lock records it (`witness_imprint`), with `pages: []` and the origin *supplied by the user,
origin unrecorded*.

## 2. The transcription

`data/references/islambouli_letters.csv` has 29 rows (poster rows 0–28). Each row is kept twice:
`text_as_printed` reproduces the image, with fused words, commas, periods and the legible marks,
and `text` is the same with spaces restored. The validator checks that the two differ by
whitespace alone. Every row is `transcribed_from_poster`, and no other status is accepted.

The copy was read row by row at 3× on the original. Beyond the fused words, the details that
matter are these:

- **row 12** «انتشار وتفش.»: a mark below the line could not be read, so it is left out and
  named;
- **the commas before «أو»** on rows 18, 20, 21 and 24: they decide what a trailing qualifier
  attaches to;
- **row 0**: a period, not a comma, after «ظهورمتوقف». Its clause «وهو جزء من صوت (آ)» stays
  text, and nothing structures it;
- **row 26** «إثارة» (ث, not ش), labelled «آ - ى».

`islambouli_letters.lock.json` v1.0.0 freezes the CSV by digest. A row changes only through a
new version that corrects a copy error proved on the image. The validator refuses a history
reason that cites a root or a result.

## 3. Is the table a system?

Before any root was read, each gloss was decomposed into alternatives and, per alternative, into
**action / intensity / ending**, using only words the gloss contains. The criteria and the
verdict rule were written in the design before the grid existed. The validator recomputes them
from the decomposition in `islambouli_letters_grid.json`.

**Verdict: PARTIAL SYSTEM** (identical under both readings of row 14's lone comma).

| | |
|---|---|
| C1 literal | holds |
| C2 exhaustive | fails: row 0's relation clause lies outside the scheme |
| C3 no form in two slots | holds |
| C4 discrimination | holds |
| rows with ≥ 2 slots | 23 / 29 |
| H2 emphatic one intensity step above its plain letter (ت→ط ذ→ظ د→ض), phonetically grounded | holds |
| H1 equal-intensity pairs differing by متوقف/ملتصق (ت/ث ط/ذ د/ظ, ض alone), a pattern with no phonetic claim | holds |
| H3 س/ص differ only by ending | holds |
| H4 ح/هـ differ only by intensity | fails: ح has a second alternative |

The دفع rows fill 7 of the 8 cells of intensity × {متوقف, ملتصق}; the empty cell is
شديد جداً × ملتصق. **The grid is an analysis, never an input.** No module of
`linguistics/lisan/islambouli/` may name it.

## 4. The protocol, in the order it ran

Each step is its own commit. The history is the evidence that the order held.

| step | commit |
|---|---|
| the harness is extracted and shared; the closed record replays byte for byte | `90a0b1d` |
| the second holdout is drawn (seed 20260928, 176 + 64 → 29 + 11), before any row existed | `92e1e6d` |
| the table is transcribed from the original poster | `9681268` |
| the system check | `fc626da` |
| the freeze, with the imprint | `142af29` |
| the composer, the blindness edge and the guard | `e48cb95` |
| the uses, written blind and frozen | `5c26985` |
| the readings, generated after the uses | `c98d522` |
| the verdicts | `b443f65` |

- **Same harness.** The draw, the guard, the uses record, the verdicts and the strict metric are
  imported by both engines from `linguistics/lisan/harness/`. They are not copied.
- **The reading.** Each radical's row text sits verbatim in its fixed position (opens · body ·
  concludes), with no sentence, connective or LLM. Every character of every QAC triliteral key
  has a row: hamza seats go to ء, bare ا to «آ - ى».
- **Blindness** is an import edge. No module but `confront.py` may reach or name a meaning
  dataset, either uses record, or `harness/verdicts.py`, and no module at all may name the grid.
- **The uses** were written by five fresh sub-agents that never saw the poster. Each read one
  batch of a reproducible bundle: Ibn Fāris' aṣl verbatim and every occurrence verse, with
  nothing from the table and no example drawn from the closed run. Each transcript shows only
  that read. Their outputs are recorded unchanged.
- **The criterion** is inherited verbatim, with two applications fixed before any reading: «أو»
  is disjunctive, and a row's whole text counts as said.

## 5. Redoing it

```bash
python scripts/validate_islambouli_datasets.py               # the result block, with R1–R6
python scripts/record_islambouli_verdicts.py worksheet       # every reading beside its uses
python scripts/draw_islambouli_witness_set.py --check        # replay the draw
python scripts/record_islambouli_verdicts.py bundle <dir>    # rebuild the blind writers' input
```

The frozen uses, the readings, every verdict with its reason, and the calibration are committed
in `data/references/islambouli_attestation.json`. Anyone can redo the judgement from them and
disagree.
