## 1. Baseline measurement (before)

- [x] 1.1 Add a local script (e.g. `tests/eval/mizan_coverage.py`) sweeping every rooted word in `qac_words()` through the current `compute_mizan`, reporting total / verified / اجتهادي / rate **and the same breakdown per root class**. Stdlib + on-disk corpus only, no ML — the full corpus runs in seconds, so measure all 49 967 rooted words rather than a sample.
- [x] 1.2 Run on unmodified `main` and freeze the output as the baseline. It must reproduce `proposal.md`: 49 967 rooted words, 14 815 اجتهادي, 29.6 %; per class صحيح سالم 11 / أجوف 5 504 / مضاعف 4 055 / ناقص 2 739 / لفيف 1 186 / مهموز 1 006 / مثال 308 / رباعي 6. A mismatch means the corpus artifacts differ — resolve before writing code.
- [x] 1.3 Add a `--dump` mode writing the residual اجتهادي set (`ref, root, class, stem, wazn`) to a file. This doubles as the coverage log required in 5.4 — one mechanism, not two. Confirm the known false-اجتهادي cases appear: آلَاء→«فعَاء», قَالَ→«فَال», دُعَاء→«فُعَاء», يَدْعُ→«يَفْع», مَدَّ→«فَعّ», مُؤْمِنِين (unprojected).

## 2. Root classification (Layer 1)

- [x] 2.1 Add a pure `classify_root(root: str) -> str` in `analysis/mizan.py` returning **one weak-letter class** — صحيح سالم / مضاعف / مثال / أجوف / ناقص / لفيف (plus رباعي for 4-letter roots) — with the precedence لفيف → مضاعف → أجوف → ناقص → مثال → صحيح سالم pinned in code + docstring. **حرف علة is و/ي only; hamza is not one.**
- [x] 2.2 Return the hamzated radical position(s) as a **separate, orthogonal attribute** (the positions QAC stores as alif), not as a rival class label — a root is frequently both hamzated and weak. The hamza attribute must **not** gate any إعلال rule (§3's `_fold` fix covers hamza).
- [x] 2.3 Surface both fields in the `compute_mizan` result dict (additive) and add the matching optional fields to `api/models/qlisan.py::Mizan`; `available`/`wazn`/`verified`/`bab` keep their meaning.
- [x] 2.4 Unit-test the classifier: قول (أجوف), دعو (ناقص), مدد (مضاعف), وعد (مثال), وقي (لفيف), رحم (صحيح سالم), وسوس (رباعي). **Plus the two hamza cases that motivated the split:** `الو` (آلاء) → class **ناقص** + hamzated فاء — *not* لفيف; and `سال` (سأل) → صحيح سالم + hamzated عين.
- [x] 2.5 Re-run 1.1 — the rate must be **unchanged**, proving the fields are inert/additive at this point. The per-class table stays comparable to the baseline because 2.1's precedence is the one the baseline script used; the baseline's «مهموز» row corresponds to *otherwise-sound* hamzated roots, which now report as صحيح سالم + hamza attribute. Note that relabeling in the after-table so the two runs stay readable side by side.

## 3. Close the `_fold` hamza-carrier gap (prerequisite, not an إعلال rule)

- [x] 3.1 Add ؤ and ئ to `_fold`'s alif-folding branch. QAC stores roots hamza-folded onto alif, but `_fold` covers only أ/إ/آ/ٱ — so مُؤْمِنِين (root امن) matches *zero* radicals and emits itself verbatim. Update the docstring: hamza *carriers* are orthographic, folded here, deliberately not modelled as إعلال بالقلب.
- [x] 3.2 Re-run 1.1 and record the delta (expect ~1 000 words, concentrated in مهموز: امن, اله, الو…). Land this before §4 so the إعلال rules are measured on a correct fold instead of compensating for it.
- [x] 3.3 Guard: the صحيح سالم row must not move.

## 4. إعلال/إبدال-tolerant matcher (Layer 2a)

- [x] 4.1 Refactor the projection loop's `_fold(letter) == _fold(radical)` into a single class-gated predicate returning *(matched, rule_name | None)* so every acceptance path is named. Pure refactor — rate must stay flat.
- [x] 4.2 إعلال بالقلب, reachable only for أجوف/ناقص/مثال/لفيف: a و/ي radical may match surface ا, ى, or ء. Verify قَالَ (قول) → «فَعَلَ» and دُعَاء (دعو) → «فُعَال», not «فُعَاء».
- [x] 4.3 إعلال بالحذف, reachable only for ناقص/مثال/لفيف: a weak radical consumed with **no output letter** when absent on the surface, instead of being stranded. Cover all three positions, not just the لام: يَدْعُ (23:117:2, ناقص — لام dropped), **يَعِدُ (35:40:28, root وعد, مثال — فاء dropped, today «يَعِد»)**, and **يُوحَ (6:93:13, root وحي, لفيف مفروق — لام dropped, today «يُفع»)**.
- [x] 4.4 Known إبدال: assimilated تاء الافتعال (اصطبر / ازدجر) and hamzat waṣl. Pin it on **مُتَّقِين (2:2:7, root وقي)** — the highest-frequency لفيف root (258 occurrences), where the assimilated فاء currently leaves *zero* radicals matched and the word is emitted verbatim.
- [x] 4.5 Thread the fired rule name(s) into the result as an additive traceability field; a rule-resolved radical keeps `verified=True`.
- [x] 4.6 Guard, checked after **each** of 4.2–4.4 separately: re-run 1.1 and assert the صحيح سالم row is untouched. A rule that moves a sound-root word is over-generalized — fix its class gate before continuing.

## 5. Pattern library (Layer 2b) + wiring into compute_mizan

- [x] 5.1 Rank candidate patterns from the 1.3 dump so the seed table is corpus-driven, not theory-driven. Leading roots today: قول, كون, كلل, حقق, ربب, شيا, اله, ايي, امن, نوس, نور, سمو, دنو, عزز.
- [x] 5.2 Create the versioned data file (e.g. `analysis/data/mizan_patterns.*`) of ف/ع/ل templates + fixed letters/vowels → canonical mīzān, with an in-file provenance note citing the صرف source per scheme, a documented explicit ordering (more-specific / fixed-letter-richer first), and a **family tag per entry** (derived singular vs جمع تكسير) for the 5.5 gate.
- [x] 5.3 Seed derived singulars (فَعِيل, فَعُول, فَاعِل, مَفْعُول, فَعَّال, مِفْعال, فُعْلة…) and broken plurals (أَفْعَال, أَفْعُل, فُعُول, فِعَال, فُعَل, فِعَل, مَفَاعِل, فَوَاعِل, أَفْعِلَة, فُعَلَاء, أَفْعِلَاء…). **Rule: no pattern ships without at least one gold assertion** (§7) binding it to a real corpus word — a matched pattern goes *under* the verified badge, so an untested entry is a silent wrong-answer generator. Add patterns in small batches so 8.3's per-pattern inspection stays tractable; when a scheme is doubtful, leave it out and let the word stay honestly اجتهادي in the coverage log.
- [x] 5.4 Implement the cached loader (same `@lru_cache` shape as `analysis/qlisan_data.py`) + the alignment routine: bind radical slots via the §4 matcher, require fixed letters and vowels to match, deterministic first-hit.
- [x] 5.5 Gate family selection on QAC's `features.number`: `number == "P"` → try broken-plural templates first, otherwise singular templates first. The gate **orders** candidates, it does not hard-filter, so an odd/missing `number` degrades to un-gated behaviour. **Never test `== "S"`** — singulars carry no `number` at all (`كِتَابٌ` 2:89:3 is `None`, while `رِجَالٌ` 7:46:5 and `مَسَاجِدَ` 2:114:5 are `"P"`); an `== "S"` test would route every singular into the plural branch.
- [x] 5.6 Insert the ordering in `compute_mizan`: classify → pattern-match (emit the pattern's canonical mīzān with `verified=True` on hit) → else the existing raw projection (now matcher-aware) as last resort. Verify آلَاء (root الو) → «أَفْعَال», never «فعَاء».
- [x] 5.7 Test that two patterns matching one stem resolve to the documented first-hit, so ordering is pinned behaviour and not file-order accident. Include the singular/plural pair كِتَاب (2:89:3) / رِجَال (7:46:5) — identical فِعَال surfaces, opposite families — both must still yield «فِعَال» `verified=True` after the gate.

## 6. verified semantics + coverage log

- [x] 6.1 Redefine `verified` = pattern matched OR projection fully resolved (possibly via a recorded §4 rule); `False` **only** when no pattern matched AND radicals remain unresolved.
- [x] 6.2 **Implement the مضاعف shadda-fusion rule → `verified=True`** (decided, not open — 4 055 words, 27 % of all اجتهادي). Delete the blanket `radicals[-1] == radicals[-2] → False` special-case and replace it with a rule that consumes radical₂ and radical₃ against the single geminated surface letter and records itself in the trace. A geminate's mīzān is deterministic (مَدَّ = فَعَلَ in origin, أصله مَدَدَ; فَعَّ after إدغام), so اجتهادي was never the right label.
- [x] 6.2b Emit the **fused, surface-faithful** form as `wazn` (مَدَّ → «فَعَّ»), carrying the pre-إدغام أصل «فَعَلَ» in the trace. Rationale to record in the module docstring: the module's contract is that the mīzān mirrors the surface, and only the fused form composes with the rest of the word — رَبِّهِمْ → «فَعِّهِمْ», رَبَّكُمُ → «فَعَّكُمُ», whereas an أصل form would leave the stem un-fused while its suffix still carries the fused vowel. Sanity check: the emitted strings are already what the current code produces, so **only the flag should change** — any `wazn` diff on a مضاعف word signals a bug in the new rule.
- [x] 6.3 Wire the residual اجتهادي coverage log through the 1.3 dump path so every `verified=False` word stays enumerable.

## 7. Gold set + tests

- [x] 7.1 Create the curated gold fixture (~30–50 words) pinning `(ref, root, expected_mīzān, expected_verified, expected_class, expected_hamza)` across regular / إعلال / broken-plural / مضاعف cases. **Coverage rule: every root class gets at least one case** — صحيح سالم, مضاعف, مثال, أجوف, ناقص, لفيف, رباعي — so 8.1's per-class acceptance is backed by a test for every class it reports on. Note `expected_class` for آلَاء is **ناقص** (+ hamzated فاء), not لفيف.
- [x] 7.2 One test per key case: آلَاء (7:69:24)→أَفْعَال verified (no فعَاء); دُعَاء (2:171:11)→فُعَال; قَالَ (2:30:2)→فَعَلَ with the قلب rule recorded; يَدْعُ (23:117:2) with the weak لام consumed empty; **يَعِدُ (35:40:28, مثال — فاء consumed empty)**; **يُوحَ (6:93:13, لفيف مفروق)**; **مُتَّقِين (2:2:7, إبدال تاء الافتعال)**; مَدَّ (13:3:3)→فَعَّ `verified=True` plus رَبِّهِمْ (2:5:5)→فَعِّهِمْ and رَبَّكُمُ (2:21:4)→فَعَّكُمُ; and the regression set رَحِيم→فَعِيل, كِتَاب→فِعَال, رُسُل→فُعُل, مَسَاجِد→مَفَاعِل, رِجَال (7:46:5)→فِعَال.
- [x] 7.3 Rewrite the two tests that **invert by design** — `test_hollow_verb_is_flagged_heuristic` (قِيلَ, root قول) and `test_geminate_root_is_flagged_heuristic` (وَيَمُدُّهُمْ, root مدد) in `tests/test_mizan.py` both assert `verified is False` today. قِيلَ is exactly the أجوف case §4 exists to resolve; مدد is now `verified=True` per 6.2 (its `wazn` unchanged). Rename them to state the new expectation and call the inversion out in the change summary — it must read as an explicit decision, not a silently relaxed assertion.
- [x] 7.4 Assert the coverage rule from 5.3 mechanically where practical: every entry in the pattern data file is referenced by at least one gold assertion, so an untested pattern fails the suite rather than shipping silently.
- [x] 7.5 Verify the rest of `tests/test_mizan.py` passes untouched: يَرْتَع→يَفْعَل, السَّحَاب→فَعَال, الْعَالَمِين→فَاعَلِين, تَسْأَلُوا→تَفْعَلُوا, فَوَسْوَسَ→فَعْلَل, حِفْظُهُمَا→فِعْلُهُمَا, the segment-breakdown block, `verb_bab`.
- [x] 7.6 Run the full local backend suite (`python -m pytest -q`) — the `test_qlisan_*.py` files consume the same fiche and must stay green.

## 8. After measurement + wrap-up

- [x] 8.1 Final 1.1 run: record the after-table and the delta **per class**, not just the aggregate. Acceptance = the aggregate falls markedly AND no class regresses AND صحيح سالم stays ≥ 99.9 % verified.
- [x] 8.2 Enumerate the residual اجتهادي words from the coverage log for triage / future patterns.
- [x] 8.3 **Per-pattern inspection of newly-verified words — the main defence against "verified but wrong".** For *each* pattern added in §5, sample the words that newly flipped to `verified=True` **because of that pattern** and check the emitted mīzān by hand. A few words overall is not enough: the aggregate اجتهادي drop cannot distinguish a correct pattern from a wrong one, because both lower it. Record which patterns were sampled and at what depth; a pattern whose sample shows a bad mīzān is removed or corrected before release, not shipped with a caveat.
- [x] 8.3b Sanity-check the rendered fiche end-to-end for a handful of flipped words spanning the rule families (آلَاء 7:69:24 pattern, قَالَ 2:30:2 قلب, يَعِدُ 35:40:28 حذف, مَدَّ 13:3:3 fusion, مُؤْمِنِين fold) — اجتهادي tag gone, mīzān correct, class label sane. No frontend change is expected; if one turns out to be needed, report it as a scope finding rather than absorbing it.
- [x] 8.4 Update the module docstring / `architecture.md` / `plans/` to describe the layered derivation and the pattern data file.
- [x] 8.5 `openspec validate harden-mizan-irregular-roots --strict` and the local pytest suite green.

## 9. Curated special cases for the residual (follow-on, 2026-08-03)

Direction taken after the §8 measurement: **stop chasing general rules.** What survived the
general layers is not a long tail of near-misses — it is a few closed, very frequent classes.
More general إعلال rules would risk the sound-root guarantee for a few hundred words; a named
table is safer and reviewable. Everything not named stays honestly اجتهادي in the coverage log,
so patterns can be added one at a time without reopening this work.

- [x] 9.1 Add a `special_cases` section to `analysis/data/mizan_patterns.json` (same versioned
      file, same provenance discipline) with a `why` for each entry.
- [x] 9.2 `hamza_elision_roots` — a **named closed class** of roots whose hamza radical is simply
      dropped: راي (يَرَى < يَرْأَى, the عين) and اكل/اخذ/امر (كُلْ/خُذْ/مُرْ, the فاء). Deletion
      stays reserved for و/ي radicals everywhere else; licensing it for hamza in general would
      fire wherever a hamzated root came up short. Golds: نَرَىٰ→نَفَل, أَرَىٰ→أَفَل,
      كُلُوا→عُلُوا, خُذْ→عُل, plus a negative gold (تَسْأَلُوا, root سال, untouched).
- [x] 9.3 `not_weighed` — الأعلام لا توزن. لفظ الجلالة (lemma الله, pos PN) and اللهم are
      reported as *no mīzān* (`available=False`) instead of being guessed. Scoped to the exact
      (root, lemma, pos) triple: إله/آلهة share the root but are ordinary nouns and still weigh
      as فِعَال. Its derivation is also genuinely contested (أصله الإله on فِعَال vs. جامد), so
      emitting any wazn would pick a side the corpus does not settle.
- [x] 9.4 **Finding — the metric was rewarding a wrong answer.** 2 540 لفظ الجلالة occurrences
      were `verified=True` with «فعلَّل» — four slots for a three-letter root, i.e. the article's
      letters mapped onto ف/ع/ل. They counted as *successes* in every coverage number, so no
      aggregate could ever have surfaced them; only reading the output did. This is the single
      largest wrong-verified cleanup in the change and the sharpest evidence for the per-pattern
      inspection rule in §8.3.
- [x] 9.5 Re-measure and re-run the gates: صحيح سالم unchanged at 11, no class regressed.
- [x] 9.6 Track the pre-existing `test_madar.py` failure as a separate issue (`plans/STATUS.md`
      → Known open issues, KI-1) so a known red cannot mask a new one.
- [ ] 9.7 **Deferred (polish, not a fix):** surface `asl` in the fiche — «الوزن فَعّ — وأصله
      فَعَلَ» for a geminate, «أصله قَوَلَ، قُلبت الواو ألفاً» for a قلب — showing it only when a
      rule actually fired. Turns a correct-but-opaque wazn into a teaching moment. The data is
      already in the payload (`rules`, `asl`); this is a UI decision, and may belong to the
      future دلالي/synthesis layer instead.
