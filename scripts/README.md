# Running Quran RAG

Operational guide: prerequisites, one-time setup, and launching the app from a
fresh clone. For the project overview (features, architecture, retrieval design)
see the top-level [`README.md`](../README.md). **Run all commands from the repo
root.**

## Prerequisites

- Python 3.11+
- Docker + Docker Compose (for Qdrant and Ollama)
- Node.js 18+ (for the frontend)

## What ships vs. what's generated

The repo contains the source and the `data/raw/quran.csv` corpus. The processed
data (`data/processed/`), the fetched translations (`data/translations/`), and
the Qdrant + BM25 indexes are **built locally** — they are not committed, so the
one-time build below is required after cloning.

## One-time setup

```bash
# 1. Python env (.venv) + install deps + create .env from .env.example
./scripts/setup.sh && source .venv/bin/activate

# 2. Edit .env for a HOST run (the example targets Docker hostnames):
#      QDRANT_URL=http://localhost:6333
#      OLLAMA_BASE_URL=http://localhost:11434
#      OLLAMA_MODEL=qwen2.5:7b        # or LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY

# 3. Start Qdrant + Ollama, then pull the LLM weights (~4.7 GB)
./scripts/start_dev.sh
docker exec quran-ollama ollama pull qwen2.5:7b

# 4. Build the data + indexes (translations → pipeline → embeddings)
python scripts/fetch_translations.py    # FR/EN; skip → Arabic-only retrieval
python ingestion/run_pipeline.py        # data/raw/quran.csv → data/processed/
python indexing/build_index.py          # embeds into Qdrant + BM25 (first run slow)
```

## Launch (one command)

```bash
./scripts/run.sh
```

Starts Qdrant + Ollama (Docker), the backend (`:8000`) and the frontend
(`:3000`), waits until both are ready, and opens the browser. It refuses to
start if the indexes aren't built (and prints the build commands). Ctrl+C stops
the app; Docker keeps running. Override ports with
`BACKEND_PORT=8001 FRONTEND_PORT=3001 ./scripts/run.sh`.

---

## Run each component yourself

Useful for development or to understand each layer.

### Ingestion pipeline

```bash
python ingestion/run_pipeline.py    # or ./scripts/ingest.sh
# Expected: "6236 verses processed, 0 errors, morphology.json created with N roots"
```

Outputs (under `data/processed/`):

| File | Description |
|------|-------------|
| `verses_raw.json`      | Parsed verses, canonical schema |
| `verses_enriched.json` | + period, surah names (en/fr), juz |
| `morphology.json`      | Arabic root → forms / verses / count |
| `verses_final.json`    | Verses with the `roots` field filled |

> **Arabic NLP fallback:** `camel-tools` is heavy (~2 GB) and optional. The
> morphology stage falls back to `tashaphyne`, then an internal heuristic — the
> pipeline runs either way.

### Build the indexes

```bash
python indexing/build_index.py            # resumable via a checkpoint
python indexing/build_index.py --rebuild  # recreate the Qdrant collection
```

Embeds every verse (`intfloat/multilingual-e5-large-instruct`, 1024-dim, cosine)
into Qdrant and builds the BM25 sparse index. The first run downloads the
embedding model and can take 10–30 minutes depending on hardware.

### Smoke-test hybrid search

```bash
python -c "from indexing.hybrid_search import HybridSearch; \
print(HybridSearch().search('الرحمن الرحيم', top_k=5))"
```

### Run the chat pipeline (CLI)

```bash
python generation/chat_engine.py "What does the Quran say about patience?"
```

> The Ollama model needs ~5–6 GB RAM; raise Docker Desktop's memory limit
> accordingly. Ollama in Docker on macOS is CPU-only — for Metal-accelerated
> speed run Ollama natively and keep `OLLAMA_BASE_URL=http://localhost:11434`.
> Or set `LLM_PROVIDER=anthropic` to use the Claude API.

### Run the API

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000   # pick another port if 8000 is taken
```

| Method | Path           | Description |
|--------|----------------|-------------|
| GET    | `/health`      | Readiness: `{status, qdrant, llm}` |
| GET    | `/search`      | Hybrid search: `?q=...&surah=&period=&juz=&limit=` |
| POST   | `/chat`        | Full answer + sources (JSON); persists the turn under `session_id` |
| POST   | `/chat/stream` | Token stream as Server-Sent Events |
| POST   | `/lexical`     | Root analysis of a word: `{word, language}` → forms, occurrences, analysis, verses |
| POST   | `/lexical/stream` | Streaming root analysis (SSE) |
| GET    | `/verse/{surah}/{ayah}` | One verse + neighbor context + adjacent ids (`?window=`) |
| GET    | `/surah/{number}` | Full surah: ordered verses + metadata |
| GET    | `/surahs`      | All 114 surahs (number, names, ayah count) for pickers |
| POST   | `/feedback`    | Record 👍/👎 on an answer; returns running stats |
| GET    | `/feedback/stats` | Aggregate feedback counts |
| GET    | `/sessions/{id}` | Server-persisted chat history for a session |

```bash
curl "http://127.0.0.1:8000/search?q=%D8%A7%D9%84%D8%B5%D8%A8%D8%B1&surah=2&limit=3"

curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Que dit le Coran sur la patience ?"}]}'

curl -X POST http://127.0.0.1:8000/lexical -H "Content-Type: application/json" \
  -d '{"word":"رحمة","language":"fr"}'
```

### Run the frontend (Next.js)

```bash
cd frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL to the backend
npm install
npm run dev                         # http://localhost:3000
```

Pages: `/` (project landing), `/chat` (streaming chat + sources + 👍/👎 feedback
+ health banner), `/search` (direct verse lookup: Arabic surah picker + ayah
number → verse + context), `/lexical` (Arabic root analysis), and
`/verse/[surah]/[ayah]` + `/surah/[number]` (deep-linking, Arabic-only). The API
base URL is read from `NEXT_PUBLIC_API_URL` — `npm run dev` picks up `.env.local`
automatically; for a production `npm run build`, set the variable before building
(it is inlined). The backend must allow the frontend origin via `CORS_ORIGINS`
(defaults to `http://localhost:3000`).

---

## Scripts reference

| Script | What it does |
|--------|--------------|
| `scripts/setup.sh` | Create `.venv`, install `requirements.txt`, copy `.env.example` → `.env` |
| `scripts/start_dev.sh` | `docker compose up -d qdrant ollama` |
| `scripts/fetch_translations.py` | Download FR (Hamidullah) + EN (Sahih) translations → `data/translations/` |
| `scripts/ingest.sh` | Run the ingestion pipeline (wrapper for `ingestion/run_pipeline.py`) |
| `scripts/run.sh` | One-command launcher: Qdrant + Ollama + backend + frontend |

## Gotchas

- **`.env` hostnames:** `.env.example` uses Docker-internal hostnames
  (`qdrant:6333`, `ollama:11434`). For host runs (uvicorn/scripts on your
  machine), switch them to `localhost` — this is the most common first error.
- **First run is heavy:** the embedding model (~1–2 GB) and `qwen2.5:7b`
  (~4.7 GB) download on first use; keep ≥ 8 GB RAM free.
- **Two backend ports:** examples here use `:8000`; `run.sh` defaults to `:8000`
  too but is overridable. Keep `NEXT_PUBLIC_API_URL` in sync with whichever you use.
