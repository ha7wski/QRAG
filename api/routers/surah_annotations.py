"""GET /surah/{number}/annotations — the reading page's closeness cues, model-free.

One static lookup per surah over the two closeness datasets, both already built
and measured — this route reads, it never computes:

  * `surah_similarity.json` (through `api/routers/surah_similarity.py`'s loader)
    — the surah's GROUPS, the same ones «المتقاربات داخل السورة» shows, never
    the wider neighbour lists → the green marker;
  * `quran_close_verses.json` (through `api/routers/quran_similarity.py`'s
    loader and `retrieval.quran_close_verses.surah_partners`) — every pair
    holding a verse of the surah, split by RELATION, never by a threshold:
    `similarity` in `from` → `whole` (orange marker), `from == ["passage"]` →
    `passage` (orange words, through the stored spans).

Each annotated ayah lists its group partners and its cross partners; every
partner verse travels once in `verses`, through `verse_from_record`, so the
bubble never fetches. Span lists are oriented to the ayah's side (`spans_self`)
and each span is checked against the displayed `text_ar_tashkil` of the verse it
indexes.

Errors: surah outside 1..114 → 422 (path validation); either dataset missing,
of an unknown schema or malformed, naming a verse the corpus does not hold, or
placing a span outside its verse's text → 503 whose detail carries the rebuild
command. A surah with no cue → 200 with `ayahs: []` and `verses: {}`.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Request

from api.models.surah_annotations import (
    AnnotatedAyah,
    AnnotationPartner,
    SurahAnnotationsResponse,
)
from api.models.verse import Verse, verse_from_record
from api.routers import quran_similarity as cross
from api.routers import surah_similarity as intra

router = APIRouter(tags=["verse"])


def _groups(by_ayah: dict[int, dict], surah: int) -> dict[int, set[int]]:
    """Each grouped ayah → the other members of its group(s)."""
    data = intra._dataset()
    try:
        view = intra.reader.surah_view(data, surah)
    except (intra.reader.SurahNotInDataset, intra.reader.MalformedEntry) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    partners: dict[int, set[int]] = {}
    for g in view["groups"]:
        for a in g["ayahs"]:
            intra._record(by_ayah, surah, a)  # a stale dataset is a 503
            partners.setdefault(a, set()).update(b for b in g["ayahs"] if b != a)
    return partners


@router.get(
    "/surah/{number}/annotations",
    response_model=SurahAnnotationsResponse,
)
def get_surah_annotations(
    request: Request,
    number: int = Path(..., ge=1, le=114),
) -> SurahAnnotationsResponse:
    """The surah's annotated ayahs, ayah ascending, and their partner verses."""
    retriever = request.app.state.engine.retriever
    records = retriever.get_surah(number)
    if not records:
        raise HTTPException(status_code=404, detail=f"Surah {number} not found")
    by_ayah = {v["ayah_number"]: v for v in records}

    groups = _groups(by_ayah, number)
    pairs = cross._aggregate(cross.reader.surah_partners, number)

    verses: dict[str, Verse] = {}

    def verse(surah: int, ayah: int) -> Verse:
        ref = f"{surah}:{ayah}"
        if ref not in verses:
            record = (intra._record(by_ayah, surah, ayah) if surah == number
                      else cross._record(retriever, surah, ayah))
            verses[ref] = verse_from_record(record)
        return verses[ref]

    selves: dict[int, Verse] = {}
    ayahs: list[AnnotatedAyah] = []
    for ayah in sorted(groups.keys() | pairs.keys()):
        whole: list[AnnotationPartner] = []
        passage: list[AnnotationPartner] = []
        for p in pairs.get(ayah, []):
            if ayah not in selves:
                selves[ayah] = verse_from_record(cross._record(retriever, number, ayah))
            other = verse(p["surah"], p["ayah"])
            partner = AnnotationPartner(
                ref=other.id,
                score=p["score"],
                words=p["words"],
                spans_self=cross._placed(selves[ayah], p["spans_self"]),
                spans_other=cross._placed(other, p["spans_other"]),
            )
            (whole if "similarity" in p["from"] else passage).append(partner)
        group = sorted(groups.get(ayah, ()))
        for a in group:
            verse(number, a)
        ayahs.append(AnnotatedAyah(ayah=ayah, group=group, whole=whole, passage=passage))

    return SurahAnnotationsResponse(surah=number, ayahs=ayahs, verses=verses)
