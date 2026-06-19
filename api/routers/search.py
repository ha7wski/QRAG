"""Search endpoint: hybrid retrieval without generation."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Query, Request

from api.models.verse import SearchResponse, verse_from_record

router = APIRouter(tags=["search"])

# Per-request timing; surfaces live in the backend log (start.sh tail -f).
logger = logging.getLogger("quran_rag.timing")


@router.get("/search", response_model=SearchResponse)
def search(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    surah: int | None = Query(None, ge=1, le=114),
    period: str | None = Query(None, description="makkiyya | madani"),
    juz: int | None = Query(None, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50),
) -> SearchResponse:
    """Hybrid (dense + BM25) search with optional filters."""
    engine = request.app.state.engine
    filters = {"surah_number": surah, "period": period, "juz": juz}
    filters = {k: v for k, v in filters.items() if v is not None}

    t0 = time.perf_counter()
    results = engine.retriever.retrieve(q, top_k=limit, filters=filters or None)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    rerank = "on" if engine.retriever.reranker else "off"
    logger.info(
        "search: retrieval=%.0fms | results=%d limit=%d filters=%s rerank=%s | q=%r",
        elapsed_ms,
        len(results),
        limit,
        filters or {},
        rerank,
        q[:60],
    )
    return SearchResponse(
        query=q,
        results=[verse_from_record(r) for r in results],
        total=len(results),
    )
