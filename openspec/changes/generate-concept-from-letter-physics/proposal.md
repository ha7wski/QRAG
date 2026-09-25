## Why

The `constrain-lisan-by-root-core` change fixed a real bug — a letter carries a *bundle* of
senses, and nothing was selecting among them — by letting Ibn Fāris' aṣl select. That fix has
a consequence its own spec did not anticipate: **the aṣl enters upstream, so nothing downstream
can say anything the aṣl does not already say.** A sense survives selection by sharing an axis
with the core, so the published reading is, structurally, a paraphrase of the core. `رحمة` is
the visible symptom — `ر` is selected out entirely and the reading asserts nothing about it —
but the symptom is not the point: an engine that can only agree with its input is not reading
the letters, it is restating a dictionary entry with extra steps.

The value the `/lexical` tab was supposed to deliver is a reading that comes from **somewhere
else** and can therefore be *checked against* the aṣl. This change inverts the direction a
second time and puts the aṣl on the far side of the pipeline: the concept is generated blind
from the measurable phonetics of each root letter, and Ibn Fāris becomes the **test**, not the
input.

The two engines ship side by side until the comparison is done. The core-first engine is not
touched, not deprecated and not flagged off by this change.

## What Changes

### The objective layer is read, and only the objective layer

- `data/references/arabic_letters_dataset.csv` already carries the tajwīd facts — `makhraj_ar`
  and `sifat` for all 28 letters. Nothing there is curated for this feature and nothing is added
  to it.
- **The same file's `ibn_jinni_note*` columns are banned from this path.** They are one frozen
  interpretive gloss per letter — exactly the artefact the whole `/lexical` history has been
  trying to get rid of. Reading them here would rebuild the original bug behind a new name.
- The raw `sifat` strings (19 distinct values) and `makhraj_ar` strings (23 distinct values for
  28 letters) are **reduced to a declared, closed feature vocabulary** before anything is mapped.
  A 23-value مخرج vocabulary over 28 letters is a per-letter glossary in disguise; it collapses
  to the five classical zones. A صفة carried by 24 of 28 letters distinguishes nothing; only the
  **marked** member of an opposed pair yields a feature, the unmarked member (انفتاح، استفال)
  being the default state.

### A frozen quality → primitive table

- Add **`data/references/physical_primitives.csv`** — one row per (physical feature, primitive),
  over a **closed vocabulary of at most 15 primitives**. It is written against the feature list,
  **before the first root is looked at**, and applied mechanically to every root with no per-root
  exception.
- **Each row declares a `status`.** `attested` carries a named authority and real pages;
  `hypothesis` is the project's own claim, carrying the uncontested tajwīd fact as its
  `physical_basis` and citing support without borrowing authority. No source tabulates the صفات
  into a general quality-to-notion mapping — Ibn Jinnī illustrates the principle on particular
  cases, Ḥasan ʿAbbās gives senses per letter — so most rows are the project's construction and say
  so. That is what makes `k / 40` able to falsify them.
- Add **`data/references/physical_primitives.lock.json`** — version, `frozen_on`, sha256 of the
  table's bytes, and a sourced `history[]`, on the exact model of `letter_senses.lock.json`.
  A change to the table is a new lock version justified by a feature-level authority with a page;
  it is never a fix for a root that reads badly.

### Composition is posed in advance and never adapted

- Positional rule, documented before the first root and invariant: **first letter opens the
  action, second is its body, third concludes it.** Quadriliteral roots (43 of 1656) and the 142
  roots whose key carries a hamza carrier or a bare alef need a declared rule each — stated in
  design.md, not improvised per root.
- Output is a **مفهوم**: one sentence, fixed, context-independent. The screen — not the engine —
  carries the distinction between a fixed مفهوم and a context-dependent معنى; that sentence is a
  UI requirement of this change.
- If a LLM phrases the sentence, it is **containment-checked**: it may only realise primitives the
  composition selected, and a phrasing introducing a notion absent from them is rejected, not
  shown. The deterministic template is the default and remains the ground truth.
- **No silent fallback.** A letter yielding no primitive makes the concept *partial*, the response
  says which letter is silent, and the screen says so.

### Confrontation replaces constraint

- After the concept is generated blind, the response carries alongside it the attested aṣl
  (`root_cores.json`, already on disk) and the root's real Quranic occurrences, plus a recorded
  verdict on whether the concept covers them. **Agreement is attestation; disagreement is a
  result to record, never a reason to retouch the table.**
- **The witness set is drawn now, and it is in this change** (design.md §7): 40 triliteral roots
  with a cited aṣl and ≥ 20 occurrences, drawn with seed `20260925`, excluding the 5 already-curated
  roots and the declared development case `ضرب`. It is never looked at during curation.
- **One metric is reported**: of the 40 witness roots, how many generated concepts cover *all*
  their attested uses. Not a per-letter match rate, not an average, not a partial-credit score. It
  is published with **one declared-in-advance split** — roots containing a signature letter
  (`ر ش ض ل ص ز س`) against roots that do not — because the rarity rule structurally favours the
  first group and the headline number would hide it.
- **A collision probe gates the whole curation.** The table maps 28 letters onto 18 profiles, so
  `ب`/`ج`/`د` and six other groups are indistinguishable to it. Before a single witness root is
  curated, real minimal pairs (`حرب`/`حرج`/`حرد`, `تبر`/`كبر`, `كود`/`كيد`) are composed and
  compared to their attested aṣl, on a criterion fixed beforehand — `identical` / `order-distinct` /
  `distinct`, the middle one counted as a partial collision rather than a pass. A single `identical`
  on an aṣl-divergent pair ends the probe: mapping the five classical مخرج zones becomes v1 of the
  table and work stops to report it.

### The two engines coexist

- Add **`POST /lisan/concept`**, mounted next to the untouched `POST /lisan/analyze`, and a
  comparison surface on `/lexical` that shows both readings for the same root.
- **Nothing in `linguistics/lisan/` is modified.** The new engine is new modules; `letter_senses.csv`,
  `root_cores.json`, `semantic_axes.json` and their locks are read-only inputs here.

## Capabilities

### New Capabilities
- `letter-physical-primitives`: the input layer — which columns of the letter sheet are in scope
  and which are banned, the reduction of raw مخرج/صفات to a closed feature vocabulary, the
  marked/unmarked rule, the ≤15-primitive table, its sourcing gate and its sha256 freeze.
- `root-concept-composition`: generation — the invariant positional rule, non-triliteral and
  hamza/alef root handling, partial concepts, the مفهوم output contract, LLM containment,
  `POST /lisan/concept`, and the `/lexical` presentation including the مفهوم/معنى statement.
- `concept-attestation-protocol`: evaluation — the blind-then-confront ordering, the frozen
  witness set, the single coverage metric, the `ضرب` acceptance case, and the rule that a
  recorded disagreement is never resolved by editing the table.

### Modified Capabilities
- `served-surface`: one route is added (`POST /lisan/concept`) and called by the frontend. The
  spec's invariant — mounted routes equal routes the frontend calls, and the removed six stay
  removed — is unchanged; the route list it enumerates gains an entry.

<!-- Deliberately NOT modified: `constrained-letter-reading`, `letter-sense-inventory` and
     `root-semantic-core` keep every requirement they have. This change adds a second engine; it
     does not amend the first. `dataset-registry` is unchanged — the two new files comply with its
     path-constant + loader + manifest rule rather than alter it. -->

## Impact

- **Data** — new: `physical_primitives.csv`, `physical_primitives.lock.json`. Each needs a
  `quran_data/paths.py` constant, a cached `quran_data/loaders.py` loader and a
  `quran_data/manifest.py` entry (`tests/test_quran_data.py` fails otherwise).
  `arabic_letters_dataset.csv` is read, never written.
- **Backend** — new package `linguistics/lisan/concept/` (feature extraction, primitive table
  store, composition, phrasing, confrontation). `api/models/lisan.py` gains the concept models;
  `api/routers/lisan.py` gains one route; `api/main.py` mounts it. Import direction unchanged:
  `linguistics/` reads `quran_data` and the injected `retrieval/` resolver, never `api/`.
- **Frontend** — `app/lexical/page.tsx` gains the concept panel and the engine comparison;
  `lib/lisanTypes.ts`, `lib/api.ts`, `lib/strings.ts`, plus Vitest files (local-only) and
  `tsconfig.test.json` type-checking.
- **Scripts** — `scripts/build_physical_primitives_seed.py` (pre-fills feature rows from the letter
  sheet, leaves the primitive and its citation to the curator — and, like
  `build_root_cores_seed.py`, may never write to the frozen table) and
  `scripts/validate_concept_datasets.py` (sourcing gate, ≤15 vocabulary, lock digest, and the
  witness-set integrity check).
- **Tests** (local-only) — `tests/test_physical_primitives.py` (freeze + vocabulary cap + the ban
  on `ibn_jinni_note`), `tests/test_concept_composition.py` (`ضرب`, partial concepts, determinism),
  `tests/test_concept_witness_set.py` (the drawn set is reproducible from the declared seed and
  has not moved).
- **Docs** — `documentation/` gains a French deep dive on this engine; `CLAUDE.md`'s
  `linguistics/lisan/` section gains the coexistence note.
- **Out of scope** — `/madar` stays quarantined; `linguistics/tahlil/huruf.py` and
  `arabic_letter_semantics_hasan_abbas.json` are untouched; no change to retrieval, indexing or
  the chat path.
