"""
qlisan_data.py — Cached loaders for the QLisan foundation artifacts.

The four artifacts built by `ingestion/qac_treebank.py` are read-only, keyed by
`"surah:ayah:word"` (or normalized root, for the root graph). Several QLisan
services need them in the same process; the shared `quran_data.loaders` registry
parses each file once and hands back a shared object (same pattern as
`quran_data/corpus.py`). Reading them through the registry rather than through a
second set of caches here is what keeps a backend serving both QLisan and Tahlīl
to ONE resident copy of `qac_words.json` (29 MB) instead of two.

**Read-only contract:** callers must not mutate the returned dicts in place.

If an artifact is missing, the registry raises with the dataset's name, its
expected path and the exact rebuild command.
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arabic_text import fold_blind, fold_carrier  # noqa: E402
from quran_data import loaders  # noqa: E402


def qac_words() -> dict[str, dict]:
    """`"surah:ayah:word"` -> morphology record (root / lemma / pos / features / …)."""
    return loaders.qac_words()


def qac_syntax() -> dict[str, dict]:
    """`"surah:ayah:word"` -> dependency role. Words with no usable relation are absent."""
    return loaders.qac_syntax()


def root_graph() -> dict[str, list[str]]:
    """root -> ordered list of occurrence refs `"surah:ayah:word"` (nazair).

    Keys are the EXACT root spelling (`أمن`, `لؤلؤ`), decided per word by
    `ingestion/root_resolver.py`. A word is listed under its primary root and under
    any alternate reading, so reachability does not depend on which one is held.
    Callers holding a folded spelling must go through `canonical_root()`.
    """
    return loaders.root_graph()


@functools.lru_cache(maxsize=1)
def _root_fold_index() -> dict[str, str]:
    """Any folded spelling of a corpus root -> the exact spelling stored as a key."""
    idx: dict[str, str] = {}
    for r in root_graph():
        for k in (fold_carrier(r), fold_blind(r)):
            if k:
                idx.setdefault(k, r)
    return idx


def canonical_root(query: str) -> str | None:
    """`امن` -> `أمن`, `لالا` -> `لؤلؤ`, unknown -> None.

    The single way to ask "is this a corpus root, and how is it spelled?". The fold
    is a lookup key; the answer is always the stored spelling.
    """
    if not query:
        return None
    if query in root_graph():
        return query
    idx = _root_fold_index()
    return idx.get(fold_carrier(query)) or idx.get(fold_blind(query))


def word_index() -> dict[str, dict]:
    """`"surah:ayah:word"` -> {uthmani, imlaai, chakl_char_start, chakl_char_end, aligned}."""
    return loaders.word_index()


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
