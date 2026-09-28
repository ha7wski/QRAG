#!/usr/bin/env python3
"""
validate_islambouli_datasets.py — OFFLINE gate on the Islambouli measurement.

The Islambouli letter table is measured under the harness that measured the
closed physics-first engine, on its own holdout. This script checks the datasets
that measurement rests on, and prints the report. Exit code 0 when clean, 1 with
every finding listed otherwise. No network, no model, no LLM.

It grows with the change, one section per step, and each section exists before
the data it checks:

  A. the second holdout — replayed from its own seed, through the code that also
     replays the first draw, with the first draw's preconditions asserted
     (`linguistics/lisan/harness/draw.py`).

Usage:
    python scripts/validate_islambouli_datasets.py     # 0 = clean, 1 = findings
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from linguistics.lisan.harness import draw  # noqa: E402

LABEL_WITNESS = "islambouli_witness_set.json"
SEED = 20260928                          # fixed in design.md §D2, before any draw


def _text(value) -> str:
    return (value or "").strip() if isinstance(value, (str, type(None))) else str(value)


# ── inputs ───────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Datasets:
    """The inputs every rule reads, as plain data — swapped whole by the tests."""

    witness: dict                        # islambouli_witness_set.json
    first_witness: dict                  # concept_witness_set.json
    morphology: dict[str, dict]
    maqayis_has_asl: frozenset[str]

    @classmethod
    def load(cls) -> "Datasets":
        return cls(
            witness=loaders.islambouli_witness_set(),
            first_witness=loaders.concept_witness_set(),
            morphology=loaders.morphology(),
            maqayis_has_asl=frozenset(
                r["root_normalized"] for r in loaders.maqayis_asl()
                if _text(r.get("asl_status")) == "has_asl"
            ),
        )

    def with_(self, **changes) -> "Datasets":
        return replace(self, **changes)


# ── A. the second holdout ────────────────────────────────────────────────────
@dataclass(frozen=True)
class Replay:
    drawn: tuple[str, ...]
    lower: int
    upper: int
    ran: bool


def check_witness_set(data: Datasets) -> tuple[Replay, list[str]]:
    """The 40 are the drawn ones, drawn from the right frame, and none is burned."""
    findings: list[str] = []
    w = data.witness
    first = tuple(_text(e.get("root")) for e in data.first_witness.get("roots") or []
                  if isinstance(e, dict))

    if w.get("seed") != SEED:
        findings.append(
            f"{LABEL_WITNESS}: `seed` is {w.get('seed')!r}; the design fixed "
            f"{SEED} before any draw. A seed changed after the fact is a re-draw."
        )
    strata = w.get("strata")
    counts = ((strata[0].get("drawn"), strata[1].get("drawn"))
              if isinstance(strata, list) and len(strata) == 2
              and all(isinstance(s, dict) for s in strata) else None)
    if counts != draw.FIRST_DRAWN:
        findings.append(
            f"{LABEL_WITNESS}: `strata[].drawn` is {counts!r}; the allocation is "
            f"the first draw's, {draw.FIRST_DRAWN[0]} + {draw.FIRST_DRAWN[1]}"
        )

    try:
        lower, upper, drawn = draw.draw_after(
            data.morphology, data.maqayis_has_asl, first, SEED, *draw.FIRST_DRAWN
        )
    except draw.FrameMoved as exc:
        return Replay((), 0, 0, ran=False), findings + [
            f"{LABEL_WITNESS}: cannot be replayed — {exc}. The second holdout "
            "claims the first one's frame; if that frame has moved, the claim no "
            "longer holds."
        ]
    replay_ = Replay(drawn, len(lower), len(upper), ran=True)

    if isinstance(strata, list) and len(strata) == 2:
        for stratum, computed, label in ((strata[0], lower, "lower"),
                                         (strata[1], upper, "upper")):
            if isinstance(stratum, dict) and stratum.get("frame") != len(computed):
                findings.append(
                    f"{LABEL_WITNESS}: the {label} stratum records a frame of "
                    f"{stratum.get('frame')}, the replay gives {len(computed)}"
                )
    if (w.get("frame") or {}).get("size") != len(lower) + len(upper):
        findings.append(
            f"{LABEL_WITNESS}: `frame.size` is {(w.get('frame') or {}).get('size')}, "
            f"the replay gives {len(lower) + len(upper)}"
        )

    entries = w.get("roots")
    if not isinstance(entries, list) or not entries:
        return replay_, findings + [f"{LABEL_WITNESS}: `roots` is missing or empty"]
    on_file = tuple(_text(e.get("root")) for e in entries if isinstance(e, dict))

    if on_file != drawn:
        added = sorted(set(on_file) - set(drawn))
        dropped = sorted(set(drawn) - set(on_file))
        findings.append(
            f"{LABEL_WITNESS}: the recorded draw does not reproduce the roots on "
            "file (or not in draw order) — a holdout re-rolled after the fact is "
            f"not a holdout.\n      on file, not drawn : {'، '.join(added) or '—'}"
            f"\n      drawn, not on file : {'، '.join(dropped) or '—'}"
        )

    burned = set(first) | {draw.DEVELOPMENT_CASE} | set(draw.CURATED_AT_FIRST_DRAW)
    for root in sorted(set(on_file) & burned):
        findings.append(
            f"{LABEL_WITNESS}: «{root}» is in the second holdout and must not be — "
            "burned by the first measurement, or excluded from its frame"
        )

    seen: set[str] = set()
    for i, entry in enumerate(entries):
        where = f"{LABEL_WITNESS}: roots[{i}]"
        if not isinstance(entry, dict):
            findings.append(f"{where} is not an object")
            continue
        root = _text(entry.get("root"))
        if root in seen:
            findings.append(f"{where}: «{root}» appears twice")
        seen.add(root)
        record = data.morphology.get(root)
        if record is None:
            findings.append(f"{where}: «{root}» is not a canonical QAC root key")
            continue
        if entry.get("occurrences") != record.get("count"):
            findings.append(
                f"{where}: «{root}» records {entry.get('occurrences')} occurrences, "
                f"morphology.json holds {record.get('count')}"
            )
    return replay_, findings


# ── entry points ─────────────────────────────────────────────────────────────
def validate(data: Datasets | None = None) -> list[str]:
    """Every finding, in section order. Empty == clean."""
    data = data or Datasets.load()
    _replay, witness_findings = check_witness_set(data)
    return [*witness_findings]


def report(findings: list[str], data: Datasets, replay_: Replay) -> None:
    w = data.witness
    print("=" * 64)
    print("ISLAMBOULI DATASETS — validation report")
    print("=" * 64)
    print(f"  second holdout       : {len(w.get('roots') or [])} roots, seed "
          f"{w.get('seed', '?')}, drawn {_text(w.get('drawn_on')) or '?'}")
    if replay_.ran:
        on_file = tuple(_text(e.get("root")) for e in w.get("roots") or []
                        if isinstance(e, dict))
        verdict = ("reproduces the file exactly" if replay_.drawn == on_file
                   else "DOES NOT reproduce the file")
        print(f"    draw replay        : first frame 205 + 75 and first draw "
              f"asserted; rest {replay_.lower} + {replay_.upper} → {verdict}")
    else:
        print("    draw replay        : could not be replayed — see the findings")
    if not findings:
        print("\n  findings: none — the Islambouli datasets are consistent.")
    else:
        print(f"\n  findings: {len(findings)}")
        for f in findings:
            print(f"    - {f}")
    print("=" * 64)


def main() -> int:
    data = Datasets.load()
    replay_, _ = check_witness_set(data)
    findings = validate(data)
    report(findings, data, replay_)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
