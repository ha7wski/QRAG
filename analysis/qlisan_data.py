"""
qlisan_data.py — Cached loaders for the QLisan foundation artifacts.

The four artifacts built by `ingestion/qac_treebank.py` are read-only, keyed by
`"surah:ayah:word"` (or normalized root, for the root graph). Several QLisan
services need them in the same process; these `@lru_cache` loaders parse each file
once and hand back a shared object (same pattern as `indexing/corpus.py`).

**Read-only contract:** callers must not mutate the returned dicts in place.

If an artifact is missing, a clear FileNotFoundError points at the build command.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

_QAC_WORDS = PROCESSED / "qac_words.json"
_QAC_SYNTAX = PROCESSED / "qac_syntax.json"
_ROOT_GRAPH = PROCESSED / "root_graph.json"
_WORD_INDEX = PROCESSED / "word_index.json"

_BUILD_HINT = "Run `python ingestion/qac_treebank.py` to build it."


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. {_BUILD_HINT}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def qac_words() -> dict[str, dict]:
    """`"surah:ayah:word"` -> morphology record (root / lemma / pos / features / …)."""
    return _load(_QAC_WORDS)


@functools.lru_cache(maxsize=1)
def qac_syntax() -> dict[str, dict]:
    """`"surah:ayah:word"` -> dependency role. Words with no usable relation are absent."""
    return _load(_QAC_SYNTAX)


@functools.lru_cache(maxsize=1)
def root_graph() -> dict[str, list[str]]:
    """normalized_root -> ordered list of occurrence refs `"surah:ayah:word"` (nazair)."""
    return _load(_ROOT_GRAPH)


@functools.lru_cache(maxsize=1)
def word_index() -> dict[str, dict]:
    """`"surah:ayah:word"` -> {uthmani, imlaai, chakl_char_start, chakl_char_end, aligned}."""
    return _load(_WORD_INDEX)


if __name__ == "__main__":
    w = qac_words()
    s = qac_syntax()
    g = root_graph()
    x = word_index()
    print(f"qac_words : {len(w)} words")
    print(f"qac_syntax: {len(s)} words")
    print(f"root_graph: {len(g)} roots")
    print(f"word_index: {len(x)} words")
    print("1:1:1 ->", w.get("1:1:1"))
