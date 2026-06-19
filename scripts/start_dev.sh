#!/usr/bin/env bash
# Start the development infrastructure (Qdrant + Ollama) via Docker Compose.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d qdrant ollama
echo "Qdrant:  http://localhost:6333/dashboard"
echo "Ollama:  http://localhost:11434"
echo "Next:    python indexing/build_index.py"
