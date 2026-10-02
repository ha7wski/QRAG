"""GET /surah/{number}/similar — close verses inside one surah, model-free.

Served from `data/derived/surah_similarity.json` through the pure reader
`retrieval/surah_similarity.py`. No model is loaded, no Qdrant query is made:
the cross-encoder, the E5 vectors and the QAC signatures were all spent once,
offline, by `scripts/build_surah_similarity.py`.

Verse records, the surah's Arabic name and its ayah count are read the way
`GET /surah/{number}` reads them (`app.state.engine.retriever.get_surah`), and
every verse goes through `verse_from_record`.

Errors: surah outside 1..114 or `ayah < 1` → 422 (path/query validation);
`ayah` past the surah's end → 404; dataset missing, of an unknown schema,
without this surah, or with a malformed entry for it → 503 whose detail
carries the rebuild command.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, Request

from api.models.surah_similarity import (
    AyahSimilarityResponse,
    SimilarityGroup,
    SimilarNeighbour,
    SurahSimilarityResponse,
)
from api.models.verse import verse_from_record
from quran_data.loaders import DatasetMissing
from retrieval import surah_similarity as reader

router = APIRouter(tags=["verse"])

_REBUILD = "python scripts/build_surah_similarity.py"


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


def _record(by_ayah: dict[int, dict], surah: int, ayah: int) -> dict:
    """A verse record the dataset names; a miss means the dataset is stale."""
    record = by_ayah.get(ayah)
    if record is None:
        raise HTTPException(
            status_code=503,
            detail=(
                f"surah_similarity.json names {surah}:{ayah}, which the corpus does "
                f"not hold; the dataset is stale. Rebuild it with:\n    {_REBUILD}"
            ),
        )
    return record


@router.get(
    "/surah/{number}/similar",
    response_model=SurahSimilarityResponse | AyahSimilarityResponse,
)
def get_surah_similarity(
    request: Request,
    number: int = Path(..., ge=1, le=114),
    ayah: int | None = Query(None, ge=1, description="Anchor verse; omit for the groups"),
) -> SurahSimilarityResponse | AyahSimilarityResponse:
    """The surah's groups of close verses, or one verse's close verses with `?ayah=`."""
    retriever = request.app.state.engine.retriever
    verses = retriever.get_surah(number)
    if not verses:
        raise HTTPException(status_code=404, detail=f"Surah {number} not found")
    by_ayah = {v["ayah_number"]: v for v in verses}
    name_ar = verses[0].get("surah_name_ar", "")
    ayah_count = len(verses)

    # Range check BEFORE the dataset: an invalid ref is a 404 whether or not the
    # file has been built.
    if ayah is not None and ayah > ayah_count:
        raise HTTPException(
            status_code=404, detail=f"Verse {number}:{ayah} not found"
        )

    data = _dataset()
    try:
        if ayah is None:
            view = reader.surah_view(data, number)
            return SurahSimilarityResponse(
                surah_number=number,
                surah_name_ar=name_ar,
                ayah_count=ayah_count,
                unscored=view["unscored"],
                groups=[
                    SimilarityGroup(
                        ayahs=g["ayahs"],
                        strength=g["strength"],
                        verses=[
                            verse_from_record(_record(by_ayah, number, a))
                            for a in g["ayahs"]
                        ],
                    )
                    for g in view["groups"]
                ],
            )

        view = reader.ayah_view(data, number, ayah, ayah_count)
    except reader.AyahOutOfRange as exc:  # pragma: no cover - checked above
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (reader.SurahNotInDataset, reader.MalformedEntry) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return AyahSimilarityResponse(
        surah_number=number,
        surah_name_ar=name_ar,
        ayah_count=ayah_count,
        anchor=verse_from_record(by_ayah[ayah]),
        unscored=view["unscored"],
        neighbours=[
            SimilarNeighbour(
                verse=verse_from_record(_record(by_ayah, number, n["ayah"])),
                score=n["score"],
                roots=n["roots"],
            )
            for n in view["neighbours"]
        ],
    )
