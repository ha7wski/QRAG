"""
confront.py — the ONE module of this package allowed to read the uses, and it
only ever REPORTS.

It composes a root's reading ONCE, carries it through untouched, and sets it
beside the uses frozen for that root. There is no path here that re-selects,
re-orders or re-words a reading, and there is no flag that adds one. A
disagreement is a RESULT — recorded, published, and never a reason to change a
row of the table, which is transcribed and would stop citing Islambouli.

The use record, the per-use and per-root verdicts and `counts_toward_k` come from
`linguistics/lisan/harness/verdicts.py`, the code that judged the closed engine,
so both measurements are read by one piece of code.

Nothing else in the package imports this module (`tests/test_import_direction.py`).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from linguistics.lisan.harness.verdicts import (  # noqa: E402
    DEVELOPMENT_CASE,
    AttestedUse,
    counts_toward_k,
    read_uses,
    records,
    verdict_for,
    witness_roots,
)
from linguistics.lisan.islambouli.compose import Reading, compose  # noqa: E402


@dataclass(frozen=True)
class Confrontation:
    root: str
    reading: Reading
    uses: tuple[AttestedUse, ...]
    uses_blind: tuple[AttestedUse, ...]     # ضرب's calibration copy; empty elsewhere
    verdict: str                            # covers_all | partial | not_recorded
    uses_frozen_at: str
    reading_recorded_at: str
    in_witness_set: bool
    counts_toward_k: bool


def confront(root: str, attestation: dict | None = None,
             witness: dict | None = None) -> Confrontation:
    root = (root or "").strip()
    reading = compose(root)
    record = records(attestation if attestation is not None
                     else loaders.islambouli_attestation()).get(root) or {}
    holdout = witness_roots(witness if witness is not None
                            else loaders.islambouli_witness_set())
    uses = read_uses(record)
    in_witness = root in holdout
    return Confrontation(
        root=root,
        reading=reading,
        uses=uses,
        uses_blind=read_uses(record, "uses_blind"),
        verdict=verdict_for(uses),
        uses_frozen_at=str(record.get("uses_frozen_at") or "").strip(),
        reading_recorded_at=str(record.get("reading_recorded_at") or "").strip(),
        in_witness_set=in_witness,
        counts_toward_k=counts_toward_k(root, in_witness, DEVELOPMENT_CASE),
    )
