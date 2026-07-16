"""
Madar endpoint: sourced lexical reading of an Arabic word's root.

Returns Ibn Fāris' cited aṣl (verified), the root's Quranic occurrences (proof),
and an optional, clearly-flagged LLM synthesis of the pivot (GENERATED — off
unless MADAR_SYNTHESIS_ENABLED=1). Arabic-only. Pure pipeline logic lives in
`madar/`; this layer validates input and lazily builds the shared service from
the already-loaded QAC resolver + LLM client (no lifespan change).
"""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request

from api.models.madar import MadarRequest, MadarResponse

router = APIRouter(tags=["madar"])

# Any Arabic-script character (incl. the bare hamza ء) makes the input valid.
_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿ]")


def _service(request: Request):
    """Lazily build and cache the MadarService on app.state, reusing the shared
    QAC resolver and LLM client — no new heavy components."""
    svc = getattr(request.app.state, "madar_service", None)
    if svc is None:
        from madar.madar_service import MadarService

        svc = MadarService(
            resolver=request.app.state.lexical_analyzer.retriever,
            llm=request.app.state.engine.llm,
        )
        request.app.state.madar_service = svc
    return svc


@router.post("/madar/analyze", response_model=MadarResponse)
def madar_analyze(req: MadarRequest, request: Request) -> MadarResponse:
    """Read a word's root as a sourced lexical entry: cited aṣl + occurrences +
    optional generated synthesis.

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
