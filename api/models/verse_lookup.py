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


class VerseLookupLemma(BaseModel):
    root: str                       # the root this lemma belongs to
    lemma: str                      # normalized lemma key
    lemma_display: str              # diacritized lemma label for display
    count: int                      # number of verses under this lemma
    verses: list[VerseLookupVerse]


class VerseLookupResponse(BaseModel):
    word: str
    root: str                       # " / "-joined root(s), for back-compat display
    roots: list[str]                # every matched root (homographs → several)
    root_found: bool                # True also for a resolved proper noun
    is_proper_noun: bool = False    # rootless name (لوط …): lemmas has one group
    total: int                      # distinct verses across all lemma groups
    lemmas: list[VerseLookupLemma]  # a root's occurrences split per lemma
