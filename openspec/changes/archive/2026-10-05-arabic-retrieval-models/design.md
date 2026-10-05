## Context

Phase 0 audit (2026-10-05), read from the code and the data, not from CLAUDE.md:

- **Dense encoder** — `indexing/embedder.py`: `EMBEDDING_MODEL` (`.env`:
  `intfloat/multilingual-e5-large-instruct`, 1024 d), fallback mpnet (768 d). Passage text
  `passage: {text_ar_clean} {translation_fr} {translation_en}`, query `query: {q}`.
  **That is the E5 v1/v2 convention.** The instruct model's card asks for
  `Instruct: {task}\nQuery: {q}` on queries and *no* prefix on documents. `text_ar_clean`
  also has hamza deleted (أشده → شده).
- **Reranker** — `retrieval/reranker.py`: `RERANK_MODEL` (default `BAAI/bge-reranker-v2-m3`),
  `CrossEncoder`, passage = raw `text_ar` (Arabic only). Chat: `RERANK_ENABLED=0`. `/search`:
  `SEARCH_RERANK_ENABLED=1` in `.env`, built lazily by `LazyReranker`.
- **`/search` has no RRF.** `api/routers/search.py` builds a candidate POOL: root candidates
  (`SimilarVerses.candidates_for`, ≤ 20) then BM25 on the stopword-cleaned query (≤ 16),
  deduped, **truncated to 32**, cross-encoder reranked, coverage-blended, AND-filtered,
  thresholded. RRF exists only in `indexing/hybrid_search.py` (the chat path: dense + BM25
  + root channel). So "a dense channel in the `/search` RRF" has to be designed: see D5.
- **BM25** — one index (`bm25_index.pkl`) over `text_ar` + FR + EN, tokenised with
  `normalize_search`. An Arabic query never matches an FR/EN token; the translations
  only change BM25's **document-length normalisation**.
- **Gold sets (all Arabic, all local-only, in `tests/eval/`)**:
  | file | n | targets / query | role today |
  |---|---|---|---|
  | `phrase_qa.json` | 27 | 1 for 22 queries, up to 13 | `/search` (`search_eval.py`) |
  | `qa_dataset.json` | 40 | ≈ 5.1 | thematic, chat retrieval (`evaluate.py`) |
  | `root_concordance_qa.json` | 30 | 11–93 | root recall, report-only here |
  A gold set exists for `/search`, so the brief's "stop and propose one" branch does not
  trigger — but it is **small**: 27 queries, mostly single-target, so a difference of one
  query moves Hit@10 by 0.037. The adoption rule below accounts for that.
- **Tafsir** — none on disk (`data/source`, `data/references`, `data/derived` searched;
  `ميسر` only matches الميسر in verse 5:90). Text variant (b) is therefore NOT run unless the
  user authorises a download (Open Questions).
- **Environment** — `sentence-transformers` 5.6, `transformers` 5.12, `torch` 2.12; HF cache
  holds only e5-large-instruct and bge-reranker-v2-m3; 28 GB free disk; 16 GB unified memory.

## Goals / Non-Goals

**Goals:**
- A reproducible benchmark whose verdict is computed by a rule frozen in this file BEFORE
  the first run.
- Integration of measured winners only, in new files, behind flags that default OFF; every
  flag OFF reproduces today's outputs byte-for-byte.
- Phase 3 rebuilds that never overwrite the current datasets.

**Non-Goals:** fine-tuning; the LLM; deleting any old model path, collection or index;
changing the chat path's encoder (measured and reported, not integrated — Open Questions);
tuning any `/search` constant (`ROOT_POOL`, `MIN_RERANK_SCORE`, `COVERAGE_FLOOR`, …).

## Decisions

### D1 — Candidates (each verified on the Hub 2026-10-05: public, not gated, safetensors present, Apache-2.0)

Encoders:
| id | dim | weights | prompt, per its card |
|---|---|---|---|
| `intfloat/multilingual-e5-large-instruct` — **E5-deployed** | 1024 | cached | `query: ` / `passage: ` (today's code) |
| same — **E5-card** | 1024 | cached | query `Instruct: {T}\nQuery: {q}`, document bare |
| `Omartificial-Intelligence-Space/GATE-AraBert-v1` | 768 | 541 MB | none |
| `Omartificial-Intelligence-Space/Arabic-Triplet-Matryoshka-V2` (GATE's base) | 768 | 541 MB | none |
| `omarelshehy/Arabic-Retrieval-v1.0` | 768 | 541 MB | `<query>: ` / `<passage>: ` |
| `Qwen/Qwen3-Embedding-0.6B` | 1024 | 1.2 GB | query `Instruct: {T}\nQuery:{q}`, document bare, `padding_side="left"` |

Rerankers:
| id | weights | loading |
|---|---|---|
| `BAAI/bge-reranker-v2-m3` — baseline | cached | `CrossEncoder` |
| `NAMAA-Space/GATE-Reranker-V1` (the "GATE-Reranker"; base GATE-AraBert-v1) | 541 MB | `CrossEncoder(max_length=512)` |
| `Omartificial-Intelligence-Space/ARA-Reranker-V1` | 2.3 GB | `CrossEncoder` |
| `Qwen/Qwen3-Reranker-0.6B` | 1.2 GB | `AutoModelForCausalLM`; score = softmax over the `yes`/`no` logits at the last position, with the card's system prefix / `<think>` suffix and `<Instruct>: {T}` |

Excluded, with the reason: **Swan-Large** — no Swan model by UBC-NLP (or any Arabic Swan) is
published on the Hub; **`Harrier-Arabic-Matryoshka-0.6B`** — exists, but declares no licence;
older Omartificial Matryoshka v1 models (`Arabert-`/`Marbert-`/`Arabic-labse-` / `E5-all-nli-…`)
— not requested by name; one line each in the candidate table if wanted.

**One instruction `T`, written once, never iterated** (iterating it against the gold set is
back-fitting): `Given an Arabic query, retrieve Quranic verses relevant to it` — in English,
as both Qwen cards recommend. E5-card and both Qwen models get the same `T`.

### D2 — Text variants (both sides normalised identically)

- **a1 `raw`** — passage `text_ar` (hamza preserved, the source has no harakat), query as typed.
- **a2 `norm`** — `arabic_text.normalize_search` on both sides (folds hamza carriers without
  deleting, strips waqf marks, ى → ي, ة → ه). Reused rather than re-implemented, per the
  `arabic_text/__init__.py` table; whether ة → ه helps or hurts a subword tokeniser trained on
  standard orthography is exactly what a1 vs a2 measures.
- **E5-deployed** is additionally run on today's exact text (`text_ar_clean` + FR + EN), so
  the table carries the production number.
- **b `+tafsir`** — not run (no tafsir on disk).

### D3 — Configurations

- **A — dense alone.** Brute-force cosine (normalised vectors, numpy) over the 6 236 verses.
  No Qdrant: the benchmark cannot touch any collection because it never opens the store.
  Vectors cached under `eval/arabic_retrieval/cache/{model}__{variant}.npy` with the model
  revision hash in the file name.
- **B — `/search` as deployed, reranker swapped.** The bench calls the **real**
  `api.routers.search.search` function with a stand-in `request.app.state` (engine with a
  `Retriever`, `similar_verses`, and a provider whose `get()` returns the candidate reranker).
  No copy of the route logic, so B cannot drift from production.
- **C — B + Arabic dense candidates** (`N_DENSE = 16`). This needs new route logic, so the
  bench holds it; its parity guard: **C with `N_DENSE = 0` must reproduce B's ranked ids on
  every gold query**, asserted before any C number is printed. Two merge strategies,
  pre-registered (see D5).
- **Report-only — chat hybrid**: `HybridSearch`-equivalent RRF (dense + BM25 + root channel)
  with each encoder, on `qa_dataset` — informs the chat Open Question, decides nothing.

### D4 — Metrics and the pre-registered adoption rule

Per query: Recall@5, Recall@10 (|top-k ∩ gold| / |gold|), MRR@10, nDCG@10 (binary gain), Hit@10;
macro-averaged. Per model: encode time for the corpus, median and p95 query latency (encode +
search, or rerank of the pool), peak memory (`torch.mps.current_allocated_memory()` +
`driver_allocated_memory()` after load and after the first batch, plus process RSS).

Significance: **paired bootstrap** over queries, 10 000 resamples, seed 0, 95 % interval on the
per-query difference of the primary metric. A candidate **wins** a decision only if
1. the lower bound of that interval is **> 0** against the reference, and
2. no guard metric drops by more than its tolerance.

| decision | reference | primary (set · metric) | guards |
|---|---|---|---|
| **D-enc** encoder for the `/search` channel | E5-card, same variant | `qa_dataset` · nDCG@10, config A | `phrase_qa` MRR@10 (A) ≥ ref − 0.02 |
| **D-chan** add the dense channel to `/search` | config B with the baseline reranker | `phrase_qa` ∪ `qa_dataset` (67 q) · nDCG@10 | `phrase_qa` Hit@10 not lower; median latency ≤ +300 ms |
| **D-rr** replace the `/search` reranker | bge-reranker-v2-m3, config B | `phrase_qa` ∪ `qa_dataset` · nDCG@10 | `phrase_qa` Hit@10 not lower; `phrase_qa` MRR@10 ≥ ref − 0.02 |

E5-card, not E5-deployed, is D-enc's reference: a new model must beat the baseline used
correctly. If E5-card itself beats E5-deployed, that is reported as its own finding (a
prompt fix the chat path could take with no model change). Among several winners the highest
primary mean is chosen; the variant (a1/a2) is part of the winner, not tuned afterwards.
D-chan is evaluated with the D-enc winner, or with E5-card if none wins. Latency and memory
are reported for every model; only D-chan gates on latency, because it adds work to every
request.

If no candidate meets the rule, the result is "keep the current models", recorded in the
report — not a reason to widen the candidate list or the instruction.

### D5 — How dense candidates enter the `/search` pool

The pool is truncated to 32 and root (≤ 20) + BM25 (≤ 16) already fill it, so appending
dense hits would usually cut them off. Two strategies, both measured, the better one by
D-chan's rule adopted:
- **C1 append** — root, then BM25, then dense, deduped; cap raised to 48 for this config only
  (more rerank pairs: its latency is reported).
- **C2 RRF-order** — the union of the three lists ordered by `Σ 1/(60 + rank)`, then capped
  at 32 (same rerank cost as today).

### D6 — Phase 2 shape (only for the decisions that won)

- `indexing/embedder_ar.py` — `EmbedderAr(model_name=EMBEDDING_MODEL_AR)`; a per-model prompt
  table (the D1 column), the D2 variant, lazy load, `_resolve_device` reused by import.
- `indexing/build_index_ar.py` — writes the collection named by `QDRANT_COLLECTION_AR`
  (default `quran_verses_ar`) through the existing `QuranQdrant(collection=…, vector_size=…)`;
  refuses to run when `QDRANT_COLLECTION_AR == QDRANT_COLLECTION`; same embedded-lock rule as
  `build_index.py` (backend stopped).
- `retrieval/reranker_ar.py` — the `Reranker` interface (`rerank(query, verses, top_k)`),
  `CrossEncoder` for the BERT rerankers, the yes/no head for Qwen3.
- `retrieval/dense_ar_channel.py` — query → ranked verse ids from the AR collection, with the
  route's filters as Qdrant payload filters.
- `api/routers/search.py` — one branch under `SEARCH_DENSE_AR_ENABLED` (default `0`), the D5
  strategy that won. `api/main.py` — a lazy provider like `LazyReranker`;
  `RERANKER_MODEL_AR` non-empty makes `LazyReranker` build `reranker_ar` instead.
- Arabic-only BM25: `bm25_index_ar.pkl` built by a new script from `text_ar` alone, new
  constant in `quran_data/paths.py` + entry in `manifest.py`; selected by
  `SEARCH_BM25_AR_ONLY` (default `0`). Built and measured in the bench first (it only changes
  length normalisation); integrated only if measured not worse on `phrase_qa`.
- `.env.example` documents every flag; `.env` is not edited by this change.

### D7 — Phase 3: rebuilds by wrapper, never by edit

The three builds hard-code `RERANKER_MODEL` and read/write fixed `paths.*` constants,
**including checkpoint directories**: re-running them with another model would silently reuse
checkpoints scored by bge. A wrapper (`eval/arabic_retrieval/rebuild.py`, local-only) imports
each script as a module, overrides `RERANKER_MODEL`, the `CrossEncoderScorer` factory, every
output path AND every checkpoint dir to `eval/arabic_retrieval/rebuild/…`, and for close
verses points the similarity input at the rebuilt file (passages are model-free and reused).
The build parameters (τ, gates, `W_CE`, K, M) were frozen against bge's score scale; they are
**kept unchanged** — retuning them for another reranker would be a new, pre-registered change,
and the report says plainly that the thresholds are uncalibrated for the new scale.

Diff report: pair-set Jaccard per dataset; per-verse top-K overlap on 50 verses drawn with
seed 0; the existing eval scripts against their gold sets where they accept an alternate input
(recorded where they refuse).

## Risks / Trade-offs

- **Small gold sets** → a real but small gain can fail the CI rule. Accepted: the rule errs
  towards keeping what works; the raw per-query JSON lets a reader see near-misses.
- **The gold sets were built with today's pipeline in view** (concordance-anchored, phrase
  sources picked by hand) → some bias towards lexical/root retrieval; a dense model may be
  under-rewarded on paraphrase. Reported, not corrected here.
- **Memory** → MPS-wired weights don't show in RSS; the bench loads one model at a time,
  `del` + `gc.collect()` + `torch.mps.empty_cache()` between models, and refuses to start if
  the backend port answers or Ollama has a model loaded.
- **Qwen3-Reranker on MPS** → fp32 0.6 B causal LM over a 32-pair pool may be slow; measured,
  and D-rr has no latency gate, so the report must make it visible.
- **Two collections in one embedded store** → same lock, ~24 MB more; no interference with
  `quran_verses`.

## Migration Plan

Nothing migrates by default. Turning the path on = build the AR collection, set the flags in
`.env`, restart. Rollback = unset the flags. Removal of the old path is out of scope.

## Clarifications fixed before the first benchmark run (2026-10-05)

Written after the live `/search` baseline was captured (`eval/arabic_retrieval/
live_search_*_before.*`, today's production numbers: phrase_qa Hit@10 0.963, MRR@10 0.909)
and before any candidate was measured. They make the text above executable, without
changing what it measures.

- **Parity (D3, config C).** The route's comparison stage is copied into the bench; the
  check that the copy is faithful is: **C1 with `N_DENSE = 0` and cap 32** returns B's ranked
  ids on every gold query, for every reranker. (C2 with no dense list re-orders the pool by
  RRF, so it is by construction not B.) B itself is checked against the ids the live backend
  returned before it was stopped.
- **Encoder for C when D-enc has no winner**: E5-card in whichever variant (a1/a2) has the
  higher config-A `qa_dataset` nDCG@10.
- **C's latency** = the route's own time + that encoder's measured single-query encode time
  (median) + the brute-force dense search; encoders and rerankers run in separate processes so
  only one model is resident.
- **Arabic-only BM25 "not worse" (D6)**: on `phrase_qa`, in config B with bge, mean nDCG@10
  ≥ the reference's AND Hit@10 ≥ the reference's.
- Rerankers score the same passage as production (`retrieval.reranker._passage_text`, raw
  `text_ar`); the D2 variants apply to encoders only. CrossEncoder rerankers run through the
  production `retrieval.reranker.Reranker` class; only Qwen3 needs its own adapter.
- Every model is loaded from a downloaded snapshot directory, so the commit hash recorded in
  the results is the one that ran. All encoders use `max_seq_length = 512`; truncations are
  counted and reported.

## Resolved Questions (user, 2026-10-05)

1. **Tafsir variant (b)**: not run, nothing downloaded.
2. **Chat path**: out of this change, and not scheduled (user, 2026-10-05: "pour l'instant
   on ne traite pas le chat"). `quran_verses_ar` stays ready for it; nothing else is prepared. The report-only chat-hybrid configuration of D3 is dropped accordingly.
3. **Adoption rule**: D4 accepted as written, with D1's candidates, the instruction `T` and
   D5's strategies. Frozen from this point; no benchmark number existed when it was accepted.

## D8 — Phase 2 as validated (user, 2026-10-05), superseding D6

Scope: the C-rrf channel only. Three conditions from the user:

1. **One E5 in the process.** The channel does not load a model: it borrows the chat's lazy
   `HybridSearch.embedder` (`app.state.engine.retriever.hybrid`) and the same embedded Qdrant
   client (`hybrid.qdrant.client` — a second `QdrantClient(path=…)` on the same directory would
   hit the exclusive lock anyway). Whichever of chat or `/search` runs first pays for E5 once.
   There is no `EMBEDDING_MODEL_AR`: the encoder is `EMBEDDING_MODEL`, and the channel abstains
   (logs once, returns no ids → the route's old pool) when the shared embedder's model is not
   the one the collection was built with.
2. **`quran_verses_ar` is built for the chat fix too.** Same point ids (`point_id`), same
   payload (`qdrant_store._payload`) and the same three payload indexes as `quran_verses`, so
   `HybridSearch`'s dense branch can later point at it by collection name and query with
   `indexing.embedder_ar.query_text` — no re-indexing. Each point also carries `emb_model` and
   `emb_format` (`e5-instruct-card/normalize_search/v1`), the contract a reader checks.
   `indexing/embedder_ar.py` holds that contract (instruction `T`, passage and query formatting)
   and loads nothing.
3. **Old collection and old path kept**; `SEARCH_DENSE_AR_ENABLED=0` by default; with it off
   `app.state.search_dense_ar` is None and the route runs today's code.

Route (`api/routers/search.py`): when the channel returns ids, the pool is the union of root,
BM25 and dense lists ordered by `Σ 1/(60 + rank)` (insertion order root → BM25 → dense breaks
ties, as in the bench) and capped at `SEARCH_RERANK_POOL_MAX`; everything after the pool is
unchanged. When it returns nothing (off, failed, abstained), the old pool is built exactly as
before. New env: `SEARCH_DENSE_AR_ENABLED` (0), `QDRANT_COLLECTION_AR` (`quran_verses_ar`),
`SEARCH_DENSE_AR_POOL` (16). `GET /health`'s existing `models.embedder` already reports the
shared encoder's residency; nothing is added there.

Verification: route-with-flag vs the bench's C-rrf ids on the 97 gold queries, and resident
memory of the backend measured with the flag on and off.
