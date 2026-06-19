#!/usr/bin/env bash
#
# start.sh — Launch the full Quran RAG app for local development.
#
# Brings up every component needed to use the app in a browser:
#   1. Qdrant      (Docker, port 6333)        — vector database
#   2. Ollama      (Docker, port 11434)       — local LLM (qwen2.5:7b)
#   3. Backend     (uvicorn, port 8001)       — FastAPI RAG API
#   4. Frontend    (next dev, port 3000)      — Next.js UI
#
# Then it opens http://localhost:3000 in your browser.
# Press Ctrl+C to stop everything (backend + frontend); Docker keeps running.
#
# Each step is timed: the latency is printed inline (⏱), a summary table is
# shown at the end, and one CSV line per run is appended to logs/timings.log
# so you can track startup latency across runs.
#
# Usage:
#   ./local-dev/start.sh
#
set -uo pipefail

# ── Paths & config ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

BACKEND_PID=""
FRONTEND_PID=""

say()  { printf "\n\033[1;36m▶ %s\033[0m\n" "$*"; }
ok()   { printf "  \033[1;32m✓\033[0m %s\n" "$*"; }
warn() { printf "  \033[1;33m!\033[0m %s\n" "$*"; }
die()  { printf "\n\033[1;31m✗ %s\033[0m\n" "$*"; exit 1; }

# ── Step timing ───────────────────────────────────────────────────────────
# Measures the wall-clock latency of each startup step, prints it inline, then
# shows a summary table at the end and appends one CSV line per run to
# logs/timings.log so you can track latency across runs.
TIMINGS_LOG="$LOG_DIR/timings.log"
STEP_LABELS=()
STEP_DURS=()
_step_label=""
_step_t0=""

# High-resolution clock (sub-second via python3; falls back to whole seconds).
_now() { python3 -c 'import time;print(time.time())' 2>/dev/null || date +%s; }

SCRIPT_T0="$(_now)"

step_begin() { _step_label="$1"; _step_t0="$(_now)"; }
step_end() {
  local dt
  dt="$(awk "BEGIN{printf \"%.2f\", $(_now) - ${_step_t0}}")"
  STEP_LABELS+=("$_step_label")
  STEP_DURS+=("$dt")
  printf "  \033[1;35m⏱  %-22s %8ss\033[0m\n" "$_step_label" "$dt"
}

print_timings() {
  local total ts i line
  total="$(awk "BEGIN{printf \"%.2f\", $(_now) - ${SCRIPT_T0}}")"
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  say "Startup timings"
  printf "  %-24s %10s\n" "step" "seconds"
  printf "  %-24s %10s\n" "------------------------" "----------"
  for i in "${!STEP_LABELS[@]}"; do
    printf "  %-24s %10s\n" "${STEP_LABELS[$i]}" "${STEP_DURS[$i]}"
  done
  printf "  %-24s %10s\n" "------------------------" "----------"
  printf "  \033[1m%-24s %10s\033[0m\n" "TOTAL" "$total"
  # Append a CSV record for run-over-run history.
  line="$ts"
  for i in "${!STEP_LABELS[@]}"; do
    line="$line,${STEP_LABELS[$i]}=${STEP_DURS[$i]}"
  done
  line="$line,TOTAL=$total"
  echo "$line" >> "$TIMINGS_LOG"
  echo "  (history: $TIMINGS_LOG)"
}

# ── Cleanup on exit ─────────────────────────────────────────────────────
cleanup() {
  say "Stopping app processes (Docker services stay up)..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  # Fallbacks: next dev spawns a child server; uvicorn may have reloader.
  pkill -f "uvicorn api.main:app" 2>/dev/null || true
  pkill -f "next dev" 2>/dev/null || true
  pkill -f "next start" 2>/dev/null || true
  pkill -f "next-server" 2>/dev/null || true
  ok "Stopped. Run 'docker compose down' to stop Qdrant/Ollama too."
}
trap cleanup INT TERM EXIT

# ── 0. Prerequisites ────────────────────────────────────────────────────
step_begin "Prerequisites & env"
say "Checking prerequisites"
command -v docker >/dev/null || die "Docker not found. Install Docker Desktop."
docker info >/dev/null 2>&1 || die "Docker daemon not running. Start Docker Desktop first."
command -v node   >/dev/null || die "Node.js not found. Install Node 18+."
ok "Docker and Node are available"

# Pick a Python interpreter (prefer the project venv).
if [ -d "$ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
  PY="python"
  ok "Using virtualenv .venv"
else
  PY="python3"
  warn "No .venv found — using system python3 (run ./scripts/setup.sh for an isolated env)"
fi

# Ensure env files exist.
[ -f "$ROOT/.env" ] || { cp "$ROOT/.env.example" "$ROOT/.env"; warn "Created .env from .env.example"; }
if [ ! -f "$ROOT/frontend/.env.local" ]; then
  printf 'NEXT_PUBLIC_API_URL=http://localhost:%s\n' "$BACKEND_PORT" > "$ROOT/frontend/.env.local"
  warn "Created frontend/.env.local -> backend on port $BACKEND_PORT"
fi

# Load backend env (QDRANT_URL, OLLAMA_*, etc.).
set -a; # shellcheck disable=SC1091
source "$ROOT/.env"; set +a
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
step_end

# ── 1. Docker services: Qdrant + Ollama ─────────────────────────────────
step_begin "Docker services"
say "Starting Docker services (Qdrant + Ollama)"
docker compose up -d qdrant ollama >/dev/null 2>&1 || die "docker compose up failed"
ok "Qdrant and Ollama containers up"
step_end

# ── 2. Ollama model ─────────────────────────────────────────────────────
step_begin "Ollama model"
say "Checking Ollama model: $OLLAMA_MODEL"
if docker exec quran-ollama ollama list 2>/dev/null | grep -q "${OLLAMA_MODEL%%:*}"; then
  ok "Model $OLLAMA_MODEL present"
else
  warn "Pulling $OLLAMA_MODEL (first time only, ~4.7 GB)..."
  docker exec quran-ollama ollama pull "$OLLAMA_MODEL" || die "Model pull failed"
  ok "Model pulled"
fi
step_end

# ── 3. Data / indexes ───────────────────────────────────────────────────
step_begin "Data / index warm"
say "Checking processed data and indexes"
if [ ! -f "$ROOT/data/processed/verses_final.json" ]; then
  die "Missing data/processed/verses_final.json — run: $PY ingestion/run_pipeline.py"
fi
if [ ! -f "$ROOT/data/processed/bm25_index.pkl" ]; then
  die "Missing BM25 index — run: $PY indexing/build_index.py"
fi
# Pre-materialize files (Desktop is iCloud-synced; avoids a slow first read).
cat "$ROOT"/data/processed/*.json "$ROOT"/data/processed/*.pkl > /dev/null 2>&1 || true
ok "Indexes present and warmed"
step_end

# ── Readiness helper ────────────────────────────────────────────────────
# wait_http NAME URL PID MAX_SECS LOGFILE — poll URL once per second until it
# answers, the process dies, or MAX_SECS elapses. Breaks immediately on the
# first success (accurate timing) and fails loudly with the log tail otherwise
# — it never silently proceeds with a backend that isn't up.
wait_http() {
  local name="$1" url="$2" pid="$3" max="$4" logf="$5" i
  printf "  waiting for %s" "$name"
  for ((i = 0; i < max; i++)); do
    if curl -s --max-time 2 "$url" >/dev/null 2>&1; then
      printf "\n"; return 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      printf "\n"; tail -25 "$logf"; die "$name crashed (see $logf)"
    fi
    printf "."; sleep 1
  done
  printf "\n"; tail -25 "$logf"
  die "$name not ready after ${max}s (see $logf)"
}

# ── 4. Backend (FastAPI) ────────────────────────────────────────────────
# The backend loads the embedding model + indexes (~tens of seconds). We start
# it and wait for /health BEFORE touching the frontend. Counter-intuitively,
# running them concurrently is SLOWER here: the backend's Torch/transformers
# import does thousands of small-file reads, and on this iCloud-synced folder
# those contend with the frontend's cold reads — observed backend init balloon
# from ~56s (alone) to ~90s+ (concurrent with the frontend). Sequential keeps
# each phase uncontended and predictable.
step_begin "Backend ready"
say "Starting backend (uvicorn) on port $BACKEND_PORT"

# HuggingFace Hub: avoid slow network round-trips when the model is cached.
# sentence-transformers checks huggingface.co for the model snapshot on every
# load. Unauthenticated requests get rate-limited and retried with exponential
# backoff, which can add MINUTES to startup (observed: 180s vs ~6s offline).
# The embedding (and rerank) models are downloaded once; if the embedding model
# is already in the local HF cache, force fully-offline loads so startup is
# deterministic. Set HF_FORCE_ONLINE=1 to re-enable Hub access (e.g. to pull a
# new EMBEDDING_MODEL or RERANK_MODEL).
HF_HUB_DIR="${HF_HOME:-$HOME/.cache/huggingface}/hub"
EMB_MODEL="${EMBEDDING_MODEL:-intfloat/multilingual-e5-large-instruct}"
EMB_CACHE="$HF_HUB_DIR/models--${EMB_MODEL//\//--}/snapshots"
if [ "${HF_FORCE_ONLINE:-0}" != "1" ] && [ -d "$EMB_CACHE" ]; then
  export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
  ok "HF offline mode (model cached) — skips Hub network checks"
else
  warn "HF online mode — first-time model download or HF_FORCE_ONLINE=1 (slower)"
fi

# Write .pyc bytecode caches OUTSIDE the iCloud tree. By default Python writes a
# __pycache__/*.pyc next to every imported module; on this iCloud-synced folder
# each write stalls on sync, which dominated startup (~100s+ just importing the
# app's own modules before the model even loads). PYTHONPYCACHEPREFIX redirects
# all bytecode to a local cache, so imports stay fast and nothing syncs.
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-$HOME/Library/Caches/quran-rag/pycache}"
mkdir -p "$PYTHONPYCACHEPREFIX" 2>/dev/null || true

# PYTHONUNBUFFERED + -u: flush logs immediately so per-request timing lines
# (e.g. "chat(stream): retrieval=… generation=… total=…") show live in the
# `tail -f` below instead of being stuck in a block buffer.
PYTHONUNBUFFERED=1 "$PY" -u -m uvicorn api.main:app --host 127.0.0.1 --port "$BACKEND_PORT" \
  > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
wait_http "/health" "http://127.0.0.1:$BACKEND_PORT/health" "$BACKEND_PID" 300 "$LOG_DIR/backend.log"
ok "Backend ready: http://localhost:$BACKEND_PORT (docs at /docs)"
step_end

# ── 5. Frontend (Next.js) ───────────────────────────────────────────────
# Mode: "prod" (default) rebuilds when the source changed (so you always get the
# current code), then `next start` — serves instantly. "dev" uses `next dev`,
# which recompiles each route on every request; that is very slow here because
# this project lives on an iCloud-synced folder and the .next cache writes crawl.
# Use FRONTEND_MODE=dev only if you need hot reload.
FRONTEND_MODE="${FRONTEND_MODE:-prod}"
step_begin "Frontend build/prep"
say "Starting frontend (Next.js, mode=$FRONTEND_MODE) on port $FRONTEND_PORT"

# node_modules + iCloud don't mix: iCloud evicts files to dataless placeholders,
# so reads stall while iCloud re-downloads them. The durable fix is to move the
# whole project off ~/Desktop (see local-dev/README.md). We mark node_modules
# doNotSync to keep freshly-installed files local. We do NOT bulk pre-materialize
# it: `cat`-ing all ~6k files forces a slow serial re-download of the entire tree
# (incl. source maps / typings that `next start` never reads) on every launch —
# that band-aid cost minutes. `next start` reads only what it needs on demand.
NM="$ROOT/frontend/node_modules"
if [ ! -f "$NM/.bin/next" ]; then
  warn "Installing frontend dependencies..."
  ( cd "$ROOT/frontend" && npm install >/dev/null 2>&1 ) || die "npm install failed"
fi
xattr -w com.apple.cloud.doNotSync 1 "$NM" 2>/dev/null || true

if [ "$FRONTEND_MODE" = "dev" ]; then
  ( cd "$ROOT/frontend" && npm run dev -- --port "$FRONTEND_PORT" ) \
    > "$LOG_DIR/frontend.log" 2>&1 &
  FRONTEND_PID=$!
else

  # Rebuild whenever the build is missing, REBUILD=1 is set, or any frontend
  # source file is newer than the last build — so start.sh always serves the
  # current code, while skipping the (iCloud-slow) build when nothing changed.
  # Set SKIP_REBUILD=1 to force-reuse an existing build regardless of changes.
  BUILD_ID_FILE="$ROOT/frontend/.next/BUILD_ID"
  reason=""
  if [ ! -f "$BUILD_ID_FILE" ]; then
    reason="no existing build"
  elif [ "${REBUILD:-0}" = "1" ]; then
    reason="REBUILD=1"
  elif [ "${SKIP_REBUILD:-0}" = "1" ]; then
    reason=""  # explicitly reuse
  elif find "$ROOT/frontend" \( -path '*/node_modules' -o -path '*/.next' \) -prune \
        -o -type f ! -name 'tsconfig.tsbuildinfo' -newer "$BUILD_ID_FILE" -print 2>/dev/null \
        | grep -q .; then
    # tsconfig.tsbuildinfo is excluded: it's a build artifact, not source, and
    # `next build` can write it after BUILD_ID — which would force a rebuild
    # every launch.
    reason="source changed since last build"
  fi

  if [ -n "$reason" ]; then
    warn "Building frontend ($reason; SKIP_REBUILD=1 reuses the existing build)..."
    rm -rf "$ROOT/frontend/.next"
    mkdir -p "$ROOT/frontend/.next"
    xattr -w com.apple.cloud.doNotSync 1 "$ROOT/frontend/.next" 2>/dev/null || true
    # The API base URL is read at build time from frontend/.env.local
    # (NEXT_PUBLIC_API_URL). It is inlined into the static bundle.
    ( cd "$ROOT/frontend" && npm run build ) > "$LOG_DIR/frontend-build.log" 2>&1 \
      || { tail -25 "$LOG_DIR/frontend-build.log"; die "Frontend build failed"; }
    ok "Build complete"
  else
    ok "Frontend build is up to date — reusing it"
  fi

  # Guard: wait until the build manifest is readable on disk before starting.
  # On iCloud-synced folders the file can lag behind the build process exit.
  printf "  waiting for .next/BUILD_ID"
  for _ in $(seq 1 60); do
    [ -f "$ROOT/frontend/.next/BUILD_ID" ] && break
    printf "."; sleep 2
  done
  [ -f "$ROOT/frontend/.next/BUILD_ID" ] \
    || die "Build did not produce .next/BUILD_ID (iCloud sync?). Try: REBUILD=1 ./local-dev/start.sh"
  printf "\n"; ok "Build ready: $(cat "$ROOT/frontend/.next/BUILD_ID")"

  # `next start` cold-reads the whole .next build output; on this iCloud-synced
  # folder those reads can be dataless (slow). Mark .next doNotSync and
  # pre-materialize it (~30 MB, cheap) so the server boots from warm files.
  xattr -w com.apple.cloud.doNotSync 1 "$ROOT/frontend/.next" 2>/dev/null || true
  find "$ROOT/frontend/.next" -type f -print0 2>/dev/null | xargs -0 -P 8 cat > /dev/null 2>&1 || true

  ( cd "$ROOT/frontend" && npm run start -- --port "$FRONTEND_PORT" ) \
    > "$LOG_DIR/frontend.log" 2>&1 &
  FRONTEND_PID=$!
fi
step_end  # Frontend build/prep

# ── 6. Wait for the frontend server (backend is already up) ─────────────
step_begin "Frontend serve ready"
wait_http "the frontend server" "http://127.0.0.1:$FRONTEND_PORT" "$FRONTEND_PID" 120 "$LOG_DIR/frontend.log"
ok "Frontend ready: http://localhost:$FRONTEND_PORT"
step_end

# ── Done ────────────────────────────────────────────────────────────────
say "Quran RAG is running"
echo "  App:      http://localhost:$FRONTEND_PORT"
echo "  API:      http://localhost:$BACKEND_PORT  (Swagger: /docs)"
echo "  Logs:     $LOG_DIR/{backend,frontend}.log"
echo ""
echo "  Press Ctrl+C to stop the app (Qdrant/Ollama keep running)."

# Per-step latency summary (and append to logs/timings.log for history).
print_timings

# Open the browser (macOS / Linux).
if command -v open >/dev/null 2>&1; then open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 || true
fi

# Stream logs and keep the script alive until Ctrl+C.
tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
