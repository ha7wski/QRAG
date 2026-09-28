"""
guard.py — the holdout-independent half of a witness guard.

Each engine keeps its own `witness_guard` module, because each guards its own
holdout and each explains its own refusal. What they share is what a guard IS:

* **Test-runner detection.** Two signals, because neither alone covers every
  case. The env var is set by pytest per test and is absent at import time and
  in fixtures; `sys.modules` catches collection, session fixtures and anything a
  plugin does outside a test. A subprocess spawned by a test inherits the env
  var and is covered by the first.
* **A sanction that nests.** A counter rather than a bool, so that a recording
  script calling a helper that also takes the sanction cannot let the outer one
  lift the guard early on its way out.
* **One exception type.** `WitnessRootComposed`, whichever holdout raised it.

There is no environment switch here and there must never be one. Reading
`PYTEST_CURRENT_TEST` detects a test run; any other read would be an off switch.
"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager


class WitnessRootComposed(RuntimeError):
    """A test composed a root from a pre-registered holdout."""


def under_test_runner() -> bool:
    """Whether this process is a test run."""
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules


def roots_of(witness: dict) -> frozenset[str]:
    """The root spellings a holdout file records. Absent or malformed → empty.

    Empty is NOT safe for a guard, and each guard raises on it. This parser only
    reports what the file says.
    """
    entries = witness.get("roots")
    if not isinstance(entries, list):
        return frozenset()
    return frozenset(
        str(entry.get("root") or "").strip()
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("root") or "").strip()
    )


class Sanction:
    """The nesting counter behind a guard's one sanctioned recording door."""

    def __init__(self) -> None:
        self.depth = 0

    @contextmanager
    def held(self):
        self.depth += 1
        try:
            yield
        finally:
            self.depth -= 1

    def __bool__(self) -> bool:
        return self.depth > 0
