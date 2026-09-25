"""
template.py — the مفهوم itself: nine realised primitives, assembled and nothing else.

**This module is the GROUND TRUTH of the sentence.** The optional LLM pass in
`phrasing.py` may re-word what this produces and may never add to it; when that
pass is off — which is the default — what this function returns is what the
reader sees. So the rule here is not «write good Arabic», it is «write Arabic
that asserts exactly the primitives and exactly nothing else», and where the two
pull against each other the second wins every time.

**PURE.** No disk, no clock, no randomness, no environment, no model. It reads
`concept.positions[*].realised[*].primitive` and `.position` and nothing further
— not even the primitive table, which is already what produced those hits. Two
fresh processes therefore assemble a root byte-identically, and the determinism
test that pins that covers the sentence as well as the primitives.

─────────────────────────────────────────────────────────────────────────────
THE SHAPE, AND WHY THIS ARABIC

§D6 of the design fixes the skeleton at nine slots — three per position, since
§D5 widened the realised window from two to three — and deliberately leaves the
Arabic to this module: «writing the sentence in the design, before the template
module exists, is how a phrasing gets chosen for how well it reads on `ضرب`».

What is assembled:

    clause   = P₁ + «و»P₂ + «و»P₃                    one position's realised set
    sentence = clause(opens) + «، ثُمَّ » + clause(body)
                             + «، حتَّى » + clause(concludes)

and `ضرب`, the one declared development case, comes out as

    «امتِدادٌ وضَخامةٌ وطَرَفٌ، ثُمَّ تَكرارٌ وتَمَهُّلٌ وطَرَفٌ، حتَّى بُرُوزٌ وارتِدادٌ وقَطْعٌ»

Every content word is a primitive's own name, which is in turn a declared lemma
of that primitive — checked, not assumed: `phrasing.contained` is run against
this module's own output by a test, and a template that failed its own veto
would be the bug that test exists to catch.

**The iʿrāb.** One nominal enumeration, every member مرفوع منوَّن. `و` is the
عاطفة inside a clause and attaches to the following word without a space, which
is how Arabic coordinates a list — it does not stack bare nouns side by side.
`ثُمَّ` and `حتَّى` are the عاطفة between clauses; `حتَّى` is here the **عاطفة**
(«مات الناس حتى الأنبياءُ»), so the third clause takes the case of the first two
and the enumeration stays nominative throughout. The tanwīn is appended rather
than written into the table because the table's `primitive` column is a citation
form, not a word in a sentence; under the containment fold the two are the same
string, so nothing is smuggled by adding it.

**The connectives are the ONLY thing added, and they add no notion.** `ثُمَّ`
and `حتَّى` say «then» and «up to»: that is the positional rule — first radical
opens, second is the body, third concludes — which the composition already
declares. They are not a relation between the primitives and they do not claim
one. Nothing else is added: no example, no Quranic citation, no hedge, no second
participant, no trace left behind.

**The sentence reads bluntly, permanently, and that is the price.** §D6 compares
it with the brief's «إيقاعُ شيءٍ على شيءٍ إيقاعًا يُحدِثُ أثرًا» and says the
plain thing: that sentence is better Arabic and it is *richer than the
composition licenses*. Neither شيء على شيء nor أثر follows from
`امتِداد · ضَخامة · طَرَف · تَكرار · تَمَهُّل · طَرَف · بُرُوز · ارتِداد · قَطْع`;
both come from already knowing what ضرب means. Nine primitives held together by
coordination alone is closer to a list than to prose, and the honest response to
that is to leave it a list rather than to buy fluency with content.

─────────────────────────────────────────────────────────────────────────────
SHAPES REJECTED, recorded so the choice reads as a decision

1. **The skeleton's bare juxtaposition** — `{P1} {P2} {P3}`, three nominatives
   with nothing between them. §D6 writes the slots that way, but Arabic has no
   comma-list: «امتِدادٌ ضَخامةٌ طَرَفٌ» parses as نعت or بدل or a broken إضافة
   chain, i.e. it asserts that the ضخامة IS the امتداد. That is a relation the
   composition never licensed, arrived at by *omitting* a word. The `و` is added
   for exactly the reason the rest is not: it prevents an assertion rather than
   making one.

2. **The predicative / verbal shape** — the superseded six-slot exemplar
   «امتِدادٌ ضَخْمٌ، يَتَكَرَّرُ مُتَمَهِّلًا، حتَّى يَنقَطِعَ فَيَرتَدَّ».
   It reads far better and it is refused twice over. It *binds* the primitives:
   `ضَخْم` becomes a نعت of the امتداد (the extension is bulky) and the تكرار
   becomes that extension's own action — two claims the letters never made, since
   each primitive is one letter's independent contribution. And it needs a
   per-primitive table of derived forms (اسم فاعل, حال, فعل) to exist at all; a
   second curated artefact, keyed per primitive, is exactly the surface on which
   a reading could be tuned until roots came out well.

3. **Prepositional binding** — «امتِدادٌ وضَخامةٌ في طَرَفٍ». A preposition is a
   function word but it is not contentless: في asserts a locus, بـ an instrument,
   عن a source. Each is a notion, and «the primitives did not license it» applies
   to a relation as much as to a noun.

─────────────────────────────────────────────────────────────────────────────
PARTIAL AND REFUSED

A silent position is **omitted**, and nothing is put where it was. No filler, no
default primitive, no flag restoring one — a placeholder at a silent position
would read on screen exactly like a letter that had been described, which is the
one failure the «no silent fallback» rule exists to prevent. `اول` (bare `ا`,
silent) therefore reads as two clauses and says so elsewhere in the response,
through `partial` and `silent_letters`.

The connective belongs to the clause's **position**, not to its rank among the
survivors: `body` is joined with `ثُمَّ`, `concludes` with `حتَّى`, and whichever
clause comes first carries none. That is what keeps every partial grammatical —
a sentence opening on a bare `ثُمَّ` is a عاطفة with nothing to coordinate onto.
Every case lands correctly: «X، ثُمَّ Y، حتَّى Z» · «Y، حتَّى Z» (opens silent) ·
«X، حتَّى Z» (body silent) · «X، ثُمَّ Y» (concludes silent) · «X» alone.

A refused root — a quadriliteral, which the three-slot rule does not cover — and
a root whose every position is silent both return `""`. An empty sentence is the
only honest output for «no مفهوم», and the refusal's own Arabic reason travels
in `Concept.refusal_reason` beside it.

A position may also realise FEWER than three primitives without being partial:
`ء` carries exactly two (`قَطْع`, `غَوْر`) because the sheet records its جهر/همس
as disputed and a disputed fact is not a fact. `أنس` is a full, non-partial
three-clause sentence whose first clause has two members.

─────────────────────────────────────────────────────────────────────────────
THE FUNCTION WORDS ARE DECLARED HERE

`FUNCTION_WORDS`, `PROCLITICS` and `ARTICLE` below are the closed set that
`phrasing.contained` subtracts before demanding that every remaining word be a
declared lemma. They are declared in this module, once, because they are a fact
about what the template may WRITE; a check that carried its own copy could drift
into subtracting more than the template ever emits, and every word it subtracts
beyond that set is a word the veto stops looking at.
"""
from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only, and never at runtime
    # A runtime import would be circular: `compose` imports this module to build
    # the sentence. `from __future__ import annotations` makes the annotations
    # strings, so the name is needed only by a type checker.
    from linguistics.lisan.concept.compose import Concept, PositionReading

# ARABIC DAMMATAN — the indefinite nominative ending, appended to every
# primitive. Written as an escape, never as a literal: a lone combining mark in
# source attaches itself to the preceding quote character and is unreviewable on
# screen, which is the same rule `arabic_text/marks.py` states for mark classes.
NOMINATIVE = "ٌ"

# The عاطفة inside a clause. Attached to the following word without a space,
# which is Arabic orthography and not a formatting choice.
COORDINATOR = "و"

# Between two clauses. The comma is the design's; the space after it is what
# separates the connective from the preceding clause.
CLAUSE_SEPARATOR = "، "

# Which عاطفة introduces a clause, by the POSITION it reads — never by its rank
# among the surviving clauses. The keys mirror `compose.POSITIONS`; they are
# literals here rather than an import because `compose` imports this module, and
# a position this table does not know raises rather than silently losing its
# connective.
POSITION_CONNECTIVE: dict[str, str] = {
    "opens": "",        # the first radical opens: nothing precedes it
    "body": "ثُمَّ",     # sequence — the positional rule, not a new notion
    "concludes": "حتَّى",  # عاطفة, so the last clause keeps the nominative
}

# Standalone particles a sentence may contain. Closed, and it is the whole of
# what `phrasing.contained` subtracts: `و` and `ثُمَّ` and `حتَّى` are what this
# module writes, and `فَ` is admitted as the one other pure عاطفة a re-wording
# may reach for. Nothing that asserts a relation — no preposition — is here.
FUNCTION_WORDS: frozenset[str] = frozenset({"و", "ثُمَّ", "حتَّى", "فَ"})

# Particles that ride on the FRONT of a word: the two coordinators, which this
# module itself attaches (`وضَخامةٌ` is one token), and the article. They are
# peeled only when the remainder is itself a declared lemma, so a false peel can
# never manufacture a match — `وَلَد` peels to `لد`, which is nobody's lemma.
PROCLITICS: tuple[str, ...] = ("و", "ف")

# حرف التعريف. Definiteness is not a notion: «الامتِداد» and «امتِدادٌ» name the
# same primitive, and rejecting the first would be vetoing morphology instead of
# vetoing content.
ARTICLE = "ال"


def _clause(reading: "PositionReading") -> str:
    """One position's realised primitives, coordinated and in the nominative.

    Order is the reading's own — rarity order, rarest first — and is never
    re-sorted here. The sentence says what the composition ranked; a template
    that reordered would be a second, undeclared ranking rule hiding in the
    presentation layer.
    """
    words = [hit.primitive + NOMINATIVE for hit in reading.realised]
    # The space goes BEFORE the و and never after it: `و` binds forward onto the
    # word it coordinates and is separated from the previous one. Written the
    # other way the clause renders as a single token — «امتِدادٌوضَخامةٌ» — which
    # is not a spelling mistake a reader would forgive, and which would hand the
    # containment check one unsplittable word where it expects three.
    return words[0] + "".join(f" {COORDINATOR}{word}" for word in words[1:])


def build_sentence(concept: "Concept") -> str:
    """The مفهوم — one Arabic sentence, or `""` when there is nothing to say.

    `""` in exactly two cases, and they are different failures: the root was
    REFUSED (the three-slot rule does not cover it), or every position is silent
    so no clause exists. Both are honest emptiness; neither is a fallback.

    Pure. Reads the positions, their `realised` primitives and their position
    names, and nothing else.
    """
    if concept.refused:
        return ""

    clauses = [
        (reading.position, _clause(reading))
        for reading in concept.positions
        if not reading.silent and reading.realised
    ]
    if not clauses:
        return ""

    parts = [clauses[0][1]]
    for position, clause in clauses[1:]:
        connective = POSITION_CONNECTIVE.get(position)
        if connective is None:
            raise ValueError(
                f"No connective is declared for the position {position!r}. The "
                f"positional rule names three — opens, body, concludes — and a "
                f"fourth is a rule change, not a presentation detail. Declare the "
                f"connective in POSITION_CONNECTIVE; do not let the clause join "
                f"silently with nothing."
            )
        head = f"{connective} " if connective else ""
        parts.append(CLAUSE_SEPARATOR + head + clause)

    # NFC, and it is not cosmetic. Appending the tanwīn after a shadda produces
    # `مَدّ` + `ٌ` = د ـّ ـٌ, which canonical ordering rewrites to د ـٌ ـّ because
    # the two marks have different combining classes. Both render identically and
    # neither is wrong, so the difference is invisible on screen and fatal to a
    # comparison — `مَدٌّ` typed by hand matches one of them and not the other.
    # That is the same trap the Basmala detection records: combining-mark order
    # is not stable, so a string that will be compared has to be canonical before
    # it leaves. Every other primitive is already NFC, so this fixes exactly one
    # word and changes nothing else.
    return unicodedata.normalize("NFC", "".join(parts))


if __name__ == "__main__":
    # The repo's path anchoring, but INSIDE the smoke test. The module itself
    # imports nothing from the project at runtime and must keep that property:
    # `build_sentence` is pure, and a module-level `sys.path` insert plus a
    # sibling import is the first step away from it.
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

    from linguistics.lisan.concept.compose import compose

    for probe in ("ضرب", "كود", "كيد", "أنس", "اول", "برزخ"):
        concept = compose(probe)
        label = "REFUSED" if concept.refused else ("PARTIAL" if concept.partial else "")
        print(f"{probe:<6} {label:<8} {build_sentence(concept) or '—'}")
