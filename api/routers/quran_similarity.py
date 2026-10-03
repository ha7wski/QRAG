"""GET /verse/{surah}/{ayah}/similar — close verses in the other surahs, model-free.

Served from `data/derived/quran_similarity.json` through the pure reader
`retrieval/quran_similarity.py`. No model is loaded, no Qdrant query is made:
the cross-encoder, the E5 vectors and the QAC signatures were all spent once,
offline, by `scripts/build_quran_similarity.py`.

A separate route — and a separate dataset — from `GET /surah/{number}/similar`,
so the two fail apart: without this file the intra-surah view still answers.
No conflict with `GET /verse/{surah}/{ayah}`: one more path segment, so neither
pattern can match the other's URL.

Verse records, the surah's Arabic name and its ayah count are read the way
`GET /surah/{number}` reads them (`app.state.engine.retriever`), and every
verse — the anchor and each neighbour, whatever its surah — goes through
`verse_from_record`.

Errors: surah outside 1..114 or `ayah < 1` → 422 (path validation); `ayah` past
the surah's end → 404; dataset missing, of an unknown schema, malformed for
this verse, or naming a verse the corpus does not hold → 503 whose detail
carries the rebuild command.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Request

from api.models.quran_similarity import VerseQuranSimilarityResponse
from api.models.surah_similarity import SimilarNeighbour
from api.models.verse import verse_from_record
from quran_data.loaders import DatasetMissing
from retrieval import quran_similarity as reader

router = APIRouter(tags=["verse"])

_REBUILD = "python scripts/build_quran_similarity.py"


def _dataset() -> dict:
    """The dataset, or a 503 naming the rebuild command."""
    try:
        return reader.load()
    except DatasetMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:  # unknown schema version — the loader's own subclass
        detail = str(exc)
        if _REBUILD not in detail:
            detail = f"{detail}\nRebuild it with:\n    {_REBUILD}"
        raise HTTPException(status_code=503, detail=detail) from exc


def _record(retriever, surah: int, ayah: int) -> dict:
    """A verse record the dataset names; a miss means the dataset is stale."""
    record = retriever.get_by_ref(surah, ayah)
    if record is None:
        raise HTTPException(
            status_code=503,
            detail=(
                f"quran_similarity.json names {surah}:{ayah}, which the corpus does "
                f"not hold; the dataset is stale. Rebuild it with:\n    {_REBUILD}"
            ),
        )
    return record


@router.get(
    "/verse/{surah}/{ayah}/similar",
    response_model=VerseQuranSimilarityResponse,
)
def get_verse_quran_similarity(
    request: Request,
    surah: int = Path(..., ge=1, le=114),
    ayah: int = Path(..., ge=1),
) -> VerseQuranSimilarityResponse:
    """One verse's close verses in the other 113 surahs, in dataset (score) order."""
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

    data = _dataset()
    try:
        view = reader.ayah_view(data, surah, ayah)
    except reader.MalformedEntry as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return VerseQuranSimilarityResponse(
        surah_number=surah,
        surah_name_ar=verses[0].get("surah_name_ar", ""),
        ayah_count=ayah_count,
        anchor=verse_from_record(by_ayah[ayah]),
        unscored=view["unscored"],
        neighbours=[
            SimilarNeighbour(
                verse=verse_from_record(_record(retriever, n["surah"], n["ayah"])),
                score=n["score"],
                roots=n["roots"],
            )
            for n in view["neighbours"]
        ],
    )
