"""QLisan endpoints: deterministic per-word analysis fiche (no LLM).

`POST /qlisan/word` returns the four-level fiche (صوتي → صرفي → نحوي → دلالي) for a
word at `surah:ayah:word`; صرفي + نحوي come only from the parsed on-disk treebank,
صوتي + دلالي are stubs in this increment. `GET /qlisan/verse/{surah}/{ayah}` returns
the vocalized verse with QAC-aligned token boundaries for word selection.

The analysis module (`analysis/word_analysis.py`) is pure/light (cached dict
lookups), so this layer just validates input and maps errors to HTTP status —
no heavy service on `app.state` is needed.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from analysis.word_analysis import analyze_form, analyze_word, verse_tokens
from api.models.qlisan import (
    QlisanFormRequest,
    QlisanFormResponse,
    QlisanVerseResponse,
    QlisanWordRequest,
    QlisanWordResponse,
)

router = APIRouter(tags=["qlisan"])


@router.post("/qlisan/word", response_model=QlisanWordResponse)
def qlisan_word(req: QlisanWordRequest) -> QlisanWordResponse:
    """Assemble the deterministic four-level fiche for one word.

    400 on non-positive/invalid indices; 404 when `surah:ayah:word` does not
    exist in the corpus."""
    try:
        fiche = analyze_word(req.surah, req.ayah, req.word)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"word position not found: {req.surah}:{req.ayah}:{req.word}"
        ) from exc
    return QlisanWordResponse(**fiche)


@router.get("/qlisan/verse/{surah}/{ayah}", response_model=QlisanVerseResponse)
def qlisan_verse(surah: int, ayah: int) -> QlisanVerseResponse:
    """Return the vocalized verse + QAC-aligned token boundaries for selection.

    400 on non-positive indices; 404 when the verse does not exist."""
    try:
        data = verse_tokens(surah, ayah)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"verse not found: {surah}:{ayah}"
        ) from exc
    return QlisanVerseResponse(**data)


@router.post("/qlisan/form", response_model=QlisanFormResponse)
def qlisan_form(req: QlisanFormRequest) -> QlisanFormResponse:
    """The صرفي level for a word typed with no verse position (Lisan Analysis).

    Always 200: an empty / unattested word comes back `available:false` with an
    Arabic message rather than an error, so this supplementary section can never
    break the page that hosts it."""
    return QlisanFormResponse(**analyze_form(req.word))
