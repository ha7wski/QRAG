"""Fāṣila endpoints: the pausal rhyme-letter of every āya, per sūra and corpus-wide.

Read-only and derived entirely from the corpus — no LLM, no state, no retrieval.
The computation lives in `analysis/fassila.py` and is cached per process, so this
router is a thin pass-through.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path

from analysis.fassila import analyse_surah, overview
from api.models.fassila import FassilaOverviewResponse, FassilaResponse

router = APIRouter(tags=["fassila"])


# ⚠️ ORDER MATTERS — this route MUST stay above `/fassila/{surah}`.
#
# FastAPI matches routes in declaration order. `/fassila/{surah}` types its path
# parameter as `int`, so if it were declared first, a request for `/fassila/overview`
# would match *it*, fail integer coercion and return 422 — never reaching this handler.
# Alphabetizing or otherwise reordering the handlers in this file breaks the endpoint
# with no import error and no test failure other than the one guarding this.
@router.get("/fassila/overview", response_model=FassilaOverviewResponse)
def get_fassila_overview() -> FassilaOverviewResponse:
    """Return the fāṣila summary of all 114 sūras plus the corpus aggregates."""
    return FassilaOverviewResponse(**overview())


@router.get("/fassila/{surah}", response_model=FassilaResponse)
def get_fassila(
    surah: int = Path(..., ge=1, le=114, description="Surah number"),
) -> FassilaResponse:
    """Return the fāṣila analysis of one sūra (counts, orderings, per-āya detail)."""
    try:
        return FassilaResponse(**analyse_surah(surah))
    except ValueError as exc:  # surah absent from the corpus
        raise HTTPException(status_code=404, detail=str(exc)) from exc
