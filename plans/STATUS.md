# Implemented — Status

What exists and works in the codebase today. Mapped to the 8-step plan in
`architecture.md` and the feature set (F1–F6) in `project_summary.md`.

## Build steps (architecture.md) — Steps 1–8 done

### Step 1 — Setup ✅
- `docker-compose.yml` (Qdrant :6333, Ollama :11434, + backend/frontend service defs),
  `requirements.txt`, `.env.example`, `scripts/setup.sh`.
- One-command local launcher `local-dev/start.sh` / `stop.sh` (Docker + backend + frontend,
  with health checks, timing, and iCloud/startup-latency mitigations).

### Step 2 — Ingestion pipeline ✅
- `ingestion/`: `parser.py`, `normalizer.py` (Arabic diacritics/alif/ya/ta-marbuta/tatweel,
  NFC), `enricher.py` (period, surah names, juz), `translator.py`, `morphology.py`
  (root → forms/verses/count; camel-tools → tashaphyne → heuristic fallback),
  orchestrated by `run_pipeline.py`.
- Produced artifacts in `data/processed/`: `verses_raw.json`, `verses_enriched.json`,
  `verses_final.json` (with `roots` filled), `morphology.json`.
- Translations fetched into `data/translations/`: `fr_hamidullah.json`, `en_sahih.json`
  (via `scripts/fetch_translations.py`).

### Step 3 — Indexing ✅
- `indexing/`: `embedder.py` (multilingual-e5-large-instruct, 1024-dim, device auto,
  768-dim fallback), `qdrant_store.py`, `bm25_index.py` (built to `bm25_index.pkl`),
  `hybrid_search.py` (RRF), `build_index.py` (resumable, `--rebuild`).
- Embedded passage and BM25 cover Arabic + FR + EN.

### Step 4 — Base RAG pipeline ✅
- `generation/`: `llm_client.py` (Ollama + Anthropic), `prompts.py`, `chat_engine.py`
  (question → retrieval + neighbor context → streamed generation).

### Step 5 — API backend ✅
- `api/main.py` (FastAPI, shared `ChatEngine` + SQLite `Store` via lifespan, CORS, logging
  middleware).
- Routers: `chat.py` (`POST /chat`, `POST /chat/stream` SSE — both persist each turn under
  `session_id` and fall back to stored history), `search.py` (`GET /search` with
  `surah`/`period`/`juz`/`limit` filters), `lexical.py` (`POST /lexical`, `POST /lexical/stream`),
  `verse.py` (`GET /verse/{surah}/{ayah}`, `GET /surah/{number}`), `feedback.py`
  (`POST /feedback`, `GET /feedback/stats`), `sessions.py` (`GET /sessions/{id}`).
  `GET /health` reports Qdrant + LLM readiness.
- Pydantic models in `api/models/` (`chat.py`, `verse.py` incl. `VerseDetailResponse`/
  `SurahResponse`, `lexical.py`, `feedback.py`).
- Persistence: `api/store.py` — SQLite session history + feedback (`data/runtime/app.db`,
  override `APP_DB_PATH`). Unit-tested offline (`tests/test_store.py`, 7 cases).

### Step 6 — Lexical search ✅
- `retrieval/lexical_retriever.py` (root lookup via `morphology.json`) +
  `generation/lexical_analyzer.py` (LLM analysis of all occurrences) + `/lexical` endpoint.

### Step 7 — Frontend ✅
- Next.js 14 under `frontend/src/`. Pages: `/` (streaming chat + sources), `/search`,
  `/lexical`. Components: `ChatInterface`, `VerseCard`, `LexicalResult`, `ArabicText` (RTL),
  `Navbar`. `lib/api.ts` client + `lib/types.ts`.

### Step 8 — Quality layer ✅
- `retrieval/query_processor.py` (on by default), `retrieval/hyde.py` (opt-in),
  `retrieval/reranker.py` (`BAAI/bge-reranker-v2-m3`, opt-in), all wired into `chat_engine.py`
  behind env toggles.
- Evaluation harness: `tests/eval/evaluate.py` (`--rerank`), `verify_gold.py`,
  `qa_dataset.json` (50 questions: 15 ar / 15 fr / 15 en / 5 mixed), `EVAL_REPORT.md`.
  Baseline recall@10 0.277 / hit-rate 0.80 / MRR 0.433; with bge-reranker 0.343 / 0.84 / 0.561.

## Feature coverage (project_summary.md)

| Feature | State | Notes |
|---|---|---|
| **F1 — Chatbot Q&A** | ✅ Done | Streaming answers with cited sources, multilingual (ar/fr/en). Server-side session persistence + 👍/👎 feedback + health/retry resilience (2026-06-19). |
| **F2 — Lexical search / word definition** | ✅ Done | Root extraction + exhaustive occurrence retrieval + LLM analysis. The project's distinctive feature. |
| **F3 — Thematic exploration** | ❌ Not started | No `themes` enrichment, no `/themes` endpoint, no theme map UI. |
| **F4 — Translation comparison** | ⛔ Removed from scope | _(2026-06-19)_ FR/EN remain indexed and shown inline on each verse; no dedicated compare view. |
| **F5 — Study / memorization mode** | ❌ Not started | No flashcards, quiz, or progress tracking. (`transliteration` field intentionally left empty until built here.) |
| **F6 — Export & sharing** | ❌ Not started | No citation copy/PDF/share. |

Deep-linking (P1): `GET /verse/{s}/{a}` + `GET /surah/{n}` endpoints and frontend pages
`/verse/[surah]/[ayah]`, `/surah/[number]`, with clickable `VerseCard` references (2026-06-19).

## Known-good operational notes
- Project lives at `~/Projects/quran-rag` (off iCloud), symlinked from
  `~/Desktop/Tech Projects/quran-rag`. Startup ~10–20s once warm.
- Default LLM: Ollama `qwen2.5:7b`. Reranking off by default (cost). HyDE off by default.
