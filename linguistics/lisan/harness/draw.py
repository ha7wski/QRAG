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
