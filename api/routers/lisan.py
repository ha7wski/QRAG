"""
Lisan endpoint: letter-symbolism reading of an Arabic word's root.

Arabic-only and LLM-free: the reading is composed deterministically from the
letter data (see `lisan/synthesis_template.py`). Interpretive (Hasan Abbas'
sound-symbolism + Ibn Jinni), NOT lexicography — the disclaimer travels in the
response. Pure pipeline logic lives in `lisan/`; this layer only validates input
and lazily builds the shared `LisanService` from the already-loaded QAC resolver
(so app startup / main.py wiring is a single include_router line, no lifespan
change).
"""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request

from api.models.lisan import LisanRequest, LisanResponse

router = APIRouter(tags=["lisan"])

# Any Arabic-script character (incl. the bare hamza ء) makes the input valid.
_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿ]")


def _service(request: Request):
    """Lazily build and cache the LisanService on app.state, reusing the shared
    QAC resolver (LexicalRetriever) — no LLM, no new heavy components."""
    svc = getattr(request.app.state, "lisan_service", None)
    if svc is None:
        from lisan.lisan_service import LisanService

        svc = LisanService(
            resolver=request.app.state.lexical_analyzer.retriever,
        )
        request.app.state.lisan_service = svc
    return svc


@router.post("/lisan/analyze", response_model=LisanResponse)
def lisan_analyze(req: LisanRequest, request: Request) -> LisanResponse:
    """Read a word's root letter-by-letter and compose an Arabic Lisan reading.

    Arabic-only: no `lang` parameter (any sent is ignored). 422 on empty /
    non-Arabic input. When no root resolves, returns 200 with `root: null` and a
    helpful `message` (never 500)."""
    word = (req.word or "").strip()
    if not word:
        raise HTTPException(status_code=422, detail="word must not be empty")
    if not _ARABIC_RE.search(word):
        raise HTTPException(
            status_code=422, detail="word must be written in Arabic script"
        )

    return _service(request).analyze(word)
