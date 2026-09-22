## Context

`/lexical` (voie 1, `POST /lisan/analyze`) reads a root letter by letter. `letter_lexicon.describe()`
returns **one** `abbas_meaning_ar` per letter and `synthesis_template.render_synthesis()` chains them
in root order, then prints the union of their keywords as «صورة عامة». Nothing in that path knows
what the root means, so nothing can prefer one sense of a letter over another — there is only one on
file. On `خ-ي-ر` the result is «القذارة والخشونة والخواء … فساد» against Ibn Fāris' «أصله العطف
والميل».

Three facts about the existing repo shape this design more than anything else:

1. **The core data is already here.** `data/references/maqayis_asl.csv` holds 4 662 roots, 3 326 with
   a cited aṣl, read by `linguistics/madar/maqayis_store.py` — a live module on the request path.
   1 149 of the 1 656 QAC roots have a `has_asl` row. This change does not need a new corpus, it
   needs a structured layer over one the repo already ships.
2. **This feature has already been burned by generation, twice.** The Lisan synthesis was an LLM step
   until qwen2.5:7b produced corrupted tokens and prose contradicting the attested sense; `/madar` is
   quarantined for the same reason. Whatever selects a sense here must be inspectable by reading it.
3. **Roots are stored in exact, hamza-bearing spelling.** A curated list keyed on the folded form
   silently stops matching and the default takes over — the failure has already happened once in
   `mizan.py`'s curated lists. The Maqāyīs CSV is keyed on the *fold*; this dataset must not be.

## Goals / Non-Goals

**Goals:**

- Invert the pipeline to `root → attested core → constrained letter reading → synthesis`.
- Make the *bundle* of senses per letter first-class, and make the selection among them explainable
  in the response itself (which axes matched, why each rejected sense was rejected).
- Make the absence of a core a visible, documented outcome rather than a fallback.
- Detect — never repair — a reading that contradicts its own core.
- Keep the whole path deterministic, offline and LLM-free.

**Non-Goals:**

- Fixing letter symbolism as a discipline. This remains an interpretive framework; the disclaimer
  stays in every response. The goal is that the reading stops contradicting the citation it sits next to.
- Reaching full coverage of the QAC root set. Coverage is bounded by Maqāyīs and by curation time.
- Touching `linguistics/tahlil/huruf.py`, `arabic_letter_semantics_hasan_abbas.json`, `/madar`'s
  quarantine, or any retrieval path.
- Introducing a model anywhere in this pipeline.

## Decisions

### D1 — Invert the pipeline; do not patch the glosses

**Chosen:** compute the core first and let it constrain the letters.

Alternatives rejected: (a) *fix the `خ` row* — the same row is right for `خ-ب-ث` and wrong for
`خ-ي-ر`, so there is no single correct value; (b) *blacklist negative words for positive roots* —
that is a sentiment filter, it needs the answer it is meant to produce, and it would silently break
`خ-ب-ث`; (c) *drop the feature* — the letter reading is the point of the page.

### D2 — The core comes from Ibn Fāris, cited verbatim

**Chosen:** `root_cores.json`, curated from `maqayis_asl.csv`, storing Ibn Fāris' own words in
`verbatim` and a curated `gloss` beside them — never instead of them.

Alternatives rejected: (a) *generate cores with an LLM* — the exact failure mode the feature already
suffered, and the core is now load-bearing for every letter selection, so an invented core corrupts
the whole reading rather than one paragraph; (b) *derive axes by keyword-matching the aṣl prose* —
«خلاف الطيب» and «خلاف الضياء والنور» both define a root by its negation, which keyword extraction
reads backwards; (c) *use Lisān al-ʿArab* — much larger, not shipped, and it gives usage senses where
what is needed is precisely the *aṣl*, the etymological core.

### D3 — A closed axis vocabulary, in its own file

**Chosen:** `semantic_axes.json` — a finite list of axes, each with an id, an Arabic label, and an
optional symmetric `antonym` link. Cores and letter senses both tag against it, by id.

Rationale: the selection step is a set intersection between the core's axes and a sense's axes. With
free-text axes, «ميل» and «الميل والانعطاف» do not intersect, and agreement becomes an accident of
wording — the mechanism would appear to work and fail unpredictably. The `antonym` link is what turns
"these two share nothing" into a distinguishable "these two are opposed", which the guard and the
`conflicting-axis` rejection reason both need.

Alternatives rejected: (a) *free-text axes with fuzzy string matching* — reintroduces silent
mismatch, and the threshold becomes an unauditable magic number; (b) *sentence embeddings between
gloss and aṣl* — plausible-looking, untraceable, and it would make the reading depend on a 1.1 GB
model on a page that currently costs nothing (`HybridSearch` is lazy precisely so the lexical pages
hold no model memory); (c) *axes inline in each dataset* — no shared namespace, no validation, same
failure as (a).

A third file is real cost. It buys the only thing that makes «appariement avec les axes du noyau» a
definition rather than an intention.

### D4 — Ranking is a total, hand-written tuple

**Chosen:** eligibility (shares ≥1 axis, conflicts with none) then
`(shared axes, position fit, source confidence, −declaration index)`, highest first.

Every component is visible in the response, and the last term makes ties resolve by the curator's own
ordering rather than by dict iteration order. Position fit is not decoration: Ḥasan ʿAbbās states
position-dependent values (`position_notes` in the sibling JSON already records this), so a sense
that only applies word-initially should lose to one that applies where the letter actually sits.

Alternatives rejected: (a) *weighted numeric score* — the weights would be invented and would need
tuning against the very examples they are meant to judge; (b) *ask a model to pick* — see D2 and
constraint 2 above; (c) *always take the highest-confidence sense* — ignores the core, which is the
whole change.

### D5 — Split the letter dataset in two

**Chosen:** `arabic_letters_dataset.csv` keeps 28 letter-level rows (identity + phonetics);
`letter_senses.csv` holds one row per (letter, sense).

A single denormalized CSV would repeat `makhraj_ar` and `sifat_ar` on every sense row and let them
drift per row. The manifest records `arabic_letters_dataset.csv`'s only consumer as
`letter_lexicon.py`, so dropping the meaning columns breaks nothing else.

### D6 — Key on the canonical root key, and canonicalize on the way in

**Chosen:** `root_cores.json` keys are the exact spelling `LexicalRetriever._canon` returns; lookups
pass through `_canon`; the seed script folds with `normalize_root` only to *find* the Maqāyīs row.

This is the one place where a plausible shortcut — reusing the Maqāyīs key, since that is where the
data comes from — produces a dataset that matches ~0 hamzated roots and degrades to "no core", which
looks exactly like normal uncovered-root behaviour. Validation asserting every key is a real QAC root
key is what makes it loud.

### D7 — Multi-aṣl roots yield parallel readings

**Chosen:** one reading per core, never a merge. Pooling the axes of ظلم's two aṣl («خلاف الضياء
والنور» and «وضع الشيء غير موضعه تعديا») would make almost any sense eligible and rebuild the blend
this change removes. Which aṣl the user finds convincing is a scholarly judgement the tool presents,
not one it makes.

### D8 — The guard is a detector

**Chosen:** compare the aggregate pole of the selected senses against the core's polarity, report a
divergence, change nothing.

A corrective guard — re-ranking until the poles agree — would make the tool incapable of ever
disagreeing with the aṣl, i.e. it would always look right. The user's own `ك-ف-ر` worry is exactly
this: a constraint that forces the answer. The guard firing is information about the *data*; the fix
is curation.

Corollary worth writing down: **a guard that never fires is a warning sign, not a success.** It would
suggest the letter senses were curated to fit the cores (see R1).

### D9 — Polarity is a property of the citation

**Chosen:** `polarity` describes the aṣl as cited, `neutral` when the aṣl is descriptive.

This is what makes the `ك-ف-ر` case tractable. Ibn Fāris gives «الستر والتغطية» — a descriptive aṣl.
The root's negative charge is Quranic usage. Recording that usage charge as the *aṣl's* polarity would
make the dataset a sentiment lexicon, and the guard would then fire on every root whose usage and
etymology differ — which is many of them. It also means `خ-ب-ث` («خلاف الطيب») is the root that
genuinely exercises the negative pole.

### D10 — Module placement follows the existing direction

New: `linguistics/lisan/root_core_store.py` (canon-keyed lookup with geminate variants, modelled on
`madar/maqayis_store.py`) and `linguistics/lisan/sense_selection.py` (pure, disk-free, unit-testable
on hand-built inputs). Datasets are reached only through `quran_data.loaders`. `_canon` is reached
through the `LexicalRetriever` that `LisanService` is already handed. `linguistics/` keeps importing
only shared packages and `retrieval/`, never `api/` — `tests/test_import_direction.py` unchanged.

### D11 — Break the API and move the frontend in the same change

`sequential_reading` and the single `letters[].meaning` describe a pipeline that will not exist. The
frontend lives in this repo and `/lisan/analyze` has exactly one caller, so a compatibility shim would
only preserve a shape whose semantics are gone.

## Risks / Trade-offs

- **R1 — Circular curation.** If a curator writes the senses of `خ` while looking at `خ-ي-ر`, the
  match is tautological and proves nothing. → Every sense must cite a letter-level authority and a
  page (`letter-sense-inventory` makes an uncited sense a validation failure), the sense set is
  curated per letter rather than per root, and D8's corollary makes a permanently silent guard a
  signal to audit. This risk cannot be eliminated by a mechanism, only kept visible.
- **R2 — Coverage collapse.** Roots outside the curated set lose their paragraph. Ceiling is
  1 149/1 656 QAC roots, and phase 1 is far below it. → The uncovered path is designed, labelled and
  documented rather than papered over; the inventory display keeps the page informative; the
  validator reports coverage so the number is never a guess.
- **R3 — The axis vocabulary is the whole design.** Too coarse and everything matches; too fine and
  nothing does. → Seed it from the aṣl texts of the regression roots plus the letters they use, keep
  it small, and treat an axis used by exactly one core or one sense as a smell.
- **R4 — Curation is the long pole.** Axes and polarity for ~1 100 roots and senses for 28 letters is
  human work no script replaces. → Phase the work: mechanism + validator + a small curated set that
  covers the regression battery first; the "no core" path makes a partial dataset shippable.
- **R5 — Two datasets can now disagree.** A miscurated core corrupts every letter of that root. →
  `verbatim` is checked byte-for-byte against the Maqāyīs CSV, so the citation half cannot drift; only
  axes and polarity are opinion, and the guard watches the polarity half.
- **R6 — A user reads the constrained reading as lexicography.** It is more convincing than the old
  one *because* it now agrees with a citation. → The interpretive disclaimer stays, the core is shown
  as a citation with its source, and the selected sense is always shown next to the ones rejected.
- **R7 — `position` data may be thin.** Ḥasan ʿAbbās does not state a position for every sense. →
  `any` is the default and contributes 0 to the fit term, so the ranking degrades to axis overlap
  plus confidence rather than misfiring.

## Migration Plan

1. **Vocabulary and validator first.** `semantic_axes.json` + the validator + `paths.py`/`loaders.py`/
   `manifest.py` entries. Nothing user-visible; `tests/test_quran_data.py` must stay green.
2. **Seed the cores.** `scripts/build_root_cores_seed.py` fills verbatim/source/canonical key for
   every `has_asl` QAC root; axes and polarity stay empty and the validator rejects half-curated
   entries, so an unfinished file cannot ship.
3. **Curate the regression set.** `خير`, `خبث`, `كفر`, `ظلم`, `رحم`, plus the senses of the letters
   they use. This is the smallest dataset that can prove the mechanism.
4. **Selection engine.** `sense_selection.py` against hand-built inputs, no disk, no data dependency.
5. **Wire the pipeline.** `letter_lexicon`, `root_core_store`, `synthesis_template`, `lisan_service`,
   models, router.
6. **Frontend.** Types, `LisanResult.tsx` (selected + discarded + warning + divergence banners),
   Vitest, `tsconfig.test.json` type-check.
7. **Widen curation** afterwards, one batch of roots at a time — each batch is data only and needs no
   code change.

**Rollback:** steps 1–4 are additive and inert. From step 5 the rollback is a revert of the change;
there is deliberately no runtime flag restoring the old reading, since a flag that restores the
`خ-ي-ر` bug is the thing this proposal exists to remove.

## Open Questions

- **How large should the axis vocabulary be?** Order of 30–60 axes is the working assumption; it must
  be settled while curating the regression set (step 3), because both datasets are tagged against it.
- **Does `ishtiqaq_akbar` (Ibn Jinnī's taqālīb) stay as-is?** It is independent of this change and is
  assumed to survive untouched, but it is the one remaining unconstrained section on the page.
- **Is the uncovered-root inventory the right UX**, or should the page show only the root, the
  grammar section and the warning? Recommendation: keep the inventory, clearly labelled — but this is
  a product call.
- **Should `parse_uncertain` Maqāyīs rows (1 322) be curated by hand into cores later?** Out of scope
  here; they are excluded by `root-semantic-core`.
