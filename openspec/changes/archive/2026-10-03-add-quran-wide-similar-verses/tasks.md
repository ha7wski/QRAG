## 1. Decisions to settle before any measurement

- [x] 1.1 Draft (Claude) `tests/eval/quran_similarity_gold.json` from verse texts alone, under the intra gold's `conventions` and drafting rule: cross-surah pairs only — positives (same meaning or subject AND near syntax: near-verbatim returns such as 3:116/58:17, 2:5/31:5, 7:73/11:61, prophets' formulas across 7/11/26), negatives of two kinds (same subject / different syntax; same syntax / different subject) — every pair with its reason; no cross-surah score computed yet
- [x] 1.2 Write the pre-registered target under this task, BEFORE the first build: recall@10 of positives, max positives lost at candidate generation, max negatives in any top-3, and 0 positives lost at the pre-filter stages — each with its a-priori justification and the gold sha256

  **Pre-registered target** — written before any cross-surah build, score, coverage or syntactic
  similarity was computed on any pair; gold sha256
  `d202178ef95a1b2a49d5f49dd7acd7b44ae5410bf29bed04982649f300272b53` (86 pairs, every one across two
  surahs: 60 positives, of which 16 verbatim identical and 2 sharing no content word; 13
  same-subject/different-syntax and 13 same-syntax/different-subject negatives). `N10(v)` is verse
  `v`'s stored cross-surah neighbour list. The parameters are the intra build's, reused (D1); nothing
  below may be met by changing them.

  - **Recall rule.** A positive `(a, b)` is recalled iff `b ∈ N10(a)` or `a ∈ N10(b)`. When `a` and
    `b` are verbatim identical (equal `quran_data.qac.ayah_words()` tuples), it is also recalled when
    `N10(a)` holds any verse verbatim identical to `b`, or `N10(b)` one identical to `a` — «وَيْلٌ
    يَوْمَئِذٍ لِلْمُكَذِّبِينَ» has ten copies in surah 77, so which of them fill 83:10's K slots is the
    tie-break, not closeness.
  - **recall@10 of positives ≥ 0.70** (≥ 42 of 60). Why: 2 positives (73:1/74:1, 81:1/82:1) share no
    content word, so the shared-root rule cannot store them; the candidate-generation budget below
    allows 12 more; and the remaining short positives (about 20 have a longer verse of ≤ 5 shown
    words) sit in moulds repeated across the whole Book («وَمَا أَدْرَاكَ مَا»، «إِذَا» + subject +
    verb, «كَذَّبَتْ» + a people), where K = 10 slots are shared with other same-mould verses that
    are close under the definition too. 0.70 is below the intra target because the competition
    for the K slots is the whole Quran instead of one surah, not because the definition changed.
  - **Positives lost at candidate generation (syntax gate + M cap) ≤ 20 %** (≤ 12 of 60). Why: no
    positive exceeds the 1/3 rule that `σ` is derived from, but six are at or within one word of it
    by their written reasons (15:11/36:30, 61:1/62:1, 7:8/23:102, 26:141/54:23, 7:141/14:6,
    7:59/23:23), and the signature charges for what the rule treats as free — a prefixed conjunction,
    a proper name against a common noun in one slot, the vocative glued to its noun (intra design D3
    «Known granularity») — so those six may fall under `σ`. The cap is where cross-surah scale bites:
    a 3–5-word verse passes the syntax gate against every same-mould verse of the Book, so its
    survivors can far exceed M = 30; a pair is kept when EITHER verse keeps it, by
    `max(dense rank, cov rank)`, and a near-verbatim pair is expected near the top of both rankings,
    so the cap is allowed the other six.
  - **Negatives in any top-3 (either direction) ≤ 4 of 26**, kinds combined and reported per kind.
    Why: the 13 same-subject/different-syntax pairs are all beyond the 1/3 rule, so the syntactic
    gate should stop them (3:10/58:17, 7 of 16 words, is the closest to the limit). The 13
    same-syntax/different-subject pairs pass that gate by construction and meet only the weaker
    semantic gate (`τ_sem = 0.125`) and the shared-root rule; four of them are in the «وَمَا أَدْرَاكَ
    مَا» / «هَلْ أَتَاكَ حَدِيثُ» moulds, whose members share their content roots and fill one
    another's top-3 almost by tie-break, so up to four may surface.
  - **Positives lost at the `length_window` and `bag_bound` pre-filters: exactly 0.** Why: both are
    exact lower bounds on the edit distance (D3), so a pair they drop has `syn < σ`. The evaluation
    computes the full `syn` of every positive; a positive whose `syn < σ` is reported as a
    `syntax_gate` loss whichever stage dropped it first, so a positive is reported at a pre-filter
    only if its `syn ≥ σ` — which is a bug in a bound or its implementation, not a measurement.

## 2. Dataset registration

- [x] 2.1 Add `QURAN_SIMILARITY_JSON` to `quran_data/paths.py` and its `manifest.py` entry (producer, inputs: `verses_final.json` + Qdrant collection + `morphology.json` + `roots_resolved.json` + `quran-morphology.txt` + `word_function.json`, consumers, rebuild command, backend-must-be-stopped note)
- [x] 2.2 Add `loaders.quran_similarity()` (lazy, cached, schema-version check, `DatasetMissing` with the rebuild command)
- [x] 2.3 Confirm `tests/test_quran_data.py` passes with the new constant and entry

## 3. Builder

- [x] 3.1 Create `scripts/build_quran_similarity.py` (`parents[N]` anchoring) importing the pure helpers and constants of `scripts/build_surah_similarity.py` (design D1); refuse to start when the embedded Qdrant lock is held
- [x] 3.2 Load signatures, content-root sets, IDF, vectors and verbatim word tuples through the intra builder's loaders; key verses by global corpus index; list `unscored` refs
- [x] 3.3 Syntactic stage (D3): elements interned to ints, length window over length-sorted verses, bag-distance bound, then `syn_similarity` on the residue; split per anchor surah (each unordered cross-surah pair once), optional `multiprocessing` pool; log examined / surviving per stage
- [x] 3.4 Dense (D4): cosine matrix, same-surah blocks masked, global cross-surah average-rank percentile via sorted array + `searchsorted`; verbatim pairs keep `dense` stored but `None` in `sem`
- [x] 3.5 Cap (`cap_pairs`, M), symmetrised cross-encoder on kept pairs, `sem` → semantic gate → shared-root rule → `score = sem × syn` → `select_neighbours` (K); ties by (surah, ayah)
- [x] 3.6 Write header (scope, models, parameters, `dense_population`, gold sha256) and file with `"s:a"` refs; checkpoint per anchor surah keyed on parameters + inputs digests; byte-identical across two builds
- [x] 3.7 `--dry-run`: print counts and elapsed time per stage up to (not including) the cross-encoder
- [x] 3.8 Document the command in `scripts/README.md`

## 4. Measurement

- [x] 4.1 Create `scripts/eval_quran_similarity.py`: recall@K, rank of each positive, positives lost per stage (`length_window`, `bag_bound`, `syntax_gate`, `candidate_cap`, `semantic_gate`, `no_shared_root`, `top_k`), negatives stored per kind; refuse a gold file whose digest differs from the header
- [x] 4.2 Run the dry run, then the build (backend stopped), then the evaluation once; record the numbers against the 1.2 target in `design.md`, a miss recorded as the result
- [x] 4.3 If anything changes afterwards, record a justification that does not cite the gold score, bump the header, rebuild — *not triggered: nothing changed after the measurement*

## 5. Backend route

- [x] 5.1 Create `retrieval/quran_similarity.py` (pure reader: one verse's neighbours + unscored flag from the loader dict; imports `quran_data` only)
- [x] 5.2 Add the response model in `api/models/` (anchor, unscored, neighbours with verse/score/roots — reuse `SimilarNeighbour`)
- [x] 5.3 Create `api/routers/quran_similarity.py` serving `GET /verse/{surah}/{ayah}/similar`, every verse through `verse_from_record`; 422 / 404 on invalid refs, 503 with the rebuild command when the dataset is missing
- [x] 5.4 Mount it in `api/main.py`; check no conflict with `GET /verse/{surah}/{ayah}`
- [x] 5.5 Tests: dataset invariants (no same-surah neighbour, no self, both gates on every entry, non-empty roots, symmetry, sort, `2:1` unscored), header parameters equal to `surah_similarity.json`'s, pre-filters exact on a random sample of dropped pairs, numpy percentile equals `percentile_ranks` on small inputs with ties, route contract, intra route unaffected when the new dataset is missing, no model resident after calls, `test_import_direction.py` and `test_module_root_depth.py` green

## 6. Frontend

- [x] 6.1 Add `getVerseQuranSimilarity(s, a)` and its types in `frontend/src/lib/api.ts`
- [x] 6.2 Add the Arabic strings (section heading «الآيات المتشابهات في سائر القرآن», no-close-verse sentence) to `lib/strings.ts`
- [x] 6.3 In `components/SurahSimilarity.tsx`, fetch the cross-surah answer in parallel with the intra one on verse pick (own sequence counter, loading line, `FailureNote`), cached under `verse-study.similar.surah.quranAnchors` keyed `"s:a"`, reset on surah change, re-issued on mount when stranded
- [x] 6.4 Render the section below the intra list: vocalized verse, Arabic surah name + ayah number, shared-root chips, no score; card opens «الآية في سياقها»; empty sentence for a scored verse with no neighbour
- [x] 6.5 Vitest: both lists render, intra shown while cross-surah is loading or failed, empty sentence, cached revisit issues no request; `npx tsc --noEmit -p tsconfig.test.json` green

## 7. Surface and docs

- [x] 7.1 Update `tests/test_served_surface.py` with `GET /verse/{surah}/{ayah}/similar`
- [x] 7.2 Update `CLAUDE.md` (route list, `retrieval/` and frontend sections)
- [x] 7.3 Manual check in the browser: surah 3 → 3:116 (58:17 in the new section), surah 55 refrain verse, surah 7 Ṣāliḥ/Hūd formulas, a verse with no cross-surah neighbour, and the intra list unchanged
