"""
quran_passages.py — the pure reader behind GET /quran-passages/*.

The shared-passage relation («does this wording come back in another surah?»)
is answered once, offline and model-free, by `scripts/build_quran_passages.py`,
and shipped as `data/derived/quran_passages.json` (change `add-shared-passages`,
design D5). This module only aggregates it into the surah × surah map and one
cell's list.

It loads no model, opens no Qdrant client, and imports nothing from the project
but `quran_data`. The dataset is reached through `quran_data.loaders.quran_passages()`
at CALL time, never at import: a backend without the file must still start, and a
request against it must become a 503 carrying the rebuild command. It is a
separate file from `quran_similarity.json`, so either relation can be missing
without the other failing.

Shape (D5, schema 1):

    passages = [{"a": "<s:a>", "b": "<s:a>", "wa": [i1, i2], "wb": [j1, j2],
                 "k": int, "roots": [str]}]   # a in the lower surah, sorted by (a, b)

One passage per verse pair — the build keeps the best alignment only — so a pair
is simply an entry. The aggregate is memoised per loaded dict (one slot, locked),
exactly as `retrieval/quran_similarity.py` does: computed once per process in
production, recomputed for a different dict (a test fixture, a reloaded file).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quran_data import loaders  # noqa: E402

REBUILD = "python scripts/build_quran_passages.py"


class MalformedEntry(LookupError):
    """The dataset is not in the D5 shape (a missing key, a wrong type, a broken rule).

    The schema number matched, so the file was written by a builder that broke
    its own contract, or edited by hand. It is a 503 carrying the rebuild
    command — never a 500 out of a bare `KeyError`.
    """


_MALFORMED = (KeyError, TypeError, ValueError, AttributeError, IndexError)
_SURAHS = range(1, 115)


def load() -> dict:
    """The whole dataset, through its one cached loader.

    Raises `quran_data.loaders.DatasetMissing` when the file is absent and
    `loaders.UnknownSchema` (a `ValueError`) on an unknown schema — both carry
    the rebuild command, and the route turns both into a 503.
    """
    return loaders.quran_passages()


def _malformed(where, exc: Exception) -> MalformedEntry:
    return MalformedEntry(
        f"quran_passages.json holds a malformed entry at {where!r} "
        f"({type(exc).__name__}: {exc}); the dataset is corrupt or stale. "
        f"Rebuild it with:\n    {REBUILD}"
    )


def _ref(raw) -> tuple[int, int]:
    """`"s:a"` → `(s, a)` with a surah in 1..114 and an ayah ≥ 1."""
    if not isinstance(raw, str):
        raise TypeError(f"ref {raw!r} is not a string")
    surah, ayah = raw.split(":")
    surah, ayah = int(surah), int(ayah)
    if surah not in _SURAHS or ayah < 1:
        raise ValueError(f"ref {raw!r} names no verse of the Quran")
    return surah, ayah


def _int(value, name: str) -> int:
    """A positive int; a `bool` (an `int` to Python) or anything else is malformed."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise TypeError(f"{name} {value!r} is not a positive integer")
    return value


def _span(value, name: str) -> tuple[int, int]:
    """A 1-based inclusive word span `[first, last]`, `1 ≤ first ≤ last`."""
    if not isinstance(value, list) or len(value) != 2:
        raise TypeError(f"{name} {value!r} is not a [first, last] pair")
    first, last = _int(value[0], name), _int(value[1], name)
    if first > last:
        raise ValueError(f"{name} {value!r} ends before it starts")
    return first, last


def _roots(value) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(r, str) and r for r in value):
        raise TypeError(f"roots {value!r} is not a list of non-empty str")
    if not value:
        raise ValueError("roots is empty; a passage matches at least three content words")
    return tuple(value)


def _aggregate(data: dict) -> dict:
    """Every passage keyed by its pair, and the pairs grouped by surah cell.

    Returns `{"pairs": {(u, v): {"wa", "wb", "k", "roots"}}, "cells": {(a, b):
    [(u, v), ...]}}` with `u`, `v` as `(surah, ayah)`, `surah(u) < surah(v)`;
    each cell's list is already in served order (`k` desc, then `(u, v)`).
    """
    raw = data.get("passages") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise _malformed("passages", TypeError("passages is not a list"))
    pairs: dict[tuple, dict] = {}
    for n, p in enumerate(raw):
        try:
            u, v = _ref(p["a"]), _ref(p["b"])
            if u[0] >= v[0]:
                raise ValueError(f"{p['a']} / {p['b']}: `a` must lie in the LOWER surah "
                                 f"(a same-surah pair is never a passage)")
            if (u, v) in pairs:
                raise ValueError(f"{p['a']} / {p['b']} is listed twice; one passage per pair")
            pairs[(u, v)] = {"wa": _span(p["wa"], "wa"), "wb": _span(p["wb"], "wb"),
                             "k": _int(p["k"], "k"), "roots": _roots(p["roots"])}
        except _MALFORMED as exc:
            raise _malformed(f"passages[{n}]", exc) from exc

    cells: dict[tuple[int, int], list[tuple]] = {}
    for pair in pairs:
        cells.setdefault((pair[0][0], pair[1][0]), []).append(pair)
    for members in cells.values():
        members.sort(key=lambda q: (-pairs[q]["k"], q))
    return {"pairs": pairs, "cells": cells}


# One slot: the dict last aggregated and its result. Holding the dict itself
# keeps its id from being reused while the slot is alive.
_memo: tuple[dict, dict] | None = None
_memo_lock = threading.Lock()


def _aggregated(data: dict) -> dict:
    """`_aggregate(data)`, memoised on the identity of `data` (treated as read-only)."""
    global _memo
    with _memo_lock:
        if _memo is not None and _memo[0] is data:
            return _memo[1]
        result = _aggregate(data)
        _memo = (data, result)
        return result


def _verse(ref: tuple[int, int]) -> dict:
    return {"surah": ref[0], "ayah": ref[1]}


def _entry(u: tuple, v: tuple, p: dict) -> dict:
    """A fresh served entry: the memoised aggregate is shared and must not be mutated."""
    return {"u": _verse(u), "v": _verse(v), "wa": list(p["wa"]), "wb": list(p["wb"]),
            "k": p["k"], "roots": list(p["roots"])}


def pair_set(data: dict) -> list[dict]:
    """Every passage pair, `u` in the lower surah, ordered by `(u, v)`.

    `[{"u": {"surah", "ayah"}, "v": {...}, "wa", "wb", "k", "roots"}]`.
    Raises `MalformedEntry` when the dataset is not in the D5 shape.
    """
    pairs = _aggregated(data)["pairs"]
    return [_entry(u, v, pairs[(u, v)]) for u, v in sorted(pairs)]


def matrix(data: dict) -> dict:
    """The non-empty surah cells and the totals — the similarity map's shape (D6).

    `{"cells": [{"a", "b", "pairs", "verses_a", "verses_b"}], "total_pairs",
    "max_pairs"}`, `a < b`, ordered by `(a, b)`, empty cells absent.
    `sum(pairs) == total_pairs` by construction.
    Raises `MalformedEntry` when the dataset is not in the D5 shape.
    """
    agg = _aggregated(data)
    cells = [
        {"a": a, "b": b, "pairs": len(members),
         "verses_a": len({u for u, _ in members}),
         "verses_b": len({v for _, v in members})}
        for (a, b), members in sorted(agg["cells"].items())
    ]
    return {
        "cells": cells,
        "total_pairs": len(agg["pairs"]),
        "max_pairs": max((c["pairs"] for c in cells), default=0),
    }


def cell_pairs(data: dict, a: int, b: int) -> list[dict]:
    """The passages of the cell `{a, b}`, in served order; `(b, a)` answers as `(a, b)`.

    `[{"u", "v", "wa", "wb", "k", "roots"}]` with `u` in `min(a, b)`, ordered
    by `k` descending, then `(u, v)` numerically. An empty cell is `[]`.
    `a == b` raises `ValueError` — the map has no diagonal. Surah numbers are
    not range-checked: an out-of-range one is simply an empty cell.
    Raises `MalformedEntry` when the dataset is not in the D5 shape.
    """
    if a == b:
        raise ValueError(f"cell ({a}, {b}) is on the diagonal; the map has none")
    lo, hi = (a, b) if a < b else (b, a)
    agg = _aggregated(data)
    pairs = agg["pairs"]
    return [_entry(u, v, pairs[(u, v)]) for u, v in agg["cells"].get((lo, hi), [])]
