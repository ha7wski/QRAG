"""
quran_close_verses.py — the pure reader of the unified cross-surah relation.

Behind GET /verse/{surah}/{ayah}/similar (one verse's close verses in the other
surahs, quarantined), GET /surah/{number}/annotations (a surah's close verses,
per ayah, for the reading page), GET /quran-similarity/matrix (the surah × surah map) and
GET /quran-similarity/pairs/{a}/{b} (one cell's pairs). Change
`unify-close-verses`, design D6–D7: it replaces the two readers of the input
relations (`quran_similarity.py`, `quran_passages.py`), which no route reads
any more.

The relation is answered once, offline, by `scripts/build_quran_close_verses.py`
— the union of the whole-verse similarity pairs and the shared-passage pairs,
each with its combined score and, when it has one, its common part already
placed as lists of character spans in each verse's DISPLAYED `text_ar_tashkil` (Basmala
stripped). Placing them at build time is what keeps `word_index.json` (64 MB
resident) off the request path: this module reads one small file.

It therefore loads no model, opens no Qdrant client, and imports nothing from
the project but `quran_data`. The dataset is reached through
`quran_data.loaders.quran_close_verses()` at CALL time (the module, then the
attribute), never at import: a backend without the file must still start, and a
request against it must become a 503 carrying the rebuild command.

Shape (D6, schema 2 — change `order-invariant-common-words`, D5):

    unscored = ["<s:a>", ...]          # no content root, and no pair → not compared
    pairs    = [{"a": "<s:a>", "b": "<s:a>",       # a in the LOWER surah
                 "score", "sim", "pas", "from": [...], "roots": [str],
                 "k", "wa", "wb",                  # the PASSAGE's own figures: present
                                                   # exactly when "passage" in from
                 "m": [[p, q, "lemma"|"root"], ...],   # the common part: the matched
                 "ca": [[s, e], ...],                  # words (p in a, q in b, sorted
                 "cb": [[s, e], ...]}]                 # by p) and one char span per
                                                       # coloured run in each verse;
                                                       # all three or none

The common part is the order-invariant matching of the two verses' content
words, not one contiguous span: a verse may carry several runs, so every view
serves a LIST of spans (`spans_u` / `spans_v`, `spans`, `spans_self` /
`spans_other`), and `words` is `len(m)` — the matched content words, never the
passage's `k`. `k` / `wa` / `wb` are validated (`pas` reads `k`) but not served.

The relation is a PAIR SET, so the per-verse list is every pair holding the
verse — not capped at K: a cap would make the panel disagree with the map.
Everything is derived from one validated aggregate, memoised per loaded dict
(one slot, locked): computed once per process in production, recomputed for a
different dict (a test fixture, a reloaded file).
"""
from __future__ import annotations

import math
import re
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quran_data import loaders  # noqa: E402

REBUILD = "python scripts/build_quran_close_verses.py"

_FROM = ("similarity", "passage")
_COMMON = ("m", "ca", "cb")
_PASSAGE = ("k", "wa", "wb")
_KINDS = ("lemma", "root")
# D4 / spec `close-verses`: a pair carries a common part only when the matching
# joins at least 2 words. A shape rule of the contract, like `_KINDS`; the build
# records the same figure as `mark_min` in its header.
_MARK_MIN = 2
_SURAHS = range(1, 115)


class MalformedEntry(LookupError):
    """The dataset is not in the D6 shape (a missing key, a wrong type, a broken rule).

    The schema number matched, so the file was written by a builder that broke
    its own contract, or edited by hand. It is a 503 carrying the rebuild
    command — never a 500 out of a bare `KeyError`.
    """


_MALFORMED = (KeyError, TypeError, ValueError, AttributeError, IndexError)


def load() -> dict:
    """The whole dataset, through its one cached loader.

    Raises `quran_data.loaders.DatasetMissing` when the file is absent and
    `loaders.UnknownSchema` (a `ValueError`) on an unknown schema — both carry
    the rebuild command, and the route turns both into a 503.
    """
    return loaders.quran_close_verses()


def _malformed(where, exc: Exception) -> MalformedEntry:
    return MalformedEntry(
        f"quran_close_verses.json holds a malformed entry at {where!r} "
        f"({type(exc).__name__}: {exc}); the dataset is corrupt or stale. "
        f"Rebuild it with:\n    {REBUILD}"
    )


# ── field validators: each raises one of `_MALFORMED` ─────────────────────

# The canonical spelling only: `int()` alone would read " 2:1" and "2:+1" as
# 2:1, and "2:1_0" as 2:10 — a silent pointer to ANOTHER verse, not a 503.
_REF = re.compile(r"([1-9][0-9]*):([1-9][0-9]*)")


def _ref(raw) -> tuple[int, int]:
    """`"s:a"` → `(s, a)` with a surah in 1..114 and an ayah ≥ 1, digits only."""
    if not isinstance(raw, str):
        raise TypeError(f"ref {raw!r} is not a string")
    match = _REF.fullmatch(raw)
    if match is None:
        raise ValueError(f"ref {raw!r} is not of the form \"s:a\"")
    surah, ayah = int(match[1]), int(match[2])
    if surah not in _SURAHS or ayah < 1:
        raise ValueError(f"ref {raw!r} names no verse of the Quran")
    return surah, ayah


def _score(value, name: str) -> float:
    """A finite number in [0, 1]; anything else raises.

    `json.load` accepts `NaN` / `Infinity`, and a non-finite float would turn
    into a 500 when the response is serialised; a `bool` is an `int` to Python
    and would be served as 1.0. Both are a corrupt file, not a score.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} {value!r} is not a number")
    score = float(value)
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError(f"{name} {value!r} is not a finite number in [0, 1]")
    return score


def _roots(value) -> tuple[str, ...]:
    """The shared content roots: a list of non-empty str, possibly EMPTY (D6).

    A bare string would otherwise be split into its letters by `list()`. Unlike
    the similarity relation, an empty list is legal here: a passage-only pair
    has its roots computed by the similarity definition, which may share none.
    """
    if not isinstance(value, list) or not all(isinstance(r, str) and r for r in value):
        raise TypeError(f"roots {value!r} is not a list of non-empty str")
    return tuple(value)


def _from(value) -> tuple[str, ...]:
    """Which input holds the pair: `["similarity"]`, `["passage"]` or both, in that order."""
    if not isinstance(value, list) or not value or len(set(value)) != len(value) \
            or not all(v in _FROM for v in value) \
            or list(value) != sorted(value, key=_FROM.index):
        raise ValueError(f"from {value!r} is not one of {list(_FROM)!r}'s non-empty subsets")
    return tuple(value)


def _int(value, name: str, low: int) -> int:
    """An int ≥ `low`; a `bool` (an `int` to Python) or anything else is malformed."""
    if isinstance(value, bool) or not isinstance(value, int) or value < low:
        raise TypeError(f"{name} {value!r} is not an integer >= {low}")
    return value


def _words(value, name: str) -> tuple[int, int]:
    """A 1-based inclusive word span `[first, last]`, `1 ≤ first ≤ last`."""
    if not isinstance(value, list) or len(value) != 2:
        raise TypeError(f"{name} {value!r} is not a [first, last] pair")
    first, last = _int(value[0], name, 1), _int(value[1], name, 1)
    if first > last:
        raise ValueError(f"{name} {value!r} ends before it starts")
    return first, last


def _chars(value, name: str) -> tuple[int, int]:
    """A half-open character span `[start, end)`, `0 ≤ start < end`."""
    if not isinstance(value, list) or len(value) != 2:
        raise TypeError(f"{name} {value!r} is not a [start, end] pair")
    start, end = _int(value[0], name, 0), _int(value[1], name, 0)
    if start >= end:
        raise ValueError(f"{name} {value!r} is empty or reversed")
    return start, end


def _spans(value, name: str, matched: int) -> tuple[tuple[int, int], ...]:
    """A non-empty list of half-open spans, one per coloured run, strictly apart.

    Two runs are separated by at least one plain word, so a span that starts
    where the previous one ends is one run written as two: refused, like an
    overlap. Every run holds at least one matched word (a bridged word lies
    between two matched ones, D3), so a verse cannot have more runs than `m`
    has matches.
    """
    if not isinstance(value, list) or not value:
        raise TypeError(f"{name} {value!r} is not a non-empty list of [start, end] spans")
    spans = tuple(_chars(span, name) for span in value)
    for (_, end), (start, _) in zip(spans, spans[1:]):
        if start <= end:
            raise ValueError(f"{name} {value!r} is not ascending with a gap between runs")
    if len(spans) > matched:
        raise ValueError(f"{name} holds {len(spans)} runs for {matched} matched words; "
                         f"every run holds at least one matched word")
    return spans


def _matches(value) -> tuple[tuple[int, int, str], ...]:
    """`m`: `[[p, q, "lemma"|"root"], ...]`, ≥ `_MARK_MIN` long, sorted by `p`, one-to-one.

    `p` / `q` are 1-based word numbers in `a` / `b`; a word appears in at most
    one pair on each side (the matching is one-to-one, D2).
    """
    if not isinstance(value, list) or len(value) < _MARK_MIN:
        raise TypeError(f"m {value!r} is not a list of at least {_MARK_MIN} [p, q, kind] "
                        f"triples (D4: fewer matched words is no common part)")
    out = []
    for entry in value:
        if not isinstance(entry, list) or len(entry) != 3:
            raise TypeError(f"m entry {entry!r} is not a [p, q, kind] triple")
        p, q, kind = _int(entry[0], "m.p", 1), _int(entry[1], "m.q", 1), entry[2]
        if kind not in _KINDS:
            raise ValueError(f"m entry {entry!r}: kind is not one of {list(_KINDS)!r}")
        out.append((p, q, kind))
    ps, qs = [e[0] for e in out], [e[1] for e in out]
    if any(x >= y for x, y in zip(ps, ps[1:])):
        raise ValueError(f"m {value!r} is not sorted by p with each p once")
    if len(set(qs)) != len(qs):
        raise ValueError(f"m {value!r} matches a word of b twice; the matching is one-to-one")
    return tuple(out)


def _passage(p: dict, frm: tuple[str, ...]) -> None:
    """`k` / `wa` / `wb` — the passage's own figures — present exactly when it is one."""
    present = [f for f in _PASSAGE if f in p]
    if "passage" in frm:
        if len(present) != len(_PASSAGE):
            raise ValueError(f"a passage pair lacks {[f for f in _PASSAGE if f not in p]}")
        _int(p["k"], "k", 1)
        _words(p["wa"], "wa")
        _words(p["wb"], "wb")
    elif present:
        raise ValueError(f"{present} are the passage's figures, yet the pair is not a passage")


def _common(p: dict, frm: tuple[str, ...]) -> dict | None:
    """The common part — `{m, ca, cb}` — or None; the three travel together.

    A passage pair always has one (D4: its alignment holds ≥ 3 content matches,
    all of which the matching can take), so a passage without it is a broken
    build — served, it would colour nothing and show no marker.
    """
    present = [f for f in _COMMON if f in p]
    if not present:
        if "passage" in frm:
            raise ValueError("a passage pair lacks its common part (m / ca / cb); "
                             "D4: a passage always has one")
        return None
    if len(present) != len(_COMMON):
        missing = [f for f in _COMMON if f not in p]
        raise ValueError(f"common part has {present} but lacks {missing}; "
                         f"the three fields are present together or absent together")
    m = _matches(p["m"])
    return {"m": m, "ca": _spans(p["ca"], "ca", len(m)), "cb": _spans(p["cb"], "cb", len(m))}


# ── the aggregate ─────────────────────────────────────────────────────────

def _aggregate(data: dict) -> dict:
    """The validated pairs, grouped by surah cell and by verse.

    Returns:
      * `pairs`  — `{(u, v): {"score", "roots", "common", "from"}}`, `u`, `v` as
        `(surah, ayah)`, `surah(u) < surah(v)`;
      * `cells`  — `{(a, b): [(u, v), ...]}`, each list in served order
        (score desc, then `(u, v)`);
      * `by_ref` — `{verse: [(other, (u, v)), ...]}`, each list in served order
        (score desc, then `other`), so `ayah_view` costs only its own pairs;
      * `unscored` — the set of unscored verses.

    The whole file is validated once, here: any broken entry is a
    `MalformedEntry` for every route, which is what a corrupt file is.
    """
    raw = data.get("pairs") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise _malformed("pairs", TypeError("pairs is not a list"))
    pairs: dict[tuple, dict] = {}
    for n, p in enumerate(raw):
        try:
            u, v = _ref(p["a"]), _ref(p["b"])
            if u[0] >= v[0]:
                raise ValueError(f"{p['a']} / {p['b']}: `a` must lie in the LOWER surah "
                                 f"(the relation holds no same-surah pair)")
            if (u, v) in pairs:
                raise ValueError(f"{p['a']} / {p['b']} is listed twice; one entry per pair")
            _score(p["sim"], "sim")
            _score(p["pas"], "pas")
            frm = _from(p["from"])
            _passage(p, frm)
            pairs[(u, v)] = {"score": _score(p["score"], "score"),
                             "roots": _roots(p["roots"]), "common": _common(p, frm),
                             "from": frm}
        except _MALFORMED as exc:
            raise _malformed(f"pairs[{n}]", exc) from exc

    raw_unscored = data.get("unscored", [])
    if not isinstance(raw_unscored, list):
        raise _malformed("unscored", TypeError("unscored is not a list"))
    unscored = set()
    for n, ref in enumerate(raw_unscored):
        try:
            unscored.add(_ref(ref))
        except _MALFORMED as exc:
            raise _malformed(f"unscored[{n}]", exc) from exc

    cells: dict[tuple[int, int], list[tuple]] = {}
    by_ref: dict[tuple[int, int], list[tuple]] = {}
    for pair in pairs:
        u, v = pair
        cells.setdefault((u[0], v[0]), []).append(pair)
        by_ref.setdefault(u, []).append((v, pair))
        by_ref.setdefault(v, []).append((u, pair))
    for members in cells.values():
        members.sort(key=lambda q: (-pairs[q]["score"], q))
    for members in by_ref.values():
        members.sort(key=lambda m: (-pairs[m[1]]["score"], m[0]))

    clash = sorted(unscored & by_ref.keys())
    if clash:
        s, a = clash[0]
        raise _malformed("unscored", ValueError(
            f"{s}:{a} is listed as unscored yet holds a pair; the unscored list "
            f"excludes every verse holding a pair"))
    return {"pairs": pairs, "cells": cells, "by_ref": by_ref, "unscored": unscored}


# One slot: the dict last aggregated and its result. Holding the dict itself
# (not only its `id`) keeps that id from being reused by another object while
# the slot is alive, so an identity check is enough.
_memo: tuple[dict, dict] | None = None
_memo_lock = threading.Lock()


def _aggregated(data: dict) -> dict:
    """`_aggregate(data)`, memoised on the identity of `data`.

    The dataset is treated as read-only: a caller that mutated the loaded dict
    in place would be served the stale aggregate.
    """
    global _memo
    with _memo_lock:
        if _memo is not None and _memo[0] is data:
            return _memo[1]
        result = _aggregate(data)
        _memo = (data, result)
        return result


# ── served views: fresh objects, the memoised aggregate is shared ─────────

def _verse(ref: tuple[int, int]) -> dict:
    return {"surah": ref[0], "ayah": ref[1]}


def _side(common: dict | None, field: str) -> list[list[int]] | None:
    """One side's spans as FRESH lists (the aggregate is shared), or None."""
    return [list(span) for span in common[field]] if common else None


def _count(common: dict | None) -> int | None:
    """The matched content words — `len(m)`; bridged function words do not count (D3)."""
    return len(common["m"]) if common else None


def _pair(u: tuple, v: tuple, p: dict) -> dict:
    """One served pair: `words`, `spans_u`, `spans_v` from the common part, or all None."""
    common = p["common"]
    return {
        "u": _verse(u), "v": _verse(v), "score": p["score"], "roots": list(p["roots"]),
        "words": _count(common),
        "spans_u": _side(common, "ca"),
        "spans_v": _side(common, "cb"),
    }


def _oriented(pair: tuple, anchor: tuple) -> tuple[str, str]:
    """`(this verse's field, the partner's field)` — `ca` belongs to the pair's `u`."""
    return ("ca", "cb") if pair[0] == anchor else ("cb", "ca")


def ayah_view(data: dict, surah: int, ayah: int) -> dict:
    """One verse's close verses in the other surahs: EVERY pair holding it.

    Returns `{"unscored": bool, "neighbours": [{"surah", "ayah", "score",
    "roots", "words", "spans"}]}`, ordered by score descending then
    `(surah, ayah)`; `spans` is the common part's list of character spans in the
    NEIGHBOUR's displayed text, `words` its matched word count — both None when
    the pair has no common part. Not capped: the list is exactly the map's pairs
    holding this verse.

    An unscored anchor yields `unscored: True` and no neighbours; a scored
    anchor with no close verse yields `unscored: False` and no neighbours.
    Neither is an error — the client words them differently.

    The ref is NOT range-checked here: the dataset holds no ayah count, and the
    route already knows the surah's length from the corpus (a 404 there).
    Raises `MalformedEntry` when the dataset is not in the D6 shape.
    """
    agg = _aggregated(data)
    anchor = (surah, ayah)
    if anchor in agg["unscored"]:
        return {"unscored": True, "neighbours": []}
    neighbours = []
    for other, pair in agg["by_ref"].get(anchor, []):
        p = agg["pairs"][pair]
        common = p["common"]
        _, theirs = _oriented(pair, anchor)
        neighbours.append({
            "surah": other[0], "ayah": other[1], "score": p["score"],
            "roots": list(p["roots"]), "words": _count(common),
            "spans": _side(common, theirs),
        })
    return {"unscored": False, "neighbours": neighbours}


def surah_partners(data: dict, surah: int) -> dict[int, list[dict]]:
    """Every pair holding a verse of `surah`, grouped by that verse's ayah.

    `{ayah: [{"surah", "ayah", "score", "from", "words", "spans_self",
    "spans_other"}]}` — only the ayahs holding at least one pair, each list in the
    served order of `ayah_view` (score descending, then the partner's
    `(surah, ayah)`). `from` is the pair's relation list (`["similarity"]`,
    `["passage"]` or both); `spans_self` is the common part's list of character
    spans in THIS verse's displayed text, `spans_other` in the partner's, `words`
    its matched word count — all three None when the pair has no common part.

    Behind GET /surah/{number}/annotations, which needs a whole surah at once and
    serves every pair in one `cross` list whatever its relation: the reading page
    shows ONE orange cue (the marker, plus the common part's words) for all of them
    (unify-cross-closeness-cue D8). `from` is kept for audits, not read by the
    route. The surah is NOT range-checked: an out-of-range one simply holds no
    pair. Raises `MalformedEntry` when the dataset is not in the D6 shape.
    """
    agg = _aggregated(data)
    out: dict[int, list[dict]] = {}
    for anchor in sorted(r for r in agg["by_ref"] if r[0] == surah):
        partners = []
        for other, pair in agg["by_ref"][anchor]:
            p = agg["pairs"][pair]
            common = p["common"]
            mine, theirs = _oriented(pair, anchor)
            partners.append({
                "surah": other[0], "ayah": other[1], "score": p["score"],
                "from": list(p["from"]),
                "words": _count(common),
                "spans_self": _side(common, mine),
                "spans_other": _side(common, theirs),
            })
        out[anchor[1]] = partners
    return out


def pair_set(data: dict) -> list[dict]:
    """Every pair, `u` in the lower-numbered surah, ordered by `(u, v)`.

    `[{"u": {"surah", "ayah"}, "v": {...}, "score", "roots", "words", "spans_u",
    "spans_v"}]` — `spans_u` indexes `u`'s displayed text, `spans_v` `v`'s.
    Raises `MalformedEntry` when the dataset is not in the D6 shape.
    """
    pairs = _aggregated(data)["pairs"]
    return [_pair(u, v, pairs[(u, v)]) for u, v in sorted(pairs)]


def matrix(data: dict) -> dict:
    """The non-empty surah cells and the totals.

    `{"cells": [{"a", "b", "pairs", "verses_a", "verses_b"}], "total_pairs",
    "max_pairs"}` — `a < b`, ordered by `(a, b)`, empty cells absent (sparse:
    the client draws the mirror and the empty background). `verses_a` /
    `verses_b` count the distinct verses of each side taking part.
    `sum(pairs) == total_pairs` by construction.
    Raises `MalformedEntry` when the dataset is not in the D6 shape.
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

    Each as in `pair_set`, `u` in `min(a, b)`, ordered by score descending, then
    `(u, v)` numerically. An empty cell is `[]`, not an error. `a == b` raises
    `ValueError` — the map has no diagonal (the route turns it into a 422 before
    reaching here). Surah numbers are NOT range-checked: an out-of-range one is
    simply an empty cell. Raises `MalformedEntry` when the dataset is not in the
    D6 shape.
    """
    if a == b:
        raise ValueError(f"cell ({a}, {b}) is on the diagonal; the map has none")
    lo, hi = (a, b) if a < b else (b, a)
    agg = _aggregated(data)
    pairs = agg["pairs"]
    return [_pair(u, v, pairs[(u, v)]) for u, v in agg["cells"].get((lo, hi), [])]
