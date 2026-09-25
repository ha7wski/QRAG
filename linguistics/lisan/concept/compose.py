"""
compose.py — a root's three positions, each read from its letter's physics alone.

**BLIND BY CONSTRUCTION, and that is this module's only real guarantee.**

It imports `arabic_text`, `quran_data` and its two siblings, and nothing else. It
may not reach — directly or transitively — `root_core_store`, `sense_selection`,
`qlisan_data`, `letter_lexicon`, `synthesis_template`, or any reader of the curated
cores, the cited aṣl, the letter senses or the axis vocabulary. The attested aṣl is
read **afterwards**, by `confront.py`, which imports this module's RESULT and is
never imported back.

The rule reaches the file names too, and it has to: `quran_data` is a legal import
for every layer and it holds every dataset, so `loaders.<a meaning dataset>()` is
reachable without importing one single module this rule lists. A concept module
therefore may not even spell those datasets — naming one is the whole of the
distance between blind and not.

Why the boundary is an import edge and not a note in a runbook: a protocol that
says «generate first, then look» is kept by whoever runs it, and nobody can check
later whether it was. An import boundary is kept by the build. The practical
consequence is the point — it is not possible to write a composer that peeks at
the aṣl without first deleting a test that says so.

The defect this exists to avoid is specific and was measured on the shipped
engine before this one: when the attested core SELECTS the per-letter sense, the
selector is the answer. A sense survives by agreeing with the core, so the output
cannot carry information the core did not already carry, and on the roots where it
produces a paragraph, that paragraph is a restatement of the aṣl. Here the aṣl is
the TEST, never the input.

**The positional rule, posed once and never adapted**: the first radical OPENS the
action, the second is its BODY, the third CONCLUDES it. There is no code path that
assigns them otherwise, and there is no per-root exception mechanism to add one to.

**The ordering rule**: within a position, primitives are ordered by ASCENDING
letter-coverage — the rarer first — with ties broken by declaration order in the
table. The top THREE are `realised`; the remainder is `carried`, returned and
displayed, never discarded. Rarity is the right signal because a primitive carried
by 17 of 28 letters (`ظُهور`) is nearly free of information while one carried by a
single letter (`تَكرار`) is almost that letter's signature — and it demotes the
near-universal primitives automatically, with no special case for them.

**The window was 2 and is now 3, and that number — alone among the rules here —
was changed AFTER a measurement.** §D5 of the design says the composition rule
«was fixed before it was checked»; that sentence still covers the positions and
the ordering, and it no longer covers `REALISED_PER_POSITION`. The constant's own
comment below carries the whole account: what forced the change, why it is not
back-fitting, what it costs, and how the acceptance case moved under it. It is
written there rather than summarised here because a reader who reaches the
constant is the reader who needs it.

**The rule has a known bias and it is NOT corrected.** Four letters own a primitive
no other letter carries — `ر` (تَكرار), `ش` (انتِشار), `ض` (امتِداد), `ل` (مَيْل) —
and `ص`/`ز`/`س` share `حِدّة` between the three of them, so rarity ordering makes
all seven lead with their own signature. A letter with no rare صفة leads with
whatever its مخرج zone gives it, which since v1.0.0 of the table is never nothing:
`ب` leads with `بُرُوز`, `ق`/`ك` with `أَصْل`. The method will therefore still read
sharply on roots carrying a signature letter and more flatly on roots built from
ordinary stops — the mapped zones narrow that gap rather than closing it. There is
deliberately no weighting, boost or exception compensating for it: weighting the
order on anything other than the table is the first step back toward selecting by
meaning, which is the defect above. The bias is *measured* instead — the metric is
split on exactly this line, and the split was declared before the measurement so it
could not be chosen afterwards for being flattering.

**Determinism**: every sort key is total, so two fresh processes compose a root
byte-identically. Nothing here reads a clock, a random source or an environment
variable.

**The sentence arrives here, and it is the TEMPLATE'S sentence only.** For the
length of the collision probe this module carried no sentence field at all — the
probe compares realised primitives, not prose, and putting words on an answer
that had not yet been checked would have been backwards. The probe has now run
twice and been reported, so `Concept` carries the مفهوم, assembled by the pure
deterministic `template.build_sentence` and by nothing else.

**`compose()` does NOT run the optional LLM phrasing pass, and that is a
decision rather than an omission.** `phrasing.phrase()` reads an environment
variable and, when it is on, calls a model: a `compose()` that ran it would be
deterministic only while a toggle happened to be off, and the determinism
promised two paragraphs above — the property a fresh process reproduces a root
byte-identically — would quietly become conditional on configuration. So the
composer always publishes the template's sentence, with `sentence_source` set to
`SENTENCE_SOURCE_TEMPLATE`, and a caller that wants a re-wording runs the pass
itself and folds the `PhrasingResult` back in with `dataclasses.replace`. The
template is the ground truth in the design's words; here it is also the only
thing this function can produce.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from linguistics.lisan.concept import features, template, witness_guard  # noqa: E402
from linguistics.lisan.concept.primitives import primitive_table  # noqa: E402

# The three slots, in the only order they are ever filled. First radical opens,
# second is the body, third concludes. Named rather than indexed so a reader of a
# response sees the rule instead of having to know it.
POSITIONS = ("opens", "body", "concludes")

# How many of a position's primitives the sentence will realise. The rest are
# carried.
#
# ─────────────────────────────────────────────────────────────────────────────
# **THIS CONSTANT WAS 2 AND WAS CHANGED TO 3 AFTER A PROBE CAME BACK NEGATIVE.**
#
# Saying it that way round, first, is the point. §D5 of the design says the
# composition rule «was fixed before it was checked», and of the positions and
# the ordering that is still true. It is not true of this number, and presenting
# the window as though it had been 3 all along would be a small lie about exactly
# the thing this design exists to protect.
#
# WHAT HAPPENED, IN ORDER.
#
#   1. The ṣifāt-only draft table mapped 28 letters onto 18 profiles. §D13's
#      collision probe — run before a single witness root was curated — returned
#      `identical` on 5 of 5 qualifying comparisons: حرب=حرج=حرد, تبر=كبر,
#      كود=كيد. §D3 had declared the fallback IN ADVANCE: if the probe confirmed
#      the collision, mapping the five classical مخرج zones becomes table v1.0.0
#      rather than a later lock bump.
#   2. The zones were mapped. The table now yields **27 distinct letter profiles**
#      of 28: only ح and ه remain merged (same حلق zone, same رخاوة and همس), and
#      five zones cannot separate them.
#   3. At a window of 2 the sentence never sees past the first two primitives, and
#      there the table yields only **25 distinct realised pairs**. Two pairs
#      collide in the window while differing outside it:
#         و/ي  — both open لِين(2) · مَدّ(2); the zone that parts them, بُرُوز(4)
#                for و against وَسَط(3) for ي, sits THIRD and never arrives.
#         خ/غ  — both open غَوْر(6) · ضَخامة(7); what parts them, خَفاء(10) against
#                جَرَيان(15), sits third. This one is worse than a miss: خ and غ
#                were DISTINCT at a window of 2 on the ṣifāt-only table
#                (ضَخامة·خَفاء against ضَخامة·جَرَيان). Adding غَوْر at the head
#                pushed their separator out of the window — the zones CREATED
#                this collision.
#      Zones that have been mapped and are invisible to the reader have not been
#      mapped in any sense that matters.
#   4. At a window of 3 the realised triples are **27 of 28** — exactly the full
#      profile count, only ح/ه merged. Everything the table can distinguish, the
#      sentence now says. A window of 4 is still 27 and buys nothing.
#
# WHY THIS IS NOT BACK-FITTING — stated rather than implied.
#
#   (a) It was FORCED by a consequence §D3 pre-declared. The design wrote down
#       that a confirmed collision makes the zones v1.0.0. What nobody anticipated
#       is that the mapping interacts with the display window: a zone ranked third
#       is a zone that was never added, and in خ/غ's case a zone that made things
#       worse. The window had to move for the pre-declared fallback to do what it
#       was declared to do.
#   (b) It was decided against the LETTER SHEET, not against any root. Every
#       number above — 18, 25, 27 — is a property of `arabic_letters_dataset.csv`
#       and `physical_primitives.csv` and of nothing else. No witness root was
#       read, no aṣl was consulted, no curated core was opened, and the 40-root
#       holdout is untouched. A rule tuned on its own input is a different act
#       from a rule tuned on its answer.
#   (c) It is DECLARED BEFORE the new probe runs. The re-run of §D13 against the
#       zoned table is still a real test, because the window it will be measured
#       at is fixed here and committed first. A window chosen after seeing that
#       probe's numbers would have been worth nothing at all.
#
# WHAT IT COSTS, recorded rather than patched. A مفهوم is one sentence, and three
# positions × three primitives is NINE notions to hold together where the brief
# budgeted six. The Arabic template — a later step — inherits the harder job, and
# a sentence carrying nine notions risks reading as a list rather than as a
# reading. That is the price of separating و/ي and خ/غ, and it is paid knowingly.
#
# THE ACCEPTANCE CASE MOVES WITH IT. `ضرب`, the one declared development case,
# now reads — old values shown superseded:
#
#     opens      ض   امتِداد(1) · ضَخامة(7) · طَرَف(13)     was  امتِداد · ضَخامة
#     body       ر   تَكرار(1) · تَمَهُّل(5) · طَرَف(13)      was  تَكرار · تَمَهُّل
#     concludes  ب   بُرُوز(4) · ارتِداد(5) · قَطْع(8)       was  ارتِداد · قَطْع
#
# Note what happened at `ب`, because it is interesting rather than alarming. §D3
# booked as a stated LOSS that `ب`'s closure comes from the مخرج — the two lips
# sealing — and therefore could not be carried. With the zones mapped `ب` now
# LEADS with بُرُوز, the lips being the outermost locus the voice reaches: part of
# the loss §D3 recorded is recovered. It was NOT arranged. بُرُوز glosses a
# POSITION on the inner→outer axis, not a closure; the zone series was written
# over the whole sheet, in one graded run from غَوْر to بُرُوز, before any root was
# composed under it; and nothing in it was tuned toward `ضرب`. The other two
# positions gained طَرَف(13) — a common primitive landing third, which is the
# window doing its job and not a signal.
# ─────────────────────────────────────────────────────────────────────────────
REALISED_PER_POSITION = 3

# The reservation that travels WITH any number produced under that window.
#
# It lives here, against the constant it describes, and is imported by everything
# that prints a coverage verdict — `scripts/validate_concept_datasets.py`'s
# `k / 40` printer and `api/routers/lisan.py`'s concept response. §D11 and the
# `concept-attestation-protocol` spec require it to be published WITH the number
# and not by reference, which makes a second copy the one real failure mode: two
# statements of one fact drift, and the drift would be invisible precisely
# because each surface looks complete on its own.
#
# Two languages, adjacent, for one fact. The validator's report is English like
# the rest of the repo's code surface; `/lexical` is an Arabic-only page and an
# English paragraph under an Arabic verdict is a paragraph nobody reads. They are
# written side by side here so that editing one without the other is a visible
# omission rather than a discovery made months later.
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

WINDOW_RESERVATION_AR = (
    "تحفُّظٌ يُنشَرُ مع الرقم: قاعدةُ التركيب ليست مُسجَّلةً سلفًا بتمامها. "
    "فعددُ الأصولِ التي تبلغُ العبارةَ في كلِّ موضعٍ حُدِّدَ باثنين، ثمَّ وُسِّعَ "
    "إلى ثلاثةٍ بعد قياسٍ جاء سلبيًّا على «ضرب»، وهي حالةُ التطويرِ المُعلَنة. "
    "أمَّا المواضعُ وترتيبُ النُّدرةِ وفضُّ التعادُلِ فقد ثبتَت قبل أن تُختبَر؛ "
    "وأمَّا سَعةُ النافذةِ فلا. والذي يَحُدُّ من أثرِ ذلك: أنَّ الأربعين المحجوزةَ "
    "لم تُقرَأ حين تغيَّرت النافذة، وأنَّ «ضرب» مُستثناةٌ من العدد. والذي لا يفعلُه: "
    "أنَّه لا يمحوه. فقد ضُبِطَ وسيطٌ حُرٌّ واحدٌ من القاعدةِ بالنظرِ إلى نتيجة، "
    "ومَن حسَمَ من قيمةِ «ك / ٤٠» لهذا السبب فقد قرأ قراءةً صحيحة."
)

# Where `Concept.sentence` came from. Declared here, beside the field they
# describe, and imported by `phrasing.py` rather than re-spelled there: two
# copies of a status string is how a comparison starts quietly failing.
#
# `template` — the deterministic assembler, which is what `compose()` always
# publishes and what a rejected phrasing falls back to. `phrasing` — an LLM
# re-wording that passed the containment veto. There is no third value: an LLM
# sentence that was produced and refused is NOT a source, it is a rejection
# recorded next to the template's own output.
SENTENCE_SOURCE_TEMPLATE = "template"
SENTENCE_SOURCE_PHRASING = "phrasing"

# Why a root gets no concept at all, as `Concept.refusal_code` names it.
REFUSAL_NOT_TRILITERAL = "not-triliteral"

# The composition rule covers three positions. 43 of the 1656 QAC roots are
# quadriliteral and they are refused rather than squeezed in: stretching a
# three-slot rule to four slots is adapting the rule to the case, which is the one
# move this whole design forbids. A four-position rule is a future change, posed in
# advance the way this one was.
_REFUSAL_NOT_TRILITERAL_AR = (
    "قاعدةُ التركيب موضوعةٌ على ثلاثةِ مواضعَ لا غير: الحرفُ الأوَّلُ يفتَحُ الحدثَ، "
    "والثاني جسَدُه، والثالثُ يختِمُه. ولم تُمَدَّ هذه القاعدةُ إلى أربعةِ مواضعَ "
    "عمدًا، لأنَّ تطويعَ القاعدةِ للحالةِ هو عينُ ما يمنعُه هذا المنهج. فلا مفهومَ "
    "لهذا الجذر."
)


@dataclass(frozen=True)
class PrimitiveHit:
    """One primitive a letter carries, with the row that licensed it.

    `status` travels with the hit so the page can say which mappings a named
    authority states and which the project asserts. `coverage` and
    `declaration_index` travel with it so a reader can re-derive the order by hand
    instead of taking it on trust.
    """

    primitive: str
    feature: str
    gloss_ar: str
    status: str
    coverage: int
    declaration_index: int


@dataclass(frozen=True)
class PositionReading:
    """One radical read at one position: the evidence, the order, and the cut.

    `letter` is the glyph as written in the root key — the stored spelling is never
    rewritten — and `sheet_letter` is the row it was read from, which differs for a
    hamza seat (`أ` → `ء`) and is None when the sheet has no row at all.

    `ordered` is every primitive the letter carries, rarest first; `realised` is
    its first `REALISED_PER_POSITION` — three today; `carried` is the remainder.
    `carried` is returned rather than dropped: the ones the sentence uses are a
    display budget, not a claim that the others are absent. Read the constant's
    comment before changing the number: it is the one rule in this module that
    moved after a measurement, and it says so.
    """

    position: str
    letter: str
    sheet_letter: str | None
    makhraj_ar: str
    features: tuple[str, ...]
    ordered: tuple[PrimitiveHit, ...]
    realised: tuple[PrimitiveHit, ...]
    carried: tuple[PrimitiveHit, ...]
    silent: bool
    silent_reason: str


@dataclass(frozen=True)
class Concept:
    """A root's composed reading, or a stated refusal to compose one.

    `refused` and `partial` are different failures and are kept apart on purpose.
    `refused` means the rule does not cover this root at all (a quadriliteral) and
    `positions` is empty. `partial` means the rule applied but one position is
    silent — the concept exists and is honestly short by that position.

    `lock_version` is the table version the reading was produced under. A reading
    published without it cannot be re-derived once the table bumps.

    `sentence` is the مفهوم and `sentence_source` says who wrote it. Straight out
    of `compose()` the source is always `SENTENCE_SOURCE_TEMPLATE`: this function
    runs no model (see the module docstring). A caller that enables the optional
    phrasing pass replaces all three fields at once with
    `dataclasses.replace(concept, sentence=…, sentence_source=…,
    phrasing_rejection=…)` from a `phrasing.PhrasingResult`.

    `phrasing_rejection` is non-empty in exactly one situation: a phrasing was
    produced and the containment veto refused it. It is NOT set when the pass is
    off, nor when the model was unreachable, timed out or returned nothing —
    those are failures, and a failure that recorded itself as a rejection would
    make «the model invented something» and «the model was not running» look the
    same in the response.
    """

    root: str
    refused: bool
    refusal_code: str
    refusal_reason: str
    positions: tuple[PositionReading, ...]
    realised_primitives: tuple[str, ...]
    sentence: str
    sentence_source: str
    phrasing_rejection: str
    partial: bool
    silent_letters: tuple[str, ...]
    lock_version: str


def _silent_reason_ar(letter: str) -> str:
    """Say WHOSE gap this is: the sheet has no row, so nothing is claimed.

    On today's corpus this fires only for the bare `ا` of `اني`, `اول`, `هاء` and
    `هات` — four roots. It is a reported absence, not a fallback: there is no
    default primitive and no flag that restores one, because a filler at a silent
    position would read on screen exactly like a letter that had been described.
    """
    return (
        f"الحرفُ «{letter}» ليس من حروفِ الجدولِ الثمانيةِ والعشرين، ولا مخرجَ له "
        f"يخصُّه فيه، فلا يُنسَبُ إليه وصفٌ صوتيٌّ ولا أصلٌ فيزيائيّ. هذا الموضعُ "
        f"ساكتٌ، والمفهومُ ناقصٌ من جهتِه، ولم يُوضَع مكانَه شيء."
    )


def _hits(profile: features.LetterProfile) -> tuple[PrimitiveHit, ...]:
    """The letter's primitives, deduplicated, ordered rarest-first.

    Deduplication is per LETTER and keeps the first feature that produced the
    primitive: `ص ض ط ظ` carry `musta'liya` and `mutbaqa`, which both map to
    `ضَخامة`, and listing it twice would let one letter's own doubling outrank a
    rarer primitive purely by repetition. The kept row is the one the sheet names
    first, which for the single duplicate pair on today's data is also the one the
    table declares first — the two readings are indistinguishable here, and the
    sheet's order is used because it is the order the profile was built in.

    The sort key `(coverage, declaration_index)` is TOTAL: coverage is the signal,
    and the table's own declaration order breaks every tie, so the result falls to
    the curator's ordering rather than to dict iteration order. That is what makes
    a fresh process reproduce the same reading.
    """
    table = primitive_table()
    by_primitive: dict[str, PrimitiveHit] = {}
    for feature in profile.features:
        row = table.for_feature(feature)
        if row is None or row.primitive in by_primitive:
            continue
        by_primitive[row.primitive] = PrimitiveHit(
            primitive=row.primitive,
            feature=row.feature,
            gloss_ar=row.gloss_ar,
            status=row.status,
            coverage=table.coverage(row.primitive),
            declaration_index=row.declaration_index,
        )
    return tuple(sorted(
        by_primitive.values(),
        key=lambda hit: (hit.coverage, hit.declaration_index),
    ))


def _read_position(position: str, letter: str) -> PositionReading:
    """Read ONE radical at ONE fixed position. Knows nothing about the other two.

    Takes the position as an argument rather than deciding it, so there is no place
    in this module where a position could be chosen for a letter.
    """
    profile = features.profile_for(letter)
    if profile is None:
        return PositionReading(
            position=position,
            letter=letter,
            sheet_letter=None,
            makhraj_ar="",
            features=(),
            ordered=(),
            realised=(),
            carried=(),
            silent=True,
            silent_reason=_silent_reason_ar(letter),
        )
    ordered = _hits(profile)
    return PositionReading(
        position=position,
        letter=letter,
        sheet_letter=profile.letter,
        makhraj_ar=profile.makhraj_ar,
        features=profile.features,
        ordered=ordered,
        realised=ordered[:REALISED_PER_POSITION],
        carried=ordered[REALISED_PER_POSITION:],
        silent=False,
        silent_reason="",
    )


def compose(root: str) -> Concept:
    """Compose `root`'s concept from its letters' physics, and from nothing else.

    The root key is taken as given — stripped of surrounding whitespace and
    otherwise untouched. It is deliberately NOT normalized: QAC stores roots in
    their exact, hamza-bearing spelling, and folding one here would be this module
    making a decision about spelling on the way to making one about meaning. A
    hamza seat is resolved for the SHEET LOOKUP only (`features.sheet_letter`), and
    the stored spelling comes back unchanged in `PositionReading.letter`.

    A root that is not exactly three letters is refused with a stated reason and no
    positions. A root one of whose letters the sheet does not describe composes
    anyway, `partial`, with that position silent and named.
    """
    root = (root or "").strip()
    # A TEST may not compose a holdout root. Placed first, before the length
    # check and before the table is read, so the refusal cannot depend on
    # anything about the root but its membership. Inert outside a test runner:
    # the shipped route composes whatever a reader types, and the recording path
    # takes the sanction. Read `witness_guard`'s docstring — it carries the
    # incident this exists because of.
    witness_guard.check(root)
    version = primitive_table().version

    if len(root) != 3:
        return Concept(
            root=root,
            refused=True,
            refusal_code=REFUSAL_NOT_TRILITERAL,
            refusal_reason=_REFUSAL_NOT_TRILITERAL_AR,
            positions=(),
            realised_primitives=(),
            # No مفهوم, and no near-miss standing in for one. The refusal's own
            # Arabic is in `refusal_reason`, where a reader looking for a reason
            # will find one; an apologetic half-sentence here would be a concept
            # for a root the rule does not cover.
            sentence="",
            sentence_source=SENTENCE_SOURCE_TEMPLATE,
            phrasing_rejection="",
            partial=False,
            silent_letters=(),
            lock_version=version,
        )

    positions = tuple(
        _read_position(POSITIONS[index], letter)
        for index, letter in enumerate(root)
    )
    # Flat, position order then rarity order. Not deduplicated across positions: a
    # primitive carried at two positions is two contributions to the sentence, and
    # collapsing them would erase the difference between a root that says a thing
    # once and one that says it twice — which is exactly what the collision probe
    # compares.
    realised = tuple(
        hit.primitive for reading in positions for hit in reading.realised
    )
    silent = tuple(reading.letter for reading in positions if reading.silent)
    draft = Concept(
        root=root,
        refused=False,
        refusal_code="",
        refusal_reason="",
        positions=positions,
        realised_primitives=realised,
        sentence="",
        sentence_source=SENTENCE_SOURCE_TEMPLATE,
        phrasing_rejection="",
        partial=bool(silent),
        silent_letters=silent,
        lock_version=version,
    )
    # Built in two steps rather than one, so `build_sentence` takes the WHOLE
    # concept and can be called again on any concept from anywhere — by a test,
    # by the phrasing pass's fallback, by a caller re-rendering a stored reading.
    # The alternative — assembling the sentence from a bare list of primitives
    # before the concept exists — would give the template a second input shape
    # that nothing else in the repo holds, and the partial and refused cases are
    # precisely the ones that shape would lose.
    return replace(draft, sentence=template.build_sentence(draft))


if __name__ == "__main__":
    for probe in ("ضرب", "برزخ", "اول", "أنس"):
        concept = compose(probe)
        print(f"{probe} — lock {concept.lock_version}"
              + (f"  REFUSED [{concept.refusal_code}]" if concept.refused else "")
              + ("  PARTIAL" if concept.partial else ""))
        if concept.refused:
            print(f"    {concept.refusal_reason}")
            continue
        for reading in concept.positions:
            if reading.silent:
                print(f"    {reading.position:<9} {reading.letter}  SILENT — "
                      f"{reading.silent_reason}")
                continue
            order = " · ".join(f"{h.primitive}({h.coverage})" for h in reading.ordered)
            realised = " · ".join(h.primitive for h in reading.realised)
            print(f"    {reading.position:<9} {reading.letter} "
                  f"[{reading.sheet_letter}] {reading.makhraj_ar}")
            print(f"              {order}   ->   {realised}")
        print(f"    realised: {' · '.join(concept.realised_primitives)}")
        print(f"    مفهوم [{concept.sentence_source}]: {concept.sentence or '—'}")
