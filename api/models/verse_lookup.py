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


class VerseLookupResponse(BaseModel):
    word: str
    root: str
    root_found: bool
    total: int
    verses: list[VerseLookupVerse]
