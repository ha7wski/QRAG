## 0. Review gate — CLOSED 2026-09-25

- [x] 0.1 Four open questions answered — citations become `attested`/`hypothesis`; `ضرب` is a
      regression case, not a coverage gate; records live in `data/references/`; no second judge
- [x] 0.2 The 15-primitive table (§D4) and the rarity rule (§D5) confirmed
- [x] 0.3 The witness set (§D10) accepted as drawn, not re-rolled
- [x] 0.4 Two amendments folded in: §D13 collision probe promoted to a gate; §D11 signature-letter
      split declared before the measurement

## 1. The frozen input layer

- [x] 1.1 Write `data/references/physical_primitives.csv` — 15 primitives, each row carrying
      `status` (`attested` | `hypothesis`), and for `hypothesis` a `physical_basis`
- [x] 1.2 For each row, attempt a real `authority` + `pages`; promote to `attested` only where a page
      actually says it, force none, and record `support` citations as support — never as authority
- [x] 1.3 Write `data/references/physical_primitives.lock.json` v1.0.0 — sha256, `frozen_on`, row
      count, `history[0]` stating that the table is the project's construction
- [x] 1.4 `PHYSICAL_PRIMITIVES_CSV` / `PHYSICAL_PRIMITIVES_LOCK_JSON` in `quran_data/paths.py`,
      cached loaders in `loaders.py`, entries in `manifest.py` (`tests/test_quran_data.py` gates this)
- [x] 1.5 `scripts/build_physical_primitives_seed.py` — emits feature rows from the letter sheet,
      leaves primitive + status + citation to the curator, can never write the frozen table
- [x] 1.6 `scripts/validate_concept_datasets.py` — pages **or** explicit `hypothesis`, never an empty
      field, never an approximate page; ≤15 cap; lock digest; `history[].source` against the
      authority index
- [x] 1.7 `tests/test_physical_primitives.py` — digest survives a seed run, cap enforced, no root key
      reachable, `ibn_jinni_note` absent from every concept module, no `hypothesis` row exposes a
      `support` citation as authority

## 2. The witness set — committed with the table, not after

- [x] 2.1 `data/references/concept_witness_set.json` — the 40 roots, frame 280, strata 205/75, seed
      20260925, draw date, exclusions
- [x] 2.2 Path constant, loader, manifest entry
- [x] 2.3 `tests/test_concept_witness_set.py` — replays the draw and fails if the file moved; asserts
      `ضرب`, the 5 curated roots and all §D13 probe roots are absent

## 3. Minimal generation path — only what the probe needs

- [x] 3.1 `linguistics/lisan/concept/features.py` — parse `sifat`; privative / equipollent /
      no-opposite / disputed rule; `makhraj_ar` exposed unmapped
- [x] 3.2 Assert the derived vocabulary excludes `munfatiha`, `mustafila` and the debated value, and
      that all 28 letters yield ≥1 feature
- [x] 3.3 `linguistics/lisan/concept/primitives.py` — frozen-table store keyed on features only,
      exposing each primitive's letter-coverage and `status`
- [x] 3.4 `linguistics/lisan/concept/compose.py`, ordering half only — three positions, rarity order,
      top-two realised, remainder as `carried`
- [x] 3.5 Add the concept package to `tests/test_import_direction.py` — it may not reach
      `root_cores.json`, `maqayis_asl.csv`, `letter_senses.csv` or `semantic_axes.json`

## 4. Collision probe (review amendment «tâche 2 bis») — HARD GATE

> Runs before **any** curation. The qualification table is published first, then the probe; stop
> and report when done. No sentence template, no LLM, no route, no page is needed: the probe
> compares realised primitives.

- [x] 4.1 Implement the three-outcome comparator on realised primitives — `identical` /
      `order-distinct` / `distinct` — and the set-based aṣl-divergence test, both before composing
      anything
- [x] 4.2 **Qualification table, committed before any composition**: for each comparison, both
      roots' aṣl sets read whole from `maqayis_asl.csv` and a `qualifying` / `non-qualifying`
      verdict under the set rule. Size stated in **roots** — 7 over 3 classes — never in pairs
- [x] 4.3 Apply the emptied-class rule: `ت`/`ك` or `و`/`ي` empty ⇒ run on what qualifies and report
      the reduced size; `ب`/`ج`/`د` empty ⇒ **stop and report**, alternates examined only after, and
      the report says the substitution followed an empty sample. No root added to compensate
- [x] 4.4 Compose `حرب` · `حرج` · `حرد` (ب/ج/د), `تبر` · `كبر` (ت/ك), `كود` · `كيد` (و/ي)
- [x] 4.5 Apply the decision rule: **one** `identical` on an aṣl-divergent pair ⇒ collision
      confirmed ⇒ stop, do not widen, the five مخرج zones become table v1.0.0 and tasks 1–3 are redone
- [x] 4.6 Report `order-distinct` outcomes as partial collisions, never grouped with `distinct`
- [x] 4.7 Widen to `ط`/`ق`, `ث`/`ح`/`ف`/`ه`, `م`/`ن` **only** if all three classes discriminate;
      `ظ`/`غ` excluded in every case (`ظلم` is already curated)
- [x] 4.8 Commit the probe record (roots, realised primitives, aṣl, per-pair outcome, verdict) and
      **report — do not continue**

> **PROBE — RUN 1, 2026-09-25, on the ṣifāt-only draft: COLLISION CONFIRMED, 5 of 5.**
> Every qualifying comparison came back `identical`. `حرب` = `حرج` = `حرد` · `تبر` = `كبر` ·
> `كود` = `كيد`. No `order-distinct`, no `distinct`. Structural, not a composer bug: that table
> gave **18 profiles for 28 letters** and the seven merged groups were exactly §D4's prediction.
> §D3's pre-declared fallback fired: the five classical مخرج zones became table **v1.0.0** — a
> replacement, not a bump — and §§1–3 were redone. The superseded draft's digest is in the lock's
> `history[0]`; both runs are on file in `data/references/concept_collision_probe.json`.
>
> **Two design amendments came out of the rebuild, and one of them is an honest exposure.**
> The cap moved 15 → 20, by exactly five, to admit a closed classical partition (§D4). The realised
> window moved 2 → 3 (§D5) — **after** a measurement — because at two the zone separating `و` from
> `ي` ranked third and never reached the sentence, so profiles became distinct while concepts stayed
> identical. «The rule was fixed before it was checked» still holds for the positions, the rarity
> order and the tie-break; **it no longer holds for the window**, and §D5 now says so rather than
> implying otherwise. No root was read and the holdout is untouched.
>
> **PROBE — RUN 2, on v1.0.0: CLEAN SWEEP, 5 `distinct` of 5.** All three mandated classes
> discriminate — the only outcome that licenses widening (4.7).
>
> **WIDENING — 130 minimal pairs over the three remaining classes, swept exhaustively.**
> Sample fixed by a mechanical enumeration rule (every pair that exists whose both roots carry a
> `has_asl` row, minus the 13 already spent) — no sampling, no ranking, no truncation, so there is
> no choice left to make by looking at the data. Result: **117 `distinct`, 0 `order-distinct`,
> 13 `identical` — and all 13 fall on the single letter pair `ح`/`ه`**, the residual §D3 declared
> before the sweep ran. 12 of the 13 carry divergent aṣl and are confirmed collisions;
> `فرح`~`فره` is filed non-qualifying under the conservative set rule. `ط`/`ق` and `م`/`ن` swept
> clean over 49 pairs — stated plainly: the zones separate them by construction, so their result was
> settled before an aṣl was read. `ظ`/`غ` excluded throughout (`ظلم` is curated).
> The widening is **one notch weaker as evidence** than the mandated probe — its aṣl verdicts were
> read after the outcomes — and the record says so and publishes every aṣl verbatim.
>
> **This is the HARD STOP of migration step 4: report, and wait.** Tasks 5–11 are NOT begun. The
> table's coarseness is now quantified rather than asserted: one letter pair, 12 root collisions.

## 5. Composition, completed

- [x] 5.1 The deterministic Arabic template and the مفهوم assembly
- [x] 5.2 Partial concepts: silent letters named, position omitted, no filler, no fallback flag
- [x] 5.3 Hamza carriers resolved to `ء` via an explicit carrier→hamza map — **NOT**
      `arabic_text.fold_carrier`, which folds toward the carrier and deletes the hamza; bare `ا`
      reported silent
- [x] 5.4 Quadriliteral roots return no concept with a stated reason
- [x] 5.5 `tests/test_concept_composition.py` — the `ضرب` pairs of §D5, determinism across processes,
      the confirmed collision behaviour, partial and refused cases, no compensation for the
      signature bias
- [x] 5.6 `linguistics/lisan/concept/witness_guard.py` — **a test may not compose a holdout root.**
      Hard failure from the first line of `compose()`, no warning mode and no flag; the shipped
      route and the recording path are unaffected (the latter takes an explicit, greppable
      sanction). Thirteen existing tests were composing witness roots incidentally and were moved
      off the holdout — including the `ح`/`ه` collision pair, `حجر`~`هجر` → `حبط`~`هبط`. The `قوم`
      note in `concept_attestation.json` is KEPT: it documents the incident, it just is no longer
      the only thing standing between the holdout and the next test somebody writes

## 6. Optional phrasing, with a veto over it

- [x] 6.1 `linguistics/lisan/concept/phrasing.py` behind `CONCEPT_LLM_PHRASING=0` (off)
- [x] 6.2 Containment check: every content word maps to a realised primitive's declared lemma set
- [x] 6.3 Rejection returns the template sentence and records the rejection in the response
- [x] 6.4 Test that an injected out-of-vocabulary phrasing is rejected, not shown

## 7. Confrontation

- [x] 7.1 `linguistics/lisan/concept/confront.py` — the only module that may read the aṣl; imports the
      concept result, never the reverse
- [x] 7.2 `data/references/concept_attestation.json`: `uses[]`, per-use verdict, frozen-at and
      recorded-at stamps; path constant, loader, manifest entry
- [x] 7.3 Validator refuses to print the metric when any `uses[]` was frozen after its concept
- [x] 7.4 Metric printer: `k / 40`, strict, with the signature-letter split, the per-root verdicts
      AND the §D11 window reservation — printed WITH the number, never by reference
- [x] 7.5 Wording check: the records are described as making an audit possible, never as audited

> **WHY 8 AND 9 RAN AFTER THE FREEZE, AND WHY THAT IS NOT A DEVIATION.**
> The numbering puts the API and the page before the curation, and they were done after it. The
> reason is the protocol's own ordering, not convenience: building `POST /lisan/concept` and the
> `/lexical` panel means composing roots and LOOKING at what comes back — that is what building a
> display is — and §D9 step 1 requires every witness root's `uses[]` to be frozen while no concept
> of theirs exists. Doing 8 and 9 first would have put the curator in front of witness readings
> before writing the uses they are measured against, which is the exact contamination `k / 40`
> exists to exclude. The tasks were deferred, never skipped, and the freeze commit
> (`6b2a6be`) sits between them in the history. `witness_guard` now makes the same
> ordering hold mechanically rather than by care: task 5.6.
>
> **Where they actually landed, stated exactly rather than implied.** The commit mounting the
> route and the panel (`9719347`) sits AFTER the measurement (`a64518d`), not merely after the
> freeze. Nothing about the measurement depends on it: `k / 40` was computed, judged and committed
> before a single byte of the route existed, so the display could not have shaped it even in
> principle. The ordering that matters is readable straight off `git log`: freeze → criterion →
> measurement, with the UI work falling where it did not matter.

## 8. API

- [x] 8.1 Concept models in `api/models/lisan.py`, carrying each realised primitive's `status`
- [x] 8.2 `POST /lisan/concept` in `api/routers/lisan.py`, mounted in `api/main.py`
- [x] 8.3 Update `tests/test_served_surface.py` for the added route and its caller
- [x] 8.4 Assert `POST /lisan/analyze` responds identically for `خير`, `خبث`, `كفر` and that
      `tests/test_lisan_regression.py` passes unmodified

## 9. Frontend

- [x] 9.1 `lib/lisanTypes.ts` + `lib/api.ts` — the concept call
- [x] 9.2 `/lexical` concept panel: the مفهوم shown as **three positional groups** (يفتَح /
      جسَد / يختِم), not as one nine-noun sentence — §D6's amendment; the recorded deterministic
      chain still shown verbatim beside them as what was measured. Per-letter profile, realised
      vs. carried primitives, partial/refused states
- [x] 9.3 Attested mappings visually distinguished from project hypotheses
- [x] 9.4 The مفهوم / معنى statement, owned by the page, present without interaction
- [x] 9.5 Comparison panel: physics-first مفهوم beside the core-first reading, aṣl `verbatim`,
      occurrences, recorded verdict — neither engine labelled correct
- [x] 9.6 Vitest files + `npx tsc --noEmit -p tsconfig.test.json`

## 10. Curation and the measurement

- [x] 10.1 For each of the 40 witness roots: freeze `uses[]` and commit it **before** generating that
      root's concept — **DONE 2026-09-25: 40 roots, 183 uses, every verse checked against that
      root's own occurrence list, every verdict `not_judged`, `concept_recorded_at` empty on all 40**
- [x] 10.2 Generate the 40 concepts; record per-use verdicts and reasons — **DONE: 183 uses
      judged, 7 covered. Miss classes: `imported` 162, `direction` 8, `inert` 6.** The coverage
      criterion was committed first, alone, with no verdict in the tree (`ec3a807`)
- [x] 10.3 Confront `ضرب` on its five brief-named uses and publish the result, expected partial,
      excluded from `k` — **DONE: 1 / 5, partial, as §D9 predicted.** Its record carries an explicit
      `ordering_exemption` rather than borrowing the blindness the 40 claim
- [x] 10.4 Publish `k / 40` with the signature-letter split and the per-root table — and change no
      dataset in that commit — **DONE: `k / 40 = 0`, split `0 / 25` signature and `0 / 15` plain.**
      1 of 40 failing roots is a collision, so §D3's reopening condition (strictly more than half)
      is not met and the `ح`/`ه` residual costs this measurement nothing

> **FREEZE COMMITTED — 2026-09-25, before any witness concept exists.**
> All 40 witness roots carry their `uses[]`: **183 uses**, each a distinct Quranic sense with one
> verse reference drawn from that root's OWN occurrence list (checked mechanically, 0 violations).
> Every verdict is `not_judged` and `concept_recorded_at` is empty on all 40 — the state §D9 step 1
> requires, committed as its own step so it exists in the history as a fact rather than a claim.
>
> **Two gate defects were found and fixed by getting here**, both of which would have corrupted the
> metric silently. (1) The validator had NO representation of the mandated intermediate state —
> uses frozen, concept not yet generated — so the only shape it accepted was uses and verdicts
> written together, which is exactly the after-the-fact record the gate exists to catch. (2)
> `recorded` counted a root as recorded because it had a FICHE, not because its concept existed, so
> the freeze printed «k / 40 : 0 / 40» — a number over nothing that reads as «the method covers no
> root» rather than «nothing has been measured yet».
>
> **Tasks 8 (API) and 9 (frontend) were deferred past the freeze rather than done first**:
> building the route and the panel means composing and LOOKING at concepts, and doing that before
> the uses were frozen is the one ordering the protocol forbids. See the note above §8.

## 11. Documentation

- [x] 11.1 `documentation/lisan-concept-from-physics.md` (French) — the table and its `status`
      regime, the rules, the probe outcome (both runs + the widening), the protocol, `k / 40` with
      its split **and the §D11 window reservation stated where the number is stated** (§0, in the
      same block as the number), the accepted `ح`/`ه` residual with its reopening condition
      **evaluated against the measurement**, and what it does not cover
- [x] 11.2 `CLAUDE.md`: `linguistics/lisan/` gains the coexistence note and the two-engine route pair
- [x] 11.3 Record what would end the comparison — this change does not pre-judge which engine
      survives (documentation §10: `k / 40 = 0` is a result about the physics-first engine and is
      **not** a measurement of the core-first one, which has no comparable metric and whose known
      defect is the opposite)

## The measurement, as published

> **k / 40 = 0.** No witness root's concept covers every use frozen for it. `0 / 25` on roots
> carrying a signature letter, `0 / 15` on roots carrying none — the split declared before the
> measurement separates nothing, because there is nothing to separate.
>
> Of 183 frozen uses, **7 are covered**. The misses classify as **`imported` 162 · `direction` 8 ·
> `inert` 6**, and that distribution is the finding rather than the zero. The engine does not miss
> by saying the wrong thing or saying it in the wrong order — it misses because the notion is not
> in the feature vocabulary. `عقل` needs إدراك; `خوف` needs an affect; `نصر` needs two parties;
> `قول` needs speech, which a vocabulary describing how sounds are made cannot assert without
> circularity. The five roots with any covered use — `قعد` `مسك` `دخل` `رجع` `رود` — all name a
> movement or a hold with **no external domain**.
>
> **RESERVATION, published with the number and not elsewhere:** the composition rule is not
> entirely pre-registered. The realised window was declared at two and widened to three after a
> measurement came back negative on `ضرب`, the declared development case. The holdout was never
> read when the window changed and `ضرب` is excluded from `k`; that contains the exposure and does
> not erase it. A reader who discounts `k / 40` on that ground is reading correctly.
>
> **§D3's reopening condition is NOT met, and the measurement is what says so.** 1 of 40 failing
> roots is a collision (`هجر` ~ `حجر`, divergent aṣl), against a threshold of strictly more than
> half. The accepted `ح`/`ه` residual costs this measurement nothing, and splitting the حلق would
> change `k / 40` by zero. The condition was written before the number existed; it is now answered
> by evidence rather than by preference.
>
> **What this does not authorise.** The result says `imported` 162 times, so the missing notion is
> not a granularity question. Widening the feature vocabulary to reach `إدراك` or `عون` would be
> adding a trait *because* the measurement failed — exactly the move the table's freeze forbids.
> The table moves only through a lock version justified by a feature-level authority.
