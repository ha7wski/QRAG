## 1. Shared core (`scripts/closeness_core.py`, pure, TDD)

- [ ] 1.1 Tests then implementation: `content_words` (D1) — primary root in the verse's content-root set (as `content_root_sets()` computes it) AND ref not in `word_function.json`
- [ ] 1.2 Tests then implementation: `match_all` (D2) — one assignment over all words, edge kinds `lemma` / `root` / `tool`, weights 1 / 0.5 / 1, relative-position tie-break; content never paired with non-content; equals step 1's content matching up to D1
- [ ] 1.3 Tests then implementation: `lex` (D3) — word-level IDF Jaccard of the content edges; symmetric, 1 for identical content in any order, 0 for a vocative-only overlap
- [ ] 1.4 Tests then implementation: `syn` (D4) — `½·uni + ½·bi` over the unchanged `(segs, stem)` elements; symmetric, bounded, 1 for identical; a 3-word displaced block in 9 loses ≤ 3 bigrams and keeps `syn ≥ σ`; the 55:13 / 55:25 refrain = 1
- [ ] 1.5 Tests then implementation: exact upper bounds (D5) — length bound and bag bounds never below the true `syn` (property test over random signatures)
- [ ] 1.6 Tests then implementation: `passage_region` (D6) — 28:20/36:20 covers «وَجَاءَ … قَالَ», 2:3/14:31 found with «يُنفِقُونَ» in the window, a short formula rejected, `root` edges count as gaps, deterministic ties

## 2. Intra build (`build_surah_similarity.py`)

- [ ] 2.1 Replace `syn_similarity` (Levenshtein) and `cov_similarity` by the core's `syn` / `lex`; the stored field `cov` → `lex`; shared roots = roots of the content edges; «shares a content root» → matched mass > 0
- [ ] 2.2 Bump `SURAH_SIMILARITY_SCHEMA`; header names the syntactic measure and the lexical signal; update tests (`tests/test_surah_similarity*.py`) and the eval script's diagnostics (`cov` → `lex`)

## 3. Cross build (`build_quran_similarity.py`)

- [ ] 3.1 Re-derive the pre-filters with the core's exact bounds (D5); the syntax stage scores survivors with the core's `syn`; `lex` replaces `cov` in `Corpus`
- [ ] 3.2 Bump `QURAN_SIMILARITY_SCHEMA`; shared-parameter check covers the new measure names; tests incl. «no passing pair is pruned» on a random sample; eval script reads `lex`

## 4. Passage build (`build_quran_passages.py`)

- [ ] 4.1 Replace Smith–Waterman by the core's `passage_region` (candidate generation unchanged); remove the SW code and its constants (`MATCH`, `MISMATCH`, `GAP`, `TRACEBACK`); header names `passage: "dense-region"`
- [ ] 4.2 Bump `QURAN_PASSAGES_SCHEMA`; tests (pinned pairs, short formula); eval script unchanged in its reading of `k` / `wa` / `wb`

## 5. Close-verses build (`build_quran_close_verses.py`)

- [ ] 5.1 Import the content-word definition and the matching from the core (no local copy); ungated `sim` for passage-only pairs through the new `syn` / `lex`; common part = core content edges, bridging and runs unchanged
- [ ] 5.2 Bump `QURAN_CLOSE_VERSES_SCHEMA`; tests (2:3/14:31 common part unchanged, 28:20/36:20 one run, scores independent of the common part)

## 6. Readers and repo guards

- [ ] 6.1 Any reader / route / frontend type reading a renamed stored field (`cov`) follows; `quran_data/manifest.py` entries describe the new rules; `python -m pytest -q` and the frontend checks pass

## 7. Rebuild and measure (backend stopped)

- [ ] 7.1 Stop the backend; rebuild intra → cross → passages → close verses; record build times and survivor / stored counts
- [ ] 7.2 Run the four eval scripts; record every figure under «Measured result» in design.md with PASS / MISS against D9 (no parameter change after this point)
- [ ] 7.3 Restart; check in the app: sūra 2 annotations (2:3 bubble lists 14:31), the map, the «داخل السورة» groups
- [ ] 7.4 Update CLAUDE.md's closeness paragraphs (syntax measure, `lex`, dense-region passages)
