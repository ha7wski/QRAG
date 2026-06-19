"""Verse & surah endpoints (P1): direct lookups for deep-linking."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, Request

from api.models.verse import (
    SurahMeta,
    SurahResponse,
    VerseDetailResponse,
    verse_from_record,
)

router = APIRouter(tags=["verse"])


@router.get("/surahs", response_model=list[SurahMeta])
def list_surahs(request: Request) -> list[SurahMeta]:
    """Return all 114 surahs (number + names + ayah count) for the picker."""
    retriever = request.app.state.engine.retriever
    return [SurahMeta(**s) for s in retriever.list_surahs()]


@router.get("/verse/{surah}/{ayah}", response_model=VerseDetailResponse)
def get_verse(
    request: Request,
    surah: int = Path(..., ge=1, le=114),
    ayah: int = Path(..., ge=1),
    window: int = Query(1, ge=0, le=5, description="Neighbor context radius"),
) -> VerseDetailResponse:
    """Return a single verse with its neighbor context and adjacent verse ids."""
    retriever = request.app.state.engine.retriever
    record = retriever.get_by_ref(surah, ayah)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Verse {surah}:{ayah} not found")

    context = retriever.neighbors(record["id"], window=window)
    prev_id, next_id = retriever.prev_next(record["id"])
    return VerseDetailResponse(
        verse=verse_from_record(record),
        context=[verse_from_record(v) for v in context],
        prev_id=prev_id,
        next_id=next_id,
    )


@router.get("/surah/{number}", response_model=SurahResponse)
def get_surah(
    request: Request,
    number: int = Path(..., ge=1, le=114),
) -> SurahResponse:
    """Return a full surah: ordered verses + metadata."""
    retriever = request.app.state.engine.retriever
    verses = retriever.get_surah(number)
    if not verses:
        raise HTTPException(status_code=404, detail=f"Surah {number} not found")

    first = verses[0]
    return SurahResponse(
        surah_number=number,
        surah_name_ar=first.get("surah_name_ar", ""),
        surah_name_en=first.get("surah_name_en", ""),
        surah_name_fr=first.get("surah_name_fr", ""),
        period=first.get("period", ""),
        ayah_count=len(verses),
        verses=[verse_from_record(v) for v in verses],
    )
