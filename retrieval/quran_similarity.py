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
"""
from __future__ import annotations

import math
import sys
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
