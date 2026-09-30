## Context

`/lexical` shows, for a trilateral root, each radical's Islambouli row verbatim. The rows come from
the frozen `islambouli_letters.csv` (v1.0.0, sha256 `319c73f4…`) and are joined in
`api/routers/lisan.py::_with_islambouli`. `linguistics/lisan/islambouli/compose.py` already maps a
root to three positions (opens / body / concludes) with each row's text verbatim. It is not mounted.
It is guarded by the second holdout's `witness_guard`.

Islambouli published two physical stages. Both were supplied by the user as video screenshots from
the programme «مفاهيم»:

| root | as printed | on-screen label |
|---|---|---|
| ضرب | «تدل على دفع شديد مكرر منتهٍ بجمع مستقر» | الحالة الفيزيائية |
| كتب | «كلمة تدل على ضغط ودفع منتهٍ بجمع مستقر» | ( مفهوم ) |

The ضرب screenshot also prints a cultural stage, «تدل على إيقاع شيء على شيء يترك فيه أثراً». The
كتب screenshot labels its sentence «مفهوم» and not «الحالة الفيزيائية». Filing it as a physical
stage is **our** classification, made because its content is an assembly of the three rows. The
label as printed is kept in the record.

Neither ضرب nor كتب is in `concept_witness_set.json` or `islambouli_witness_set.json` (checked),
so the guard lets a test assemble them.

## Goals / Non-Goals

**Goals:** assemble the physical stage mechanically, with a label saying so. Handle «أو» with no
silent choice. Show a cultural stage only when it is sourced. Pin the template's exact output on the
two published roots, and state the gap to what Islambouli published.

**Non-Goals:**
- Generating or inferring the cultural stage.
- Closing the gap to Islambouli's sentences with rules.
- Any change to the letter table, either holdout, either `k / 40`, or the closed engine.
- Quadriliteral roots.
- Building the LLM re-wording (see §D6).

## Decisions

### D1. The acceptance test, run by hand before any code, and it does not pass

**Conclusion, first: Islambouli's physical stage is NOT a mechanical assembly.** It carries
per-root editorial decisions: which words of each row count, and how the rows are joined. That is a
**third place of interpretation**, after the table itself and after the choice between alternatives.
The brief's premise, that the stage is «an assembly, not an interpretation», was generalised from
ضرب alone, and كتب breaks it.

This changes nothing in the construction and everything in the presentation. The template stays as
it is. What it produces is **the project's mechanical junction** of the three rows. It cannot be
presented as what Islambouli would write, and its label says so (§D9).

Every input is a frozen row, so the template's output is fully determined now. Derived with the
rules D2–D4, and not adjusted afterwards:

| root | template output | Islambouli |
|---|---|---|
| ضرب | «دفع شديد جداً، متوقف مكرر منتهٍ بجمع مستقر» | «دفع شديد مكرر منتهٍ بجمع مستقر» |
| كتب (both alternatives, default) | «(وقف، أو ضغط خفيف) دفع خفيف متوقف منتهٍ بجمع مستقر» | «ضغط ودفع منتهٍ بجمع مستقر» |
| كتب (explicit choice ضغط) | «ضغط خفيف دفع خفيف متوقف منتهٍ بجمع مستقر» | «ضغط ودفع منتهٍ بجمع مستقر» |

**Exact gaps:**
- **ضرب**: one gap. The template keeps «جداً، متوقف» from row ض, and Islambouli drops it. Positions
  2 and 3, the qualifier transform (تكرار → مكرر) and the connector «منتهٍ بـ» match word for word.
- **كتب**: four gaps.
  - (a) He selects ضغط from «وقف، أو ضغط خفيف». Only the explicit-choice mode reaches that.
  - (b) He drops «خفيف» after ضغط.
  - (c) He attaches position 2 with «و», which is coordination and not qualification.
  - (d) He drops «خفيف متوقف» from row ت.
  
  Position 3 and «منتهٍ بـ» match.

**What the gaps say.** His two examples do not follow one schema:
- Position 2 is a qualifier in ضرب and a coordinated noun in كتب.
- Position 1 keeps «دفع شديد» from ض (head plus first modifier) but only «ضغط» from ك (head alone).

Every gap is a word he **left out** or a connector he **chose**. Reproducing either means deciding,
root by root, which parts of a row matter, and that is the same act as choosing an alternative. The
template therefore stays as it is, and the acceptance test pins the template's output (column 2).
His sentences (column 3) are cited data (§D7), and the diff above is pinned, so the gap stays visible
and cannot be narrowed without a failing test. The page also shows it (§D9): **the gap IS the
result**.

One pattern is noted and **not adopted**: in ضرب the position-2 head has a وصف entry and is a
qualifier; in كتب it has none (دفع) and is coordinated. «No entry → join with و» would reproduce
gap (c). It rests on exactly one case, the case it was read from, and it closes neither (a), (b)
nor (d). **Refused** (review, 2026-09-28).

**Usability (brief §4).** The outputs are dense juxtapositions but they are readable Arabic
phrases, and every word is Islambouli's except the connector. They are not "really unusable", so
this change does not reach for an LLM.

### D2. What a row contributes: the meaning segment, verbatim

Every row but ء reads «صوت يدل على X.». The frame «صوت … يدل على» and the final full stop belong to
the poster's formula, not to the meaning, so the **segment** is the text after «يدل على» up to the
first sentence-ending «.», trimmed. Internal commas are kept («دفع شديد جداً، متوقف»).

Row ء reads «صوت خفيف يدل على ظهور متوقف. وهو جزء من صوت (آ)». Its segment is «ظهور متوقف». The
second sentence is the hamza relation, which the letter-table spec already keeps as text only. **Decided:** «خفيف» is dropped. The formula is «a sound X indicates Y», and خفيف qualifies the sound,
not what it indicates. ء is the **only** row whose formula varies. This is recorded as a segment note
(below).

**Segment notes** are the assembly layer's equivalent of the transcription's `reading_note`. They
live in `islambouli_wasf.lock.json` under `segment_notes`, and **not** in `islambouli_letters.csv`:
that file's digest (`319c73f4…`) is cited by `islambouli_attestation.json` and the grid, and adding a
note would change it and break the reproduction of k / 40. Three notes are recorded, and none
creates a rule:
- **ء**: the only varying formula; «خفيف» is dropped as describing the sound.
- **ع**: «عمق أو بُعد في الشيء». «في الشيء» probably covers both alternatives, but the mechanical
  split gives it to «بُعد» only. Deciding would take a scope rule written for one row.
- **ض**: «دفع شديد جداً، متوقف». The internal comma is kept verbatim; the segment is not cleaned.

The segment is computed from the frozen row at load time and is never stored, so no second copy of
Islambouli's text can drift away from the lock.

### D3. Template

```
<seg(pos1)> <wasf(seg(pos2))> منتهٍ ب<seg(pos3)>
```

- The **only** added material is the fixed string «منتهٍ ب» (ب attached to position 3's first
  word), single spaces, and the alternative brackets of D5. It is one constant, tested.
- `wasf()` replaces the **first word of each alternative** of position 2 through the table in D4.
  The rest of the segment follows unchanged. A word with no entry stays as written.
- No word is ever dropped, reordered or added beyond the connector. There are no per-root cases, no
  per-letter cases and no punctuation clean-up.
- Refusals are inherited from `compose()`: a non-trilateral root or a silent position gives **no
  assembly**, with the reason. A partial sentence is never assembled.

The assembly lives in `linguistics/lisan/islambouli/assemble.py` and calls `compose()`, so the
second holdout's witness guard stands in front of it unchanged.

### D4. The مصدر → وصف table: closed, justified by one morphological criterion

**Criterion, stated before choosing any entry:** a word gets an entry only if it is the مصدر of a
derived (مزيد) form whose اسم الفاعل and اسم المفعول have **one unvocalized spelling**. Unvocalized,
the table then never chooses between active and passive: مكرِّر and مكرَّر are both «مكرر». Form I
مصادر always need that choice (دافع / مدفوع), so they never get an entry.

Candidates are only the first words of the 29 rows' alternatives. They were enumerated from the
table, not from roots:

| مصدر | form | وصف | verdict |
|---|---|---|---|
| تكرار | تفعال of كرّر (II) | مكرر | entry |
| تأرجح | تفعلل (II q.) | متأرجح | entry |
| انتشار | افتعال (VIII) | منتشر | entry |
| امتداد | افتعال (VIII, doubled) | ممتد | entry |
| اختباء | افتعال (VIII, hamzated) | مختبئ / مختبأ | no: the hamza seat differs |
| تفشٍّ | تفعّل (V, defective) | متفشٍّ / متفشّى | no: the spellings differ |
| إثارة | إفعال (IV, hollow) | مثير / مثار | no: the spellings differ |
| دفع جمع ضغط وقف قطع … | form I | — | no |

The table has four entries. It lives in `data/references/islambouli_wasf.csv` (`masdar, wasf, form,
justification`), is frozen by `islambouli_wasf.lock.json` (version, sha256, history), and is
verified at load time like the letter table. Its lock rule is that an entry changes only when its
morphological justification is shown to be wrong, never because a root reads better. Its hard
ceiling is 20 entries.

### D5. «أو»: both alternatives by default, and a choice only when signed

Eight rows carry «أو»: ج ح خ ع غ ق ك ن. An **alternative group** is a segment split at «أو» (with
its optional preceding «،»). The split is mechanical: ع gives «عمق» / «بُعد في الشيء» — the ambiguity is recorded as a segment note (§D2), not resolved.

- **Default (mode A):** the group is rendered whole, verbatim, inside «( )»: «(وقف، أو ضغط خفيف)».
  The brackets show the scope of the alternative inside the juxtaposition, and they are the only
  mark besides the connector that the template adds.
- **Explicit choice (mode B):** a choice exists only as part of a **signed personal reading** (D8)
  that names the position and the alternative index. The assembly then renders that alternative and
  marks it on screen as «اختيار: <author> — تأويل، لا من الجدول». No request field, default,
  environment variable or score can supply a choice. `assemble(root)` with no reading always renders
  mode A.
- **Tests that prove no automatic path selects:**
  1. A property test over all 28 × 3 (letter, position) assemblies with no reading: every
     alternative of every group appears in the output.
  2. A static test: in `assemble.py` and `api/routers/lisan.py`, a choice argument can only come
     from a stored reading object, and `assemble.py` imports no `llm_client`, no `random` and no
     scoring module.
  3. An API test: a request body that carries a choice is rejected or ignored, and the output still
     contains both alternatives.

### D6. LLM re-wording: not built, and a BLOCKING condition on any future one

D1 finds the output usable, so no LLM path is built. This is recorded here because the existing
veto is **not enough** for this use.

`concept/phrasing.py::contained` accepts any sentence whose content words are a **subset** of the
allowed words. Omission therefore passes. A model given «(وقف، أو ضغط خفيف) …» could return
«ضغط ودفع منتهٍ بجمع مستقر»: every word is contained, and that one omission has silently chosen ضغط
over وقف, exactly what D5 forbids.

**Blocking condition.** No re-wording may be built unless the preservation check below exists
beside containment. Containment alone accepts omission, and omission is selection. Any future
re-wording needs two checks:
- containment;
- **preservation**: every alternative of every group still present, and every row's head word
  still present.

It would also have to extract `contained` into `linguistics/lisan/harness/`, because nothing in
`lisan/` may import the closed engine. The flag would be off by default and the template shown on
rejection. None of this is in this change.

### D7. Cultural stage: citation, else signed personal reading, else nothing

- **Citation**: `data/references/islambouli_citations.json` holds one entry per published
  statement:
  - `root`, `stage` (`physical` | `cultural`), `label_as_printed`, `text_as_printed`, `text`;
  - `source`: programme «مفاهيم», witness image under `data/source/`, its sha256, its `origin`
    (episode references are not available: "supplied by the user, origin unrecorded", as for the poster, until the user supplies them).
  
  The file is frozen by a lock. Today it has three entries: ضرب physical, ضرب cultural and كتب
  physical. Its `development_cases: ["ضرب", "كتب"]` list is asserted to be disjoint from both
  witness sets and from any future draw's frame.
- **Personal reading**: see D8. It is displayed as «قراءة شخصية — <author>».
- Where both exist, both are shown, each labelled. Where neither exists, **the section is not
  rendered**: no heading, no placeholder and no «قيد الإعداد». A Vitest test asserts the DOM has no
  cultural section for a root with neither.

### D8. Personal readings: runtime state, signed

A new `lisan_readings` table in `data/runtime/app.db`, through `api/store.py`, with the columns
`root`, `author` (non-empty, required), `cultural_text` (optional), `choices` (JSON of
`{position: alternative_index}`, optional) and `updated_at`.

- Routes: `GET /lisan/reading/{root}` and `PUT /lisan/reading/{root}`. The latter rejects an empty
  author, an index out of range and a position without an alternative group.
- The author's name is typed in the UI and remembered in `localStorage` for convenience only. The
  server keeps it as written.
- The two routes are added to `test_served_surface.py`'s served list. `/lexical` calls both.
- A personal reading is **user content**. It is never shown as Islambouli's, never fed to any
  measurement, and never committed: `data/runtime/` is git-ignored.

### D9. API and screen

`POST /lisan/analyze` gains two fields, joined in `api/routers/lisan.py` beside `_with_islambouli`:
- `islambouli_assembly`: `{sentence, positions[], groups[], choice: {author, ...} | null, refused,
  reason}`.
- `cultural_stage`: `{citations[], personal: {...} | null}`.

The engine is untouched. On `TableNotFrozen` or a wasf-lock mismatch, both fields are absent and the
page falls back to what it shows today.

Screen order:
1. The root.
2. The letter cards, with the three rows verbatim (existing).
3. **Islambouli's own physical sentence, when cited**: verbatim, under its label **as printed**
   («الحالة الفيزيائية» for ضرب, «مفهوم» for كتب). Labels are not unified. Filing كتب's sentence as a
   physical stage remains our classification (Context).
4. The **assembled sentence**, labelled «تركيبٌ آليٌّ للأسطر الثلاثة، من صنع هذا التطبيق — لا تعريفٌ،
   ولا قولُ إسلامبولي». The alternative groups are visibly bracketed, and each group has a control to
   record a signed choice.
5. **For a root with both**: the gap, named word by word (the words his sentence has that the
   assembly lacks, and the reverse). It is computed from the two texts, not stored.
6. The **cultural stage**, only when sourced.
7. المواضع.
8. الصرف والإعراب.

## Risks / Trade-offs

- **The sentence reads worse than Islambouli's, and permanently.** Closing the gap is the thing D1
  forbids. The mitigation is the label, plus the visible bracket and the pinned diff fixture.
- **The segment rule (D2) is itself a reading of the poster.** → It is one rule for all 29 rows,
  stated before assembling any root besides the two development cases. Row ء's exception is flagged
  (Open Question 1).
- **A signed choice can make the page look like Islambouli chose.** → The label names the author and
  says «تأويل». The assembly without a reading is always mode A.
- **The citations rest on screenshots of unknown origin.** → The origin is recorded as unrecorded
  unless the user gives the episode reference. The images are deposited and hashed.
- **Scope**: new routes and a store table. → The alternative is a curated JSON under
  `data/references/`, which would publish personal readings in the repo (Open Question 4).

## Review decisions (2026-09-28)

1. Row ء: «خفيف» is dropped (§D2).
2. Row ع: the mechanical split stays; the ambiguity is a segment note (§D2).
3. Label: «تركيبٌ آليٌّ للأسطر الثلاثة، من صنع هذا التطبيق — لا تعريفٌ، ولا قولُ إسلامبولي».
4. Personal readings: `app.db`, runtime.
5. Islambouli's own sentence is shown beside the assembly, with its printed label and the named gap
   (§D9). This supersedes the brief's screen.
6. Origin: unrecorded, until the user supplies it.
