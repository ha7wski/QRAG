## Context

The نحوي level is assembled by `analysis/word_analysis.py::_nahwi`, which looks the word's ref up
in `qac_syntax.json` and returns four rendered fields plus two raw ones:

```python
rec = qac_syntax().get(self_ref)          # None ⇒ available:false, never fabricated
features = record.get("features", {})     # from the صرفي record
nominal_case = features.get("nominal_case")
relation_ar = rec.get("relation_ar")
return {
    "available": True,
    "relation":   rec.get("relation"),           # raw QAC code — data, not rendered
    "relation_ar": relation_ar,                  # raw source label — data, not rendered
    "iraab_ar":   _compose_iraab(relation_ar, nominal_case),   # الموقع الإعرابي
    "marker_ar":  qac_labels.case_marker(record),              # العلامة (rendered in the صرفي card)
    "head_ref":   rec.get("head_ref"),                         # المتعلَّق
}
```

Three existing pieces are load-bearing for this change and are reused rather than duplicated:

- **`qac_labels.relation_canonical_case(relation_ar)`** already answers *what case does this role
  canonically take* — including the hard part, resolving اسم/خبر of the كان-family (اسمها مرفوع،
  خبرها منصوب) against the إنّ-family (اسمها منصوب، خبرها مرفوع) by looking up the sister in
  `_KAANA_SISTERS` / `_INNA_SISTERS`. That is exactly the case-family signal the Zero layer needs.
- **`_compose_iraab`'s mismatch guard** already refuses to append a case word when the role's
  canonical case disagrees with the word's actual `nominal_case` — the guard that catches the 83
  `Subj`-tagged-«مفعول به» source mislabels. The Zero layer must fail the same way on the same rows.
- **`qac_labels.case_marker(word)`** derives العلامة and returns `None` rather than fabricating one
  for duals, plurals, and proper-noun genitives.

The corpus shape that drives every decision below (full numbers in `baseline.md`): 187 distinct
`(relation, relation_ar)` pairs over 76 639 annotated words; `root` is the largest (12 879) and is
**not** uniformly a verb — POS `V` 4 751, `ACC` 1 714, `NEG` 1 149, `N` 985, `COND` 799, … QAC's
`root` marks *the first element of the sentence*, not the predicate.

## Goals / Non-Goals

**Goals:**

- Expose, per word, the Zero relation (1 of 4), the role under it, and the السبب sentence that
  explains the case mark — derived deterministically from data already on disk.
- Keep the existing i'rāb intact and unmoved. This layer sits *over* it: العلاقة → الدور →
  الموقع الإعرابي → العلامة → المتعلَّق, from theory down to detail.
- Preserve the fact/interpretation discipline: derived-but-deterministic keeps «معطى محقّق»;
  anything asserted rather than read is visibly not محقّق; anything that does not derive is omitted
  and logged, never guessed.
- Keep the mapper importable and testable without fastapi/pydantic/Qdrant/network, like
  `qac_labels.py` and `mizan.py`.

**Non-Goals:**

- **The D3 verse pyramid is out of scope** — this change adds rows to the word fiche and nothing
  else. No new route, no verse-level graph, no cross-word edge rendering.
- No LLM, in any tier, in this change (decided; see Decision 7).
- No change to `ingestion/qac_treebank.py`, the QAC artifacts on disk, or the QAC tagset. No
  re-ingest is required to ship this.
- No change to the صرفي, صوتي, or دلالي levels; `marker_ar` keeps rendering in the صرفي card where
  it is today.
- Not a reanalysis of the Quran. Where QAC is wrong or silent, this layer is silent too.

## Decisions

### 1. العلاقة is decided by case FAMILY, not by a hand-written role→relation table

The four relations map onto the three cases plus تبعية:

| family | relation | why |
|---|---|---|
| رفع | **إسناد** | فاعل، نائب فاعل، مبتدأ، خبر، اسم كان، خبر إنّ |
| نصب | **تخصيص** | مفعول به، مفعول مطلق/لأجله، ظرف، حال، تمييز، مستثنى، اسم إنّ، خبر كان |
| جر | **إضافة** | مضاف إليه، مجرور بحرف |
| تبعية | **توضيح** | نعت، توكيد، بدل، عطف بيان/نسق |

Implemented as `FAMILY[canonical_case(relation, relation_ar)]` where `canonical_case` delegates to
`relation_canonical_case` and only adds the one case it deliberately withholds (`gen` → `GEN`,
withheld because its display override «اسم مجرور» already names the case).

*Alternative rejected:* a second explicit table `{"مفعول به": تخصيص, "حال": تخصيص, …}`. It would
duplicate 187 source labels, drift from `relation_canonical_case`, and — the real defect — get the
كان/إنّ families wrong unless it re-implemented the sister lookup. Deriving from the family means
«اسم كان» lands on إسناد and «خبر كان» on تخصيص for free, and both stay correct if the sister sets
are ever corrected.

*Consequence worth stating plainly:* «اسم إنّ» is منصوب, so it maps to **تخصيص** even though it is
functionally the مسند إليه. That is not a bug — under the theory the case *is* the sign of the
relation, and إنّ is a حرف نصب, i.e. أداة التخصيص. الدور keeps the functional reading visible.

### 2. تبعية is decided by the relation, never by the case

A تابع copies its متبوع's case, so its case family carries no information: «الرَّحْمَٰنِ» in
`1:1:3` is مجرور only because «ٱللَّهِ» is. Relations `Adj` / `App` / `conj` / `emph` are therefore
matched *before* the family lookup and map straight to **توضيح**, role تابع. Skipping this order
would file every genitive نعت under إضافة — 5 843 words wrong.

### 3. Verbs and particles are markers, not relata

Three marker classes, each carrying a relation without being one of its ends:

| POS / condition | العلاقة | الدور | السبب |
|---|---|---|---|
| `V` (any relation) | إسناد | مسند | — (لا محلّ له من الإعراب) |
| `P` (حرف جر) | إضافة | أداة الإضافة | — |
| `ACC` (حرف نصب) | تخصيص | أداة التخصيص | — |

The verb rule is checked **first**, before the relation lookup, because QAC's `root` is not a
predicate marker (4 751 of 12 879 `root` rows are verbs; the rest are particles and nouns). Keying
on POS `V` rather than on `relation == "root"` yields 22 244 مسند markers — every verb in the
corpus, whatever its relation (`root`, `صلة`, `معطوف`, `شرط`, …) — instead of the 4 751 a
relation-keyed rule would find.

Markers get no السبب: they bear no case mark, so there is nothing to explain. Fabricating
«لا محلّ له من الإعراب» as a *reason* would dress a non-fact as one; the field is simply absent.

### 4. الدور splits الإضافة into its two theory-recognised forms

The source itself distinguishes «إضافة مباشرة» from «إضافة بواسطة أدوات الإضافة المسماة بحروف
الجر». So a GEN relatum resolves its role by relation, not by case: `Poss` → **مضاف إليه**
(3 588 words), anything else GEN → **مجرور بأداة الإضافة** (10 259). Collapsing both to «مضاف إليه»
was defect 2 in `baseline.md` — complete-looking output that erased a distinction the theory draws.

Under رفع, الدور splits by whether the role name starts with «خبر»: خبر/خبر كان/خبر إنّ → **مسند**
(the predicate), everything else → **مسند إليه**.

### 5. Three guards keep a rate from hiding a false relation

Ordered, and each traceable to a defect the per-relation sampling caught:

1. **A relatum must be able to bear a case.** POS ∈ {N, PN, ADJ, PRON, REL, DEM, T, LOC} **or** a
   present `nominal_case`. Without it, `2:2:3 لَا` (a NEG tagged `circ`/«حال») becomes «تخصيص /
   مخصِّص» — confidently wrong, invisible in the coverage rate.
2. **A case conflict omits, never resolves.** If the role's canonical case and the word's actual
   `nominal_case` disagree (1 006 words), the relation is omitted and logged. This is the same rule
   `_compose_iraab` already applies to the case word, applied to the relation; the two must agree,
   or the fiche would show «مفعول به» with no case word yet claim تخصيص underneath.
3. **A حرف جر in a nominal slot omits.** When a `P` carries a nominal-slot relation
   (`Subj`/`Pass`/`Pred`/`Obj`/`Poss`/`Spec`/`circ`/the إنّ-`an` families), the جار ومجرور fills that
   slot; calling it a bare أداة الإضافة asserts less than QAC knows, and calling it the slot-filler
   asserts more than a single word can carry. 77 words, omitted and logged for triage.

### 6. The السبب string — one line, two forms

| word | form |
|---|---|
| معرب (79.8 % of relata) | `{case_word} لأنه {relation} ({fine_role})` → «منصوب لأنه تخصيص (مفعول به)» |
| مبني (20.2 %) | `في محلّ {case_noun} لأنه {relation} ({fine_role})` → «في محلّ نصب لأنه تخصيص (مفعول به)» |
| marker | *absent* |

`{case_word}` is `NOMINAL_CASE_AR[case]` (مرفوع/منصوب/مجرور), `{case_noun}` its maṣdar
(رفع/نصب/جر), and `{fine_role}` the existing `relation_ar_display(relation_ar)` — so the classical
fine role is preserved verbatim *inside* the theory sentence. For a مبني relatum the case comes
from the role's canonical case (the word has none of its own), which is precisely why guard 2 must
run first: without it a مبني word would get a محلّ derived from a role QAC contradicts elsewhere.

العلامة is **not** duplicated into the نحوي card and is **not** re-worded. It stays in the صرفي
card exactly as today; the السبب line already names the case, so restating «الفتحة — علامةُ
التخصيص» would be a third rendering of the same fact.

### 7. No LLM tier, and the reason is measured

Of the 11.4 % omitted, only 1 083 words (1.4 %) are ambiguous in the sense an LLM could address:
QAC contradicting its own case tag, or a preposition in a nominal slot. The dominant bucket —
6 168 words, 8.0 % — is particles (نفي، شرط، استفهام، حصر، تحقيق، نهي، …) whose function is simply
**not one of the four relations**. A model asked to choose one of four for «لَا» must produce a
relation that does not exist, and the result would be indistinguishable, in the coverage rate, from
a correct one. That is the failure mode this project already paid for once.

So: omit, log, ship the log. Whether the 1 083 ambiguous edges warrant a flagged
«قراءة مرجَّحة» reading is a follow-up decision to be taken *on the triaged log*, not in advance.

### 8. Minted عطف markers are shown, but not as محقّق

754 standalone CONJ words are absent from `qac_syntax.json` entirely, so نحوي is
`available:false` for them today. They get a minted marker row — العلاقة توضيح, الدور أداة العطف,
no السبب — because a reader clicking a و is owed something. But no QAC role backs the assertion, so
the row carries a distinct, visibly non-محقّق treatment and is enumerated in the coverage log.

This is the one place the fiche shows a relation it did not read from the treebank, and it forces
the existing spec requirement to be sharpened: «معطى محقّق» must now distinguish *derived from a
verbatim field* (which it covers) from *asserted from POS* (which it does not).

Fused و/ف prefixes — the thousands of `وَبِٱلْءَاخِرَةِ`-style words — are **not** given a second
relation row. The word already carries its own; adding a prefix relation would put two relations on
one fiche with no way to say which the case mark answers to.

### 9. Derivation is on the fly, in the assembler

`analysis/zero_relations.py` exposes one pure function over `(word_record, syntax_record)` → a
`ZeroRelation` result (or `None`, with a reason). `_nahwi` calls it and merges the fields; nothing
is precomputed, no new file is written to `data/processed/`, and `qac_words.json` /
`qac_syntax.json` are read-only as they are today. The coverage log is produced by a script for
triage, not consumed at request time.

### 10. API fields are additive and optional

`NahwiLevel` gains `zero_relation`, `zero_role`, `zero_reason`, `zero_verified`, all defaulting to
`None`/`False`. No existing field is removed, renamed, or has its meaning changed — `role_ar` stays
deprecated-but-present, `iraab_ar`/`marker_ar`/`head_ref` keep their exact semantics. A client that
ignores the new fields renders precisely what it renders today.

## Risks / Trade-offs

- **The four relations are a theoretical commitment, not a neutral fact.** Al-Bayati's framework is
  one reading of Arabic syntax, not consensus grammar. → It is presented as an *additional* layer
  over an unchanged classical i'rāb; the fine role (مفعول به، حال، …) is preserved inside the السبب
  sentence, so a reader who rejects the theory loses nothing and can still read the classical
  analysis intact.
- **«اسم إنّ» → تخصيص will read as wrong to some users**, since it is functionally the مسند إليه.
  → الدور keeps the functional reading, and the السبب names the fine role, so the fiche shows both
  the family verdict and the classical function rather than silently choosing.
- **Whole-word granularity blurs compound tokens.** `1:1:1 بِسْمِ` is ب + اسم in one QAC word and
  gets «مجرور بأداة الإضافة» — the أداة and the مجرور collapsed into one row. → Accepted: the fiche
  is per-word by construction, the صرفي card already shows the segment breakdown (بادئة/جذع), and
  the alternative is a per-segment نحوي card, which is a different change.
- **The mapper inherits every QAC error.** 1 006 case conflicts are QAC contradicting itself. → They
  are omitted rather than propagated, and the log makes them countable instead of invisible.
- **87.6 % verified coverage will look like a regression to a reader who expects 100 %.** → The
  نحوي level itself is unchanged and still available for those words; only the *Zero rows* are
  absent. A word keeps its الموقع الإعرابي and المتعلَّق whether or not its relation derives.
- **The demo sentence from the source deck is not Quranic.** «يَعْبُدُ الإنسانُ العاقلُ خالِقَ
  الكَوْنِ» cannot be fetched through the API. → It is tested as a unit test over synthetic
  QAC-shaped records, and paired with a Quranic verse exercising the same four relations so the
  live path is covered too.

## Migration Plan

No data migration, no re-ingest, no index rebuild. The change is additive at every layer:
ship the mapper + model fields (backend renders nothing new until the frontend reads them), then
the three card rows. Rollback is deleting the three rows from the نحوي card; the API fields are
optional and inert if unread.

## Open Questions

Resolved before freezing (recorded here so the decisions are not silently reopened):

- **السبب rendering** → one line, in the two forms of Decision 6. العلامة is not recadrée and stays
  in the صرفي card.
- **عطف/استئناف** → the 754 standalone CONJ words get a minted, visibly non-محقّق marker row;
  fused و/ف prefixes get nothing (Decision 8).
- **LLM threshold** → no LLM tier in this change; decide on the triaged log (Decision 7).

Still open, deliberately deferred:

- Whether the 1 083 ambiguous edges (case conflicts + prepositions in nominal slots) deserve a
  flagged «قراءة مرجَّحة» reading, and from which provider. Needs the log triaged first.
- Whether the `no-case` bucket (798 words: ظروف and pronouns whose relation fixes no case) can be
  narrowed by reading the head's case instead of the word's own. Cheap to try, but it is a second
  inference step and belongs after the first layer is in users' hands.
