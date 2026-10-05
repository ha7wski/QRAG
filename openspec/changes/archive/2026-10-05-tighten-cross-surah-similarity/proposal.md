## Why

The surah × surah map made the cross-surah pairs visible as a set, and the set holds pairs whose
verses share a construction frame but not a subject (26:203/37:54 «هل نحن منظرون» / «هل أنتم مطلعون»,
26:70/37:124, 26:115/37:15 — reported by the user on 2026-10-05). A diagnostic over the 605 stored
pairs found three causes, one of them a defect:

- **Dense carries no information across surahs.** It is the cosine's percentile among the 19 M
  cross-surah pairs, and every pair that survives the syntax gate is already near the top of that
  population: 590 of 605 stored pairs have `dense ≥ 0.95`. The `0.3·dense` term is a near-constant
  +0.3, so the semantic gate passes a pair the cross-encoder calls unrelated as soon as `cov ≥ 0.22`
  (gold negative 75:1/90:1 is stored with `ce = 0.09`). The intra build ranks dense inside one surah,
  where the candidates are spread over the population; the cross build inherited the weights without
  the property they rest on.
- **Short verses pass the syntax gate on a shared frame.** 309 of 605 pairs have a verse of ≤ 4 words;
  at `σ = 2/3` a 3-word verse passes with one construction in three changed.
- **No relative cut.** 26:70 already lists its true return 37:85 at `s = 0.83`, and still lists
  37:124 at `0.16`, because only the absolute gate applies.

## What Changes

- **A — dense ranked among the candidates.** `dense` becomes the cosine's percentile among the
  cross-surah pairs that pass the syntactic gate (the population the semantic gate actually decides
  between), not among all 19 M pairs. Header `dense_population: "syntax-survivors"`.
- **B — exact syntax for short pairs.** A pair whose LONGER signature has ≤ 3 elements must be
  syntactically identical (`syn = 1`). Header `short_exact_max_len: 3`.
- **C — relative cut.** In each verse's list, a neighbour is kept only if its score is at least
  `ρ = 0.5` × the best score of that list. Header `rho: 0.5`.
- The gold set gains a **second sample** (version 2): pairs drawn at random from the syntax-gate
  survivors, labelled from the verse texts alone by independent blind labellers, frozen before the
  rebuild. The motivating pairs are excluded from it.
- All three rules are **cross-surah only**: the intra build and `surah_similarity.json` are unchanged,
  and the parameters both builds share keep their digest.

## Capabilities

### New Capabilities

### Modified Capabilities
- `quran-wide-similarity`: the dense population, a short-pair syntax rule and a relative cut become
  part of the cross-surah definition; the gold set gains a randomly sampled, blindly labelled second
  sample.

## Impact

- `scripts/build_quran_similarity.py`, `scripts/eval_quran_similarity.py`,
  `tests/eval/quran_similarity_gold.json`, the tests of the build and the eval.
- `data/derived/quran_similarity.json` is rebuilt (backend stopped); the map, the routes and the
  frontend read it unchanged.
