## Context

`build_quran_similarity.py` imports the intra-surah definition (D1) and changes only the population.
The diagnostic in the proposal shows that one of the imported settings, the dense weight, does not
survive the change of population, and that two properties of the cross-surah set (very short verses,
whole-Book competition for K slots) need rules the intra build never needed.

## Decisions

All values below are frozen in this file BEFORE the gold set's second sample is labelled and before
any rebuild. None is chosen from the motivating pairs or from a measured result; the rebuild measures
them once.

### D1 — dense among the syntax survivors (A)

`dense(p)` = average-rank percentile of `cos(p)` among the cosines of every cross-surah pair that
passes the syntactic gate, B included. That is the population the semantic gate chooses within, as the
intra build's surah population is. Gold pairs outside it are ranked against the same population
(`percentile_in`). `w_ce`, `w_dense`, `floor`, `τ_sem` are unchanged: the defect is the scale dense is
expressed in, not its weight.

### D2 — exact syntax for short pairs (B)

If `max(|sig(a)|, |sig(b)|) ≤ 3`, the pair passes the syntactic gate only with `syn = 1`. Reason: with
three words one edit is the whole difference between a shared frame and a shared construction, and
the signature already treats a same-slot substitution as no difference (equal elements). This departs
from the gold drafting rule (≤ 1/3 of the words may differ) for 2–3-word verses; positives it costs are
a reported result. Applied after `σ`, so the pre-filters stay exact (they are lower bounds for the
weaker `σ` gate). Gold stage `short_exact`.

### D3 — relative cut (C)

After `select_neighbours(K)`, each verse's list keeps the entries with `s ≥ ρ · s_best`, `ρ = 0.5`
(on the stored, rounded scores). A neighbour at less than half the verse's best match is an echo of a
different order. The cut is per list: a pair dropped from u's list stays in the dataset if v's list
keeps it (the map's union, unchanged). Gold stage `relative_cut`.

### D4 — cross-surah only

The three rules live in the cross builder; the intra builder is untouched. `SHARED_PARAMS` and their
digest are unchanged, so the spec scenario «the parameters are the intra-surah ones» still holds for
the keys it lists. The header adds `dense_population`, `short_exact_max_len`, `rho`.

### D5 — gold version 2: a random, blind second sample

60 pairs drawn uniformly (seed 20261005) from the cross-surah pairs passing `σ` (the gate BEFORE B, so
B's effect is measurable), excluding v1's pairs and the three motivating pairs. Each pair is labelled
from its two verse texts only — no score, signal or list shown — by three independent labellers under
v1's definition and drafting rule (positive, neg_same_syntax_diff_subject,
neg_same_subject_diff_syntax, neg_diff_subject_diff_syntax). A label needs two votes of three; a pair
without a majority is dropped and counted. Added pairs carry `"sample": "v2-syntax-survivors"`.

### D6 — pre-registered targets

Measured once on the rebuilt dataset; a miss is recorded as the result.

- **T1** recall@10 of the 60 v1 positives ≥ 0.65 (≥ 39; today 44). B and C may cost short positives
  and weak returns; five is the tolerance.
- **T2** v1 negatives in any top-3 ≤ 4 (unchanged).
- **T3** v2 negatives stored: at most HALF the number the current build stores (baseline computed on
  the current dataset before the rebuild and written into tasks.md).
- **T4** v2 positives stored: at least 80 % of those the current build stores.
- **T5** positives lost at the pre-filters: 0.

## Risks / Trade-offs

- B changes the definition for 2–3-word verses, against the gold's 1/3 rule → accepted by the user;
  T1 bounds the cost.
- The second sample is labelled by language models, not a scholar → three blind labellers, majority,
  disagreements dropped and counted.
