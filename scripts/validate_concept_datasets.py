#!/usr/bin/env python3
"""
validate_concept_datasets.py — OFFLINE gate on the physics-first concept datasets.

Checks `physical_primitives.csv`, its lock, `concept_witness_set.json` and — once
it exists — `concept_attestation.json` against the rules `k / 40` depends on, and
prints the report. Exit code 0 when clean, 1 with every finding listed otherwise.
No network, no model, no LLM: every rule is a comparison between files already on
disk, or a replay of a draw the file itself records.

Why a validator rather than trust in curation: each rule guards a failure that is
SILENT, and several of them would not corrupt an output — they would corrupt the
MEASUREMENT, which is worse, because a corrupted measurement still prints a
number.

  * **A row with an empty `status`, or `attested` dressed in an unresolvable
    page.** The table is this project's own construction; that is the condition
    under which `k / 40` can falsify it. A row wearing a borrowed citation can
    always blame its failure on the source, so the measurement stops being able
    to say anything. A page that resolves nowhere is that borrowing with an
    audit trail that dead-ends — and the answer is never to quietly re-file the
    row as `hypothesis`, because the claim that was made is the one that must be
    checked.
  * **A digest that no longer matches.** Root curation runs against a FIXED
    table. The failure this guards is not a crash but a method failure: a root
    reads badly, a primitive is reglossed, the root now "works" — and nothing
    records that the evidence was written to fit the conclusion.
  * **A `history[].source` written as prose.** A draft of the previous change's
    lock carried nine invented page ranges before a manual re-read caught them.
    A justification nobody can follow back makes the freeze decorative: it looks
    like evidence and costs nothing to fabricate.
  * **A witness set quietly re-rolled.** The 40 roots are the holdout; a draw
    repeated until it looks convenient is not one. The draw is replayed from the
    file's OWN recorded seed and strata, so editing the roots without editing the
    procedure fails, and editing the procedure is visible in the diff.
  * **A `uses[]` list frozen after its concept was read.** "Does the concept
    cover its uses" is elastic the moment the list can shape itself around the
    sentence. The ordering IS the protocol, so the metric is refused rather than
    printed with a caveat.

**The `project` authority, and why it is not a hole.** The lock's
`history[].source` may name `project` — and the shipped v1.0.0 entry does. That
is not an exemption from citation; it is the LOCK-LEVEL ANALOGUE of a row's
`hypothesis` status, and it is *narrower* than a citation rather than looser. A
cited source must name real pages; `project` must name NONE (a construction has
no locus, and pages on it would be a borrowed locus), must carry an explicit
`basis` saying what it rests on, and must carry a `reason`. Three required
fields against a citation's two. What it buys is the ability to say «this is
ours» out loud instead of reaching for a page that does not exist — which is the
single behaviour the nine invented ranges came from.

Usage:
    python scripts/validate_concept_datasets.py     # 0 = clean, 1 = findings

`validate()` takes a `Datasets` so `tests/test_physical_primitives.py` drives
these exact rules against a deliberately broken in-memory copy
(`dataclasses.replace`) instead of restating them — a second copy of a rule is a
rule that can disagree with itself.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arabic_text import normalize_root  # noqa: E402
from quran_data import loaders, paths  # noqa: E402
from quran_data.paths import (  # noqa: E402
    LETTER_SEMANTICS_JSON,
    PHYSICAL_PRIMITIVES_CSV,
    REFERENCES,
)

# ── the wording the report is held to (§D11) ─────────────────────────────────
# A module-level constant so a test can grep for it, and so the claim is written
# ONCE. «Auditable» and «audited» differ by one letter and by everything else:
# the second would be a description of a review that did not happen.
AUDIT_CLAIM = (
    "The committed records — each root's frozen uses, its generated concept, its "
    "per-use verdict and its reason — make this judgement REDOABLE by anyone who "
    "clones the repository. There is no second judge: the verdicts are the "
    "curator's own, and no independent review took place."
)

# §D11's reservation, printed WITH the number and never by reference. `k / 40`
# comes out of a composition rule that is not entirely pre-registered: the
# realised window was declared at two and widened to three AFTER a negative
# measurement on the declared development case. A reader meeting the number is
# owed its provenance at that moment — a caveat someone has to go and find in a
# design note is a caveat the publisher has kept.
#
# Note what this text deliberately does NOT do: it does not let the containment
# swallow the admission. The holdout really was untouched and ضرب really is
# excluded from `k`, and both are said — but one free parameter of the rule was
# still set by looking at an outcome, and the last sentence is what keeps that
# visible instead of letting the mitigations read as an acquittal.
WINDOW_RESERVATION = (
    "RESERVATION, carried with the number: the composition rule is NOT entirely "
    "pre-registered. The realised window — how many primitives per position reach "
    "the sentence — was declared at two and widened to three after a measurement "
    "came back negative on ضرب, the declared development case. The positions, the "
    "rarity ordering and the tie-break were fixed before they were checked; the "
    "window was not. What contains this: the holdout was never read when the "
    "window changed, and ضرب is excluded from k. What it does not do: erase it. "
    "One free parameter of the rule was set by looking at an outcome, and a "
    "reader who discounts k / 40 on that ground is reading correctly."
)

# ── the closed enumerations every rule is checked against ────────────────────
# A row either names an authority that states the mapping, or owns the claim.
# There is no third state and no empty one: «unfilled» would read on screen as
# «not yet cited», which is indistinguishable from «cited» to everyone except
# the curator who left it blank.
STATUSES = ("attested", "hypothesis")

# §D4. The vocabulary is closed because the brief's «une quinzaine maximum» is a
# claim about EXPLANATORY POWER, not about file size: with enough primitives every
# root reads well and «it reads well» stops being evidence of anything.
#
# **Raised from 15 to 20** when the five classical مخرج zones entered the table as
# v1.0.0 — §D3's pre-declared fallback, triggered by §D13's collision probe
# returning `identical` on 5 of 5 qualifying comparisons. The ceiling moved by
# exactly five, and what came in is one CLOSED classical partition of the mouth
# rather than five free parameters: there is no sixth zone to reach for the next
# time a root disappoints. A cap that admits a named partition whole, once, on a
# trigger declared in advance is still a cap.
PRIMITIVE_CAP = 20

# The feature-level authorities a row or a lock entry may name. Closed for the
# same reason the Lisan axis vocabulary is: the field is otherwise free text, and
# free text is where an unfollowable citation lives.
#
# id → the label shown beside a reading. `project` is registered here and its
# label says what it is in both languages, because the whole exposure of this
# change is that most of the table is the project's own construction: a label
# reading like a scholar's name would smuggle authority back in through the one
# field that exists to disclaim it.
FEATURE_AUTHORITIES = {
    "hasan_abbas": "حسن عباس، خصائص الحروف العربية ومعانيها",
    "ibn_jinni": "ابن جني، الخصائص — باب في إمساس الألفاظ أشباه المعاني",
    "project": (
        "هذا المشروع — بناء ذاتي لا يستند إلى مرجع "
        "(this project's own construction; no borrowed authority)"
    ),
}
PROJECT_AUTHORITY = "project"

# `physical_primitives.csv`'s exact column set. Checked rather than assumed: an
# undeclared column is the only way a root-keyed column could arrive without
# being called `root`, and the table's whole guarantee is that it is keyed on the
# feature vocabulary ALONE.
TABLE_COLUMNS = (
    "feature", "primitive", "gloss_ar", "gloss_en", "status",
    "authority", "pages", "physical_basis", "support", "lemmas",
)

# The columns anything could ever be LOOKED UP by. The no-root rule applies here
# and only here — see `check_primitive_table` for why the free-text columns are
# deliberately not included.
KEY_COLUMNS = ("feature", "primitive")

# Non-empty on every row whatever its status. `gloss_en` is not in the list: it
# is a convenience for a non-Arabic reader and asserts nothing.
ALWAYS_REQUIRED = ("feature", "primitive", "gloss_ar", "lemmas")

# Page strings that gesture at a locus instead of naming one. Membership in the
# authority index already refuses all of these; the pattern exists only so the
# finding can say WHY rather than «not found».
APPROXIMATE_PAGE = re.compile(
    r"[~≈+]|\bff?\b|\bcirca\b|\babout\b|\bp{1,2}\.|\bص\b|\bحوالي\b|\?", re.IGNORECASE
)

# Tatweel (kashida): a display elongation, not a letter.
# `arabic_letter_semantics_hasan_abbas.json` spells hāʾ as «هـ», so an index of
# that file keyed on its raw `letter` answers nothing for «ه».
TATWEEL = "ـ"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# Every lock history entry carries all five. `source` is the load-bearing one: a
# row changes because a FEATURE-level authority says so, never because a root
# failed to match — so a version whose reason cannot name a source is exactly the
# edit this freeze exists to catch.
HISTORY_FIELDS = ("version", "date", "sha256", "reason", "source")

# ── §D10: the frame criteria the draw is replayed under ──────────────────────
# Declared here rather than parsed out of the file's prose `procedure[]`: the
# procedure is a human-readable record, and a validator that re-derived its rule
# by reading its own subject could be satisfied by editing the prose. The recorded
# frame and stratum sizes ARE read from the file and compared against what these
# constants produce, so a drift in either direction is a finding.
MIN_OCCURRENCES = 20
STRATUM_BOUNDARY = 100

# The frame exclusions AS THEY STOOD AT THE DRAW. Frozen literals, not a re-read
# of today's `root_cores.json`: the draw is a historical event and replaying it
# against a curated set that has since grown would "reproduce" a different set
# and report the file as edited.
CURATED_AT_DRAW = ("خبث", "خير", "رحم", "ظلم", "كفر")
DEVELOPMENT_CASE = "ضرب"

# §D13's collision-probe roots. Probe roots are never witness roots: a root used
# to settle whether the table discriminates cannot also be evidence that it
# works.
PROBE_ROOTS = ("حرب", "حرج", "حرد", "تبر", "كبر", "كود", "كيد")

# §D5's structural bias, declared BEFORE the measurement so the split cannot be
# chosen afterwards for being flattering: seven letters own a صفة no other letter
# carries, so rarity ordering makes them always lead with their own signature.
SIGNATURE_LETTERS = frozenset("رشضلصزس")

# The attestation record, not yet on disk (task 7.2 writes it, AFTER this gate
# exists — the same ordering the protocol itself is about). Resolved through
# `paths` when the constant lands there, so the day it does this line needs no
# edit and the manifest becomes its single home as usual.
CONCEPT_ATTESTATION_JSON = getattr(
    paths, "CONCEPT_ATTESTATION_JSON", REFERENCES / "concept_attestation.json"
)

# A use is covered or it is not. There is no partial credit anywhere in this
# protocol, at the use level or at the root level.
USE_VERDICTS = ("covered", "not_covered")

# The verdict a use carries between the two moments the protocol separates: its
# `uses[]` are frozen and committed, and its concept does not exist yet.
#
# This state had no representation here, and its absence was a real hole rather
# than an oversight to tidy: §D9's ordering REQUIRES a commit in which the uses
# are on file and the concept is not, so a gate that rejects that state makes the
# protocol it enforces impossible to follow. The only way to satisfy the old rules
# was to write `uses[]` and the verdicts together — which is precisely the
# after-the-fact record the gate exists to catch.
#
# A root in this state is not counted as `recorded`, contributes nothing to `k`,
# and produces no finding. What is still refused: a concept recorded while a use
# is unjudged (below), and a `concept_recorded_at` earlier than `uses_frozen_at`.
VERDICT_NOT_JUDGED = "not_judged"


# ── inputs ───────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Datasets:
    """The inputs every rule reads, as plain data.

    Held as a value object so a test can hand in a deliberately broken in-memory
    copy (`dataclasses.replace` via `with_`) without writing a file to disk — the
    rules and the shipped files are then exercised by the same code. That pattern
    is load-bearing: a rule tested against a fixture it does not share with
    production is a rule tested twice and enforced once.

    `morphology` is the whole index rather than a key set, because two rules need
    it in two shapes: the witness replay reads `count`, and the no-root rule asks
    only for membership.

    `attestation` is `None` when the file is not on disk yet. That is a normal
    state for most of this change's life, not an error, and the metric gate
    distinguishes «no records» from «records that break the protocol».
    """

    table: list[dict]                    # physical_primitives.csv rows, file order
    table_bytes: bytes                   # the RAW bytes the lock's digest is over
    lock: dict                           # physical_primitives.lock.json
    witness: dict                        # concept_witness_set.json
    morphology: dict[str, dict]          # canonical QAC root key → record
    maqayis_has_asl: frozenset[str]      # normalized roots with a has_asl row
    authority_pages: dict[str, str]      # base letter → the pages the authority is cited at
    attestation: dict | None             # concept_attestation.json, or None

    @classmethod
    def load(cls) -> "Datasets":
        """Read the shipped files through the registry's cached loaders.

        Returns the loaders' own objects — nothing here mutates them. A caller
        building a broken copy must deep-copy the piece it breaks, or it would
        corrupt the process-wide cache for every later test.

        `table_bytes` is the one input read off disk rather than through a
        loader, because the freeze is taken over the FILE, not over the parsed
        rows: a reformat that leaves every row equal still moves the table, and a
        frozen table does not get reformatted by accident.
        """
        return cls(
            table=loaders.physical_primitives(),
            table_bytes=PHYSICAL_PRIMITIVES_CSV.read_bytes(),
            lock=loaders.physical_primitives_lock(),
            witness=loaders.concept_witness_set(),
            morphology=loaders.morphology(),
            maqayis_has_asl=frozenset(
                r["root_normalized"] for r in loaders.maqayis_asl()
                if _text(r.get("asl_status")) == "has_asl"
            ),
            authority_pages=_authority_pages(loaders.letter_semantics()),
            attestation=_read_attestation(),
        )

    def with_(self, **changes) -> "Datasets":
        """A copy with some inputs swapped — the injection point for tests."""
        return replace(self, **changes)

    @property
    def witness_roots(self) -> tuple[str, ...]:
        """The roots the file records, in file order (= draw order)."""
        entries = self.witness.get("roots")
        if not isinstance(entries, list):
            return ()
        return tuple(_text(e.get("root")) for e in entries if isinstance(e, dict))


def _read_attestation() -> dict | None:
    """The attestation record, or None while it does not exist yet.

    Absence is read off the filesystem rather than through a loader, because
    there is no loader (and no manifest entry) until the file exists. A malformed
    file on the other hand is NOT absence — it is returned as an empty document
    so the shape rules report it instead of the gate reading «nothing recorded».
    """
    if not CONCEPT_ATTESTATION_JSON.exists():
        return None
    try:
        return json.loads(CONCEPT_ATTESTATION_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ── shared helpers ───────────────────────────────────────────────────────────
def _text(value) -> str:
    """A CSV/JSON cell as trimmed text — `None` and a missing column read empty."""
    return (value or "").strip() if isinstance(value, (str, type(None))) else str(value)


def _split_cell(value: str) -> list[str]:
    """Split a ';'-separated dataset cell, trimmed, empties dropped."""
    return [part.strip() for part in (value or "").split(";") if part.strip()]


def _authority_pages(semantics_doc: dict) -> dict[str, str]:
    """`base letter → the page range the letter-level authority is cited at`.

    Read from `arabic_letter_semantics_hasan_abbas.json` — the same index
    `scripts/validate_lisan_datasets.py` builds, by the same rule and with the
    same tatweel strip — so a page claimed anywhere in this repo is checked
    against one registry rather than against whichever list its own change
    happened to ship.
    """
    pages: dict[str, str] = {}
    for entry in semantics_doc.get("letters", []):
        if not isinstance(entry, dict):
            continue
        letter = _text(entry.get("letter")).replace(TATWEEL, "")
        dalala = entry.get("dalala_hasan_abbas") or {}
        page = _text(dalala.get("pages")) if isinstance(dalala, dict) else ""
        if letter and page:
            pages[letter] = page
    return pages


def _check_pages(pages: list[str], authority_pages: dict[str, str],
                 where: str, field: str) -> list[str]:
    """Every page is an EXACT member of the authority index, or it is a finding.

    Exact, never a prefix or a substring match: «148» inside «148-152» is how a
    half-remembered locus passes as a checked one. Approximation is refused for
    the same reason a `hypothesis` row exists — a claim that cannot be followed
    back should be made as the project's own, not as a scholar's with a hedge.
    """
    findings: list[str] = []
    declared = set(authority_pages.values())
    for page in pages:
        if page in declared:
            continue
        if APPROXIMATE_PAGE.search(page):
            findings.append(
                f"{where}: `{field}` cites «{page}», an APPROXIMATE reference. A "
                "page is named exactly or the claim is made as the project's own "
                "— there is no hedged citation in this table."
            )
        else:
            findings.append(
                f"{where}: `{field}` cites «{page}», which is not a page range "
                f"the authority declares — look it up in "
                f"{LETTER_SEMANTICS_JSON.name}"
            )
    return findings


# ── A. the primitive table ───────────────────────────────────────────────────
def check_primitive_table(rows: list[dict], authority_pages: dict[str, str],
                          root_keys: frozenset[str]) -> list[str]:
    """Statuses carry their evidentiary duty, the cap holds, and no root keys it.

    **Scope of the no-root rule, stated because the shipped data forces the
    question.** `feature` and `primitive` are the only columns anything is ever
    looked up by, so they are the only ones a root could KEY the table through,
    and the rule is enforced there. `lemmas`, `gloss_ar`, `gloss_en`,
    `physical_basis` and `support` are free Arabic word-lists and prose — the
    lemma set exists to contain an optional LLM rephrasing, not to be indexed —
    and Arabic vocabulary inevitably coincides with root keys (`قطع` in the
    `shadida` row's lemma set is a real QAC root key today). Refusing that would
    be refusing the Arabic language, not refusing a per-root exception. The
    coincidence is reported in the summary instead of hidden, so the narrower
    reading is visible rather than assumed.
    """
    findings: list[str] = []
    if not rows:
        return ["physical_primitives.csv: file is empty"]

    columns = tuple(rows[0])
    missing = [c for c in TABLE_COLUMNS if c not in columns]
    extra = [c for c in columns if c not in TABLE_COLUMNS]
    if missing:
        findings.append(
            f"physical_primitives.csv: missing column(s) {', '.join(missing)}"
        )
    if extra:
        findings.append(
            f"physical_primitives.csv: undeclared column(s) {', '.join(extra)} — "
            "the table is keyed on the feature vocabulary alone, and an "
            "undeclared column is how a root-keyed one would arrive without "
            "being called `root`"
        )
    for column in columns:
        if "root" in column.lower():
            findings.append(
                f"physical_primitives.csv: column «{column}» names a root. The "
                "table carries no root, no root key and no per-root exception, "
                "and there is no mechanism by which a root can override it."
            )

    seen_features: set[str] = set()
    primitives: set[str] = set()

    for i, row in enumerate(rows):
        feature = _text(row.get("feature"))
        where = f"physical_primitives.csv: row #{i + 2} «{feature or '?'}»"  # +2: header + 1-based

        for field in ALWAYS_REQUIRED:
            if not _text(row.get(field)):
                findings.append(
                    f"{where}: empty `{field}` — every row carries it whatever its "
                    "status"
                )

        if feature:
            if feature in seen_features:
                findings.append(
                    f"{where}: duplicate `feature` — a feature maps to exactly one "
                    "primitive, and two rows for one feature make the mapping "
                    "depend on which is read last"
                )
            seen_features.add(feature)

        primitive = _text(row.get("primitive"))
        if primitive:
            primitives.add(primitive)

        # 1. No root may KEY the table.
        for column in KEY_COLUMNS:
            value = _text(row.get(column))
            if value and value in root_keys:
                findings.append(
                    f"{where}: `{column}` is «{value}», a canonical QAC root key. "
                    "The table is keyed on the feature vocabulary alone; a root "
                    "reaching a key column is a per-root exception by another name."
                )

        status = _text(row.get("status"))
        authority = _text(row.get("authority"))
        pages = _split_cell(_text(row.get("pages")))
        basis = _text(row.get("physical_basis"))
        support = _text(row.get("support"))

        if status not in STATUSES:
            findings.append(
                f"{where}: `status` is «{status}», expected exactly one of "
                f"{' or '.join(STATUSES)} — an empty status reads on screen as "
                "«not yet cited», which is indistinguishable from «cited»"
            )
            continue

        # 2. `attested` owes a real authority at a real page.
        if status == "attested":
            if not authority:
                findings.append(
                    f"{where}: `status` is `attested` with an empty `authority` — "
                    "attestation names who states the mapping, or it is a "
                    "`hypothesis`"
                )
            elif authority not in FEATURE_AUTHORITIES:
                findings.append(
                    f"{where}: `authority` is «{authority}», not one of the "
                    f"registered feature-level authorities "
                    f"({', '.join(sorted(FEATURE_AUTHORITIES))}) — adding one is a "
                    "visible decision, not something a row smuggles in"
                )
            elif authority == PROJECT_AUTHORITY:
                findings.append(
                    f"{where}: `status` is `attested` with `authority` "
                    f"«{PROJECT_AUTHORITY}» — a construction attesting to itself "
                    "is a hypothesis, and `hypothesis` is exactly the status that "
                    "says so without borrowing anyone's name"
                )
            if not pages:
                findings.append(
                    f"{where}: `status` is `attested` with empty `pages`. The row "
                    "is NOT downgraded to `hypothesis` on that account — the claim "
                    "that was made is the one that must be checked; either produce "
                    "the page or change the status deliberately."
                )
            else:
                page_findings = _check_pages(pages, authority_pages, where, "pages")
                findings += page_findings
                if page_findings:
                    findings.append(
                        f"{where}: the row stays `attested` and stays a finding — "
                        "an unresolvable page is never silently re-filed as "
                        "`hypothesis`, which would turn a failed citation into a "
                        "clean record"
                    )

        # 3. `hypothesis` owns the claim, and may not dress it as authority.
        else:
            if not basis:
                findings.append(
                    f"{where}: `status` is `hypothesis` with an empty "
                    "`physical_basis` — the project asserts the mapping, so it "
                    "must at least state the uncontested tajwīd fact it asserts "
                    "it from"
                )
            if authority:
                findings.append(
                    f"{where}: `status` is `hypothesis` but `authority` is "
                    f"«{authority}» — a hypothesis borrows no authority. If the "
                    "authority is real, the row is `attested` and owes pages; if "
                    "it is a supporting reference, it belongs in `support`."
                )
            if pages:
                findings.append(
                    f"{where}: `status` is `hypothesis` but `pages` is "
                    f"«{'; '.join(pages)}» — pages are a locus for an attestation, "
                    "and a locus on an owned claim reads as one"
                )
        # `support` is deliberately NOT page-checked, under either status:
        # checking it against the authority index is precisely what would render
        # it as authority. It is reported separately by `report()` and never
        # substitutes for `authority`.
        if support and status == "attested" and not authority:
            findings.append(
                f"{where}: `support` is «{support}» on an `attested` row with no "
                "`authority` — support is never promoted to authority to fill a "
                "gap"
            )

    # 4. The cap.
    if len(primitives) > PRIMITIVE_CAP:
        findings.append(
            f"physical_primitives.csv declares {len(primitives)} distinct "
            f"primitives, over the closed cap of {PRIMITIVE_CAP} — a richer table "
            "explains everything and therefore nothing. Merge, or drop; the cap "
            "is a claim about explanatory power, not about file size. It has been "
            "raised exactly once, by five, to admit the five classical مخرج zones "
            "as a closed partition on a pre-declared trigger — raising it again to "
            "fit a reading is the move it exists to block."
        )
    return findings


# ── B / D. the freeze, and the `project` escape hatch ────────────────────────
def check_source(source, authority_pages: dict[str, str], where: str) -> list[str]:
    """A lock history entry's `source`, checked the way a row's citation is.

    Two shapes, one field, and the difference is the whole point:

      * a CITATION (`hasan_abbas`, `ibn_jinni`) names pages, and every page must
        resolve in the authority index;
      * a CONSTRUCTION (`project`) names NO pages — a construction has no locus,
        and a page on it would be a borrowed one — and must carry a `basis`
        saying what it rests on.

    So `project` is narrower than a citation, not looser: three required fields
    against two, and the one it drops is the one it has no right to. That is the
    lock-level analogue of a row's `hypothesis`, and it exists for the same
    reason — a draft of the previous change's lock carried nine invented page
    ranges, produced by having no honest way to say «this is ours».
    """
    findings: list[str] = []
    if not isinstance(source, dict):
        return [
            f"{where}: `source` must be an object {{authority, pages}} — prose "
            "cannot be checked against anything, and an unverifiable citation is "
            "not a citation"
        ]

    authority = _text(source.get("authority"))
    if authority not in FEATURE_AUTHORITIES:
        findings.append(
            f"{where}: `source.authority` is «{authority}», expected one of "
            f"{', '.join(sorted(FEATURE_AUTHORITIES))}"
        )

    pages = source.get("pages")
    if pages is not None and not isinstance(pages, list):
        findings.append(f"{where}: `source.pages` must be a list")
        pages = []
    pages = [_text(p) for p in (pages or [])]

    if authority == PROJECT_AUTHORITY:
        if any(pages):
            findings.append(
                f"{where}: `source.authority` is «{PROJECT_AUTHORITY}» but "
                f"`source.pages` names «{'; '.join(p for p in pages if p)}». A "
                "construction cites no locus — a page here is a borrowed one, "
                "which is the exact move the `project` authority exists to make "
                "unnecessary."
            )
        if not _text(source.get("basis")):
            findings.append(
                f"{where}: `source.authority` is «{PROJECT_AUTHORITY}» with no "
                "`basis` — saying «this is ours» is allowed, saying it without "
                "stating what it rests on is not"
            )
        return findings

    if not pages or not any(pages):
        findings.append(
            f"{where}: `source.pages` is missing or empty. A named authority is "
            f"cited at a locus; if there is none, the source is "
            f"«{PROJECT_AUTHORITY}» with a `basis`."
        )
        return findings
    for page in pages:
        if not page:
            findings.append(f"{where}: `source.pages` holds an empty range")
    findings += _check_pages([p for p in pages if p], authority_pages, where,
                             "source.pages")
    return findings


def check_lock(lock: dict, table_bytes: bytes, rows: list[dict],
               authority_pages: dict[str, str]) -> list[str]:
    """The freeze on `physical_primitives.csv`: it did not move, or the version did.

    The rule is not «never change a row». It is «change it through a new version,
    justified by a FEATURE-level authority» — so the check is against the lock's
    own history, not against immutability. A root that reads badly is never such
    a justification: that is back-fitting, and its recorded outcome is a result.
    """
    findings: list[str] = []
    if not isinstance(lock, dict) or not lock:
        return ["physical_primitives.lock.json: missing or not an object"]

    version = _text(lock.get("version"))
    if not SEMVER.match(version):
        findings.append(
            f"physical_primitives.lock.json: `version` «{version}» is not "
            "MAJOR.MINOR.PATCH"
        )

    declared = _text(lock.get("sha256")).lower()
    actual = hashlib.sha256(table_bytes).hexdigest()
    if not declared:
        findings.append("physical_primitives.lock.json: no `sha256`")
    elif declared != actual:
        findings.append(
            f"physical_primitives.csv has changed under a frozen version:\n"
            f"      expected : {declared}\n"
            f"      actual   : {actual}\n"
            f"      Either revert the edit, or bump `version` and add a `history` "
            f"entry naming the FEATURE-level authority that justifies it — never "
            f"a root that did not work."
        )

    features = {_text(r.get("feature")) for r in rows if _text(r.get("feature"))}
    primitives = {_text(r.get("primitive")) for r in rows if _text(r.get("primitive"))}
    for field, expected in (("rows", len(rows)),
                            ("features", len(features)),
                            ("primitives", len(primitives))):
        if field in lock and lock.get(field) != expected:
            findings.append(
                f"physical_primitives.lock.json: `{field}` says {lock.get(field)}, "
                f"the table holds {expected}"
            )
    if "rows" not in lock:
        findings.append(
            "physical_primitives.lock.json: no `rows` — the row count is part of "
            "the freeze, so a truncated table cannot pass on its digest alone"
        )

    target = _text(lock.get("target"))
    if target and not target.endswith(PHYSICAL_PRIMITIVES_CSV.name):
        findings.append(
            f"physical_primitives.lock.json: `target` «{target}» is not "
            f"{PHYSICAL_PRIMITIVES_CSV.name}"
        )
    if not _text(lock.get("frozen_on")):
        findings.append("physical_primitives.lock.json: no `frozen_on`")

    history = lock.get("history")
    if not isinstance(history, list) or not history:
        findings.append("physical_primitives.lock.json: `history` is missing or empty")
        return findings

    seen: set[str] = set()
    for i, entry in enumerate(history):
        where = f"physical_primitives.lock.json: history #{i}"
        if not isinstance(entry, dict):
            findings.append(f"{where} is not an object")
            continue
        for field in HISTORY_FIELDS:
            if field == "source":
                findings += check_source(entry.get("source"), authority_pages, where)
                continue
            if not _text(entry.get(field)):
                findings.append(f"{where} has no `{field}`")
        hver = _text(entry.get("version"))
        if hver and hver in seen:
            findings.append(
                f"physical_primitives.lock.json: history declares version "
                f"«{hver}» twice"
            )
        seen.add(hver)

    # The current version must be the one the history ends on, with the digest it
    # ends on. A bumped version with no entry behind it is a freeze whose reason
    # was never written down.
    last = history[-1] if isinstance(history[-1], dict) else {}
    if version and _text(last.get("version")) != version:
        findings.append(
            f"physical_primitives.lock.json: `version` is «{version}» but the last "
            f"history entry is «{_text(last.get('version'))}» — every version "
            "carries its own reason and source"
        )
    if declared and _text(last.get("sha256")).lower() != declared:
        findings.append(
            "physical_primitives.lock.json: the last history entry's `sha256` "
            "disagrees with the top-level one"
        )
    return findings


# ── C. the witness set ───────────────────────────────────────────────────────
@dataclass(frozen=True)
class Draw:
    """A replay of the recorded draw, and what it produced."""

    drawn: tuple[str, ...]
    frame: int
    lower: int
    upper: int
    ran: bool          # False when the recorded procedure could not be replayed


def replay_draw(witness: dict, morphology: dict[str, dict],
                has_asl: frozenset[str]) -> tuple[Draw, list[str]]:
    """Re-run §D10's draw from the file's OWN seed and stratum sizes.

    The frame criteria (`MIN_OCCURRENCES`, `STRATUM_BOUNDARY`) and the exclusions
    are the module's constants; the seed and the two `drawn` counts come from the
    file. That split is deliberate: a validator that read its whole rule out of
    the document it validates can be satisfied by editing the document, and one
    that hardcoded everything would never notice the file's record drifting from
    the draw it describes.

    Both `sample()` calls run on the SAME generator, lower stratum first. Order
    is not cosmetic — reversing it yields a different 40.
    """
    findings: list[str] = []
    seed = witness.get("seed")
    if not isinstance(seed, int):
        return Draw((), 0, 0, 0, ran=False), [
            f"concept_witness_set.json: `seed` is {seed!r}, not an integer — the "
            "draw cannot be replayed, so the holdout cannot be shown to be the "
            "one that was drawn"
        ]

    excluded = set(CURATED_AT_DRAW) | {DEVELOPMENT_CASE}
    frame = sorted(
        root for root, rec in morphology.items()
        if len(root) == 3
        and normalize_root(root) in has_asl
        and rec.get("count", 0) >= MIN_OCCURRENCES
        and root not in excluded
    )
    lower = [r for r in frame if morphology[r]["count"] < STRATUM_BOUNDARY]
    upper = [r for r in frame if morphology[r]["count"] >= STRATUM_BOUNDARY]

    recorded_frame = (witness.get("frame") or {}).get("size")
    if recorded_frame is not None and recorded_frame != len(frame):
        findings.append(
            f"concept_witness_set.json: `frame.size` records {recorded_frame}, the "
            f"criteria reproduce {len(frame)} — the frame moved under the recorded "
            "draw, so the roots below are not the roots that were drawn"
        )

    strata = witness.get("strata")
    if not isinstance(strata, list) or len(strata) != 2:
        return Draw((), len(frame), len(lower), len(upper), ran=False), findings + [
            "concept_witness_set.json: `strata` must be exactly two entries, the "
            "lower one first — that order IS the draw order"
        ]

    for stratum, computed, label in ((strata[0], lower, "lower"),
                                     (strata[1], upper, "upper")):
        recorded = stratum.get("frame") if isinstance(stratum, dict) else None
        if recorded is not None and recorded != len(computed):
            findings.append(
                f"concept_witness_set.json: the {label} stratum records a frame of "
                f"{recorded}, the criteria reproduce {len(computed)}"
            )

    counts = [stratum.get("drawn") if isinstance(stratum, dict) else None
              for stratum in strata]
    if not all(isinstance(c, int) and c >= 0 for c in counts):
        return Draw((), len(frame), len(lower), len(upper), ran=False), findings + [
            f"concept_witness_set.json: `strata[].drawn` is {counts!r}, not two "
            "integers"
        ]
    if counts[0] > len(lower) or counts[1] > len(upper):
        return Draw((), len(frame), len(lower), len(upper), ran=False), findings + [
            f"concept_witness_set.json: the recorded draw wants "
            f"{counts[0]}+{counts[1]} roots from strata holding "
            f"{len(lower)}+{len(upper)} — the frame has shrunk below the draw"
        ]

    rng = random.Random(seed)
    drawn = tuple(sorted(rng.sample(lower, counts[0]))
                  + sorted(rng.sample(upper, counts[1])))
    return Draw(drawn, len(frame), len(lower), len(upper), ran=True), findings


def check_witness_set(witness: dict, morphology: dict[str, dict],
                      has_asl: frozenset[str]) -> tuple[Draw, list[str]]:
    """The 40 roots are the drawn ones, they are real, and none is contaminated."""
    draw, findings = replay_draw(witness, morphology, has_asl)

    entries = witness.get("roots")
    if not isinstance(entries, list) or not entries:
        return draw, findings + ["concept_witness_set.json: `roots` is missing or empty"]

    on_file = tuple(_text(e.get("root")) for e in entries if isinstance(e, dict))

    if draw.ran and on_file != draw.drawn:
        added = sorted(set(on_file) - set(draw.drawn))
        dropped = sorted(set(draw.drawn) - set(on_file))
        if added or dropped:
            findings.append(
                "concept_witness_set.json: the recorded draw does not reproduce the "
                "roots on file — a holdout re-rolled after the fact is not a "
                f"holdout.\n      on file, not drawn : {'، '.join(added) or '—'}\n"
                f"      drawn, not on file : {'، '.join(dropped) or '—'}"
            )
        else:
            findings.append(
                "concept_witness_set.json: the roots on file are the drawn set but "
                "in a different ORDER. The file's order is the draw order (lower "
                "stratum, then upper, each sorted); a reordering hides which "
                "stratum a root came from."
            )

    # 2. Contamination. A root used to build the rule, or to settle whether the
    #    table discriminates, cannot also be evidence that the table works.
    present = set(on_file)
    for root, why in (
        [(DEVELOPMENT_CASE, "the declared development case: the composition rule "
                            "was verified on it, so coverage measured on it proves "
                            "nothing")]
        + [(r, "already curated in root_cores.json before the draw") for r in CURATED_AT_DRAW]
        + [(r, "a §D13 collision-probe root") for r in PROBE_ROOTS]
    ):
        if root in present:
            findings.append(
                f"concept_witness_set.json: «{root}» is in the witness set and must "
                f"not be — {why}"
            )

    # 3. Every root is real and its recorded occurrence count still matches.
    seen: set[str] = set()
    for i, entry in enumerate(entries):
        where = f"concept_witness_set.json: roots[{i}]"
        if not isinstance(entry, dict):
            findings.append(f"{where} is not an object")
            continue
        root = _text(entry.get("root"))
        if not root:
            findings.append(f"{where} has no `root`")
            continue
        if root in seen:
            findings.append(f"{where}: «{root}» appears twice")
        seen.add(root)
        record = morphology.get(root)
        if record is None:
            findings.append(
                f"{where}: «{root}» is not a canonical QAC root key — a witness "
                "root that does not exist can never be confronted"
            )
            continue
        recorded = entry.get("occurrences")
        if recorded is not None and recorded != record.get("count"):
            findings.append(
                f"{where}: «{root}» records {recorded} occurrences, morphology.json "
                f"holds {record.get('count')}"
            )
    return draw, findings


# ── E. the metric gate (§D9 / §D11) ──────────────────────────────────────────
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

    @property
    def off_set(self) -> str:
        """Why `ضرب` never contributes, stated wherever the number is."""
        return (f"«{DEVELOPMENT_CASE}» is confronted and published like any other "
                f"root and contributes to neither half: it verified the "
                f"composition rule, so it cannot also test it.")


def _records(attestation: dict) -> dict[str, dict]:
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


def _moment(value) -> datetime | None:
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
                      witness_roots: tuple[str, ...]) -> tuple[Metric, list[str]]:
    """The freeze-before-generate ordering, then `k / 40` when it holds.

    The gate is the point, not the number. §D9's ordering is what makes "does the
    concept cover its uses" a question with an answer: a `uses[]` list written
    after the concept has been read shapes itself around the sentence, silently
    and in good faith. Nothing downstream can detect that, so it is detected here
    by refusing to print.
    """
    total = len(witness_roots)
    empty = Metric(total=total, recorded=0, k=0, signature=(0, 0), plain=(0, 0),
                   blocked=(), printable=False, note="")

    if attestation is None:
        return replace(empty, note=(
            "no attestation records yet; the metric is not printable. "
            f"{CONCEPT_ATTESTATION_JSON.relative_to(ROOT)} is written root by "
            "root, each root's `uses[]` committed BEFORE its concept is generated."
        )), []

    findings: list[str] = []
    records = _records(attestation)
    if not records:
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
                "committed BEFORE its concept is generated — that ordering is "
                "the only property the file has."
            )), []
        findings.append(
            "concept_attestation.json: exists but records no root — `roots` must "
            "be an object keyed by root (or a list of objects each carrying "
            "`root`). An EMPTY `roots` object is the skeleton and is accepted; "
            "an absent or malformed one is a file that failed to say anything."
        )
        return replace(empty, note="the record file carries no root."), findings

    witness = set(witness_roots)
    off_set = sorted(set(records) - witness)

    blocked: list[str] = []
    k = 0
    sig_k = sig_n = plain_k = plain_n = 0

    for root in witness_roots:
        record = records.get(root)
        if record is None:
            continue

        where = f"concept_attestation.json: «{root}»"
        frozen_at = _moment(record.get("uses_frozen_at"))
        recorded_at = _moment(record.get("concept_recorded_at"))

        # FROZEN, AWAITING GENERATION — the mandated intermediate state.
        # An absent `concept_recorded_at` is not a missing field; it is the
        # record saying the concept has not been generated, which is what the
        # commit that freezes `uses[]` is FOR.
        awaiting = not _text(record.get("concept_recorded_at"))
        if awaiting:
            if frozen_at is None:
                findings.append(
                    f"{where}: `uses_frozen_at` is missing or not an orderable "
                    "ISO-8601 timestamp. A record awaiting its concept still has "
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
                        f"no concept is recorded. A use judged before the concept "
                        f"exists was judged against nothing — leave it "
                        f"«{VERDICT_NOT_JUDGED}» until the concept is generated."
                    )
            continue

        if frozen_at is None or recorded_at is None:
            blocked.append(root)
            findings.append(
                f"{where}: `uses_frozen_at` / `concept_recorded_at` is missing or "
                "not an orderable ISO-8601 timestamp. The protocol's one claim is "
                "about ORDER; a record that cannot state its order has not made "
                "the claim."
            )
        elif frozen_at > recorded_at:
            blocked.append(root)
            findings.append(
                f"{where}: `uses[]` was frozen at {frozen_at.isoformat()}, AFTER "
                f"the concept was recorded at {recorded_at.isoformat()}. The list "
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
                    "concept IS recorded. Generation without judgement leaves a "
                    "root that can never reach `covers_all` and never appear as a "
                    "miss either — it would silently drop out of the denominator."
                )
            elif verdict not in USE_VERDICTS:
                findings.append(
                    f"{where}: uses[{j}] `verdict` is «{verdict}», expected one of "
                    f"{', '.join(USE_VERDICTS)} — there is no partial credit at "
                    "the use level either"
                )
            if verdict == "not_covered" and not _text(use.get("reason")):
                findings.append(
                    f"{where}: uses[{j}] is a miss with no `reason` — a miss is a "
                    "recorded result and carries its one line; it is never a "
                    "reason to edit the table"
                )

        covers_all = all(
            isinstance(u, dict) and _text(u.get("verdict")) == "covered" for u in uses
        )
        k += 1 if covers_all else 0
        if SIGNATURE_LETTERS & set(root):
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
        if isinstance(records.get(root), dict)
        and _text(records[root].get("concept_recorded_at"))
    )
    awaiting_roots = tuple(sorted(
        root for root in witness_roots
        if isinstance(records.get(root), dict)
        and not _text(records[root].get("concept_recorded_at"))
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
                "`uses[]` FROZEN and not one concept has been generated, so "
                "the metric is not printable — and that is the protocol "
                "working, not a gap. The freeze is committed as its own step "
                "so that it exists in the history before any concept does."
            )
        else:
            note = (
                f"{recorded} of {total} witness roots have a concept recorded"
                + (f" ({len(awaiting_roots)} frozen and awaiting generation)"
                   if awaiting_roots else "")
                + "; the metric is not printable yet. A `k` over a subset is not a "
                "smaller version of this measurement — it is a different one, and "
                "the design forbids reporting it as the result."
            )
        return replace(empty, recorded=recorded, note=note), findings

    if off_set:
        findings.append(
            "concept_attestation.json: record(s) for non-witness root(s) "
            f"{'، '.join(off_set)} — published like any other root, and counted "
            "in neither half of k / " + str(total)
        )

    return Metric(total=total, recorded=recorded, k=k,
                  signature=(sig_k, sig_n), plain=(plain_k, plain_n),
                  blocked=(), printable=True, note=""), findings


# ── the summary the report prints on a clean run ─────────────────────────────
@dataclass(frozen=True)
class Summary:
    """Figures read off the shipped files, never hardcoded.

    A hardcoded figure stops being true on the first curation batch, and these
    are the numbers the next one starts from.
    """

    rows: int
    features: int
    primitives: int
    attested: int
    hypothesis: int
    supported: int
    free_text_root_collisions: tuple[str, ...]


def summarize(rows: list[dict], root_keys: frozenset[str]) -> Summary:
    """Count the table, and record the free-text/root-key coincidences.

    The collisions are REPORTED rather than refused: see `check_primitive_table`
    for why a lemma set that happens to contain a real root key is Arabic doing
    what Arabic does, not a per-root exception. Printing them is what keeps the
    narrower reading of the no-root rule visible instead of assumed.
    """
    free_text = [c for c in TABLE_COLUMNS if c not in KEY_COLUMNS]
    collisions: list[str] = []
    for row in rows:
        for column in free_text:
            for value in _split_cell(_text(row.get(column))):
                if value in root_keys:
                    collisions.append(f"{value} (`{column}`)")
    statuses = [_text(r.get("status")) for r in rows]
    return Summary(
        rows=len(rows),
        features=len({_text(r.get("feature")) for r in rows if _text(r.get("feature"))}),
        primitives=len({_text(r.get("primitive")) for r in rows
                        if _text(r.get("primitive"))}),
        attested=statuses.count("attested"),
        hypothesis=statuses.count("hypothesis"),
        supported=sum(1 for r in rows if _text(r.get("support"))),
        free_text_root_collisions=tuple(dict.fromkeys(collisions)),
    )


# ── entry points ─────────────────────────────────────────────────────────────
def validate(data: Datasets | None = None) -> list[str]:
    """Every finding across the concept datasets, in file order. Empty == clean."""
    data = data or Datasets.load()
    root_keys = frozenset(data.morphology)
    _draw, witness_findings = check_witness_set(
        data.witness, data.morphology, data.maqayis_has_asl
    )
    _metric, metric_findings = check_attestation(data.attestation, data.witness_roots)
    return [
        *check_primitive_table(data.table, data.authority_pages, root_keys),
        *check_lock(data.lock, data.table_bytes, data.table, data.authority_pages),
        *witness_findings,
        *metric_findings,
    ]


def report(findings: list[str], summary: Summary, lock: dict, witness: dict,
           draw: Draw, metric: Metric) -> None:
    """Print the state of the datasets, then the findings when there are any.

    The summary prints even on a clean run: these are the figures the next
    curation batch starts from, and a clean validator that said nothing would
    leave them to be guessed.
    """
    print("=" * 64)
    print("CONCEPT DATASETS — validation report")
    print("=" * 64)
    print(f"  primitive table      : {summary.rows} rows / {summary.features} "
          f"features / {summary.primitives} primitives (cap {PRIMITIVE_CAP})")
    print(f"    attested           : {summary.attested:>3}  "
          "(a named authority states the mapping, at a resolvable page)")
    print(f"    hypothesis         : {summary.hypothesis:>3}  "
          "(the project asserts it and owns the claim)")
    print(f"    support citations  : {summary.supported:>3}  "
          "(rendered as SUPPORT, never as a row's authority)")
    if summary.free_text_root_collisions:
        print(f"    note               : {len(summary.free_text_root_collisions)} "
              "free-text cell(s) coincide with a QAC root key — "
              + "، ".join(summary.free_text_root_collisions))
        print("                         a lemma set is a containment vocabulary, "
              "not a key; the no-root")
        print("                         rule is enforced on `feature` and "
              "`primitive`, the only lookup columns.")
    print(f"  table freeze         : FROZEN at v{_text(lock.get('version')) or '?'} "
          f"(sha256 {_text(lock.get('sha256'))[:12] or '?'}…, since "
          f"{_text(lock.get('frozen_on')) or '?'})")

    print()
    print(f"  witness set          : {len(witness.get('roots') or [])} roots, seed "
          f"{witness.get('seed', '?')}, drawn {_text(witness.get('drawn_on')) or '?'}")
    if draw.ran:
        on_file = tuple(_text(e.get("root")) for e in witness.get("roots") or []
                        if isinstance(e, dict))
        verdict = ("reproduces the file exactly" if draw.drawn == on_file
                   else "DOES NOT reproduce the file")
        print(f"    draw replay        : frame {draw.frame} "
              f"({draw.lower} + {draw.upper}) → {verdict}")
    else:
        print("    draw replay        : could not be replayed — see the findings")
    print(f"    held out from      : «{DEVELOPMENT_CASE}», the {len(CURATED_AT_DRAW)} "
          f"roots curated at the draw, and the {len(PROBE_ROOTS)} §D13 probe roots")

    print()
    print(f"  ── the metric (§D11: k / {metric.total}, strict, no partial credit) ──")
    if metric.printable:
        print(f"  k / {metric.total}              : {metric.k} / {metric.total} "
              "roots whose concept covers EVERY frozen use")
        print(f"    with a signature letter ({''.join(sorted(SIGNATURE_LETTERS))}) : "
              f"{metric.signature[0]} / {metric.signature[1]}")
        print(f"    with none                        : "
              f"{metric.plain[0]} / {metric.plain[1]}")
        print("    the split is declared before the measurement and neither half "
              "is the result;")
        print("    the headline number hides the bias, the split is what exposes "
              "it.")
        for line in _wrap(metric.off_set, width=58):
            print(f"    {line}")
        print()
        for line in _wrap(WINDOW_RESERVATION, width=58):
            print(f"    {line}")
        print()
        for line in _wrap(AUDIT_CLAIM, width=58):
            print(f"    {line}")
    else:
        for line in _wrap(metric.note, width=58):
            print(f"  {line}")

    if not findings:
        print("\n  findings: none — the concept datasets are consistent.")
    else:
        print(f"\n  findings: {len(findings)}")
        for f in findings:
            print(f"    - {f}")
    print("=" * 64)


def _wrap(text: str, width: int) -> list[str]:
    """Soft-wrap a sentence for the report block; no dependency for four lines."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines


def main() -> int:
    data = Datasets.load()
    findings = validate(data)
    draw, _ = check_witness_set(data.witness, data.morphology, data.maqayis_has_asl)
    metric, _ = check_attestation(data.attestation, data.witness_roots)
    report(
        findings,
        summarize(data.table, frozenset(data.morphology)),
        data.lock,
        data.witness,
        draw,
        metric,
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
