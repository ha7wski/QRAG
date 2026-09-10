#!/usr/bin/env bash
#
# start_dev.sh — Start the development infrastructure (Ollama) via Docker Compose.
#
# Qdrant is deliberately NOT started here any more.
#
# With QDRANT_PATH set — which is what .env carries — Qdrant runs EMBEDDED inside
# the backend process, against a local directory. There is no server to start.
# Bringing its container up anyway would start a service the backend never talks
# to, and re-create the Docker Desktop memory reservation this project has
# documented as the cause of a hard machine freeze: ~11 GB reserved to serve a
# 24 MB vector set, on a 16 GB shared-memory Mac. See the memory-budget section
# of CLAUDE.md.
#
# Both real launchers (scripts/run.sh, local-dev/start.sh) already skip it
# correctly; this shortcut was the one place that still asked for it.
#
# To run Qdrant as a server on purpose: leave QDRANT_PATH empty, point QDRANT_URL
# at it, and start it yourself with `docker compose up -d qdrant`.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d ollama
echo "Ollama:  http://localhost:11434"
echo "Qdrant:  embedded in the backend (QDRANT_PATH), no container needed"
echo "Next:    python indexing/build_index.py     # with the backend stopped"
