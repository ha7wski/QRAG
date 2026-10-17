"""Pydantic models for GET /surah/{number}/similar — close verses inside one surah.

The surah's groups of mutually close verses (the per-verse `?ayah=` view was
removed with the page that read it). Every verse is the
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


class SurahGroupCount(BaseModel):
    """One surah of the overview chart: its name and how many groups it holds."""

    surah_number: int
    surah_name_ar: str = ""
    groups: int


class SurahSimilarityOverview(BaseModel):
    """GET /surah-similarity/overview — the surahs holding ≥ 1 group, mushaf order."""

    surahs: list[SurahGroupCount]
