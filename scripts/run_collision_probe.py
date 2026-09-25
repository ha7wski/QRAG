#!/usr/bin/env python3
"""run_collision_probe.py — the §D13 gate, run once, before any curation.

The primitive table maps 28 letters onto 18 profiles, so ten letters have no
profile of their own: `ب`/`ج`/`د` are strictly indistinguishable to it, as are
`ث`/`ح`/`ف`/`ه`, `ط`/`ق`, `ظ`/`غ`, `م`/`ن`, `و`/`ي` and `ت`/`ك`. Whether that is
an acceptable cost or the method's dominant failure mode decides whether
curating 40 witness roots is worth doing at all — so it is settled FIRST, on
real minimal pairs, against aṣl already on disk. No curated dataset is needed
and none is read: the probe compares REALISED PRIMITIVES, so the sentence
template, the LLM pass, the route and the page are all unnecessary to it.

**The ordering is the whole protocol.** The qualification table — which
comparisons the probe is entitled to make, and the aṣl sets that entitle them —
is written by hand and committed BEFORE a single concept is composed. This
script refuses to run without it, and records the sha256 of the qualification
block it ran against, so a qualification quietly rewritten after the fact stops
matching its own record. Publishing the table first fixes the test's
denominator before anyone knows its numerator.

The script reports. It does not decide anything by itself and it changes no
dataset: a confirmed collision is a result to act on in a separate, deliberate
step, never something a runner silently repairs.

    python scripts/run_collision_probe.py            # report only
    python scripts/run_collision_probe.py --write    # also append the probe block
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linguistics.lisan.concept.compose import REALISED_PER_POSITION, compose  # noqa: E402
from quran_data import loaders  # noqa: E402
from quran_data.paths import (  # noqa: E402
    CONCEPT_COLLISION_PROBE_JSON,
    PHYSICAL_PRIMITIVES_CSV,
)

# The three outcomes, fixed before the probe ran. `order-distinct` is a PARTIAL
# COLLISION and is reported as one: two concepts built from one set of
# primitives shuffled are separated by the composition rule alone, not by
# anything the table knows about their letters. Filing it with `distinct` would
# report a near-miss as a pass.
IDENTICAL = "identical"
ORDER_DISTINCT = "order-distinct"
DISTINCT = "distinct"


def _qualification_digest(qualification: dict) -> str:
    """sha256 of the qualification block, serialised canonically.

    Canonical (sorted keys, no spare whitespace) so the digest tracks the
    block's CONTENT rather than the indentation the file happens to carry.
    """
    payload = json.dumps(qualification, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _realised_by_position(root: str) -> tuple[tuple[str, ...], ...]:
    """The realised primitives of each position, in position and rarity order."""
    concept = compose(root)
    if concept.refused:
        raise SystemExit(
            f"{root}: the composer refused it ({concept.refusal_code}). A probe root "
            f"that cannot be composed is a broken sample, not a result — fix the "
            f"sample declaration in {CONCEPT_COLLISION_PROBE_JSON.name}."
        )
    return tuple(tuple(hit.primitive for hit in p.realised) for p in concept.positions)


def _compare(left: tuple[tuple[str, ...], ...], right: tuple[tuple[str, ...], ...]) -> str:
    if left == right:
        return IDENTICAL
    flat_left = Counter(p for position in left for p in position)
    flat_right = Counter(p for position in right for p in position)
    return ORDER_DISTINCT if flat_left == flat_right else DISTINCT


def run() -> tuple[dict, int]:
    doc = loaders.concept_collision_probe()
    qualification = doc.get("qualification")
    if not qualification:
        raise SystemExit(
            f"{CONCEPT_COLLISION_PROBE_JSON.name} carries no `qualification` block. "
            f"The probe does not run before its denominator is fixed."
        )

    readings: dict[str, dict] = {}
    comparisons: list[dict] = []
    for klass in qualification["classes"]:
        for root_entry in klass["roots"]:
            root = root_entry["root"]
            if root in readings:
                continue
            by_position = _realised_by_position(root)
            readings[root] = {
                "root": root,
                "occurrences": root_entry["occurrences"],
                "realised_by_position": [list(p) for p in by_position],
                "asl_senses": root_entry["asl_senses"],
            }
        for comparison in klass["comparisons"]:
            left, right = comparison["pair"]
            outcome = _compare(_realised_by_position(left), _realised_by_position(right))
            comparisons.append({
                "class": klass["class"],
                "pair": [left, right],
                "qualifying": comparison["qualifying"],
                "asl_divergent": comparison["qualifying"],
                "outcome": outcome,
                "partial_collision": outcome == ORDER_DISTINCT,
                "collision_confirmed": outcome == IDENTICAL and comparison["qualifying"],
            })

    counted = [c for c in comparisons if c["qualifying"]]
    confirmed = [c for c in counted if c["collision_confirmed"]]
    partial = [c for c in counted if c["partial_collision"]]

    if confirmed:
        verdict = "collision-confirmed"
        consequence = (
            "One `identical` on an aṣl-divergent pair ends the probe. Do NOT widen. "
            "Mapping the five classical مخرج zones becomes v1.0.0 of the table rather "
            "than a later lock bump, and tasks 1–3 are redone before anything else proceeds."
        )
    elif all(c["outcome"] == DISTINCT for c in counted):
        verdict = "all-classes-discriminate"
        consequence = (
            "A clean sweep. Only this licenses extending the probe to ط/ق, ث/ح/ف/ه and م/ن "
            "before any conclusion is drawn. ظ/غ stays excluded in every case."
        )
    else:
        verdict = "partial-collision"
        consequence = (
            "No `identical`, but at least one `order-distinct`: the table does not collapse "
            "the pair outright, yet what separates the two concepts is the composition rule "
            "alone, not the letters. This is NOT a clean sweep, so the probe does not widen; "
            "it is reported as a partial collision and the decision is a reviewer's."
        )

    probe = {
        "ran_on": date.today().isoformat(),
        "qualification_sha256": _qualification_digest(qualification),
        "table_lock_version": compose("ضرب").lock_version,
        # The lock VERSION does not identify the table: §D3's pre-declared fallback
        # replaced the ṣifāt-only draft in place, so two runs can both report v1.0.0
        # over different bytes. The digest is what tells them apart.
        "table_sha256": hashlib.sha256(PHYSICAL_PRIMITIVES_CSV.read_bytes()).hexdigest(),
        "realised_per_position": REALISED_PER_POSITION,
        "compared_on": f"realised primitives (top {REALISED_PER_POSITION} per position)",
        "size": {"roots": len(readings), "classes": len({c['class'] for c in comparisons}),
                 "qualifying_comparisons": len(counted),
                 "stated_as": f"{len(readings)} roots over {len({c['class'] for c in comparisons})} classes"},
        "readings": list(readings.values()),
        "comparisons": comparisons,
        "tally": {
            IDENTICAL: sum(1 for c in counted if c["outcome"] == IDENTICAL),
            ORDER_DISTINCT: len(partial),
            DISTINCT: sum(1 for c in counted if c["outcome"] == DISTINCT),
        },
        "verdict": verdict,
        "consequence": consequence,
        "widened": False,
    }
    return probe, (1 if confirmed else 0)


# ── the widening (§D13), licensed only by a clean sweep ──────────────────────
#
# The three mandated classes are a hand-curated sample with a hand-written
# qualification table. The widening is NOT, and the difference is deliberate:
# its sample is fixed by an ENUMERATION RULE rather than by selection —
#
#     every minimal pair, in the three remaining classes, whose two roots are
#     both real triliteral QAC keys and both carry a `has_asl` Maqāyīs row,
#     minus the roots already spent (the 7 probe roots, the 5 curated, ضرب).
#
# No sampling, no ranking, no truncation, no cut-off on occurrence count. That
# is what removes the «chosen by looking at the data» problem here: there is no
# choice left to make. The cost is that the aṣl-divergence verdicts for the
# pairs that come back `identical` are read AFTER their outcome, where the
# mandated probe committed its qualification first. The widening is therefore
# one notch weaker as evidence, it is labelled as such in the record, and every
# aṣl it rests on is published verbatim so a reader can redo the judgement.
#
# ظ/غ is excluded here as everywhere: its only real minimal pair runs through
# ظلم, already curated in root_cores.json and contaminated either way.
WIDENED_CLASSES = {"ط/ق": "طق", "ث/ح/ف/ه": "ثحفه", "م/ن": "من"}
SPENT_ROOTS = frozenset({"خبث", "خير", "رحم", "ظلم", "كفر", "ضرب",
                         "حرب", "حرج", "حرد", "تبر", "كبر", "كود", "كيد"})


def enumerate_widened_pairs() -> dict[str, list[tuple[str, str, str, str]]]:
    """Every qualifying-by-existence minimal pair, class by class.

    Deterministic and exhaustive: iterating `sorted(...)` and de-duplicating on
    the unordered pair means two runs enumerate the same list in the same order.
    """
    import itertools
    from arabic_text import normalize_root

    morphology = loaders.morphology()
    has_asl = {r["root_normalized"] for r in loaders.maqayis_asl()
               if r.get("asl_status") == "has_asl"}
    triliteral = {r for r in morphology if len(r) == 3}

    out: dict[str, list[tuple[str, str, str, str]]] = {}
    for label, letters in WIDENED_CLASSES.items():
        seen: set[tuple[str, str]] = set()
        pairs: list[tuple[str, str, str, str]] = []
        for left, right in itertools.combinations(letters, 2):
            for root in sorted(triliteral):
                for i, char in enumerate(root):
                    if char != left:
                        continue
                    other = root[:i] + right + root[i + 1:]
                    if other not in triliteral:
                        continue
                    if root in SPENT_ROOTS or other in SPENT_ROOTS:
                        continue
                    if normalize_root(root) not in has_asl or normalize_root(other) not in has_asl:
                        continue
                    key = tuple(sorted((root, other)))
                    if key in seen:
                        continue
                    seen.add(key)
                    pairs.append((root, other, left, right))
        out[label] = pairs
    return out


def run_widening() -> dict:
    """Sweep the three remaining classes and report every non-`distinct` outcome."""
    from collections import Counter

    morphology = loaders.morphology()
    maqayis = {r["root_normalized"]: r for r in loaders.maqayis_asl()}
    from arabic_text import normalize_root

    # Recorded aṣl-divergence verdicts, keyed on the unordered pair. They are
    # written by hand into the record and READ BACK here rather than recomputed,
    # for two reasons: a judgement over an aṣl set is not something a script can
    # derive, and a re-run that silently dropped them would erase the only thing
    # that turns an `identical` outcome into a counted collision.
    recorded: dict[tuple[str, str], dict] = {}
    try:
        for run in loaders.concept_collision_probe().get("probes", []):
            for klass in (run.get("widening") or {}).get("classes", []):
                for entry in klass.get("non_distinct", []):
                    if "asl_divergent" in entry:
                        recorded[tuple(sorted(entry["pair"]))] = entry
    except Exception:  # pragma: no cover - a first run has no record to read
        recorded = {}

    classes: list[dict] = []
    for label, pairs in enumerate_widened_pairs().items():
        tally: Counter[str] = Counter()
        flagged: list[dict] = []
        for left, right, la, lb in pairs:
            outcome = _compare(_realised_by_position(left), _realised_by_position(right))
            tally[outcome] += 1
            if outcome == DISTINCT:
                continue
            flagged_entry = {
                "pair": [left, right],
                "differing_letters": [la, lb],
                "occurrences": [morphology[left]["count"], morphology[right]["count"]],
                "outcome": outcome,
                "realised": [[list(p) for p in _realised_by_position(r)] for r in (left, right)],
                "asl_verbatim": {
                    r: maqayis[normalize_root(r)]["asl_text"].split(" ||| ") for r in (left, right)
                },
            }
            prior = recorded.get(tuple(sorted((left, right))))
            if prior:
                flagged_entry["asl_divergent"] = prior["asl_divergent"]
                flagged_entry["divergence_reason"] = prior["divergence_reason"]
                flagged_entry["collision_confirmed"] = (
                    prior["asl_divergent"] and outcome == IDENTICAL)
            else:
                flagged_entry["asl_divergent"] = None
                flagged_entry["divergence_reason"] = (
                    "NOT YET JUDGED — the aṣl are published above; the verdict is written into "
                    "the record by hand, never derived here.")
                flagged_entry["collision_confirmed"] = None
            flagged.append(flagged_entry)
        roots = {r for pair in pairs for r in pair[:2]}
        classes.append({
            "class": label, "pairs": len(pairs), "roots": len(roots),
            "tally": dict(tally), "non_distinct": flagged,
        })
    return {"sample_rule": (
                "every minimal pair in the class whose two roots are triliteral QAC keys carrying a "
                "has_asl Maqāyīs row, minus the 13 roots already spent. No sampling, no ranking, no "
                "truncation."),
            "evidential_status": (
                "ONE NOTCH WEAKER than the three mandated classes: the sample is fixed by an "
                "enumeration rule rather than by a committed qualification table, so the "
                "aṣl-divergence verdicts on the `identical` pairs were read after their outcome. "
                "Every aṣl is published verbatim above so the judgement can be redone."),
            "excluded": {"class": "ظ/غ", "why": "its only minimal pair runs through the curated ظلم"},
            "classes": classes}


def report(probe: dict) -> None:
    print("§D13 COLLISION PROBE")
    print(f"  size: {probe['size']['stated_as']} "
          f"({probe['size']['qualifying_comparisons']} qualifying comparisons; the three "
          f"ب/ج/د comparisons are correlated, sharing their roots)")
    print(f"  table lock: v{probe['table_lock_version']}")
    print()
    for reading in probe["readings"]:
        joined = "  |  ".join(" · ".join(p) for p in reading["realised_by_position"])
        print(f"  {reading['root']}  ({reading['occurrences']:>3} occ)   {joined}")
    print()
    for c in probe["comparisons"]:
        mark = {IDENTICAL: "COLLISION", ORDER_DISTINCT: "partial collision", DISTINCT: "distinct"}[c["outcome"]]
        print(f"  [{c['class']}] {c['pair'][0]} ~ {c['pair'][1]}: {c['outcome']}  ({mark})")
    print()
    print(f"  tally: {probe['tally']}")
    print(f"  VERDICT: {probe['verdict']}")
    print(f"  {probe['consequence']}")
    widening = probe.get("widening")
    if not widening:
        return
    print()
    print("  WIDENING — the three remaining classes, swept exhaustively")
    print(f"  sample rule: {widening['sample_rule']}")
    for klass in widening["classes"]:
        print(f"    [{klass['class']}] {klass['pairs']} pairs over {klass['roots']} roots "
              f"-> {klass['tally']}")
        for entry in klass["non_distinct"]:
            confirmed = entry.get("collision_confirmed")
            mark = ("COLLISION" if confirmed else
                    "not counted — aṣl not divergent" if confirmed is False else
                    "verdict not yet recorded")
            print(f"        {entry['outcome']}: {entry['pair'][0]} ~ {entry['pair'][1]} "
                  f"[{'/'.join(entry['differing_letters'])}]  ({mark})")
    summary = widening.get("summary")
    if summary:
        print(f"    tally: {summary['tally']} over {summary['pairs_swept']} pairs")
        print(f"    confirmed collisions: {summary['confirmed_collisions']}, "
              f"all on {summary['all_confined_to']}")
    print(f"    NOTE: {widening['evidential_status']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--widen", action="store_true",
                        help="sweep the three remaining classes (licensed only by a clean sweep)")
    parser.add_argument("--write", action="store_true",
                        help="append the probe block to the record (it is a report otherwise)")
    args = parser.parse_args()
    probe, status = run()
    if args.widen:
        if probe["verdict"] != "all-classes-discriminate":
            raise SystemExit(
                "Widening is licensed ONLY by a clean sweep of the three mandated classes. "
                f"This run's verdict is «{probe['verdict']}» — report it and stop."
            )
        probe["widening"] = run_widening()
        probe["widened"] = True
    report(probe)
    if args.write:
        doc = json.loads(CONCEPT_COLLISION_PROBE_JSON.read_text(encoding="utf-8"))
        # Runs ACCUMULATE. A run is never overwritten by the next: run 1 is the reason
        # the table was replaced, and deleting it would leave the replacement
        # unexplained — a v1.0.0 whose digest moved with nothing on file saying why.
        runs = doc.get("probes") or ([doc["probe"]] if doc.get("probe") else [])
        doc.pop("probe", None)
        probe["run"] = len(runs) + 1
        for earlier in runs:
            earlier.setdefault("run", runs.index(earlier) + 1)
        runs.append(probe)
        doc["probes"] = runs
        CONCEPT_COLLISION_PROBE_JSON.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n  written as run {probe['run']} to "
              f"{CONCEPT_COLLISION_PROBE_JSON.relative_to(ROOT)} "
              f"({len(runs)} run(s) on file; none overwritten)")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
