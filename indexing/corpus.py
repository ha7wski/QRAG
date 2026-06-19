"""
corpus.py — Single cached loader for the processed verse corpus.

`verses_final.json` (~6.8 MB, 6236 verses) is needed by several components in
the same backend process — `HybridSearch`, `Retriever`, and `LexicalRetriever`.
Loading it independently in each would hold 2–3 copies in RAM. These helpers
parse the file once per process (cached) and hand back a shared object.

**Read-only contract:** callers must not mutate the returned list/dict or the
verse dicts in place (everyone shares them). Need a different order? Use
`sorted(load_verses(), ...)`, which returns a new list over the same dicts.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSES_FINAL = ROOT / "data" / "processed" / "verses_final.json"


@functools.lru_cache(maxsize=1)
def load_verses() -> list[dict]:
    """Return the parsed verse list, loaded once per process and cached."""
    if not VERSES_FINAL.exists():
        raise FileNotFoundError(
            f"{VERSES_FINAL} not found. Run `python ingestion/run_pipeline.py` first."
        )
    with VERSES_FINAL.open(encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def verses_by_id() -> dict[str, dict]:
    """`{verse_id: verse}` view over the cached corpus (built once, shared)."""
    return {v["id"]: v for v in load_verses()}
