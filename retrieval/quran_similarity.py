"""
quran_similarity.py — the pure reader behind GET /verse/{surah}/{ayah}/similar.

The cross-surah similarity question («where else in the Quran is this said,
built the same way?») is answered once, offline, by
`scripts/build_quran_similarity.py`, and shipped as
`data/derived/quran_similarity.json`. Everything expensive — the cross-encoder,
the E5 vectors, the QAC syntactic signatures, the exact pre-filters over 19 M
pairs — happens there. This module only reads the result for one verse.

It therefore loads no model, opens no Qdrant client, and imports nothing from
the project but `quran_data`. The dataset is reached through
`quran_data.loaders.quran_similarity()` at CALL time (the module, then the
attribute), never at import: a backend without the file must still start, and a
request against it must become a 503 carrying the rebuild command — not a
startup failure. It is a separate file from `surah_similarity.json` on purpose:
without it, the intra-surah view (`retrieval/surah_similarity.py`) still answers.

Shape (dataset design D7, schema 1), keyed by `"surah:ayah"` refs:

    unscored             = ["<s:a>", ...]           # no content root → not compared
    neighbours["<s:a>"]  = [{"r": "<s:a>", "s", "sem", "syn", "ce", "dense", "cov",
                             "roots", "verbatim"?}]  # only verses with ≥ 1 neighbour

Order is the dataset's. The builder already sorts neighbours (score desc, ref
asc) and already excluded the anchor's own surah; re-sorting or re-filtering
here would make the served answer a second opinion on the build instead of the
build itself.

The map (`pair_set`, `matrix`, `cell_pairs`) is an AGGREGATION of the same
lists, computed here at request time rather than shipped as a second file that
could drift from the one it summarises (change `add-cross-surah-similarity-map`,
D1–D2). A pair is the unordered `{u, v}`, present when either verse lists the
other — the lists are top-K, so the relation is not always mutual — and counted
once. It is memoised per loaded dict: the loader is process-cached, so in
production it is computed once; a different dict (a test fixture, a reloaded
file) is recomputed.
"""
from __future__ import annotations

import math
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quran_data import loaders  # noqa: E402


class MalformedEntry(LookupError):
    """The dataset is not in the D7 shape for this verse (a missing key, a wrong type).

    The schema number matched, so the file was written by a builder that broke
    its own contract, or edited by hand. It is a 503 carrying the rebuild
    command — never a 500 out of a bare `KeyError`.
    """


_MALFORMED = (KeyError, TypeError, ValueError, AttributeError)


def _malformed(surah: int, ayah: int, exc: Exception) -> MalformedEntry:
    return MalformedEntry(
        f"quran_similarity.json holds a malformed entry for {surah}:{ayah} "
        f"({type(exc).__name__}: {exc}); the dataset is corrupt or stale. "
        f"Rebuild it with:\n    python scripts/build_quran_similarity.py"
    )


def load() -> dict:
    """The whole dataset, through its one cached loader.

    Raises `quran_data.loaders.DatasetMissing` when the file is absent and the
    loader's own `ValueError` subclass on an unknown schema — both carry the
    rebuild command, and the route turns both into a 503.
    """
    return loaders.quran_similarity()


def _parse_ref(ref: str) -> tuple[int, int]:
    """`"s:a"` → `(s, a)`; anything else raises one of `_MALFORMED`."""
    surah, ayah = ref.split(":")
    return int(surah), int(ayah)


def _score(value) -> float:
    """A served score: a finite number in [0, 1]; anything else raises `ValueError`.

    `json.load` accepts `NaN` / `Infinity`, and a non-finite float would turn
    into a 500 when the response is serialised; a `bool` is an `int` to Python
    and would be served as 1.0. Both are a corrupt file, not a score.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"score {value!r} is not a number")
    score = float(value)
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError(f"score {value!r} is not a finite number in [0, 1]")
    return score


def _roots(value) -> list[str]:
    """The shared content roots: a non-empty list of str, else `TypeError`/`ValueError`.

    A bare string would otherwise be split into its letters by `list()`, and a
    neighbour shares at least one content root by construction (the spec).
    """
    if not isinstance(value, list) or not all(isinstance(r, str) and r for r in value):
        raise TypeError(f"roots {value!r} is not a list of non-empty str")
    if not value:
        raise ValueError("roots is empty; a neighbour shares at least one content root")
    return list(value)


def ayah_view(data: dict, surah: int, ayah: int) -> dict:
    """One verse's close verses in the other surahs, in dataset order.

    Returns `{"unscored": bool, "neighbours": [{"surah", "ayah", "score",
    "roots"}]}`. An unscored anchor (no content root) yields `unscored: True`
    and no neighbours; a scored anchor with no close verse yields
    `unscored: False` and no neighbours. Neither is an error — the two states
    are worded differently by the client, so they must stay distinguishable.

    The ref is NOT range-checked here: the dataset holds no ayah count, and the
    route already knows the surah's length from the corpus (a 404 there).
    Raises `MalformedEntry` when the dataset is not in the D7 shape.
    """
    key = f"{surah}:{ayah}"
    try:
        if key in set(data.get("unscored", [])):
            return {"unscored": True, "neighbours": []}
        raw = data.get("neighbours", {}).get(key, [])
        neighbours = []
        for n in raw:
            s, a = _parse_ref(n["r"])
            neighbours.append(
                {"surah": s, "ayah": a, "score": _score(n["s"]),
                 "roots": _roots(n["roots"])}
            )
        return {"unscored": False, "neighbours": neighbours}
    except _MALFORMED as exc:
        raise _malformed(surah, ayah, exc) from exc


# ── the surah × surah map ─────────────────────────────────────────────────

_SURAHS = range(1, 115)


def _ref_in_range(ref: str) -> tuple[int, int]:
    """`_parse_ref`, plus a surah in 1..114 and an ayah ≥ 1 (a cell needs a real surah)."""
    surah, ayah = _parse_ref(ref)
    if surah not in _SURAHS or ayah < 1:
        raise ValueError(f"ref {ref!r} names no verse of the Quran")
    return surah, ayah


def _malformed_key(key, exc: Exception) -> MalformedEntry:
    return MalformedEntry(
        f"quran_similarity.json holds a malformed entry under {key!r} "
        f"({type(exc).__name__}: {exc}); the dataset is corrupt or stale. "
        f"Rebuild it with:\n    python scripts/build_quran_similarity.py"
    )


def _aggregate(data: dict) -> dict:
    """Every distinct cross-surah pair, and the pairs grouped by surah cell.

    Returns `{"pairs": {(u, v): (score, roots)}, "cells": {(a, b): [(u, v), ...]}}`
    with `u < v` as `(surah, ayah)` tuples and `a = surah(u) < b = surah(v)`;
    each cell's list is already in served order (score desc, then (u, v)).

    A pair listed by both of its verses carries the same score and roots on both
    sides (the score is symmetric by construction). Should a rebuilt file ever
    disagree, the higher score wins — so the answer does not depend on which
    verse the dict happens to iterate first.
    """
    neighbours = data.get("neighbours", {})
    if not isinstance(neighbours, dict):
        raise _malformed_key("neighbours", TypeError("neighbours is not an object"))
    pairs: dict[tuple, tuple[float, tuple[str, ...]]] = {}
    for key, raw in neighbours.items():
        try:
            anchor = _ref_in_range(key)
            if not isinstance(raw, list):
                raise TypeError(f"neighbour list {raw!r} is not a list")
            for n in raw:
                other = _ref_in_range(n["r"])
                if other[0] == anchor[0]:
                    # The builder excludes the anchor's own surah; a same-surah
                    # entry would put a cell on the diagonal the map never has.
                    raise ValueError(f"neighbour {n['r']!r} is in the anchor's own surah")
                score, roots = _score(n["s"]), tuple(_roots(n["roots"]))
                pair = (anchor, other) if anchor < other else (other, anchor)
                seen = pairs.get(pair)
                if seen is None or score > seen[0]:
                    pairs[pair] = (score, roots)
        except _MALFORMED as exc:
            raise _malformed_key(key, exc) from exc

    cells: dict[tuple[int, int], list[tuple]] = {}
    for pair in pairs:
        cells.setdefault((pair[0][0], pair[1][0]), []).append(pair)
    for members in cells.values():
        members.sort(key=lambda p: (-pairs[p][0], p))
    return {"pairs": pairs, "cells": cells}


# One slot: the dict last aggregated and its result. Holding the dict itself
# (not only its `id`) keeps that id from being reused by another object while
# the slot is alive, so an identity check is enough.
_memo: tuple[dict, dict] | None = None
_memo_lock = threading.Lock()


def _aggregated(data: dict) -> dict:
    """`_aggregate(data)`, memoised on the identity of `data`.

    The dataset is treated as read-only (as `ayah_view` already does): a caller
    that mutated the loaded dict in place would be served the stale aggregate.
    """
    global _memo
    with _memo_lock:
        if _memo is not None and _memo[0] is data:
            return _memo[1]
        result = _aggregate(data)
        _memo = (data, result)
        return result


def _verse(ref: tuple[int, int]) -> dict:
    return {"surah": ref[0], "ayah": ref[1]}


def pair_set(data: dict) -> list[dict]:
    """Every distinct cross-surah pair, `u` in the lower-numbered surah.

    `[{"u": {"surah", "ayah"}, "v": {...}, "score", "roots"}]`, ordered by
    `(u, v)`. Fresh objects on every call: the memoised aggregate is shared
    by every request and must not be mutated through what is returned.
    Raises `MalformedEntry` when the dataset is not in the D7 shape.
    """
    pairs = _aggregated(data)["pairs"]
    return [
        {"u": _verse(u), "v": _verse(v), "score": pairs[(u, v)][0],
         "roots": list(pairs[(u, v)][1])}
        for u, v in sorted(pairs)
    ]


def matrix(data: dict) -> dict:
    """The non-empty surah cells and the totals.

    `{"cells": [{"a", "b", "pairs", "verses_a", "verses_b"}], "total_pairs",
    "max_pairs"}` — `a < b`, ordered by `(a, b)`, empty cells absent (sparse:
    the client draws the mirror and the empty background). `verses_a` /
    `verses_b` count the distinct verses of each side taking part, so «31 pairs»
    can read as «1 verse × 31». `sum(pairs) == total_pairs` by construction.
    Raises `MalformedEntry` when the dataset is not in the D7 shape.
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
    """The pairs of the cell `{a, b}`, in served order; `(b, a)` answers as `(a, b)`.

    `[{"u": {"surah", "ayah"}, "v": {...}, "score", "roots"}]` with `u` in
    `min(a, b)`, ordered by score descending, then `(u, v)` numerically. An
    empty cell is `[]`, not an error. `a == b` raises `ValueError` — the map has
    no diagonal (the route turns it into a 422 before reaching here). Surah
    numbers are NOT range-checked: an out-of-range one is simply an empty cell.
    Raises `MalformedEntry` when the dataset is not in the D7 shape.
    """
    if a == b:
        raise ValueError(f"cell ({a}, {b}) is on the diagonal; the map has none")
    lo, hi = (a, b) if a < b else (b, a)
    agg = _aggregated(data)
    pairs = agg["pairs"]
    return [
        {"u": _verse(u), "v": _verse(v), "score": pairs[(u, v)][0],
         "roots": list(pairs[(u, v)][1])}
        for u, v in agg["cells"].get((lo, hi), [])
    ]
