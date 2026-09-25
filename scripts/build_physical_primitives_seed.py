#!/usr/bin/env python3
"""
build_physical_primitives_seed.py — OFFLINE seeder for the physics-first table.

Turns the tajwīd description in `data/references/arabic_letters_dataset.csv` into
the MECHANICAL half of the quality-to-notion table: the derived feature, the
letters that carry it, and its letter-coverage. `primitive`, `gloss_ar`,
`gloss_en`, `status`, `authority`, `pages`, `physical_basis`, `support` and
`lemmas` are the CURATOR's half and are emitted EMPTY — every one of them is a
reading of a physical fact, and this script has no way to read.

**This script cannot write the frozen table, and that is the point.**

The freeze is the whole method. The table is written against the FEATURE
vocabulary and locked by digest before the first root is composed, so that a root
which reads badly is a RESULT to record rather than a reason to edit a row. A
seed script able to overwrite it is a back-door around that freeze: one
`--out` typo, one re-run "to refresh the coverage numbers", and the curated
statuses, citations and lemma sets are gone — replaced by blanks that still
validate as a shape and no longer validate as scholarship. So:

  * the frozen table's path is **not importable from here** — the constant is
    never named and the file name never appears in this source, which
    `tests/test_physical_primitives.py` checks by reading these bytes;
  * `--out` refuses anything under `data/references/`, and refuses any path
    whose basename is the one the lock declares as its `target`;
  * the default destination is **stdout**, so a bare invocation produces text on
    a terminal and touches no file at all;
  * the emitted header is deliberately NOT the frozen table's header — it
    carries two derived columns (`letters`, `coverage`) the table does not
    have — so a seed cannot be renamed into place. It is a worklist.

**The reduction rule (§D2) is declared here, over the vocabulary, never over a
letter.** That ordering is what makes the exclusions principled rather than
convenient: `munfatiha` (24 of 28 letters) and `mustafila` (21 of 28) yield
nothing because each is the ABSENT member of a privative opposition, not because
a coverage threshold was drawn where it happened to help. A value recording a
scholarly dispute — `ء`'s `mahmusa/majhura (debated)` — yields nothing either: a
disputed fact is not a fact, and `ء` is left with `shadida` alone.

**The interpretive columns of the sheet are never read.** `arabic_letters_dataset.csv`
mixes two layers: a tajwīd description of the mouth, and one frozen
per-letter gloss written by a scholar. The gloss layer IS the first `/lexical`
engine, sitting in a CSV; reading it would reintroduce the defect this whole
change exists to remove. Only the three columns in `READ_COLUMNS` are touched,
selected by name, and a test reads this source to check the ban is enforced
rather than merely stated.

`makhraj_ar` IS mapped in v1.0.0, and this script reports its raw strings for
the curator's eye. The sheet holds 18 distinct مخرج strings for 28 letters, so a
table keyed on them would be a per-letter glossary arrived at by arithmetic —
which is why they are reduced to the five classical zones (حلق · أقصى اللسان ·
وسط اللسان · طرف اللسان · شفتان) and the ZONES are what the table maps. The draft
mapped nothing from them; §D13's collision probe proved that draft could not tell
ب from ج from د, and §D3's pre-declared fallback brought the zones in. The
reduction itself lives in `linguistics/lisan/concept/features.py`, not here: a
seed script reports what the sheet says, it does not own a rule.

Usage:
    python scripts/build_physical_primitives_seed.py             # CSV to stdout
    python scripts/build_physical_primitives_seed.py --out /tmp/seed.csv

The report always goes to STDERR, so `... > seed.csv` yields a clean file while
the coverage summary still reaches the terminal. That is the opposite of
`build_root_cores_seed.py`, where the report IS the product; here the product is
the rows.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from quran_data.paths import ARABIC_LETTERS_CSV, REFERENCES  # noqa: E402

# ── the sheet, read by NAME and nothing else ─────────────────────────────────
# `letter` is the row's identity (coverage is counted in letters), `sifat` is the
# only mapped input, `makhraj_ar` is carried unmapped for the curator to see.
# The sheet's two interpretive per-letter gloss columns are absent from this
# tuple, from this file, and from every module on this path — §D1's ban, enforced
# by a static test rather than by discipline.
READ_COLUMNS = ("letter", "makhraj_ar", "sifat")

# ── §D2: the reduction rule, stated over the vocabulary ──────────────────────
# EQUIPOLLENT — both/all members are positive articulatory states, so every
# member yields a feature. Three degrees of air obstruction, then air checked
# against air running.
EQUIPOLLENT: tuple[tuple[str, ...], ...] = (
    ("shadida", "mutawassita (bayniyya)", "rikhwa"),
    ("majhura", "mahmusa"),
)

# PRIVATIVE — the second member is DEFINED as the absence of the first
# (`انفتاح` is the absence of `إطباق`, `استفال` the absence of `استعلاء`), so
# only the marked member yields a feature. This is the classical structure of
# the صفات, not a judgement about these two values, which is precisely why it
# can exclude the sheet's two most frequent strings without anyone deciding they
# are inconvenient.
PRIVATIVE: tuple[tuple[str, str], ...] = (
    ("musta'liya", "mustafila"),
    ("mutbaqa", "munfatiha"),
)

# صفات لا ضد لها — each stands alone and each yields a feature.
NO_OPPOSITE: tuple[str, ...] = (
    "qalqala", "safir", "takrir", "tafashshi", "istitala", "inhiraf",
    "lin", "madd", "ghunna",
)

# A sheet value recording a scholarly DISPUTE yields nothing. `ء` is the only
# carrier today; it keeps `shadida` and therefore exactly one primitive.
DISPUTED: tuple[str, ...] = ("mahmusa/majhura (debated)",)

# A sheet value naming two features at once. `و` and `ي` are `rikhwa/madd`: both
# halves are real and both are in the vocabulary, so the cell yields BOTH rather
# than being read as a third, compound feature.
COMPOUND: dict[str, tuple[str, ...]] = {"rikhwa/madd": ("rikhwa", "madd")}

# The closed feature vocabulary, IN DECLARATION ORDER. That order is the emitted
# order and it is the classical grouping — the obstruction triad, the jahr/hams
# pair, the two marked privative members, then the صفات لا ضد لها. It is not
# rarity order: §D5's rarity rule orders primitives inside a composed concept,
# which is a different question from how a curator reads a worklist.
VOCABULARY: tuple[str, ...] = (
    tuple(member for group in EQUIPOLLENT for member in group)
    + tuple(marked for marked, _absent in PRIVATIVE)
    + NO_OPPOSITE
)

# The absent halves, flattened for lookup. Named so a finding can say WHICH
# opposition a value was excluded by.
ABSENT: dict[str, str] = {absent: marked for marked, absent in PRIVATIVE}

# The emitted header. Deliberately NOT the frozen table's header: `letters` and
# `coverage` are derived facts the table does not carry, so this file cannot be
# moved into place as the table. The curator's columns follow in the table's own
# order, so the two read side by side.
DERIVED_COLUMNS = ("feature", "letters", "coverage")
CURATOR_COLUMNS = (
    "primitive", "gloss_ar", "gloss_en", "status", "authority", "pages",
    "physical_basis", "support", "lemmas",
)
HEADER = DERIVED_COLUMNS + CURATOR_COLUMNS

# The sheet's own separator, reused for the `letters` cell.
CELL_SEP = ";"


# ── reduction ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Reduction:
    """What one raw `sifat` value yields, and why when it yields nothing.

    `known` separates «declared to yield nothing» from «the vocabulary has never
    heard of this». The second must never be silent: §D2's rule is stated over
    the vocabulary, so a value the vocabulary does not classify is a gap in the
    rule, and dropping it quietly would be the exact failure the rule exists to
    prevent — a feature excluded because nobody looked at it.
    """

    features: tuple[str, ...]
    reason: str        # why empty; "" when `features` is non-empty
    known: bool


def reduce_value(value: str) -> Reduction:
    """Apply §D2 to one raw `sifat` string."""
    value = value.strip()
    if not value:
        return Reduction((), "empty cell", known=True)
    if value in COMPOUND:
        return Reduction(COMPOUND[value], "", known=True)
    if value in DISPUTED:
        return Reduction(
            (), "records a scholarly dispute — a disputed fact is not a fact",
            known=True,
        )
    if value in ABSENT:
        return Reduction(
            (),
            f"absent member of the privative opposition with «{ABSENT[value]}»",
            known=True,
        )
    if value in VOCABULARY:
        return Reduction((value,), "", known=True)
    return Reduction(
        (value,),
        "NOT in the declared vocabulary — classify it in EQUIPOLLENT, PRIVATIVE, "
        "NO_OPPOSITE or DISPUTED before curating a row for it",
        known=False,
    )


def _split_cell(value: str) -> list[str]:
    """Split a ';'-separated sheet cell, trimmed, empties dropped."""
    return [part.strip() for part in (value or "").split(CELL_SEP) if part.strip()]


# ── the plan ─────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SeedRow:
    """One emitted row: a derived feature and the letters carrying it."""

    feature: str
    letters: tuple[str, ...]
    declared: bool      # in VOCABULARY, as opposed to met in the sheet unclassified

    @property
    def coverage(self) -> int:
        return len(self.letters)


@dataclass(frozen=True)
class SeedPlan:
    """What a run emits, computed without touching the destination.

    `rows` is in declaration order, with any unclassified feature appended at the
    end; `makhraj` is the unmapped مخرج profile per letter (§D3); `excluded`
    counts the raw values that yielded nothing, by reason; `silent` names letters
    that yielded no feature at all — empty on today's sheet, and a finding for
    the curator if it ever is not.
    """

    rows: tuple[SeedRow, ...]
    makhraj: tuple[tuple[str, str], ...]
    excluded: Counter
    silent: tuple[str, ...]
    letters_seen: int

    @property
    def unclassified(self) -> tuple[SeedRow, ...]:
        return tuple(r for r in self.rows if not r.declared)


def build_seed() -> SeedPlan:
    """Reduce every letter's `sifat` and group the result by feature."""
    sheet = loaders.arabic_letters()

    carriers: dict[str, list[str]] = {}
    makhraj: list[tuple[str, str]] = []
    excluded: Counter = Counter()
    silent: list[str] = []

    for row in sheet:
        letter = (row.get("letter") or "").strip()
        if not letter:
            continue
        makhraj.append((letter, (row.get("makhraj_ar") or "").strip()))
        found = 0
        for raw in _split_cell(row.get("sifat") or ""):
            red = reduce_value(raw)
            if not red.features:
                excluded[f"{raw} — {red.reason}"] += 1
                continue
            for feature in red.features:
                carriers.setdefault(feature, []).append(letter)
                found += 1
        if not found:
            silent.append(letter)

    # Declaration order first, then anything the sheet carried that the
    # vocabulary does not classify — appended rather than dropped, and reported
    # loudly by `report()`.
    ordered = [f for f in VOCABULARY if f in carriers]
    ordered += [f for f in carriers if f not in VOCABULARY]

    rows = tuple(
        SeedRow(feature=f, letters=tuple(carriers[f]), declared=f in VOCABULARY)
        for f in ordered
    )
    return SeedPlan(
        rows=rows,
        makhraj=tuple(makhraj),
        excluded=excluded,
        silent=tuple(silent),
        letters_seen=len(makhraj),
    )


# ── emission ─────────────────────────────────────────────────────────────────
def render(plan: SeedPlan) -> str:
    """The seed as CSV text: derived columns filled, curator columns empty."""
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(HEADER)
    for row in plan.rows:
        writer.writerow(
            [row.feature, CELL_SEP.join(row.letters), row.coverage]
            + [""] * len(CURATOR_COLUMNS)
        )
    return buf.getvalue()


def _frozen_target_name() -> str:
    """The basename the lock declares as its target, read from the LOCK.

    Read rather than written down, so this guard tracks the freeze instead of a
    string that can fall out of step with it — and so the frozen table's own file
    name never appears in this source, which is what a test asserts.

    A missing or unreadable lock degrades to "" and the directory guard below
    carries the refusal on its own; it covers the same path and more.
    """
    try:
        target = (loaders.physical_primitives_lock().get("target") or "").strip()
    except (loaders.DatasetMissing, OSError, ValueError):
        return ""
    return PurePosixPath(target).name if target else ""


def refuse_destination(out: Path) -> str | None:
    """Why `--out` may not be written, or None when it may.

    Two independent refusals, because one of them can be defeated by a rename and
    the other by a move:

      1. Nothing under `data/references/` is ever written by a seed script. That
         directory holds curated scholarship — every file in it carries a human
         decision — and a generator has no business emitting into it.
      2. Nothing carrying the frozen table's own basename, wherever it sits, so
         `--out ./physical_…csv` in a scratch directory still reads as an attempt
         at the table and is refused before it becomes a habit.
    """
    resolved = out.expanduser().resolve()
    references = REFERENCES.resolve()
    if resolved == references or references in resolved.parents:
        return (
            f"refusing --out {out}: nothing under "
            f"{references.relative_to(ROOT)}/ is written by a seed script. That "
            "directory holds curated scholarship, and the physics-first table in "
            "it is frozen by digest BEFORE the first root is composed — a "
            "generator that can overwrite it is a back-door around the freeze."
        )
    frozen = _frozen_target_name()
    if frozen and resolved.name == frozen:
        return (
            f"refusing --out {out}: «{frozen}» is the basename the lock declares "
            "as its frozen target. A seed is a worklist; it never becomes the "
            "table, not even under a different directory."
        )
    return None


def report(plan: SeedPlan, destination: str) -> None:
    """Coverage summary, on STDERR so the CSV on stdout stays pipeable."""
    def say(line: str = "") -> None:
        print(line, file=sys.stderr)

    say("=" * 64)
    say("PHYSICAL PRIMITIVES SEED — worklist, never the frozen table")
    say("=" * 64)
    say(f"  source sheet      : {ARABIC_LETTERS_CSV.relative_to(ROOT)} "
        f"[{', '.join(READ_COLUMNS)}]")
    say(f"  destination       : {destination}")
    say(f"  letters read      : {plan.letters_seen}")
    say(f"  features derived  : {len(plan.rows)} "
        f"(declaration order; curator columns left empty)")
    say()
    say("  feature                        letters  carriers")
    say("  " + "-" * 60)
    for row in plan.rows:
        mark = " " if row.declared else "!"
        say(f"  {mark}{row.feature:<29}{row.coverage:>5}   "
            + CELL_SEP.join(row.letters))
    say()
    say(f"  values yielding nothing (§D2): {sum(plan.excluded.values())} "
        "occurrence(s)")
    for reason, count in sorted(plan.excluded.items(), key=lambda kv: (-kv[1], kv[0])):
        say(f"    {count:>5}  {reason}")

    if plan.unclassified:
        say()
        say(f"  UNCLASSIFIED      : {len(plan.unclassified)} feature(s) the sheet "
            "carries and §D2's vocabulary does not know")
        for row in plan.unclassified:
            say(f"    ! {row.feature} ({row.coverage} letter(s))")
        say("    emitted anyway, marked «!» above: a value dropped for being "
            "unrecognised is exactly")
        say("    the silent exclusion the vocabulary-first rule exists to "
            "prevent. Classify it first.")

    if plan.silent:
        say()
        say(f"  SILENT LETTERS    : {len(plan.silent)} — "
            + CELL_SEP.join(plan.silent))
        say("    a letter yielding no feature yields no primitive, so every "
            "concept containing it is partial.")

    say()
    say("  مخرج, as the sheet writes it — reduced to five classical zones by "
        "features.py, never here:")
    zones = Counter(zone for _letter, zone in plan.makhraj if zone)
    say(f"    {len(zones)} distinct مخرج string(s) for {plan.letters_seen} letters")

    say()
    say("  `primitive`, `gloss_ar`, `gloss_en`, `status`, `authority`, `pages`,")
    say("  `physical_basis`, `support` and `lemmas` are EMPTY by design — each is "
        "a reading")
    say("  of a physical fact, and this script cannot read. "
        "`scripts/validate_concept_datasets.py`")
    say("  refuses a row that left them that way, so a seed cannot ship as a "
        "finished table.")
    say("=" * 64)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Emit the feature worklist for the physics-first primitive "
                    "table (offline; cannot write the frozen table).")
    ap.add_argument(
        "--out", metavar="PATH", default=None,
        help="write the CSV here instead of stdout; refused for any path under "
             "data/references/ or carrying the frozen table's basename",
    )
    args = ap.parse_args()

    plan = build_seed()
    text = render(plan)

    if args.out is None:
        sys.stdout.write(text)
        destination = "- (stdout)"
    else:
        out = Path(args.out)
        refusal = refuse_destination(out)
        if refusal:
            print(refusal, file=sys.stderr)
            return 2
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        destination = str(out)

    report(plan, destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
