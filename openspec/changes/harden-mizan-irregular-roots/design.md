## Context

`analysis/mizan.py::compute_mizan` derives the صرفي mīzān by walking the vocalized stem
(after `_strip_proclitics`) and, for each surface letter, matching it in order against the
next unconsumed root radical via `_fold`; a matched radical is replaced by the corresponding
ف/ع/ل target and non-radicals are copied verbatim. `verified` is `matched == len(radicals)
and ptr == len(radicals)`, forced `False` for geminated (مضاعف) roots.

This is exact only for **sound** roots whose radicals appear unchanged and contiguous in the
stem. It fails structurally for two large, overlapping classes:

- **إعلال/إبدال** — a weak/hamzated radical mutates (و/ي → ا/ى/ء) or is deleted on the
  surface, so the in-order `_fold` match breaks and later radicals never align.
- **جموع التكسير** — a broken plural is not a linear projection of the root at all
  (آلاء ≠ فَعَاء); its mīzān is a *named pattern* (أَفْعَال), so no letter-walk recovers it.

Both currently strand radicals → false `verified=False` → false اجتهادي on exactly the words
a lisānī fiche must render authoritatively. The whole module is pure-stdlib, deterministic,
on-the-fly, LLM-free — a hard constraint we keep.

**Measured baseline** (corpus-wide, 49 967 rooted words with a mīzān): **14 815 اجتهادي =
29.6 %**. It is concentrated exactly where the two failure modes live — أجوف 56.6 % (5 504
words), مضاعف 100 % (4 055, forced by the existing special-case), ناقص 53.5 % (2 739), لفيف
57.3 % (1 186), مهموز 14.9 % (1 006), مثال 24.6 % (308) — while **صحيح سالم is already 99.9 %
verified (11 misses / 20 896)** and رباعي 93.8 %. Two consequences shape the design: the
upside is large and bounded to irregular classes, and the regression surface is tiny and
easy to guard.

The failures are also *wrong values*, not merely unflagged ones: قَالَ → «فَال» (ع slot lost),
دُعَاء → «فُعَاء», آلَاء → «فعَاء», مَدَّ → «فَعّ», يَدْعُ → «يَفْع».

## Goals / Non-Goals

**Goals:**

- Reduce false اجتهادي on irregular roots and broken plurals, measurably, on a Qurʾān sample.
- Keep every regular word that is correct today correct (zero regression).
- Stay 100% deterministic, on-the-fly, verbatim-from-QAC/chakl; no store, no LLM, no network.
- Make every non-trivial resolution *traceable* (which pattern / which إعلال rule fired) and
  make every remaining اجتهادي word *loggable* for coverage measurement.

**Non-Goals:**

- Full coverage of Arabic إعلال/تكسير theory. We curate the patterns/rules the corpus
  actually exercises and log the rest, rather than modelling صرف exhaustively.
- Changing the نحوي/صوتي/دلالي levels, the QAC source data, the alignment spine, the API
  response shape, or the frontend/badge UI (same `verified` flag, computed more accurately).
- A precomputed mīzān store — derivation stays at assembler time.

## Decisions

### D1 — Three ordered layers ahead of the legacy projection; projection becomes last resort

`compute_mizan` runs: **[1] classify root → [2] pattern-match (tolerant matcher) → emit
canonical mīzān on hit → [3] else raw projection (existing code, tolerant-matcher-aware)**.
Ordering matters: broken plurals must be caught by the pattern library *before* the
letter-walk strands them. The existing projection block is preserved as the fallback so
sound roots with no matching pattern behave exactly as today.

*Alternative considered:* fix only the matcher (make `_fold` weak-aware) without a pattern
library. Rejected — a tolerant matcher recovers إعلال cases (قَالَ) but cannot produce
أَفْعَال for آلاء, because a broken plural is a template, not a projection. Both layers are
needed and they compose (2b uses 2a to fill radical slots).

### D2 — Root classification: one weak-letter class + an orthogonal hamza attribute

Derive from the 3–4 root letters: مضاعف (radical₂ = radical₃), مثال (radical₁ ∈ و/ي), أجوف
(radical₂ ∈ و/ي), ناقص (radical₃ ∈ و/ي), لفيف (**two** radicals ∈ و/ي), else صحيح سالم — plus
رباعي for 4-letter roots. The class is returned in the result dict and is the **gate** for every
إعلال rule (D3), which is what prevents over-generalization onto sound roots.

**حرف علة is و/ي only — hamza is not one.** This is the decisive definition, and it fixes a
mislabel: آلاء (QAC root `الو`) is **ناقص** (third radical و), *not* لفيف. The alif at position 1
is a hamza that QAC folded onto alif (D3b) — so آلاء is classically مهموز الفاء **and** ناقص
واوي. True لفيف requires two actual و/ي radicals: وقي, ولي, وحي, وفي, وصي.

**مهموز is therefore an orthogonal attribute, not a rival class.** A root can be both hamzated
and weak (الو, رأى), so forcing one label would have to discard information. We expose two
fields: `class` (the single weak-letter class above) and a hamza attribute (the radical positions
QAC stores as alif). Only `class` gates the D3 إعلال rules — hamza needs no rule, because D3b
handles it in `_fold`.

**Precedence, pinned:** لفيف → مضاعف → أجوف → ناقص → مثال → صحيح سالم, evaluated in that order,
with the hamza attribute computed independently. This is exactly the precedence the measured
baseline uses, so the class table in `proposal.md` stays valid under it. Note the consequence:
the baseline's «مهموز 6 759 / 1 006» row means *مهموز whose root is otherwise sound* — hamzated
weak roots are already counted inside أجوف/ناقص/لفيف.

*Alternative considered:* infer class from surface behaviour. Rejected — the root letters are
verbatim ground truth from QAC; classifying from them is unambiguous and testable.

*Alternative considered:* keep مهموز as a seventh mutually-exclusive class (tested last, as the
baseline script did). Rejected once the class became a **user-visible result field**: it would
label آلاء ناقص while silently dropping the fact that its فاء is hamzated, and would label رأى
ناقص with no hint of the hamza that explains its surface. An exposed label must be defensible.

### D3 — إعلال/إبدال rules extend the matcher, each gated on the root class

Generalize the radical↔surface comparison (today: `_fold(letter) == _fold(radical)`) into a
class-conditioned predicate that also accepts:

- **إعلال بالقلب** — for أجوف/ناقص/مثال/لفيف: a و/ي radical matches surface ا, ى, or ء.
- **إعلال بالحذف** — for ناقص/مثال (jussive/imperative/مضارع contexts): a weak radical may be
  consumed with **no output letter** when it is absent on the surface (يَدْعُ, قُلْ).
- **إبدال** — assimilated تاء الافتعال (اصطبر/ازدجر) and hamzat waṣl handled as fixed-letter
  reconciliations.

Each acceptance path is tagged with the rule name; a resolution via any path keeps
`verified=True`. Rules are *only* reachable for the classes that license them, so a صحيح سالم
root can never trigger a قلب/حذف substitution (the D2 guardrail).

*Alternative considered:* one permissive "fuzzy" matcher for all roots. Rejected — it would
rewrite regular words and destroy the regression guarantee. Class-gating is the safety.

### D3b — `_fold` closes the ؤ/ئ hamza-carrier gap (prerequisite, not an إعلال rule)

`_fold` folds أ/إ/آ/ٱ → ا but **not** ؤ/ئ, while QAC stores roots hamza-folded onto alif. So
مُؤْمِنِين (root امن) matches *zero* radicals and emits itself verbatim; يُؤْلُونَ (root الو)
likewise. Adding ؤ/ئ → ا to `_fold` is a plain normalization fix — it belongs to the same
"fold surface variants onto the stored root form" contract already documented in `_fold`, is
independent of root class, and is safe because no non-hamzated root contains an alif radical
that a ؤ/ئ could spuriously bind. Worth ~1 000 words on its own; land it first so the إعلال
rules are measured on top of a correct fold rather than compensating for it.

*Note:* this is deliberately **not** modelled as إعلال بالقلب — a hamza written on a wāw/yāʾ
seat is the same hamza, an orthographic carrier choice, not a mutated radical. Keeping it in
`_fold` avoids inflating the traced-rule set with a spelling detail.

### D4 — Pattern library is a versioned data file of ف/ع/ل templates → canonical mīzān

Each entry is a template of slots (ف/ع/ل, with a 4th ل for rubāʿī) plus fixed
letters/vowels and the canonical mīzān string it emits. Matching aligns the stem against a
candidate, binding radical slots via the D3 matcher and requiring the fixed
letters/vowels to match; the first hit emits its mīzān with `verified=True`. Seed set
(prioritized to corpus frequency): singulars فَعِيل/فَعُول/فَاعِل/مَفْعُول/فَعَّال/مِفْعال/
فُعْلة…; plurals أَفْعَال/أَفْعُل/فُعُول/فِعَال/فُعَل/فِعَل/مَفَاعِل/فَوَاعِل/أَفْعِلَة/
فُعَلَاء/أَفْعِلَاء…. The file carries an in-file provenance note citing the صرف source per
scheme. Data, not inlined constants, so the table is reviewable and extensible without code
churn (spec: "pattern table is data").

*Alternative considered:* hard-code patterns in `mizan.py`. Rejected — the proposal/spec
require a versioned, documented, corpus-prioritized data source; separating data from logic
also keeps the coverage-growth loop (add pattern → rerun measurement) cheap.

**Family selection is gated on the QAC `number` feature.** Several templates are ambiguous
between a singular and a broken plural — فِعَال is كِتَاب (singular) *and* رِجَال (plural);
مَفَاعِل, أَفْعَال, فُعُول are plural-only in practice. QAC already carries the answer in the
record, so the pattern table tags each entry with the family it belongs to and matching consults
`features.number`: **`number == "P"` → try plural templates first; otherwise → singular
templates first.** The other family stays reachable as a fallback (the tag orders candidates, it
does not hard-filter), so a mis-tagged record degrades to today's behaviour instead of failing.

**Gotcha, verified in the corpus:** singular nouns are marked by the *absence* of `number`, not
by `"S"` — `كِتَابٌ` (2:89:3) has `number=None`, while `رِجَالٌ` (7:46:5) and `مَسَاجِدَ`
(2:114:5) both carry `number="P"`. A `number == "S"` test would silently route every singular
into the plural branch. Gate on `== "P"`, never on `== "S"`.

### D5 — `verified` redefined; every اجتهادي fallback is logged

`verified = pattern_matched OR projection_fully_resolved` (resolution may go through a D3
rule). `verified=False` ⇔ no pattern AND unresolved radicals remain — and that word is written
to a coverage log (ref, root, class, stem) so the residual اجتهادي set is enumerable and the
before/after rate is measurable.

**The مضاعف "force False" special-case is deleted. مضاعف resolves to `verified=True`.** Settled,
not open: the mīzān of a geminate is *deterministic*, not a conjecture — مَدَّ is فَعَلَ in origin
(أصله مَدَدَ) and فَعَّ after إدغام. Nothing is being guessed, so flagging 4 055 words (27 % of all
اجتهادي) as اجتهادي was never right. A shadda-fusion rule consumes radical₂ and radical₃ against
the single geminated surface letter, records the rule, and keeps `verified=True`.

**The emitted `wazn` is the fused, surface-faithful form فَعَّ**, with the pre-إدغام أصل فَعَلَ
carried in the rule trace (and available to the UI as an إدغام note). Reasoning: the whole module
copies the surface's vocalization verbatim, and the fused form is the only one that *composes*
with the rest of the word. The corpus makes this concrete — رَبِّهِمْ (2:5:5) and رَبَّكُمُ
(2:21:4) yield فَعِّهِمْ and فَعَّكُمُ, which stay coherent word-forms; emitting the أصل would
require un-fusing the stem while its suffix still carries the fused vowel, producing nothing a
reader could match against the surface. So: **one rule for the whole module — the mīzān mirrors
the surface; the أصل lives in the trace.**

Convenient consequence: for مضاعف the emitted string is *already* what the current code produces
(مَدَّ → «فَعّ», رَبِّهِمْ → «فَعِّهِمْ»). Only the flag flips. That makes the single largest
coverage win also the lowest-risk change in this proposal — no value churn, nothing to re-verify
letter by letter.

*Reversibility:* if the أصل form is later preferred for display, it is one rule in the pattern
data plus the trace already carrying فَعَلَ — not a redesign.

### D6 — Gold set + before/after measurement

A curated fixture (~30–50 words) pins `(ref, root, expected_mīzān, expected_verified,
expected_class)` for regular / إعلال / broken-plural / مضاعف cases, one test each (آلاء,
دُعَاء, رَحِيم, كِتَاب, رُسُل, مَسَاجِد, قَالَ, يَدْعُ, مَدَّ, …). A small script computes the
اجتهادي rate over a Qurʾān sample before and after; the after-rate must fall markedly. Tests
are local-only (per repo convention, `tests/` is git-excluded).

**Every class must have a gold case, or D6's acceptance is hollow** — an aggregate drop on
untested classes is not evidence. Two classes had no case and now do, both picked from real
corpus occurrences that fail today:

- **مثال with a deleted فاء** — يَعِدُ (35:40:28, root وعد, مثال). The initial و drops in the
  مضارع; today it yields «يَعِد» `verified=False` with the ف slot stranded. Exercises D3's
  حذف rule on radical₁, the position the يَدْعُ case does not cover.
- **لفيف مفروق** — يُوحَ (6:93:13, root وحي, لفيف). Both radicals are weak; the لام ي is deleted
  and today it yields «يُفع» `verified=False`. A second, harder لفيف case is مُتَّقِين (2:2:7,
  root وقي — the highest-frequency لفيف root at 258 occurrences): the فاء و is assimilated into
  تاء الافتعال, so *zero* radicals match today and the word emits itself verbatim. It is the one
  gold case that cross-checks the D3 إبدال rule, so it is tied to that task rather than to the
  لفيف class as such.

Also add a singular-vs-plural pair for the D4 `number` gate — كِتَاب (2:89:3, `number=None`) and
رِجَال (7:46:5, `number="P"`), both فِعَال on the surface, must both stay correct. They already
produce «فِعَال»; the gate must not break either.

The metric is the **full corpus** — the measurement above runs over all 49 967 rooted words in
seconds with no ML on the path, so a sample buys nothing and a full sweep is reproducible and
per-class breakable. Report the same class table before/after; the acceptance signal is
per-class, not just the aggregate, so an aggregate win cannot mask a class going backwards.

**Two existing tests invert by design** and must be rewritten rather than kept green:
`test_hollow_verb_is_flagged_heuristic` (قِيلَ, root قول) and
`test_geminate_root_is_flagged_heuristic` (وَيَمُدُّهُمْ, root مدد) currently assert
`verified is False`. قِيلَ is precisely the أجوف case D3 is built to resolve; مدد now flips to
`verified=True` per D5. Flag them in review so the inversion is an explicit decision, not an
accidental relaxation.

## Risks / Trade-offs

**The governing trade-off: an honest اجتهادي is better than a wrong mīzān badged محقّق.** This
change moves words *into* the «معطى محقّق» badge, so its dominant failure mode is no longer the
old one. Today a bad derivation is *labelled* bad — the اجتهادي tag warns the reader. After this
change, a mis-entered pattern produces a confidently wrong mīzān under the verified badge, and
nothing on screen says so. That is strictly worse than the status quo for the affected word, and
it is worse than the regression risk below, because a regression breaks a word that *was* right
(loud, caught by gold tests) whereas this quietly corrupts a word that was already flagged
(silent, invisible to any aggregate metric). Ranked accordingly:

- **[TOP] A pattern is mis-entered or over-matches → wrong mīzān under the verified badge** →
  Mitigate: (a) **every pattern added to the table carries at least one gold assertion** — a
  pattern with no test does not ship; (b) patterns require fixed letters/vowels *and* bound
  radicals to match; (c) deterministic first-hit on a documented ordering; (d) after each
  pattern batch, spot-check a sample of the words that newly flipped to verified **per pattern**,
  not a handful overall — the aggregate rate cannot detect this class of error, only inspection
  can; (e) when in doubt about a scheme, leave it out: an uncovered word stays honestly اجتهادي
  and appears in the coverage log for a later, better-evidenced pattern.
- **Over-generalized إعلال rewrites a regular word** → Mitigate: every rule gated on root class
  (D2/D3); a صحيح سالم root reaches no قلب/حذف path; regression gold tests (رَحِيم, كِتَاب,
  رُسُل, مَسَاجِد) plus the per-class table check after *each* rule.
- **Pattern ambiguity (two templates match one stem)** → Mitigate: deterministic first-hit on
  a documented ordering (more-specific / fixed-letter-richer patterns first) plus the D4
  `number` gate for the singular/plural ambiguity; ordering is data in the file and covered by
  a test.
- **The `number` gate mis-routes** → Mitigate: it *orders* candidates rather than hard-filtering,
  so a missing/odd `number` degrades to today's behaviour; gated on `== "P"` only (never `"S"`,
  which singulars do not carry); pinned by the كِتَاب / رِجَال pair.
- **Coverage stays partial** → Accepted and made visible: the coverage log enumerates every
  residual اجتهادي word so the gap is measured, not hidden (proposal guardrail).

## Migration Plan

Additive and behind no flag — pure improvement to a deterministic derivation with no schema,
API, or data-format change. Steps: (1) add pattern data file + provenance; (2) add root
classifier; (3) extend matcher with class-gated إعلال/إبدال; (4) insert pattern layer ahead of
projection; (5) redefine `verified` + add coverage log; (6) add gold tests + before/after
measurement. Rollback = revert `mizan.py` + remove the data file; nothing else depends on the
new result fields (root class / trace are additive). No data migration.

## Open Questions

- Exact seed contents/ordering of the pattern file — finalize against a corpus frequency pass
  during implementation (proposal scopes it to corpus-present patterns). The اجتهادي log grouped
  by (root, current wazn) already ranks the targets: قول, كون, كلل, حقق, ربب, شيا, اله, ايي,
  امن, نوس, نور, سمو, دنو, عزز lead the list.
- Whether the applied-rule trace is surfaced in the API/UI or stays internal (traceability +
  tests only). The proposal assumes internal-plus-additive-field; no frontend work is scoped.
  The one candidate for surfacing is the مضاعف إدغام note (D5), where showing «أصله فَعَلَ»
  alongside فَعَّ is pedagogically useful — but that is a UI decision, out of scope here.

*Settled since the first draft:* the مضاعف flag (now D5 — `verified=True`, fused form emitted,
أصل in the trace) and the root class of آلاء (now D2 — ناقص + hamzated فاء, not لفيف).
