"""
maqayis_store.py — Offline reader for the Maqāyīs aṣl dataset.

Loads `data/references/maqayis_asl.csv` (built once by
`scripts/build_maqayis_dataset.py` from the OpenITI edition of Ibn Fāris'
*Muʿjam Maqāyīs al-Lugha*) and answers `lookup(root_normalized)`. Read-only,
cached, NO network at runtime — the dataset is a fixed, verified reference.

Keys are the hamza-safe `normalize_root` form, so a QAC root key looked up here
folds to the same key the builder stored. A geminate fallback bridges QAC's
doubled orthography (`ابب`) to Maqāyīs' contracted form (`اب`) and back.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.root_normalize import normalize_root  # noqa: E402

DEFAULT_CSV = ROOT / "data" / "references" / "maqayis_asl.csv"

# Sentinel joining several aṣl of one root inside the single `asl_text` cell
# (must match `scripts/build_maqayis_dataset.py::ASL_DELIM`). Never occurs in
# Arabic prose, so splitting on it is safe; a single-aṣl root has no sentinel.
ASL_DELIM = " ||| "


@dataclass(frozen=True)
class MaqayisEntry:
    """One root's aṣl record, as cited from Ibn Fāris (never paraphrased)."""

    root_normalized: str
    root_raw: str
    asl_text: str            # empty when asl_status == "no_asl"; ASL_DELIM-joined when multi-aṣl
    asl_count: int
    asl_status: str          # "has_asl" | "no_asl" | "parse_uncertain"
    source: str
    edition: str
    confidence: str
    # Ibn Fāris' own opening declaration (e.g. "الباء والعين واللام أصول ثلاثة"),
    # shown as a synthetic lead ABOVE the numbered aṣl list. "" for single-aṣl /
    # fallback / no_asl. Kept last with a default so older positional callers work.
    asl_preamble: str = ""

    def asl_list(self) -> list[str]:
        """The individual aṣl of this root as a list (0 for no_asl, ≥1 else)."""
        if not self.asl_text:
            return []
        return [s for s in self.asl_text.split(ASL_DELIM) if s.strip()]

    def to_dict(self) -> dict:
        """Serialize for the API `maqayis` field. `asl_text` is exposed as a
        LIST (0 entries for no_asl, ≥1 otherwise) so multi-aṣl roots render as a
        numbered list, led by `asl_preamble` when present."""
        return {
            "asl_text": self.asl_list(),
            "asl_preamble": self.asl_preamble,
            "asl_count": self.asl_count,
            "asl_status": self.asl_status,
            "source": self.source,
            "edition": self.edition,
        }


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, MaqayisEntry]:
    """Load the CSV once per path into a {root_normalized: MaqayisEntry} map."""
    data: dict[str, MaqayisEntry] = {}
    p = Path(path)
    if not p.exists():
        return data
    with p.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                count = int(row.get("asl_count") or 0)
            except ValueError:
                count = 0
            data[row["root_normalized"]] = MaqayisEntry(
                root_normalized=row["root_normalized"],
                root_raw=row.get("root_raw", ""),
                asl_text=row.get("asl_text", ""),
                asl_count=count,
                asl_status=row.get("asl_status", "parse_uncertain"),
                source=row.get("source", ""),
                edition=row.get("edition", ""),
                confidence=row.get("confidence", ""),
                asl_preamble=row.get("asl_preamble", ""),
            )
    return data


def _geminate_variants(root: str) -> list[str]:
    """Orthographic bridges between QAC's doubled geminate roots and Maqāyīs'
    contracted spelling: `اب` ↔ `ابب`. Empty for non-geminate shapes."""
    out: list[str] = []
    if len(root) == 2:                       # اب → ابب
        out.append(root + root[-1])
    elif len(root) == 3 and root[1] == root[2]:  # ابب → اب
        out.append(root[:2])
    return out


class MaqayisStore:
    """Cached, offline lookup of Ibn Fāris' aṣl by normalized root key."""

    def __init__(self, csv_path: str | Path | None = None):
        self._path = str(csv_path or DEFAULT_CSV)

    def _data(self) -> dict[str, MaqayisEntry]:
        return _load(self._path)

    def lookup(self, root_normalized: str) -> MaqayisEntry | None:
        """Return the aṢl entry for a normalized root, or None if absent.

        Re-normalizes the key defensively (so a caller passing a raw QAC root
        still hits), then tries the geminate orthographic variants."""
        if not root_normalized:
            return None
        key = normalize_root(root_normalized)
        data = self._data()
        entry = data.get(key)
        if entry is not None:
            return entry
        for cand in _geminate_variants(key):
            entry = data.get(cand)
            if entry is not None:
                return entry
        return None


if __name__ == "__main__":
    store = MaqayisStore()
    for w in ["لحد", "جعم", "جعن", "رحم", "كتب", "زقزقة"]:
        e = store.lookup(normalize_root(w))
        if e is None:
            print(f"{w}: no entry")
        else:
            print(f"{w}: [{e.asl_status} count={e.asl_count}] {e.asl_text or '(no aṣl)'}")
