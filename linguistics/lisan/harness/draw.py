"""
draw.py — the holdout frame and the seeded, stratified sample.

This is the procedure `concept_witness_set.json` records, written once:

    frame = triliteral QAC roots with a Maqāyīs `has_asl` row (joined through
            `normalize_root`) and at least 20 occurrences, minus the exclusions
    lower = frame roots with < 100 occurrences;  upper = the rest
    rng   = random.Random(seed)
    drawn = sorted(rng.sample(lower, n_lower)) + sorted(rng.sample(upper, n_upper))

Both `sample()` calls use the SAME generator, lower stratum first. The order is
not cosmetic: reversing it yields a different set.

The constants below record the exclusions as they stood at the FIRST draw. They
are frozen literals, not a re-read of today's `root_cores.json`. A draw is a
historical event, and replaying it against a curated set that has since grown
would reproduce a different frame and report the file as edited.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from arabic_text import normalize_root  # noqa: E402

MIN_OCCURRENCES = 20
STRATUM_BOUNDARY = 100

CURATED_AT_FIRST_DRAW = ("خبث", "خير", "رحم", "ظلم", "كفر")
DEVELOPMENT_CASE = "ضرب"

# The closed engine's collision-probe roots. They are recorded here because every
# later holdout reports its overlap with them.
PROBE_ROOTS = ("حرب", "حرج", "حرد", "تبر", "كبر", "كود", "كيد")

# The first draw, as recorded. Every later draw asserts that it can still
# reproduce this one before it samples anything.
FIRST_SEED = 20260925
FIRST_FRAME = (205, 75)
FIRST_DRAWN = (29, 11)


def build_frame(morphology: dict[str, dict], has_asl: frozenset[str],
                excluded) -> tuple[list[str], list[str], list[str]]:
    """`(frame, lower, upper)`, each sorted — the list the sample is drawn from."""
    excluded = set(excluded)
    frame = sorted(
        root for root, rec in morphology.items()
        if len(root) == 3
        and normalize_root(root) in has_asl
        and rec.get("count", 0) >= MIN_OCCURRENCES
        and root not in excluded
    )
    lower = [r for r in frame if morphology[r]["count"] < STRATUM_BOUNDARY]
    upper = [r for r in frame if morphology[r]["count"] >= STRATUM_BOUNDARY]
    return frame, lower, upper


def sample(lower: list[str], upper: list[str], seed: int,
           n_lower: int, n_upper: int) -> tuple[str, ...]:
    """The draw: one generator, lower stratum first, each stratum sorted."""
    rng = random.Random(seed)
    return tuple(sorted(rng.sample(lower, n_lower))
                 + sorted(rng.sample(upper, n_upper)))


class FrameMoved(RuntimeError):
    """The first draw no longer reproduces, so no later draw can claim its frame."""


def first_draw(morphology: dict[str, dict],
               has_asl: frozenset[str]) -> tuple[list[str], list[str], tuple[str, ...]]:
    """`(lower, upper, drawn)` for the FIRST holdout, with its preconditions asserted.

    Raises `FrameMoved` if the recorded frame (205 + 75) or the recorded draw
    (seed 20260925, 29 + 11) no longer reproduces. A later draw built on a frame
    that has moved would be drawn from a different population than the one it
    claims to share with the first.
    """
    _frame, lower, upper = build_frame(
        morphology, has_asl, set(CURATED_AT_FIRST_DRAW) | {DEVELOPMENT_CASE}
    )
    if (len(lower), len(upper)) != FIRST_FRAME:
        raise FrameMoved(
            f"the first frame reproduces {len(lower)} + {len(upper)}, recorded "
            f"{FIRST_FRAME[0]} + {FIRST_FRAME[1]}"
        )
    drawn = sample(lower, upper, FIRST_SEED, *FIRST_DRAWN)
    return lower, upper, drawn


def draw_after(morphology: dict[str, dict], has_asl: frozenset[str],
               first_recorded: tuple[str, ...], seed: int,
               n_lower: int, n_upper: int) -> tuple[list[str], list[str], tuple[str, ...]]:
    """A later holdout: the first frame, minus the first holdout, resampled.

    `first_recorded` is the first holdout as its file records it. It must equal
    the replay of the first draw, or `FrameMoved` is raised: the roots excluded
    here are the ones actually burned, not the ones a moved frame would produce.
    Returns `(lower_remaining, upper_remaining, drawn)`.
    """
    lower, upper, first = first_draw(morphology, has_asl)
    if tuple(first_recorded) != first:
        raise FrameMoved("the first holdout on file is not the replay of the first draw")
    burned = set(first)
    lower_rest = [r for r in lower if r not in burned]
    upper_rest = [r for r in upper if r not in burned]
    return lower_rest, upper_rest, sample(lower_rest, upper_rest, seed, n_lower, n_upper)
