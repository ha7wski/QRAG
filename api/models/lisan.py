"""Pydantic models for the Lisan Analysis (letter-symbolism) endpoint.

The response publishes the CONSTRAINT, not just the conclusion. A letter holds a
bundle of sourced senses; which member applies depends on the root's attested
aṣl, so the reading has to show the core it was built from, the axes each
selected sense shared with it, and every sense it dropped with the reason. A
single gloss per letter — the old `letters[].meaning` — is what made خ-ي-ر read
«القذارة والخشونة والخواء» against Ibn Fāris' «أصله العطف والميل», so it is gone,
and so is the `sequential_reading` chain that concatenated those glosses.
"""
from __future__ import annotations

from pydantic import BaseModel


class LisanRequest(BaseModel):
    word: str
    # The Lisan feature is Arabic-only; there is no `lang` parameter. Any `lang`
    # sent by an old client is silently ignored (Pydantic drops unknown fields).


# ── the attested core ─────────────────────────────────────────────────────

class RootCore(BaseModel):
    """One aṣl of the root, as Ibn Fāris states it.

    `verbatim` is his own words, byte-identical to the shipped Maqāyīs segment;
    `gloss`, `axes` and `polarity` are curated beside it, never instead of it.
    `polarity` describes the aṣl AS CITED — `neutral` when it is descriptive —
    so it can be checked against the citation rather than against a sentiment
    prior (ك-ف-ر's «الستر والتغطية» is neutral; its negative charge is usage).
    """

    gloss: str
    verbatim: str
    axes: list[str] = []
    polarity: str                      # "positive" | "negative" | "neutral"
    source: str
    edition: str = ""


# ── the letter side ───────────────────────────────────────────────────────

class LetterSense(BaseModel):
    """One member of a letter's sense bundle, with the citation that admits it."""

    sense_id: str
    gloss_ar: str
    pole: str                          # "positive" | "negative" | "neutral"
    axes: list[str] = []
    # A SET of positions, not one. Ḥasan ʿAbbās states «في الآخر والوسط» as a
    # single predicate over two positions; two rows for that was the sheet's only
    # duplicate gloss, and `any` would contradict the different «في الأول» he
    # states separately. `["any"]` means he states no position for the sense.
    position: list[str] = []           # of "initial" | "medial" | "final" | "any"
    # What the stated position CLAIMS: "exclusive" (only there — closes the
    # selection gate) or "dominant" (a proportion or comparison — ranks only).
    # Empty when `position` is `["any"]`. Ḥasan ʿAbbās mostly gives proportions,
    # so reading every stated position as exclusive shut slots he never shut:
    # «في آخر الألفاظ (78%) أكثر منه في أولها (36%)» is mostly, not only.
    position_kind: str = ""
    gesture_ar: str = ""
    source: str
    page: str
    confidence: str                    # "verified" | "high" | "summary"


class LetterIdentity(BaseModel):
    """A root letter's phonetics — stable across every core, so it is published
    once at the top level rather than repeated inside each reading.

    It carries NO gloss, deliberately. The dataset's Ibn Jinnī sound-imitation
    note is one: for خ it reads «يوحي بالأشياء الخشنة الكريهة الجوفاء» — the same
    reading, in inflected form, that this change exists to keep off خ-ي-ر. A
    payload that ships it puts an unconstrained letter gloss one line away from
    being rendered beside the root again, and a substring guard on
    «خشونة»/«خواء» would not even see it. Meaning belongs to a reading, and a
    reading belongs to a core.
    """

    index: int                         # 1-based position in the root
    letter: str
    name: str
    makhraj: str
    sifat: list[str] = []
    position: str                      # "initial" | "medial" | "final"
    sense_count: int


class DiscardedSense(BaseModel):
    """A sense the core did not admit, kept visible with why it was dropped.

    Hiding these would leave the reader with a single gloss again, only a
    different one — and the bundle is the whole point of the change.
    """

    sense: LetterSense
    # "no-shared-axis" | "conflicting-axis" | "wrong-position" | "outranked"
    reason: str


class LetterReading(BaseModel):
    """What one core made of one letter. `selected` is null when nothing was
    eligible — the gap is shown, never filled with the letter's first or
    most-confident sense."""

    index: int
    letter: str
    selected: LetterSense | None = None
    matched_axes: list[str] = []
    selection_rule: str                # "axis-match" | "axis-match+position" | "unmatched"
    discarded: list[DiscardedSense] = []


# ── the guard ─────────────────────────────────────────────────────────────

class Divergence(BaseModel):
    """The reading's aggregate pole contradicts its own core's polarity.

    A DETECTOR: it reports and changes nothing. A guard that re-ranked until the
    poles agreed would make the tool incapable of ever disagreeing with the aṣl.
    """

    core_polarity: str
    reading_polarity: str
    letters: list[str] = []
    message: str                       # Arabic, shown as its own banner


class Reading(BaseModel):
    """One complete reading, built from ONE core. Never a blend: a root with two
    aṣl gets two readings, and their axes are never pooled."""

    core: RootCore
    letters: list[LetterReading] = []
    synthesis: str = ""
    divergence: Divergence | None = None


class LetterInventory(BaseModel):
    """The unconstrained path: a letter's bundle, nothing selected.

    `senses` holds those the authority scopes to where this letter actually
    sits; `out_of_position` holds the rest — kept on the page rather than
    dropped, the way `discarded` keeps a rejected sense on the constrained path.
    Offering the ر of ح-ر-ب a sense its own source scopes to «بدايات المصادر»
    prints a position beside a sense that ignores it, which reads as evidence.
    """

    index: int
    letter: str
    senses: list[LetterSense] = []
    out_of_position: list[LetterSense] = []


class IshtiqaqItem(BaseModel):
    form: str
    gloss: str


class LisanResponse(BaseModel):
    """`constrained` is the fork.

    True  → `readings` holds one entry per core, each with its own selections.
    False → `readings` is empty, `warning` says why in Arabic, and `inventory`
            lists the letters' senses with none selected. There is no synthesis
            on that path and no setting that restores one.
    """

    word: str
    root: str | None
    root_source: str | None = None      # "qac" | "fallback" | None
    # The ATTESTED layer, and it is published before anything composed from it.
    # `occurrence_verses` is the exhaustive reference list — the page shows a
    # handful and sends the reader to «دراسة الآية» for the vocalized display
    # with highlighting, which is that page's job and not this one's. These used
    # to reach the screen only through the concept engine's confrontation block,
    # which made an attested fact depend on an experimental route staying up.
    occurrences: int = 0                # distinct āyāt
    occurrence_words: int = 0           # distinct WORDS — 339 for رحم against 313 āyāt
    occurrence_verses: list[str] = []
    # The distinct ألفاظ — WRITTEN forms, proclitics stripped, grammatical-tool
    # occurrences out — exactly what «الكلمة في الآيات» lists. NOT
    # `morphology.json`'s `forms_found`, which is vocalized surfaces and counted
    # `رَحْمَةً` / `رَحْمَةٍ` / `رَحْمَةُ` as three ألفاظ of one written form.
    forms: list[str] = []
    constrained: bool = False
    letters: list[LetterIdentity] = []
    cores: list[RootCore] = []
    readings: list[Reading] = []
    inventory: list[LetterInventory] = []
    # id → Arabic label for every axis named anywhere above, so the UI renders
    # axis names without holding a copy of the vocabulary.
    axis_labels: dict[str, str] = {}
    # Why there is no core — set with `warning`, null on every other path.
    # «no core» has three causes and conflating them made the page state that
    # Maqāyīs holds no aṣl for حرب, where Ibn Fāris gives three. The project's
    # own gap (`not_curated`, `not_recorded`) is freely reported; his silence
    # (`no_asl_in_source`) only where the dataset positively records it.
    core_status: str | None = None      # "not_curated" | "not_recorded" | "no_asl_in_source"
    warning: str | None = None          # set when `constrained` is false
    synthesis_source: str = "template"  # origin of every `synthesis` (auditable)
    ishtiqaq_akbar: list[IshtiqaqItem] = []
    disclaimer: str
    sources: dict[str, str] = {}
    message: str | None = None          # set when root could not be resolved


# ── the physics-first engine: مفهوم from the letters, aṣl afterwards ──────
#
# A SECOND engine, mounted beside the first and sharing nothing with it but this
# file and the root resolver. Everything above is CORE-FIRST: the attested aṣl
# selects among each letter's sourced senses. Everything below is the inverse —
# the concept is composed from the tajwīd description of the root's letters and
# from nothing else, and Ibn Fāris arrives afterwards as the TEST. The two are
# published side by side until the comparison is done; neither is labelled
# correct.
#
# The models are flatter than the core-first ones on purpose. There is nothing to
# select, so there is no `discarded`, no `matched_axes` and no `selection_rule`:
# a letter's primitives are ALL returned, ordered by the published rule, cut into
# `realised` and `carried` by a published window. A reader can re-derive the
# order by hand from `coverage` and `declaration_index`, which is why both travel
# with every hit.


class PrimitiveHitModel(BaseModel):
    """One primitive a letter carries, with the table row that licensed it.

    `status` is the sourcing regime and the page MUST distinguish on it.
    `attested` means a named authority with real pages states this mapping;
    `hypothesis` means the project asserts it, carrying an uncontested tajwīd
    fact as its `physical_basis` and citing support without borrowing authority.
    Most rows are hypotheses — no source tabulates the ṣifāt into a general
    quality-to-notion mapping — and that is precisely what makes `k / 40` able to
    falsify them. A screen that rendered both alike would publish the project's
    construction with Ibn Jinnī's face on.

    `coverage` is how many of the 28 letters carry this primitive, and it is the
    ordering signal: rarest first. `declaration_index` is the table's own row
    order, which breaks every tie — together they make the sort total, which is
    what makes two fresh processes agree.
    """

    primitive: str
    feature: str
    gloss_ar: str
    status: str                        # "attested" | "hypothesis"
    coverage: int
    declaration_index: int


class PositionReadingModel(BaseModel):
    """One radical read at one fixed slot, with its whole evidence chain.

    `position` is the rule, not a label: `opens` · `body` · `concludes`, in that
    order, always. The Arabic wording belongs to the page — the same division of
    labour `LetterIdentity.position` already follows.

    `letter` is the glyph as the root key spells it and is never rewritten;
    `sheet_letter` is the row it was read from, which differs for a hamza seat
    (`أ` → `ء`) and is null when the sheet has no row at all.

    `ordered` is everything the letter carries, `realised` its first three,
    `carried` the remainder. `carried` is published rather than dropped: the cut
    is a display budget, not a claim that the rest are absent.
    """

    position: str                      # "opens" | "body" | "concludes"
    letter: str
    sheet_letter: str | None = None
    makhraj_ar: str = ""
    features: list[str] = []
    ordered: list[PrimitiveHitModel] = []
    realised: list[PrimitiveHitModel] = []
    carried: list[PrimitiveHitModel] = []
    silent: bool = False
    silent_reason: str = ""            # Arabic; says WHOSE gap it is


class ConceptModel(BaseModel):
    """A root's composed مفهوم, or a stated refusal to compose one.

    `refused` and `partial` are different failures and the page must not merge
    them. `refused` — the rule does not cover this root at all (a quadriliteral);
    `positions` is empty and `refusal_reason` carries the Arabic statement.
    `partial` — the rule applied and one position is silent; the concept exists
    and is honestly short by that position.

    `sentence` is the ground truth and the thing the metric is measured on. The
    page may GROUP the realised primitives by position for readability (§D6), and
    grouping is all it may do: the chain is shown verbatim beside the groups.

    `phrasing_rejection` is non-empty in exactly one case — a phrasing was
    produced and the containment veto refused it. It is not set when the optional
    pass is off, nor when the model failed: «the model invented something» and
    «the model was not running» must not look the same.
    """

    root: str
    refused: bool = False
    refusal_code: str = ""
    refusal_reason: str = ""
    positions: list[PositionReadingModel] = []
    realised_primitives: list[str] = []
    sentence: str = ""
    sentence_source: str = "template"  # "template" | "phrasing"
    phrasing_rejection: str = ""
    partial: bool = False
    silent_letters: list[str] = []
    lock_version: str                  # the table version this was produced under


class AttestedUseModel(BaseModel):
    """One Quranic sense frozen for a root BEFORE its concept was generated.

    `verdict` is `covered`, `not_covered`, or `not_judged` — the last being the
    mandated intermediate state, not a third grade. `reason` is required on
    anything that is not covered, and it is the only thing that lets a reader who
    disagrees redo the judgement.
    """

    gloss: str
    verse: str                         # "s:a"
    verdict: str                       # "covered" | "not_covered" | "not_judged"
    reason: str = ""


class ConfrontationModel(BaseModel):
    """What is attested for the root, set beside the concept — a report only.

    This is the far side of the pipeline and the whole reason the engine exists:
    the aṣl arrives AFTER the answer, so the two can disagree. Nothing here feeds
    back into the concept, and there is no path in the engine that would let it.

    `core_status` says whose silence it is when `cores` is empty —
    `not_curated` (he states an aṣl, we have not transcribed it), `not_recorded`
    (no Maqāyīs row, or one the parser could not read) or `no_asl_in_source`
    (his entry itself formulates none). It is "" when cores exist.

    `counts_toward_k` is a published exclusion, never a silence: `ضرب` and every
    root off the 40-root holdout are confronted and shown like any other, and
    contribute to neither half of the metric.
    """

    cores: list[RootCore] = []
    core_status: str = ""
    occurrences: int = 0
    verses: list[str] = []
    uses: list[AttestedUseModel] = []
    verdict: str = "not_recorded"      # "covers_all" | "partial" | "not_recorded"
    uses_frozen_at: str = ""
    concept_recorded_at: str = ""
    in_witness_set: bool = False
    counts_toward_k: bool = False


class ConceptRequest(BaseModel):
    word: str


class ConceptResponse(BaseModel):
    """`root: null` with a `message` when nothing resolves — never a 500.

    `concept` and `confrontation` are both null on that path and both present
    otherwise, including when the concept is refused: a refusal is an answer the
    page displays, not an empty panel.
    """

    word: str
    root: str | None
    root_source: str | None = None     # "qac" | "fallback" | None
    concept: ConceptModel | None = None
    confrontation: ConfrontationModel | None = None
    # The window reservation (§D11), carried in the response rather than left to
    # the page: any surface that prints a coverage verdict must print it with the
    # number, and `confrontation.verdict` IS a coverage verdict.
    metric_reservation: str = ""
    disclaimer: str
    message: str | None = None
