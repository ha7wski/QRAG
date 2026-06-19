#!/usr/bin/env bash
# Run the data ingestion pipeline (parser → normalizer → enricher → morphology).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] && source .venv/bin/activate || true
python ingestion/run_pipeline.py
