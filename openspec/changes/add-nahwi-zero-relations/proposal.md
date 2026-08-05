## Why

The نحوي card today answers *what slot is this word in* — «الموقع الإعرابي: مفعول به منصوب»,
«العلامة: الفتحة», «المتعلَّق: 1:6:1». It never answers **why the word carries that mark**. A
learner reads «منصوب» and takes it as a brute fact of the parse; the mark looks like an accident
of the verb it follows rather than the visible sign of a semantic relation.

نظرية اكتشاف الصفر (د. سناء البياتي) supplies exactly the missing layer. It reduces every link
between words to **four relations**, arranged as a pyramid whose apex is الإسناد:

| relation | what it binds (per the source) |
|---|---|
| **إسناد** | يربط المسند إليه بالمسند — the apex; every other relation attaches to it |
| **تخصيص** | يربط المفعولات كلها، والحال، والتمييز، والمستثنى بالإسناد |
| **إضافة** | إما إضافة مباشرة أو إضافة بواسطة أدوات الإضافة المسماة بحروف الجر |
| **توضيح** | يربط الصفة (التوابع) والبيان بالإسناد |

Under this reading the case mark stops being arbitrary: **النصب is the sign of التخصيص**, الجر is
the sign of الإضافة, الرفع is the sign of الإسناد. That single sentence — «منصوب لأنه تخصيص
(مفعول به)» — is what separates a grammar *theory* from a dependency *parser*, and it is derivable
from the treebank we already ship. Nothing else in the fiche has to move.

**Measured first.** A prototype mapper was run over all 77 429 QAC words before this proposal was
written (see `baseline.md` + `baseline-coverage.tsv` in this change):

| bucket | words | share | badge |
|---|---:|---:|---|
| relatum — carries one of the 4 relations | 38 742 | 50.0 % | معطى محقّق |
| marker (أداة/مسند) — carries a relation without being a relatum | 29 108 | 37.6 % | معطى محقّق |
| **shown, verified** | **67 850** | **87.6 %** | معطى محقّق |
| minted عطف marker (754 standalone CONJ, absent from the treebank) | 754 | 1.0 % | *not* محقّق |
| **shown, total** | **68 604** | **88.6 %** | |
| omitted + logged — no relation invented | 8 825 | 11.4 % | — |

Relation split of the 68 604 shown: إسناد 28 701 (41.8 %) · إضافة 21 361 (31.1 %) ·
تخصيص 11 944 (17.4 %) · توضيح 6 598 (9.6 %).

Per-relation sampling — not just the aggregate — caught three *wrong-but-complete* failures that a
coverage rate alone hides, the same trap the mīzān work hit with lafẓ al-jalāla. All three are
closed by guards specified in `design.md`:

1. **Particle promoted to relatum.** `2:2:3 لَا` is tagged `circ`/«حال» by QAC; a naive case-family
   mapping made it «تخصيص / مخصِّص». A حرف carries no case and can never be a relatum.
2. **الإضافة المباشرة conflated with الإضافة بالأداة.** `1:1:2 ٱللَّهِ` (مضاف إليه) and
   `1:2:2 لِلَّهِ` (مجرور بحرف) both landed on «مضاف إليه», erasing the distinction the theory
   itself draws.
3. **حرف جر heading a nominal slot.** `1:7:7 عَلَيْهِمْ` is QAC's «نائب فاعل»; labelling it a bare
   «أداة الإضافة» drops the slot it fills (77 words).

## What Changes

Everything below is **additive**. `iraab_ar`, `marker_ar`, `head_ref`, and the classical fine role
stay exactly as they are; the four levels صوتي/صرفي/نحوي/دلالي keep their order and contents.

- **New deterministic mapper** — a pure-stdlib module derives, per word, from the QAC role already
  on disk: `relation` (1 of 4), `role` (مسند / مسند إليه / مخصِّص / مضاف إليه / مجرور بأداة الإضافة /
  تابع / أداة الإضافة / أداة التخصيص / أداة العطف), and `reason` (the السبب sentence). No LLM, no
  network, no new data file, derived on the fly in the assembler.
- **العلاقة is decided by case FAMILY, not by a per-label list** — رفع→إسناد, نصب→تخصيص,
  جر→إضافة, and تبعية→توضيح (a تابع inherits its متبوع's case, so its family cannot decide). This
  reuses the already-verified `qac_labels.relation_canonical_case`, which resolves اسم/خبر of
  كان-family vs إنّ-family correctly, instead of hardcoding a second role table that could drift.
- **Verbs and particles are markers, never relata** — a verb is مسند, the pole of الإسناد, with no
  case; a حرف جر is أداة الإضافة; a حرف نصب is أداة التخصيص. They get العلاقة and الدور but no
  السبب, because they bear no case mark to explain.
- **New السبب line** — «منصوب لأنه تخصيص (مفعول به)» for a معرب word; «في محلّ نصب لأنه تخصيص
  (مفعول به)» for a مبني one (20.2 % of relata carry no lafẓī case). This is the line that carries
  the theory.
- **754 standalone عطف particles get a minted marker row** (توضيح / أداة العطف, no السبب). They are
  absent from the treebank, so نحوي is `available:false` for them today. The minted row is flagged
  **not** «معطى محقّق» and is enumerated in the coverage log — the relation is asserted from POS,
  not read from QAC.
- **No LLM anywhere in this change.** Of the 11.4 % omitted, only ~1.4 % (1 083 words) is genuinely
  *ambiguous* — QAC contradicting its own case tag (1 006) or a preposition in a nominal slot (77).
  The other 8 % are particles (نفي/شرط/استفهام/حصر/…) that simply fall **outside** the four
  relations; an LLM asked to pick one of four would invent, not resolve. A word whose relation does
  not derive cleanly gets **no relation, the field omitted**, and a coverage-log row — exactly what
  the mīzān did for lafẓ al-jalāla. Whether the 1 083 ambiguous edges deserve a flagged LLM reading
  is a decision for a follow-up change, taken on the triaged log.
- **Frontend: three rows added to the نحوي card** (العلاقة, الدور, السبب), above the existing
  الموقع الإعرابي / المتعلَّق. No new view, no new route. **The D3 verse-pyramid is explicitly out of
  scope** (separate V2 change).

## Capabilities

### New Capabilities
- `nahwi-zero-relations`: the Zero-theory relation layer over the نحوي level — the four-relation
  mapping from QAC roles, the relatum/marker/omitted trichotomy, the السبب rendering, the badge
  discipline, and the coverage log.

### Modified Capabilities
- `qlisan-word-analysis`: the «verified badge covers only verbatim fields» requirement is extended
  — a *derived-but-deterministic* Zero relation keeps «معطى محقّق», while a **minted** marker row
  (asserted from POS, with no QAC role behind it) must be visibly distinguished from it.

## Impact

- **`analysis/zero_relations.py`** — new; pure stdlib, no fastapi/pydantic import, testable in
  isolation (same contract as `analysis/qac_labels.py`).
- **`analysis/qac_labels.py`** — additive only: the Zero mapping tables and the case-family lookup
  that extends `relation_canonical_case` with the two cases it deliberately withholds (`gen`→GEN).
- **`analysis/word_analysis.py::_nahwi`** — calls the mapper and merges its fields into the نحوي
  dict. The existing `iraab_ar` / `marker_ar` / `head_ref` composition is untouched.
- **`api/models/qlisan.py::NahwiLevel`** — four additive optional fields (`zero_relation`,
  `zero_role`, `zero_reason`, `zero_verified`); no field removed or renamed, so existing clients
  keep working.
- **`frontend/src/lib/types.ts` + `frontend/src/app/qlisan/page.tsx`** — three rows in the نحوي
  card and a non-محقّق visual treatment for minted rows.
- **Not touched:** `ingestion/qac_treebank.py` and the QAC artifacts on disk (no re-ingest, no
  schema change), the صرفي/صوتي/دلالي levels, `analysis/mizan.py`, retrieval, and every other route.
- **Tests (local-only):** a ~26-word gold set covering each relation, both marker classes, and the
  three guard defects, plus a corpus-wide sweep asserting the baseline rates do not regress.
