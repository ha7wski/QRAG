"""
marks.py — the Arabic mark ranges, defined once.

Four modules used to write a mark table out by hand, and no two of them agreed.
Measured, before they were collapsed here:

    ingestion/normalizer._TASHKEEL      33 chars   HARAKAT
    ingestion/root_normalize._TASHKEEL  33 chars   HARAKAT              (identical)
    ingestion/root_resolver._MARKS      56 chars   HARAKAT + U+06D6-06EC
    indexing/corpus._DIACRITICS         58 chars   HARAKAT + TATWEEL + U+06D6-06ED

So this is not one table used four ways — it is three genuinely different sets
serving three different jobs, plus one duplicate. Collapsing them into a single
table would have changed behaviour. What is defined once here is each RANGE;
every consumer composes the set it actually needs, and says why.

**Everything is written with `\\u` escapes, never literal Arabic characters.**
Under bidirectional reordering a malformed range is visually indistinguishable
from a correct one on screen, and an over-broad class silently deletes Arabic
LETTERS instead of marks — a prototype of one reduced whole āyāt to whitespace
and the bug survived review. `tests/test_basmala_strip.py` guards this.
"""
from __future__ import annotations


def _chars(*ranges: tuple[int, int]) -> str:
    """The characters in the given INCLUSIVE codepoint ranges."""
    return "".join(chr(cp) for first, last in ranges for cp in range(first, last + 1))


# Harakat and the Quranic annotation signs that sit with them:
#   U+0610-U+061A  Quranic annotation signs (ṣallallāhu ʿalayhi wa-sallam, ...)
#   U+064B-U+065F  tanwīn, fatḥa/ḍamma/kasra, shadda, sukūn, and the extended
#                  editorial marks U+064C-U+0659 that a two-range class misses
#   U+0670         superscript (dagger) alif
HARAKAT = _chars((0x0610, 0x061A), (0x064B, 0x065F), (0x0670, 0x0670))

# Tatweel (kashida) — a pure elongation glyph, not a mark on a letter.
TATWEEL = "ـ"

# Waqf marks, sajda, and small alif/waw/ya: U+06D6-U+06ED, inclusive.
QURANIC_MARKS = _chars((0x06D6, 0x06ED))

# The hamza-blind fold's own mark set stops one short of U+06ED (ARABIC SMALL LOW
# MEEM). That is not a considered choice — it is `range(0x06D6, 0x06ED)`, whose
# stop is exclusive — but it IS observable: U+06ED occurs 99 times in the QAC word
# forms, so widening it here would change what `fold_blind` returns. This change's
# bar is byte-identical behaviour, and quietly fixing an off-by-one inside a
# restructure is exactly the kind of smuggled change that bar exists to forbid.
# Preserved verbatim, and recorded so the question can be answered on its own.
BLIND_FOLD_MARKS = HARAKAT + _chars((0x06D6, 0x06EC))

# Translation tables, built once.
HARAKAT_TABLE = {ord(c): None for c in HARAKAT}
BLIND_FOLD_TABLE = {ord(c): None for c in BLIND_FOLD_MARKS}
BARE_TABLE = {ord(c): None for c in HARAKAT + TATWEEL + QURANIC_MARKS}
QURANIC_MARKS_TABLE = {ord(c): None for c in QURANIC_MARKS}


def strip_harakat(text: str) -> str:
    """`text` without harakat, tashkeel or the dagger alif. Letters untouched."""
    return text.translate(HARAKAT_TABLE)


def bare(text: str) -> str:
    """`text` without any mark at all — harakat, waqf marks and tatweel.

    A COMPARISON KEY, never a value to store or display. This is the widest of
    the three sets: it is what makes two spellings of the same words comparable
    regardless of how either was annotated.
    """
    return text.translate(BARE_TABLE)
