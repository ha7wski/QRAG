## Why

QLisan increment 1 shipped the deterministic صرفي / نحوي levels, but a review of the
live fiche (13:12 الرعد, word السحاب) found four presentation/mapping defects, and an
adversarial review of the *first* fix plan against the whole corpus (77,429 words)
found that the naïve fix would itself leak Latin/Buckwalter codes and emit
grammatically wrong iʿrāب on **tens of thousands** of words — because the demo word
(السحاب, an `Obj` with a clean nominal head) is precisely the one case where every
latent bug is masked. The defects are display/mapping bugs on data that is already
correct on disk, but the *fix* must be corpus-wide-safe, not anchor-safe: it
undercuts the «معطى محقّق» (verified) badge the levels carry, so it should be fixed
before the صوتي / دلالي increments build on the same fiche.

## What Changes

- **[1] المقاطع field misuse (صرفي).** The row labelled «المقاطع» renders the
  morphological **segments** (STEM / PREFIX / SUFFIX), not syllables. Relabel it
  «البنية الصرفية» and translate the segment values (STEM→جذع, PREFIX→بادئة,
  SUFFIX→لاحقة). Reserve the term «مقاطع» for the future صوتي level (CV/CVC
  syllables) alone.
- **[2] Raw tags leaking into the RTL UI — corpus-wide.** Introduce **one complete
  tag→Arabic mapping table** covering **every feature key present in the corpus**, not
  a named subset. The corpus carries **12** feature keys — `nominal_case`, `gender`,
  `number`, `nominal_state`, `person`, `pgn`, `verb_aspect`, `verb_form`, `verb_mood`,
  `verb_voice`, `derived_nouns`, `special_group` — the last of which holds raw
  **Buckwalter** (`SP:kaAn`, `SP:<in~`, `SP:kaAd`). Every one must map both its
  **key** (`FEATURE_LABEL_AR`) and its **values** to Arabic; `pgn` is decomposed into
  person/gender/number and deduped against the standalone columns. An unmapped code is
  a **test failure, never a rendered passthrough**. POS itself needs **no** table:
  `pos_ar` is populated for 100 % of records — the «اسم N» leak is solely the frontend
  `{level.pos}` fallback, removed in the frontend task.
- **[3] نحوي — iʿrāب function, composed SAFELY.** «الموقع الإعرابي» must show the
  iʿrāب **function** (from the dependency relation + case), not the word class. But
  the raw `relation_ar` cannot be blindly concatenated with the case word:
  - `relation == root` (**12,897** words, incl. 1:2:1 ٱلْحَمْدُ) has
    `relation_ar == "root"` — **Latin**; it must map to an Arabic label (e.g.
    «عمدة الجملة»), never pass through.
  - `relation == gen` (**10,510** words, incl. 1:1:1 بِسْمِ, 1:2:2 لِلَّهِ) already
    has `relation_ar == "مجرور"`; appending the case word yields the stutter
    «مجرور مجرور». It must compose «اسم مجرور» instead.
  - Source mislabels (**83** words tagged `Subj` yet `relation_ar == "مفعول به"`, e.g.
    2:80:4 ٱلنَّارُ, NOM) must not be amplified into the self-contradiction
    «مفعول به مرفوع»: the case word is appended only when the relation's canonical case
    matches the present case.
  - منادى (`voc`) and indeclinable (مبني: PRON/REL/DEM/COND — **0** carry a
    `nominal_case`) words get no fabricated lafẓī case marker.
  Add a «العلامة» row (case marker) **as a derived hint (الأصل), rendered outside the
  «معطى محقّق» badge** (see [5]); keep «المتعلَّق» for the governing word.
  **Test anchor:** السحاب (13:12:8) ⇒ الموقع الإعرابي = «مفعول به منصوب», العلامة =
  «الفتحة», المتعلَّق → 13:12:7 (the verb ويُنشئُ, word **7**).
- **[4] النظائر mix root homonyms.** Concordance is by **root**, so it aggregates
  unrelated senses (السحاب "cloud" beside يُسحبون "they are dragged" — same root سحب,
  different lemma). Filter naẓāʾir by **lemma**; when same-lemma siblings are too few,
  keep the root but **group/label by distinct lemma**. **Test anchor:** on السحاب
  (13:12:8), يُسحبون / يسحبون no longer appear in the same-lemma group.
- **[5] «معطى محقّق» must not cover derived fields.** The relation function name and
  the case name are verbatim QAC (verified). The case **marker** (العلامة) is a
  derived heuristic — wrong for sound-plural / dual / diptote (e.g. 1:2:4
  ٱلْعَٰلَمِينَ, GEN plural: the plan's الكسرة should be الياء). The badge stays on the
  verbatim fields only; the marker is shown as «الأصل» **outside** the badge and is
  **omitted** (never fabricated) for the classes where الأصل is unreliable.

**Constraints (load-bearing):** touch only the **presentation layer** and the
**corpus→UI mapping**; do **not** alter the source QAC data (`quranic-treebank.csv`)
**nor the ingestion build** (`ingestion/qac_treebank.py` — no re-ingestion, code-only);
the «معطى محقّق» badge stays on the **verbatim** صرفي / نحوي fields; each of the five
points ships with a test whose coverage is corpus-wide (points [2]/[3] sweep the whole
corpus and multiple adversarial anchors, not the single demo word). No LLM anywhere.

## Capabilities

### New Capabilities

<!-- None. This change refines the presentation/mapping of existing QLisan capabilities. -->

### Modified Capabilities

- `qlisan-word-analysis`: the per-word fiche presentation contract — a **complete**
  tag→Arabic label mapping (every feature key + value, `pgn` decomposed, Buckwalter
  `special_group` stripped) so no Latin code is ever shown for **any** word; the
  «البنية الصرفية» relabel + segment-value translation; and the badge scoped to
  verbatim fields (the derived marker rendered outside it).
- `qac-morphosyntax-index`: the deterministic data served to the نحوي and naẓāʾir
  views — a **safely composed** iʿrāب function (relation + case, with root/gen/voc/
  mislabel/مبني guards) rather than the part-of-speech in the role field, a derived
  case marker (العلامة, الأصل) presented as a hint, and **lemma-scoped** (not
  root-scoped) naẓāʾir grouping.

## Impact

- **Backend (mapping — new):** a single shared, deterministic label module
  (`analysis/qac_labels.py`) holding tag→Arabic tables for **every** feature key +
  value in the corpus, the feature-key labels (`FEATURE_LABEL_AR`), the relation
  overrides (incl. `root`→Arabic), `decompose_pgn` (character-set classification, not
  positional), and `case_marker` — pure dict lookups, unit-testable in isolation. **No
  POS table** (pos_ar is authoritative).
- **Backend (assembler):** `analysis/word_analysis.py` composes the iʿrāب function
  with the root/gen/voc/mislabel/مبني guards, the derived case marker, Arabic-
  translated features (with `pgn` split), and Arabic segment labels; reads
  `nominal_case` from the صرفي record; stops reading the stale `role_ar`. **No
  ingestion edit** — the misleading `role_ar = pos_ar` line in
  `ingestion/qac_treebank.py` is simply not read; removing it is a separate
  ingestion-hygiene change, out of scope here.
- **Backend (models):** `api/models/qlisan.py` gains the display fields (`iraab_ar`,
  `marker_ar`, translated `features` as an ordered `[{label_ar, value_ar}]` list,
  Arabic `segments`, naẓāʾir `lemma`/`lemma_display`), keeping the four-level ordered
  shape and the `available` flags. Raw `pos`/`relation` remain in the payload (data,
  not display); `role_ar` is deprecated (no longer populated). The set of
  **display fields** the "no-Latin" test sweeps is enumerated explicitly.
- **Frontend:** `frontend/src/app/qlisan/page.tsx` renders the pre-translated Arabic
  fields and **removes every raw-code fallback** (`{level.pos}`, `{k}: {String(v)}`,
  the gray `{level.relation}`), **removes the standalone «العلاقة» (`relation_ar`)
  row** (subsumed by «الموقع الإعرابي»), relabels «المقاطع»→«البنية الصرفية», renders
  the marker as a distinct «الأصل» hint outside the «معطى محقّق» badge, and groups
  naẓāʾir by lemma. Types in `frontend/src/lib/types.ts` updated to match.
- **Tests (local-only):** corpus-wide sweep for [2] (every feature key+value + every
  `relation_ar` → no `[A-Za-z]`); multi-anchor نحوي for [3] (السحاب Obj; 1:2:1 root;
  1:1:1 gen; 1:2:4 sound plural; 2:80:4 Subj-mislabel; a مبني pronoun; the no-case verb
  13:12:7); lemma naẓāʾir for [4] (dense anchor السحاب + a sparse/grouped anchor);
  `pgn` round-trip over all 25 forms; the «البنية الصرفية» relabel for [1]; and an
  **update to the existing** `tests/test_qlisan_analysis.py` (the `role_ar` assertion
  becomes an `iraab_ar` assertion).
- **No change** to ingestion source data or the build, Qdrant, the chat/search path,
  or the صوتي / دلالي stubs.
