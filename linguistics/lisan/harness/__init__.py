"""
harness/ — the measurement a letter table is put through, shared by every table.

`k / 40` means something only if the method stays fixed while the table changes.
The physics-first engine (`linguistics/lisan/concept/`) was the first table to go
through it and closed at `k / 40 = 0`. The Islambouli table
(`linguistics/lisan/islambouli/`) is the second. For the two numbers to be
comparable, the method is not copied into the second engine; it lives here and
both engines import it. "Same method" is then a property of the call graph rather
than a sentence in a design note.

The modules, split by what they are allowed to know:

    letters.py   the hamza-carrier table that turns a root-key seat into `ء`
    draw.py      the holdout frame, its strata and the seeded sample
    guard.py     the pieces of the witness guard that do not depend on which
                 holdout is guarded
    verdicts.py  the uses record, the per-use and per-root verdicts, the miss
                 classes and the strict metric gate

`letters`, `draw` and `guard` know root spellings and occurrence counts, and
nothing about meaning, so a composer may import them. `verdicts` reads glossed
uses. The composers never import it, and `tests/test_import_direction.py`
enforces that for each engine.

This package was extracted from the closed engine without changing its
behaviour: the closed validator's output and its verdict worksheet were replayed
byte for byte before and after the move.
"""
