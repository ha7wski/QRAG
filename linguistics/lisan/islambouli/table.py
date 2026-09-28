"""
table.py — the transcribed table, refused unless it is the frozen one.

The composer reads ONE dataset, `islambouli_letters.csv`, and only through this
module. On load, the sha256 of the CSV bytes is compared with the lock. A table
that has moved since it was frozen raises instead of reading: a reading built on
a table that is no longer Islambouli's as transcribed would be the project
speaking in his name.
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from quran_data.paths import ISLAMBOULI_LETTERS_CSV  # noqa: E402


class TableNotFrozen(RuntimeError):
    """The table on disk is not the one the lock froze."""


@dataclass(frozen=True)
class Row:
    row: int                  # the poster's own index, 0–28
    label: str                # as printed: "ء", "هـ", "آ - ى", …
    text: str                 # the gloss, verbatim up to whitespace


@dataclass(frozen=True)
class Table:
    version: str
    sha256: str
    rows: tuple[Row, ...]

    def by_label(self) -> dict[str, Row]:
        return {r.label: r for r in self.rows}


@lru_cache(maxsize=1)
def table() -> Table:
    lock = loaders.islambouli_letters_lock()
    digest = hashlib.sha256(ISLAMBOULI_LETTERS_CSV.read_bytes()).hexdigest()
    if digest != str(lock.get("sha256") or ""):
        raise TableNotFrozen(
            f"islambouli_letters.csv hashes to {digest[:12]}…, the lock froze "
            f"{str(lock.get('sha256'))[:12]}…. The table is transcribed, not "
            "curated: it changes only through a new lock version that corrects a "
            "copy error proved on the image."
        )
    rows = tuple(
        Row(row=int(r["row"]), label=r["label_as_printed"], text=r["text"])
        for r in loaders.islambouli_letters()
    )
    return Table(version=str(lock.get("version") or ""), sha256=digest, rows=rows)
