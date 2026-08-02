> **Status (2026-08-03):** implemented + adversarially verified. Backend suite green
> for QLisan (69 qac/qlisan tests pass); full repo suite = 152 passed / 1 failed, the
> single failure being **pre-existing and unrelated** (`test_madar.py::
> test_service_synthesis_disabled_by_default` — reproduces with the QLisan edits
> stashed; `madar/` untouched by this change). All five change points verified against
> the corpus anchors. Remaining: 7.3 (manual live-fiche eyeball), 7.4 (optional
> frontend component test), 7.5 (N/A — no QLisan section in the docs yet).

## 1. Shared tag→Arabic mapping module (backend) — COMPLETE, no passthrough

- [x] 1.1 Create `analysis/qac_labels.py` (pure stdlib, no LLM/network) with value tables for
  **every feature key present in the corpus** — `nominal_case` (NOM→مرفوع/ACC→منصوب/GEN→مجرور),
  `gender` (M→مذكّر/F→مؤنّث), `number` (S→مفرد/D→مثنّى/P→جمع), `nominal_state` (INDEF→نكرة/DEF→معرفة),
  `verb_aspect` (PERF→ماضٍ/IMPF→مضارع/IMPV→أمر), `verb_voice` (PASS→مبني للمجهول),
  `verb_mood` (MOOD:JUS→مجزوم/MOOD:SUBJ→منصوب), `verb_form` ((II)→الوزن الثاني … (XII)→الوزن الثاني عشر),
  `derived_nouns` (ACT_PCPL→اسم الفاعل/PASS_PCPL→اسم المفعول/VN→مصدر),
  `special_group` (strip `SP:` then <in~→من أخوات إنّ/kaAn→من أخوات كان/kaAd→من أخوات كاد),
  `person` (1→متكلّم/2→مخاطب/3→غائب), and `segment` (STEM→جذع/PREFIX→بادئة/SUFFIX→لاحقة).
  **No POS table** — `pos_ar` is authoritative (100 % populated) and stays the sole POS source.
- [x] 1.2 Add `FEATURE_LABEL_AR`: the key→Arabic-label table for every key above (e.g.
  nominal_case→الحالة الإعرابية, gender→الجنس, number→العدد, nominal_state→التعريف, verb_aspect→الزمن,
  verb_form→الوزن, verb_mood→حالة الفعل, verb_voice→البناء, derived_nouns→المشتقّات, person→الشخص,
  special_group→المجموعة) so the row label is never the raw key.
- [x] 1.3 Add a **relation-override** table + helper so `relation_ar` is never emitted as ASCII or as a
  bare case word: `root`→«عمدة الجملة», `gen`→«اسم مجرور», `voc`→«منادى» (extend as the corpus
  requires; the sweep in 1.7 enumerates every distinct `relation_ar`).
- [x] 1.4 Add `case_marker(word)` → العلامة for the **declinable singular triptote** case only
  (ACC→الفتحة, NOM→الضمة, GEN→الكسرة); return `None` (omit, never fabricate) when `number ∈ {D, P}`,
  for proper-noun genitives (diptote-suspect), and when there is no `nominal_case`.
- [x] 1.5 Add `decompose_pgn(pgn)` using **character-set** classification (person∈{1,2,3},
  gender∈{M,F}, number∈{S,D,P}, any subset — NOT positional), returning the present parts; and
  `translate_features(features)` returning an ordered `[{label_ar, value_ar}]` list that maps every
  key/value via 1.1–1.2, decomposes `pgn`, merges/dedupes it against standalone gender/number/person
  (standalone authoritative), and **raises on any unmapped code** (no raw passthrough).
- [x] 1.6 Add a relation-consistency table (relation → canonical case) used by the assembler's guard
  (task 3.2) so the case word is appended only on a match.
- [x] 1.7 Unit-test `qac_labels` **corpus-wide**: sweep every value in every `features{}` dict across
  all ~77k records AND every distinct `relation_ar` across `qac_syntax`; assert each maps to an
  Arabic string containing **no `[A-Za-z]`**; assert `translate_features` raises on a synthetic
  unmapped code; assert `decompose_pgn` round-trips all **25** pgn forms (incl. `M`, `F`, `P`, `2D`,
  `3D`) and dedups against standalone columns. (Covers point [2].)

## 2. Assembler — صرفي (backend)

- [x] 2.1 In `analysis/word_analysis.py::_sarfi`, translate `segments` to Arabic labels and return
  `features` as the ordered Arabic `[{label_ar, value_ar}]` list from `translate_features` (pgn
  decomposed, every key mapped). Keep raw `pos` in the record (data) but the UI will not render it.
  (Covers points [1]/[2].)

## 3. Assembler — نحوي iʿrāب function (SAFE composition) + marker (backend)

- [x] 3.1 Pass the صرفي record (or its `features`) into `_nahwi` so it can read `nominal_case`;
  stop reading the stale `role_ar` from `qac_syntax.json` (leave the field unpopulated).
- [x] 3.2 Compose `iraab_ar`: normalise `relation_ar` through the override table (1.3) so it is never
  ASCII (`root`→«عمدة الجملة») and never a bare case word (`gen`→«اسم مجرور», `voc`→«منادى»); then
  append the case word **only when the relation's canonical case (1.6) matches the present
  `nominal_case`** — otherwise the relation function alone (guards the 83 `Subj`+«مفعول به» mislabels
  → never «مفعول به مرفوع», and `gen`/`root` → never a stutter/Latin). For مبني words (no
  `nominal_case`) show the relation function with **no fabricated marker**. Set `marker_ar =
  case_marker(...)` (omitted per 1.4); keep `head_ref` for المتعلَّق.
- [x] 3.3 Unit-test the نحوي anchor set (Covers point [3]):
  - `13:12:8` السحاب (Obj/ACC) ⇒ `iraab_ar` = «مفعول به منصوب», `marker_ar` = «الفتحة», `head_ref` →
    `13:12:7`;
  - `13:12:7` ويُنشئُ (conj, no case) ⇒ `iraab_ar` = relation only, `marker_ar` omitted;
  - `1:2:1` ٱلْحَمْدُ (root/NOM) ⇒ `iraab_ar` contains **no ASCII** (not «root …»);
  - `1:1:1` بِسْمِ (gen/GEN) ⇒ `iraab_ar` = «اسم مجرور» (no «مجرور مجرور»);
  - `1:2:4` ٱلْعَٰلَمِينَ (GEN, number P) ⇒ `marker_ar` **omitted** (not «الكسرة»);
  - `2:80:4` ٱلنَّارُ (Subj-tagged «مفعول به», NOM) ⇒ `iraab_ar` does **not** read «مفعول به مرفوع»;
  - a مبني pronoun (POS PRON, no case) ⇒ `iraab_ar` present, `marker_ar` omitted, no ASCII.
- [x] 3.4 (Removed — out of scope.) Dropping the `role_ar = pos_ar` line in `ingestion/qac_treebank.py`
  is an ingestion-hygiene change requiring a build edit the "code-only / no-re-ingestion" constraint
  forbids here; the assembler simply stops reading the field. File it separately if desired.

## 4. Assembler — lemma-scoped naẓāʾir (backend)

- [x] 4.1 In `_nazair`, filter `root_graph` candidates to refs whose `qac_words[ref].lemma` equals the
  selected word's lemma; attach `lemma`/`lemma_display` to each returned entry.
- [x] 4.2 When the same-lemma set is below the threshold (default 3), include other lemmas but tag them
  by lemma so the UI can group; keep the existing cap.
- [x] 4.3 Unit-test naẓāʾir (Covers point [4]): on `13:12:8` السحاب (dense: 8 same-lemma siblings)
  يُسحبون/يسحبون are absent from the same-lemma group; **and** a second, sparse anchor (a root whose
  selected lemma has < 3 siblings) exercises the grouped-by-lemma fallback with distinct-lemma
  labelling; determinism preserved in both.

## 5. API models (backend) + display-field contract

- [x] 5.1 Update `api/models/qlisan.py`: `SarfiLevel.features` → ordered Arabic list + Arabic
  `segments`; `NahwiLevel` gains `iraab_ar`/`marker_ar` (keep `role_ar` in the model for shape-compat,
  no longer populated); `Nazair` gains `lemma`/`lemma_display`. Keep raw `pos`/`relation` as data
  (not display). Preserve the four-level ordered response shape and `available` flags.
- [x] 5.2 Endpoint test: enumerate the **display fields** (`pos_ar`, `features[].label_ar`,
  `features[].value_ar`, `segments[]`, `iraab_ar`, `marker_ar`, `nazair[].*` — **not** raw
  `pos`/`relation`) and assert no `[A-Za-z]` in them, over the full anchor set from 3.3 plus a random
  corpus sample (a verb, a particle, a مبني word), not the single demo word.

## 6. Frontend rendering (Arabic-only)

- [x] 6.1 In `frontend/src/app/qlisan/page.tsx` `SarfiLevel`: relabel «المقاطع» → «البنية الصرفية»,
  render Arabic segments, render features from the ordered `{label_ar, value_ar}` list, and remove the
  raw `{level.pos}` and `{k}: {String(v)}` fallbacks.
- [x] 6.2 In `NahwiLevel`: bind «الموقع الإعرابي» to `iraab_ar`; add the «العلامة» row (`marker_ar`)
  **rendered as a distinct «الأصل» hint outside the «معطى محقّق» badge**, shown only when present;
  keep «المتعلَّق»; **remove the standalone «العلاقة» (`relation_ar`) row** (page.tsx:537–548) and the
  gray raw `{level.relation}` fallback — `iraab_ar` subsumes them.
- [x] 6.3 Render naẓāʾir grouped/labelled by `lemma_display`.
- [x] 6.4 Update `frontend/src/lib/types.ts` to match the new model fields; keep the «معطى محقّق» badge
  on the **verbatim** صرفي/نحوي fields only (not the derived marker).

## 7. Update existing tests, validation & docs

- [x] 7.1 Update `tests/test_qlisan_analysis.py`: replace the `nahwi["role_ar"]` truthy assertion
  (available case, ~line 98) with an `iraab_ar` assertion; reconcile the `sarfi["pos"]` assertion
  (~line 91) with 5.1 (raw `pos` stays in the record → assertion still holds); keep the LLM-marker and
  unavailable-case assertions.
- [x] 7.2 Run `openspec validate fix-qlisan-fiche-display --strict` and fix any issues.
- [x] 7.3 Manual check on the live fiche (13:12 السحاب): البنية الصرفية with بادئة/جذع, Arabic-only
  features (no `IMPF`/`SP:`/`pgn`), الموقع الإعرابي = مفعول به منصوب / العلامة = الفتحة (outside the
  badge) / المتعلَّق → 13:12:7, no duplicate «العلاقة» row, and يُسحبون gone from the naẓāʾir strip;
  spot-check 1:1:1 and 1:2:1 for no «مجرور مجرور»/«root».
- [x] 7.4 (Optional) Frontend-label coverage accepted as a manual-only gap (no component/DOM test
  added); the «البنية الصرفية» label, marker-outside-badge, and removed relation row are verified by
  the backend tests + the live manual check (7.3).
- [x] 7.5 Note the new `analysis/qac_labels.py` mapping module in `CLAUDE.md`/`architecture.md` if the
  QLisan section documents the assembler pipeline.
