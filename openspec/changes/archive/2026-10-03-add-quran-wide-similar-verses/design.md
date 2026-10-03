## Context

`add-surah-similar-verses` (archived 2026-10-02) shipped «المتشابهات داخل السورة»: an offline
dataset `data/derived/surah_similarity.json` built by `scripts/build_surah_similarity.py`, served by
`GET /surah/{number}/similar[?ayah=]`, rendered by `components/SurahSimilarity.tsx`. Picking a verse
inside a group opens the anchor panel: the verse, then its close verses **of the same surah**.

Its definition of «close» is two gates — semantic (`sem = (0.7·ce + 0.3·dense) × (0.25 + 0.75·cov)`
≥ `τ_sem = 0.125`, dense ignored between verbatim verses) AND syntactic (`syn = 1 − lev/max` over the
QAC `(segs, stem)` word signature ≥ `σ = 2/3`) — with tool words out of the root signal, and a
neighbour stored only when the two verses share a content root. Its first measured build:
319 309 pairs → 971 pass the syntax gate → 778 stored; recall@10 0.80 on a 60-positive gold set.

The user asked for the same verse to show, below that list, its closest verses **across the whole
Quran**, and fixed two points: **the same definition of closeness**, and **only verses of other
surahs** (the anchor's own surah is already listed above).

The constraints are the same as the intra-surah build: the 16 GB budget (no model resident to serve
this), embedded Qdrant's exclusive lock (build with the backend stopped), the dependency order, the
dataset-registry rule, and the rule against back-fitting. The new constraint is scale: **19 113 299**
cross-surah pairs, 60× the intra-surah population.

## Goals / Non-Goals

**Goals:**
- For any scored verse, its close verses in the other 113 surahs — same two gates, same frozen
  parameters — ranked, with the shared content roots.
- Rendered under the intra-surah list when a group verse is picked; static lookup, no model at serve
  time.
- A gold set of cross-surah pairs and a pre-registered target, written before the first build.

**Non-Goals:**
- Cross-surah **groups** (e.g. a formula series spanning surahs). A different question; not built.
- Changing the definition, `σ`, `τ_sem`, the weights, `floor`, or the signature. They were frozen
  against the intra-surah gold and are reused as they stand; re-tuning them on cross-surah pairs would
  be a new decision taken after seeing data.
- Modifying `surah_similarity.json`, `GET /surah/{number}/similar`, `GET /search` or the phrase mode.
- Showing cross-surah neighbours anywhere else (verse page, phrase results, «الآية في سياقها»).
- Offering verses that are in no group: the anchor panel is still reached only from a group.

## Decisions

### D1 — A separate dataset and builder, sharing the intra-surah code

`scripts/build_quran_similarity.py` writes `data/derived/quran_similarity.json`. It **imports** the
pure helpers of `scripts/build_surah_similarity.py` — `build_signatures`, `syn_similarity`,
`passes_syntax`, `cov_similarity`, `sem_score`, `cap_pairs`, `select_neighbours`, `rnd`,
`content_root_sets` / `load_content_roots`, `load_signatures`, `load_vectors`,
`CrossEncoderScorer`, `qdrant_lock_held` and the parameter constants — rather than copying them, so
the two datasets cannot drift on the definition. Its header records the intra builder's digest of
those parameters, and a test asserts the constants are the same objects.

*Alternatives rejected*: (a) extend `surah_similarity.json` with a cross-surah list — couples the two
builds (a 2-hour cross-surah run to rebuild a 2-minute intra one) and their failure modes; (b) extract
a shared `similarity_core` package now — a refactor of a just-shipped builder, not needed for the
feature; `scripts/` already sits outside the layered packages, so a script importing a sibling script
breaks no direction rule.

### D2 — Population: every cross-surah pair of scored verses

Pairs `(u, v)` with `surah(u) ≠ surah(v)`, both scored (≥ 1 content root after the D4 tool filter of
the intra build — the same `unscored` set, 22 āyāt). Same-surah pairs are excluded by construction,
so the consecutive rule (`|Δayah| = 1`) has nothing left to exclude. Verses are keyed by their global
corpus index (0…6235) inside the build, so the intra helpers keyed on `int` work unchanged; the file
uses `"s:a"` refs.

### D3 — Syntactic gate at 19 M pairs: exact pre-filters, then the same Levenshtein

The gate is `syn ≥ σ − 1e-9`, `σ = 2/3`. Two **exact** lower bounds on the edit distance prune
without ever dropping a passing pair:

1. **Length window** — `lev(A, B) ≥ ||A| − |B||`, so `syn ≥ 2/3` requires `min/max ≥ 2/3`. Verses
   sorted by signature length; each anchor scans only the window `[⌈2n/3⌉, ⌊3n/2⌋]`.
2. **Bag distance** — `lev(A, B) ≥ max(|A ∖ B|, |B ∖ A|)` over multisets of elements. Elements are
   interned to ints once; bag sizes come from a per-verse `Counter`.

Only pairs surviving both bounds go through `syn_similarity` (the intra builder's own Levenshtein),
so the stored `syn` is computed by exactly the same function. A unit test asserts, on a random sample
of pairs, that no pair the pre-filters drop has `syn ≥ σ`. Work is split per anchor surah (`u`'s surah
< `v`'s surah, each unordered pair once) and may run in a `multiprocessing` pool; the result does not
depend on the split. `--dry-run` prints, per stage, pairs examined / surviving and the elapsed time,
so the cost is known before the cross-encoder is loaded.

*Alternative rejected*: candidates from dense / root top-N first, then the syntax gate — it would make
the dense branch a third gate (a pair with a low cosine but a high cross-encoder score would never be
seen), which the definition does not contain. *Also rejected*: adding `rapidfuzz` — a new dependency
for a build step that the exact pre-filters make affordable.

### D4 — Dense percentile over the cross-surah population

In the intra build, `dense` is a cosine's percentile among the surah's own pairs. Here the population
is **all cross-surah scored pairs**: one 6 236 × 6 236 cosine matrix (float32, ~155 MB, build time
only), the same-surah blocks masked, the upper triangle sorted once; a pair's `dense` is its average
rank `(r − 1)/(n − 1)` by `searchsorted`, the numpy equivalent of `percentile_ranks` (a test compares
the two on small inputs, ties included). Symmetric by construction; the median maps to 0.5, which is
what `τ_sem`'s justification relies on. Verbatim pairs (equal `quran_data.qac.ayah_words()` tuples)
keep the intra rule: `dense` stored, not used, `"verbatim": true`.

*Alternative rejected*: a percentile per anchor — asymmetric, so `s(u, v) ≠ s(v, u)`.

### D5 — Candidate cap, cross-encoder, storage: as the intra build

`cap_pairs(signals, M = 30)` per verse by `max(dense rank, cov rank)`; the symmetrised cross-encoder
on the kept pairs; `sem` → semantic gate → shared-root rule (`require_shared_root: true`) →
`score = sem × syn` → `select_neighbours(K = 10)`, imported unchanged. Two rules, as in the intra
build: the LISTED order is score descending, ties by global ref (surah, ayah) ascending; WHICH K are
KEPT on a tied score is the helper's «nearest index first», which across surahs favours partners in
the adjacent surahs. Kept as is (D1: the helper is reused, not forked); verbatim ties are covered by
the verbatim-class recall rule of `tasks.md` 1.2, and other ties at 4-decimal rounding are rare.
Cross-encoder calls are bounded by `≤ 6 236 × 30` pairs × 2 directions; the dry run reports the real
count. Checkpoint per anchor surah, keyed by the parameters digest and the inputs digest, like the
intra build.

### D6 — Gold set and target, frozen before the first build

`tests/eval/quran_similarity_gold.json` (local-only), drafted by Claude from verse texts alone,
before any cross-surah score exists, under the intra gold's `conventions` (same drafting rule: a
positive differs in construction in at most 1/3 of the longer verse's words). Cross-surah pairs only:
- **positives** — near-verbatim returns and formulas built alike in two surahs (e.g. 3:116 / 58:17,
  2:5 / 31:5, 7:73 / 11:61, the prophets' call «يَٰقَوْمِ ٱعْبُدُوا۟ ٱللَّهَ مَا لَكُم مِّنْ إِلَٰهٍ غَيْرُهُۥ»
  across 7 and 11 — an intra-surah pair such as 2:48 / 2:123 is not eligible);
- **negatives** — same subject / different syntax; same syntax / different subject.

Its sha256 goes into the header. `scripts/eval_quran_similarity.py` reports recall@10, each
positive's rank, the positives lost per stage (`length_window`, `bag_bound` — both must be 0 by
construction —, `syntax_gate`, `candidate_cap`, `semantic_gate`, `no_shared_root`, `top_k`) and
negatives stored; it refuses a gold file whose digest differs from the header's. The target is
written in `tasks.md` 1.2 before the run; a miss is recorded as the result. The parameters are NOT
re-derived from this gold (they are reused, D1) — it measures, it does not tune.

### D7 — Dataset shape

```json
{
  "schema": 1,
  "build": {"scope": "cross-surah", "reranker": "BAAI/bge-reranker-v2-m3", "embedder": "…",
            "K": 10, "M": 30, "w_ce": 0.7, "w_dense": 0.3, "floor": 0.25,
            "sigma": 0.6666666666666666, "tau_sem": 0.125, "signature": "segs+stem",
            "dense_on_verbatim": "ignored", "dense_population": "cross-surah",
            "require_shared_root": true, "gold_sha256": "…"},
  "unscored": ["2:1", "…"],
  "neighbours": {
    "3:116": [{"r": "58:17", "s": 0.91, "sem": 0.93, "syn": 0.98, "ce": 0.97,
               "dense": 0.99, "cov": 0.86, "roots": ["ولد", "غني", "مول", "نور", "…"]}]
  }
}
```

Neighbour lists only for verses that have at least one; ≤ 6 236 × 10 entries, estimated ≤ 3 MB.

### D8 — Route `GET /verse/{surah}/{ayah}/similar`

A new router `api/routers/quran_similarity.py`, reading through the pure reader
`retrieval/quran_similarity.py` (imports `quran_data` only) and the cached
`loaders.quran_similarity()`. Response: `{anchor: Verse, unscored: bool, neighbours:
[{verse: Verse, score, roots}]}` — every verse through `verse_from_record`, so each carries
`surah_name_ar` and `text_ar_tashkil` with the Basmala stripped. 422 for a surah outside 1–114, 404
for an ayah beyond the surah, 503 with the rebuild command when the dataset is missing.

A separate route rather than a field of `GET /surah/{n}/similar?ayah=` keeps the two datasets'
failures apart: without `quran_similarity.json` the intra view still answers. It sits under
`/verse/{s}/{a}` because its answer is about one verse and leaves the surah. No conflict with
`GET /verse/{surah}/{ayah}` (one more path segment).

### D9 — Frontend: a second list in the anchor panel

In `SurahSimilarity.tsx`, `chooseAyah` fetches both answers in parallel, each with its own sequence
counter, loading line and `FailureNote`, so a slow or failed cross-surah request never delays or
hides the intra list. Below the intra list (or its empty note), a section headed «الآيات المتشابهات
في سائر القرآن»: ranked cards, each verse vocalized with **its surah's Arabic name and ayah number**
(the intra cards need only the number; these leave the surah), shared-root chips, no score. A card
opens «الآية في سياقها». Empty: «لا آية في سائر القرآن تقاربها في المعنى والتركيب معًا». State
cached under `verse-study.similar.surah.quranAnchors`, keyed `"s:a"`, reset with the intra anchors
when the surah changes.

## Risks / Trade-offs

- **Build time** — 19 M pairs through two Python bounds, then Levenshtein on the residue, then up to
  ~374 k cross-encoder calls → the dry run reports every count before the model loads; multiprocessing
  on the syntax stage; per-surah checkpoint so an interrupted run resumes.
- **Short formulaic verses flood the candidates** (two- and three-word verses pass the length window
  against hundreds of others) → the M cap bounds cross-encoder work per verse; the shared-root rule
  and `τ_sem` still apply.
- **The parameters were frozen on intra-surah pairs** → reused deliberately (same definition, user
  decision); the cross-surah gold measures how well they transfer. A miss is a result, not a reason to
  re-tune.
- **The anchor panel grows longer** → the cross-surah list comes last, after the intra one the reader
  asked for first.
- **Build needs the backend stopped** and ~1.1 GB → refuses to start while the Qdrant lock is held.
- **Stale dataset after a corpus or index rebuild** → inputs in the manifest; header records models,
  parameters and gold digest; the loader checks the schema version.

## Migration Plan

Additive. Build the dataset (backend stopped) → start the backend → ship the frontend. If the dataset
is missing, the new route answers 503 with the rebuild command and the cross-surah section shows it,
while the intra list above renders normally. Rollback: remove the `include_router` line and the
section.

## Open Questions

- None blocking. If the dry run shows the syntax stage beyond ~2 h even with the pool, the fallback
  (to be decided then, before any score is seen) is a third exact bound, not a heuristic candidate
  filter.

## Measured result (task 4.2, first build, 2026-10-03)

Build: the intra parameters unchanged (σ = 2/3, τ_sem = 0.125, K = 10, M = 30, w_ce = 0.7,
w_dense = 0.3, floor = 0.25, signature `segs+stem`, dense ignored on verbatim), gold sha256
`d202178e…2b53` (60 positives, 13 + 13 negatives). 18 978 384 cross-surah scored pairs → 5 934 258 in
the length window → 3 709 past the bag bound → **2 257 pass the syntax gate** → 2 257 cross-encoded
(the M cap never bites: no verse has more than 30 survivors) → 606 stored pairs, 708 verses with at
least one neighbour; file 0.16 MB; 60 s end to end. The cost the Risks section feared did not
materialise: the syntax gate is far more selective across surahs than within one.

| Pre-registered target (1.2) | Measured | |
|---|---|---|
| recall@10 of positives ≥ 0.70 | 44/60 = 0.733 | PASS |
| positives lost at candidate generation ≤ 12 | 14/60 | **MISS** |
| positives lost at the pre-filters = 0 | 0 | PASS |
| non-consecutive negatives in a top-3 ≤ 4 | 4 | PASS |

Positives lost by stage: syntax gate 14 (21:2/26:5, 7:141/14:6, 3:11/8:52, 3:184/35:25, 15:11/36:30,
9:32/61:8, 3:2/27:26, 7:65/11:50, 7:59/23:23, 57:1/59:1, 61:1/62:1, 7:8/23:102, 81:19/86:13,
20:102/78:18), no shared root 2 (81:1/82:1, 73:1/74:1 — the structural loss of the kept shared-root
rule). Negatives: same-subject/different-syntax 0/13 stored; same-syntax/different-subject 4/13 stored,
all four in a top-3 (69:3/83:19, 86:2/90:12, 79:15/88:1, 75:1/90:1 — short oath / «وما أدراك»
openings, where the cross-encoder scores form over subject).

The candidate-generation miss is the D3 element's granularity against the drafting rule (the same
cause the intra change recorded), not a pre-filter fault (0 lost there). Recorded as the result; no
parameter moved (task 4.3 not triggered).

Process note: during implementation a test-timing probe ran the syntactic stage over anchor surahs
2, 3 and 77, which hold gold pairs; only aggregate survivor counts were printed, no gold-pair value
was read, and no parameter was set after it (all were reused from the intra build).
