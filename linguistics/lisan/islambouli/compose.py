"""
compose.py — a root's reading under Islambouli's table: three positions, verbatim.

**The positional rule is the harness's, and it is inherited unchanged**: the 1st
radical OPENS, the 2nd is the BODY, the 3rd CONCLUDES. No code path assigns any
other, and there is no per-root exception mechanism.

**Each position carries its radical's row text, VERBATIM**, and the reading is
nothing more than the three texts in that order. There is no sentence, no
connective, no template and no LLM. The closed engine licensed each word of its
sentence from a primitive's declared lemmas; here the only licensed words are
Islambouli's, and any connective written between his glosses would be the project
speaking in his name. The judge is given the three texts in positional order,
which is exactly what the coverage criterion says the reader is given.

**The inherited composition constants are NON-BINDING here, and are declared so
before any reading exists.** Within a position, the closed engine ordered its
primitives by rarity and realised the top three. A row of this table is ONE
gloss, and one gloss per position never reaches a window of three, so neither
the ordering nor the window selects anything. `REALISED_PER_POSITION` is kept to
say that, not to do anything.

**Root-key letters → rows** (design.md §D5):

    the 28 consonants   their own row (`ه` → «هـ»)
    أ ؤ ئ ء (and آ)     «ء», through the harness's explicit carrier map
    bare ا               «آ - ى» — the user's decision, taken before the draw
    و ي as radicals      their own rows, with no exception

`آ` and `ى` occur in no QAC root key, so row «آ - ى» is reachable only through a
bare `ا` (اني اول هاء هات). None of the 40 witness roots has one.

A character with no row makes its position SILENT and the reading PARTIAL, with
the letter named. Nothing falls back, and no flag restores a fallback. On today's
data every character of every QAC root key has a row, so this path is
unreachable; it stays, and it is tested.

Quadriliteral roots get NO reading, with the reason stated. The three-position
rule is not stretched to four: adapting the rule to the case is what this design
forbids.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from linguistics.lisan.harness.letters import HAMZA_CARRIERS  # noqa: E402
from linguistics.lisan.islambouli import witness_guard  # noqa: E402
from linguistics.lisan.islambouli.table import table  # noqa: E402

POSITIONS = ("opens", "body", "concludes")

# Inherited from the closed engine and non-binding under this table (see above).
REALISED_PER_POSITION = 3

# The two root-key letters whose row label is not the letter itself. Everything
# else maps by identity to a single-letter label, or through HAMZA_CARRIERS.
LABEL_EXCEPTIONS = {"ه": "هـ", "ا": "آ - ى"}

REFUSAL_NOT_TRILITERAL = "not-triliteral"


@dataclass(frozen=True)
class Position:
    position: str               # opens | body | concludes
    letter: str                 # the root-key character
    row: int | None             # the poster row, None when silent
    label: str                  # the row's label as printed, "" when silent
    text: str                   # the row's text VERBATIM, "" when silent

    @property
    def silent(self) -> bool:
        return self.row is None


@dataclass(frozen=True)
class Reading:
    root: str
    table_version: str
    table_sha256: str
    positions: tuple[Position, ...]
    refused: bool = False
    refusal_code: str = ""
    refusal_reason: str = ""

    @property
    def partial(self) -> bool:
        return any(p.silent for p in self.positions)

    @property
    def silent_letters(self) -> tuple[str, ...]:
        return tuple(p.letter for p in self.positions if p.silent)

    @property
    def texts(self) -> tuple[str, ...]:
        """The three texts in positional order — what the judge is given."""
        return tuple(p.text for p in self.positions)


def row_label(letter: str) -> str | None:
    """The label of the row a root-key character reads from, or None."""
    labels = table().by_label()
    if letter in LABEL_EXCEPTIONS:
        return LABEL_EXCEPTIONS[letter] if LABEL_EXCEPTIONS[letter] in labels else None
    folded = HAMZA_CARRIERS.get(letter, letter)
    return folded if folded in labels else None


def _radical_count(n: int) -> str:
    """«ذو أربعة أحرف» — the refusal is printed on the page as is, so it is Arabic."""
    words = {0: "بلا حرف", 1: "ذو حرفٍ واحد", 2: "ذو حرفين", 4: "ذو أربعة أحرف",
             5: "ذو خمسة أحرف", 6: "ذو ستة أحرف"}
    return words.get(n, f"ذو {n} أحرف")


def compose(root: str) -> Reading:
    witness_guard.check((root or "").strip())
    root = (root or "").strip()
    t = table()
    if len(root) != 3:
        return Reading(
            root=root, table_version=t.version, table_sha256=t.sha256, positions=(),
            refused=True, refusal_code=REFUSAL_NOT_TRILITERAL,
            refusal_reason=(
                f"الجذر «{root}» {_radical_count(len(root))}، والقاعدة الموضعية ثلاثة "
                "مواضع لا تُمَدّ إلى عددٍ آخر."
            ),
        )
    rows = t.by_label()
    positions = []
    for position, letter in zip(POSITIONS, root):
        label = row_label(letter)
        row = rows.get(label) if label else None
        positions.append(Position(
            position=position, letter=letter,
            row=row.row if row else None,
            label=row.label if row else "",
            text=row.text if row else "",
        ))
    return Reading(root=root, table_version=t.version, table_sha256=t.sha256,
                   positions=tuple(positions))
