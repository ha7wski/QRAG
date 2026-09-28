"""
verdicts.py — the uses record, the verdicts and the strict metric gate.

This is the part of the harness that reads GLOSSED USES, so no composer may
import it (`tests/test_import_direction.py`). The confrontation modules and the
validators do.

Everything here is table-agnostic. The one thing that differs between the two
engines is how their record file NAMES things (the file, the timestamp field,
and the noun for what gets generated), and `RecordSpec` carries exactly that. The
closed engine's spec is `CLOSED_ENGINE`, and its messages are byte-identical to
the ones the validator printed before the extraction.

**No partial credit, at either level.** A use is `covered` or it is not; a root
`covers_all` only when every one of its frozen uses is covered. A root with no
`uses[]` on file is `not_recorded`, never `covers_all`, because `all([])` is
`True` and a vacuous pass would silently inflate `k`.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from linguistics.lisan.harness.draw import DEVELOPMENT_CASE

# What a single frozen use can be judged. `not_judged` is NOT a third outcome of
# the judgement: it is how a record without a verdict yet is read, so an unjudged
# use can never be mistaken for a covered one.
USE_COVERED = "covered"
USE_NOT_COVERED = "not_covered"
USE_NOT_JUDGED = "not_judged"

# A use is covered or it is not. There is no partial credit anywhere in this
# protocol, at the use level or at the root level.
USE_VERDICTS = (USE_COVERED, USE_NOT_COVERED)

# The verdict a use carries between the two moments the protocol separates: its
# `uses[]` are frozen and committed, and nothing has been generated yet.
VERDICT_NOT_JUDGED = USE_NOT_JUDGED

# A root's verdict.
VERDICT_COVERS_ALL = "covers_all"
VERDICT_PARTIAL = "partial"
VERDICT_NOT_RECORDED = "not_recorded"

# Every miss names its class as the FIRST word of its reason. There are four, and
# they are exhaustive by construction: a miss fails one of the criterion's three
# tests, or the reading is not about this root at all. They are validated rather
# than trusted, because a free-text reason cannot be counted afterwards without
# being re-read and re-decided.
MISS_CLASSES = ("imported", "inert", "direction", "collision")

# The closed engine's pre-declared bias split: seven letters own a صفة no other
# letter carries. Later tables report the same split for comparability.
SIGNATURE_LETTERS = frozenset("رشضلصزس")


@dataclass(frozen=True)
class RecordSpec:
    """How one engine's record file names things. Nothing else differs."""

    label: str                      # the file name findings are prefixed with
    path_label: str                 # the repo-relative path, for the empty-state note
    recorded_field: str             # the timestamp stamped when a reading is generated
    noun: str                       # what is generated: "concept", "reading"
    signature_letters: frozenset[str] = SIGNATURE_LETTERS
    development_case: str = DEVELOPMENT_CASE
    off_set_reason: str = ("it verified the composition rule, so it cannot also "
                           "test it.")


CLOSED_ENGINE = RecordSpec(
    label="concept_attestation.json",
    path_label="data/references/concept_attestation.json",
    recorded_field="concept_recorded_at",
    noun="concept",
)


def _text(value) -> str:
    """A CSV/JSON cell as trimmed text — `None` and a missing column read empty."""
    return (value or "").strip() if isinstance(value, (str, type(None))) else str(value)


@dataclass(frozen=True)
class AttestedUse:
    """One Quranic sense frozen for a root BEFORE its reading was generated.

    `reason` is required on anything that is not `covered`: a miss is a recorded
    result and carries its one line. It is the only thing that makes the
    judgement redoable by a reader who disagrees with it.
    """

    gloss: str
    verse: str                      # "s:a"
    verdict: str                    # covered | not_covered | not_judged
    reason: str


def witness_roots(witness: dict) -> frozenset[str]:
    """The holdout's roots, for the METRIC. Absent or malformed reads as EMPTY.

    Empty is the safe direction HERE: `in_witness_set` then reads False everywhere,
    and `counts_toward_k` with it, so a broken holdout file can only ever shrink
    what the metric claims. The guard reads the same file in the opposite
    direction, and raises on empty.
    """
    entries = witness.get("roots")
    if not isinstance(entries, list):
        return frozenset()
    return frozenset(
        str(e.get("root") or "").strip()
        for e in entries
        if isinstance(e, dict) and str(e.get("root") or "").strip()
    )


def _use(raw) -> AttestedUse:
    """One `uses[]` entry as read. An unknown verdict reads `not_judged`, never `covered`."""
    if not isinstance(raw, dict):
        return AttestedUse(gloss="", verse="", verdict=USE_NOT_JUDGED, reason="")
    verdict = str(raw.get("verdict") or "").strip()
    return AttestedUse(
        gloss=str(raw.get("gloss") or "").strip(),
        verse=str(raw.get("verse") or "").strip(),
        verdict=verdict if verdict in (USE_COVERED, USE_NOT_COVERED) else USE_NOT_JUDGED,
        reason=str(raw.get("reason") or "").strip(),
    )


def read_uses(record: dict, field: str = "uses") -> tuple[AttestedUse, ...]:
    """A record's frozen uses, in file order. No record, no list → empty."""
    raw = record.get(field)
    if not isinstance(raw, list):
        return ()
    return tuple(_use(entry) for entry in raw)


def verdict_for(uses: tuple[AttestedUse, ...]) -> str:
    """`covers_all` · `partial` · `not_recorded`, and EMPTY IS NOT FULL.

    The emptiness test comes FIRST, before anything that could read as agreement.
    One use short of covered — judged a miss or never judged — makes the root
    `partial`. There is no third grade, no weighting and no «mostly».
    """
    if not uses:
        return VERDICT_NOT_RECORDED
    if all(use.verdict == USE_COVERED for use in uses):
        return VERDICT_COVERS_ALL
    return VERDICT_PARTIAL


def counts_toward_k(root: str, in_witness_set: bool,
                    development_case: str = DEVELOPMENT_CASE) -> bool:
    """Whether this root may contribute to `k / 40`.

    The development case is named here rather than left to fall out of its
    absence from the holdout, so the exclusion survives the day someone adds it.
    """
    return in_witness_set and root != development_case


@dataclass(frozen=True)
class Metric:
    """`k / 40`, or the reason it is not printable.

    `printable` is False in two very different situations and the report must not
    conflate them: nothing has been recorded yet (normal, most of this change's
    life), or something was recorded out of protocol order (a finding). `blocked`
    names the roots responsible for the second.

    `total` is always the witness set's size. A `k` over a subset is not a
    smaller version of this measurement, it is a different one — which is why a
    partial record prints progress and no `k` at all.
    """

    total: int
    recorded: int
    k: int
    signature: tuple[int, int]        # (k, n) over roots carrying a signature letter
    plain: tuple[int, int]            # (k, n) over roots carrying none
    blocked: tuple[str, ...]
    printable: bool
    note: str
    # Roots the record file carries that are NOT on the holdout. They are
    # published beside the number and counted in neither half — `ضرب` above all,
    # which §D9 step 3 REQUIRES to be confronted and published.
    published_off_set: tuple[str, ...] = ()
    development_case: str = DEVELOPMENT_CASE
    off_set_reason: str = ("it verified the composition rule, so it cannot also "
                           "test it.")

    @property
    def off_set(self) -> str:
        """Why the development case never contributes, stated wherever the number is."""
        line = (f"«{self.development_case}» is confronted and published like any "
                f"other root and contributes to neither half: "
                f"{self.off_set_reason}")
        if self.published_off_set:
            line += (" Published and uncounted in this run: "
                     + "، ".join(self.published_off_set) + ".")
        return line


def records(attestation: dict) -> dict[str, dict]:
    """`root → record`, accepting either shape the record file may take.

    A dict keyed by root, or a list of objects each carrying `root`. Tolerated
    rather than pinned because this gate is written BEFORE the file it gates: an
    ordering that is the whole point of the protocol should not also be an
    invitation to guess a schema wrong and fail the writer.
    """
    roots = attestation.get("roots")
    if isinstance(roots, dict):
        return {k: v for k, v in roots.items() if isinstance(v, dict)}
    if isinstance(roots, list):
        return {
            _text(r.get("root")): r for r in roots
            if isinstance(r, dict) and _text(r.get("root"))
        }
    return {}


def moment(value) -> datetime | None:
    """An ISO-8601 timestamp, or None when it cannot be ordered.

    A commit hash is accepted by the schema as an alternative identity but is NOT
    orderable here, and «not orderable» blocks the metric rather than passing it:
    the protocol's one claim is about ORDER, so a record that cannot state its
    order has not made the claim.
    """
    text = _text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def check_attestation(attestation: dict | None,
                      witness_roots: tuple[str, ...],
                      spec: RecordSpec = CLOSED_ENGINE) -> tuple[Metric, list[str]]:
    """The freeze-before-generate ordering, then `k / 40` when it holds.

    The gate is the point, not the number. §D9's ordering is what makes "does the
    concept cover its uses" a question with an answer: a `uses[]` list written
    after the concept has been read shapes itself around the sentence, silently
    and in good faith. Nothing downstream can detect that, so it is detected here
    by refusing to print.
    """
    total = len(witness_roots)
    empty = Metric(total=total, recorded=0, k=0, signature=(0, 0), plain=(0, 0),
                   blocked=(), printable=False, note="",
                   development_case=spec.development_case,
                   off_set_reason=spec.off_set_reason)

    if attestation is None:
        return replace(empty, note=(
            "no attestation records yet; the metric is not printable. "
            f"{spec.path_label} is written root by "
            f"root, each root's `uses[]` committed BEFORE its {spec.noun} is generated."
        )), []

    findings: list[str] = []
    records_ = records(attestation)
    if not records_:
        # AN EMPTY `roots` CONTAINER IS THE SKELETON, NOT A BROKEN FILE, and the
        # two must not be conflated. This gate was written before the record file
        # existed, and it assumed «the file exists» meant «curation has begun».
        # It does not: the skeleton is committed first, carrying the protocol and
        # the record shape and no root at all, precisely so that the first root's
        # `uses[]` lands in a file whose rules are already published. Reporting
        # that as a finding would make the ordering the protocol is about
        # impossible to commit — the skeleton could only ever arrive with a
        # record already in it.
        #
        # The finding stays for everything else that produces no records: a
        # missing `roots` key, a `roots` of the wrong type (which is what a file
        # that failed to parse reads as, `_read_attestation` returning `{}`), or
        # a container holding entries none of which is a usable record. Those are
        # a file saying nothing when it meant to say something.
        container = attestation.get("roots")
        if isinstance(container, (dict, list)) and not container:
            return replace(empty, note=(
                "the record file is on disk as a SKELETON and records no root "
                "yet; the metric is not printable. Each root's `uses[]` is "
                f"committed BEFORE its {spec.noun} is generated — that ordering is "
                "the only property the file has."
            )), []
        findings.append(
            f"{spec.label}: exists but records no root — `roots` must "
            "be an object keyed by root (or a list of objects each carrying "
            "`root`). An EMPTY `roots` object is the skeleton and is accepted; "
            "an absent or malformed one is a file that failed to say anything."
        )
        return replace(empty, note="the record file carries no root."), findings

    witness = set(witness_roots)
    off_set = sorted(set(records_) - witness)

    blocked: list[str] = []
    k = 0
    sig_k = sig_n = plain_k = plain_n = 0

    for root in witness_roots:
        record = records_.get(root)
        if record is None:
            continue

        where = f"{spec.label}: «{root}»"
        frozen_at = moment(record.get("uses_frozen_at"))
        recorded_at = moment(record.get(spec.recorded_field))

        # FROZEN, AWAITING GENERATION — the mandated intermediate state.
        # An absent `concept_recorded_at` is not a missing field; it is the
        # record saying the concept has not been generated, which is what the
        # commit that freezes `uses[]` is FOR.
        awaiting = not _text(record.get(spec.recorded_field))
        if awaiting:
            if frozen_at is None:
                findings.append(
                    f"{where}: `uses_frozen_at` is missing or not an orderable "
                    f"ISO-8601 timestamp. A record awaiting its {spec.noun} still has "
                    "to state WHEN it was frozen — that stamp is the whole claim."
                )
            uses = record.get("uses")
            if not isinstance(uses, list) or not uses:
                findings.append(f"{where}: `uses[]` is missing or empty")
                continue
            for j, use in enumerate(uses):
                if not isinstance(use, dict):
                    findings.append(f"{where}: uses[{j}] is not an object")
                    continue
                if not _text(use.get("gloss")):
                    findings.append(f"{where}: uses[{j}] has no `gloss`")
                if not _text(use.get("verse")):
                    findings.append(f"{where}: uses[{j}] has no verse reference")
                verdict = _text(use.get("verdict"))
                if verdict and verdict != VERDICT_NOT_JUDGED:
                    findings.append(
                        f"{where}: uses[{j}] carries the verdict «{verdict}» while "
                        f"no {spec.noun} is recorded. A use judged before the {spec.noun} "
                        f"exists was judged against nothing — leave it "
                        f"«{VERDICT_NOT_JUDGED}» until the {spec.noun} is generated."
                    )
            continue

        if frozen_at is None or recorded_at is None:
            blocked.append(root)
            findings.append(
                f"{where}: `uses_frozen_at` / `{spec.recorded_field}` is missing or "
                "not an orderable ISO-8601 timestamp. The protocol's one claim is "
                "about ORDER; a record that cannot state its order has not made "
                "the claim."
            )
        elif frozen_at > recorded_at:
            blocked.append(root)
            findings.append(
                f"{where}: `uses[]` was frozen at {frozen_at.isoformat()}, AFTER "
                f"the {spec.noun} was recorded at {recorded_at.isoformat()}. The list "
                "can then have shaped itself around the sentence, so coverage is "
                "not a measurement of anything — re-freeze the uses and regenerate."
            )

        uses = record.get("uses")
        if not isinstance(uses, list) or not uses:
            findings.append(f"{where}: `uses[]` is missing or empty")
            continue
        for j, use in enumerate(uses):
            if not isinstance(use, dict):
                findings.append(f"{where}: uses[{j}] is not an object")
                continue
            if not _text(use.get("gloss")):
                findings.append(f"{where}: uses[{j}] has no `gloss`")
            if not _text(use.get("verse")):
                findings.append(f"{where}: uses[{j}] has no verse reference")
            verdict = _text(use.get("verdict"))
            if verdict == VERDICT_NOT_JUDGED:
                findings.append(
                    f"{where}: uses[{j}] is still «{VERDICT_NOT_JUDGED}» although a "
                    f"{spec.noun} IS recorded. Generation without judgement leaves a "
                    "root that can never reach `covers_all` and never appear as a "
                    "miss either — it would silently drop out of the denominator."
                )
            elif verdict not in USE_VERDICTS:
                findings.append(
                    f"{where}: uses[{j}] `verdict` is «{verdict}», expected one of "
                    f"{', '.join(USE_VERDICTS)} — there is no partial credit at "
                    "the use level either"
                )
            if verdict == "not_covered":
                reason = _text(use.get("reason"))
                if not reason:
                    findings.append(
                        f"{where}: uses[{j}] is a miss with no `reason` — a miss is "
                        "a recorded result and carries its one line; it is never a "
                        "reason to edit the table"
                    )
                elif reason.split(":", 1)[0].split()[0] not in MISS_CLASSES:
                    findings.append(
                        f"{where}: uses[{j}]'s reason does not open with one of "
                        f"{', '.join(MISS_CLASSES)}. An unclassified miss cannot be "
                        "counted later, and §D3's reopening condition is a count "
                        "over exactly these classes."
                    )

        covers_all = all(
            isinstance(u, dict) and _text(u.get("verdict")) == "covered" for u in uses
        )
        k += 1 if covers_all else 0
        if spec.signature_letters & set(root):
            sig_n += 1
            sig_k += 1 if covers_all else 0
        else:
            plain_n += 1
            plain_k += 1 if covers_all else 0

    # RECORDED means «this root's concept has been generated and judged», never
    # «this root has a record». The two were the same expression until the file
    # first held its mandated intermediate state, and then they were not: with
    # all 40 frozen and none generated, counting records made `recorded == total`
    # and printed «k / 40 : 0 / 40» — a number over nothing, which reads as «the
    # method covers no root» rather than «nothing has been measured yet». The
    # most dangerous number this script can print is the one that looks like a
    # result and is an artefact of its own bookkeeping.
    recorded = sum(
        1 for root in witness_roots
        if isinstance(records_.get(root), dict)
        and _text(records_[root].get(spec.recorded_field))
    )
    awaiting_roots = tuple(sorted(
        root for root in witness_roots
        if isinstance(records_.get(root), dict)
        and not _text(records_[root].get(spec.recorded_field))
    ))

    if blocked:
        note = (
            "REFUSED — {n} witness root(s) recorded out of protocol order: "
            "{roots}. The number is not printed at all; a caveat beside it would "
            "be a number nobody reads the caveat of."
        ).format(n=len(blocked), roots="، ".join(sorted(set(blocked))))
        return replace(empty, recorded=recorded, blocked=tuple(sorted(set(blocked))),
                       note=note), findings

    if recorded < total:
        if awaiting_roots and recorded == 0:
            note = (
                f"{len(awaiting_roots)} of {total} witness roots have their "
                f"`uses[]` FROZEN and not one {spec.noun} has been generated, so "
                "the metric is not printable — and that is the protocol "
                "working, not a gap. The freeze is committed as its own step "
                f"so that it exists in the history before any {spec.noun} does."
            )
        else:
            note = (
                f"{recorded} of {total} witness roots have a {spec.noun} recorded"
                + (f" ({len(awaiting_roots)} frozen and awaiting generation)"
                   if awaiting_roots else "")
                + "; the metric is not printable yet. A `k` over a subset is not a "
                "smaller version of this measurement — it is a different one, and "
                "the design forbids reporting it as the result."
            )
        return replace(empty, recorded=recorded, note=note), findings

    # Off-set records get the SHAPE rules and not the ordering gate, and the
    # asymmetry is the honest one. A published record must still be readable — a
    # gloss, a verse, a verdict from the closed vocabulary, a reason on every
    # miss — because a reader cannot tell from the page that this root is
    # uncounted. But the freeze-before-generate ORDER cannot be claimed for
    # `ضرب`: its concept has been read since §D5 was written, which is exactly
    # why §D9 excludes it from `k`. Asserting the ordering here would be the
    # record claiming a blindness it never had.
    for root in off_set:
        record = records_.get(root)
        if not isinstance(record, dict):
            continue
        where = f"{spec.label}: «{root}» (published, uncounted)"
        uses = record.get("uses")
        if not isinstance(uses, list) or not uses:
            findings.append(f"{where}: `uses[]` is missing or empty")
            continue
        generated = bool(_text(record.get(spec.recorded_field)))
        for j, use in enumerate(uses):
            if not isinstance(use, dict):
                findings.append(f"{where}: uses[{j}] is not an object")
                continue
            if not _text(use.get("gloss")):
                findings.append(f"{where}: uses[{j}] has no `gloss`")
            if not _text(use.get("verse")):
                findings.append(f"{where}: uses[{j}] has no verse reference")
            verdict = _text(use.get("verdict"))
            if not generated:
                if verdict and verdict != VERDICT_NOT_JUDGED:
                    findings.append(
                        f"{where}: uses[{j}] carries «{verdict}» while no {spec.noun} "
                        f"is recorded — judged against nothing."
                    )
            elif verdict not in USE_VERDICTS:
                findings.append(
                    f"{where}: uses[{j}] `verdict` is «{verdict}», expected one of "
                    f"{', '.join(USE_VERDICTS)}"
                )
            elif verdict == "not_covered":
                reason = _text(use.get("reason"))
                if not reason:
                    findings.append(
                        f"{where}: uses[{j}] is a miss with no `reason` — an "
                        f"uncounted root's miss is still a published result"
                    )
                elif reason.split(":", 1)[0].split()[0] not in MISS_CLASSES:
                    findings.append(
                        f"{where}: uses[{j}]'s reason does not open with one of "
                        f"{', '.join(MISS_CLASSES)}"
                    )

    # A RECORD FOR A NON-WITNESS ROOT IS NOT A FINDING, and treating it as one
    # made the gate contradict two documents it is supposed to enforce. §D9 step 3
    # requires `ضرب` to be confronted and published; `concept_attestation.json`'s
    # own meta says records may exist for roots off the holdout and are published
    # like any other. A finding fails the run (`main` returns 1 on any), so the
    # mandated step could not be taken without breaking the validator.
    #
    # It is safe to publish and not to count because `k` is computed by iterating
    # `witness_roots`, not `records`: an off-set record has no path into either
    # half of the number, whatever it says. What it CAN do is mislead a reader, so
    # it is shape-checked above like every other record and named beside the
    # number here rather than left to be discovered in the file.

    return Metric(total=total, recorded=recorded, k=k,
                  signature=(sig_k, sig_n), plain=(plain_k, plain_n),
                  blocked=(), printable=True, note="",
                  published_off_set=tuple(off_set),
                  development_case=spec.development_case,
                  off_set_reason=spec.off_set_reason), findings



