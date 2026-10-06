"""GET /verse/{surah}/{ayah}/similar — QUARANTINED: imported, NOT mounted.

One verse's close verses in the other 113 surahs, every pair, score desc then
ref — over the same dataset as the surah × surah map
(`data/derived/quran_close_verses.json`), through the same helpers
(`api/routers/quran_similarity.py`). Its only page, the picked-verse panel of
«المتقاربات داخل السورة», was removed at the user's request; the map is where
cross-surah closeness is read now.

Quarantine, not deletion (the `madar` convention): the handler, its models and
its tests stay and pass, and `api/main.py` imports this module so it is proven
to import on every startup. Rebranching is exactly one line in `api/main.py`,
`app.include_router(verse_quran_similarity_router.router)`, plus a client
function and a caller in the frontend (`tests/test_served_surface.py` requires
both).

No conflict with `GET /verse/{surah}/{ayah}`: one more path segment.

Errors: surah outside 1..114 or `ayah < 1` → 422 (path validation); `ayah` past
the surah's end → 404; dataset missing, of an unknown schema, malformed, naming
a verse the corpus does not hold, or placing a span outside a verse's text →
503 whose detail carries the rebuild command.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Request

from api.models.quran_similarity import QuranNeighbour, VerseQuranSimilarityResponse
from api.models.verse import verse_from_record
from api.routers import quran_similarity as qs

router = APIRouter(tags=["verse"])


@router.get(
    "/verse/{surah}/{ayah}/similar",
    response_model=VerseQuranSimilarityResponse,
)
def get_verse_quran_similarity(
    request: Request,
    surah: int = Path(..., ge=1, le=114),
    ayah: int = Path(..., ge=1),
) -> VerseQuranSimilarityResponse:
    """One verse's close verses in the other 113 surahs: every pair, score desc then ref."""
    retriever = request.app.state.engine.retriever
    verses = retriever.get_surah(surah)
    if not verses:
        raise HTTPException(status_code=404, detail=f"Surah {surah} not found")
    by_ayah = {v["ayah_number"]: v for v in verses}
    ayah_count = len(verses)

    # Range check BEFORE the dataset: an invalid ref is a 404 whether or not the
    # file has been built.
    if ayah > ayah_count or ayah not in by_ayah:
        raise HTTPException(
            status_code=404, detail=f"Verse {surah}:{ayah} not found"
        )

    view = qs._aggregate(qs.reader.ayah_view, surah, ayah)
    neighbours = []
    for n in view["neighbours"]:
        verse = verse_from_record(qs._record(retriever, n["surah"], n["ayah"]))
        neighbours.append(QuranNeighbour(
            verse=verse, score=n["score"], roots=n["roots"],
            words=n["words"], span=qs._placed(verse, n["span"]),
        ))

    return VerseQuranSimilarityResponse(
        surah_number=surah,
        surah_name_ar=verses[0].get("surah_name_ar", ""),
        ayah_count=ayah_count,
        anchor=verse_from_record(by_ayah[ayah]),
        unscored=view["unscored"],
        neighbours=neighbours,
    )
