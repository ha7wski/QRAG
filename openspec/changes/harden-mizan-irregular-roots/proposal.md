## Why

`analysis/mizan.py::compute_mizan` derives the الميزان الصرفي by walking the vocalized stem and
matching each surface letter, in order, against the next unconsumed root radical. That is exact
only for **sound** roots whose radicals surface unchanged. It breaks structurally whenever a
radical mutates or disappears (إعلال/إبدال) or the word follows a broken-plural template — and
those two classes are not a long tail. Measured over the whole corpus today (49 967 rooted words
with a mīzān):

| root class | words | flagged اجتهادي | rate | share of all اجتهادي |
|---|---:|---:|---:|---:|
| صحيح سالم | 20 896 | 11 | 0.1 % | 0.1 % |
| أجوف | 9 719 | 5 504 | 56.6 % | 37.2 % |
| مضاعف | 4 055 | 4 055 | 100 % | 27.4 % |
| ناقص | 5 118 | 2 739 | 53.5 % | 18.5 % |
| لفيف | 2 070 | 1 186 | 57.3 % | 8.0 % |
| مهموز (otherwise sound) | 6 759 | 1 006 | 14.9 % | 6.8 % |
| مثال | 1 254 | 308 | 24.6 % | 2.1 % |
| رباعي | 96 | 6 | 6.2 % | 0.0 % |
| **total** | **49 967** | **14 815** | **29.6 %** | |

Rows are the single weak-letter class under the precedence لفيف → مضاعف → أجوف → ناقص → مثال →
صحيح سالم; the مهموز row therefore counts hamzated roots that are *otherwise* sound, since
hamzated-and-weak roots (آلاء = `الو`) already sit in their weak class.

Nearly **three words in ten** are pushed out of the «معطى محقّق» badge and rendered as an
اجتهادي guess — and the guess is usually wrong, not merely unverified: قَالَ → «فَال» (the ع slot
vanished), آلَاء → «فعَاء», دُعَاء → «فُعَاء», مُؤْمِنِين → «مُؤْمِنِين» (root امن, *zero* radicals
matched, because `_fold` folds أ/إ/آ/ٱ but not ؤ/ئ). The سالم baseline being already at 99.9 %
shows the failure is entirely concentrated in irregular roots and templates, so this is fixable
without touching what already works.

## What Changes

Two layers are inserted **ahead of** the existing raw projection, which is demoted to a last
resort. Everything stays deterministic, on-the-fly, LLM-free, and verbatim-from-QAC/chakl.

- **Root classification** — a pure function over the QAC root letters yields exactly one weak-letter
  class (صحيح سالم / مضاعف / مثال / أجوف / ناقص / لفيف, plus رباعي for 4-letter roots) **plus an
  orthogonal hamza attribute**. حرف علة is و/ي only — hamza is not one — so مهموز cannot be a rival
  label: a root is frequently both (آلاء = root `الو` = مهموز الفاء **and** ناقص واوي; true لفيف
  needs two real و/ي radicals, as in وقي/وحي). Since the class is a user-visible result field, it
  is two fields rather than one contestable label. The weak class alone gates every إعلال rule
  below; hamza needs no rule (the `_fold` fix covers it).
- **إعلال/إبدال-tolerant radical matcher** — the radical↔surface comparison is generalized,
  *conditioned on the root class*, to accept إعلال بالقلب (a و/ي radical may match a surface
  ا/ى/ء), إعلال بالحذف (a weak radical may be absent and be consumed with no output letter), and
  known إبدال (assimilated تاء الافتعال, hamzat waṣl). Each acceptance records which rule fired.
- **`_fold` hamza-carrier gap closed** — ؤ and ئ join أ/إ/آ/ٱ in folding to ا, so مهموز roots
  stored hamza-folded by QAC (امن, اله, ألو…) match their surface carriers. This alone is
  ~1 000 words.
- **Curated awzān / جموع التكسير pattern library** — a versioned, documented data file of
  templates (ف/ع/ل slots + fixed letters and vowels) each emitting a canonical mīzān. On a match
  the pattern's mīzān is emitted directly (آلاء → «أَفْعَال»), because a broken plural is a
  template, not a projection. Seeded and prioritized by what the corpus actually contains.
  Singular-vs-plural ambiguity (فِعَال is both كِتَاب and رِجَال) is resolved by **gating pattern
  family selection on QAC's `number` feature**, which the record already carries — `number == "P"`
  prefers the plural schemes. (Gate on `"P"`, never `"S"`: singulars carry *no* `number` at all —
  كِتَابٌ is `None`, not `"S"`.)
- **`verified` semantics tightened** — `True` when a pattern matched *or* the projection resolved
  every radical (possibly via a recorded rule); `False` **only** when no pattern matched *and*
  radicals remain unresolved. Every residual `False` is logged (ref, root, class, stem) so the
  remaining gap is enumerable rather than invisible.
- **مضاعف resolves to verified — settled, not left open.** The geminate special-case
  (`radicals[-1] == radicals[-2] → False`) is deleted and replaced by a shadda-fusion rule. A
  geminate's mīzān is deterministic, not a conjecture (مَدَّ = فَعَلَ in origin, أصله مَدَدَ;
  فَعَّ after إدغام), so اجتهادي was never the right label for it. The emitted `wazn` is the
  fused, surface-faithful **فَعَّ** — the only form that composes with the rest of the word
  (رَبِّهِمْ → فَعِّهِمْ) — with the أصل فَعَلَ carried in the rule trace. This is the single
  largest win in the change (**4 055 words, 27 % of all اجتهادي**) *and* the lowest-risk one: the
  emitted string is already what the code produces today, so only the flag changes.
- **Gold set + before/after measurement** — a curated ~30–50-word fixture pinning
  `(mīzān, verified, class)` across regular / إعلال / broken-plural / مضاعف cases, plus a script
  reporting the اجتهادي rate corpus-wide. Current outputs to beat:

  | word | ref | root | class | today | target |
  |---|---|---|---|---|---|
  | آلَاء | 7:69:24 | الو | ناقص (+hamzated فاء) | `فعَاء` ✗ | `أَفْعَال` ✓ |
  | دُعَاء | 2:171:11 | دعو | ناقص | `فُعَاء` ✗ | `فُعَال` ✓ |
  | قَالَ | 2:30:2 | قول | أجوف | `فَال` ✗ | `فَعَلَ` ✓ (قلب traced) |
  | يَدْعُ | 23:117:2 | دعو | ناقص | `يَفْع` ✗ | لام consumed empty ✓ |
  | يَعِدُ | 35:40:28 | وعد | مثال | `يَعِد` ✗ | فاء consumed empty ✓ |
  | يُوحَ | 6:93:13 | وحي | لفيف | `يُفع` ✗ | لام consumed empty ✓ |
  | مُتَّقِين | 2:2:7 | وقي | لفيف | `مُتَّقِين` ✗ (0 radicals) | إبدال تاء الافتعال ✓ |
  | مَدَّ | 13:3:3 | مدد | مضاعف | `فَعّ` **✓ but اجتهادي** | `فَعَّ` `verified=True` |
  | رِجَال | 7:46:5 | رجل | صحيح سالم | `فِعَال` ✓ (`number=P`) | unchanged (plural gate) |
  | رَحِيم / كِتَاب / رُسُل / مَسَاجِد | — | — | — | `فَعِيل` `فِعَال` `فُعُل` `مَفَاعِل` ✓ | unchanged (regression guard) |

  The مثال and لفيف rows are new: without them the final per-class acceptance check would
  declare victory on classes no test covers.

- **Non-goals:** no exhaustive model of Arabic صرف (curate what the corpus exercises, log the
  rest), no precomputed mīzān store, no change to the QAC source data, the API response shape,
  the alignment spine, or the frontend badge UI.

## Primary risk

**An honest اجتهادي beats a wrong mīzān badged محقّق.** This change moves words *into* the
verified badge, which inverts the dominant failure mode. Today a bad derivation is *labelled*
bad — the اجتهادي tag warns the reader. Afterwards, a mis-entered pattern yields a confidently
wrong mīzān under «معطى محقّق» with nothing on screen to signal it. That outranks the regression
risk: a regression breaks a word that *was* right and is caught loudly by gold tests, whereas
this silently corrupts a word that was already flagged — and no aggregate metric can see it,
because "اجتهادي rate fell" is exactly what a wrong-but-confident pattern also produces.

Consequences, binding on implementation: **every pattern added to the table ships with at least
one gold assertion** (no test, no pattern); after each pattern batch, a sample of newly-flipped
words is inspected **per pattern**, not a handful overall; and when a scheme is doubtful it is
left out — the word stays honestly اجتهادي and surfaces in the coverage log for a later,
better-evidenced entry. Full ranking in `design.md` → Risks.

## Capabilities

### New Capabilities

None. This hardens an existing derivation inside an already-specified capability.

### Modified Capabilities

- `qlisan-word-analysis`: adds requirements for the layered (classify → pattern → project)
  mīzān derivation, root-class exposure, class-gated إعلال/إبدال-tolerant matching with rule
  traceability, the redefined verified/اجتهادي semantics plus coverage logging, the versioned
  awzān data file, and the no-regression + measurable-improvement guarantee. The existing
  requirement *"The verified badge covers only verbatim fields"* is unchanged in intent — the
  badge still covers only non-fabricated data; this change makes the mīzān *earn* it on far more
  words rather than widening what the badge means.

## Impact

- **Code:** `analysis/mizan.py` (`_fold`, the projection block in `compute_mizan`; new classifier,
  matcher, and pattern-matching layer). New versioned data file for the awzān table under
  `data/` with in-file provenance.
- **Result shape:** `compute_mizan` gains additive fields (root class, hamza attribute,
  applied-rule trace). `api/models/qlisan.py::Mizan` grows optional fields; `available` / `wazn` /
  `verified` / `bab` keep their meaning, so the frontend (`frontend/src/app/qlisan/page.tsx`,
  which renders the اجتهادي tag off `verified`) needs no change — it simply shows the tag far
  less often.
- **Reads one more QAC field:** `features.number` (already present in the record) for the
  singular/plural pattern gate. No new data source.
- **Tests (local-only):** `tests/test_mizan.py` extended; two current expectations invert by
  design — `test_hollow_verb_is_flagged_heuristic` (قِيلَ, resolved by the أجوف قلب rule) and
  `test_geminate_root_is_flagged_heuristic` (وَيَمُدُّهُمْ, now `verified=True` per the مضاعف
  decision) both assert `verified is False` and must be rewritten. New gold-set fixture +
  measurement script.
- **No impact:** ingestion pipeline, indexes, retrieval, generation, other API routes, DB.
- **Dependencies:** none added — pure stdlib, same corpus artifacts.
