## 1. Shared core (`scripts/closeness_core.py`, pure, TDD)

- [x] 1.1 Tests then implementation: `content_words` (D1) — primary root in the verse's content-root set (as `content_root_sets()` computes it) AND ref not in `word_function.json`
- [x] 1.2 Tests then implementation: `match_all` (D2) — one assignment over all words, edge kinds `lemma` / `root` / `tool`, weights 1 / 0.5 / 1, relative-position tie-break; content never paired with non-content; equals step 1's content matching up to D1
- [x] 1.3 Tests then implementation: `lex` (D3) — word-level IDF Jaccard of the content edges; symmetric, 1 for identical content in any order, 0 for a vocative-only overlap
- [x] 1.4 Tests then implementation: `syn` (D4) — `½·uni + ½·bi` over the unchanged `(segs, stem)` elements; symmetric, bounded, 1 for identical; a 3-word displaced block in 9 loses ≤ 3 bigrams and keeps `syn ≥ σ`; the 55:13 / 55:25 refrain = 1
- [x] 1.5 Tests then implementation: exact upper bounds (D5) — length bound and bag bounds never below the true `syn` (property test over random signatures)
- [x] 1.6 Tests then implementation: `passage_region` (D6) — 28:20/36:20 covers «وَجَاءَ … قَالَ», 2:3/14:31 found with «يُنفِقُونَ» in the window, a short formula rejected, `root` edges count as gaps, deterministic ties

## 2. Intra build (`build_surah_similarity.py`)

- [x] 2.1 Replace `syn_similarity` (Levenshtein) and `cov_similarity` by the core's `syn` / `lex`; the stored field `cov` → `lex`; shared roots = roots of the content edges; «shares a content root» → matched mass > 0
- [x] 2.2 Bump `SURAH_SIMILARITY_SCHEMA`; header names the syntactic measure and the lexical signal; update tests (`tests/test_surah_similarity*.py`) and the eval script's diagnostics (`cov` → `lex`)

## 3. Cross build (`build_quran_similarity.py`)

- [x] 3.1 Re-derive the pre-filters with the core's exact bounds (D5); the syntax stage scores survivors with the core's `syn`; `lex` replaces `cov` in `Corpus`
- [x] 3.2 Bump `QURAN_SIMILARITY_SCHEMA`; shared-parameter check covers the new measure names; tests incl. «no passing pair is pruned» on a random sample; eval script reads `lex`

## 4. Passage build (`build_quran_passages.py`)

- [x] 4.1 Replace Smith–Waterman by the core's `passage_region` (candidate generation unchanged); remove the SW code and its constants (`MATCH`, `MISMATCH`, `GAP`, `TRACEBACK`); header names `passage: "dense-region"`
- [x] 4.2 Bump `QURAN_PASSAGES_SCHEMA`; tests (pinned pairs, short formula); eval script unchanged in its reading of `k` / `wa` / `wb`

## 5. Close-verses build (`build_quran_close_verses.py`)

- [x] 5.1 Import the content-word definition and the matching from the core (no local copy); ungated `sim` for passage-only pairs through the new `syn` / `lex`; common part = core content edges, bridging and runs unchanged
- [x] 5.2 Bump `QURAN_CLOSE_VERSES_SCHEMA`; tests (2:3/14:31 common part unchanged, 28:20/36:20 one run, scores independent of the common part)

## 6. Readers and repo guards

- [x] 6.1 Any reader / route / frontend type reading a renamed stored field (`cov`) follows; `quran_data/manifest.py` entries describe the new rules; `python -m pytest -q` and the frontend checks pass

## 7. Version 1 — rebuilt, measured, closed (see design «Version 1»)

- [x] 7.1 Stop the backend; rebuild intra → cross → passages → close verses; record build times and survivor / stored counts
- [x] 7.2 Run the four eval scripts; record every figure under «Measured result» in design.md with PASS / MISS against D9 (no parameter change after this point)
- [x] 7.3 Version 1 result recorded (9 MISS of 15); app check and CLAUDE.md deferred to version 2

## 8. Gold protocol (D10) — BEFORE any version-2 code

- [x] 8.1 Write the definition text (Arabic + English) and put it in the header of the three gold files; relabel them in a FRESH context (definition + verse texts only, no system output): `neg_scattered` split into permuted blocks (positive) / scattered (negative), every changed label with its reason; bump versions; update the digests the eval scripts refuse
- [x] 8.2 `scripts/draw_closeness_blind_sample.py`: seeded, model-free draw of 60 cross-surah pairs sharing ≥ 3 content lemmas, 20 per `lex` bin `[0.3,0.5)` / `[0.5,0.7)` / `[0.7,1]`, no gate; label in a fresh context; commit `tests/eval/closeness_blind_v2.json`
- [x] 8.3 `scripts/eval_closeness_blind.py`: positives stored (either direction) / negatives stored over the cross-surah and close-verses datasets; refuses a digest mismatch; targets ≥ 0.65 / ≤ 0.25 printed

## 9. Core version 2 (`scripts/closeness_core.py`, TDD)

- [x] 9.1 D2 tie-break: anchors (token unique in both verses), `δ = median(q − p)`, penalty `10⁻³·|(q−p)−δ|/max(n)`; tests: 2:255/3:2 content edges pair the OPENING «لا», step-1 pinned pairs unchanged
- [x] 9.2 D4 coarse element: `coarse_element(segments)`; tests: 43:83/70:42 equal signatures, رَبِّكُمْ/رَبِّهِمْ one element, PASS kept, case/mood dropped; 55:13/55:25 still equal
- [x] 9.3 D4 block re-ordering + `syn = max(plain, A·B′, A′·B)`; tests: pure block permutation → 1, substitution costs 1/n, symmetric, bounded, no edge → plain Levenshtein; 2:173/16:115 ≥ σ
- [x] 9.4 D5 bounds: length + coarse bag only (bigram bound removed); property test over random signatures AND random block re-orderings
- [x] 9.5 D6 largest accepted region with the full tie order and A-orientation; exact pruning; tests: 28:20/36:20 (1..7), 2:3/14:31 found, 2:255/3:2 k = 7, 2:164/45:5 accepted sub-window, short formula rejected, brute-force equality on small random cases

## 10. Builds, version 2

- [x] 10.1 `build_surah_similarity.py`: signature = coarse elements from the core; `syn` with re-ordering needs the edges → the intra syntax stage computes the matching for the pairs it scores (candidate generation unchanged); header names (D8)
- [x] 10.2 `build_quran_similarity.py`: pre-filters = length + coarse bag (drop the bigram stage from stats/diagnostics/eval), syntax stage with the core's `syn`; header names; blind-sample digest in the header
- [x] 10.3 `build_quran_passages.py`: largest accepted region from the core; header names
- [x] 10.4 `build_quran_close_verses.py`: D2 tie-break through the core; blind-sample digest in the header
- [ ] 10.5 Tests of the four builds and the eval scripts follow; `python -m pytest -q` green; frontend checks green

## 11. Rebuild and measure, version 2 (backend stopped)

- [ ] 11.1 Stop the backend; rebuild intra → cross → passages → close verses (`--fresh`); record build times and survivor / stored counts
- [ ] 11.2 Run the four evals on the relabelled gold (in-sample) and `eval_closeness_blind.py`; record every figure under «Measured result (version 2)» with PASS / MISS against D9 — no parameter change after this point
- [ ] 11.3 Restart; check in the app: sūra 2 annotations (2:3 bubble lists 14:31), the map, the «داخل السورة» groups
- [ ] 11.4 Update CLAUDE.md's closeness paragraphs (coarse signature, block re-ordering, `lex`, largest accepted region, blind sample)
