## Context

QLisan increment 1 assembles the صرفي / نحوي fiche deterministically in
`analysis/word_analysis.py` from three on-disk artifacts built by
`ingestion/qac_treebank.py`: `qac_words.json` (morphology: root, lemma, pos, pos_ar,
`features{}` of **raw** QAC codes, `segments[]` of STEM/PREFIX/SUFFIX),
`qac_syntax.json` (`role_ar`, `relation`, `relation_ar`, `head_ref`), and
`root_graph.json` (root → occurrence refs, used for naẓāʾir). The frontend
(`frontend/src/app/qlisan/page.tsx`) renders these fields directly.

The QAC source carries Arabic **only** for `pos`/`rel_label`/`root`/`lemma`; feature
*values* (`ACC`, `M`, `IMPF`, `SP:kaAn`, …) and `segment` codes have **no** Arabic
column. A corpus sweep (77,429 words / 76,639 syntax rows) exposed that the first fix
plan was **anchor-safe but not corpus-safe** — the demo word السحاب (13:12:8) is the
one record where every latent bug is masked. Verified facts driving this design:

- **`pos_ar` is populated for 100 % of records** → no POS→Arabic table is needed; the
  «اسم N» leak is only the frontend `{level.pos}` fallback (page.tsx:429–433).
- **12 feature keys** occur, only 5 of which the first plan mapped. Unmapped-and-thus-
  leaked: `verb_aspect` (19,356 recs), `verb_form` (8,977), `derived_nouns` (4,199),
  `special_group` (3,870 — raw **Buckwalter**), `verb_mood` (2,748), `verb_voice`
  (1,140), standalone `person` (22,708). Feature **keys** themselves were never mapped
  (`nominal_case: منصوب` still leaks the key).
- **`relation_ar == "root"`** for **12,897** syntax rows (Latin), incl. 1:2:1
  ٱلْحَمْدُ; **11,588** carry no case.
- **`relation_ar == "مجرور"`** (relation `gen`) for **10,510** rows → blind append =
  «مجرور مجرور» (incl. 1:1:1 بِسْمِ, 1:2:2 لِلَّهِ).
- **83** rows tagged `Subj` but `relation_ar == "مفعول به"` (source mislabel, e.g.
  2:80:4 ٱلنَّارُ, NOM) → blind append = «مفعول به مرفوع».
- **PRON/REL/DEM/COND** (8,723 words) carry **0** `nominal_case` (all مبني).
- The case marker الأصل is wrong for sound plural / dual / diptote (1:2:4
  ٱلْعَٰلَمِينَ GEN plural: الأصل الكسرة, correct الياء). `number=D` reliably flags
  duals; `number=P` does **not** separate sound from broken plurals; diptote is not a
  feature column.
- `ingestion/qac_treebank.py:278` sets `role_ar = pos_ar` — the stale field the نحوي
  slot wrongly showed; it is now simply not read (no build edit).
- `_nazair()` walks `root_graph` (root-scoped), mixing homographic lemmas. Every
  word with a root has a lemma (0 root-without-lemma), so lemma-scoping never
  degenerates for a word that has siblings.

## Goals / Non-Goals

**Goals:**
- **No Latin/Buckwalter token is ever visible for ANY word in the corpus** — every
  label and value Arabic, produced by **one** deterministic table covering every
  feature key and value, verified by a corpus-wide sweep (not a single anchor).
- «الموقع الإعرابي» shows a **safely composed** iʿrāب function (relation + case) that
  never leaks Latin (root), never stutters (gen), never contradicts itself
  (Subj-mislabel), and never fabricates a lafẓī marker on مبني/منادى words.
- «العلامة» shows the case marker **as a derived الأصل hint, outside the verified
  badge**, and is omitted (not fabricated) where الأصل is unreliable.
- «المقاطع» is relabelled «البنية الصرفية» with Arabic segment values; «مقاطع» is
  freed for the future صوتي level.
- naẓāʾir are lemma-scoped (or lemma-grouped), never mixing homograph senses.
- Each point ships a corpus-wide/multi-anchor test; existing tests are updated, not
  left asserting the old behaviour.

**Non-Goals:**
- No change to source QAC data, the ingestion **build**, the ingestion artifacts'
  *content* for صرفي, Qdrant, the chat/search path, or the صوتي / دلالي stubs.
- No full iʿrāب engine: العلامة uses the primary marker (الأصل) for the singular
  triptote only and is **omitted** for dual/plural/diptote-genitive rather than shown
  wrong; case-word gender agreement is not inflected («صفة منصوب», not «منصوبة»);
  positional محلّ for مبني words is a documented future refinement (the MVP must at
  least not fabricate a lafẓī marker for them).
- No LLM anywhere.

## Decisions

### D1 — Mapping lives in a shared backend module, applied at assembler time, COMPLETE
Add `analysis/qac_labels.py`: pure dict tables + tiny helpers. It maps **every**
feature key and value present in the corpus, not a named subset:
- **Value tables:** `nominal_case` (NOM→مرفوع/ACC→منصوب/GEN→مجرور), `gender`
  (M→مذكّر/F→مؤنّث), `number` (S→مفرد/D→مثنّى/P→جمع), `nominal_state` (INDEF→نكرة,
  DEF→معرفة), `verb_aspect` (PERF→ماضٍ/IMPF→مضارع/IMPV→أمر), `verb_voice`
  (PASS→مبني للمجهول), `verb_mood` (MOOD:JUS→مجزوم/MOOD:SUBJ→منصوب), `verb_form`
  ((II)→الوزن الثاني … (XII)→الوزن الثاني عشر), `derived_nouns` (ACT_PCPL→اسم الفاعل/
  PASS_PCPL→اسم المفعول/VN→مصدر), `special_group` (strip `SP:` then <in~→من أخوات إنّ/
  kaAn→من أخوات كان/kaAd→من أخوات كاد), `person` (1→متكلّم/2→مخاطب/3→غائب), `segment`
  (STEM→جذع/PREFIX→بادئة/SUFFIX→لاحقة).
- **Key table** `FEATURE_LABEL_AR` for all keys (nominal_case→الحالة الإعرابية,
  gender→الجنس, number→العدد, nominal_state→التعريف, verb_aspect→الزمن, verb_form→
  الوزن, verb_mood→حالة الفعل, verb_voice→البناء, derived_nouns→المشتقّات,
  person→الشخص, special_group→المجموعة).
- **No POS table** — `pos_ar` is authoritative and already populated; a second source
  would drift (the corpus writes «حرف جر», a hand table would write «حرف جرّ»).
- **Unmapped code = hard error, never rendered.** The old "clearly-marked passthrough"
  fallback is removed: `translate_features` must map every code or the coverage test
  fails.
- **Why assembler-time (not build-time / not frontend):** keeps the JSON source-
  faithful (raw QAC), makes the fix a code-only deploy with no re-ingestion, and lets
  the tests (and the API's "no-Latin" guarantee) assert on one backend source of
  truth. The explicit anchors ([3]/[4]) are naturally assembler/API assertions.

### D2 — نحوي iʿrāب composed SAFELY in the assembler; `role_ar` deprecated, source untouched
`_nahwi()` takes the صرفي record so it can read `nominal_case`. `relation_ar` is first
normalised through a **relation-override map** (never emit ASCII, never a bare case
word), then the case word is appended only under a consistency guard:
- **`relation == root`** → «عمدة الجملة» (deterministic Arabic; finer مبتدأ/خبر/فعل
  resolution is a possible later refinement). Case word may be appended (it is not a
  case word itself).
- **`relation == gen`** → «اسم مجرور» directly (do **not** append a second «مجرور»).
- **`relation == voc`** → «منادى»; no case word, no lafẓī marker (منادى is مبني on its
  surface ḥarakah / في محل نصب).
- **Consistency guard:** each case-bearing relation has a canonical case. Append the
  case word **only when the present `nominal_case` matches** the relation's canonical
  case; on mismatch (the 83 `Subj`+`مفعول به` mislabels, etc.) show the relation name
  alone — never «مفعول به مرفوع». `link`/متعلق-type relations are treated as
  non-composable (relation name alone).
- **مبني words** (POS ∈ {PRON, REL, DEM, COND}, or any word with no `nominal_case`):
  show the relation function with **no fabricated lafẓī marker**; `marker_ar` omitted.
  (Emitting «مبني في محلّ …» from the relation's canonical case is a documented
  future refinement, not required for this change.)
- `iraab_ar` = normalised relation function [+ case word when the guard allows];
  `head_ref` unchanged (المتعلَّق).
The stale `role_ar = pos_ar` in `qac_syntax.json` is simply **not read** anymore. No
re-ingestion, and **no build edit** (dropping the line in `qac_treebank.py` is a
separate ingestion-hygiene change — out of scope, see Non-Goals).

### D3 — Features returned as an ordered Arabic list; every key mapped; `pgn` decomposed by character-set
`_sarfi()` converts the raw `features{}` dict into an ordered list of
`{label_ar, value_ar}` via `qac_labels`, mapping **every** key (D1). `decompose_pgn`
classifies by **character set** — person ∈ {1,2,3}, gender ∈ {M,F}, number ∈ {S,D,P},
in any subset — **not positionally** (a positional parser breaks on the 9 forms
lacking a middle gender or a leading person: `M`, `F`, `P`, `MS`, `MP`, `FS`, `FP`,
`2D`, `3D`). The parts merge/dedupe with any standalone `gender`/`number`/`person`
columns; the standalone columns are authoritative and `pgn` only fills gaps
(corpus-verified: **zero** pgn-vs-standalone conflicts, so the merge is always safe).
The fiche shows «مذكّر / مفرد» once — not «pgn: M» + «gender: M». No code is ever
passed through raw (D1).

### D4 — Segments translated + row relabelled
`segments[]` values map STEM→جذع / PREFIX→بادئة / SUFFIX→لاحقة (assembler-side). The
frontend row label changes «المقاطع» → «البنية الصرفية». «مقاطع» is reserved for صوتي.

### D5 — naẓāʾir filtered by lemma, grouped when sparse
`_nazair()` keeps `root_graph` as the candidate pool but filters to refs whose
`qac_words[ref].lemma` equals the selected word's lemma; each returned entry carries
`lemma` / `lemma_display`. If the same-lemma set is below a threshold (default 3),
other lemmas are included but **tagged by lemma** so the UI renders them in separate,
labelled groups — never as one undifferentiated "same meaning" strip. No new ingestion
artifact (per-ref lemma is already in `qac_words`). For the anchor السحاب the same-
lemma set is 8 (≥3), so a **second, sparse anchor** must exercise the grouped path.

### D6 — «معطى محقّق» scoped to verbatim fields; derived marker rendered as a hint
The badge attests **provenance**, not level. It stays on the fields taken verbatim
from QAC (the relation function name, the case name) and on the deterministic صرفي
data. `marker_ar` (العلامة) is a **derived heuristic**: it is emitted only for a
declinable singular triptote nominal (`number` absent or `S`, not a diptote-genitive)
and **omitted** for `number ∈ {D, P}` and diptote-genitive (where الأصل is wrong).
When shown, it is rendered as a distinct «الأصل» hint **outside** the «معطى محقّق»
badge so the badge never certifies a heuristic. (Diptote is not a feature column;
singular diptote-genitives like فرعون/إبراهيم/مريم are a documented residual — the
conservative rule omits the marker for proper-noun genitives to avoid the common
cases.)

### D7 — Frontend renders Arabic-only; raw-code fallbacks AND the duplicate relation row removed
`SarfiLevel`/`NahwiLevel` drop `{level.pos}`, the raw `{k}: {String(v)}` chips, the
gray `{level.relation}` span, raw segment text, **and the standalone «العلاقة»
(`relation_ar`) row** (page.tsx:537–548) — `iraab_ar` subsumes it, so keeping it would
show «مفعول به منصوب» and a duplicate «مفعول به». New rows: «الموقع الإعرابي» bound to
`iraab_ar`; «العلامة» bound to `marker_ar` **rendered outside the verified badge**.
naẓāʾir render grouped by `lemma_display`. `frontend/src/lib/types.ts` gains the new
fields; the four-level order and `available` flags are unchanged. (Point [1]'s label
relabel and this row removal are frontend-only; verified by the backend segment/iʿrāب
tests + a manual check — recorded as an accepted frontend-coverage gap unless a small
component test is added.)

### D8 — API model + display-field contract
`api/models/qlisan.py`: `SarfiLevel.features` becomes the ordered Arabic list; Arabic
`segments`; `NahwiLevel` gains `iraab_ar`/`marker_ar`; `Nazair` gains
`lemma`/`lemma_display`. Raw `pos`/`relation` stay in the payload (data, not rendered);
`role_ar` stays in the model for shape-compat but is no longer populated. The
**display fields** the "no-Latin" endpoint test sweeps are enumerated explicitly:
`pos_ar`, `features[].label_ar`, `features[].value_ar`, `segments[]`, `iraab_ar`,
`marker_ar`, `nazair[].*` — not the raw `pos`/`relation` passthroughs.

## Risks / Trade-offs

- **[العلامة over-simplified for sound-plural/dual/diptote]** → the marker is
  **omitted** (not shown wrong) for `number ∈ {D,P}` and proper-noun genitives, and is
  rendered outside the verified badge (D6). A later increment can add sound-plural/dual
  (الياء) and diptote handling.
- **[Blind iʿrāب composition would leak/stutter/contradict]** → the D2 override map +
  consistency guard handle root (12,897), gen (10,510), voc, and the 83 Subj-mislabels;
  the نحوي test set covers all these classes, not just `Obj`.
- **[Unmapped QAC code slips through]** → D1 removes the passthrough fallback and the
  1.4 test sweeps every feature key + value + every `relation_ar` across the corpus,
  asserting no `[A-Za-z]`.
- **[Existing tests assert the old behaviour]** → the change updates
  `tests/test_qlisan_analysis.py` (role_ar→iraab_ar) rather than leaving it red.
- **[Contract change: features dict→list]** → the only consumer is the qlisan page +
  `types.ts` (grep-confirmed); both are updated in the same change; the four-level
  shape and `available` flags are preserved.

## Migration Plan

Code-only; no data migration, no re-ingestion, **no build edit** (D1/D2 read existing
JSON). Deploy = ship backend + frontend; rollback = revert the commit. Existing
`qac_*.json` / `root_graph.json` are consumed unchanged.

## Open Questions

- Row label: **«البنية الصرفية»** chosen over «الأجزاء»; confirm during apply.
- `root`-relation label: **«عمدة الجملة»** chosen as the deterministic default; whether
  to refine to مبتدأ/خبر/فعل by POS+case is deferred.
- naẓāʾir same-lemma threshold (default 3) — pinned by the sparse-anchor test (D5); tune
  against a few dense roots during apply.
- Whether to add a frontend component test for the «البنية الصرفية» relabel + the
  removed relation row, or accept the documented manual-only coverage gap (D7).
