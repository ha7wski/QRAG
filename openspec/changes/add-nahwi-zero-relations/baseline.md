# Baseline — Zero-relation coverage over the whole corpus

Measured **before** the proposal was frozen, with the prototype in `baseline.py`
(reproduce: `python openspec/changes/add-nahwi-zero-relations/baseline.py baseline-coverage.tsv`).
Source: `data/processed/qac_words.json` (77 429 words) + `qac_syntax.json` (76 639 annotated).

## Coverage

| bucket | words | share | badge |
|---|---:|---:|---|
| relatum — carries one of the 4 relations, with a السبب | 38 742 | 50.0 % | معطى محقّق |
| marker — أداة/مسند: carries a relation, no السبب | 29 108 | 37.6 % | معطى محقّق |
| **verified subtotal** | **67 850** | **87.6 %** | معطى محقّق |
| minted عطف marker (754 standalone CONJ, no QAC role) | 754 | 1.0 % | **not** محقّق |
| **shown subtotal** | **68 604** | **88.6 %** | |
| omitted + logged — no relation invented | 8 825 | 11.4 % | — |

## Distribution by relation

| relation | words | of shown | of corpus |
|---|---:|---:|---:|
| إسناد | 28 701 | 41.8 % | 37.1 % |
| إضافة | 21 361 | 31.1 % | 27.6 % |
| تخصيص | 11 944 | 17.4 % | 15.4 % |
| توضيح | 6 598 | 9.6 % | 8.5 % |

The pyramid holds: الإسناد is the single largest relation, as the theory's apex predicts.

## Distribution by role

| role | words | share | bucket |
|---|---:|---:|---|
| مسند | 22 244 | 28.7 % | marker (verb) |
| مجرور بأداة الإضافة | 10 259 | 13.2 % | relatum |
| مخصِّص | 9 707 | 12.5 % | relatum |
| أداة الإضافة | 7 514 | 9.7 % | marker (حرف جر) |
| مسند إليه | 6 457 | 8.3 % | relatum |
| تابع | 5 843 | 7.5 % | relatum |
| مضاف إليه | 3 588 | 4.6 % | relatum |
| أداة التخصيص | 2 237 | 2.9 % | marker (حرف نصب) |
| أداة العطف | 755 | 1.0 % | 1 marker + 754 minted |

## معرب vs مبني — which السبب form fires

The full sentence «منصوب لأنه تخصيص (مفعول به)» needs a lafẓī case. **79.8 %** of relata
(30 907 / 38 742) have one; the other **20.2 %** are مبني and take the «في محلّ نصب لأنه تخصيص»
variant. Neither form is ever fabricated for a marker (a verb or حرف bears no case at all).

| relation | معرب | مبني |
|---|---:|---:|
| إسناد | 6 825 | 2 520 |
| تخصيص | 8 490 | 1 217 |
| إضافة | 10 700 | 3 147 |
| توضيح | 4 892 | 951 |

## Omitted — triage of the 11.4 %

Every row below is enumerated in `baseline-coverage.tsv` (`ref · word · relation · relation_ar · reason`).

| reason | words | share | what it is | ambiguous? |
|---|---:|---:|---|---|
| `non-nominal-pos` | 6 168 | 7.97 % | NEG 2 225 · COND 959 · SUB 659 · RES 551 · CERT 401 · INTG 399 · PRO 292 · … — particles whose function (نفي، شرط، استفهام، حصر، تحقيق) is **outside** the four relations | no — out of theory |
| `case-conflict` | 1 006 | 1.30 % | QAC contradicts its own case tag: «مفعول به» 463 · root 146 · «مضاف إليه» 136 · «اسم إن» 63 · «حال» 50 … | **yes** |
| `no-case` | 798 | 1.03 % | T 358 · PRON 255 · DEM 80 · LOC 54 — مبني word whose relation (متعلق/صلة/…) fixes no case either | partly |
| `tabi-non-nominal` | 740 | 0.96 % | a تبعية relation landing on a particle (NEG 418 · P 87 · COND 85 · ACC 46 …) | no |
| `prep-in-nominal-slot` | 77 | 0.10 % | حرف جر tagged with a nominal slot (نائب فاعل، خبر) — a شبه جملة filling that slot | **yes** |
| `absent-from-treebank` | 36 | 0.05 % | INL 27 · COND 4 · ANS 3 · PRON 1 · LOC 1 (the 754 CONJ are minted, not omitted) | no |

**Genuinely ambiguous: 1 083 words = 1.4 %.** The remaining 8.0 % is not a gap the mapper could
close — those particles have no relation among the four to find. This is why no LLM fallback ships
in this change.

## Per-relation sampling — three wrong-but-complete defects the aggregate hid

Inspecting samples *per relation* (not just the rate) caught three cases where a naive mapping
produced a complete-looking but false relation. Each is closed by a guard in `design.md`; the
percentages above are already **post-guard**.

| # | example | naive output | why it was wrong | guard |
|---|---|---|---|---|
| 1 | `2:2:3 لَا` — POS `NEG`, QAC `circ`/«حال» | تخصيص / مخصِّص | a حرف bears no case, so it can never be a relatum; the naive pass read the relation's canonical ACC and stopped | relatum requires a nominal POS **or** a present `nominal_case` |
| 2 | `1:1:2 ٱللَّهِ` (Poss) vs `1:2:2 لِلَّهِ` (gen) | both «مضاف إليه» | erases the theory's own split between الإضافة المباشرة and الإضافة بواسطة أدوات الإضافة | GEN role splits: `Poss`→مضاف إليه, `gen`→مجرور بأداة الإضافة |
| 3 | `1:7:7 عَلَيْهِمْ` — POS `P`, QAC «نائب فاعل» | أداة الإضافة | drops the nominal slot the جار ومجرور fills; the bare أداة label asserts less than QAC knows | a `P` carrying a nominal-slot relation is omitted + logged, not mislabelled |

Defect 1 is the exact shape of the lafẓ al-jalāla failure from the mīzān work: **a coverage rate
cannot see a relation that is confidently wrong.** Sampling per relation is therefore a required
step of the acceptance procedure, not an optional check.
