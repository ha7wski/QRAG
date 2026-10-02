"""Pydantic models for the Verse Lookup endpoint (exhaustive root lookup)."""
from __future__ import annotations

from pydantic import BaseModel


class VerseLookupRequest(BaseModel):
    word: str


class VerseLookupVerse(BaseModel):
    surah_number: int
    surah_name: str
    aya_number: int
    text: str                       # vocalized (with full diacritics)
    match_indices: list[int]        # token indices in `text` to highlight


class VerseLookupForm(BaseModel):
    """One لفظ — a WRITTEN form of the root, with the verses that spell it so.

    Not a lemma: `آيات`, `آياتنا` and `آياته` are three ألفاظ of the one lemma
    آيَة. The lemma is gone from this contract entirely; it survives only as an
    internal input to the highlighter (see `retrieval/verse_lookup.py`).
    """

    root: str                       # the root this form belongs to; "" for a name
    form: str                       # the لفظ itself — marks removed, proclitics off
    count: int                      # distinct āyāt in this block
    occurrences: int                # words carrying this form
    verses: list[VerseLookupVerse]


class VerseLookupResponse(BaseModel):
    word: str
    root: str                       # " / "-joined root(s), for back-compat display
    roots: list[str]                # every matched root (homographs → several)
    root_found: bool                # True also for a resolved proper noun
    is_proper_noun: bool = False    # rootless name (لوط …), grouped by لفظ too
    # The name's vocalized spelling (لُوط), which the header used to read from the
    # first lemma group. Top-level because the grouping it lived in is gone.
    proper_noun_display: str = ""
    occurrences: int = 0            # distinct WORDS carrying the root
    total: int                      # distinct āyāt — NOT the sum of the blocks:
    #                                 19 of أيي's 353 hold two ألفاظ and would
    #                                 otherwise be counted twice.
    forms: list[VerseLookupForm]    # one block per لفظ, first occurrence first
    # Only when nothing was found: Quranic words one confusable letter away
    # (العضيم → العظيم), most frequent first. Offered, never followed.
    suggestions: list[str] = []
