"""
witness_guard.py — a test may not compose a root of the SECOND holdout.

The same guard as the closed engine's, over `islambouli_witness_set.json`: under
a test runner, `compose()` raises `WitnessRootComposed` from its first line for
any of those 40 roots. There is no warning mode, no flag and no environment
switch. A test that pins a witness root's reading is an expectation written from
that reading, living in the repository — and the uses for these roots are
written blind to it.

An empty or unreadable holdout RAISES under a test runner rather than letting
every root through: an empty set would disarm the guard, which is the failure
the guard exists to prevent.

The recording path takes the one sanctioned door, `recording_the_witness_set()`,
so the exemption is greppable.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from linguistics.lisan.harness.guard import (  # noqa: E402,F401
    Sanction,
    WitnessRootComposed,
    roots_of,
    under_test_runner,
)

_sanction = Sanction()


@lru_cache(maxsize=1)
def witness_roots() -> frozenset[str]:
    """The second holdout's 40 roots — spellings only, no meaning."""
    return roots_of(loaders.islambouli_witness_set())


@contextmanager
def recording_the_witness_set():
    """The one sanctioned way to compose a second-holdout root under a test runner."""
    with _sanction.held():
        yield


def check(root: str) -> None:
    """Raise if a test is composing a root of the second holdout."""
    if not under_test_runner() or _sanction:
        return
    roots = witness_roots()
    if not roots:
        raise WitnessRootComposed(
            "The Islambouli holdout read back EMPTY under a test runner, so this "
            "guard cannot tell a witness root from any other and refuses instead "
            "of letting everything through. Check "
            "data/references/islambouli_witness_set.json."
        )
    if root in roots:
        raise WitnessRootComposed(
            f"«{root}» is one of the 40 roots of the Islambouli holdout, and a TEST "
            f"just composed it. Refused. Its uses are written blind to its reading; "
            f"a test that pins the reading puts it in the repository first. Use a "
            f"root off both holdouts, or, on the recording path, "
            f"witness_guard.recording_the_witness_set()."
        )
