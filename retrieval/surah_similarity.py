"""
surah_similarity.py — the pure reader behind GET /surah/{number}/similar.

The intra-surah similarity question («which verses of THIS surah echo each
other?») is answered once, offline, by `scripts/build_surah_similarity.py`, and
shipped as `data/derived/surah_similarity.json`. Everything expensive — the
cross-encoder, the E5 vectors, the QAC syntactic signatures — happens there.
This module only reads the result and shapes it for one surah or one verse.

It therefore loads no model, opens no Qdrant client, and imports nothing from
the project but `quran_data`. The dataset is reached through
`quran_data.loaders.surah_similarity()` at CALL time (the module, then the
attribute), never at import: a backend without the file must still start, and a
request against it must become a 503 carrying the rebuild command — not a
startup failure.

Shapes (dataset design D10, schema 2 — `lex` replaced `cov` in order-invariant-closeness):

    surahs["<n>"] = {
        "unscored":   [ayah, ...],                       # no content root → not compared
        "groups":     [{"ayahs": [...], "strength": s}], # strongest first
        "neighbours": {"<ayah>": [{"a", "s", "sem", "syn", "ce", "dense", "lex", "roots",
                                          "verbatim"?}]},
    }

Order is the dataset's. The builder already sorts neighbours (score desc, ayah
asc) and groups (strength desc, first ayah asc), and already excluded
consecutive verses; re-sorting or re-filtering here would make the served
answer a second opinion on the build instead of the build itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quran_data import loaders  # noqa: E402


class AyahOutOfRange(ValueError):
    """An `ayah` outside 1..ayah_count of its surah (a 404 at the route)."""


class SurahNotInDataset(LookupError):
    """The dataset holds no entry for a valid surah — an incomplete or stale build."""


class MalformedEntry(LookupError):
    """A surah's entry is not in the D10 shape (a missing key, a wrong type).

    The schema number matched, so the file was written by a builder that broke
    its own contract, or edited by hand. Like a missing surah, it is a 503
    carrying the rebuild command — never a 500 out of a bare `KeyError`.
    """


_MALFORMED = (KeyError, TypeError, ValueError, AttributeError)


def _malformed(surah: int, exc: Exception) -> MalformedEntry:
    return MalformedEntry(
        f"surah_similarity.json holds a malformed entry for surah {surah} "
        f"({type(exc).__name__}: {exc}); the dataset is corrupt or stale. "
        f"Rebuild it with:\n    python scripts/build_surah_similarity.py"
    )


def load() -> dict:
    """The whole dataset, through its one cached loader.

    Raises `quran_data.loaders.DatasetMissing` when the file is absent and the
    loader's own `ValueError` subclass on an unknown schema — both carry the
    rebuild command, and the route turns both into a 503.
    """
    return loaders.surah_similarity()


def _surah_entry(data: dict, surah: int) -> dict:
    try:
        entry = data.get("surahs", {}).get(str(surah))
    except _MALFORMED as exc:
        raise _malformed(surah, exc) from exc
    if entry is None:
        raise SurahNotInDataset(
            f"surah_similarity.json holds no entry for surah {surah}; the build is "
            f"incomplete. Rebuild it with:\n    python scripts/build_surah_similarity.py"
        )
    return entry


def surah_view(data: dict, surah: int) -> dict:
    """A surah's groups and unscored ayahs, in dataset order.

    Returns `{"unscored": [int], "groups": [{"ayahs": [int], "strength": float}]}`.
    Raises `MalformedEntry` when the surah's entry is not in the D10 shape.
    """
    entry = _surah_entry(data, surah)
    try:
        return {
            "unscored": [int(a) for a in entry.get("unscored", [])],
            "groups": [
                {
                    "ayahs": [int(a) for a in g["ayahs"]],
                    "strength": float(g["strength"]),
                }
                for g in entry.get("groups", [])
            ],
        }
    except _MALFORMED as exc:
        raise _malformed(surah, exc) from exc


def ayah_view(data: dict, surah: int, ayah: int, ayah_count: int) -> dict:
    """One verse's close verses within its surah, in dataset order.

    Returns `{"unscored": bool, "neighbours": [{"ayah", "score", "roots"}]}`.
    An unscored anchor (no content root) yields `unscored: True` and no
    neighbours; a scored anchor with no close verse yields `unscored: False` and
    no neighbours. Neither is an error — the two states are worded differently
    by the client, so they must stay distinguishable.

    Raises `AyahOutOfRange` when `ayah` is not in 1..ayah_count, and
    `MalformedEntry` when the surah's entry is not in the D10 shape.
    """
    if not 1 <= ayah <= ayah_count:
        raise AyahOutOfRange(
            f"Ayah {ayah} is outside surah {surah} (1..{ayah_count})"
        )
    entry = _surah_entry(data, surah)
    try:
        unscored = ayah in {int(a) for a in entry.get("unscored", [])}
        if unscored:
            return {"unscored": True, "neighbours": []}
        raw = entry.get("neighbours", {}).get(str(ayah), [])
        return {
            "unscored": False,
            "neighbours": [
                {"ayah": int(n["a"]), "score": float(n["s"]),
                 "roots": list(n.get("roots", []))}
                for n in raw
            ],
        }
    except _MALFORMED as exc:
        raise _malformed(surah, exc) from exc
