#!/usr/bin/env bash
#
# stop.sh — Stop everything started by start.sh.
#
# By default stops the app processes (backend + frontend). Pass --all to also
# stop the Docker services (Qdrant + Ollama).
#
#   ./local-dev/stop.sh         # stop backend + frontend
#   ./local-dev/stop.sh --all   # also: docker compose down
#
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Stopping backend and frontend..."
pkill -f "uvicorn api.main:app" 2>/dev/null && echo "  backend stopped" || echo "  backend not running"
pkill -f "next dev" 2>/dev/null || true
pkill -f "next start" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null && echo "  frontend stopped" || echo "  frontend not running"

if [ "${1:-}" = "--all" ]; then
  echo "Stopping Docker services (Qdrant + Ollama)..."
  ( cd "$ROOT" && docker compose down ) && echo "  docker services stopped"
fi
echo "Done."
