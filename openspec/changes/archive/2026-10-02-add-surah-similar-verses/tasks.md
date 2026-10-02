## 1. Decisions to settle before any measurement

- [x] 1.1 Fix the syntactic signature element exactly (segment tags, stem features) as written in design D3, before any pair is scored — `role_ar` was in the first version and was removed before the first build (design D3, amendment 2026-10-02)
- [x] 1.2 Draft (Claude) `tests/eval/surah_similarity_gold.json`: positives = same meaning or subject AND near syntax (refrains of 55/77/54/26/37, parallel formulas, narrative statements built alike); negatives of three kinds = same subject / different syntax, same syntax / different subject, consecutive verses close by continuity — every pair with its reason
- [x] 1.3 Write the pre-registered target (recall@10 of positives, max negatives in top-3, max candidate-pool loss) into this file under 1.3, BEFORE the first build

  **Pre-registered target** — written before any build, any score, any coverage; gold sha256
  `34dfcdaa9523d4f5dc5b7c02580f4dff03d2987a0cdf7422a472cccab33cd55c` (60 positives, 13 + 10
  non-consecutive negatives, 15 consecutive). `N10(v)` is verse `v`'s stored neighbour list.

  - **Recall rule.** A positive `(a, b)` is recalled iff `b ∈ N10(a)` or `a ∈ N10(b)`. When `a` and
    `b` are verbatim identical (equal `quran_data.qac.ayah_words()` tuples), it is also recalled when
    `N10(a)` holds any verse verbatim identical to `b`, or `N10(b)` one identical to `a` — al-Raḥmān's
    refrain has 31 occurrences, so which ten fill the K slots is the tie-break, not closeness.
  - **recall@10 of positives ≥ 0.75** (≥ 45 of 60). Why: every positive is within the drafting
    rule, but the D3 element is finer than that rule (case, `role_ar`, prefix segments), and 8 of the
    60 share no content word, which task 3.6's «with shared content roots» storage rule — if kept —
    cannot store; 0.75 leaves room for both while still requiring the design to find three in four.
  - **Positives lost at candidate generation (syntax gate + M cap) ≤ 15 %** (≤ 9 of 60). Why: no
    positive exceeds the 1/3 rule that `σ` is derived from, so a gate loss can only come from the
    signature's finer granularity — design D3 «Known granularity» names the three kinds the drafting
    rule did not count (a prefixed conjunction, a proper name against a common noun in the same slot,
    the vocative glued to its noun), carried by at least six positives (the four الذين-series pairs,
    54:23/33, 37:159/180) on top of the seven placed at or near the limit, so this target may be
    missed; numbers unchanged, a miss is recorded as the result. The cap only bites in surahs over
    61 verses, where a near-identical pair should rank in each other's top 30 by dense or coverage.
  - **Non-consecutive negatives in any top-3 (either direction) ≤ 2 of 23**, kinds combined and
    reported per kind. Why: the 13 same-subject/different-syntax pairs are all beyond the 1/3 rule, so
    the syntactic gate should stop them; the 10 same-syntax/different-subject pairs pass that gate by
    construction and meet only the weaker semantic gate (`τ_sem = 0.125`), so a couple may surface.
  - **Consecutive negatives stored as neighbours: exactly 0** of 15. Why: D5 drops `|Δayah| = 1`
    before scoring; any non-zero count is a build bug, not a measurement.
- [x] 1.4 Fix `σ`, `τ_sem` and the group threshold τ a priori from the gold set's written reasons (D2, D8) and record them with K, M, `w_ce`, `w_dense`, `floor` in `design.md`

## 2. Dataset registration

- [x] 2.1 Add `SURAH_SIMILARITY_JSON` to `quran_data/paths.py` and its `manifest.py` entry (producer, inputs: `verses_final.json` + Qdrant collection + `morphology.json` + `quran-morphology.txt` + `word_function.json`, consumers, rebuild command, backend-must-be-stopped note)
- [x] 2.2 Add `loaders.surah_similarity()` (lazy, cached, schema-version check, `DatasetMissing` with the rebuild command)
- [x] 2.3 Confirm `tests/test_quran_data.py` passes with the new constant and entry

## 3. Builder

- [x] 3.1 Create `scripts/build_surah_similarity.py` with the `parents[N]` root anchoring; refuse to start when the embedded Qdrant lock is held
- [x] 3.2 Build per-verse content-root sets from `LexicalRetriever.index`, dropping roots whose every occurrence in the verse is in `word_function.json` or the `SimilarVerses` stoplist; mark root-less verses `unscored`
- [x] 3.3 Build per-verse syntactic signatures from `quran_data.qac.records()` (build time only; never `qac_words.json`; no `qac_syntax.json`)
- [x] 3.4 Enumerate non-consecutive intra-surah pairs of scored verses (drop `|Δayah| = 1`) and apply the syntactic gate (`1 − normalized word-level edit distance ≥ σ`); log survivors per surah
- [x] 3.5 Read verse vectors from Qdrant (`scroll`, `with_vectors=True`); compute rank-normalised dense and IDF-weighted content-root Jaccard on survivors; cap at M per verse by `max(dense rank, cov rank)` (all for short surahs)
- [x] 3.6 Run the symmetrised cross-encoder on kept pairs; compute `sem`, apply the semantic gate, rank by `sem × syn`; keep top-K with shared content roots; enforce score symmetry and the deterministic sort
- [x] 3.7 Compute groups (mutual stored pairs with score ≥ τ, connected components ≥ 2, ordered by strength then first ayah)
- [x] 3.8 Write the header (models, parameters, gold sha256) and the file; checkpoint per surah so a run resumes
- [x] 3.9 Document the command in `scripts/README.md`

## 4. Measurement

- [x] 4.1 Create `scripts/eval_surah_similarity.py` (or under `tests/eval/`): recall@K, rank of each positive, positives lost at each stage (syntax gate, candidate cap, semantic gate), negatives of each kind stored as neighbours; refuse a gold file whose digest differs from the header
- [x] 4.2 Run the build once and the evaluation once; record the numbers against the 1.3 target in `design.md`, including a miss as the result
- [x] 4.3 If a parameter changes afterwards, record a justification that does not cite the gold score, bump the header, rebuild — *one change after the first measurement: dense ignored between verbatim-identical verses (user, 2026-10-02; design «Amendment … dense ignored»), header `dense_on_verbatim`, rebuilt and re-measured*

## 5. Backend route

- [x] 5.1 Create `retrieval/surah_similarity.py` (pure reader: groups and neighbour lists from the loader dict; imports `quran_data` only)
- [x] 5.2 Add response models in `api/models/` (surah view: groups + unscored; anchor view: anchor + neighbours with shared roots + unscored flag)
- [x] 5.3 Create `api/routers/surah_similarity.py` serving `GET /surah/{number}/similar[?ayah=]`, all verses through `verse_from_record`; 422/404 on invalid refs, 503 with the rebuild command when the dataset is missing
- [x] 5.4 Mount it in `api/main.py`; check no route conflict with `GET /surah/{number}`
- [x] 5.5 Tests: dataset invariants (same-surah, no self, no `|Δ| = 1`, both gates hold on every entry, symmetry, sort, unscored 2:1), syntactic similarity symmetric/bounded/1 on identical signatures, vocative-only verses share no root, route contract, no model resident after calls (`/health`), `test_import_direction.py` and `test_module_root_depth.py` green

## 6. Frontend

- [x] 6.1 Add the client function and types in `frontend/src/lib/api.ts`
- [x] 6.2 Add the Arabic strings (mode labels «بعبارة» / «داخل سورة», unscored note, «no close verse in meaning and syntax» note, empty-groups message) to `lib/strings.ts`
- [x] 6.3 Add the two-way mode switch to the `similar` tab, «بعبارة» default, phrase panel untouched — *revised 2026-10-02 (user): the surah mode is labelled «المتشابهات داخل السورة» and comes first, the phrase mode «المتشابهات من عبارة»*
- [x] 6.4 Create the «داخل سورة» component in `frontend/src/components/`: surah select, groups (each framed in green and numbered in a green disc), ranked close verses with root chips, no numeric score, no consecutive verse; state under `verse-study.similar.surah.*` via `useCachedState` — *the ayah selector was removed 2026-10-02 (user): a verse is picked inside a group*
- [x] 6.5 Route verse-card activation to the «الآية في سياقها» tab like the phrase results
- [x] 6.6 Vitest: mode switch keeps both states; unscored vs no-close-verse messages; `npx tsc --noEmit -p tsconfig.test.json` green

## 7. Surface and docs

- [x] 7.1 Update `tests/test_served_surface.py` expectations with `GET /surah/{number}/similar`
- [x] 7.2 Confirm `tests/test_frontend_reachability.py` sees the new component imported
- [x] 7.3 Update `CLAUDE.md` (route list, `retrieval/` and frontend sections) and the served-surface table
- [x] 7.4 Manual check in the browser: surahs 55 (refrain group), 12, 2 (unscored 2:1), 108 (3 verses, likely no group), and the phrase mode unchanged
