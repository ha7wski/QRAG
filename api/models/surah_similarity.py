"""Pydantic models for GET /surah/{number}/similar — close verses inside one surah.

Two shapes from one route: without `ayah`, the surah's groups of mutually close
verses; with `?ayah=a`, that verse's ranked close verses. Every verse is the
shared `Verse`, built through `verse_from_record`, so it carries
`text_ar_tashkil` with the Basmala stripped like every other verse the API emits.
"""
from __future__ import annotations

from pydantic import BaseModel

from api.models.verse import Verse


class SimilarityGroup(BaseModel):
    """A connected set of mutually close verses, with its mean internal score."""

    ayahs: list[int]
    strength: float
    verses: list[Verse]               # same order as `ayahs`


class SurahSimilarityResponse(BaseModel):
    """The surah view: its groups (strongest first) and its unscored ayahs."""

    surah_number: int
    surah_name_ar: str = ""
    ayah_count: int
    unscored: list[int]               # verses with no content root — never compared
    groups: list[SimilarityGroup]


class SimilarNeighbour(BaseModel):
    """One close verse of the anchor, with the content roots the two share."""

    verse: Verse
    score: float
    roots: list[str]


class AyahSimilarityResponse(BaseModel):
    """The anchor view: one verse and its close verses, in dataset (score) order.

    `unscored: true` with no neighbours means the anchor carries no content word
    and was not compared; `unscored: false` with no neighbours means it was
    compared and nothing passed both gates.
    """

    surah_number: int
    surah_name_ar: str = ""
    ayah_count: int
    anchor: Verse
    unscored: bool
    neighbours: list[SimilarNeighbour]
