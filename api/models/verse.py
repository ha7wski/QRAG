"""Pydantic models for verses and search responses."""
from __future__ import annotations

from pydantic import BaseModel

from quran_data.corpus import chakl_by_ref, strip_leading_basmala


class Verse(BaseModel):
    id: str                       # e.g. "2:255"
    surah_number: int
    surah_name_ar: str
    surah_name_en: str = ""
    surah_name_fr: str = ""
    ayah_number: int
    text_ar: str
    text_ar_tashkil: str = ""     # fully vocalized (harakat) — for display
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
    # The surah's own opening Basmala, to be shown once as a heading rather than
    # welded onto ayah 1. Empty for al-Fatiha (where it IS ayah 1, already in
    # `verses`) and for at-Tawba (which has none) — so a consumer renders the
    # field when non-empty and holds no scripture rule of its own.
    basmala: str = ""
    verses: list[Verse]


def verse_from_record(record: dict, text_ar_tashkil: str | None = None) -> Verse:
    """Build a Verse model from a retriever/pipeline record dict.

    `text_ar_tashkil` (fully vocalized text) is auto-filled from the shared
    chakl source so every verse shown in the UI is vocalized; pass it
    explicitly only to override.

    The auto-filled text goes through `strip_leading_basmala`: the chakl CSV
    prepends the Basmala to ayah 1 of 113 surahs, and this function is the choke
    point every display surface passes through (`/chat` sources, `/search`,
    `/verse/{s}/{a}`, `/surah/{n}`), so correcting it here corrects all of them
    at once. An explicitly passed override is the caller's own text and is left
    exactly as given.
    """
    if text_ar_tashkil is None:
        entry = chakl_by_ref().get((record["surah_number"], record["ayah_number"]))
        text_ar_tashkil = (
            strip_leading_basmala(
                record["surah_number"], record["ayah_number"], entry["text"]
            )
            if entry
            else ""
        )
    return Verse(
        id=record["id"],
        surah_number=record["surah_number"],
        surah_name_ar=record.get("surah_name_ar", ""),
        surah_name_en=record.get("surah_name_en", ""),
        surah_name_fr=record.get("surah_name_fr", ""),
        ayah_number=record["ayah_number"],
        text_ar=record.get("text_ar", ""),
        text_ar_tashkil=text_ar_tashkil,
        text_ar_clean=record.get("text_ar_clean", ""),
        translation_fr=record.get("translation_fr", ""),
        translation_en=record.get("translation_en", ""),
        period=record.get("period", ""),
        juz=record.get("juz", 0),
        # Prefer the cross-encoder score when the record was reranked; it is a
        # far more meaningful relevance signal than the raw RRF fusion score.
        relevance_score=record.get("rerank_score", record.get("score")),
    )
