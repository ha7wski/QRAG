## Why

Every user query is, and will stay, Arabic — yet the retrieval stack is multilingual: the
dense encoder (`intfloat/multilingual-e5-large-instruct`) embeds `text_ar_clean` glued to
the French and English translations, the BM25 index tokenises all three languages, and the
cross-encoder (`BAAI/bge-reranker-v2-m3`) was chosen for being multilingual, not for being
good at Classical Arabic. Arabic-specialised encoders and rerankers now exist with open
weights. Whether any of them does better **on this corpus** is unknown, and this project
does not adopt a model on a model card's word: a candidate is adopted only if it beats the
current one on the Arabic gold sets already on disk, under a rule frozen before the first run.

The Phase 0 audit also found that the baseline itself is mis-prompted: the code sends E5
v1/v2 prefixes (`query: ` / `passage: `) to an *instruct* model whose card asks for
`Instruct: {task}\nQuery: {q}` on queries and **no** prefix on documents. A fair comparison
has to measure that baseline both as deployed and as documented — otherwise a new model
would be credited for fixing a prompt bug.

## What Changes (as proposed — see "Outcome of Phase 1" for what was built)

- **Phase 1 — a benchmark, no production impact.** A new local-only script measures every
  candidate encoder and reranker (identifiers verified on Hugging Face, see design.md)
  against the three Arabic gold sets, in three configurations: dense alone, the current
  `/search` pipeline, and `/search` with an added Arabic dense candidate channel. Brute-force
  cosine over the 6 236 verses in memory: **no Qdrant collection is created or opened**.
  Output: a Markdown comparison table + raw JSON, with the adoption verdict computed by a
  rule pre-registered in design.md.
- **Validation gate.** Nothing past Phase 1 starts until the user has read the table.
- **Phase 2 — integrate measured winners only, behind flags, default OFF.** New files
  `indexing/embedder_ar.py`, `retrieval/reranker_ar.py`, an Arabic-only index build into a
  **new** Qdrant collection (`QDRANT_COLLECTION_AR`), and an Arabic dense candidate channel in
  `/search`. New env: `EMBEDDING_MODEL_AR`, `QDRANT_COLLECTION_AR`, `RERANKER_MODEL_AR`,
  `SEARCH_DENSE_AR_ENABLED`, plus a flag selecting an Arabic-only BM25 index. Existing
  modules, the `quran_verses` collection and `bm25_index.pkl` are not modified; rollback is a
  `.env` edit.
- **Phase 3 — similarity builds re-run with the winning reranker, to NEW files.** The three
  `build_*` scripts are driven by wrappers that override the model and output path, never by
  editing them; the old outputs are never overwritten; a sampled diff is reported.
- **Not changed:** default behaviour of every route, the LLM, fine-tuning, deletion of any
  old code or collection.

## Capabilities

### New Capabilities
- `arabic-retrieval-benchmark`: the pre-registered, reproducible comparison of encoders and
  rerankers on the Arabic gold sets — candidates, text variants, configurations, metrics,
  adoption rule, outputs.
- `arabic-retrieval-channel`: the flag-gated Arabic encoder/reranker modules, the separate
  Qdrant collection and Arabic-only BM25 index, and the dense candidate channel in `/search`;
  every flag OFF reproduces today's behaviour exactly.

### Modified Capabilities
<!-- None: with every new flag OFF (the default), no existing requirement changes. A later
     change that flips a default would modify `verse-study` / `close-verses`. -->

## Outcome of Phase 1 (2026-10-05)

No reranker and no Arabic-specialised encoder won; the only win is the dense channel C-rrf
using **E5 itself**, prompted per its card on `normalize_search`-ed Arabic text. Phase 2 is
therefore reduced, at the user's direction, to that channel (design D8), and Phase 3 does not
happen (it was conditional on a reranker win) — the `arabic-similarity-rebuild` capability is
withdrawn. `reranker_ar.py`, `RERANKER_MODEL_AR`, `EMBEDDING_MODEL_AR` and the Arabic-only BM25
flag are not created.

## Impact

- **New code:** `tests/eval/bench_arabic_retrieval.py` (local-only, beside the gold sets it
  reads); conditionally `indexing/embedder_ar.py`, `indexing/build_index_ar.py`,
  `retrieval/reranker_ar.py`, `retrieval/dense_ar_channel.py`, wrapper scripts for Phase 3.
- **Touched only to add a flag-gated branch (Phase 2):** `api/routers/search.py`,
  `api/main.py` (lazy provider), `quran_data/paths.py` + `manifest.py` (the Arabic BM25 file),
  `.env.example`.
- **Downloads (Phase 1):** ~5–6 GB of weights into the HF cache (largest: two 0.6 B Qwen3
  models at 1.2 GB each, `ARA-Reranker-V1` at 2.3 GB). Disk has 28 GB free.
- **Memory:** benchmark runs with the backend and Ollama STOPPED, one model resident at a
  time, on MPS (16 GB unified memory — see CLAUDE.md's memory budget).
- **Dependencies:** none new (`sentence-transformers` 5.6, `transformers` 5.12 satisfy the
  Qwen3 cards' `>= 4.51` requirement).
