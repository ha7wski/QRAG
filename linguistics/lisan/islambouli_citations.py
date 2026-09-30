"""
islambouli_citations.py — what Islambouli himself published for a root, verbatim.

The citations hold MEANING — a cultural stage is precisely what none of the three
letter rows contains — so this module lives OUTSIDE `linguistics/lisan/islambouli/`,
whose modules are blind by an import edge (`tests/test_import_direction.py` bans
this file's dataset name there). Nothing here composes, infers or completes a stage:
a root absent from the file has no cited stage, and the page shows nothing for it.

The file and every witness image are digest-checked on load. `development_cases`
names the roots used to accept the assembly template; they count in no measurement.
"""
from __future__ import annotations

import hashlib
import sys
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from quran_data.paths import ISLAMBOULI_CITATIONS_JSON  # noqa: E402

STAGES = ("physical", "cultural")
FORMULA = "تدل على"
_EDGE_MARKS = "،,.()«»:"


class CitationsNotFrozen(RuntimeError):
    """The citations file, or one of its witnesses, is not the frozen one."""


@dataclass(frozen=True)
class Citation:
    id: str
    root: str
    stage: str
    label: str
    label_as_printed: str
    text: str
    reading_note: str
    source: dict

    @property
    def statement(self) -> str:
        """What the sentence says the root indicates: the text after «تدل على»."""
        at = self.text.find(FORMULA)
        return self.text[at + len(FORMULA):].strip() if at >= 0 else self.text


@dataclass(frozen=True)
class Citations:
    version: str
    development_cases: frozenset[str]
    entries: tuple[Citation, ...]

    def for_root(self, root: str) -> tuple[Citation, ...]:
        return tuple(c for c in self.entries if c.root == root)


@lru_cache(maxsize=1)
def citations() -> Citations:
    lock = loaders.islambouli_citations_lock()
    digest = hashlib.sha256(ISLAMBOULI_CITATIONS_JSON.read_bytes()).hexdigest()
    if digest != str(lock.get("sha256") or ""):
        raise CitationsNotFrozen(
            f"islambouli_citations.json hashes to {digest[:12]}…, the lock froze "
            f"{str(lock.get('sha256'))[:12]}…."
        )
    data = loaders.islambouli_citations()
    entries = []
    for c in data.get("citations") or ():
        if c.get("stage") not in STAGES:
            raise CitationsNotFrozen(f"{c.get('id')}: unknown stage {c.get('stage')!r}.")
        src = c.get("source") or {}
        witness = ROOT / str(src.get("witness") or "")
        if not witness.is_file() or hashlib.sha256(witness.read_bytes()).hexdigest() != src.get("witness_sha256"):
            raise CitationsNotFrozen(f"{c.get('id')}: witness {src.get('witness')} is missing or changed.")
        entries.append(Citation(
            id=c["id"], root=c["root"], stage=c["stage"], label=c["label"],
            label_as_printed=c["label_as_printed"], text=c["text"],
            reading_note=c.get("reading_note") or "", source=src,
        ))
    return Citations(version=str(lock.get("version") or ""),
                     development_cases=frozenset(data.get("development_cases") or ()),
                     entries=tuple(entries))


def _words(text: str) -> list[str]:
    words = (w.strip(_EDGE_MARKS) for w in text.split())
    return [w for w in words if w]


def word_gap(ours: str, theirs: str) -> dict[str, list[str]]:
    """Words only in one sentence, counted with multiplicity, in order of appearance."""
    a, b = _words(ours), _words(theirs)

    def only(xs: list[str], other: list[str]) -> list[str]:
        left = Counter(xs) - Counter(other)
        out = []
        for w in xs:
            if left[w] > 0:
                out.append(w)
                left[w] -= 1
        return out

    return {"only_assembly": only(a, b), "only_cited": only(b, a)}
