#!/usr/bin/env bash
#
# run.sh — One-command local launcher for Quran RAG.
#
# Brings up everything needed to use the app in a browser:
#   1. Qdrant + Ollama   (Docker)            — vector DB + local LLM
#   2. Backend (uvicorn, :8000)              — FastAPI RAG API
#   3. Frontend (next dev, :3000)            — Next.js UI
# then opens http://localhost:3000. Ctrl+C stops the app (Docker keeps running).
#
# Assumes one-time setup is done (see README "Run from a clone"):
#   ./scripts/setup.sh && source .venv/bin/activate
#   # edit .env for a host run: QDRANT_URL/OLLAMA_BASE_URL → localhost
#   python scripts/fetch_translations.py
#   python ingestion/run_pipeline.py
#   python indexing/build_index.py
#
# Ports are overridable: BACKEND_PORT=8001 FRONTEND_PORT=3001 ./scripts/run.sh
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
LOG_DIR="${TMPDIR:-/tmp}/quran-rag"
mkdir -p "$LOG_DIR"

say()  { printf "\n\033[1;36m▶ %s\033[0m\n" "$*"; }
ok()   { printf "  \033[1;32m✓\033[0m %s\n" "$*"; }
warn() { printf "  \033[1;33m!\033[0m %s\n" "$*"; }
die()  { printf "\n\033[1;31m✗ %s\033[0m\n" "$*"; exit 1; }

BACKEND_PID=""; FRONTEND_PID=""
cleanup() {
  say "Stopping app (Docker services stay up)…"
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  pkill -f "uvicorn api.main:app" 2>/dev/null || true
  pkill -f "next dev" 2>/dev/null || true
  ok "Stopped. Run 'docker compose down' to stop Qdrant/Ollama too."
}
trap cleanup INT TERM EXIT

# ── Prerequisites ─────────────────────────────────────────────────────────
say "Checking prerequisites"
command -v docker >/dev/null || die "Docker not found. Install Docker Desktop."
docker info >/dev/null 2>&1 || die "Docker daemon not running — start Docker first."
command -v node >/dev/null || die "Node.js not found (need 18+)."
command -v curl >/dev/null || die "curl not found (used for readiness checks)."

# Python: prefer the project venv.
if [ -d "$ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"; PY="python"
  ok "Using virtualenv .venv"
else
  PY="python3"
  warn "No .venv — run ./scripts/setup.sh first for an isolated env."
fi

# Env files.
[ -f "$ROOT/.env" ] || {
  cp "$ROOT/.env.example" "$ROOT/.env"
  warn "Created .env — set QDRANT_URL/OLLAMA_BASE_URL to localhost for host runs."
}
set -a; # shellcheck disable=SC1091
source "$ROOT/.env"; set +a
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
if [ ! -f "$ROOT/frontend/.env.local" ]; then
  printf 'NEXT_PUBLIC_API_URL=http://localhost:%s\n' "$BACKEND_PORT" > "$ROOT/frontend/.env.local"
  warn "Created frontend/.env.local → backend on :$BACKEND_PORT"
fi

# ── Data check (built once via the README "Run from a clone" steps) ───────
say "Checking processed data & indexes"
if [ ! -f "$ROOT/data/processed/verses_final.json" ] || [ ! -f "$ROOT/data/processed/bm25_index.pkl" ]; then
  die "Data/indexes missing. Run the one-time build first:
    $PY scripts/fetch_translations.py
    $PY ingestion/run_pipeline.py
    $PY indexing/build_index.py"
fi
ok "Data present"

# ── Docker services: Qdrant + Ollama ──────────────────────────────────────
say "Starting Qdrant + Ollama (Docker)"
docker compose up -d qdrant ollama >/dev/null 2>&1 || die "docker compose up failed"
ok "Containers up"

if docker exec quran-ollama ollama list 2>/dev/null | grep -q "${OLLAMA_MODEL%%:*}"; then
  ok "Model $OLLAMA_MODEL present"
else
  warn "Pulling $OLLAMA_MODEL (first time only, ~4.7 GB)…"
  docker exec quran-ollama ollama pull "$OLLAMA_MODEL" || die "Model pull failed"
fi

# ── Readiness helper ──────────────────────────────────────────────────────
# wait_http NAME URL PID MAX_SECS LOGFILE — poll until URL answers, the process
# dies, or the timeout elapses (then fail loudly with the log tail).
wait_http() {
  local name="$1" url="$2" pid="$3" max="$4" logf="$5" i
  printf "  waiting for %s" "$name"
  for ((i = 0; i < max; i++)); do
    curl -s --max-time 2 "$url" >/dev/null 2>&1 && { printf "\n"; return 0; }
    kill -0 "$pid" 2>/dev/null || { printf "\n"; tail -20 "$logf"; die "$name crashed (see $logf)"; }
    printf "."; sleep 1
  done
  printf "\n"; tail -20 "$logf"; die "$name not ready after ${max}s (see $logf)"
}

# ── Backend (FastAPI) ─────────────────────────────────────────────────────
say "Starting backend (uvicorn :$BACKEND_PORT)"
PYTHONUNBUFFERED=1 "$PY" -u -m uvicorn api.main:app \
  --host 127.0.0.1 --port "$BACKEND_PORT" > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
wait_http "/health" "http://127.0.0.1:$BACKEND_PORT/health" "$BACKEND_PID" 300 "$LOG_DIR/backend.log"
ok "Backend ready: http://localhost:$BACKEND_PORT (docs at /docs)"

# ── Frontend (Next.js, dev mode) ──────────────────────────────────────────
say "Starting frontend (next dev :$FRONTEND_PORT)"
if [ ! -x "$ROOT/frontend/node_modules/.bin/next" ]; then
  warn "Installing frontend dependencies…"
  ( cd "$ROOT/frontend" && npm install >/dev/null 2>&1 ) || die "npm install failed"
fi
( cd "$ROOT/frontend" && npm run dev -- --port "$FRONTEND_PORT" ) > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
wait_http "the frontend" "http://127.0.0.1:$FRONTEND_PORT" "$FRONTEND_PID" 120 "$LOG_DIR/frontend.log"
ok "Frontend ready: http://localhost:$FRONTEND_PORT"

# ── Done ──────────────────────────────────────────────────────────────────
say "Quran RAG is running"
echo "  App:  http://localhost:$FRONTEND_PORT"
echo "  API:  http://localhost:$BACKEND_PORT  (Swagger: /docs)"
echo "  Logs: $LOG_DIR/{backend,frontend}.log"
echo "  Press Ctrl+C to stop the app (Qdrant/Ollama keep running)."

if command -v open >/dev/null 2>&1; then open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 || true
fi

# Stream logs and keep the script alive until Ctrl+C.
tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
