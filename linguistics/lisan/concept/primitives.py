"""
primitives.py — the frozen quality-to-notion table, keyed on features alone.

One row per (physical feature, primitive) in `physical_primitives.csv`: 21 rows
over the 21-member feature vocabulary — the 16 ṣifāt features plus the five
classical مخرج zones — mapping onto **20** distinct primitives. The single merge
is `musta'liya` + `mutbaqa` → `ضَخامة`, and it is what brings the count to exactly
20 rather than 21.

**The vocabulary is capped at 20 and the cap is enforced here, at load.** A richer
table explains everything and therefore nothing: with enough primitives every root
reads well, and «it reads well» stops being evidence of anything. The cap is the
reason `k / 40` can come back low — which is a result — instead of coming back
high for free. That reason is unchanged by the number; what changed is the number.

**THE TABLE IS KEYED ON FEATURES ONLY.** Neither `PrimitiveTable` nor any function
in this module accepts, carries, stores or returns a root key, and there is no
mechanism by which a root can override a row. That is not an accident of the
current shape, it is the invariant: a per-root exception is how a mapping table
becomes a per-root glossary one plausible special case at a time, and a test
inspects the signatures here so the property has to be broken deliberately.

**A row that reads badly on a root is never a reason to edit the row.** The table
moves only through a new `physical_primitives.lock.json` version justified by a
**feature-level** authority. A root whose concept misses its attested aṣl is a
recorded miss — a result — and editing the table to absorb it would be writing the
evidence to fit the conclusion, which is the failure mode this whole change is
built around avoiding.

**Every row declares whose claim it is.** `status` is `attested` (a named
authority states this quality-to-notion mapping, at a real page) or `hypothesis`
(the project asserts it; the *physical* fact in `physical_basis` is uncontested
tajwīd). All 21 rows ship as `hypothesis`, because no known source tabulates the
صفات — or the مخارج — into a general mapping: Ibn Jinnī states the principle and
illustrates it on particular cases, Ḥasan ʿAbbās gives senses per LETTER rather
than per صفة. Saying so per row is the condition under which the metric can
falsify the table: a row wearing a borrowed citation could always blame its
failure on the source. The `status` travels with every hit so the page can say
which is which.

**Coverage is derived here and never stored.** `coverage(primitive)` counts the
sheet letters whose DEDUPED primitive set contains it — deduped, because `ص ض ط ظ`
carry `musta'liya` AND `mutbaqa` and both map to `ضَخامة`, so counting rows would
report 11 letters for a primitive that 7 letters carry. Storing the number in the
CSV would freeze a figure derived from a *different* file, and the day the sheet
moved the two would disagree with nothing to say so.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402

from linguistics.lisan.concept import features  # noqa: E402

# The closed vocabulary's ceiling, enforced below rather than trusted.
#
# **Raised from 15 to 20 deliberately, to admit the five مخرج zones.** The brief
# said «une quinzaine maximum» and the ṣifāt alone filled that exactly; §D3 cited
# the cap as one of its two reasons for leaving the مخرج unmapped. §D13's
# collision probe then returned `identical` on 5 of 5 qualifying comparisons —
# the ṣifāt-only table mapped 28 letters onto 18 profiles — and §D3 had declared
# in advance that this outcome makes the zones v1.0.0. Admitting them costs five
# primitives and the ceiling moved by exactly five.
#
# **Why raising it by five is not the same as removing it.** The cap exists
# against ARBITRARY enrichment: a vocabulary that grows whenever a root reads
# badly ends up explaining everything and therefore nothing. What came in is not
# five free parameters — it is one CLOSED CLASSICAL PARTITION of the mouth, five
# zones covering all 28 letters exactly once, fixed by the tajwīd literature and
# not by this project. There is no sixth zone to reach for the next time a root
# disappoints, and «حافة اللسان as its own zone» was available and refused for
# precisely that reason (see `features.MAKHRAJ_ZONE_RULES`). A cap that admits a
# named partition whole, once, on a pre-declared trigger is still a cap; a cap
# raised by one row to make a reading work would not be.
MAX_PRIMITIVES = 20

_STATUS_ATTESTED = "attested"
_STATUS_HYPOTHESIS = "hypothesis"


def _split_lemmas(cell: str) -> tuple[str, ...]:
    """Split the ';'-separated `lemmas` cell into trimmed, non-empty entries."""
    return tuple(part.strip() for part in (cell or "").split(";") if part.strip())


@dataclass(frozen=True)
class PrimitiveRow:
    """One (feature → primitive) mapping, with the evidence it declares.

    `lemmas` is the primitive's declared word family. It exists for the optional
    phrasing pass's containment check — a generated sentence may only use words
    that map back to a realised primitive — and is carried here so that check can
    never be run against a list assembled somewhere else.

    `declaration_index` is the row's position in the CSV. It is load-bearing, not
    bookkeeping: it breaks coverage ties in the composition order, so ties fall to
    the curator's own ordering rather than to whatever order a dict iterated in,
    and two fresh processes read a root the same way.
    """

    feature: str
    primitive: str
    gloss_ar: str
    gloss_en: str
    status: str
    authority: str
    pages: str
    physical_basis: str
    support: str
    lemmas: tuple[str, ...]
    declaration_index: int


@dataclass(frozen=True)
class PrimitiveTable:
    """The whole table, plus the lock version it was read under.

    Note what is NOT here: no root, no root key, no per-root anything. The table
    answers questions about features and about the 28 letters, and it has no way
    to be asked about a word.

    The two derived indexes are built once in `__post_init__` and then only read:
    `for_feature` is a dict lookup and `coverage` is a dict lookup, so the
    ordering rule in `compose.py` pays for neither.
    """

    rows: tuple[PrimitiveRow, ...]
    version: str

    def __post_init__(self) -> None:
        # The two indexes are attached with `object.__setattr__` rather than
        # declared as dataclass fields, so `dataclasses.fields(PrimitiveTable)`
        # stays exactly `(rows, version)` — the table's columns ARE its published
        # surface, and a test inspects them to assert no root key is reachable.
        # A derived index is not a column, and it should not look like one.
        object.__setattr__(self, "_by_feature", {})
        object.__setattr__(self, "_coverage", {})

        for row in self.rows:
            if row.feature in self._by_feature:
                raise ValueError(
                    f"physical_primitives.csv maps the feature {row.feature!r} "
                    f"twice. One feature yields one primitive: two rows would make "
                    f"a letter's reading depend on which row was read last."
                )
            self._by_feature[row.feature] = row

        distinct = self.primitives()
        if len(distinct) > MAX_PRIMITIVES:
            raise ValueError(
                f"physical_primitives.csv declares {len(distinct)} distinct "
                f"primitives; the vocabulary is capped at {MAX_PRIMITIVES}. A "
                f"richer table explains everything and therefore nothing — with "
                f"enough primitives every root reads well and no root can falsify "
                f"anything. Merge a primitive or drop a row; do not raise the cap "
                f"to fit a reading."
            )

        # Coverage over the 28 sheet letters, deduplicated per letter. Computed
        # from `features.letter_profiles()` and this table and from nothing else,
        # so it cannot drift away from either.
        for profile in features.letter_profiles().values():
            for primitive in {
                self._by_feature[f].primitive
                for f in profile.features
                if f in self._by_feature
            }:
                self._coverage[primitive] = self._coverage.get(primitive, 0) + 1

    def for_feature(self, feature: str) -> PrimitiveRow | None:
        """The row a physical feature maps to, or None if the table declares none."""
        return self._by_feature.get(feature)

    def coverage(self, primitive: str) -> int:
        """How many of the 28 sheet letters carry this primitive.

        The ordering signal: a primitive carried by 17 letters (`ظُهور`) is nearly
        free of information, one carried by a single letter (`تَكرار`) is almost
        that letter's signature. Zero for a primitive no letter carries — which
        would be a table declaring a feature the sheet never states.
        """
        return self._coverage.get(primitive, 0)

    def primitives(self) -> tuple[str, ...]:
        """The distinct primitives, in declaration order — 20 of them today."""
        seen: dict[str, None] = {}
        for row in self.rows:
            seen.setdefault(row.primitive, None)
        return tuple(seen)


@lru_cache(maxsize=1)
def primitive_table() -> PrimitiveTable:
    """Load and freeze the table. Parsed once per process.

    The `version` comes from the lock rather than from the CSV, and it rides along
    with every concept: a reading published without the version of the table that
    produced it cannot be re-derived once the table bumps.
    """
    rows = tuple(
        PrimitiveRow(
            feature=(row.get("feature") or "").strip(),
            primitive=(row.get("primitive") or "").strip(),
            gloss_ar=(row.get("gloss_ar") or "").strip(),
            gloss_en=(row.get("gloss_en") or "").strip(),
            status=(row.get("status") or "").strip(),
            authority=(row.get("authority") or "").strip(),
            pages=(row.get("pages") or "").strip(),
            physical_basis=(row.get("physical_basis") or "").strip(),
            support=(row.get("support") or "").strip(),
            lemmas=_split_lemmas(row.get("lemmas", "")),
            declaration_index=index,
        )
        for index, row in enumerate(loaders.physical_primitives())
    )
    version = str(loaders.physical_primitives_lock().get("version") or "").strip()
    return PrimitiveTable(rows=rows, version=version)


if __name__ == "__main__":
    table = primitive_table()
    print(f"lock version {table.version} — {len(table.rows)} rows, "
          f"{len(table.primitives())} distinct primitives (cap {MAX_PRIMITIVES})")
    for primitive in sorted(table.primitives(), key=table.coverage):
        print(f"  {primitive:<10} coverage {table.coverage(primitive):>2} / 28")
    profiles = {
        tuple(dict.fromkeys(
            table.for_feature(f).primitive
            for f in profile.features if table.for_feature(f)))
        for profile in features.letter_profiles().values()
    }
    print(f"{len(profiles)} distinct letter profiles over "
          f"{len(features.letter_profiles())} letters")
