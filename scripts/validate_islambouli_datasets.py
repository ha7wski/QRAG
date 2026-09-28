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
  B. the transcription — the witness image is the original, by digest; the table
     has the poster's 29 rows; every row's `text` equals its `text_as_printed` up
     to whitespace; no row claims more than `transcribed_from_poster`.

The one risk a transcribed table carries is a wrong copy. Section B makes the
copy's only permitted liberty — whitespace — mechanically checkable, and the
image it was copied from identifiable by digest.

Usage:
    python scripts/validate_islambouli_datasets.py     # 0 = clean, 1 = findings
"""
from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from quran_data.paths import ISLAMBOULI_POSTER_PNG  # noqa: E402
from linguistics.lisan.harness import draw  # noqa: E402

LABEL_WITNESS = "islambouli_witness_set.json"
LABEL_TABLE = "islambouli_letters.csv"

# The original poster. The truncated first deposit had another digest; it is the
# original the table was transcribed from, and nothing else may stand in for it.
POSTER_SHA256 = "e64906b3b351539cc600f1bff88c9156b703142f740df5a691fac56feabcac0c"

# The poster's letter column, rows 0–28, as printed. Structure of the witness,
# not content of the table: a missing, duplicated or reordered row is a copy error.
POSTER_LABELS = (
    "ء", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر", "ز", "س", "ش", "ص", "ض",
    "ط", "ظ", "ع", "غ", "ف", "ق", "ك", "ل", "م", "ن", "هـ", "آ - ى", "و", "ي",
)
TABLE_COLUMNS = ("row", "label_as_printed", "text_as_printed", "text", "status",
                 "reading_note")
# The only status this version admits. `attested` needs a page of the book, and
# none has been read.
STATUS = "transcribed_from_poster"
_WHITESPACE = re.compile(r"\s+")
SEED = 20260928                          # fixed in design.md §D2, before any draw


def _text(value) -> str:
    return (value or "").strip() if isinstance(value, (str, type(None))) else str(value)


# ── inputs ───────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Datasets:
    """The inputs every rule reads, as plain data — swapped whole by the tests."""

    witness: dict                        # islambouli_witness_set.json
    table: list[dict]                    # islambouli_letters.csv rows
    poster_sha256: str                   # digest of the witness image on disk
    first_witness: dict                  # concept_witness_set.json
    morphology: dict[str, dict]
    maqayis_has_asl: frozenset[str]

    @classmethod
    def load(cls) -> "Datasets":
        return cls(
            witness=loaders.islambouli_witness_set(),
            table=loaders.islambouli_letters(),
            poster_sha256=hashlib.sha256(ISLAMBOULI_POSTER_PNG.read_bytes()).hexdigest(),
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


# ── B. the transcription ─────────────────────────────────────────────────────
def _strip_ws(text: str) -> str:
    return _WHITESPACE.sub("", text)


def check_table(data: Datasets) -> list[str]:
    """The copy is the poster's, row for row, and claims nothing it has not read."""
    findings: list[str] = []
    if data.poster_sha256 != POSTER_SHA256:
        findings.append(
            f"{ISLAMBOULI_POSTER_PNG.name}: sha256 {data.poster_sha256[:12]}…, "
            f"expected {POSTER_SHA256[:12]}… — the witness on disk is not the "
            "original the table was transcribed from"
        )

    rows = data.table
    if rows and tuple(rows[0].keys()) != TABLE_COLUMNS:
        findings.append(
            f"{LABEL_TABLE}: columns are {tuple(rows[0].keys())}, expected "
            f"{TABLE_COLUMNS}. A further column would be a place to put an "
            "interpretation of a row; the text is the row."
        )
    if len(rows) != len(POSTER_LABELS):
        findings.append(
            f"{LABEL_TABLE}: {len(rows)} rows, the poster prints {len(POSTER_LABELS)}"
        )
    for i, row in enumerate(rows):
        where = f"{LABEL_TABLE}: row {_text(row.get('row')) or '?'}"
        if _text(row.get("row")) != str(i):
            findings.append(f"{where} sits at position {i} — out of the poster's order")
        if i < len(POSTER_LABELS) and _text(row.get("label_as_printed")) != POSTER_LABELS[i]:
            findings.append(
                f"{where}: label «{_text(row.get('label_as_printed'))}», the poster "
                f"prints «{POSTER_LABELS[i]}»"
            )
        printed = row.get("text_as_printed") or ""
        spaced = row.get("text") or ""
        if not _strip_ws(printed):
            findings.append(f"{where}: `text_as_printed` is empty")
        if _strip_ws(printed) != _strip_ws(spaced):
            findings.append(
                f"{where}: `text` differs from `text_as_printed` by more than "
                "whitespace. Restoring a space is the one liberty a transcription "
                "takes; changing a letter or a mark is no longer a copy."
            )
        if _text(row.get("status")) != STATUS:
            findings.append(
                f"{where}: status «{_text(row.get('status'))}», the only admissible "
                f"one is «{STATUS}» — no page of the book has been read"
            )
    return findings


# ── entry points ─────────────────────────────────────────────────────────────
def validate(data: Datasets | None = None) -> list[str]:
    """Every finding, in section order. Empty == clean."""
    data = data or Datasets.load()
    _replay, witness_findings = check_witness_set(data)
    return [*witness_findings, *check_table(data)]


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
    rows = data.table
    noted = [r for r in rows if _text(r.get("reading_note"))]
    print()
    print(f"  letter table         : {len(rows)} rows, all «{STATUS}»; "
          f"{len(noted)} with a reading note")
    print(f"    witness            : {ISLAMBOULI_POSTER_PNG.name}, sha256 "
          f"{data.poster_sha256[:12]}… "
          + ("(the original)" if data.poster_sha256 == POSTER_SHA256 else "(NOT the original)"))
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
