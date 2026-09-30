"""
wasf.py — the closed مصدر → وصف table, refused unless it is the frozen one.

Position 2 of the physical-stage assembly is a qualifier, and a qualifier needs a
وصف where Islambouli's row gives a مصدر (ر «تكرار» → «مكرر»). The table that makes
that step is CLOSED and admitted by ONE morphological criterion, stated in its
lock before any entry was chosen: a مصدر gets an entry only when its اسم الفاعل
and اسم المفعول share one unvocalized spelling, so the table never chooses a
voice. A form I مصدر never qualifies (دافع / مدفوع), and a word without an entry
stays exactly as written — nothing is guessed.

The sha256 of the CSV is checked against the lock on load, and the ceiling of
20 entries is enforced: an entry added because a root reads better is the
failure this freeze exists to make visible.
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
from quran_data.paths import ISLAMBOULI_WASF_CSV  # noqa: E402

REQUIRED_FIELDS = ("masdar", "wasf", "form", "justification")


class WasfNotFrozen(RuntimeError):
    """The وصف table on disk is not the one the lock froze, or breaks its rules."""


@dataclass(frozen=True)
class SegmentNote:
    row: int
    label: str
    note: str


@dataclass(frozen=True)
class WasfTable:
    version: str
    sha256: str
    entries: dict[str, str]                 # masdar → wasf
    segment_notes: tuple[SegmentNote, ...]

    def get(self, word: str) -> str | None:
        return self.entries.get(word)


@lru_cache(maxsize=1)
def wasf_table() -> WasfTable:
    lock = loaders.islambouli_wasf_lock()
    digest = hashlib.sha256(ISLAMBOULI_WASF_CSV.read_bytes()).hexdigest()
    if digest != str(lock.get("sha256") or ""):
        raise WasfNotFrozen(
            f"islambouli_wasf.csv hashes to {digest[:12]}…, the lock froze "
            f"{str(lock.get('sha256'))[:12]}…. An entry changes only through a new "
            "lock version whose reason is morphological, never a root that reads better."
        )
    rows = loaders.islambouli_wasf()
    ceiling = int(lock.get("max_entries") or 0)
    if not rows or len(rows) > ceiling:
        raise WasfNotFrozen(f"islambouli_wasf.csv has {len(rows)} entries; the ceiling is {ceiling}.")
    entries: dict[str, str] = {}
    for r in rows:
        missing = [f for f in REQUIRED_FIELDS if not (r.get(f) or "").strip()]
        if missing:
            raise WasfNotFrozen(f"Entry {r!r} lacks {missing}: every entry carries its justification.")
        if r["masdar"] in entries:
            raise WasfNotFrozen(f"«{r['masdar']}» has two entries.")
        entries[r["masdar"]] = r["wasf"]
    notes = tuple(
        SegmentNote(row=int(n["row"]), label=n["label"], note=n["note"])
        for n in lock.get("segment_notes") or ()
    )
    return WasfTable(version=str(lock.get("version") or ""), sha256=digest,
                     entries=entries, segment_notes=notes)
