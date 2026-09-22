## Why

On `/lexical`, the letter reading of a root is built by **concatenating one frozen gloss per
letter**. `خ-ي-ر` therefore reads «القذارة والخشونة والخواء… فساد» — the antonym of the attested
sense (Ibn Fāris: «الخاء والياء والراء **أصله العطف والميل**»). The bug is not a bad row in a CSV:
it is the direction of the pipeline. A letter carries a *bundle* of senses, and today nothing
selects among them, because there is nothing to select *against* — the reading is composed with no
knowledge of what the root means.

The fix is to invert the pipeline: **root → attested semantic core → letter reading constrained by
that core → synthesis**. The core comes from a source the repo already ships and already parses:
`data/references/maqayis_asl.csv` (4 662 roots, 3 326 with a cited aṣl; 1 149 of the 1 656 QAC roots
have one). What is missing is the structured layer on top of it — axes and polarity — and a letter
dataset that admits it holds more than one sense per letter.

The same خ is legitimately «خشونة/خبث» in `خ-ب-ث` («أصل واحد يدل على **خلاف الطيب**») and
legitimately «انعطاف/ميل» in `خ-ي-ر`. Any design that cannot produce both readings from the same
letter row is still the current bug wearing a new schema.

## What Changes

### A new attested-core dataset

- Add **`data/references/root_cores.json`** — curated from Ibn Fāris' *Maqāyīs*, keyed on the
  **canonical QAC root key** (the exact, hamza-bearing spelling `LexicalRetriever._canon` returns —
  *not* the folded `normalize_root` form the Maqāyīs CSV is keyed on; a curated list keyed on the
  fold silently stops matching). Value = a **list** of أصول, since a root may have several
  (`ظ-ل-م` has two: «خلاف الضياء والنور» ‖ «وضع الشيء غير موضعه تعديا»). Each aṣl carries
  `gloss` / `verbatim` (Ibn Fāris' own words, never paraphrased) / `axes` / `polarity` / `source`.
- Add **`data/references/semantic_axes.json`** — the **closed vocabulary** both datasets tag
  against. Without one shared, finite axis list, "matching the letter senses to the core's axes" is
  undefined: free-text axes intersect by luck. Each axis carries an id, an Arabic label, and an
  optional `antonym` link — which is what lets the guard below distinguish *no match* from
  *contradiction*.

### The letter dataset admits N senses per letter

- **BREAKING (data schema)** — `data/references/arabic_letters_dataset.csv` keeps the letter-level
  identity and phonetics (28 rows) and **loses** `abbas_meaning*` / `abbas_keywords*`.
- Add **`data/references/letter_senses.csv`** — one row per **(letter, sense)**: `gloss_ar`,
  `pole`, `axes`, `position` (initial/medial/final/any — Ḥasan ʿAbbās already states position-
  dependent values), `gesture_ar` (the articulatory gesture), `source` + `page`, `confidence`.
  A sense with no cited source is rejected at validation — the cite-or-omit gate `tahlil/citations.py`
  already applies to generated prose, applied here to curated scholarship.

### The pipeline is inverted

- New **deterministic, LLM-free** selection step: for each root letter, keep the senses sharing at
  least one axis with the core and contradicting none, then rank by a fixed tuple
  (axis overlap → position fit → source confidence → declaration order). One sense per letter, per
  core. No ML, no embeddings — the reading must stay auditable, and this feature has already been
  burned twice by fluent-but-false generation.
- **No silent fallback.** A letter with no eligible sense is reported `unmatched` and asserts
  nothing. A root absent from `root_cores.json` disables the constrained reading entirely: the page
  shows the letter senses as an *inventory*, explicitly labelled unconstrained, with a warning — it
  never composes them into an assertive paragraph. The old concatenation is **removed**, not kept
  behind a flag.
- **Divergence guard**: when the polarity of the selected reading contradicts the core's polarity,
  the response carries a `divergence` object and the UI shows it. The guard **detects, never
  corrects** — it must not flip a sense to manufacture agreement.
- **BREAKING (HTTP)** — `POST /lisan/analyze` returns cores, one reading per core, per-letter
  selected + **discarded** senses with the reason each was dropped, `constrained`, `warning`, and
  `divergence`. `sequential_reading` (the unconstrained chain) is removed.

### Regression battery

`خ-ي-ر` is the canonical test. The **decisive** one is the minimal pair `خ-ي-ر` / `خ-ب-ث`: same
letter, two cores, two different senses selected — a mechanism that cannot do that has not fixed
anything. `ك-ف-ر` is the counter-test the constraint must not distort.

> **One correction to the brief, stated once:** `ك-ف-ر` is not an evaluatively negative root *at the
> aṣl level* — Ibn Fāris gives «الستر والتغطية», which is descriptive. Its negative charge is
> Quranic usage, not aṣl. That makes it a *better* counter-test than intended (it proves the
> constraint follows the cited aṣl rather than a sentiment prior, in both directions), so it is
> kept — and `خ-ب-ث` («خلاف الطيب») is added as the genuinely negative-pole root, since otherwise
> the negative pole is never exercised.

## Capabilities

### New Capabilities
- `root-semantic-core`: the attested-core dataset — its key contract (canonical root key), the
  multi-aṣl shape, verbatim fidelity to Ibn Fāris, the closed axis vocabulary, polarity semantics,
  the seed script, and the validator that keeps it from drifting.
- `letter-sense-inventory`: the letter dataset refonte — N sourced senses per letter, the split
  between the phonetic sheet and the sense sheet, and the sourcing gate.
- `constrained-letter-reading`: the inverted pipeline — selection algorithm, discarded senses,
  behaviour when no core exists, the divergence guard, the `/lisan/analyze` contract, the `/lexical`
  UI, and the regression battery.

### Modified Capabilities
<!-- None. `dataset-registry` already requires a path constant, a cached loader and a manifest entry
     per dataset; the three new files comply with it rather than change it. `served-surface` is
     route-level and no route is added or removed. -->

## Impact

- **Data** — new: `root_cores.json`, `semantic_axes.json`, `letter_senses.csv`. Modified:
  `arabic_letters_dataset.csv` (columns dropped). Each needs a `quran_data/paths.py` constant, a
  cached `quran_data/loaders.py` loader and a `quran_data/manifest.py` entry
  (`tests/test_quran_data.py` fails otherwise).
- **Backend** — `linguistics/lisan/`: `letter_lexicon.py` (senses, not one gloss), new
  `root_core_store.py` and `sense_selection.py`, rewritten `synthesis_template.py`, reorchestrated
  `lisan_service.py`. `api/models/lisan.py` + `api/routers/lisan.py`. Import direction is unchanged:
  `linguistics/` reads `quran_data` and the `retrieval/` resolver it is already handed, never `api/`.
- **Frontend** — `lib/lisanTypes.ts`, `components/LisanResult.tsx` (+ its Vitest file),
  `app/lexical/page.tsx` (+ its Vitest file), `lib/strings.ts`.
- **Scripts** — `scripts/build_root_cores_seed.py` (pre-fills gloss/verbatim/source from the Maqāyīs
  CSV, leaves `axes`/`polarity` for the curator) and a dataset validator.
- **Coverage cost, stated up front** — at most 1 149 of 1 656 QAC roots can ever have a core from
  Maqāyīs, and the curated set starts far smaller. Roots outside it lose their paragraph and gain a
  warning. That is the intended trade: the alternative is keeping the `خ-ي-ر` reading for them.
- **Out of scope** — `linguistics/tahlil/huruf.py` keeps reading
  `arabic_letter_semantics_hasan_abbas.json` untouched; `/madar` stays quarantined; no LLM is
  introduced anywhere.
