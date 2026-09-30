## Why

Samer Islambouli publishes, for a root, a **physical stage** (الحالة الفيزيائية) that is an
*assembly* of the three rows of his letter table: ضرب → «دفع شديد مكرر منتهٍ بجمع مستقر»,
كتب → «ضغط ودفع منتهٍ بجمع مستقر». The first radical leads, the second qualifies it, and the
third is attached by «منتهٍ بـ». Because the stage is only an assembly and not an interpretation,
a template can produce it without a model. The `/lexical` page already shows the three rows verbatim
under each letter, so the missing piece is the mechanical sentence those rows make together.

His **cultural stage** (الحالة الثقافية, ضرب → «إيقاع شيء على شيء يترك فيه أثراً») is a different
matter. None of the three rows contains it, and it is what both measurements scored at k / 40 = 0.
This change never generates it. It only quotes it where he published it, or shows a personal reading
that carries its author's name.

## What Changes

- **Deterministic assembly** of the physical stage from the three frozen Islambouli rows, with this
  schema: `<pos 1> <pos 2 as qualifier> منتهٍ بـ<pos 3>`. There is no model and no per-root rule,
  and the result carries the label «assemblage mécanique des trois lignes, non une définition».
- **Closed مصدر → وصف table**:
  - Frozen by a sha256 lock, versioned like the other `data/references/` tables.
  - Each entry is justified by morphology alone.
  - A word with no entry stays as written.
- **Explicit handling of «أو»**: eight rows carry an alternative (e.g. ك «وقف، أو ضغط خفيف»). Only
  two behaviours are allowed:
  - Both alternatives are shown. This is the default.
  - The user makes an explicit choice, shown as an interpretation with its author.
  
  No automatic path may select an alternative, and a test enforces that.
- **No LLM path is built.** The template's output is usable (design §D1). The existing containment
  veto would also let a model choose an alternative by omission (§D6), so any future re-wording
  needs a preservation check beside it.
- **Cultural stage**:
  - Shown only from a sourced Islambouli citation (a new frozen dataset with a witness per entry),
    or from a personal reading signed by its author.
  - If there is neither, the section is absent, with no placeholder.
- **Screen** (`/lexical`): root → the three rows verbatim (already there) → the assembled sentence
  with its label → the cultural stage, only when it is sourced.
- The two published roots, ضرب and كتب, are **declared development cases**. They are acceptance
  fixtures and enter no measurement.

## Capabilities

### New Capabilities
- `islambouli-physical-assembly`: covers the template, the مصدر→وصف table and its lock, the «أو»
  rule, the absence of any model, and the acceptance test against ضرب and كتب.
- `lisan-cultural-stage`: covers sourced citations and signed personal readings. The stage is
  never generated or inferred, and it is absent unless sourced.

### Modified Capabilities
- `served-surface`: adds the personal-reading routes (see design §D8) to the list of mounted routes
  that the `/lexical` page calls.

## Impact

- **New data**: `data/references/islambouli_wasf.csv` and its `.lock.json`, and
  `data/references/islambouli_citations.json` with its witnesses under `data/source/`. Each gets a
  `quran_data/paths.py` constant and a `manifest.py` entry.
- **New modules**: `linguistics/lisan/islambouli/assemble.py` and `wasf.py`.
- **API**:
  - `POST /lisan/analyze` gains `islambouli_assembly` and `cultural_stage`, joined in
    `api/routers/lisan.py` as the gloss already is.
  - The new personal-reading routes are backed by `api/store.py` (`data/runtime/app.db`).
- **Frontend**: `LisanResult.tsx` (the assembly block, the alternative toggle, the cultural block),
  `strings.ts` and `lisanTypes.ts`.
- **Unchanged**: the Islambouli letter table and its lock, both witness sets, the closed engine and
  its number, and `k / 40` for both tables.
