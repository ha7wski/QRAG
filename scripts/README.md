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

`data/` is organized by what a file **is**, and that is also the ship/build rule:

| Bucket | Holds | Committed? |
|--------|-------|-----------|
| `data/source/` | Third-party originals the project never rewrites — `quran.csv`, `quran_chakl.csv`, the QAC morphology, the treebank | yes (except `source/maqayis/`, see below) |
| `data/references/` | Curated scholarship, each file carrying a human decision | yes |
| `data/derived/` | Anything a script can rebuild: the processed corpus, the QAC indexes, the fetched translations, the BM25 index | **no — built locally** |
| `data/runtime/` | Mutable state the running app owns: the SQLite store, the embedded Qdrant collection | **no** |

So the one-time build below is required after cloning: it fills `data/derived/`
and populates Qdrant. `data/source/maqayis/` is the single documented departure
— a large re-downloadable original that is git-ignored while its curated
derivative `data/references/maqayis_asl.csv` ships.

**Every dataset's provenance lives in `quran_data/manifest.py`** — what it is,
where it came from (upstream project + URL, or the fetching script), which step
writes it, who reads it, whether it is regenerable and with which exact command.
Consult it there rather than re-deriving it from this page; it is also what the
loaders read to tell you what to run when a file is missing.

## One-time setup

```bash
# 1. Python env (.venv) + install deps + create .env from .env.example
./scripts/setup.sh && source .venv/bin/activate

# 2. Edit .env for a HOST run (the example targets Docker hostnames):
#      QDRANT_PATH=data/runtime/qdrant   # run Qdrant embedded — no container at all
#      QDRANT_URL=http://localhost:6333  # only if you leave QDRANT_PATH empty
#      OLLAMA_BASE_URL=http://localhost:11434
#      OLLAMA_MODEL=qwen2.5:7b        # or LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY

# 3. Start Ollama, then pull the LLM weights (~4.7 GB)
./scripts/start_dev.sh                  # Ollama only; Qdrant runs embedded
docker exec quran-ollama ollama pull qwen2.5:7b

# 4. Build the data + indexes (translations → pipeline → embeddings)
python scripts/fetch_translations.py    # FR/EN; skip → Arabic-only retrieval
python ingestion/run_pipeline.py        # data/source/quran.csv → data/derived/
python indexing/build_index.py          # embeds into Qdrant + BM25 (first run slow)
```

## Launch (one command)

```bash
./scripts/run.sh
```

Starts Ollama (Docker), the backend (`:8000`) and the frontend (`:3000`), waits
until both are ready, and opens the browser. It brings up the Qdrant container
only when `QDRANT_PATH` is empty — with it set, Qdrant runs embedded in the
backend and there is nothing to start. It refuses to start if the indexes aren't
built (and prints the build commands). Ctrl+C stops
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

Outputs land in `data/derived/`. The ones the runtime actually loads:

| File | Description |
|------|-------------|
| `verses_final.json`    | **The serving corpus** — verses with the `roots` field filled; the backend and the indexer both load it |
| `morphology.json`      | Arabic root → forms / verses / count; powers lexical search and Verse Study |
| `qac_resolution.json`  | `form_to_roots` + `lem_to_roots` — resolves a typed word to its root(s) |
| `verses_raw.json`, `verses_enriched.json` | Stage snapshots, same schema as `verses_final`; nothing reads them |

The QLisan / Tahlīl stages write several more (`qac_words.json`,
`qac_syntax.json`, `root_graph.json`, `word_index.json`, `lemma_index.json`,
`proper_nouns.json`, `roots_resolved.json`). Rather than list them twice, see
`quran_data/manifest.py` — one entry per dataset, with its producer, its
consumers, and its rebuild command.

> **Roots come from the Quranic Arabic Corpus**, not from a stemmer:
> `data/source/quran-morphology.txt` ships manually-verified roots in native
> Arabic. `camel-tools` is therefore **not** a dependency (it is ~2 GB), and the
> legacy `tashaphyne` stemmer in `ingestion/morphology.py` is left in place but
> unused — an optional fallback behind `QAC_STEMMER_FALLBACK=1`, off by default
> because it mis-roots (`كريم` → `ريم` instead of `كرم`).

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

> The Ollama model needs ~5–6 GB RAM. Run Ollama **natively**, not in Docker:
> Docker on macOS has no access to the Metal GPU, so a containerized model runs
> on CPU (~2 tok/s) *and* forces you to hand that memory to the Docker VM. Keep
> `OLLAMA_BASE_URL=http://localhost:11434`, or set `LLM_PROVIDER=anthropic` to
> use the Claude API and load nothing locally.
>
> **Do not raise Docker Desktop's memory limit to fit the model** — that is the
> opposite of what you want. Whatever you give the VM is taken from the host,
> where the native model and the embedders actually live. Qdrant is the only
> container here and it serves ~24 MB of vectors: 4 GB is already generous, and
> `QDRANT_PATH` removes the VM from the picture entirely (see Gotchas).

### Run the API

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000   # pick another port if 8000 is taken
```

This is the whole served surface — every route below has a caller in the
frontend, and nothing else is mounted:

| Method | Path           | Description |
|--------|----------------|-------------|
| GET    | `/health`      | Readiness: `{status, qdrant, llm, models, qdrant_location}` |
| GET    | `/search`      | Similar-verse search: `?q=...&surah=&period=&juz=&limit=` |
| POST   | `/chat/stream` | Token stream as Server-Sent Events; persists the turn under `session_id` |
| POST   | `/lisan/analyze` | Letter-level reading of a word's root: `{word}` → letters + composed Arabic reading (no LLM) |
| POST   | `/verse-lookup` | Every verse containing a word or a derivative of its root, vocalized, with match offsets |
| POST   | `/qlisan/word` | The deterministic four-level fiche for one word, by `surah:ayah:word` |
| GET    | `/qlisan/verse/{surah}/{ayah}` | Vocalized verse + QAC-aligned token boundaries, for word selection |
| POST   | `/qlisan/form` | The صرفي level alone, for a word typed with no verse position |
| POST   | `/tahlil/word` | The five-block integral analysis of one word |
| POST   | `/tahlil/review` | Mark one word's analysis reviewed by a named expert (durable; 503 with no store) |
| GET    | `/verse/{surah}/{ayah}` | One verse + neighbor context + adjacent ids (`?window=`) |
| GET    | `/surah/{number}` | Full surah: ordered verses + metadata + `basmala` |
| GET    | `/surahs`      | All 114 surahs (number, names, ayah count) for pickers |
| GET    | `/fassila/overview` | Fāṣila distribution across the whole corpus |
| GET    | `/fassila/{surah}` | Fāṣila derivation and run-structure for one surah |
| POST   | `/feedback`    | Record 👍/👎 on an answer |

**Removed — these now answer 404:** `POST /lexical`, `POST /lexical/stream`,
`POST /chat` (the non-streaming twin of `/chat/stream`), `POST /tahlil/verse`,
`GET /sessions/{id}` and `GET /feedback/stats`. None of them had a caller: chat
history is reassembled client-side, and a route no page calls is a route nobody
audits. `POST /madar/analyze` also 404s, but for a different reason — it is
quarantined rather than removed; see `linguistics/madar/__init__.py`.

```bash
curl "http://127.0.0.1:8000/search?q=%D8%A7%D9%84%D8%B5%D8%A8%D8%B1&surah=2&limit=3"

curl -N -X POST http://127.0.0.1:8000/chat/stream -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Que dit le Coran sur la patience ?"}]}'

curl -X POST http://127.0.0.1:8000/lisan/analyze -H "Content-Type: application/json" \
  -d '{"word":"رحمة"}'
```

### Run the frontend (Next.js)

```bash
cd frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL to the backend
npm install
npm run dev                         # http://localhost:3000
```

Pages: `/` (project landing), `/chat` (streaming chat + sources + 👍/👎 feedback
+ health banner), `/verse-study` (Word in Verses + Similar Verses),
`/lexical` (Lisan: letter-level root reading), `/tahlil` (integral word
analysis), `/fassila` (fāṣila distribution), `/qlisan` (the per-word fiche,
reached from the other pages), and `/surah` + `/surah/[number]` +
`/verse/[surah]/[ayah]` (reading and deep-linking, Arabic-only). The API
base URL is read from `NEXT_PUBLIC_API_URL` — `npm run dev` picks up `.env.local`
automatically; for a production `npm run build`, set the variable before building
(it is inlined). The backend must allow the frontend origin via `CORS_ORIGINS`
(defaults to `http://localhost:3000`).

---

## Scripts reference

| Script | What it does |
|--------|--------------|
| `scripts/setup.sh` | Create `.venv`, install `requirements.txt`, copy `.env.example` → `.env` |
| `scripts/start_dev.sh` | `docker compose up -d ollama` — Qdrant is deliberately not started: with `QDRANT_PATH` set it runs embedded in the backend |
| `scripts/fetch_translations.py` | Download FR (Hamidullah) + EN (Sahih) translations → `data/derived/translations/` |
| `scripts/ingest.sh` | Run the ingestion pipeline (wrapper for `ingestion/run_pipeline.py`) |
| `scripts/build_maqayis_dataset.py` | Build the curated Maqāyīs aṣl reference `data/references/maqayis_asl.csv` from the OpenITI source |
| `scripts/run.sh` | One-command launcher: Qdrant + Ollama + backend + frontend |

### Rebuilding the Maqāyīs reference

> The Maqāyīs CSV is **live**, not dormant. `POST /madar/analyze` is quarantined,
> but `linguistics/tahlil/evidence.py` reads Ibn Fāris' aṣl through the same
> `linguistics/madar/maqayis_store.py` rather than re-parsing it, so the Tahlīl
> page depends on this file.


`data/references/maqayis_asl.csv` (the curated Ibn Fāris *aṣl* per root) is
committed and is all the runtime needs. Its original — the ~3.8 MB OpenITI
text — is **git-ignored** (`data/source/maqayis/`) as a large, re-downloadable
file. To reconstitute it and rebuild the CSV from a fresh clone:

```bash
python scripts/build_maqayis_dataset.py --fetch   # downloads the OpenITI source, then parses → CSV
python scripts/build_maqayis_dataset.py           # re-parse a source already on disk
```

## Gotchas

- **`.env` hostnames:** `.env.example` uses Docker-internal hostnames
  (`qdrant:6333`, `ollama:11434`). For host runs (uvicorn/scripts on your
  machine), switch them to `localhost` — this is the most common first error.
- **First run is heavy:** the embedding model (~1–2 GB) and `qwen2.5:7b`
  (~4.7 GB) download on first use; keep ≥ 8 GB RAM free.
- **Memory on a 16 GB Mac.** Models are loaded on demand — the embedder and the
  `/search` reranker are built by the first request that needs them, so a session
  spent on the Arabic study tools holds no model memory. Two settings matter more
  than anything else: set **`QDRANT_PATH=data/runtime/qdrant`** to run Qdrant
  in-process (no Docker VM at all — the corpus is 24 MB), and keep
  **`OLLAMA_KEEP_ALIVE`** short (`10m`). On Apple Silicon a loaded model is wired
  GPU memory that macOS cannot swap, so a long keep_alive starves everything else
  for that whole window. Embedded Qdrant takes an exclusive lock: stop the backend
  before running `build_index.py`.
- **A full disk turns memory pressure into a freeze.** macOS grows its swapfile on
  demand; with a nearly full SSD it cannot, and the machine hard-locks instead of
  killing a process. Keep some tens of GB free.
- **Two backend ports:** examples here use `:8000`; `run.sh` defaults to `:8000`
  too but is overridable. Keep `NEXT_PUBLIC_API_URL` in sync with whichever you use.
