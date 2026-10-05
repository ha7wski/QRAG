"""GET /quran-passages/matrix and GET /quran-passages/pairs/{a}/{b} — shared passages, model-free.

The second cross-surah relation (change `add-shared-passages`, design D6): two
verses of different surahs SHARE A PASSAGE when a local alignment of their QAC
lemma sequences passes the acceptance rule. Served from
`data/derived/quran_passages.json` through the pure reader
`retrieval/quran_passages.py`; the alignment was spent once, offline, by
`scripts/build_quran_passages.py`. No model is loaded, no Qdrant query is made.

A separate dataset — and a separate router — from the similarity map
(`api/routers/quran_similarity.py`), whose shapes and error rules these mirror,
so the two relations fail apart.

**The spans.** The dataset stores 1-based QAC WORD spans; a pair is served with
CHARACTER spans into each verse's `text_ar_tashkil`, read from `word_index.json`'s
`chakl_char_start` / `chakl_char_end`. Those offsets are computed against the RAW
chakl row, Basmala included (deliberately: the QLisan fiche slices by them), while
the text a verse is served with has the Basmala stripped by
`quran_data.corpus.strip_leading_basmala` (inside `verse_from_record`). So every
offset is rebased by exactly what that strip removed — the same rebase
`retrieval/verse_lookup.py` applies to its highlights. Skipping it would move a
passage in an āya 1 by the Basmala's four words.

Errors: `a == b` → 422 before any read; a surah outside 1..114 → 422 (path
validation); an empty cell → 200 with `pairs: []`; `(b, a)` answers as `(a, b)`;
dataset missing, of an unknown schema, malformed, naming a verse the corpus does
not hold, or a word `word_index.json` lacks → 503 whose detail carries the
rebuild command.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Request

from api.models.quran_passages import (
    PassagePair,
    QuranPassagesCellResponse,
    QuranPassagesMatrixResponse,
)
from api.models.quran_similarity import SimilarityCell, SurahName
from api.models.verse import verse_from_record
from quran_data import loaders
from quran_data.corpus import chakl_by_ref, strip_leading_basmala
from quran_data.loaders import DatasetMissing
from retrieval import quran_passages as reader

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
    """A reader aggregation over the dataset, its `MalformedEntry` as a 503."""
    data = _dataset()
    try:
        return fn(data, *args)
    except reader.MalformedEntry as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _record(retriever, surah: int, ayah: int) -> dict:
    """A verse record the dataset names; a miss means the dataset is stale."""
    record = retriever.get_by_ref(surah, ayah)
    if record is None:
        raise _stale(f"quran_passages.json names {surah}:{ayah}, which the corpus does not hold")
    return record


def char_span(word_index: dict, chakl: dict, surah: int, ayah: int,
              words: list[int]) -> tuple[int, int]:
    """The `[start, end)` character span of words `words[0]..words[1]` in the DISPLAYED text.

    `word_index` offsets address the raw chakl row; the displayed text is that row
    through `strip_leading_basmala`, so both offsets move back by what it removed.
    Raises `KeyError` / `ValueError` when the words or the row cannot be found or
    the span falls outside the displayed text — the caller's 503.
    """
    raw = chakl[(surah, ayah)]["text"]
    shown = strip_leading_basmala(surah, ayah, raw)
    shift = len(raw) - len(shown)
    first = word_index[f"{surah}:{ayah}:{words[0]}"]
    last = word_index[f"{surah}:{ayah}:{words[1]}"]
    start = first["chakl_char_start"] - shift
    end = last["chakl_char_end"] - shift
    if not 0 <= start < end <= len(shown):
        raise ValueError(f"span [{start}, {end}) of {surah}:{ayah} lies outside its "
                         f"{len(shown)}-character text")
    return start, end


@router.get(
    "/quran-passages/matrix",
    response_model=QuranPassagesMatrixResponse,
)
def get_quran_passages_matrix(request: Request) -> QuranPassagesMatrixResponse:
    """Verse pairs sharing a passage, per pair of surahs: all 114 surahs, non-empty cells only."""
    retriever = request.app.state.engine.retriever
    view = _aggregate(reader.matrix)
    # The map links to verses: a cell naming one the corpus lacks would open onto
    # a 503 when clicked, so the stale dataset is reported here already.
    for pair in _aggregate(reader.pair_set):
        for ref in (pair["u"], pair["v"]):
            _record(retriever, ref["surah"], ref["ayah"])
    return QuranPassagesMatrixResponse(
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
    "/quran-passages/pairs/{a}/{b}",
    response_model=QuranPassagesCellResponse,
)
def get_quran_passages_pairs(
    request: Request,
    a: int = Path(..., ge=1, le=114),
    b: int = Path(..., ge=1, le=114),
) -> QuranPassagesCellResponse:
    """One cell's shared passages; `(b, a)` answers as `(a, b)`, lower surah first."""
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
    if pairs:
        # Read only when there is something to place: `word_index.json` is large.
        try:
            word_index = loaders.word_index()
        except DatasetMissing as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        chakl = chakl_by_ref()
        for p in pairs:
            u, v = p["u"], p["v"]
            u_rec = _record(retriever, u["surah"], u["ayah"])
            v_rec = _record(retriever, v["surah"], v["ayah"])
            try:
                span_u = char_span(word_index, chakl, u["surah"], u["ayah"], p["wa"])
                span_v = char_span(word_index, chakl, v["surah"], v["ayah"], p["wb"])
            except (KeyError, ValueError, TypeError) as exc:
                raise _stale(
                    f"quran_passages.json places a passage of {u['surah']}:{u['ayah']} / "
                    f"{v['surah']}:{v['ayah']} on words the displayed text cannot hold "
                    f"({type(exc).__name__}: {exc})"
                ) from exc
            served.append(PassagePair(
                u=verse_from_record(u_rec),
                v=verse_from_record(v_rec),
                words=p["k"],
                span_u=span_u,
                span_v=span_v,
            ))

    return QuranPassagesCellResponse(
        a=lo,
        b=hi,
        surah_name_a=_surah_name(retriever, lo),
        surah_name_b=_surah_name(retriever, hi),
        verses_a=len({(p["u"]["surah"], p["u"]["ayah"]) for p in pairs}),
        verses_b=len({(p["v"]["surah"], p["v"]["ayah"]) for p in pairs}),
        pairs=served,
    )
