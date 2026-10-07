## Why

`order-invariant-closeness` (version 2) solved recall (blind sample 36/42 positives stored) but left one
precision defect, recorded and not tuned: short verses that share ONE content lemma inside the same
mould pass both gates — the coarse element makes the mould pass σ and the single shared lemma passes the
matched-mass rule — so only the semantic gate stands between them and a list (69:3/83:19
«وَمَا أَدْرَاكَ مَا X», 43:74/54:47, 81:19/86:13; nine `neg_same_syntax_diff_subject` in a top-3). In a
verse of five words or fewer the mould IS most of the verse, so one shared word is not «the same
material». The user's decision (2026-10-07): when a verse has five words or fewer, at least two shared
content lemmas are required.

## What Changes

- **Short-verse material rule**: a pair whose SHORTER verse has at most 5 QAC words is stored as close
  (intra-surah neighbour or group edge, cross-surah neighbour) only when its order-invariant matching
  holds at least 2 `lemma` content edges. Root-only edges do not count; longer pairs keep the
  matched-mass rule alone.
- A new diagnostic stage `short_material` in the intra and cross evals, between the semantic gate and
  the matched-mass rule.
- A fresh blind sample of SHORT pairs, drawn model-free and labelled before the build, measures the
  rule; the existing blind sample checks recall did not fall.
- Passages are untouched (they already require ≥ 3 content words); close verses inherit the rule
  through `quran_similarity.json`.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `surah-internal-similarity`: adds the short-verse material rule beside the matched-mass rule
  (inherited by `quran-wide-similarity`, which reuses the intra definition).

## Impact

- `scripts/closeness_core.py` (the rule, pure), `scripts/build_surah_similarity.py`,
  `scripts/build_quran_similarity.py`, the two eval scripts' stage lists, their tests.
- New `scripts/draw_short_pair_blind_sample.py`, `tests/eval/closeness_blind_short.json`; the blind
  eval script reads either sample.
- Rebuild intra → cross → close verses (backend stopped); passages unchanged.
