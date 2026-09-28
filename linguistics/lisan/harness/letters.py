"""
letters.py — a root-key hamza seat, resolved to the letter `ء`.

Moved here from `concept/features.py` so that a second engine can map a seat the
same way without importing the closed engine (the core-first → concept boundary
in `tests/test_import_direction.py` forbids any other lisan module from reaching
into `concept/`). `concept/features.py` re-exports this same object.

**Do NOT "simplify" this into `arabic_text.fold_carrier`.** That helper maps
أ→ا, ؤ→و, ئ→ي, آ→ا: it folds TOWARD the carrier and deletes the hamza. A letter
table keyed on the hamza then resolves every seat either to a letter that has no
row (`ا`) or to the wrong one (`و`, `ي`). The failure is silent, because an
unmapped letter already has a documented, plausible-looking outcome. The explicit
map is the right primitive here; the obvious helper does the opposite of what is
needed.

There are four entries. `إ` and `ٱ` are deliberately absent: neither occurs in a
QAC root key (the 1656 keys use 31 distinct characters, and those two are not
among them).
"""
from __future__ import annotations

HAMZA_CARRIERS: dict[str, str] = {"أ": "ء", "ؤ": "ء", "ئ": "ء", "آ": "ء"}
