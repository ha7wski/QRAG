#!/usr/bin/env bash
# Set up the Python environment for the Quran RAG project.
#
# Uses uv (https://docs.astral.sh/uv/) to create .venv and install the pinned
# dependencies. The venv path stays .venv because both launchers — scripts/run.sh
# and local-dev/start.sh — activate "$ROOT/.venv" by name.
#
#   requirements.txt   direct dependencies, hand-curated and pinned
#   requirements.lock  full transitive closure (uv pip compile)
#
# Pass --lock to install the exact locked closure instead of resolving fresh.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install it with one of:"
  echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "    brew install uv"
  exit 1
fi

# .python-version pins the interpreter; uv downloads it if absent.
echo "Creating virtual environment (.venv) with uv..."
uv venv

if [ "${1:-}" = "--lock" ] && [ -f requirements.lock ]; then
  echo "Installing the locked dependency closure (requirements.lock)..."
  uv pip install -r requirements.lock
else
  echo "Installing dependencies from requirements.txt..."
  uv pip install -r requirements.txt
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — review it before running services."
fi

echo
echo "Setup complete. Activate with: source .venv/bin/activate"
echo "Or run commands without activating:  uv run python -m pytest -q"
