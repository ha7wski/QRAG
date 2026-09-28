#!/usr/bin/env python3
"""
draw_islambouli_witness_set.py — draw the second holdout, once.

The Islambouli letter table is measured on its own 40 roots. The first holdout
(`concept_witness_set.json`) is burned: its 183 uses have been read. This script
draws the second one from the same frame, by the same procedure, with a new seed
fixed in the design note BEFORE any draw ran (`design.md` §D2):

    frame  = the first frame (280 = 205 + 75), rebuilt and asserted
    first  = seed 20260925 over it, asserted equal to the first file
    rest   = frame − first  (176 + 64)
    drawn  = Random(20260928): 29 from the lower rest, then 11 from the upper rest

The work is done by `linguistics/lisan/harness/draw.py`, the code that replays
the first draw, so "same method" is a fact of the call graph.

The file is written ONCE. If it exists, this script refuses: a draw repeated
until it looks convenient is not a holdout. `--check` replays the draw and
compares it with the file, without writing.

The structure recorded after the draw (weak radicals, hamza seats, bare alef,
overlap with every root the closed run exposed) is RECORDED, never acted on. No
root is excluded or replaced on its account.

Usage:
    python scripts/draw_islambouli_witness_set.py          # draw and write, once
    python scripts/draw_islambouli_witness_set.py --check  # replay against the file
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from quran_data.paths import ISLAMBOULI_WITNESS_SET_JSON  # noqa: E402
from linguistics.lisan.harness import draw  # noqa: E402

SEED = 20260928
DRAWN_ON = "2026-09-28"
N_LOWER, N_UPPER = draw.FIRST_DRAWN      # 29 + 11, the first draw's allocation


def has_asl() -> frozenset[str]:
    return frozenset(
        r["root_normalized"] for r in loaders.maqayis_asl()
        if (r.get("asl_status") or "").strip() == "has_asl"
    )


def first_recorded() -> tuple[str, ...]:
    return tuple(e["root"] for e in loaders.concept_witness_set()["roots"])


def replay() -> tuple[list[str], list[str], tuple[str, ...]]:
    """`(lower_rest, upper_rest, drawn)`, every precondition asserted."""
    return draw.draw_after(loaders.morphology(), has_asl(), first_recorded(),
                           SEED, N_LOWER, N_UPPER)


def _exposed_by_the_closed_run() -> dict[str, set[str]]:
    """Every root the closed run exposed, by how it was exposed.

    The probe roots are listed in the harness. The widening's roots are
    re-enumerated by the probe script's own rule, since the probe record keeps
    counts, not the list. The roots whose aṣl the widening published verbatim
    are the members of its non-`distinct` pairs.
    """
    from scripts.run_collision_probe import enumerate_widened_pairs

    widened = {root for pairs in enumerate_widened_pairs().values()
               for left, right, *_ in pairs for root in (left, right)}
    probe = loaders.concept_collision_probe()
    published = {
        root
        for run in probe.get("probes") or []
        for klass in (run.get("widening") or {}).get("classes") or []
        for item in klass.get("non_distinct") or []
        for root in item.get("pair") or []
    }
    return {
        "probe_roots": set(draw.PROBE_ROOTS),
        "widening_roots": widened,
        "widening_asl_published": published,
    }


def structure(drawn: tuple[str, ...]) -> dict:
    exposed = _exposed_by_the_closed_run()
    weak = sorted(r for r in drawn if set(r) & {"و", "ي"})
    hamza = sorted(r for r in drawn if set(r) & {"أ", "ؤ", "ئ", "ء"})
    bare = sorted(r for r in drawn if "ا" in r)
    return {
        "weak_radical_waw_or_ya": weak,
        "hamza_seat": hamza,
        "bare_alef": bare,
        "overlap_with_closed_run": {
            "probe_roots": sorted(set(drawn) & exposed["probe_roots"]),
            "widening_roots": sorted(set(drawn) & exposed["widening_roots"]),
            "widening_asl_published_verbatim": sorted(
                set(drawn) & exposed["widening_asl_published"]),
            "development_case": sorted(set(drawn) & {draw.DEVELOPMENT_CASE}),
        },
        "note": "Recorded after the draw, never acted on. No root was excluded, "
                "replaced or re-drawn on account of anything here. A root whose "
                "aṣl the closed run published has not had its USES read, which is "
                "what burned the first 40; the overlap is published so a reader "
                "can discount it.",
    }


def document(lower_rest: list[str], upper_rest: list[str],
             drawn: tuple[str, ...]) -> dict:
    morphology = loaders.morphology()
    lower_set = set(lower_rest)
    return {
        "meta": {
            "name": "islambouli-witness-set",
            "description": "The frozen holdout for the Islambouli letter table: 40 "
                           "triliteral roots against which k/40 is measured under "
                           "the harness that measured the closed physics-first "
                           "engine. Drawn and committed before any row of the "
                           "table was transcribed.",
            "holdout_discipline": [
                "The IDENTITY of these roots is public: a set can only be held "
                "out if it is known.",
                "What never happens before the table is frozen: writing their "
                "uses, reading their aṣl for the purpose of this measurement, or "
                "generating their readings.",
                "The set is never re-drawn. A draw repeated until it looks "
                "convenient is not a holdout.",
            ],
        },
        "seed": SEED,
        "seed_rationale": "Fixed in the design note (design.md §D2) before any "
                          "draw ran, and reviewed there. It is the date the note "
                          "was written.",
        "drawn_on": DRAWN_ON,
        "procedure": [
            "frame, lower, upper = harness.draw.build_frame(morphology, has_asl, "
            "CURATED_AT_FIRST_DRAW | {DEVELOPMENT_CASE}); assert (len(lower), "
            "len(upper)) == (205, 75)",
            "assert harness.draw.sample(lower, upper, 20260925, 29, 11) == "
            "concept_witness_set.json roots",
            "lower_rest = lower − first holdout; upper_rest = upper − first "
            "holdout",
            "drawn = harness.draw.sample(lower_rest, upper_rest, 20260928, 29, 11)"
            " — one generator, lower stratum first, each stratum sorted",
        ],
        "frame": {
            "size": len(lower_rest) + len(upper_rest),
            "derived_from": "the first holdout's frame (280 = 205 + 75), minus its "
                            "40 roots",
            "criteria": [
                "a triliteral QAC root key",
                "joined through arabic_text.normalize_root to a maqayis_asl.csv "
                "row whose asl_status is has_asl",
                "at least 20 Quranic occurrences (morphology.json `count`)",
            ],
            "exclusions": {
                "curated_at_first_draw": list(draw.CURATED_AT_FIRST_DRAW),
                "development_case": [draw.DEVELOPMENT_CASE],
                "first_holdout": "the 40 roots of concept_witness_set.json — "
                                 "burned, their 183 uses read",
            },
        },
        "preconditions_asserted": {
            "first_frame_reproduces": [205, 75],
            "first_draw_reproduces": True,
        },
        "strata": [
            {"name": "20-99 occurrences", "frame": len(lower_rest), "drawn": N_LOWER},
            {"name": "100+ occurrences", "frame": len(upper_rest), "drawn": N_UPPER},
        ],
        "structure_of_the_draw": structure(drawn),
        "roots": [
            {
                "root": root,
                "occurrences": morphology[root]["count"],
                "stratum": "20-99 occurrences" if root in lower_set
                           else "100+ occurrences",
            }
            for root in drawn
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="replay the draw against the file; write nothing")
    args = parser.parse_args()

    lower_rest, upper_rest, drawn = replay()

    if args.check:
        on_file = tuple(e["root"] for e in loaders.islambouli_witness_set()["roots"])
        ok = on_file == drawn
        print(f"frame {len(lower_rest)} + {len(upper_rest)}, seed {SEED}: "
              + ("the file reproduces exactly" if ok else "the file DOES NOT reproduce"))
        return 0 if ok else 1

    if ISLAMBOULI_WITNESS_SET_JSON.exists():
        print(f"{ISLAMBOULI_WITNESS_SET_JSON.relative_to(ROOT)} exists. The holdout "
              "is drawn once and never re-drawn; use --check to replay it.")
        return 1

    doc = document(lower_rest, upper_rest, drawn)
    ISLAMBOULI_WITNESS_SET_JSON.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"drew {len(drawn)} roots from {len(lower_rest)} + {len(upper_rest)} "
          f"with seed {SEED}; wrote {ISLAMBOULI_WITNESS_SET_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
