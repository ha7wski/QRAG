"""
assemble.py — the project's mechanical junction of a root's three Islambouli rows.

    <seg(pos 1)> <wasf(seg(pos 2))> منتهٍ ب<seg(pos 3)>

**This is NOT Islambouli's physical stage, and must never be presented as such.**
His two published stages do not follow one schema: ضرب keeps «دفع شديد» of row ض and
qualifies position 2 (مكرر); كتب keeps only «ضغط» of row ك, picks it over «وقف», and
COORDINATES position 2 with «و». Which words of a row count, and how rows join, are
per-root editorial decisions — a third place of interpretation after the table and
after the choice between alternatives. The template reproduces none of them, on
purpose; the gap to his sentences is pinned by the tests and shown on the page
(design.md §D1 of `assemble-islambouli-physical-stage`).

**The segment** of a row is the text after «يدل على» up to its first sentence-ending
full stop, verbatim. The frame «صوت … يدل على» is the poster's formula. Row ء is the
one row whose formula varies («صوت خفيف يدل على»), and its «خفيف» qualifies the
sound, so it goes with the frame. Ambiguities are recorded as segment notes in the
وصف lock, never resolved by a rule.

**The only material this module adds** is `CONNECTOR`, single spaces and the
brackets around an alternative group. No word is dropped, reordered or added; there
is no per-root and no per-letter case; the comma of row ض dangles and stays.

**«أو» is never decided here.** A segment split at «أو» is a group, rendered whole
inside «( )». A single alternative is rendered only from a `SignedChoices` — a
personal reading whose author is named — and that is the ONLY way a choice enters.
There is no default, no heuristic, no score, no model, and no randomness.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from linguistics.lisan.islambouli.compose import POSITIONS, compose  # noqa: E402
from linguistics.lisan.islambouli.wasf import wasf_table  # noqa: E402

CONNECTOR = "منتهٍ ب"
FORMULA = "يدل على"
ALTERNATIVE = "أو"
LIST_COMMA = "،"
QUALIFIED_POSITION = 1          # index into POSITIONS: the body

REFUSAL_SILENT = "silent-position"
REFUSAL_NO_FORMULA = "no-formula"


class InvalidChoice(ValueError):
    """A signed choice names a position without a group, or an absent alternative."""


@dataclass(frozen=True)
class SignedChoices:
    """Alternatives chosen by a NAMED person. The only door through which a choice enters."""

    author: str
    choices: dict[int, int] = field(default_factory=dict)   # position index → alternative index

    def __post_init__(self):
        if not (self.author or "").strip():
            raise InvalidChoice("A choice between alternatives is an interpretation and must be signed.")


@dataclass(frozen=True)
class AssembledPosition:
    position: str
    letter: str
    segment: str                      # the row's meaning segment, verbatim
    alternatives: tuple[str, ...]     # >1 only when the segment carries «أو»
    rendered: str                     # what this position contributes to the sentence
    chosen: int | None = None         # the alternative a signed reading chose

    @property
    def is_group(self) -> bool:
        return len(self.alternatives) > 1


@dataclass(frozen=True)
class Assembly:
    root: str
    sentence: str
    positions: tuple[AssembledPosition, ...]
    author: str | None = None         # set only when a signed choice was applied
    wasf_version: str = ""
    refused: bool = False
    refusal_code: str = ""
    refusal_reason: str = ""


def segment(text: str) -> str | None:
    """The meaning segment of a row: after «يدل على», up to the first full stop."""
    at = text.find(FORMULA)
    if at < 0:
        return None
    rest = text[at + len(FORMULA):]
    stop = rest.find(".")
    return " ".join((rest if stop < 0 else rest[:stop]).split())


def _alternative_groups(tokens: list[str]) -> list[list[str]]:
    """Split tokens at every standalone «أو»; the separator itself is not kept."""
    groups: list[list[str]] = [[]]
    for token in tokens:
        if token == ALTERNATIVE:
            groups.append([])
        else:
            groups[-1].append(token)
    return groups


def _qualify(tokens: list[str]) -> list[str]:
    """Replace the head (first word) of each alternative through the closed table."""
    table = wasf_table()
    out, head = [], True
    for token in tokens:
        if head and token != ALTERNATIVE:
            bare = token.rstrip(LIST_COMMA)
            wasf = table.get(bare)
            token = (wasf + token[len(bare):]) if wasf else token
            head = False
        elif token == ALTERNATIVE:
            head = True
        out.append(token)
    return out


def _position(index: int, letter: str, seg: str, chosen: int | None) -> AssembledPosition:
    tokens = seg.split()
    if index == QUALIFIED_POSITION:
        tokens = _qualify(tokens)
    groups = _alternative_groups(tokens)
    alternatives = tuple(" ".join(g).rstrip(LIST_COMMA).strip() for g in groups)
    if len(groups) == 1:
        rendered = " ".join(tokens)
    elif chosen is None:
        rendered = "(" + " ".join(tokens) + ")"
    else:
        rendered = alternatives[chosen]
    return AssembledPosition(position=POSITIONS[index], letter=letter, segment=seg,
                             alternatives=alternatives, rendered=rendered, chosen=chosen)


def assemble(root: str, signed: SignedChoices | None = None) -> Assembly:
    """The mechanical junction of `root`'s three rows. No choice without `signed`."""
    reading = compose(root)
    version = wasf_table().version
    if reading.refused:
        return Assembly(root=reading.root, sentence="", positions=(), wasf_version=version,
                        refused=True, refusal_code=reading.refusal_code,
                        refusal_reason=reading.refusal_reason)
    if reading.partial:
        return Assembly(root=reading.root, sentence="", positions=(), wasf_version=version,
                        refused=True, refusal_code=REFUSAL_SILENT,
                        refusal_reason=f"لا سطرَ في الجدول للحرف {'، '.join(reading.silent_letters)}، "
                                       "ولا تُركَّب جملةٌ ناقصة.")
    choices = dict(signed.choices) if signed else {}
    positions = []
    for index, p in enumerate(reading.positions):
        seg = segment(p.text)
        if not seg:
            return Assembly(root=reading.root, sentence="", positions=(), wasf_version=version,
                            refused=True, refusal_code=REFUSAL_NO_FORMULA,
                            refusal_reason=f"سطر «{p.label}» لا يتضمّن «{FORMULA}».")
        positions.append(_position(index, p.letter, seg, None))
    for index, alt in choices.items():
        if not 0 <= index < len(positions) or not positions[index].is_group:
            raise InvalidChoice(f"Position {index} of «{reading.root}» has no alternative group.")
        if not 0 <= alt < len(positions[index].alternatives):
            raise InvalidChoice(f"Position {index} of «{reading.root}» has no alternative {alt}.")
        p = positions[index]
        positions[index] = _position(index, p.letter, p.segment, alt)
    first, body, last = (p.rendered for p in positions)
    return Assembly(
        root=reading.root,
        sentence=f"{first} {body} {CONNECTOR}{last}",
        positions=tuple(positions),
        author=signed.author.strip() if (signed and choices) else None,
        wasf_version=version,
    )
