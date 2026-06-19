# local-dev

One-command local launcher for the whole Quran RAG stack.

## Usage

```bash
./local-dev/start.sh
```

This starts, in order:

1. **Qdrant** (Docker, `:6333`) — vector database
2. **Ollama** (Docker, `:11434`) — local LLM, pulls `qwen2.5:7b` if missing
3. **Backend** (uvicorn, `:8001`) — FastAPI RAG API (`/docs` for Swagger)
4. **Frontend** (Next.js dev, `:3000`) — the UI

When everything is ready it opens **http://localhost:3000** in your browser and
tails the logs. Press **Ctrl+C** to stop the backend and frontend (Docker keeps
running).

## Stop

```bash
./local-dev/stop.sh         # stop backend + frontend
./local-dev/stop.sh --all   # also stop Qdrant + Ollama (docker compose down)
```

## Step timings

Each startup step is timed. You see the latency inline as it runs (`⏱`), a
summary table at the end:

```
▶ Startup timings
  step                        seconds
  Prerequisites & env             0.40
  Docker services                 1.10
  Ollama model                    0.30
  Data / index warm               0.20
  Backend ready                  58.30
  Frontend build/prep            41.20
  Frontend serve ready            6.10
  TOTAL                         107.60
```

and one CSV line per run appended to `local-dev/logs/timings.log`, so you can
track latency across runs:

```
2026-06-17 00:43:08,Prerequisites & env=0.40,...,Backend ready=58.30,...,TOTAL=107.60
```

The ingestion pipeline (`python ingestion/run_pipeline.py`) is timed per stage
too (parser / normalizer / enricher / translator / morphology).

### Per-request timing (live)

`start.sh` streams the backend log (`tail -f`), and the backend runs unbuffered,
so **each question you ask in the app prints a timing summary live**, e.g.:

```
quran_rag.timing: chat(stream): retrieval=987ms ttft=1330ms generation=26135ms \
  total=27122ms | sources=5 chunks=229 | qp=on hyde=off rerank=off | q='الصبر'
```

- `retrieval` — hybrid search (+ optional rerank/HyDE) to build the context
- `ttft` — time to first token from the LLM
- `generation` — full LLM generation (streamed)
- `total` — end to end

All three endpoints log under `quran_rag.timing`:

```
search:  retrieval=87ms  | results=5 limit=5 filters={} rerank=off | q='الصبر'
lexical: lookup=28ms generation=…ms total=…ms | root=ر-ح-م occurrences=313 | q='رحمة'
chat(stream): retrieval=…ms ttft=…ms generation=…ms total=…ms | sources=5 … | q='…'
```

`/search` is fast (no LLM). `/lexical` and `/chat` include LLM generation and
are slow on CPU — the lexical analysis sends a large multi-verse prompt, so its
`generation` time dominates (a good signal if you want to lower `LLM_SAMPLE`).

(The generic `POST /chat/stream -> 200 (2 ms)` middleware line only measures
time-to-stream-start, not full generation — the `quran_rag.timing` line is the
accurate one.)

## ⚠️ iCloud caveat (this project is on an iCloud-synced folder)

This project currently lives at **`~/Desktop/Tech Projects/quran-rag`**, which
**is** iCloud-synced. iCloud and `node_modules`/`.next` don't mix well: iCloud
can evict files to dataless placeholders and create conflict copies
(`lucide-react 2`, `.next-C5AVnZaZ`, …), which corrupt the Next.js build and
runtime (`Unexpected end of JSON input`).

`start.sh` mitigates this on every launch:

- marks `frontend/node_modules` and `frontend/.next` `com.apple.cloud.doNotSync`,
- pre-materializes `node_modules` (forces any dataless files local) before
  starting Next,
- runs the frontend in **production mode** by default (`next build` once, then
  `next start`) so `.next` isn't rewritten on every request.

These make it usable here, but the durable fix is to keep the project on a
**non-iCloud** path (e.g. `~/Projects/quran-rag`): `rm -rf node_modules` is
instant again and there are no conflict copies. `com.apple.cloud.doNotSync` and
symlinking `node_modules` out of the tree alone do **not** fully fix it (iCloud
dereferences the symlink back into a synced folder) — only moving the whole tree
does.

To relocate, a plain `mv` works (all script paths are relative); then
`cd frontend && rm -rf node_modules .next && npm install`.

## Notes

- The frontend runs in **production mode** by default (`next build` once, then
  `next start`). This is intentional: `next dev` recompiles each route on every
  request, which crawls because the project sits on an iCloud-synced folder
  (`.next` cache writes are slow). For hot reload, use `FRONTEND_MODE=dev`.
- The frontend **rebuilds automatically when its source changed** since the last
  build, so `./local-dev/start.sh` always serves the current code. Force a rebuild
  anytime with `REBUILD=1 ./local-dev/start.sh`, or reuse the existing build (skip
  the check) with `SKIP_REBUILD=1 ./local-dev/start.sh`.
- Ports are overridable: `BACKEND_PORT=8000 FRONTEND_PORT=3001 ./local-dev/start.sh`.
- Logs are written to `local-dev/logs/{backend,frontend}.log`.
- The script expects the data indexes to exist. If they don't, it tells you to run:
  - `python ingestion/run_pipeline.py`
  - `python indexing/build_index.py`
- First backend startup loads the embedding model (~6–10 s once cached). The
  iCloud-synced `data/processed/` files are pre-warmed to avoid stalls.
- **Bytecode off iCloud:** Python writes a `__pycache__/*.pyc` next to every
  imported module; on this iCloud-synced folder each write stalls on sync and
  dominated startup (~100–180 s just importing the app's own modules, before the
  model even loads). `start.sh` sets `PYTHONPYCACHEPREFIX` to
  `~/Library/Caches/quran-rag/pycache` (non-iCloud), which collapsed backend
  startup to ~8 s. If you ever see backend startup balloon again, delete stale
  in-tree caches: `find . -type d -name __pycache__ -not -path '*/node_modules/*' -exec rm -rf {} +`.
- **Memory pressure:** the stack is RAM-hungry (Ollama `qwen2.5:7b` ~5 GB +
  Docker + the e5-large embedder ~2 GB). If the Mac is swapping hard
  (`sysctl vm.swapusage`), model loading thrashes and every step slows down —
  close heavy apps or use a smaller `OLLAMA_MODEL`/`EMBEDDING_MODEL`.
- **HF Hub offline:** `sentence-transformers` otherwise pings huggingface.co on
  every load to check the model snapshot; unauthenticated requests get
  rate-limited and retried with backoff, which can add **minutes** to startup
  (observed: ~180 s instead of ~6 s). `start.sh` auto-detects the cached model
  and sets `HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1` so loads are fully local.
  To pull a new `EMBEDDING_MODEL`/`RERANK_MODEL`, run with `HF_FORCE_ONLINE=1`.
