"""
islambouli/ — Samer Islambouli's letter table, placed verbatim, and measured.

The physics-first engine (`linguistics/lisan/concept/`) closed at `k / 40 = 0`.
Its table was the project's own construction, so the obvious objection was left
standing: the project's table failed, not the tradition's. This package measures
a table PUBLISHED by someone else — Islambouli's, «علمية اللسان العربي وعالميته»,
transcribed from a poster that reproduces it — under the same harness
(`linguistics/lisan/harness/`), on a fresh holdout.

A transcribed table cannot be tuned: changing a row would mean no longer citing
Islambouli. The one risk it carries is a wrong copy, and
`scripts/validate_islambouli_datasets.py` checks that mechanically.

The modules:

    table.py          the frozen table, digest-checked against its lock at load
    witness_guard.py  a test may not compose a root of the second holdout
    compose.py        three fixed positions, each carrying its radical's row text
                      VERBATIM — no sentence, no connective, no template, no LLM
    confront.py       the ONE module allowed to read the aṣl and the uses; it
                      imports the reading result, and nothing here imports it

**Blindness is an import edge.** `tests/test_import_direction.py` forbids every
module here but `confront.py` from reaching or naming any dataset that says what
a root or a letter MEANS, other than this table. It also forbids EVERY module,
`confront.py` included, from naming the system-check grid. The grid analyses
the table; it is never an input.

Nothing is re-exported, so that no function shadows its module (the closed
engine's `__init__` records why).
"""
