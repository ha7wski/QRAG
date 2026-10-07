## 1. Measurement first

- [x] 1.1 `scripts/draw_short_pair_blind_sample.py` (seeded, model-free, D2 population and strata) → `tests/eval/closeness_blind_short.json`
- [ ] 1.2 Label it in a fresh context (definition + texts only), before any build
- [ ] 1.3 `scripts/eval_closeness_blind.py` takes the sample path (`--sample`), reports per stratum; refuses a digest mismatch (headers carry `blind_short_sha256`)

## 2. The rule (TDD)

- [ ] 2.1 `closeness_core.short_material_ok(edges, na, nb)` + constants; tests (69:3/83:19 refused, 55 refrain kept, root-only edges ignored, n = 6 exempt)
- [ ] 2.2 Apply it in `build_surah_similarity.py` and `build_quran_similarity.py` after the semantic gate, stage `short_material` in diagnostics and both eval scripts' stage lists; headers name the constants; tests

## 3. Rebuild and measure (backend stopped)

- [ ] 3.1 Rebuild intra → cross → close verses
- [ ] 3.2 Run the evals (short blind, blind v2, intra, cross, close verses); record under «Measured result» in design.md, PASS / MISS
- [ ] 3.3 Restart; update CLAUDE.md
