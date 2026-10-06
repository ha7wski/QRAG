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

- **Syntax gate, order-robust**: `syn = ½·uni + ½·bi` — multiset overlap of the per-word signature
  elements (unigrams) and of consecutive element pairs (bigrams), each over the longer verse. A
  displaced block costs only its junctions; the construction inside each block is still measured.
  `σ = 2/3` and the short-pair rule are kept as they are.
- **Lexical signal from the matching**: `cov` (IDF Jaccard of root SETS) is replaced by `lex`, the
  IDF-weighted Jaccard of the order-invariant content-word matching (same lemma 1, same root 0.5).
  `sem = (0.7·ce + 0.3·dense) × (0.25 + 0.75·lex)`; every other weight, threshold and cap unchanged.
- **Shared passages without Smith–Waterman**: a passage is the densest window pair of identical-token
  matches, in any order (`2k − gaps` maximised), accepted with the current thresholds (k ≥ 6,
  density ≥ 0.75, ≥ 3 content words).
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
- `surah-internal-similarity`: the syntactic similarity (signature unchanged, measure order-robust)
  and the root signal (`lex` over the matching instead of `cov` over root sets).
- `quran-wide-similarity`: inherits both; its exact pre-filters are re-derived for the new `syn`.
- `shared-passages`: the passage becomes an order-free dense region of identical-token matches.
- `close-verses`: the common part's content-word definition becomes the shared one; measured against
  pre-registered targets.

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
