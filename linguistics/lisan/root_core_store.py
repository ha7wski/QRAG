"""
root_core_store.py — offline reader for the curated attested root cores.

Answers `lookup(root)` with Ibn Fāris' aṣl(s) for a root, curated in
`data/references/root_cores.json` and read through `quran_data.loaders`.
Read-only, cached, NO network — the datasets are fixed, verified references.
Also serves the closed axis vocabulary (`axis_labels`, `antonym_map`), so the
pure selection step can receive the antonym links as an argument and stay
disk-free.

**Keys are the CANONICAL QAC root key** — the exact, hamza-bearing spelling
`retrieval.lexical_retriever.LexicalRetriever._canon` returns — never the folded
`normalize_root` form that `maqayis_asl.csv` (the dataset these cores were
curated FROM) is indexed on. This is the single most dangerous trap in the
feature and it is silent: 139 QAC root keys carry a hamza, a curated file keyed
on the fold matches none of them, and "no core found" is a NORMAL outcome here —
a large minority of roots have no curated core at all. A whole class of hamzated
roots would therefore degrade to the uncovered path looking exactly like every
other uncovered root, with nothing raising and nothing to notice. Hence: the
file is keyed canonically, and every lookup canonicalizes on the way in.

A geminate fallback bridges QAC's doubled orthography (`ابب`) to the contracted
spelling (`اب`) and back — the same bridge `linguistics/madar/maqayis_store.py`
carries. It is deliberately COPIED rather than imported: `lisan/` and `madar/`
are siblings, one of them is quarantined, and neither should be able to break
the other by editing its own helper.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402

# The two fields a curator must supply. `scripts/build_root_cores_seed.py` fills
# the citation half mechanically and leaves exactly these blank, so "seeded but
# not yet curated" is precisely `axes == []` or `polarity == ""`.
_CURATED_FIELDS = ("axes", "polarity")


def _is_curated(core: dict) -> bool:
    """A core is servable only once a human has read the citation.

    The seed script writes 1 285 entries with `axes: []` and `polarity: null`.
    Served as-is they would come back `constrained: true` with a reading in which
    no letter ever matches — structurally indistinguishable from a genuine
    all-unmatched reading, and silently immune to the divergence guard (an empty
    polarity short-circuits it). The spec's rule is that such an entry never
    reaches the product; this is where that is enforced at RUNTIME, not only in
    the offline validator, because the gap between a `--write` and the next
    `pytest` run is exactly where a seeded file would ship.
    """
    return bool(core.get("axes")) and bool(core.get("polarity"))


def _core(raw: dict) -> dict:
    """One dataset record → exactly the `api.models.lisan.RootCore` keys, in its order.

    An absent field becomes an empty string rather than an invented value — in
    particular an empty `polarity` is NOT rewritten to "neutral", which would
    make a half-curated core look finished. Such a core is dropped by
    `_is_curated` before it can be served; the normalization here only makes the
    incompleteness inspectable.
    """
    return {
        "gloss": str(raw.get("gloss") or ""),
        "verbatim": str(raw.get("verbatim") or ""),
        "axes": [str(a).strip() for a in (raw.get("axes") or []) if str(a).strip()],
        "polarity": str(raw.get("polarity") or ""),
        "source": str(raw.get("source") or ""),
        "edition": str(raw.get("edition") or ""),
    }


@lru_cache(maxsize=1)
def _load() -> dict[str, list[dict]]:
    """`{canonical root key: [core, ...]}`, cores in dataset order. Cached per process."""
    raw = loaders.root_cores() or {}
    out: dict[str, list[dict]] = {}
    for root, cores in (raw.get("roots") or {}).items():
        key = (root or "").strip()
        if not key:
            continue
        # Half-curated cores are dropped, not served. A root whose every core is
        # incomplete therefore has NO core at all and takes the uncovered path —
        # `constrained: false` plus the Arabic warning — which is the honest
        # outcome and the one the reader can act on.
        curated = [c for c in (_core(c) for c in cores or []) if _is_curated(c)]
        if curated:
            out[key] = curated
    return out


@lru_cache(maxsize=1)
def axis_labels() -> dict[str, str]:
    """Axis id → its Arabic label, for every axis in the closed vocabulary.

    Published so the UI can name the axes a selection matched without holding a
    copy of the vocabulary — a second copy is a second thing to drift.
    """
    axes = (loaders.semantic_axes() or {}).get("axes") or []
    return {a["id"]: a.get("label_ar", "") for a in axes if a.get("id")}


def _copy(mapping: dict[str, str]) -> dict[str, str]:
    """Hand out a copy of a cached map.

    `lookup` already copies for this reason — these dicts travel towards an HTTP
    response, and one caller annotating in place would poison every later request
    in the process. Leaving two of four cached accessors open was the gap."""
    return dict(mapping)


@lru_cache(maxsize=1)
def antonym_map() -> dict[str, str]:
    """Axis id → the id it is declared opposed to, for axes that declare one.

    This link is what separates «these two share no axis» from «these two are
    opposed». Without it, a sense carrying the exact contrary of the core's axis
    would merely fail to match, indistinguishable from an unrelated sense — and
    the `conflicting-axis` rejection reason, which is the honest one, could not
    exist.
    """
    axes = (loaders.semantic_axes() or {}).get("axes") or []
    return {a["id"]: a["antonym"] for a in axes if a.get("id") and a.get("antonym")}


def _geminate_variants(root: str) -> list[str]:
    """Orthographic bridges between a doubled geminate root and its contracted
    spelling: `اب` ↔ `ابب`. Empty for non-geminate shapes."""
    out: list[str] = []
    if len(root) == 2:                           # اب → ابب
        out.append(root + root[-1])
    elif len(root) == 3 and root[1] == root[2]:  # ابب → اب
        out.append(root[:2])
    return out


class RootCoreStore:
    """Cached, offline lookup of a root's attested core(s) by canonical key."""

    def __init__(self, resolver=None):
        # The shared `LexicalRetriever` — the object that OWNS the canonical
        # spellings, since it is the index they are stored in. Optional so the
        # store stays constructible (and smoke-testable) without loading
        # `morphology.json`; a lookup without one falls back to the raw key,
        # which is already canonical for the ~92% of roots carrying no hamza.
        self._resolver = resolver

    def _data(self) -> dict[str, list[dict]]:
        return _load()

    def _candidates(self, root: str, resolver=None) -> list[str]:
        """The keys to try, best first: canonical, raw, then their geminate variants."""
        res = resolver if resolver is not None else self._resolver
        keys: list[str] = []
        if res is not None:
            # `_canon` is private, and reaching it is the design's explicit
            # choice (D6/D10): the canonical spelling is defined by the index,
            # so re-deriving it here would be a second, drifting definition.
            # It returns "" for a root it does not know.
            canon = res._canon(root)
            if canon:
                keys.append(canon)
        if root not in keys:
            keys.append(root)
        for key in list(keys):
            keys.extend(v for v in _geminate_variants(key) if v not in keys)
        return keys

    def lookup(self, root: str, resolver=None) -> list[dict]:
        """Return this root's cores in dataset order, or an EMPTY LIST if absent.

        Never a placeholder core and never None-as-a-core: "no attested aṣl on
        record" is a designed, user-visible outcome (`constrained: false` plus an
        Arabic warning), not an error and not something to paper over with a
        default. A default core would constrain every letter of the root with an
        assertion nobody cited.
        """
        if not root:
            return []
        data = self._data()
        for key in self._candidates(root, resolver):
            cores = data.get(key)
            if cores:
                # Copied out of the process-wide cache: these dicts travel into
                # the response and a caller annotating one in place would poison
                # every later request for that root.
                return [{**c, "axes": list(c["axes"])} for c in cores]
        return []

    # Thin façades, so a caller holding only the store can reach the vocabulary
    # the eligibility rule needs without importing the module separately.
    def axis_labels(self) -> dict[str, str]:
        return _copy(axis_labels())

    def antonym_map(self) -> dict[str, str]:
        return _copy(antonym_map())


if __name__ == "__main__":
    store = RootCoreStore()
    for w in ["خير", "ظلم", "زقزقة"]:
        cores = store.lookup(w)
        if not cores:
            print(f"{w}: no core on record")
            continue
        print(f"{w}: {len(cores)} core(s)")
        for c in cores:
            print(f"    gloss={c['gloss']}  polarity={c['polarity']}")
            print(f"    verbatim={c['verbatim']}")
            print(f"    axes={','.join(c['axes'])}  source={c['source']}")
    labels = axis_labels()
    print(f"axis vocabulary: {len(labels)} axes, {len(antonym_map())} with an antonym")
