"""Pydantic models for the Tahlil (five-block word analysis) endpoints.

Shape mirrors QLisan's fiche — an ordered list of independently-labelled blocks, each
carrying its own `available` flag and an explanatory `message` when it is not — because
the two pages sit side by side and a reader should not have to learn two layouts. What
differs is epistemic: QLisan is deterministic end to end, while ~80 % of Tahlil's prose is
generated, so **every claim carries a badge and its citations travel with it** rather than
living in a footnote.

THE BADGE VOCABULARY IS IMPORTED, NEVER RE-DECLARED. `tahlil/citations.py` owns the three
badge strings, their labels and their tooltips because it is the module that ENFORCES them:
the gate compares a claim's badge against those exact strings. A literal copy here would be
the third instance of the "two tables drift apart invisibly" failure this change has already
been bitten by (the letters dataset, the badge labels) — and it would drift in the worst
direction, since a claim whose badge string stopped matching the gate's would be silently
rejected as un-badged and vanish from the page with no error anywhere.
"""
from __future__ import annotations

from pydantic import BaseModel

# Re-exported so the API layer (and its tests) have exactly ONE badge vocabulary, by
# identity, not by copy. `BADGES` is the closed set, `BADGE_LABELS`/`BADGE_TOOLTIPS` the
# specified display strings of design decision 3b (contract, not UI choice: «مُولَّد» must
# say «غير مُحقَّق» in words, and تأويلي must differ from محقّق in LABEL TEXT so the
# distinction survives greyscale and a screenshot).
from tahlil.citations import (  # noqa: F401  (re-export is the point)
    BADGE_GENERATED,
    BADGE_INTERPRETIVE,
    BADGE_LABELS,
    BADGE_TOOLTIPS,
    BADGE_VERIFIED,
    BADGES,
    UNVERIFIED_MENTION,
)

# The five block ids, in their one rendering order — also imported from the module that
# enforces block membership, for the same reason as the badges.
from tahlil.tahlil_service import BLOCKS_ORDER  # noqa: F401


class TahlilWordRequest(BaseModel):
    surah: int
    ayah: int
    word: int  # 1-based QAC word_id — identical to the QLisan token index by construction


class TahlilReviewRequest(BaseModel):
    """An expert marking one analysis reviewed. `ref` is «surah:ayah:word»."""

    ref: str
    reviewer: str = ""
    note: str = ""


class Claim(BaseModel):
    """One assertion on the page: its text, its provenance badge, and its evidence.

    `cites` are machine-readable evidence ids (`letter:…`, `nazir:…`, `sigha:…`,
    `contrast:…`, `maqayis:…`, `qac:…`) that resolve in the bundle that produced the claim;
    `sources` are the human-readable citation-strip lines (author + page, KB row id +
    version, the treebank). Both travel WITH the claim rather than under the block, because
    the guarantee is per-assertion: a block-level citation list would let one anchored
    sentence lend its provenance to an unanchored neighbour.
    """

    text_ar: str
    badge: str  # one of BADGES — the licensed badge, never the one a generator asked for
    cites: list[str] = []
    sources: list[str] = []


class Block(BaseModel):
    """One of the five levels.

    `available` false is a first-class outcome, never an error: it means we had nothing we
    could anchor, and `message` says why in Arabic (a rootless word, a missing lexical
    anchor, a model that is off or unreachable). An empty card with no message would read
    as «this level has nothing to say about this word», which is a different and false
    statement.
    """

    id: str
    title_ar: str
    available: bool = False
    message: str | None = None
    claims: list[Claim] = []
    # `{source, disclaimer}` for a block whose evidence rests on a named framework — today
    # only الحروف, whose دلالة rows come from a contested school. Served rather than left to
    # the page: the module that owns the dataset is the one that knows what must be said
    # about it, so a dataset upgrade cannot leave a stale disclaimer behind.
    attribution: dict | None = None


class TahlilWordResponse(BaseModel):
    """The five-block analysis of one word.

    `blocks_order` is served explicitly rather than left implicit in a dict's insertion
    order: the order الحروف → صرفي → نحوي → دلالي → تركيب is presentation contract (sound,
    then form, then syntax, then meaning, and only then the synthesis), so a client must be
    able to assert it instead of inferring it.

    `generation_enabled` and `reviewed` are the two honesty flags the UI renders: the first
    tells the reader whether any prose was even attempted, the second whether a human has
    looked at it. `reviewed` defaults false and is returned with EVERY analysis — reviewing
    never gates rendering, it only removes the «غير مُحقَّق» mention.
    """

    ref: str  # "surah:ayah:word"
    surah: int
    ayah: int
    word: int
    word_vocalized: str = ""  # from the chakl corpus, never the QAC `uthmani` field
    blocks_order: list[str] = list(BLOCKS_ORDER)
    blocks: dict[str, Block] = {}
    reviewed: bool = False
    generation_enabled: bool = False

    # The badge vocabulary travels ON THE WIRE, and that is the point of decision 3b rather
    # than an over-delivery. The labels and tooltips are *contract*: «مُولَّد» must say «غير
    # مُحقَّق» in words, and تأويلي must differ from محقّق in LABEL TEXT so the distinction
    # survives greyscale and a screenshot. A frontend holding its own copy of those strings
    # can drift from the gate that assigns them — silently, and in the one direction that
    # matters, since a stale tooltip reading «verified» over a generated claim is exactly
    # the misreading the badges exist to prevent. Serving them keeps ONE vocabulary, by
    # identity: the page renders what the module that badged the claim says it means.
    badge_labels: dict[str, str] = dict(BADGE_LABELS)
    badge_tooltips: dict[str, str] = dict(BADGE_TOOLTIPS)
    unverified_mention: str = UNVERIFIED_MENTION

    # The closed badge set in CAUTION ORDER — محقّق, then مُولَّد, then تأويلي. Served so a
    # client can answer «which of these claims should a reader approach most carefully?»
    # without hardcoding the three Arabic keys or, worse, guessing them from a mapping's
    # iteration order. That ordering is a design statement, not a UI preference: تأويلي
    # names a contested framework, مُولَّد names anchored-but-unverified prose, and a card
    # summarising a mixed block must announce the weakest provenance it contains, never the
    # commonest — a card of four facts and one interpretation is one a reader must approach
    # as interpretive.
    badges: list[str] = list(BADGES)


class TahlilReviewResponse(BaseModel):
    ref: str
    reviewed: bool
    reviewer: str = ""
    note: str = ""
    reviewed_at: float | None = None


# `TahlilVerseRequest` / `TahlilVerseResponse` lived here for `POST /tahlil/verse`, which no
# page ever called and which is no longer mounted. They went with it: an unserved wire shape
# is a shape nothing can hold to its word. The verse synthesis they described is still built
# by `tahlil_service.analyze_verse` and still tested there, so re-serving it means declaring
# the models again next to a handler — not reconstructing what they meant.
