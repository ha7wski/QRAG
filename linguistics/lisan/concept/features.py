"""
features.py — the tajwīd sheet reduced to a closed, letter-independent vocabulary.

Reads TWO columns of `arabic_letters_dataset.csv` and nothing else: `makhraj_ar`
and `sifat`. Both are description of the mouth — `ب` is
`shadida; majhura; mustafila; munfatiha; qalqala`, which is a fact about lips and
air, not a reading of anything.

**The interpretive columns of that same file are banned from this path**, and the
ban is the reason this package exists. They hold one frozen gloss per letter —
«the lips seal and hold air, then burst — gesture of enclosing and then releasing
what is contained» — which is the FIRST `/lexical` engine, verbatim, sitting in a
CSV. Reading them here would reintroduce the original defect wearing the new
engine's name. So the columns are selected BY EXPLICIT NAME below, never by
iterating the row dict, and a test reads this package's source to assert the
banned names appear nowhere in it. Selecting by name is what makes the ban a
property of the code rather than of whoever last edited it.

**The reduction rule is posed over the VOCABULARY, never over a letter.** That is
the whole guarantee: a rule stated over letters is a per-letter decision with a
rule's grammar, and it could be tuned root by root without anyone noticing.

    privative opposition   one member is defined as the ABSENCE of the other —
                           `انفتاح` is the absence of `إطباق`, `استفال` the
                           absence of `استعلاء`. The absent member yields
                           NOTHING. This is what excludes `munfatiha` (24 of 28
                           letters) and `mustafila` (21 of 28), and it excludes
                           them by their classical structure rather than by a
                           coverage threshold drawn where it happened to be
                           convenient.
    equipollent opposition both members are positive articulatory states —
                           `شدة`/`توسط`/`رخاوة` (three degrees of obstruction),
                           `جهر`/`همس` (air checked vs. air running). EVERY
                           member yields a feature, including `mahmusa`, which
                           10 of 28 letters carry.
    صفة لا ضد لها          yields a feature: `قلقلة`, `صفير`, `تكرير`, `تفشي`,
                           `استطالة`, `انحراف`, `لين`, `غنة`.
    unresolved value       yields NOTHING. `ء` carries
                           `mahmusa/majhura (debated)`; a disputed fact is not a
                           fact, and `ء` is left with `شدة` alone — exactly one
                           feature, which is a result and not an oversight.

Nothing is silently discarded: a dropped raw value comes back in
`LetterProfile.dropped` with the rule that dropped it, so the profile on screen
accounts for every string the sheet wrote.

**`makhraj_ar` IS mapped, and the draft that left it unmapped was wrong.** The
first version of this module carried the مخرج through untouched and said so at
length: a table keyed on it «would be a per-letter glossary reached by arithmetic
instead of by prose». §D3 of the design chose that on two grounds — the primitive
cap had no room, and the acceptance case `ضرب` cleared the bar on the صفات alone
— and it declared IN ADVANCE what would overturn it: if §D13's collision probe
found concepts colliding where the attested aṣl diverge, mapping the five zones
becomes table **v1.0.0**, not a later lock bump.

The probe ran on the ṣifāt-only draft, before a single witness root was curated,
and returned `identical` on **5 of 5** qualifying comparisons — حرب=حرج=حرد,
تبر=كبر, كود=كيد. That draft mapped 28 letters onto 18 profiles: it could not tell
`ب` from `ج` from `د`, and three roots whose aṣl Ibn Fāris separates came back as
one concept. The verdict is committed in `data/references/concept_collision_probe.json`
and the superseded draft's digest is recorded in the table's own lock, so the
replacement can be audited instead of taken on trust. The fallback was pre-declared,
so taking it is not a repair made after seeing a number — it is the branch the
design had already written down.

Two corrections to the design text, while this paragraph is being rewritten. §D3
says the sheet holds **23** distinct مخرج strings; it holds **18** — the figure was
a factual error and is enumerated below where the reduction is declared, so that a
reviewer can count them rather than believe either number. And §D3's *Consequence,
stated up front* — that `ب`'s closure comes from the lips and so could not be
carried — is now only half true: `ب` leads with `بُرُوز`, the outermost locus on the
articulation axis. The loss booked there is partly recovered, and it was NOT
arranged: `بُرُوز` glosses a POSITION on the inner→outer axis, not a closure, and
nothing in the zone rows was tuned toward `ضرب`.

What the zones assert is one graded series — غَوْر · أَصْل · وَسَط · طَرَف · بُرُوز —
and nothing more: where in the mouth the sound is made, read as a position between
inside and outside. They do not read a meaning off a place of articulation.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402
from linguistics.lisan.harness.letters import HAMZA_CARRIERS  # noqa: E402

# The sheet columns this path may read, named once so the ban above is checkable
# by reading this file. A `row.get(...)` over an unnamed key, or a loop over
# `row.items()`, would make the ban depend on what the CSV happens to contain.
_COLUMN_LETTER = "letter"
_COLUMN_MAKHRAJ = "makhraj_ar"
_COLUMN_SIFAT = "sifat"

# The closed feature vocabulary: 21 members, in the declaration order of
# `physical_primitives.csv` — the 16 ṣifāt features first, then the five مخرج
# zones. The order is the table's and the split is the table's: a reader
# comparing the two files reads them in one order, and the zones sit last
# because they were added last, by the probe recorded in the docstring.
#
# Declared literally rather than derived at import time, for two reasons. A
# module constant must not open a file — importing `quran_data` opens nothing and
# this package keeps that discipline. And "closed" has to mean something: a
# vocabulary recomputed from the sheet on every run would silently grow the day
# the sheet gains a value, which is precisely the drift `_derive` raises on
# below. The set of these names IS the set the sheet yields under the rule.
FEATURE_VOCABULARY: tuple[str, ...] = (
    # ── the 16 ṣifāt features, from the `sifat` column ────────────────────────
    "shadida",
    "mutawassita (bayniyya)",
    "rikhwa",
    "majhura",
    "mahmusa",
    "musta'liya",
    "mutbaqa",
    "qalqala",
    "safir",
    "takrir",
    "tafashshi",
    "istitala",
    "inhiraf",
    "lin",
    "madd",
    "ghunna",
    # ── the 5 مخرج zones, reduced from the `makhraj_ar` column ────────────────
    # Inner → outer, which is the order of the series they assert.
    "makhraj:halq",
    "makhraj:aqsa_al_lisan",
    "makhraj:wasat_al_lisan",
    "makhraj:taraf_al_lisan",
    "makhraj:shafatan",
)

# ── the مخرج reduction: 18 sheet strings → 5 classical zones ─────────────────
#
# Declared as an ordered table of (substring, zone) rather than as a chain of
# `if`s inside a function, for the same reason `PRIVATIVE_ABSENT` is a set: a
# reducer written as control flow is audited by reading code, a reducer written
# as data is audited by reading five lines against the classical مخارج.
#
# THE SHEET'S 18 STRINGS, ENUMERATED, so the mapping can be checked without
# running anything. (§D3 of the design says 23; that is a factual error — the
# sheet holds 18. Counting the rows below is the check.)
#
#   → makhraj:halq              (6 letters)
#       أقصى الحلق                         ء ه
#       وسط الحلق                          ح ع
#       أدنى الحلق                         خ غ
#   → makhraj:aqsa_al_lisan     (2)
#       أقصى اللسان مع الحنك اللين          ق
#       أقصى اللسان أسفل من مخرج القاف      ك
#   → makhraj:wasat_al_lisan    (3)
#       وسط اللسان مع وسط الحنك             ج ش
#       وسط اللسان (حرف علة)                ي
#   → makhraj:shafatan          (4)
#       الشفتان                            ب
#       الشفتان مع الغنة                   م
#       الشفتان (حرف علة)                  و
#       باطن الشفة السفلى مع الثنايا        ف
#   → makhraj:taraf_al_lisan    (13, the fallback)
#       طرف اللسان وأصول الثنايا            ت د ط
#       طرف اللسان وأطراف الثنايا           ث ذ ظ
#       طرف اللسان مع ما يليه من اللثة      ر
#       طرف اللسان وفويق الثنايا السفلى     ز س ص
#       طرف اللسان مع الغنة                 ن
#       حافة اللسان مع الأضراس              ض
#       حافة اللسان مع ما يحاذيها من اللثة  ل
#
#   6 + 2 + 3 + 4 + 13 = 28.
#
# **حافة اللسان is grouped with طرف اللسان, and that is a stated curation
# decision, not an oversight.** §D3's cut names five zones and حافة is not one of
# them; the front-of-tongue region is therefore taken WHOLE. The alternative — a
# sixth zone for the two edge letters — would be choosing the granularity by its
# result, which is the move this whole design exists to refuse. Recorded with it:
# the merge costs nothing measurable. `ض` owns `istitala` and `ل` owns `inhiraf`,
# so both already carry a ṣifa no other letter carries and neither is merged into
# any other profile by sharing a zone with ت د ط.
#
# **The ORDER of these rules is load-bearing.** They are tested in sequence and
# the FIRST match wins, so `الشفتان` must be tested before falling through to
# طرف اللسان; `_zone` additionally asserts that no string matches two rules, so a
# future sheet edit that made the order decide an outcome fails loudly instead of
# resolving by position. On today's sheet the rules are in fact disjoint — the
# assertion holds on all 18 strings — and the order is what keeps that a checked
# property rather than a lucky one.
MAKHRAJ_ZONE_RULES: tuple[tuple[str, str], ...] = (
    ("الحلق", "makhraj:halq"),
    ("أقصى اللسان", "makhraj:aqsa_al_lisan"),
    ("وسط اللسان", "makhraj:wasat_al_lisan"),
    ("الشفتان", "makhraj:shafatan"),
    ("الشفة", "makhraj:shafatan"),
)

# Everything the five rules above do not claim is the front of the tongue: the
# ثنايا rows, the لثة rows, the two حافة rows and `ن`'s. A fallback rather than a
# sixth rule listing seven substrings, because the zone is one anatomical region
# and the sheet spells it a different way for nearly every letter in it.
MAKHRAJ_ZONE_FALLBACK = "makhraj:taraf_al_lisan"

# The absent member of a privative opposition. Yields nothing — see the rule
# above. Written as data, not as an `if`, so the exclusion is one list a reviewer
# can read against the classical صفات instead of a branch buried in a parser.
PRIVATIVE_ABSENT: frozenset[str] = frozenset({"munfatiha", "mustafila"})

# Values recording a scholarly dispute. `ء`'s جهر/همس is the only one on today's
# sheet. Kept as a set rather than special-cased on `ء`, because the rule is
# about the value and not about the letter that happens to carry it.
DISPUTED: frozenset[str] = frozenset({"mahmusa/majhura (debated)"})

# Sheet cells naming two features at once. `و` and `ي` are `rikhwa/madd`: they run
# continuously AND prolong, and both are real, positive states. Splitting them
# yields both features in the declared order; collapsing them to one would drop a
# مَدّ the sheet actually states.
COMPOUND_VALUES: dict[str, tuple[str, ...]] = {
    "rikhwa/madd": ("rikhwa", "madd"),
}

# Hamza carriers → the bare `ء` row of the sheet, which is where their phonetic
# description lives. 139 letter positions over 138 QAC root keys are a seat.
#
# **Do NOT "simplify" this into `arabic_text.fold_carrier`.** The design text says
# to fold with it and the design text is wrong on this point: `fold_carrier` maps
# أ→ا, ؤ→و, ئ→ي, آ→ا — toward the CARRIER, deleting the hamza. The sheet is keyed
# on the hamza, so folding that way resolves every seat to a letter that is not in
# the 28-letter sheet at all (`ا`) or to the wrong one (`و`, `ي`), and the failure
# is silent in the worst way: `ا` is already the documented silent case, so all 138
# roots would come back `partial` with a plausible-looking reason instead of
# raising. The explicit map is the correct primitive here and the obvious helper
# does the opposite of what this path needs.
#
# Four entries, as `design.md` §D7 names them. `إ` and `ٱ` are deliberately absent:
# neither occurs in a QAC root key (the 1656 keys use 31 distinct characters, and
# those two are not among them), so adding them would be coverage for a case that
# does not exist, in a map whose whole job is to be checkable at a glance.
# `HAMZA_CARRIERS` itself is imported above from `linguistics/lisan/harness/letters.py`,
# so that a later letter table resolves a seat the same way without importing this
# engine.

# Why a raw value produced no feature, as `DroppedValue.rule` names it.
RULE_PRIVATIVE_ABSENT = "privative-absent"
RULE_DISPUTED = "disputed"


@dataclass(frozen=True)
class DroppedValue:
    """A raw `sifat` value the reduction rule refused, and which rule refused it.

    Returned, never swallowed. A profile that showed only what survived would let
    a sheet edit change a letter's reading with no trace on screen; carrying the
    refusal means the displayed profile accounts for every string the CSV wrote.
    """

    value: str
    rule: str


@dataclass(frozen=True)
class LetterProfile:
    """One sheet letter's physical description, reduced but not interpreted.

    `letter` is the SHEET's glyph, not the caller's: a hamza seat resolves here to
    `ء`, so a profile always names the row it actually came from.

    `makhraj_ar` is the sheet's own string, carried unchanged — it is what the
    page displays, and it says more than a zone does. `zone` is that string
    reduced to one of the five classical zones, and it is the member of
    `FEATURE_VOCABULARY` the مخرج contributes.

    `features` holds the ṣifāt features in SHEET ORDER — the order the CSV cell
    writes them — followed by `zone`, appended last. The order matters twice
    over: it is the order `physical_primitives.csv` declares, so the two files
    read the same way, and `compose.py` breaks coverage ties on declaration index,
    so «appended last» is a statement about ranking and not only about layout.
    Every member is in `FEATURE_VOCABULARY`.
    """

    letter: str
    makhraj_ar: str
    zone: str
    sifat_raw: tuple[str, ...]
    features: tuple[str, ...]
    dropped: tuple[DroppedValue, ...]


def _split_sifat(cell: str) -> tuple[str, ...]:
    """Split a ';'-separated `sifat` cell into trimmed, non-empty raw values."""
    return tuple(part.strip() for part in (cell or "").split(";") if part.strip())


def _zone(makhraj_ar: str) -> str:
    """Reduce one sheet `makhraj_ar` string to one of the five classical zones.

    Rules are tested in declaration order and the first match wins; everything
    unclaimed falls to `MAKHRAJ_ZONE_FALLBACK`. Every string therefore resolves,
    and resolves to EXACTLY ONE zone — which is asserted rather than assumed: a
    string matching two rules would make the answer depend on the order of the
    table above, and an ordering that silently decides an outcome is precisely the
    kind of undeclared rule this package is built to refuse. On today's 18 strings
    the rules are disjoint and the assertion never fires.
    """
    matched = [zone for substring, zone in MAKHRAJ_ZONE_RULES if substring in makhraj_ar]
    distinct = tuple(dict.fromkeys(matched))
    if len(distinct) > 1:
        raise ValueError(
            f"The مخرج {makhraj_ar!r} matches {len(distinct)} zone rules "
            f"({', '.join(distinct)}). A مخرج belongs to one zone: two matches "
            f"would make the reduction depend on the order of MAKHRAJ_ZONE_RULES, "
            f"which is an undeclared rule deciding a reading. Narrow a substring, "
            f"do not reorder the table."
        )
    return distinct[0] if distinct else MAKHRAJ_ZONE_FALLBACK


def _derive(
    sifat_raw: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[DroppedValue, ...]]:
    """Apply the reduction rule to one letter's raw values, in sheet order.

    Raises on a value the closed vocabulary does not contain. The sheet is
    read-only input to this capability, so an unknown صفة means someone edited it
    — and the loud failure is the point: silently ignoring the value would leave a
    letter quietly poorer than the sheet says it is, which reads as a modelling
    choice rather than as an accident.
    """
    features: list[str] = []
    dropped: list[DroppedValue] = []
    for value in sifat_raw:
        if value in PRIVATIVE_ABSENT:
            dropped.append(DroppedValue(value, RULE_PRIVATIVE_ABSENT))
            continue
        if value in DISPUTED:
            dropped.append(DroppedValue(value, RULE_DISPUTED))
            continue
        for feature in COMPOUND_VALUES.get(value, (value,)):
            if feature not in FEATURE_VOCABULARY:
                raise ValueError(
                    f"arabic_letters_dataset.csv declares the sifa {feature!r}, which "
                    f"is not in the closed feature vocabulary. The vocabulary is "
                    f"closed on purpose: either the sheet was edited, or the value "
                    f"belongs in PRIVATIVE_ABSENT / DISPUTED / COMPOUND_VALUES by a "
                    f"rule stated over the vocabulary — never over the letter that "
                    f"happens to carry it."
                )
            features.append(feature)
    return tuple(features), tuple(dropped)


@lru_cache(maxsize=1)
def letter_profiles() -> dict[str, LetterProfile]:
    """The 28 sheet letters, keyed by glyph. Parsed once per process.

    Every letter yields at least one feature — the table leaves none empty, and
    `ء` is the floor at exactly one. A letter that reduced to nothing would be a
    silent hole in the composition, so it raises here instead.
    """
    profiles: dict[str, LetterProfile] = {}
    for row in loaders.arabic_letters():
        letter = (row.get(_COLUMN_LETTER) or "").strip()
        if not letter:
            continue
        sifat_raw = _split_sifat(row.get(_COLUMN_SIFAT, ""))
        features, dropped = _derive(sifat_raw)
        if not features:
            raise ValueError(
                f"The letter {letter!r} reduces to no feature at all. Every one of "
                f"the 28 letters carries at least one; a silent letter here would "
                f"become a silent position in a concept with no reason attached."
            )
        makhraj_ar = (row.get(_COLUMN_MAKHRAJ) or "").strip()
        zone = _zone(makhraj_ar)
        profiles[letter] = LetterProfile(
            letter=letter,
            makhraj_ar=makhraj_ar,
            zone=zone,
            sifat_raw=sifat_raw,
            # The zone is appended AFTER the ṣifāt, which is the order
            # `physical_primitives.csv` declares its rows in. Not interleaved and
            # not prepended: the sheet states the ṣifāt as a list and the مخرج as
            # a separate column, and the reduction keeps that shape visible.
            features=features + (zone,),
            dropped=dropped,
        )
    return profiles


def sheet_letter(letter: str) -> str | None:
    """Resolve a root-key letter to the sheet glyph that describes it.

    A letter the sheet holds returns itself. A hamza seat returns `ء` through
    `HAMZA_CARRIERS` — read its comment before touching this. Anything else
    returns None, and on today's corpus that is the bare `ا` of `اني`, `اول`,
    `هاء` and `هات`: it is not one of the 28 and has no مخرج of its own, so it
    describes nothing. None means «no row», never «default row» — the caller
    reports the gap rather than filling it.
    """
    profiles = letter_profiles()
    if letter in profiles:
        return letter
    folded = HAMZA_CARRIERS.get(letter)
    if folded is not None and folded in profiles:
        return folded
    return None


def profile_for(letter: str) -> LetterProfile | None:
    """The profile describing a root-key letter, or None if the sheet has no row."""
    glyph = sheet_letter(letter)
    return letter_profiles().get(glyph) if glyph is not None else None


if __name__ == "__main__":
    profiles = letter_profiles()
    print(f"{len(profiles)} letters, {len(FEATURE_VOCABULARY)} features "
          f"in the vocabulary")
    zones: dict[str, list[str]] = {}
    for glyph, profile in profiles.items():
        dropped = ", ".join(f"{d.value} [{d.rule}]" for d in profile.dropped)
        zones.setdefault(profile.zone, []).append(glyph)
        print(f"  {glyph} ({profile.makhraj_ar}) -> {' · '.join(profile.features)}"
              + (f"    dropped: {dropped}" if dropped else ""))
    print(f"{len({p.makhraj_ar for p in profiles.values()})} مخرج strings "
          f"-> {len(zones)} zones")
    for zone, glyphs in zones.items():
        print(f"  {zone:<26} {len(glyphs):>2}  {' '.join(glyphs)}")
    for probe in ("أ", "ؤ", "ا", "ض"):
        print(f"  sheet_letter({probe!r}) = {sheet_letter(probe)!r}")
