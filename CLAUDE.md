# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Retrieval-Augmented Generation system over the full Quran (6236 verses), exposed as a
conversational chatbot plus a lexical (Arabic-root) analysis tool. Vision in
`project_summary.md`, full design in `architecture.md` (both are the *intended* design and
run ahead of the code — verify against the actual modules). Current implementation status
and remaining work live in `plans/`.

All code, comments, and docs are in **English**.

## Commands

```bash
# One-command local launcher (Qdrant + Ollama + backend + frontend, opens the browser)
./local-dev/start.sh                 # backend :8001, frontend :3000
./local-dev/stop.sh                  # stop app; --all also stops Docker services
REBUILD=1 ./local-dev/start.sh       # force a frontend rebuild (auto-rebuilds on source change otherwise)

# Python env (creates .venv, installs requirements.txt, copies .env.example -> .env)
./scripts/setup.sh && source .venv/bin/activate

# Data pipeline: data/raw/quran.csv -> data/processed/*.json  (parse→normalize→enrich→morphology)
python ingestion/run_pipeline.py
python scripts/fetch_translations.py # refresh data/translations/ (fr Hamidullah, en Sahih)

# Build indexes: embeds every verse into Qdrant + builds the BM25 sparse index
python indexing/build_index.py            # resumable via checkpoint
python indexing/build_index.py --rebuild  # recreate the Qdrant collection

# Exercise pieces directly (most modules have a __main__ smoke test)
python -c "from indexing.hybrid_search import HybridSearch; print(HybridSearch().search('الرحمن الرحيم', top_k=5))"
python generation/chat_engine.py "What does the Quran say about patience?"
uvicorn api.main:app --host 127.0.0.1 --port 8000   # run the API alone

# Unit tests (pure logic, offline — no Qdrant/Ollama/network)
python -m pytest -q                      # backend: normalizer, RRF fusion, root lookup
cd frontend && npm test                  # frontend: conversations.ts (Vitest); npm run test:watch to watch

# Retrieval evaluation (50-question gold set in tests/eval/qa_dataset.json)
python tests/eval/evaluate.py            # baseline hybrid
python tests/eval/evaluate.py --rerank   # + bge cross-encoder reranker
python tests/eval/verify_gold.py         # check every gold verse exists in the corpus
```

Tests: backend pytest lives in `tests/test_*.py` (config in `pytest.ini`, `pythonpath=.`); deps
are the minimal `requirements-test.txt`, not the full ML stack. Frontend tests use Vitest
(`frontend/vitest.config.ts`, jsdom); test files are excluded from `tsconfig` so `next build`
ignores them. `tests/eval/` holds the separate retrieval-evaluation harness (scripts, not pytest).
CI runs both on push (`.github/workflows/test.yml`).

## Architecture

Four decoupled layers, each replaceable without refactoring the others. The request flows
ingestion → indexing → retrieval → generation → API → frontend.

- **`ingestion/`** — `run_pipeline.py` orchestrates parser → normalizer → enricher →
  (translator) → morphology, writing `data/processed/{verses_raw,verses_enriched,verses_final}.json`
  and `morphology.json` (Arabic root → forms / verse-ids / count). `morphology.json` is what
  powers lexical search. Arabic NLP degrades gracefully: camel-tools → tashaphyne → internal
  heuristic, so the pipeline runs even without the heavy CAMeL models. The verse — not a token
  window — is the atomic unit; two Arabic forms are kept per verse: `text_ar` (with harakat,
  for display) and `text_ar_clean` (no diacritics, for search).

- **`indexing/`** — `embedder.py` (multilingual E5, 1024-dim; device auto→mps/cuda/cpu;
  falls back to a 768-dim model on load failure) + `qdrant_store.py` + `bm25_index.py`, fused
  by `hybrid_search.py` via Reciprocal Rank Fusion: `1/(60+rank_dense) + 1/(60+rank_sparse)`
  over the top-20 of each retriever. The embedded passage is
  `passage: {text_ar_clean} {translation_fr} {translation_en}` and BM25 covers all three
  languages — indexing translations raised hit-rate@10 from ~0.70 to ~0.90.

- **`retrieval/`** — `retriever.py` wraps `HybridSearch`, returns full verse records, and can
  expand each hit with neighbor verses (same surah, ±window) for LLM context. `lexical_retriever.py`
  is the separate root-lookup path. The **quality layer** shapes only the *retrieval query*:
  `query_processor.py` (language/root detection, morphology expansion, inline filter detection;
  on by default), `hyde.py` (LLM writes a hypothetical verse; off by default), `reranker.py`
  (cross-encoder `BAAI/bge-reranker-v2-m3`, opt-in). Toggled by env: `QUERY_PROCESSOR_ENABLED=1`,
  `HYDE_ENABLED=0`, `RERANK_ENABLED=0`.

- **`generation/`** — `chat_engine.py` is the orchestrator: question → query shaping → hybrid
  retrieve (+ neighbors) → LLM. **Key invariant:** QueryProcessor/HyDE change only what is
  *retrieved*; the LLM always answers the user's ORIGINAL question against the retrieved
  context. `llm_client.py` abstracts Ollama (local, default `qwen2.5:7b`) vs Anthropic
  (`claude-sonnet-4-6`) behind one interface, switched by `LLM_PROVIDER`. `lexical_analyzer.py`
  runs the root-occurrence analysis. Prompts live in `prompts.py`.

- **`api/`** — `main.py` builds **one shared `ChatEngine`** plus a SQLite `Store`
  (`api/store.py`) at startup (FastAPI lifespan) and exposes them via `app.state.engine` /
  `app.state.store`; routers reuse them. Implemented routes: `GET /health`, `GET /search`,
  `POST /chat` + `POST /chat/stream` (SSE, both persist each turn under `session_id`),
  `POST /lexical` + `POST /lexical/stream`, `GET /verse/{surah}/{ayah}`, `GET /surah/{number}`,
  `GET /surahs` (picker metadata), `POST /feedback` + `GET /feedback/stats`, `GET /sessions/{id}`.
  The `/themes` endpoint in `architecture.md` is **not** implemented. The store DB lives at `data/runtime/app.db`
  (override `APP_DB_PATH`).

- **`frontend/`** — Next.js 14 (App Router) under `frontend/src/`. Pages: `/` (project landing /
  feature presentation), `/chat` (streaming chat + sources + 👍/👎 feedback + health banner; opens
  a fresh chat — saved conversations are reopened only via the switcher), `/search` (direct verse
  lookup: Arabic surah picker + ayah number → verse + context), `/lexical` (root analysis),
  `/verse/[surah]/[ayah]` + `/surah/[number]`
  (deep-linking; `VerseCard` references are clickable). `lib/api.ts` is the backend client; the base URL is
  `NEXT_PUBLIC_API_URL` (read at build time, inlined). Arabic text is RTL via `ArabicText.tsx`;
  the rest of the UI is LTR.

## Conventions & gotchas

- **Path anchoring:** every module computes `ROOT = Path(__file__).resolve().parents[N]` and
  `sys.path.insert(0, ...)` rather than relying on cwd — keep this pattern, scripts must run
  from anywhere.
- **Data must exist before running anything retrieval-related.** Backend and `HybridSearch`
  load `data/processed/verses_final.json` + `bm25_index.pkl`; `build_index.py` must have
  populated Qdrant. `start.sh` checks for these and tells you which pipeline step to run.
- **Two ports for the backend:** the README/standalone examples use `:8000`; `local-dev/start.sh`
  uses `:8001` (and writes `frontend/.env.local` to match). Don't assume one.
- **Config is all env** (`.env`, see `.env.example`): `LLM_PROVIDER`, `OLLAMA_*`/`ANTHROPIC_*`,
  `QDRANT_URL` (use `http://localhost:6333` on the host, `http://qdrant:6333` in Docker),
  `EMBEDDING_MODEL`/`EMBEDDING_DEVICE`, and the three quality toggles above.
- **`local-dev/start.sh` runs the frontend in production mode** (`next build` once, then
  `next start`) and sets `HF_HUB_OFFLINE=1` (when the model is cached) and
  `PYTHONPYCACHEPREFIX` to a non-iCloud cache — both are startup-latency fixes; preserve them.
- **Eval gotcha:** `evaluate.py --rerank` while the backend is up can OOM-kill Qdrant (two
  e5-large models + the reranker). Stop the backend first.
- **Reranking is off by default for cost, not quality** — it improves every metric on the eval
  set (see `tests/eval/EVAL_REPORT.md`); enable with `RERANK_ENABLED=1` when quality matters.
