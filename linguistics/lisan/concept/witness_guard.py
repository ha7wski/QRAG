"""
witness_guard.py — a test may not compose a witness root. Hard failure, not a note.

**This file exists because of a recorded incident, and it says so.** While the 40
witness roots' `uses[]` were being frozen — the step §D9 orders BEFORE any concept
of theirs exists — a test run of `confront.py`'s `__main__` composed `قوم`, a
witness root. The concept was never recorded, never displayed and never read by the
person writing that root's uses, so the freeze's claim survived; it was recorded
verbatim in `concept_attestation.json`'s `how_these_uses_were_written` rather than
smoothed over. But the protection was a sentence in a meta block, and a sentence in
a meta block protects nothing from the next test somebody writes.

**What is forbidden, exactly.** Under a test runner, `compose()` — and therefore
`confront()`, which calls it — raises `WitnessRootComposed` for any root in
`data/references/concept_witness_set.json`. There is no warning mode, no
environment variable that relaxes it and no `strict=False`. A test that needs a
three-letter root has 1600 others to choose from.

**Why the guard is scoped to test runs, and not to everything.** Two callers must
compose witness roots and both are legitimate:

  * the SHIPPED PRODUCT. `POST /lisan/concept` answers for whatever root a reader
    types, and a reader does not know the holdout exists. A guard that refused
    there would turn a research protocol into a missing feature.
  * the RECORDING PATH. `scripts/record_concept_verdicts.py` composes all 40 by
    definition — that is §D9 step 2. It runs outside pytest, so it needs no
    exemption; it takes one anyway, explicitly, through
    `recording_the_witness_set()`, so the sanctioned caller is greppable and a
    test covering that script can borrow the same door instead of inventing one.

A test is the case that is different in kind. It runs constantly, unattended, and
whatever it composes it also PINS: an assertion on a witness root's realised
primitives is an expectation written from the concept, living in the repository,
and it is exactly the shape of evidence `no-back-fitting` forbids. Re-freezing or
extending that root's `uses[]` afterwards would then be done by someone who has
read its reading — with nothing in the record to show it.

**An empty or unreadable holdout raises under a test runner** rather than letting
every root through. `confront.witness_roots` fails open for the opposite and
correct reason: there, an empty set can only shrink what the metric claims. Here,
an empty set silently disarms the guard, which is the failure mode the guard is.
"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402


class WitnessRootComposed(RuntimeError):
    """A test composed a root from the pre-registered holdout."""


# How deep inside `recording_the_witness_set()` we are. An int rather than a bool
# so nesting — the recording script calling a helper that takes the sanction too —
# cannot let the outer one lift the guard early on its way out.
_sanctioned = 0


def _under_test_runner() -> bool:
    """Whether this process is a test run.

    Both signals are checked because neither alone covers the cases: the env var
    is set by pytest per test and is absent at import time and in fixtures, while
    `sys.modules` catches collection, session fixtures and anything a plugin does
    outside a test. A subprocess spawned by a test inherits the env var and is
    covered by the first.
    """
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules


@lru_cache(maxsize=1)
def witness_roots() -> frozenset[str]:
    """The holdout's 40 roots, cached for the process.

    Reads ONLY `concept_witness_set.json` — root keys and draw metadata, no gloss,
    no aṣl, no sense. The blindness rule bans the meaning datasets; a list of root
    spellings is not one, and this module could not do its job without it.
    """
    witness = loaders.concept_witness_set()
    entries = witness.get("roots")
    if not isinstance(entries, list):
        return frozenset()
    return frozenset(
        str(entry.get("root") or "").strip()
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("root") or "").strip()
    )


@contextmanager
def recording_the_witness_set():
    """The one sanctioned way to compose a witness root under a test runner.

    Used by `scripts/record_concept_verdicts.py` — which does not need it, running
    outside pytest — so that the exemption is visible at the only place it applies
    and a test of that script can take the same door. It is deliberately NOT a flag
    on `compose()`: a parameter would make every call site a place where the
    holdout can be opened, where a context manager makes it one block, named after
    what it is for.
    """
    global _sanctioned
    _sanctioned += 1
    try:
        yield
    finally:
        _sanctioned -= 1


def check(root: str) -> None:
    """Raise if a test is composing a witness root. Silent in every other case."""
    if not _under_test_runner() or _sanctioned:
        return
    roots = witness_roots()
    if not roots:
        raise WitnessRootComposed(
            "The witness set read back EMPTY under a test runner, so this guard "
            "cannot tell a holdout root from any other and is disarmed. That is "
            "the failure it exists to prevent, so it refuses instead of letting "
            "everything through. Check data/references/concept_witness_set.json."
        )
    if root not in roots:
        return
    raise WitnessRootComposed(
        f"«{root}» is one of the 40 pre-registered witness roots, and a TEST just "
        f"composed it. Refused.\n\n"
        f"The holdout is the whole evidential value of k / 40: its uses[] were "
        f"frozen before any concept of theirs existed, and a test that composes "
        f"one PINS its reading in the repository — after which nobody can extend "
        f"or re-freeze that root's uses without having read what the engine says "
        f"about it. This happened once already, to «قوم», and is recorded in "
        f"concept_attestation.json.\n\n"
        f"Use any of the ~1600 roots that are not in the holdout. If you are "
        f"writing the recording path itself, wrap it in "
        f"witness_guard.recording_the_witness_set()."
    )
