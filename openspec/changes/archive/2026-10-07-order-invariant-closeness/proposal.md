## Why

The close-verses relation still judges closeness through word ORDER at two places. The syntactic gate
`syn` is `1 − Levenshtein / longer` over the per-word QAC signature, so a block moved inside a verse
costs two edits per word; and the shared-passage relation is a Smith–Waterman alignment, which cannot
pair two words shared in a different order. 2:3 / 14:31 (the same «يقيمون الصلاة … رزقناهم ينفقون»
with «ينفقون» moved) exists only through a passage whose alignment drops the moved verb. The user's
definition: closeness SHALL be invariant to the position of lemmas and roots, while still requiring
the same syntax (syntax remains a FILTER — same subject in another construction is not close), and
weighing content roots (no tools, no stopwords) and the embeddings. Step 1
(`order-invariant-common-words`) fixed the DISPLAY with an order-invariant matching; this change makes
the relation itself order-invariant, reusing that matching.

## What Changes

- **Syntax gate, pronoun- and permutation-invariant** (version 2 — version 1's bag of bigrams was
  built, measured and closed, see the design): the signature element becomes COARSE — the stem's POS
  with the verb's aspect and voice or the noun's subcategory, the particle's tag; no prefix or suffix
  segment, no case, no mood — so a pronoun suffix, a clitic or a mood never changes it; the measure
  stays Levenshtein, with the blocks of either verse re-orderable along the lexical matching
  (`syn = max` of the plain and the two re-ordered alignments). `σ = 2/3` and the short-pair rule are
  kept as they are.
- **Lexical signal from the matching**: `cov` (IDF Jaccard of root SETS) is replaced by `lex`, the
  IDF-weighted Jaccard of the order-invariant content-word matching (same lemma 1, same root 0.5).
  `sem = (0.7·ce + 0.3·dense) × (0.25 + 0.75·lex)`; every other weight, threshold and cap unchanged.
- **Shared passages without Smith–Waterman**: a passage is the LARGEST ACCEPTED window pair of
  identical-token matches, in any order, under the current thresholds (k ≥ 6, density ≥ 0.75, ≥ 3
  content words); repeated tokens pair at the offset of the shared material (median shift of the
  unique matches), not at the same relative position.
- **Measurement protocol**: the three gold sets are RELABELLED under the written definition (permuted
  blocks are positives, not «scattered»), and a fresh blind sample of 60 cross-surah pairs is drawn
  model-free and labelled before any version-2 build; the blind figure is the one that counts, the
  relabelled gold is reported as in-sample.
- **One content-word definition** for `lex`, the passage and the displayed common part: a word whose
  root is among its verse's content roots (the set `cov` uses today) and which is not a grammatical
  tool occurrence.
- Applies to BOTH relations: intra-surah (`surah_similarity.json`, the green groups) and cross-surah
  (`quran_similarity.json`, `quran_passages.json`, `quran_close_verses.json`). All four datasets are
  rebuilt; their schemas bump; headers name the new rules.
- **BREAKING (data)**: stored per-pair fields `cov` → `lex`; the passage records keep `k`/`wa`/`wb`
  but `wa`/`wb` become the region window; Smith–Waterman is removed from the passage build.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `surah-internal-similarity`: the syntactic signature (coarse element) and similarity (block
  re-ordering) and the root signal (`lex` over the matching instead of `cov` over root sets).
- `quran-wide-similarity`: inherits both; its exact pre-filters are re-derived for the new `syn`.
- `shared-passages`: the passage becomes the largest accepted order-free region of identical-token
  matches, repeated tokens paired by median shift.
- `close-verses`: the common part's content-word definition becomes the shared one and the matching's
  tie-break becomes the median shift; measured against pre-registered targets.

## Impact

- `scripts/build_surah_similarity.py`, `scripts/build_quran_similarity.py`,
  `scripts/build_quran_passages.py`, `scripts/build_quran_close_verses.py`, the four eval scripts.
- A new shared pure module for the matching and the syntax measure (scripts-level, imported by the
  four builds — no copy).
- `quran_data/loaders.py` (schema constants), `quran_data/manifest.py`.
- Readers/routes only where a renamed stored field is read (`cov` → `lex`); no API shape change
  intended.
- Rebuild of the four datasets, backend STOPPED (embedded Qdrant lock + cross-encoder); the
  cross-surah build is the long one.
- Tests: the four build test files, eval tests, reader tests.
- Gold: `tests/eval/{surah_similarity,quran_similarity,quran_passages}_gold.json` relabelled (version
  bump); new `tests/eval/closeness_blind_v2.json`; two new scripts (draw + eval of the blind sample).
