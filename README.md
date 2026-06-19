# Quran RAG

A Retrieval-Augmented Generation system over the full Quran corpus, exposed
through a conversational chatbot. It lets anyone explore the Quranic text
intelligently: understand a word in its linguistic and theological context,
find every occurrence of a concept, compare thematically related verses, and
get answers sourced directly from the text.

> **Implementation status:** the MVP is complete end to end — ingestion
> pipeline, indexing, the base RAG pipeline (retrieval + generation), the
> FastAPI backend, lexical search (root analysis), the Next.js frontend, and
> the quality layer (query processing, HyDE, cross-encoder reranking). Plus
> single-verse / full-surah endpoints and pages (deep-linking), server-side
> session persistence (SQLite), and 👍/👎 answer feedback.

---

## Project layout

```
quran-rag/
├── ingestion/        # Data pipeline: parse → normalize → enrich → morphology
├── indexing/         # Embeddings, Qdrant, BM25, hybrid (RRF) search
├── retrieval/        # RAG retrieval (later steps)
├── generation/       # LLM generation (later steps)
├── api/              # FastAPI backend
├── frontend/         # Next.js UI
├── data/
│   ├── raw/          # quran.csv (source corpus)
│   └── processed/    # generated JSON / indexes
└── scripts/          # setup / ingest / translation helpers
```

---

## Prerequisites

- Python 3.11+
- Docker + Docker Compose (for Qdrant and Ollama)

---

## Quick start

### 1. Set up the Python environment

```bash
./scripts/setup.sh
source .venv/bin/activate
```

This creates `.venv`, installs `requirements.txt`, and copies `.env.example`
to `.env`. Review `.env` and adjust as needed.

> **Note on Arabic NLP:** `camel-tools` is heavy (~2 GB of models). The
> morphology stage falls back automatically to `tashaphyne` and then to an
> internal heuristic if it is unavailable — the pipeline runs either way.

### 2. Run the ingestion pipeline

```bash
python ingestion/run_pipeline.py
# Expected: "6236 verses processed, 0 errors, morphology.json created with N roots"
```

Outputs (under `data/processed/`):

| File | Description |
|------|-------------|
| `verses_raw.json`      | Parsed verses, canonical schema |
| `verses_enriched.json` | + period, surah names (en/fr), juz |
| `morphology.json`      | Arabic root → forms / verses / count |
| `verses_final.json`    | Verses with the `roots` field filled |

### 3. Start infrastructure

```bash
docker compose up -d qdrant ollama
# Qdrant dashboard: http://localhost:6333/dashboard
```

> When running scripts on the host (outside Docker), set
> `QDRANT_URL=http://localhost:6333` in `.env`.

### 4. Build the indexes

```bash
python indexing/build_index.py            # resumable via a checkpoint
python indexing/build_index.py --rebuild  # recreate the collection
```

This embeds every verse (`intfloat/multilingual-e5-large-instruct`, 1024-dim,
cosine) into Qdrant and builds the BM25 sparse index. The first run downloads
the embedding model and can take 10–30 minutes depending on hardware.

### 5. Test hybrid search

```bash
python -c "from indexing.hybrid_search import HybridSearch; \
print(HybridSearch().search('الرحمن الرحيم', top_k=5))"
```

### 6. Run the LLM and the chat pipeline

Start Ollama and pull the model (set `OLLAMA_MODEL` in `.env`, e.g. `qwen2.5:7b`):

```bash
docker compose up -d ollama
docker exec quran-ollama ollama pull qwen2.5:7b
```

> The model needs ~5–6 GB; raise Docker Desktop's memory limit accordingly.
> Ollama in Docker on macOS is CPU-only — for Metal-accelerated speed, run
> Ollama natively instead and keep `OLLAMA_BASE_URL=http://localhost:11434`.
> Alternatively set `LLM_PROVIDER=anthropic` to use the Claude API.

CLI test of the full RAG pipeline:

```bash
python generation/chat_engine.py "What does the Quran say about patience?"
```

### 7. Run the API

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

> If port 8000 is taken, pick another (e.g. `--port 8001`).

Endpoints:

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

### 8. Run the frontend (Next.js)

```bash
cd frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL to the backend
npm install
npm run dev                         # http://localhost:3000
```

Pages: `/` (project landing), `/chat` (streaming chat + sources + 👍/👎 feedback
+ health banner), `/search` (direct verse lookup: Arabic surah picker + ayah
number → verse + context), `/lexical` (Arabic root analysis), and
`/verse/[surah]/[ayah]` + `/surah/[number]` (deep-linking, Arabic-only). The API base URL is read from
`NEXT_PUBLIC_API_URL` — `npm run dev` picks up `.env.local` automatically; for a
production `npm run build`, set the variable before building (it is inlined).
The backend must allow the frontend origin via `CORS_ORIGINS` (defaults to
`http://localhost:3000`).

---

## How retrieval works

- **Dense:** verses embedded with a multilingual E5 model, stored in Qdrant
  (cosine). Payload indexes on `surah_number`, `period`, `juz` enable filtering.
- **Sparse:** BM25Okapi over normalized Arabic text + translations.
- **Hybrid:** Reciprocal Rank Fusion combines the top-20 of each retriever:
  `score = 1/(60 + rank_dense) + 1/(60 + rank_sparse)`.

French (Hamidullah) and English (Sahih International) translations are indexed
alongside the Arabic text, so the embedded passage is
`passage: {text_ar_clean} {translation_fr} {translation_en}` and BM25 covers all
three. Fetch them with `python scripts/fetch_translations.py` (writes
`data/translations/`), then re-run the pipeline and `build_index.py --rebuild`.
Indexing translations raised retrieval hit-rate@10 from ~0.70 to ~0.90 on the
eval set.

### Quality layer (Step 8)

These shape the **retrieval query** only; the LLM always answers the user's
original question against the retrieved context. All three are wired into
`generation/chat_engine.py` behind env toggles.

- **Query processing** (`retrieval/query_processor.py`, `QUERY_PROCESSOR_ENABLED`,
  on by default): language detection, lexical/root detection, light
  morphology-based expansion (appends Arabic root surface-forms to the query),
  and inline filter detection (e.g. "makki" → `period=makkiyya`). Cheap, no LLM.
- **HyDE** (`retrieval/hyde.py`, `HYDE_ENABLED`, off by default): the LLM writes
  a hypothetical verse for the query and it is appended to the retrieval query.
  Adds one LLM call (latency) but rescues abstract questions — e.g. "creation of
  the heavens and the earth" and "kindness to parents" went from 0 gold hits to
  2–3 when HyDE was enabled.
- **Reranking** (`retrieval/reranker.py`): a cross-encoder reorders the top-20
  candidates. Opt-in via `RERANK_ENABLED=1`. The default model is the
  multilingual `BAAI/bge-reranker-v2-m3` (ar/fr/en), which vastly outperforms
  the old English-only `ms-marco`. In testing it improved every retrieval metric
  (e.g. recall@10 ~0.28→0.34, hit-rate 0.80→0.84, MRR 0.43→0.56). Recommended for
  quality; kept **off by default** only because of its cost (~2.3 GB + per-query
  CPU latency). (Lighter alternative: `BAAI/bge-reranker-base`.)

---

## Configuration

All runtime settings live in `.env` (see `.env.example`): LLM provider,
Qdrant URL/collection, embedding model and device (`auto`/`cpu`/`cuda`/`mps`),
and batch size.
