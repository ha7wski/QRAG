## 1. Mapping tables in `qac_labels.py` (additive only)

- [ ] 1.1 Add the four relation constants (`إسناد` / `تخصيص` / `إضافة` / `توضيح`) and the
      `FAMILY = {NOM: إسناد, ACC: تخصيص, GEN: إضافة}` lookup. Do not touch any existing table.
- [ ] 1.2 Add `zero_canonical_case(relation, relation_ar)` — delegates to the existing
      `relation_canonical_case`, adding only `relation == "gen"` → `"GEN"` (which the display path
      deliberately withholds because «اسم مجرور» already names its case). Docstring must say why
      the delegation exists rather than a second role table: the كان/إنّ sister resolution lives in
      `relation_canonical_case` and must not be duplicated.
- [ ] 1.3 Add the constant sets `TABAIYA` (`Adj`/`App`/`conj`/`emph`), `NOMINAL_POS`
      (`N`/`PN`/`ADJ`/`PRON`/`REL`/`DEM`/`T`/`LOC`) and `NOMINAL_SLOT`
      (`Subj`/`Pass`/`Pred`/`Obj`/`Poss`/`Spec`/`circ` + the إنّ/أن families), each with a comment
      naming the guard it serves.
- [ ] 1.4 Add `CASE_NOUN_AR = {NOM: رفع, ACC: نصب, GEN: جر}` for the مبني «في محلّ …» form
      (`NOMINAL_CASE_AR` already covers مرفوع/منصوب/مجرور).

## 2. The mapper — `analysis/zero_relations.py`

- [ ] 2.1 Create the module with the `analysis/`-house header: pure stdlib, no
      fastapi/pydantic/network import, `ROOT = Path(__file__).resolve().parents[1]` + `sys.path`
      anchoring. Document that it derives on the fly and writes no file.
- [ ] 2.2 Implement `derive(word_record, syntax_record) -> ZeroRelation | None` returning
      `(relation, role, reason, verified)` or `None` plus an omission reason. Rule order is
      load-bearing and must be commented as such:
      **(1)** POS `V` → إسناد / مسند (keyed on POS, never on `relation == "root"` — only 4 751 of
      12 879 `root` rows are verbs);
      **(2)** relation ∈ `TABAIYA` → توضيح / تابع (before the case lookup — a تابع inherits its
      متبوع's case, so the family carries no signal);
      **(3)** POS `P` → إضافة / أداة الإضافة, unless the relation is in `NOMINAL_SLOT` → omit;
      **(4)** POS `ACC` → تخصيص / أداة التخصيص;
      **(5)** relatum path, gated on `NOMINAL_POS or nominal_case`.
- [ ] 2.3 Implement the relatum path: family from `zero_canonical_case`, else the word's own
      `nominal_case`. Role resolution — GEN splits `Poss` → «مضاف إليه» vs anything else →
      «مجرور بأداة الإضافة»; NOM splits «خبر…» → «مسند» vs everything else → «مسند إليه»;
      ACC → «مخصِّص».
- [ ] 2.4 Implement the three guards, each returning a distinct machine-readable omission reason:
      `non-nominal-pos` (a حرف can never be a relatum), `case-conflict` (role's canonical case ≠ the
      word's `nominal_case` — the same guard `_compose_iraab` already applies to the case word), and
      `prep-in-nominal-slot`.
- [ ] 2.5 Implement `compose_reason(...)` — the السبب line, in exactly two forms:
      معرب → `«{case_word} لأنه {relation} ({fine_role})»`;
      مبني → `«في محلّ {case_noun} لأنه {relation} ({fine_role})»`.
      `{fine_role}` comes from `relation_ar_display` so the classical function is preserved verbatim
      inside the sentence. Markers return `None` — never a placeholder reason.
- [ ] 2.6 Implement the minted عطف branch: a word absent from `qac_syntax.json` with POS `CONJ` →
      توضيح / أداة العطف, `reason=None`, `verified=False`. Every other absent word → omitted.
- [ ] 2.7 Add a `__main__` smoke test printing the derivation for 1:6:2, 1:5:1, 10:19:7, 1:2:2 and
      2:2:3 (the last must print an omission, not a relation) — matching the module convention in
      `mizan.py` / `qlisan_data.py`.

## 3. Assembler wiring — `analysis/word_analysis.py`

- [ ] 3.1 In `_nahwi`, call `zero_relations.derive(record, rec)` and merge `zero_relation`,
      `zero_role`, `zero_reason`, `zero_verified` into the returned dict. Leave `iraab_ar`,
      `marker_ar`, `head_ref`, `relation`, `relation_ar` and `role_ar` byte-identical.
- [ ] 3.2 Handle the `rec is None` branch: POS `CONJ` gets the minted marker with
      `available=True`/`zero_verified=False`; every other absent word keeps today's
      `available=False` payload plus the four Zero fields as `None`.
- [ ] 3.3 Update the `_nahwi` docstring and the module header to describe the Zero layer and the
      badge split (derived-from-verbatim = محقّق, minted = not محقّق).
- [ ] 3.4 Verify no import cycle and that `analysis/word_analysis.py` still imports without
      fastapi/pydantic present.

## 4. API model — `api/models/qlisan.py`

- [ ] 4.1 Add to `NahwiLevel`, all optional with safe defaults: `zero_relation: str | None = None`,
      `zero_role: str | None = None`, `zero_reason: str | None = None`,
      `zero_verified: bool = False`. Remove/rename nothing.
- [ ] 4.2 Extend the `NahwiLevel` docstring: what each field means, that `zero_reason` is absent for
      markers by design, and that `zero_verified=False` marks a minted (asserted, not read) row.
- [ ] 4.3 Confirm `/qlisan/word` serialises the new fields and that a response with them all absent
      still validates (backward compatibility).

## 5. Frontend — three rows in the نحوي card

- [ ] 5.1 Extend `QlisanNahwi` in `frontend/src/lib/types.ts` with the four optional fields.
- [ ] 5.2 In `NahwiLevel` (`frontend/src/app/qlisan/page.tsx`), render العلاقة, الدور and السبب
      **above** the existing الموقع الإعرابي and المتعلَّق. Each row renders only when its field is
      present. Do not touch the الموقع الإعرابي / المتعلَّق rows or the صرفي card's العلامة.
- [ ] 5.3 Give السبب the visual weight of the card's key line (it is the row that distinguishes the
      theory from a parser); keep العلاقة/الدور as ordinary rows.
- [ ] 5.4 When `zero_verified === false`, render the Zero rows with a visibly distinct,
      non-«معطى محقّق» treatment (the `pending`/`sourced` tone already used by `LevelCard`), so a
      minted عطف marker can never be read as verified data.
- [ ] 5.5 Confirm RTL rendering of the السبب sentence (mixed Arabic + parenthesised role) and that
      `next build` passes with no type error.

## 6. Gold set — `tests/test_zero_relations.py` (local-only)

One assertion per row; each ref below was verified against the on-disk treebank while writing this
change. Expected value = (relation, role, السبب).

- [ ] 6.1 **إسناد — relata:** `2:7:2 ٱللَّهُ` (فاعل NOM) → إسناد / مسند إليه / «مرفوع لأنه إسناد
      (فاعل)» · `2:5:8 ٱلْمُفْلِحُونَ` (خبر NOM) → إسناد / **مسند** · `10:19:3 ٱلنَّاسُ` (اسم كان
      NOM) → إسناد / مسند إليه · `2:48:12 شَفَٰعَةٌ` (نائب فاعل NOM) → إسناد / مسند إليه.
- [ ] 6.2 **إسناد — the verb as pole:** `10:19:7 فَٱخْتَلَفُوا۟` (POS V, relation `root`) →
      إسناد / مسند, **السبب absent** · `2:3:2 يُؤْمِنُونَ` (POS V, relation `صلة`) → إسناد / مسند —
      proves the rule keys on POS, not on `root`.
- [ ] 6.3 **تخصيص:** `1:6:2 ٱلصِّرَٰطَ` (مفعول به ACC) → تخصيص / مخصِّص / «منصوب لأنه تخصيص
      (مفعول به)» · `2:25:27 مُتَشَٰبِهًا` (حال ACC) · `2:26:28 مَثَلًا` (تمييز ACC) ·
      `2:25:18 رِّزْقًا` (مفعول مطلق ACC) · `10:19:5 أُمَّةً` (خبر كان ACC → تخصيص, the family
      counterpart of 6.1's اسم كان).
- [ ] 6.4 **تخصيص — the مبني form:** `1:5:1 إِيَّاكَ` (مفعول به, no case) → «في محلّ نصب لأنه تخصيص
      (مفعول به)» · `2:6:2 ٱلَّذِينَ` (اسم إن, no case) → تخصيص / مخصِّص, «في محلّ نصب …».
- [ ] 6.5 **إضافة — the two forms must differ:** `1:1:2 ٱللَّهِ` (`Poss`) → إضافة / **مضاف إليه**
      vs `1:2:2 لِلَّهِ` (`gen`) → إضافة / **مجرور بأداة الإضافة**. Assert the roles are not equal
      (guards defect 2).
- [ ] 6.6 **إضافة — compound word:** `1:1:1 بِسْمِ` (ب + اسم in one QAC word) → exactly one row,
      إضافة / مجرور بأداة الإضافة.
- [ ] 6.7 **توضيح — must beat the case family:** `1:1:3 ٱلرَّحْمَٰنِ` (صفة, GEN) → توضيح / تابع,
      **not** إضافة · `2:31:4 كُلَّهَا` (توكيد, ACC) → توضيح / تابع, **not** تخصيص ·
      `1:2:3 رَبِّ` (بدل, GEN) · `1:7:9 ٱلضَّآلِّينَ` (معطوف, GEN).
- [ ] 6.8 **Markers get a relation and no السبب:** `2:2:5 فِيهِ` (POS P) → إضافة / أداة الإضافة ·
      `2:6:1 إِنَّ` (POS ACC) → تخصيص / أداة التخصيص. Assert `zero_reason is None` for both, and
      that neither ever receives a relatum role.
- [ ] 6.9 **Minted عطف:** `2:6:7 أَمْ` (POS CONJ, absent from `qac_syntax.json`) → توضيح /
      أداة العطف, `zero_verified is False`, no السبب.
- [ ] 6.10 **Fused prefix adds nothing:** `2:4:10 وَبِٱلْءَاخِرَةِ` → exactly one relation (إضافة);
      assert no second عطف row is produced.
- [ ] 6.11 **Guard 1 — particle never a relatum:** `2:2:3 لَا` (POS NEG, QAC `circ`/«حال») → no
      relation, omission reason `non-nominal-pos`. Assert it is **not** تخصيص/مخصِّص — this is the
      lafẓ al-jalāla failure shape and the aggregate rate cannot see it.
- [ ] 6.12 **Guard 2 — case conflict omits:** `2:80:4 ٱلنَّارُ` («مفعول به» but NOM) → no relation,
      reason `case-conflict`; assert `iraab_ar` still renders the function name alone, unchanged.
- [ ] 6.13 **Guard 3 — preposition in a nominal slot:** `1:7:7 عَلَيْهِمْ` (POS P, «نائب فاعل») →
      no relation, reason `prep-in-nominal-slot`.
- [ ] 6.14 **Omission never degrades the level:** for every omitted ref in 6.11–6.13, assert the
      نحوي level still returns its existing `iraab_ar` / `head_ref` and that `available` is
      unchanged by the Zero layer.

## 7. Integration tests

- [ ] 7.1 **Quranic four-relation verse — 44:10** فَٱرْتَقِبْ يَوْمَ تَأْتِى ٱلسَّمَآءُ بِدُخَانٍ
      مُّبِينٍ (all 6 words map, and it mirrors the deck's demo structure exactly):
      إسناد تأتى↔ٱلسَّمَآءُ (verb مسند + فاعل مسند إليه) · تخصيص فَٱرْتَقِبْ↔يَوْمَ (مفعول به) ·
      إضافة بِدُخَانٍ (مجرور بأداة الإضافة) · توضيح دخان↔مُّبِينٍ (صفة). Assert relation, role,
      السبب and `head_ref` for each word through `analyze_word`.
- [ ] 7.2 **The deck's demo sentence** يَعْبُدُ الإنسانُ العاقلُ خالِقَ الكَوْنِ — **not Quranic**,
      so it cannot go through the API. Test the mapper directly on synthetic QAC-shaped records:
      إسناد يعبد↔الإنسان · توضيح الإنسان↔العاقل · تخصيص يعبد↔خالق · إضافة خالق↔الكون. Note in the
      test docstring why it is synthetic.
- [ ] 7.3 Assert the fixed level order صوتي → صرفي → نحوي → دلالي and the صرفي/صوتي/دلالي payloads
      are byte-identical before and after this change for a sample of words (no collateral drift).

## 8. Corpus sweep + coverage log

- [ ] 8.1 Promote `openspec/changes/add-nahwi-zero-relations/baseline.py` into a maintained sweep
      that imports the **shipped** `analysis/zero_relations.py` instead of re-implementing the
      mapper, and writes the coverage log TSV (`ref · word · relation · relation_ar · reason`).
- [ ] 8.2 Add a corpus-wide regression test asserting the measured baseline does not regress:
      verified ≥ 87.6 %, shown ≥ 88.6 %, omitted ≤ 11.4 %, and the per-relation split within
      tolerance (إسناد 28 701 · إضافة 21 361 · تخصيص 11 944 · توضيح 6 598).
- [ ] 8.3 Assert every omitted word carries a reason from the closed set
      {`non-nominal-pos`, `case-conflict`, `no-case`, `tabi-non-nominal`, `prep-in-nominal-slot`,
      `absent-from-treebank`} — an unrecognised reason fails the sweep (guards against silent
      drift, same contract as `translate_features` raising on an unmapped code).
- [ ] 8.4 Assert no word ever receives a relation outside the four, and that no marker ever carries
      a السبب.

## 9. Acceptance — per relation, not only in aggregate

- [ ] 9.1 Draw and **read** a sample of at least 20 words for **each** of إسناد, تخصيص, إضافة,
      توضيح separately. The rule inherited from the lafẓ al-jalāla case: a relation that is
      confidently wrong is complete-looking and therefore invisible in the coverage rate.
- [ ] 9.2 Sample the marker classes separately (verb مسند, أداة الإضافة, أداة التخصيص, minted
      أداة العطف) — a marker mislabelled as a relatum is the exact defect guard 1 exists for.
- [ ] 9.3 Triage the omission log by reason and record, in this change, whether any bucket should
      later warrant a flagged «قراءة مرجَّحة» reading — explicitly deferred, not decided here.
- [ ] 9.4 Run the fiche in the live app for 44:10 and for a word in each guard bucket; confirm the
      minted row is visually distinguishable from «معطى محقّق» and that no existing row moved.
- [ ] 9.5 Run `python -m pytest -q` and `cd frontend && npx vitest run`; confirm the existing
      QLisan suites (`test_qlisan_analysis`, `test_qlisan_fiche_fix`, `test_qlisan_regressions`,
      `test_qlisan_spine`, `test_qlisan_index`) still pass unchanged.
