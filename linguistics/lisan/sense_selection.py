"""
sense_selection.py — choose one sense per letter, constrained by an attested core.

A letter carries a BUNDLE of sourced senses; which member applies depends on
what the root actually means. This module is that decision, and nothing else:
given a letter's senses, one core's axes, the antonym links and the letter's
position in the root, it returns the sense the core admits, the axes they
shared, the rule that selected it, and every sense it dropped with the reason.

**PURE.** No disk, no network, no dataset import, no clock, no randomness — every
input arrives as an argument, so the whole mechanism is unit-testable on
hand-built senses and its output depends on nothing else in the process.

**No model is involved, deliberately.** This feature has already been burned by
generation twice: the Lisan synthesis was an LLM step until a local model
produced corrupted tokens and fluent prose contradicting the attested sense, and
`/madar` is quarantined for the same reason. A model in the *selection* step
would rebuild that failure one layer down, where it is far harder to see — the
prose would then read as sourced, because each of its glosses is, while the
choice among them stayed unaccountable. The ranking below is a fixed, total
tuple precisely so a reader can re-derive any selection by hand.

The four terms of that tuple, highest first:

    (shared axes, position fit, source confidence, −declaration index)

`−declaration index` is not a tie-breaker of last resort by accident: it makes
ties fall to the curator's own ordering rather than to dict iteration order,
which is what keeps the same input reproducible across processes.
"""
from __future__ import annotations

# The three positions a sense may be scoped to, plus `any`. `any` is the default
# in the dataset (Ḥasan ʿAbbās does not state a position for every sense), so it
# must cost nothing: it scores a position fit of 1 — the sense does apply here —
# while `selection_rule` still records that it did not match the letter's ACTUAL
# position, so a reader can tell a real positional match from a default.
POSITION_INITIAL = "initial"
POSITION_MEDIAL = "medial"
POSITION_FINAL = "final"
POSITION_ANY = "any"

# Rejection reasons, as `api.models.lisan.DiscardedSense.reason` names them.
REASON_NO_SHARED_AXIS = "no-shared-axis"
REASON_CONFLICTING_AXIS = "conflicting-axis"
REASON_OUTRANKED = "outranked"

# Selection rules, as `api.models.lisan.LetterReading.selection_rule` names them.
RULE_AXIS_MATCH = "axis-match"
RULE_AXIS_MATCH_POSITION = "axis-match+position"
RULE_UNMATCHED = "unmatched"

# Source confidence, ranked. An unknown value scores 0 rather than raising: a
# miscurated confidence must not be able to take the page down, and scoring it
# below every real value means it can only ever lose a tie.
_CONFIDENCE_RANK = {"verified": 3, "high": 2, "summary": 1}

# Poles, and their Arabic names for the divergence message.
_POLE_AR = {"positive": "إيجابية", "negative": "سلبية", "neutral": "محايدة"}


def letter_position(index: int, root_length: int) -> str:
    """Where the letter at 0-based `index` sits in a root of `root_length`.

    First is `initial`, last is `final`, anything between is `medial`. A
    1-letter root is `initial` (the first test wins, so a degenerate root still
    gets a position rather than an empty string); a 2-letter root is initial
    then final and has no medial slot.
    """
    if index <= 0:
        return POSITION_INITIAL
    if index >= root_length - 1:
        return POSITION_FINAL
    return POSITION_MEDIAL


def _positions_of(sense) -> tuple[str, ...]:
    """A sense's declared positions, as a tuple — a SET, never one value.

    Ḥasan ʿAbbās does not always speak one position at a time: for ح he states
    «في الأول: …» and then «**في الآخر والوسط**: …» — one predicate covering two
    positions. Encoding that as two rows produced the only duplicate the sheet
    ever held (identical gloss, identical axes, two `position` cells); encoding
    it as `any` would contradict the «في الأول» he states separately. A list is
    the only shape that says exactly what he says.

    A blank cell means `any`: a sense that names no position is not restricted
    to one.
    """
    raw = sense.get("position") if isinstance(sense, dict) else None
    if isinstance(raw, str):
        raw = [p.strip() for p in raw.split(";") if p.strip()]
    return tuple(raw or (POSITION_ANY,))


def _position_fit(sense_positions, letter_position_: str) -> int:
    """1 when the sense applies where the letter actually sits, else 0."""
    positions = set(sense_positions)
    return 1 if (letter_position_ in positions or POSITION_ANY in positions) else 0


def _conflicting_axes(core_axes, antonyms: dict[str, str]) -> set[str]:
    """The axes declared opposed to one of the core's.

    The relation is read from BOTH sides on purpose. The dataset's links are
    validated as symmetric, but this module is pure and is meant to be usable on
    hand-built inputs — and reading only `core axis → its antonym` meant that a
    map declaring the link on the SENSE's side alone let the opposed sense be
    SELECTED, silently, which is the one outcome the reason
    `conflicting-axis` exists to make impossible. Opposition is a property of the
    pair, so neither side may be the only one that counts.

    A core naming two mutually antonymous axes yields a conflict set that
    intersects its own axes, so every sense is rejected and the letter reads
    `unmatched`. That is the intended outcome: such a core is miscurated, and an
    all-discarded reading says so where a partial match would hide it.
    """
    core = set(core_axes)
    forward = {antonyms[a] for a in core if a in antonyms}
    backward = {axis for axis, opposite in (antonyms or {}).items() if opposite in core}
    return forward | backward


def select_for_letter(senses, core_axes, antonyms: dict[str, str],
                      position: str) -> dict:
    """Select the one sense of `senses` that a core with `core_axes` admits.

    Returns the `LetterReading` payload minus `index`/`letter`:
    `{"selected", "matched_axes", "selection_rule", "discarded"}`.

    Eligibility runs the conflict test FIRST, on purpose: a sense carrying the
    declared contrary of a core axis is rejected whatever else it happens to
    share, and it is rejected as `conflicting-axis` — the informative reason —
    rather than being ranked on its accidental overlap.

    When nothing is eligible, `selected` is None and every sense appears in
    `discarded`. There is no fallback to the first, the most-confident or the
    most-frequent sense: the honest partial reading is the product, and silently
    filling that gap is exactly the behaviour this module replaces.
    """
    core = set(core_axes or ())
    conflicts = _conflicting_axes(core, antonyms or {})

    # (rank key, declaration index, sense, shared axes) for each eligible sense,
    # plus the rejection reason for each ineligible one. Declaration order is
    # preserved throughout so `discarded` comes back deterministically.
    eligible: list[tuple[tuple[int, int, int, int], int, dict, set[str]]] = []
    rejected: dict[int, str] = {}

    for i, sense in enumerate(senses or []):
        axes = set(sense.get("axes") or ())
        if axes & conflicts:
            rejected[i] = REASON_CONFLICTING_AXIS
            continue
        shared = axes & core
        if not shared:
            rejected[i] = REASON_NO_SHARED_AXIS
            continue
        fit = _position_fit(_positions_of(sense), position)
        confidence = _CONFIDENCE_RANK.get(sense.get("confidence") or "", 0)
        eligible.append(((len(shared), fit, confidence, -i), i, sense, shared))

    winner_index = -1
    selected = None
    matched_axes: list[str] = []
    rule = RULE_UNMATCHED
    if eligible:
        _, winner_index, selected, shared = max(eligible, key=lambda e: e[0])
        matched_axes = sorted(shared)
        # `axis-match+position` only when the sense named the letter's ACTUAL
        # position. `any` fits everywhere, so reporting it as a positional match
        # would claim evidence the citation never gave.
        sense_positions = _positions_of(selected)
        rule = (RULE_AXIS_MATCH_POSITION
                if POSITION_ANY not in sense_positions
                and _position_fit(sense_positions, position)
                else RULE_AXIS_MATCH)

    discarded = [
        {"sense": sense, "reason": rejected.get(i, REASON_OUTRANKED)}
        for i, sense in enumerate(senses or [])
        if i != winner_index
    ]

    return {
        "selected": selected,
        "matched_axes": matched_axes,
        "selection_rule": rule,
        "discarded": discarded,
    }


def select_for_root(letters, core_axes, antonyms: dict[str, str]) -> list[dict]:
    """Read a whole root under ONE core: one `LetterReading` dict per letter.

    `letters` is the ordered per-letter data from `letter_lexicon.describe()`;
    `core_axes` is that ONE core's axis ids — a bare list, not the core record,
    so this module stays ignorant of `root_cores.json`'s shape and remains
    testable on hand-built inputs with no dataset knowledge at all.

    One core per call, and the readings are never merged: pooling the axes of
    ظلم's two aṣl would make almost any sense eligible and rebuild the blend
    this whole design removes.
    """
    core_axes = set(core_axes or ())
    letters = list(letters or [])
    total = len(letters)
    readings: list[dict] = []
    for i, letter in enumerate(letters):
        reading = select_for_letter(
            letter.get("senses") or [], core_axes, antonyms,
            letter_position(i, total),
        )
        readings.append({
            "index": i + 1,                       # 1-based, as the API publishes it
            "letter": letter.get("letter", ""),
            **reading,
        })
    return readings


def detect_divergence(letter_readings, core_polarity: str) -> dict | None:
    """Report — never repair — a reading whose charge contradicts its own core.

    READ-ONLY BY CONSTRUCTION: it is handed the finished selection and the core's
    polarity, and nothing else. It has no access to the sense pool, so it CANNOT
    re-rank, drop or substitute a sense even by accident. A guard that silenced
    itself by editing the reading would make the tool incapable of ever
    disagreeing with the aṣl — it would always appear to confirm the citation,
    which is a worse failure than the one it exists to catch.

    A firing guard is information about the DATA: the letter senses, the core's
    axes or its polarity need curating. It is not a defect in the reading, and
    a guard that never fires at all is a warning sign, not a success — it would
    suggest the letter senses were curated to fit the cores.

    Returns the `Divergence` payload, or None when there is nothing to report.
    """
    selected = [r.get("selected") for r in (letter_readings or []) if r.get("selected")]
    positives = sum(1 for s in selected if s.get("pole") == "positive")
    negatives = sum(1 for s in selected if s.get("pole") == "negative")

    if positives > negatives:
        reading_polarity = "positive"
    elif negatives > positives:
        reading_polarity = "negative"
    else:
        # A tie, or nothing selected: the reading makes no aggregate claim.
        reading_polarity = "neutral"

    # A neutral core never raises a divergence on polarity grounds alone. Ibn
    # Fāris' aṣl is often descriptive — ك-ف-ر's «الستر والتغطية» is neutral, and
    # the root's negative charge is Quranic usage, not etymology. Firing here
    # would turn the dataset into a sentiment lexicon and the guard would go off
    # on every root whose usage and aṣl differ, which is many of them.
    if core_polarity not in ("positive", "negative") or reading_polarity == "neutral":
        return None
    if reading_polarity == core_polarity:
        return None

    # One entry per responsible READING, not per distinct glyph: a doubled
    # letter contributing twice is two positions, and collapsing them would hide
    # one of them from the curator who has to act on this.
    letters = [r.get("letter", "") for r in (letter_readings or [])
               if r.get("selected") and r["selected"].get("pole") == reading_polarity]

    reading_ar = _POLE_AR.get(reading_polarity, reading_polarity)
    core_ar = _POLE_AR.get(core_polarity, core_polarity)
    message = (
        f"الشحنة الإجمالية لهذه القراءة ({reading_ar}) تخالف قطب الأصل المنقول "
        f"({core_ar})، وهذا مؤشر على أن بيانات معاني الحروف أو أقطابها تحتاج "
        f"مراجعة وتحقيقا، ولم يُغيَّر في القراءة شيء."
    )
    return {
        "core_polarity": core_polarity,
        "reading_polarity": reading_polarity,
        "letters": letters,
        "message": message,
    }
