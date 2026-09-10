"""
coverage.py — the Tahlil coverage log: every claim the gate refused, and every claim it
kept only after weakening the badge.

Why a log at all: the page is *cite-or-omit*, so a reader never sees what was dropped.
Without a log the failure mode is invisible by construction — a prompt that stopped
citing naẓāʾir would silently thin every دلالي block and look, from the page, exactly
like a corpus with fewer naẓāʾir. The log is the only place that difference shows up.

Two outcomes are recorded, not one:

  * ``drop``      — the claim never renders (no provenance at all).
  * ``downgrade`` — the claim renders, with a weaker badge. Exactly one reason produces
    this (``sense-selection-unanchored``); see ``citations.py``.

Both matter for triage, and they matter *differently*: a rising drop rate means the
generator is inventing, while a rising downgrade rate means the prompt stopped asking
for the disambiguator. Collapsing them into one "rejected" counter would hide which of
the two is happening — so the outcome is a column, and the sweep reports it per reason
(task 12.2).

The log is append-only TSV at ``data/runtime/tahlil_coverage.tsv`` (override with
``TAHLIL_COVERAGE_LOG``), chosen to match the change's other measurement artifacts
(`baseline-coverage.tsv`) so one toolchain reads them all. Pure stdlib; writing is
best-effort and never raises into a request path — a logging failure must not take down
an analysis, but it is reported once so it cannot pass unnoticed.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quran_data.paths import tahlil_coverage_path  # noqa: E402

COLUMNS = ("ref", "block", "reason", "outcome", "badge_before", "badge_after", "text", "cites")

_OUTCOMES = ("drop", "downgrade")

_lock = threading.Lock()
_warned = False


def log_path() -> Path:
    """The active log path. Env override keeps tests off the real runtime file.

    The default location and the `TAHLIL_COVERAGE_LOG` override both live in the
    dataset registry — the override is read on every call, not frozen at import,
    so a test that exports it after this module loaded still redirects the log.
    """
    return tahlil_coverage_path()


def _clean(value: object) -> str:
    """One TSV cell: **every** whitespace run folded to a single space.

    Not just `\\t` and `\\n`: a lone carriage return (`\\r`, and it only takes one — a
    pasted claim, a Windows-authored prompt fixture) both splits the row on read and
    silently truncates the write, so the log gains a row with fewer cells than the header.
    `read_rows` then returns a torn dict and the sweep raises `KeyError`. The log is
    APPEND-ONLY, so that single claim corrupts it permanently: every later run of task 12.2
    crashes on the same line. `str.split()` folds the whole Unicode whitespace class
    (`\\r`, `\\v`, `\\f`, NBSP, line/paragraph separators…), which is the only version of
    this rule that cannot be defeated by one more exotic character.
    """
    return " ".join(str(value if value is not None else "").split())


def record(events: list[dict], ref: str = "") -> int:
    """Append `events` to the coverage log; returns how many rows were written.

    Each event is ``{block, reason, outcome, badge_before, badge_after, text, cites}``;
    `ref` fills the first column when the event does not carry its own. Unknown outcomes
    are written verbatim rather than corrected — the sweep asserts the closed set, and
    silently normalizing a bad value here would hide the very drift that assertion exists
    to catch.

    Never raises — and "never" is unconditional, so the guard has to be too. Row BUILDING
    is inside the try and the except is `Exception`, not `OSError`: an event carrying a
    non-string cite (or not being a dict at all) used to raise straight out of a request
    path *from the function whose docstring promised it could not*. A narrow except only
    covers the failure its author happened to imagine; this one covers the failures the
    generator will actually produce. Each cite is `_clean`ed individually for the same
    reason a cell is: whatever it is, it becomes one safe token.
    """
    global _warned
    if not events:
        return 0
    path = log_path()
    try:
        rows = []
        for e in events:
            rows.append("\t".join(_clean(v) for v in (
                e.get("ref", ref),
                e.get("block", ""),
                e.get("reason", ""),
                e.get("outcome", ""),
                e.get("badge_before", ""),
                e.get("badge_after", ""),
                e.get("text", ""),
                ",".join(_clean(c) for c in (e.get("cites") or ())),
            )))
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            new = not path.exists() or path.stat().st_size == 0
            with path.open("a", encoding="utf-8") as f:
                if new:
                    f.write("\t".join(COLUMNS) + "\n")
                f.write("\n".join(rows) + "\n")
    except Exception as exc:  # unwritable disk, or a malformed event
        if not _warned:
            print(f"[tahlil.coverage] cannot write {path}: {exc}", file=sys.stderr)
            _warned = True
        return 0
    return len(rows)


def read_rows(path: Path | str | None = None) -> list[dict]:
    """Parse the log back into dicts — used by the sweep and by the tests."""
    p = Path(path) if path else log_path()
    if not p.exists():
        return []
    out: list[dict] = []
    with p.open(encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            cells = line.rstrip("\n").split("\t")
            out.append(dict(zip(header, cells)))
    return out


def summarize(path: Path | str | None = None) -> dict:
    """`{reason: {outcome: count}}` — the shape task 12.2 reports.

    Kept deliberately dumb: it counts what is in the file, including reasons outside the
    closed set, so an unknown reason surfaces as a row instead of vanishing.

    Every access is `.get`, including the increment. A short row — from a hand-edited log,
    a truncated write, or a pre-fix line already on disk — yields a dict missing `reason`
    or `outcome`, and `row["reason"]` would raise `KeyError` and take the whole sweep down
    over one bad line. Counting it under `""` keeps the sweep running AND makes the damage
    visible as a row, which is the entire purpose of this function.
    """
    agg: dict[str, dict[str, int]] = {}
    for row in read_rows(path):
        reason, outcome = row.get("reason", ""), row.get("outcome", "")
        counts = agg.setdefault(reason, {})
        counts[outcome] = counts.get(outcome, 0) + 1
    return agg


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["TAHLIL_COVERAGE_LOG"] = str(Path(tmp) / "cov.tsv")
        record([
            {"block": "dalali", "reason": "no-citation", "outcome": "drop",
             "badge_before": "مُولَّد", "text": "دعوى بلا شاهد", "cites": []},
            {"block": "sarfi", "reason": "sense-selection-unanchored", "outcome": "downgrade",
             "badge_before": "مُولَّد", "badge_after": "تأويلي", "text": "المفاعلة للمبالغة",
             "cites": ["sigha:bab.III@0.1.0"]},
            # A claim carrying a carriage return and a non-string cite: one row each, and
            # the log stays parseable — the two shapes that used to corrupt it / raise.
            {"block": "huruf", "reason": "non-arabic-output", "outcome": "drop",
             "text": "سطر\rمكسور", "cites": [3]},
        ], ref="23:61:2")
        print(f"rows: {len(read_rows())}")
        print(summarize())
        # A malformed event must be swallowed, not raised: the promise is unconditional.
        print("hostile event ->", record([None]), "rows written")
