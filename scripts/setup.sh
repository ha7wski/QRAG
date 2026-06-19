#!/usr/bin/env bash
# Set up the Python environment for the Quran RAG project.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (.venv)..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — review it before running services."
fi

echo "Setup complete. Activate with: source .venv/bin/activate"
