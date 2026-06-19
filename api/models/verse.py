"""Pydantic models for verses and search responses."""
from __future__ import annotations

from pydantic import BaseModel


class Verse(BaseModel):
    id: str                       # e.g. "2:255"
    surah_number: int
    surah_name_ar: str
    surah_name_en: str = ""
    surah_name_fr: str = ""
    ayah_number: int
    text_ar: str
    text_ar_clean: str = ""
    translation_fr: str = ""
    translation_en: str = ""
    period: str = ""
    juz: int = 0
    relevance_score: float | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[Verse]
    total: int


class VerseDetailResponse(BaseModel):
    """A single verse plus its in-surah neighbor context (P1 deep-linking)."""

    verse: Verse
    context: list[Verse]          # neighbors within ±window, includes the verse
    prev_id: str | None = None    # canonical id of the previous verse, if any
    next_id: str | None = None    # canonical id of the next verse, if any


class SurahMeta(BaseModel):
    """Lightweight surah entry for the surah picker."""

    number: int
    name_ar: str = ""
    name_en: str = ""
    name_fr: str = ""
    ayah_count: int


class SurahResponse(BaseModel):
    """A full surah: ordered verses + lightweight metadata."""

    surah_number: int
    surah_name_ar: str = ""
    surah_name_en: str = ""
    surah_name_fr: str = ""
    period: str = ""
    ayah_count: int
    verses: list[Verse]


def verse_from_record(record: dict) -> Verse:
    """Build a Verse model from a retriever/pipeline record dict."""
    return Verse(
        id=record["id"],
        surah_number=record["surah_number"],
        surah_name_ar=record.get("surah_name_ar", ""),
        surah_name_en=record.get("surah_name_en", ""),
        surah_name_fr=record.get("surah_name_fr", ""),
        ayah_number=record["ayah_number"],
        text_ar=record.get("text_ar", ""),
        text_ar_clean=record.get("text_ar_clean", ""),
        translation_fr=record.get("translation_fr", ""),
        translation_en=record.get("translation_en", ""),
        period=record.get("period", ""),
        juz=record.get("juz", 0),
        relevance_score=record.get("score"),
    )
