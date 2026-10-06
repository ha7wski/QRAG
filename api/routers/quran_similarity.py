"""The surah × surah map, model-free: GET /quran-similarity/matrix (the
per-surah-pair counts) and GET /quran-similarity/pairs/{a}/{b} (one cell's verse
pairs).

The per-verse view, GET /verse/{surah}/{ayah}/similar, is QUARANTINED in
`api/routers/verse_quran_similarity.py` (imported, not mounted): the panel that
read it was removed at the user's request. It reuses this module's helpers.

Served from `data/derived/quran_close_verses.json` — the unified relation, the
union of whole-verse similarity and shared passages (change
`unify-close-verses`, D6–D7) — through the pure reader
`retrieval/quran_close_verses.py`. No model is loaded, no Qdrant query is made,
and `word_index.json` is not read: the cross-encoder, the E5 vectors, the
alignments and the common part's character spans were all spent once, offline,
by `scripts/build_quran_close_verses.py`.

A separate dataset from `GET /surah/{number}/similar`, so the two fail apart:
without this file the intra-surah view still answers.

Verse records and surah names are read the way `GET /surah/{number}` reads them
(`app.state.engine.retriever`), and every verse goes through
`verse_from_record`. The spans index into that verse's served
`text_ar_tashkil`; one that does not fit it means the dataset is stale.

Errors: dataset missing, of an unknown schema, malformed, naming a verse the
corpus does not hold, or placing a span outside a verse's text → 503 whose
detail carries the rebuild command.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Request

from api.models.quran_similarity import (
    QuranSimilarityCellResponse,
    QuranSimilarityMatrixResponse,
    SimilarityCell,
    SimilarPair,
    SurahName,
)
from api.models.verse import Verse, verse_from_record
from quran_data.loaders import DatasetMissing
from retrieval import quran_close_verses as reader

router = APIRouter(tags=["verse"])

_REBUILD = reader.REBUILD


def _stale(detail: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=f"{detail}; the dataset is stale. Rebuild it with:\n    {_REBUILD}",
    )


def _dataset() -> dict:
    """The dataset, or a 503 naming the rebuild command."""
    try:
        return reader.load()
    except DatasetMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:  # unknown schema (the loader's subclass) or unreadable JSON
        detail = str(exc)
        if _REBUILD not in detail:
            detail = f"{detail}\nRebuild it with:\n    {_REBUILD}"
        raise HTTPException(status_code=503, detail=detail) from exc


def _aggregate(fn, *args):
    """A reader view over the dataset, its `MalformedEntry` as a 503."""
    data = _dataset()
    try:
        return fn(data, *args)
    except reader.MalformedEntry as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _record(retriever, surah: int, ayah: int) -> dict:
    """A verse record the dataset names; a miss means the dataset is stale."""
    record = retriever.get_by_ref(surah, ayah)
    if record is None:
        raise _stale(
            f"quran_close_verses.json names {surah}:{ayah}, which the corpus does not hold"
        )
    return record


def _placed(verse: Verse, span: list[int] | None) -> list[int] | None:
    """`span`, checked against the verse's served text — a span past its end is stale.

    The build already refuses such a span (D5); this keeps a file built against
    another corpus from reaching the client as a highlight on the wrong words.
    """
    if span is not None and not span[1] <= len(verse.text_ar_tashkil or ""):
        raise _stale(
            f"quran_close_verses.json places a common part at {span} in {verse.id}, "
            f"whose displayed text is {len(verse.text_ar_tashkil or '')} characters long"
        )
    return span


# ── the surah × surah map ─────────────────────────────────────────────────
#
# Both routes aggregate the same dataset through the pure reader (memoised per
# loaded dict), load no model and touch no Qdrant. Failure mode: a missing, unknown-schema or malformed dataset — or one
# naming a verse the corpus lacks — is a 503 carrying the rebuild command.


@router.get(
    "/quran-similarity/matrix",
    response_model=QuranSimilarityMatrixResponse,
)
def get_quran_similarity_matrix(request: Request) -> QuranSimilarityMatrixResponse:
    """Close verse pairs per pair of surahs: all 114 surahs, the non-empty cells only."""
    retriever = request.app.state.engine.retriever
    view = _aggregate(reader.matrix)
    # The map links to verses: a cell naming one the corpus lacks, or a common
    # part its text cannot hold, would open onto a 503 when clicked, so the
    # stale dataset is reported here already.
    for pair in _aggregate(reader.pair_set):
        for side in ("u", "v"):
            ref, span = pair[side], pair[f"span_{side}"]
            record = _record(retriever, ref["surah"], ref["ayah"])
            if span is not None:
                _placed(verse_from_record(record), span)
    return QuranSimilarityMatrixResponse(
        # The source GET /surahs reads, so the two never name a surah differently.
        surahs=[SurahName(number=s["number"], name_ar=s.get("name_ar", ""))
                for s in retriever.list_surahs()],
        cells=[SimilarityCell(**c) for c in view["cells"]],
        total_pairs=view["total_pairs"],
        max_pairs=view["max_pairs"],
    )


def _surah_name(retriever, surah: int) -> str:
    verses = retriever.get_surah(surah)
    return verses[0].get("surah_name_ar", "") if verses else ""


@router.get(
    "/quran-similarity/pairs/{a}/{b}",
    response_model=QuranSimilarityCellResponse,
)
def get_quran_similarity_pairs(
    request: Request,
    a: int = Path(..., ge=1, le=114),
    b: int = Path(..., ge=1, le=114),
) -> QuranSimilarityCellResponse:
    """One cell's close verse pairs; `(b, a)` answers as `(a, b)`, lower surah first."""
    # Before the dataset: the diagonal is invalid whether or not the file exists.
    if a == b:
        raise HTTPException(
            status_code=422,
            detail=f"cell ({a}, {b}) is on the diagonal; pick two different surahs",
        )
    lo, hi = (a, b) if a < b else (b, a)
    retriever = request.app.state.engine.retriever
    pairs = _aggregate(reader.cell_pairs, lo, hi)
    served = []
    for p in pairs:
        u = verse_from_record(_record(retriever, p["u"]["surah"], p["u"]["ayah"]))
        v = verse_from_record(_record(retriever, p["v"]["surah"], p["v"]["ayah"]))
        served.append(SimilarPair(
            u=u, v=v, score=p["score"], roots=p["roots"], words=p["words"],
            span_u=_placed(u, p["span_u"]), span_v=_placed(v, p["span_v"]),
        ))
    return QuranSimilarityCellResponse(
        a=lo,
        b=hi,
        surah_name_a=_surah_name(retriever, lo),
        surah_name_b=_surah_name(retriever, hi),
        verses_a=len({(p["u"]["surah"], p["u"]["ayah"]) for p in pairs}),
        verses_b=len({(p["v"]["surah"], p["v"]["ayah"]) for p in pairs}),
        pairs=served,
    )
