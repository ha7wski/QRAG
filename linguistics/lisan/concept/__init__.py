"""
concept/ — the PHYSICS-FIRST reading of a root: مفهوم from letters, aṣl as the test.

`/lexical` has had two engines and this is the third. The history is the design,
because each one fixed the previous defect and inherited a new one:

1. **Concatenation.** One frozen gloss per letter, chained. `خ-ي-ر` read «القذارة
   والخشونة والخواء… فساد» — the antonym of the attested sense. Defect: a letter
   carries a BUNDLE of senses and nothing selected among them.
2. **Core-first** (the shipped `linguistics/lisan/` engine, one level up). Ibn
   Fāris' aṣl is fetched FIRST and selects one sense per letter by shared axis.
   `خ-ي-ر` now reads correctly and the minimal pair `خ-ي-ر`/`خ-ب-ث` proves the same
   letter can read two ways. Defect, structural and unavoidable: **the selector is
   the answer.** A sense survives by agreeing with the core, so the output cannot
   carry information the core did not already carry — on the roots where it does
   produce a paragraph, that paragraph is a restatement of the aṣl.
3. **Physics-first** (this package). Nothing about the root's meaning enters before
   the concept exists. The input is the tajwīd description of its letters —
   `makhraj_ar` and `sifat`, facts about the mouth — and **the aṣl is read
   afterwards, to check the result**. It is the TEST, never the input.

**The engine in (2) is not modified, deprecated or hidden by this package.** Both
answer, side by side, until the comparison has a number attached to it. Nothing
here imports anything from `linguistics/lisan/`'s existing modules, and nothing
there imports this.

The modules, bottom to top:

    features.py    the letter sheet reduced to a closed 21-feature vocabulary —
                   16 ṣifāt features by a rule stated over the VOCABULARY
                   (privative / equipollent / لا ضد لها / disputed), plus the
                   five classical مخرج zones. The sheet's interpretive columns
                   are banned from this path and the ban is tested.
    primitives.py  the frozen 21-row table mapping features onto 20 primitives,
                   keyed on features ONLY — no root can reach it — plus each
                   primitive's letter-coverage, derived and never stored.
    compose.py     three fixed positions (opens · body · concludes), rarity
                   ordering within each, top THREE realised and the rest carried.
    template.py    the deterministic Arabic مفهوم — one nominal sentence, and
                   nothing the realised primitives did not license. It is the
                   GROUND TRUTH; the sentence is never richer than the table.
    phrasing.py    the optional LLM re-wording, off by default and containment
                   checked: every content word must map to a declared lemma of a
                   realised primitive, or the sentence is rejected and not shown.
                   A renderer with a veto over it, never an author.
    confront.py    the ONLY module here allowed to read the aṣl. It imports the
                   concept result; nothing above imports it back, which is what
                   keeps the generation blind.

The مخرج zones and the three-primitive window are both §D13's doing. The engine
first shipped a ṣifāt-only draft with a two-primitive window; the collision probe
returned `identical` on 5 of 5 qualifying comparisons, because that table mapped
28 letters onto 18 profiles. §D3 had declared the fallback in advance, so the
zones became v1.0.0 rather than a later lock bump — and the window widened to
three when the zones turned out to rank below it. The full account, including
what the window change costs in evidential standing, is on
`compose.py`'s REALISED_PER_POSITION.

**Blindness is an import edge, not a protocol.** A rule that says «generate first,
then look» is kept by whoever runs it; an import boundary is kept by the build. No
module here may reach — directly or transitively — the curated cores, the cited
aṣl, the letter senses or the axis vocabulary: every dataset carrying what a root
or a letter MEANS. `confront.py` is the single exemption and the reason the rule
can be absolute everywhere else; it imports the concept RESULT rather than being
imported by it. This package therefore imports no module that reads meaning, and
the test enforcing that forbids even writing those datasets' names down here —
`quran_data` is a legal import for every layer, so a loader call is one line away
from any module that can spell its dataset.

**Nothing here is tuned per root**, and there is no mechanism to be tempted by: a
root whose concept misses its attested aṣl is a recorded MISS — a result — and the
table moves only through a lock version justified by a feature-level authority. The
change is worth shipping on a low number honestly obtained and worth not shipping
on a high one obtained by editing the table.
"""
from __future__ import annotations

# `compose` the FUNCTION is deliberately NOT re-exported here, though it is this
# package's whole point. Re-exporting it binds the name `compose` on the package
# to the callable and **shadows `compose` the module**, so
# `from linguistics.lisan.concept import compose` silently hands back a function
# and `compose.REALISED_PER_POSITION` then raises `AttributeError` somewhere deep
# in a caller rather than at the import that caused it. A convenience alias is
# not worth an error that surfaces three frames from its cause.
#
# The canonical import is the explicit one, which every caller already uses:
#
#     from linguistics.lisan.concept.compose import compose
#
# `Concept` is safe to re-export — no module is named after it.
from linguistics.lisan.concept.compose import Concept
from linguistics.lisan.concept.features import letter_profiles
from linguistics.lisan.concept.primitives import primitive_table

__all__ = ["Concept", "letter_profiles", "primitive_table"]
