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

  C. the system check — the grid's decomposition uses only the poster's words,
     and its criteria (C1–C4), hypotheses (H1–H4) and verdict are RECOMPUTED here
     from the decomposition and compared with what the file records. The rules
     are design.md §D11's, fixed before the grid existed.

  D. the freeze — the lock's digest is the CSV's bytes; its source cites no page,
     names the witness by the original's digest, carries the poster's imprint
     under the same whitespace-only rule as the rows, and rests the attribution
     on that imprint; no history entry justifies itself by a root or a result.

  E. the uses and the metric — every use is evidenced by one of its root's own
     verses; `ضرب` carries the closed run's uses unchanged plus the blind
     calibration copy, whose concordance verdict is recomputed from its matches;
     then the harness's own ordering gate and strict metric
     (`linguistics/lisan/harness/verdicts.py`), unchanged, under this record's
     names.

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
from quran_data.paths import (  # noqa: E402
    ISLAMBOULI_LETTERS_CSV,
    ISLAMBOULI_POSTER_PNG,
)
from linguistics.lisan.harness import draw  # noqa: E402
from linguistics.lisan.harness.verdicts import (  # noqa: E402
    RecordSpec,
    check_attestation,
    records as _records,
)

LABEL_WITNESS = "islambouli_witness_set.json"
LABEL_TABLE = "islambouli_letters.csv"
LABEL_GRID = "islambouli_letters_grid.json"

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


def _wrap(line: str, width: int = 96) -> list[str]:
    import textwrap
    indent = " " * (len(line) - len(line.lstrip()) + 2)
    return textwrap.wrap(line, width=width, subsequent_indent=indent) or [line]


def _text(value) -> str:
    return (value or "").strip() if isinstance(value, (str, type(None))) else str(value)


# ── inputs ───────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Datasets:
    """The inputs every rule reads, as plain data — swapped whole by the tests."""

    witness: dict                        # islambouli_witness_set.json
    grid: dict | None                    # islambouli_letters_grid.json, once written
    lock: dict | None                    # islambouli_letters.lock.json, once written
    attestation: dict | None             # islambouli_attestation.json, once written
    closed_attestation: dict             # concept_attestation.json — ضرب's reference uses
    table_bytes: bytes                   # the raw CSV bytes the lock's digest is over
    table: list[dict]                    # islambouli_letters.csv rows
    poster_sha256: str                   # digest of the witness image on disk
    first_witness: dict                  # concept_witness_set.json
    morphology: dict[str, dict]
    maqayis_has_asl: frozenset[str]

    @classmethod
    def load(cls) -> "Datasets":
        return cls(
            witness=loaders.islambouli_witness_set(),
            grid=_read_grid(),
            lock=_read_lock(),
            attestation=_read_attestation(),
            closed_attestation=loaders.concept_attestation(),
            table_bytes=ISLAMBOULI_LETTERS_CSV.read_bytes(),
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


# ── C. the system check (§D11) ───────────────────────────────────────────────
INTENSITY_SCALE = ("خفيف", "وسط", "شديد", "شديد جداً")
FORMULAS = ("صوت خفيف يدل على ", "صوت يدل على ")
FUNCTION_WORDS = frozenset({"و", "أو", "في"})
SLOTS = ("action", "intensity", "ending")
PUSH = "دفع"
# design.md §D11: fewer than this many rows decomposing into two or more slots
# makes the table a `list`, whatever else holds.
LIST_THRESHOLD = 15


def _read_grid() -> dict | None:
    from quran_data.paths import ISLAMBOULI_LETTERS_GRID_JSON
    if not ISLAMBOULI_LETTERS_GRID_JSON.exists():
        return None
    return loaders.islambouli_letters_grid()


def _slot_values(alternative: dict) -> dict[str, list[str]]:
    intensity = alternative.get("intensity")
    return {
        "action": list(alternative.get("action") or []),
        "intensity": [intensity] if intensity else [],
        "ending": list(alternative.get("ending") or []),
    }


def _content_tokens(text: str) -> list[str]:
    for formula in FORMULAS:
        if text.startswith(formula):
            text = text[len(formula):]
            break
    out = []
    for token in text.split():
        token = token.strip(".،()")
        if token and token not in FUNCTION_WORDS:
            out.append(token)
    return out


def _covered(token: str, pieces: list[str]) -> bool:
    candidates = {token, token[1:] if token.startswith("و") and len(token) > 2 else token}
    return any(c in piece for c in candidates for piece in pieces)


def _signature(alternatives: list[dict]) -> tuple:
    return tuple(
        tuple((slot, tuple(values)) for slot, values in _slot_values(a).items())
        for a in alternatives
    )


def _alternatives(row: dict, reading: str, ambiguity: dict) -> list[dict]:
    if reading == "alternative" and row.get("row") == ambiguity.get("row"):
        return (ambiguity.get("alternative_reading") or {}).get("alternatives") or []
    return row.get("alternatives") or []


def evaluate_grid(grid: dict, texts: dict[int, str], reading: str = "primary") -> dict:
    """C1–C4, H1–H4 and the verdict, computed from the decomposition alone."""
    ambiguity = grid.get("rule_ambiguity") or {}
    rows = {r.get("row"): r for r in grid.get("rows") or [] if isinstance(r, dict)}
    alts = {n: _alternatives(r, reading, ambiguity) for n, r in rows.items()}
    labels = {n: r.get("label") for n, r in rows.items()}
    by_label = {labels[n]: alts[n] for n in rows}

    c1 = []
    for n, row in rows.items():
        text = texts.get(n, "")
        for a in alts[n]:
            for slot, values in _slot_values(a).items():
                c1 += [f"row {n} {slot} «{v}»" for v in values if v not in text]
        c1 += [f"row {n} residue «{v}»" for v in row.get("residue") or [] if v not in text]

    residue_rows = sorted(n for n, r in rows.items() if r.get("residue"))
    uncovered = []
    for n, row in rows.items():
        pieces = [v for a in alts[n] for vs in _slot_values(a).values() for v in vs]
        pieces += list(row.get("residue") or [])
        uncovered += [f"row {n} «{t}»" for t in _content_tokens(texts.get(n, ""))
                      if not _covered(t, pieces)]

    slots_of: dict[str, set[str]] = {}
    for n in rows:
        for a in alts[n]:
            for slot, values in _slot_values(a).items():
                for v in values:
                    slots_of.setdefault(v, set()).add(slot)
    c3 = sorted(f"«{v}» in {sorted(ss)}" for v, ss in slots_of.items() if len(ss) > 1)

    seen: dict[tuple, str] = {}
    c4 = []
    for n in sorted(rows):
        sig = _signature(alts[n])
        if sig in seen:
            c4.append(f"{seen[sig]} = {labels[n]}")
        seen.setdefault(sig, labels[n])

    multi = sorted(n for n in rows
                   if any(sum(1 for vs in _slot_values(a).values() if vs) >= 2
                          for a in alts[n]))

    def push(label: str) -> dict | None:
        for a in by_label.get(label) or []:
            if PUSH in (a.get("action") or []):
                return a
        return None

    def step(label: str) -> int | None:
        a = push(label)
        value = a.get("intensity") if a else None
        return INTENSITY_SCALE.index(value) if value in INTENSITY_SCALE else None

    def endings(label: str) -> list[str]:
        return list((push(label) or {}).get("ending") or [])

    h1_pairs = (("ت", "ث"), ("ط", "ذ"), ("د", "ظ"))
    h1_fail = []
    for stop, stick in h1_pairs:
        if step(stop) is None or step(stop) != step(stick):
            h1_fail.append(f"{stop}/{stick}: intensity {step(stop)} vs {step(stick)}")
        if endings(stop) != ["متوقف"] or endings(stick) != ["ملتصق"]:
            h1_fail.append(f"{stop}/{stick}: endings {endings(stop)} / {endings(stick)}")
    others = [lab for lab in ("ت", "ث", "ط", "ذ", "د", "ظ") if step(lab) == 3]
    if step("ض") != 3 or others:
        h1_fail.append(f"ض at step {step('ض')}; others at شديد جداً: {others}")

    h2_fail = [f"{plain}→{emph}: {step(plain)} → {step(emph)}"
               for plain, emph in (("ت", "ط"), ("ذ", "ظ"), ("د", "ض"))
               if step(plain) is None or step(emph) != step(plain) + 1]

    def differs_only(a_label: str, b_label: str, slot: str) -> list[str]:
        a_alts, b_alts = by_label.get(a_label) or [], by_label.get(b_label) or []
        if len(a_alts) != len(b_alts):
            return [f"{a_label} has {len(a_alts)} alternative(s), {b_label} {len(b_alts)}"]
        out = []
        for x, y in zip(a_alts, b_alts):
            sx, sy = _slot_values(x), _slot_values(y)
            out += [f"{k}: {sx[k]} vs {sy[k]}" for k in SLOTS if k != slot and sx[k] != sy[k]]
            if sx[slot] == sy[slot]:
                out.append(f"{slot} identical")
        return out

    h3_fail = differs_only("س", "ص", "ending")
    h4_fail = differs_only("ح", "هـ", "intensity")

    c1_ok, c2_ok = not c1, not residue_rows and not uncovered
    c3_ok, c4_ok = not c3, not c4
    h1_ok, h2_ok = not h1_fail, not h2_fail
    if not c3_ok or not c4_ok or len(multi) < LIST_THRESHOLD:
        verdict = "list"
    elif c1_ok and c2_ok and (h1_ok or h2_ok):
        verdict = "system"
    elif c1_ok:
        verdict = "partial system"
    else:
        verdict = "list"

    return {
        "C1_literal": {"holds": c1_ok, "violations": c1},
        "C2_exhaustive": {"holds": c2_ok, "rows_with_residue": residue_rows,
                          "uncovered_words": uncovered},
        "C3_no_same_form_in_two_slots": {"holds": c3_ok, "contradictions": c3},
        "C4_discrimination": {"holds": c4_ok, "identical": c4},
        "rows_with_two_or_more_slots": len(multi),
        "H1": {"holds": h1_ok, "failing": h1_fail},
        "H2": {"holds": h2_ok, "failing": h2_fail},
        "H3": {"holds": not h3_fail, "failing": h3_fail},
        "H4": {"holds": not h4_fail, "failing": h4_fail},
        "verdict": verdict,
    }


def check_grid(data: Datasets) -> list[str]:
    """The recorded result is what the decomposition produces, under both readings."""
    grid = data.grid
    if grid is None:
        return []
    texts = {int(r["row"]): r.get("text") or "" for r in data.table}
    findings = []
    rows = grid.get("rows") or []
    if [r.get("row") for r in rows] != list(range(len(POSTER_LABELS))):
        findings.append(f"{LABEL_GRID}: rows are not the poster's 0–28 in order")
    for reading in ("primary", "alternative"):
        computed = evaluate_grid(grid, texts, reading)
        recorded = (grid.get("result") or {}).get(reading)
        if recorded != computed:
            findings.append(
                f"{LABEL_GRID}: the recorded `result.{reading}` is not what the "
                "decomposition produces — the verdict is computed, never chosen"
            )
    return findings


# ── D. the freeze ────────────────────────────────────────────────────────────
LABEL_LOCK = "islambouli_letters.lock.json"
IMPRINT_POSITIONS = ("title band", "banner", "footer", "top edge")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
# A reason that cites a measurement is a rescue edit, whatever else it says.
RESULT_WORDS = re.compile(r"k\s*/\s*40|covered|not_covered|miss\b|coverage", re.I)


def _read_lock() -> dict | None:
    from quran_data.paths import ISLAMBOULI_LETTERS_LOCK_JSON
    if not ISLAMBOULI_LETTERS_LOCK_JSON.exists():
        return None
    return loaders.islambouli_letters_lock()


def check_lock(data: Datasets) -> list[str]:
    lock = data.lock
    if lock is None:
        return []
    findings: list[str] = []
    digest = hashlib.sha256(data.table_bytes).hexdigest()
    if _text(lock.get("sha256")) != digest:
        findings.append(
            f"{LABEL_LOCK}: sha256 {_text(lock.get('sha256'))[:12]}… does not match "
            f"the CSV bytes ({digest[:12]}…) — the table moved under its freeze"
        )
    if not SEMVER.match(_text(lock.get("version"))):
        findings.append(f"{LABEL_LOCK}: `version` is not x.y.z")
    history = lock.get("history")
    if not isinstance(history, list) or not history:
        return findings + [f"{LABEL_LOCK}: `history` is missing or empty"]
    if _text(history[-1].get("sha256")) != _text(lock.get("sha256")) or \
            _text(history[-1].get("version")) != _text(lock.get("version")):
        findings.append(f"{LABEL_LOCK}: the last history entry is not the current version")

    witness_roots = {_text(e.get("root")) for doc in (data.witness, data.first_witness)
                     for e in doc.get("roots") or [] if isinstance(e, dict)}
    for i, entry in enumerate(history):
        where = f"{LABEL_LOCK}: history[{i}]"
        reason = _text(entry.get("reason"))
        if not reason:
            findings.append(f"{where} has no `reason`")
        if RESULT_WORDS.search(reason) or any(r and r in reason for r in witness_roots):
            findings.append(
                f"{where}: the reason cites a root or a result. A row changes only "
                "against the image; changing it for a root is ceasing to cite "
                "Islambouli."
            )
        source = entry.get("source")
        if not isinstance(source, dict):
            findings.append(f"{where}: `source` must be an object")
            continue
        if source.get("pages") != []:
            findings.append(
                f"{where}: `pages` is {source.get('pages')!r}. No page of the book "
                "has been read; a page recorded anyway is a page invented."
            )
        if _text(source.get("witness_sha256")) != POSTER_SHA256:
            findings.append(f"{where}: `witness_sha256` is not the original poster's")
        if not _text(source.get("authority")):
            findings.append(f"{where}: no `authority`")
        if not _text(source.get("witness_origin")):
            findings.append(f"{where}: no `witness_origin`")
        imprint = source.get("witness_imprint")
        positions = tuple(_text(x.get("position")) for x in imprint or []
                          if isinstance(x, dict))
        if positions != IMPRINT_POSITIONS:
            findings.append(f"{where}: `witness_imprint` positions are {positions}, "
                            f"expected {IMPRINT_POSITIONS}")
        for item in imprint or []:
            if not isinstance(item, dict):
                continue
            printed, spaced = item.get("text_as_printed") or "", item.get("text") or ""
            label = f"{where} imprint «{_text(item.get('position'))}»"
            if _strip_ws(printed) != _strip_ws(spaced):
                findings.append(f"{label}: `text` differs from what is printed by "
                                "more than whitespace")
            if not _strip_ws(printed) and not _text(item.get("reading_note")):
                findings.append(f"{label}: empty with no `reading_note` saying why")
            if _text(item.get("position")) == "banner" and not _strip_ws(printed):
                findings.append(f"{label}: the banner is what names the book; it "
                                "cannot be empty")
        if "witness_imprint" not in _text(source.get("attribution_basis")):
            findings.append(f"{where}: `attribution_basis` does not rest on "
                            "`witness_imprint`")
    return findings


# ── E. the uses, the calibration and the metric ──────────────────────────────
LABEL_ATTESTATION = "islambouli_attestation.json"
ISLAMBOULI_RECORD = RecordSpec(
    label=LABEL_ATTESTATION,
    path_label="data/references/islambouli_attestation.json",
    recorded_field="reading_recorded_at",
    noun="reading",
    off_set_reason=("it is the closed run's development case, carried over with "
                    "its uses unchanged; it is the one root judged against "
                    "identical uses under both tables, and tests neither."),
)
# design.md §D13, fixed before the blind uses existed.
CONCORDANT_MIN_MATCHED = 4
CONCORDANT_MAX_BLIND_UNMATCHED = 2
STRONG_DIVERGENCE_BELOW = 3


def _read_attestation() -> dict | None:
    from quran_data.paths import ISLAMBOULI_ATTESTATION_JSON
    if not ISLAMBOULI_ATTESTATION_JSON.exists():
        return None
    return loaders.islambouli_attestation()


def concordance(reference: int, blind: int, matched: int) -> str:
    if matched >= CONCORDANT_MIN_MATCHED and blind - matched <= CONCORDANT_MAX_BLIND_UNMATCHED:
        return "concordant"
    if matched < STRONG_DIVERGENCE_BELOW:
        return "strong divergence"
    return "partial"


def _use_pairs(uses) -> list[tuple[str, str]]:
    return [(_text(u.get("gloss")), _text(u.get("verse")))
            for u in uses or [] if isinstance(u, dict)]


def check_uses(data: Datasets) -> list[str]:
    att = data.attestation
    if att is None:
        return []
    findings: list[str] = []
    records = _records(att)
    holdout = [_text(e.get("root")) for e in data.witness.get("roots") or []]
    for root in holdout + [draw.DEVELOPMENT_CASE]:
        record = records.get(root)
        if record is None:
            findings.append(f"{LABEL_ATTESTATION}: «{root}» has no record")
            continue
        own = set((data.morphology.get(root) or {}).get("verses") or [])
        for field in ("uses", "uses_blind"):
            for j, (gloss, verse) in enumerate(_use_pairs(record.get(field))):
                if verse and verse not in own:
                    findings.append(
                        f"{LABEL_ATTESTATION}: «{root}» {field}[{j}] cites {verse}, "
                        "where the root does not occur — not an attested use of it"
                    )

    dev = records.get(draw.DEVELOPMENT_CASE) or {}
    reference = _use_pairs((_records(data.closed_attestation).get(draw.DEVELOPMENT_CASE)
                            or {}).get("uses"))
    if _use_pairs(dev.get("uses")) != reference:
        findings.append(
            f"{LABEL_ATTESTATION}: «{draw.DEVELOPMENT_CASE}»'s uses are not the closed "
            "run's, unchanged — it is the one root judged against identical uses "
            "under both tables"
        )
    calibration = dev.get("calibration")
    if dev and not dev.get("uses_blind"):
        findings.append(f"{LABEL_ATTESTATION}: «{draw.DEVELOPMENT_CASE}» has no `uses_blind`")
    if isinstance(calibration, dict):
        blind = _use_pairs(dev.get("uses_blind"))
        matches = calibration.get("matches") or []
        ref_idx = [m.get("reference") for m in matches if isinstance(m, dict)]
        blind_idx = [m.get("blind") for m in matches if isinstance(m, dict)]
        if len(set(ref_idx)) != len(ref_idx) or len(set(blind_idx)) != len(blind_idx):
            findings.append(f"{LABEL_ATTESTATION}: a calibration use is matched twice")
        if any(not isinstance(i, int) or not 0 <= i < len(reference) for i in ref_idx) or \
                any(not isinstance(i, int) or not 0 <= i < len(blind) for i in blind_idx):
            findings.append(f"{LABEL_ATTESTATION}: a calibration match points nowhere")
        if any(not _text(m.get("reason")) for m in matches if isinstance(m, dict)):
            findings.append(f"{LABEL_ATTESTATION}: a calibration match has no reason")
        computed = concordance(len(reference), len(blind), len(matches))
        if _text(calibration.get("verdict")) != computed:
            findings.append(
                f"{LABEL_ATTESTATION}: calibration verdict «{calibration.get('verdict')}», "
                f"the fixed rule gives «{computed}» — computed, never chosen"
            )
    elif dev.get("uses_blind"):
        findings.append(f"{LABEL_ATTESTATION}: «{draw.DEVELOPMENT_CASE}» has blind uses "
                        "and no `calibration`")
    return findings


def metric(data: Datasets):
    holdout = tuple(_text(e.get("root")) for e in data.witness.get("roots") or [])
    return check_attestation(data.attestation, holdout, ISLAMBOULI_RECORD)


# ── the publication block ────────────────────────────────────────────────────
# Written ONCE and printed with the number, wherever the number is printed.
RESERVATIONS = (
    ("R1 (inherited)",
     "The harness's composition window was set after a measurement on the closed "
     "run's development case. Under this table it is non-binding — one gloss per "
     "position — and it is stated here rather than dropped."),
    ("R2 (source)",
     "Transcribed from a poster, not from the book. Title and author are printed "
     "on the poster and transcribed. No page of the book has been read. The "
     "poster's origin is unrecorded. Row 12 carries a mark that could not be read."),
    ("R3 (method)",
     "The positional rule is the harness's, not Islambouli's. A miss refutes this "
     "table under this rule, not his reading method, which the book may state "
     "differently and which was not read."),
    ("R4 (judge)",
     "One judge. The committed records make the judgement redoable by anyone who "
     "clones the repository; no independent review took place."),
    ("R5 (uses writer)",
     "These uses were written by agents blind to the table; the closed run's by a "
     "curator who knew that run's table. Blind writing may differ in nature, not only "
     "in severity, so «it can only lower k» is plausible, not demonstrated. Measured: "
     "{blind} blind uses against {closed} for the closed 40; on ضرب, {matched} of "
     "{reference} reference uses have a blind match and the blind writer lists "
     "{blind_dev}."),
    ("R6 (samples)",
     "The two numbers share a frame and a method, not a sample: two independent "
     "draws of 40. ضرب is the only root judged against identical uses under both."),
)


def _closed_figures(closed: dict) -> dict:
    from linguistics.lisan.harness.verdicts import CLOSED_ENGINE
    roots = tuple(_text(e.get("root")) for e in loaders.concept_witness_set()["roots"])
    m, _ = check_attestation(closed, roots, CLOSED_ENGINE)
    return {"metric": m, **_use_figures(closed, roots)}


def _use_figures(att: dict, roots: tuple[str, ...]) -> dict:
    recs = _records(att)
    uses = [u for r in roots for u in (recs.get(r) or {}).get("uses") or []]
    classes: dict[str, int] = {}
    for u in uses:
        if _text(u.get("verdict")) == "not_covered":
            head = _text(u.get("reason")).split(":", 1)[0].split()[0]
            classes[head] = classes.get(head, 0) + 1
    return {"uses": len(uses),
            "covered": sum(1 for u in uses if _text(u.get("verdict")) == "covered"),
            "classes": classes}


def publication(data: Datasets) -> list[str]:
    """The result block: this table's k beside the closed engine's, never alone."""
    holdout = tuple(_text(e.get("root")) for e in data.witness.get("roots") or [])
    mine, _ = metric(data)
    if not mine.printable:
        return []
    ours = _use_figures(data.attestation, holdout)
    closed = _closed_figures(data.closed_attestation)
    cm = closed["metric"]
    texts = {int(r["row"]): r.get("text") or "" for r in data.table}
    verdict = evaluate_grid(data.grid, texts)["verdict"] if data.grid else "?"
    cal = (_records(data.attestation).get(draw.DEVELOPMENT_CASE) or {}).get("calibration") or {}
    echo = sum(1 for u in (_records(data.attestation).get("قطع") or {}).get("uses") or []
               if _text(u.get("verdict")) == "covered")

    def classes(c: dict) -> str:
        return " · ".join(f"{k} {c.get(k, 0)}" for k in
                          ("imported", "direction", "inert", "collision"))

    lines = [
        f"  ── the result (k / {mine.total}, strict, no partial credit) ──",
        f"  Islambouli table      : k / {mine.total} = {mine.k} / {mine.total}   "
        f"uses covered {ours['covered']} / {ours['uses']}",
        f"    misses              : {classes(ours['classes'])}",
        f"  closed physics table  : k / {cm.total} = {cm.k} / {cm.total}   "
        f"uses covered {closed['covered']} / {closed['uses']}   (read from its record)",
        f"    misses              : {classes(closed['classes'])}",
        f"  signature-letter split (inherited for comparability; its rationale, "
        f"rarity ordering, is non-binding here):",
        f"    Islambouli          : {mine.signature[0]} / {mine.signature[1]} with · "
        f"{mine.plain[0]} / {mine.plain[1]} without",
        f"    closed              : {cm.signature[0]} / {cm.signature[1]} with · "
        f"{cm.plain[0]} / {cm.plain[1]} without",
        f"  granularity           : {ours['uses']} blind uses against {closed['uses']} — "
        f"a finer list is harder to cover under a metric with no partial credit",
        f"  calibration «{draw.DEVELOPMENT_CASE}»   : reference {cal.get('reference_count')}, "
        f"blind {cal.get('blind_count')}, matched {cal.get('matched')} → {cal.get('verdict')}",
        f"  system check          : {verdict} — a miss bears partly on a generative "
        "principle (the دفع series and the pairs H1–H3 are regular) and partly on "
        "independent single-slot glosses",
        f"  note                  : row ق's gloss is «قطع، أو وقف شديد», so for the "
        f"witness root قطع the reading contains the root's own word; {echo} of the "
        f"{ours['covered']} covered uses are that root's",
        f"  scope                 : this table, transcribed from this poster, under "
        "this positional rule and this criterion, on these 40 roots. Not a verdict "
        "on Islambouli's method, nor on the معاني الحروف tradition.",
    ]
    for label, text in RESERVATIONS:
        lines.append(f"  {label}: " + text.format(
            blind=ours["uses"], closed=closed["uses"], matched=cal.get("matched"),
            reference=cal.get("reference_count"), blind_dev=cal.get("blind_count")))
    return lines


# ── entry points ─────────────────────────────────────────────────────────────
def validate(data: Datasets | None = None) -> list[str]:
    """Every finding, in section order. Empty == clean."""
    data = data or Datasets.load()
    _replay, witness_findings = check_witness_set(data)
    _metric, metric_findings = metric(data)
    return [*witness_findings, *check_table(data), *check_grid(data), *check_lock(data),
            *check_uses(data), *metric_findings]


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
    if data.lock is not None:
        print(f"  table freeze         : FROZEN at v{_text(data.lock.get('version'))} "
              f"(sha256 {_text(data.lock.get('sha256'))[:12]}…, since "
              f"{_text(data.lock.get('frozen_on'))}); pages cited: none")
    if data.grid is not None:
        texts = {int(r["row"]): r.get("text") or "" for r in rows}
        primary = evaluate_grid(data.grid, texts, "primary")
        alt = evaluate_grid(data.grid, texts, "alternative")
        print()
        print(f"  system check (§D11)  : {primary['verdict'].upper()}"
              + ("" if primary["verdict"] == alt["verdict"]
                 else f"  (row 14 read as «، أو»: {alt['verdict']})"))
        for key in ("C1_literal", "C2_exhaustive", "C3_no_same_form_in_two_slots",
                    "C4_discrimination", "H1", "H2", "H3", "H4"):
            print(f"    {key:<30}: {'holds' if primary[key]['holds'] else 'FAILS'}")
        print(f"    rows with ≥ 2 slots           : "
              f"{primary['rows_with_two_or_more_slots']} / {len(rows)} "
              f"(a `list` below {LIST_THRESHOLD})")
    if data.attestation is not None:
        recs = _records(data.attestation)
        holdout = [_text(e.get("root")) for e in w.get("roots") or []]
        n_uses = sum(len(recs.get(r, {}).get("uses") or []) for r in holdout)
        dev = recs.get(draw.DEVELOPMENT_CASE) or {}
        cal = dev.get("calibration") or {}
        print()
        print(f"  uses                 : {n_uses} for the {len(holdout)} witness roots, "
              "written blind to the table")
        print(f"    calibration «{draw.DEVELOPMENT_CASE}» : reference {cal.get('reference_count')}, "
              f"blind {cal.get('blind_count')}, matched {cal.get('matched')} → "
              f"{str(cal.get('verdict', '?')).upper()}")
        m_, _f = metric(data)
        if m_.printable:
            print()
            for line in publication(data):
                for wrapped in _wrap(line):
                    print(wrapped)
        if not m_.printable:
            for line in (m_.note or "").split(". "):
                if line:
                    print(f"    {line.rstrip('.')}.")
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
