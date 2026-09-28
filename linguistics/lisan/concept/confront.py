"""
confront.py — the ONE module allowed to read the aṣl, and it only ever REPORTS.

Everything else under `linguistics/lisan/concept/` is blind by construction: the
مفهوم is composed from the tajwīd description of a root's letters and from
nothing else, and `tests/test_import_direction.py` enforces that with an import
boundary rather than with a protocol anybody has to remember. This module is that
rule's single exemption — written into the test under `CONFRONTATION_MODULE`
before the file existed, so the boundary already knew where it ended.

**The direction is the whole architecture.** `confront.py` imports the concept
RESULT; `compose.py` never imports `confront.py`, and neither does the package
`__init__` — a concept module reaching the aṣl *through the module allowed to read
it* is still a concept module reaching the aṣl, and the test reports it as one.

**It compares and reports only. There is no path here that re-ranks, re-selects
or re-phrases a concept, and there is no flag that adds one.** A guard that
re-ranked until the concept and the aṣl agreed would make the tool incapable of
ever disagreeing with Ibn Fāris — which is the entire point of inverting the
pipeline. The core-first engine one directory up already demonstrates the failure
in its benign form: there, the aṣl SELECTS the sense, so the output cannot carry
information the core did not already carry, and agreement is guaranteed rather
than earned. Here the aṣl arrives after the answer, and a disagreement is a
RESULT: it is recorded, published, and is never a reason to add a table row,
reglossed a primitive or re-order anything (§D9 step 4). The table moves only
through a lock version justified by a feature-level authority.

`compose(root)` is called exactly ONCE per confrontation and its return value is
passed through untouched. `tests/test_concept_confrontation.py` asserts that
statically — by reading this source — because a re-ranking door gated behind an
env flag is dormant during a behavioural test and returns exactly what the honest
path returns. The test would pass and the door would still be in the file.

**No partial credit, at either level.** A use is `covered` or it is not; a root
`covers_all` only when every one of its frozen uses is covered. The dangerous
default is the empty one: a root with no `uses[]` on file has `verdict ==
"not_recorded"`, never `covers_all`, because `all([])` is `True` and a vacuous
pass would silently inflate `k / 40` with roots nobody has judged.

**A root with no curated core says WHOSE silence that is.** `not_curated` (Ibn
Fāris states an aṣl, the project has not transcribed it — 1290 QAC roots),
`not_recorded` (no Maqāyīs row, or one the parser could not read — 365) and
`no_asl_in_source` (his entry itself formulates none — 1, `أصل`). The vocabulary
is imported from the core-first engine rather than restated, so the two readings
cannot drift apart; the asymmetry is its rule, not this module's invention: the
project reports its OWN gap freely and reports his silence only where the dataset
positively records it. One sentence for all three had the page telling محراب that
Maqāyīs holds no aṣl for حرب, where Ibn Fāris gives three.

Note what `cores` is NOT: the uncurated Maqāyīs `asl_text` is never lifted into
it. An aṣl read straight out of the CSV is an uncurated core wearing a curated
one's clothes — exactly what `root_core_store._is_curated` refuses — and
`core_status` exists so the gap can be reported instead of filled.

**`counts_toward_k` is a published exclusion, not a silence.** `ضرب` is
confronted, judged and printed like any other root and contributes to neither
half of the metric: §D5's composition rule was verified against it, so coverage
measured on it proves nothing — the rule and the case were checked against each
other. Roots off the witness set are excluded for the mirror reason: `k` is
measured on a set drawn before the table was written, and a root added afterwards
is a root that could have been chosen for how it reads.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from linguistics.lisan.concept.compose import Concept, compose  # noqa: E402
from linguistics.lisan.lisan_service import (  # noqa: E402
    CORE_STATUS_NOT_CURATED,
    CORE_STATUS_NOT_RECORDED,
    CORE_STATUS_NO_ASL_IN_SOURCE,
)
from linguistics.lisan.root_core_store import RootCoreStore  # noqa: E402
from linguistics.madar.maqayis_store import MaqayisStore  # noqa: E402

# The use record, the verdicts and `counts_toward_k` live in
# `linguistics/lisan/harness/verdicts.py`, shared with every later letter table
# so the two measurements are judged by one piece of code. Re-exported here under
# the names this module has always published.
from linguistics.lisan.harness.verdicts import (  # noqa: E402,F401
    DEVELOPMENT_CASE,
    USE_COVERED,
    USE_NOT_COVERED,
    USE_NOT_JUDGED,
    VERDICT_COVERS_ALL,
    VERDICT_NOT_RECORDED,
    VERDICT_PARTIAL,
    AttestedUse,
    _use,
    counts_toward_k,
    read_uses,
    records,
    verdict_for,
    witness_roots,
)


@dataclass(frozen=True)
class Confrontation:
    """A root's concept set beside what is attested for it. A report, not a step.

    Nothing downstream of this object may feed back into `concept`: it is the
    value `compose` returned, carried through unmodified, and that is the only
    reason the comparison means anything.
    """

    root: str
    concept: Concept
    cores: tuple[dict, ...]         # the curated aṣl, `verbatim` included
    core_status: str                # "" when cores exist; else the recorded silence
    occurrences: int                # morphology.json `count`
    verses: tuple[str, ...]         # the root's verse refs, dataset order
    uses: tuple[AttestedUse, ...]   # empty when not yet frozen
    verdict: str                    # covers_all | partial | not_recorded
    uses_frozen_at: str             # "" when not recorded
    concept_recorded_at: str        # "" when not recorded
    in_witness_set: bool
    counts_toward_k: bool


@dataclass(frozen=True)
class Sources:
    """The read-only inputs a confrontation reads, as one injectable value.

    The same pattern `scripts/validate_concept_datasets.py::Datasets` uses, for
    the same reason it gives: a test hands in a deliberately shaped in-memory
    copy and the rules it exercises are the rules production runs. A rule tested
    against a fixture it does not share with production is a rule tested twice
    and enforced once.

    `confront(root)` with no `sources` loads the shipped files, so the published
    contract stays the one-argument call.
    """

    cores: RootCoreStore
    maqayis: MaqayisStore
    attestation: dict
    morphology: dict
    witness: frozenset[str]

    @classmethod
    def load(cls) -> "Sources":
        """Read the shipped datasets through the registry's cached loaders."""
        return cls(
            cores=RootCoreStore(),
            maqayis=MaqayisStore(),
            attestation=loaders.concept_attestation(),
            morphology=loaders.morphology(),
            witness=witness_roots(loaders.concept_witness_set()),
        )


def core_status(entry, cores: tuple[dict, ...]) -> str:
    """Whose silence it is when a root shows no curated core — or "" when it does.

    Mirrors `linguistics.lisan.lisan_service.LisanService.core_status`, and
    `tests/test_concept_confrontation.py` pins the two to the same answer on a
    root of every kind. The rule is asymmetric on purpose and the asymmetry is
    the point: `parse_uncertain` falls to `not_recorded` rather than
    `not_curated`, because we know his entry exists but not that it yields an
    aṣl, and claiming «he states one» would be as much of an invention as
    claiming he states none. Absence of evidence lands on the project's side.
    """
    if cores:
        return ""
    if entry is None:
        return CORE_STATUS_NOT_RECORDED
    if entry.asl_status == "has_asl":
        return CORE_STATUS_NOT_CURATED
    if entry.asl_status == "no_asl":
        return CORE_STATUS_NO_ASL_IN_SOURCE
    return CORE_STATUS_NOT_RECORDED


def confront(root: str, sources: Sources | None = None) -> Confrontation:
    """Set `root`'s composed concept beside what is attested for it, and report.

    The concept is composed ONCE, here, and is carried into the result exactly as
    it came back. Nothing below this line inspects the aṢl and then touches it.
    """
    root = (root or "").strip()
    src = sources or Sources.load()

    concept = compose(root)

    cores = tuple(src.cores.lookup(root))
    entry = src.maqayis.lookup(root)
    morph = src.morphology.get(root) or {}
    record = records(src.attestation).get(root) or {}
    uses = read_uses(record)
    in_witness = root in src.witness

    return Confrontation(
        root=root,
        concept=concept,
        cores=cores,
        core_status=core_status(entry, cores),
        occurrences=int(morph.get("count") or 0),
        verses=tuple(morph.get("verses") or ()),
        uses=uses,
        verdict=verdict_for(uses),
        uses_frozen_at=str(record.get("uses_frozen_at") or "").strip(),
        concept_recorded_at=str(record.get("concept_recorded_at") or "").strip(),
        in_witness_set=in_witness,
        counts_toward_k=counts_toward_k(root, in_witness),
    )


if __name__ == "__main__":
    for probe in (DEVELOPMENT_CASE, "خير", "قوم", "أصل", "برزخ"):
        report = confront(probe)
        print(
            f"{report.root:<6} verdict={report.verdict:<13} "
            f"core_status={report.core_status or '(curated)':<17} "
            f"cores={len(report.cores)} occurrences={report.occurrences:<4} "
            f"witness={report.in_witness_set} counts_toward_k={report.counts_toward_k}"
        )
        if report.concept.refused:
            print(f"       REFUSED [{report.concept.refusal_code}]")
        else:
            print(f"       {' · '.join(report.concept.realised_primitives)}")
        for use in report.uses:
            print(f"       {use.verdict:<12} {use.verse:<8} {use.gloss}")
