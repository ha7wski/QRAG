"""
record_concept_verdicts.py — §D9 steps 2 and 3, and nothing else.

Step 1 (freeze the `uses[]`) is already committed: `concept_attestation.json`
carries all 40 witness roots with every verdict `not_judged` and every
`concept_recorded_at` empty. This script does the two steps after it.

    python scripts/record_concept_verdicts.py worksheet
        Composes every witness root — plus `ضرب` — and prints each one's reading
        beside its frozen uses. Writes NOTHING. This is what the curator judges
        against, and it is a separate mode precisely so that generating and
        judging are two acts rather than one function with an opinion.

    python scripts/record_concept_verdicts.py record --verdicts <file.json>
        Writes the concept block, stamps `concept_recorded_at`, and applies the
        curator's verdicts. Refuses to write a root unless EVERY one of its uses
        carries a verdict, because a root generated and half-judged reaches
        neither `covers_all` nor a published miss — it silently leaves the
        denominator.

    python scripts/record_concept_verdicts.py collisions
        Derives `collision_with` per root: whether another QAC root with a
        divergent aṣl composes to the same realised primitives. A mechanical fact
        about the table, run AFTER the verdicts exist so it cannot shape them.

**This script holds the sanctioned exemption to `witness_guard`.** It is the
recording path §D9 step 2 names, and it composes all 40 by definition. It does
not strictly need the exemption — the guard is scoped to test runs and this is
not one — and it takes it anyway, explicitly, so that the one legitimate caller
is greppable and a test covering this script can borrow the same door instead of
inventing a second one.

**It never judges.** There is no heuristic here that decides `covered`, no
similarity score and no string overlap. The criterion in §D9 is a criterion for a
reader, and a function that approximated it would be the tool grading its own
homework — with the added defect that the approximation would be tuned, by
whoever wrote it, against the answers it produced.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from quran_data.paths import CONCEPT_ATTESTATION_JSON  # noqa: E402
from linguistics.lisan.concept import witness_guard  # noqa: E402
from linguistics.lisan.concept.compose import compose  # noqa: E402
from linguistics.lisan.harness.verdicts import (  # noqa: E402
    DEVELOPMENT_CASE,
    MISS_CLASSES,
    USE_COVERED,
    USE_NOT_COVERED,
)


def _witness_roots() -> list[str]:
    return [e["root"] for e in loaders.concept_witness_set()["roots"]]


def _read() -> dict:
    return json.loads(CONCEPT_ATTESTATION_JSON.read_text(encoding="utf-8"))


def _write(doc: dict) -> None:
    CONCEPT_ATTESTATION_JSON.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _concept_block(root: str) -> dict:
    """The reading, stored exactly as `compose()` produced it.

    `realised` is kept per position AND flat. The flat chain is what the metric is
    measured on and what the probe compares; the per-position split is what a
    reader needs to check the positional rule without re-running anything. They
    are two views of one tuple, written together so they cannot disagree.
    """
    concept = compose(root)
    return {
        "sentence": concept.sentence,
        "sentence_source": concept.sentence_source,
        "realised_primitives": list(concept.realised_primitives),
        "positions": [
            {
                "position": reading.position,
                "letter": reading.letter,
                "makhraj_ar": reading.makhraj_ar,
                "realised": [hit.primitive for hit in reading.realised],
                "carried": [hit.primitive for hit in reading.carried],
                "silent": reading.silent,
            }
            for reading in concept.positions
        ],
        "partial": concept.partial,
        "silent_letters": list(concept.silent_letters),
        "refused": concept.refused,
        "refusal_code": concept.refusal_code,
        "lock_version": concept.lock_version,
    }


# ── worksheet: generate and show, decide nothing ─────────────────────────────

def cmd_worksheet(_args) -> int:
    doc = _read()
    records = doc["roots"]
    roots = _witness_roots()
    if DEVELOPMENT_CASE in records:
        roots = [*roots, DEVELOPMENT_CASE]

    with witness_guard.recording_the_witness_set():
        for root in roots:
            record = records.get(root) or {}
            block = _concept_block(root)
            print(f"### {root}   [{'witness' if root != DEVELOPMENT_CASE else 'development case — uncounted'}]")
            for position in block["positions"]:
                print(f"    {position['position']:<9} {position['letter']}  "
                      f"{position['makhraj_ar']:<12} "
                      f"{' · '.join(position['realised'])}"
                      f"   (carried: {' · '.join(position['carried']) or '—'})")
            print(f"    مفهوم: {block['sentence']}")
            for index, use in enumerate(record.get("uses") or []):
                print(f"    [{index}] {use['verse']:<8} {use['gloss']}")
            print()
    return 0


# ── record: apply the curator's judgement ────────────────────────────────────

def cmd_record(args) -> int:
    verdicts = json.loads(Path(args.verdicts).read_text(encoding="utf-8"))
    doc = _read()
    records = doc["roots"]
    stamp = datetime.now().replace(microsecond=0).isoformat()

    errors: list[str] = []
    for root, judged in verdicts.items():
        record = records.get(root)
        if record is None:
            errors.append(f"«{root}» has no frozen record; its uses[] must be "
                          f"committed before its concept is generated")
            continue
        uses = record.get("uses") or []
        if len(judged) != len(uses):
            errors.append(f"«{root}»: {len(judged)} verdicts for {len(uses)} uses")
            continue
        for index, entry in enumerate(judged):
            verdict = (entry.get("verdict") or "").strip()
            reason = (entry.get("reason") or "").strip()
            if verdict not in (USE_COVERED, USE_NOT_COVERED):
                errors.append(f"«{root}» uses[{index}]: verdict «{verdict}» is not "
                              f"one of {USE_COVERED}/{USE_NOT_COVERED}")
            if verdict == USE_NOT_COVERED:
                if not reason:
                    errors.append(f"«{root}» uses[{index}]: a miss carries a reason")
                elif reason.split(":", 1)[0].split()[0] not in MISS_CLASSES:
                    errors.append(
                        f"«{root}» uses[{index}]: the reason must open with one of "
                        f"{', '.join(MISS_CLASSES)} — an unclassified miss cannot "
                        f"be counted later"
                    )
            if verdict == USE_COVERED and reason and reason.split()[0] in MISS_CLASSES:
                errors.append(f"«{root}» uses[{index}]: a covered use carries a "
                              f"miss class in its reason")

    if errors:
        print("REFUSED — nothing written:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    with witness_guard.recording_the_witness_set():
        for root, judged in verdicts.items():
            record = records[root]
            record["concept"] = _concept_block(root)
            record["concept_recorded_at"] = stamp
            for index, entry in enumerate(judged):
                record["uses"][index]["verdict"] = entry["verdict"].strip()
                record["uses"][index]["reason"] = (entry.get("reason") or "").strip()

    _write(doc)
    covered = sum(
        1 for record in records.values()
        if record.get("concept_recorded_at")
        and all(u["verdict"] == USE_COVERED for u in record["uses"])
    )
    print(f"wrote {len(verdicts)} root(s) at {stamp}; {covered} cover every use")
    return 0


# ── collisions: a mechanical fact, derived after the judging ─────────────────

def cmd_collisions(_args) -> int:
    """Which recorded roots share their realised primitives with another root.

    The probe's own `identical` criterion — the ordered chain of realised
    primitives, compared whole — swept over every triliteral QAC root rather than
    over a chosen sample, so the answer is not a function of what anybody picked
    to compare. Divergence of aṣl is read from the Maqāyīs store and reported
    verbatim; a colliding pair whose aṣl AGREE is recorded as a collision that
    costs nothing, because two roots meaning the same thing may legitimately read
    the same.
    """
    from linguistics.madar.maqayis_store import MaqayisStore

    doc = _read()
    records = doc["roots"]
    morphology = loaders.morphology()
    maqayis = MaqayisStore()

    with witness_guard.recording_the_witness_set():
        chains: dict[tuple[str, ...], list[str]] = {}
        for root in morphology:
            if len(root) != 3:
                continue
            concept = compose(root)
            if concept.refused or concept.partial:
                continue
            chains.setdefault(concept.realised_primitives, []).append(root)

        for root, record in records.items():
            block = record.get("concept")
            if not block:
                continue
            chain = tuple(block["realised_primitives"])
            others = [r for r in chains.get(chain, ()) if r != root]
            if not others:
                record["collision_with"] = []
                continue
            mine = _asl_of(maqayis, root)
            record["collision_with"] = [
                {
                    "root": other,
                    "asl": _asl_of(maqayis, other),
                    "asl_divergent": bool(mine) and bool(_asl_of(maqayis, other))
                    and not (set(mine) & set(_asl_of(maqayis, other))),
                }
                for other in sorted(others)
            ]

    _write(doc)
    colliding = [r for r, rec in records.items() if rec.get("collision_with")]
    print(f"collision_with derived for {len(records)} recorded root(s); "
          f"{len(colliding)} collide: {'، '.join(sorted(colliding)) or '—'}")
    return 0


def _asl_of(maqayis, root: str) -> list[str]:
    entry = maqayis.lookup(root)
    if entry is None or getattr(entry, "asl_status", "") != "has_asl":
        return []
    text = getattr(entry, "asl_text", "") or ""
    return [text] if text else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("worksheet").set_defaults(run=cmd_worksheet)
    record = sub.add_parser("record")
    record.add_argument("--verdicts", required=True)
    record.set_defaults(run=cmd_record)
    sub.add_parser("collisions").set_defaults(run=cmd_collisions)
    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
