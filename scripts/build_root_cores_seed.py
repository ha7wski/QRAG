#!/usr/bin/env python3
"""
build_root_cores_seed.py — OFFLINE seeder for `data/references/root_cores.json`.

Turns the cited aṣl of `data/references/maqayis_asl.csv` into the mechanical half
of a root's semantic core: the canonical key, Ibn Fāris' own words in `verbatim`,
the source and the edition. `gloss`, `axes` and `polarity` are the CURATOR's half
and are left blank — `axes: []`, `polarity: null` — because they are readings of
the citation, and this script has no way to read. The validator refuses a
half-curated entry, so a seeded file cannot ship as a finished one.

Two rules make this script safe to re-run, and both are load-bearing:

  * **Keys are canonical, never folded.** The Maqāyīs CSV is indexed on the
    hamza-safe `normalize_root` fold; QAC roots are stored in their exact,
    hamza-bearing spelling (139 of the 1656 carry a hamza). Folding is how a row
    is FOUND, never how a key is stored (design D6). A folded key matches ~0
    hamzated roots and degrades to «no core», which is indistinguishable from a
    root nobody has curated yet.
  * **Curation is never overwritten.** An existing root keeps its entry byte for
    byte; only absent roots are added. That is why `root_cores.json` is recorded
    in `quran_data/manifest.py` as NOT regenerable even though it names a
    producer: the script reproduces the seed, never the file.

Roots whose Maqāyīs row is `no_asl` or `parse_uncertain` are SKIPPED. A root Ibn
Fāris gives no aṣl for gets no core: inventing one would put his name on a
sentence he did not write, and the core is what every letter of that root is then
selected against.

Usage:
    python scripts/build_root_cores_seed.py            # DRY RUN — reports, writes nothing
    python scripts/build_root_cores_seed.py --dry-run  # the same, said out loud
    python scripts/build_root_cores_seed.py --write    # apply: add the missing entries

Dry run is the default on purpose: the target is a hand-curated reference, and a
script that rewrites one by being invoked with no argument is the accident this
ordering removes.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arabic_text import normalize_root  # noqa: E402
from quran_data import loaders  # noqa: E402
from quran_data.paths import ROOT_CORES_JSON, SEMANTIC_AXES_JSON  # noqa: E402

# Sentinel joining several aṣl of one root inside a single `asl_text` cell (must
# match `scripts/build_maqayis_dataset.py::ASL_DELIM`). Never occurs in Arabic
# prose, so splitting on it is safe.
ASL_DELIM = " ||| "

# `maqayis_asl.csv`'s own `source` cell is a provenance TAG for the digital text
# (`maqayis_openiti`), not a citation. A core's `source` is displayed beside the
# reading as one, so it names the work; `edition` carries the row's edition tag
# verbatim. This matches the five curated entries already in the file.
SOURCE_LABEL = "ابن فارس، معجم مقاييس اللغة"

SKIP_STATUSES = ("no_asl", "parse_uncertain")

# Used only when the file does not exist yet; an existing `meta` is carried
# forward untouched.
#
# NOTHING DERIVABLE GOES IN HERE — no root count, no core count, no coverage
# share. `meta` is written once and the file grows underneath it, so a count
# stored here is a number that silently stops being true on the first `--write`
# (a block claiming `curated_roots: 5` over 1290 entries). Every such figure is
# recomputed by `scripts/validate_lisan_datasets.py`, which prints them on every
# run and never reads this block.
SEED_META = {
    "name": "root_cores",
    "version": "1.0.0",
    "description": (
        "Attested semantic core(s) per root, from Ibn Fāris, Muʿjam Maqāyīs "
        "al-Lugha. Keys are the CANONICAL QAC root spelling, never the folded "
        "Maqāyīs key. `verbatim` is byte-identical to its maqayis_asl.csv "
        "segment; `gloss`, `axes` and `polarity` are curated by hand."
    ),
    "axis_vocabulary": str(SEMANTIC_AXES_JSON.relative_to(ROOT)),
}


def _geminate_variants(root: str) -> list[str]:
    """Orthographic bridges between QAC's doubled geminate roots and Maqāyīs'
    contracted spelling: `اب` ↔ `ابب`. Empty for non-geminate shapes.

    Copied from `linguistics/madar/maqayis_store.py::_geminate_variants` rather
    than imported, so a build script does not drag a request-path package in.
    The two must agree: a row the store can reach but the seeder cannot would be
    a root that silently never gets a core.
    """
    out: list[str] = []
    if len(root) == 2:                            # اب → ابب
        out.append(root + root[-1])
    elif len(root) == 3 and root[1] == root[2]:   # ابب → اب
        out.append(root[:2])
    return out


def _find_row(root_key: str, maqayis: dict[str, dict]) -> dict | None:
    """The Maqāyīs row for a canonical QAC root key — folding to FIND it only."""
    folded = normalize_root(root_key)
    row = maqayis.get(folded)
    if row is not None:
        return row
    for cand in _geminate_variants(folded):
        row = maqayis.get(cand)
        if row is not None:
            return row
    return None


def _cores_from_row(row: dict) -> list[dict]:
    """One core per aṣl segment, in the CSV's order.

    Order is the dataset's contract: the validator pairs core #i with segment #i,
    and ظلم's two aṣl («خلاف الضياء والنور», «وضع الشيء غير موضعه تعديا») are two
    separate readings that must never be merged or reordered.
    """
    segments = [s for s in (row.get("asl_text") or "").split(ASL_DELIM) if s.strip()]
    return [
        {
            "gloss": "",              # curated: a short Arabic label for the aṣl
            "verbatim": seg,          # Ibn Fāris' words, byte-identical to the CSV
            "axes": [],               # curated: ids from semantic_axes.json
            "polarity": None,         # curated: positive | negative | neutral
            "source": SOURCE_LABEL,
            "edition": row.get("edition", ""),
        }
        for seg in segments
    ]


def _existing_document() -> dict:
    """The current `root_cores.json`, or a fresh shell when it does not exist.

    Absence is decided by the LOADER raising, not by a `.exists()` test of our
    own: two ways of asking whether the file is there is one way too many, and a
    pre-check that answers "no" while the loader would have answered "yes" turns
    this script from additive into destructive.
    """
    try:
        doc = loaders.root_cores()
    except loaders.DatasetMissing:
        return {"meta": dict(SEED_META), "roots": {}}
    # Copied, not aliased: the loader caches its object for the whole process and
    # this function's caller adds keys to `roots`.
    return {
        "meta": dict(doc.get("meta", {})),
        "roots": dict(doc.get("roots", {})),
    }


@dataclass(frozen=True)
class SeedPlan:
    """What a run would do, computed without touching disk.

    `document` already has the additions merged in; `added` maps each new root
    key to its cores; `preserved` lists the roots left exactly as curated;
    `orphans` names keys on file that are NOT QAC roots; `skipped` counts the
    roots that got no entry, by reason. Every QAC root lands in exactly one of
    `added` / `preserved` / `skipped`.
    """

    document: dict
    added: dict[str, list[dict]]
    preserved: list[str]
    orphans: list[str]
    skipped: Counter


def build_seed() -> SeedPlan:
    """Plan the seed: merge the missing entries into the document, in memory."""
    root_keys = sorted(loaders.morphology())        # sorted: a deterministic diff
    maqayis = {r["root_normalized"]: r for r in loaders.maqayis_asl()}
    document = _existing_document()
    roots: dict = document["roots"]

    added: dict[str, list[dict]] = {}
    preserved: list[str] = []
    skipped: Counter = Counter()

    # A key already on file that is not a QAC root — a folded spelling, a typo —
    # is touched by no branch of the loop below: it is neither added, preserved
    # nor skipped, so it would ride into the merged document without appearing
    # anywhere in this report. The validator does refuse it downstream, but a
    # report that cannot see it is how it would get written in the first place.
    canonical = set(root_keys)
    orphans = [k for k in roots if k not in canonical]

    for key in root_keys:
        if key in roots:
            # Already on file. Left byte for byte: its axes and polarity may be a
            # curator's, and a core count that has drifted from the CSV is a
            # finding for the validator to report, never a silent rewrite here.
            preserved.append(key)
            continue
        row = _find_row(key, maqayis)
        if row is None:
            skipped["no Maqāyīs row for the root"] += 1
            continue
        status = row.get("asl_status", "")
        if status in SKIP_STATUSES:
            skipped[f"Maqāyīs row is {status}"] += 1
            continue
        cores = _cores_from_row(row)
        if not cores:
            # has_asl with an empty cell: defensive, and worth counting rather
            # than emitting a root whose core carries no citation at all.
            skipped["Maqāyīs row carries no aṣl text"] += 1
            continue
        added[key] = cores
        roots[key] = cores

    return SeedPlan(document=document, added=added, preserved=preserved,
                    orphans=orphans, skipped=skipped)


def write(document: dict) -> None:
    """Overwrite `root_cores.json` with the merged document (2-space, UTF-8)."""
    ROOT_CORES_JSON.parent.mkdir(parents=True, exist_ok=True)
    ROOT_CORES_JSON.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def report(plan: SeedPlan, seen: int, applied: bool) -> None:
    print("=" * 64)
    print("ROOT CORES SEED — " + ("applied" if applied else "DRY RUN, nothing written"))
    print("=" * 64)
    print(f"  target            : {ROOT_CORES_JSON.relative_to(ROOT)}")
    print(f"  QAC roots seen    : {seen}")
    print(f"  entries added     : {len(plan.added)} "
          f"({sum(len(v) for v in plan.added.values())} cores, "
          "axes/polarity left blank)")
    print(f"  entries preserved : {len(plan.preserved)} (curation untouched)")
    if plan.preserved:
        print(f"    {'، '.join(plan.preserved[:10])}"
              + (" …" if len(plan.preserved) > 10 else ""))
    print(f"  roots skipped     : {sum(plan.skipped.values())}")
    for reason, count in sorted(plan.skipped.items(), key=lambda kv: -kv[1]):
        print(f"    {count:>5}  {reason}")
    if plan.orphans:
        print(f"  ORPHAN keys       : {len(plan.orphans)} already on file and NOT a "
              "canonical QAC root key")
        print(f"    {'، '.join(plan.orphans[:10])}"
              + (" …" if len(plan.orphans) > 10 else ""))
        print("    carried forward untouched; the validator refuses them — most "
              "likely a folded spelling")
    if not applied:
        print("\n  re-run with --write to apply. Seeded entries have empty `axes` "
              "and null `polarity`,\n  which the validator refuses — a seeded file "
              "is a curation worklist, not a shippable one.")
    print("=" * 64)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Seed root_cores.json from maqayis_asl.csv (offline, "
                    "non-destructive: curated entries are never overwritten).")
    ap.add_argument("--write", action="store_true",
                    help="apply the additions (default is a dry run)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change and write nothing (the default)")
    args = ap.parse_args()

    plan = build_seed()
    # `--dry-run` wins over `--write`, so the safe flag can never be cancelled by
    # a stale one left in a shell history.
    applied = args.write and not args.dry_run
    if applied:
        write(plan.document)
    # Every QAC root lands in exactly one bucket, so the three add back up to the
    # number of roots iterated (orphans are keys on file, not QAC roots).
    seen = len(plan.added) + len(plan.preserved) + sum(plan.skipped.values())
    report(plan, seen=seen, applied=applied)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
