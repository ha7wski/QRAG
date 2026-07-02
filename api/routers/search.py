"""Search endpoint: hybrid retrieval without generation."""
from __future__ import annotations

import logging
import os
import time

from fastapi import APIRouter, Query, Request

from api.models.verse import SearchResponse, verse_from_record

router = APIRouter(tags=["search"])

# Per-request timing; surfaces live in the backend log (start.sh tail -f).
logger = logging.getLogger("quran_rag.timing")

# Candidate-pool caps per source. Kept small so the cross-encoder reranks a
# bounded pool (latency ∝ pool size). Root candidates are IDF-coverage ordered
# and BM25 by lexical score, so the truly relevant verses are near the top of
# each; the union stays well under the reranker's per-batch (32) cost.
ROOT_POOL = 20
BM25_POOL = 16
# Hard cap on the deduped union handed to the reranker. The cross-encoder costs
# ~one batch (32) of latency per step, so keeping the pool ≤32 keeps a search to
# a single batch (~3–4s on Apple Silicon). Raise for more recall at more latency.
RERANK_POOL_MAX = 32
# Drop reranked results below this cross-encoder relevance (sigmoid 0–1): it
# trims the long low-relevance tail so only genuinely close verses are shown.
# Tuned conservatively; override with SEARCH_MIN_SCORE. A minimum number of
# results is always kept so a query never comes back empty when matches exist.
MIN_RERANK_SCORE = float(os.getenv("SEARCH_MIN_SCORE", "0.01"))
MIN_RESULTS = 3
# Context comparison: scale the rerank score by how much of the query's content
# (its meaningful roots) a verse covers, so shared-single-word false positives
# (e.g. بلغ "convey" vs بلغ "reach maturity") are demoted below verses that share
# the whole context. floor = weight kept for a zero-coverage verse (0 = coverage
# fully gates; 1 = coverage ignored). Only bites when the query has >1 root.
COVERAGE_FLOOR = float(os.getenv("SEARCH_COVERAGE_FLOOR", "0.25"))


@router.get("/search", response_model=SearchResponse)
def search(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    surah: int | None = Query(None, ge=1, le=114),
    period: str | None = Query(None, description="makkiyya | madani"),
    juz: int | None = Query(None, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50),
) -> SearchResponse:
    """Similar-verse search: root ∪ BM25 candidates → cross-encoder rerank →
    query-root-coverage blend → relevance threshold. Optional filters."""
    engine = request.app.state.engine
    reranker = getattr(request.app.state, "search_reranker", None)
    similar = getattr(request.app.state, "similar_verses", None)
    filters = {"surah_number": surah, "period": period, "juz": juz}
    filters = {k: v for k, v in filters.items() if v is not None}

    t0 = time.perf_counter()
    # Candidate generation: UNION of two model-free sources, deduped and capped.
    #  - root-based (content-word roots → verses by IDF-weighted coverage):
    #    precise, adds morphological neighbors, drops function-word noise.
    #  - BM25 lexical: recall on distinctive phrases (indexes ar+fr+en).
    # The dense (E5) branch is intentionally NOT used here: for Arabic phrase
    # queries it only added noise (basmala/short openers) and cost ~1.7s of query
    # embedding per request. Root ∪ BM25 gave ~0.98 target recall on the eval set.
    def _passes(v: dict) -> bool:
        return all(
            filters.get(k) is None or v.get(k) == filters[k]
            for k in ("surah_number", "period", "juz")
        )

    pool: list[dict] = []
    seen: set[str] = set()
    if similar is not None:
        for r in (similar.candidates_for(q, filters=filters or None) or [])[:ROOT_POOL]:
            if r["id"] not in seen:
                seen.add(r["id"])
                pool.append(r)
    n_root = len(pool)
    # Clean the BM25 query: drop function words so it can't match a verse via a
    # shared particle (e.g. لمّا pulling كلا لمّا يقض / فعّال لما يريد). Falls back
    # to the raw query when the query is all function words / non-Arabic.
    bm25_q = " ".join(similar.content_terms(q)) if similar is not None else ""
    bm25_q = bm25_q or q
    for vid, _score in engine.retriever.hybrid.bm25.search(bm25_q, top_k=BM25_POOL):
        if vid in seen:
            continue
        rec = engine.retriever._full(vid)
        if rec is None or (filters and not _passes(rec)):
            continue
        seen.add(vid)
        pool.append({**rec, "score": 0.0})
    candidates = pool[:RERANK_POOL_MAX]
    mode = f"union(root={n_root}+bm25={len(pool) - n_root})"

    # Comparison stage: rerank the candidate pool by cross-encoder relevance and
    # drop the low-relevance tail (threshold), else keep the pool order.
    if reranker is not None:
        ranked = reranker.rerank(q, candidates, top_k=len(candidates))
        # Context comparison: blend query-root coverage into the score, then
        # re-sort. Disambiguates shared-root false positives and demotes verses
        # that matched only a function word / single token.
        root_idf = similar.query_root_idf(q) if similar is not None else {}
        if root_idf:
            for r in ranked:
                cov = similar.coverage_fraction(r["id"], root_idf)
                r["_cov"] = cov
                r["rerank_score"] = r.get("rerank_score", 0.0) * (
                    COVERAGE_FLOOR + (1.0 - COVERAGE_FLOOR) * cov
                )
            ranked.sort(key=lambda r: r.get("rerank_score", 0.0), reverse=True)
            # Full-coverage (AND) policy: when the query has ≥2 content roots,
            # keep only verses that contain ALL of them (the query's whole
            # context), which drops single-root wrong-sense matches (e.g. بلغ
            # "convey" without أشد). Fall back to partial matches if too few.
            if len(root_idf) >= 2:
                full = [r for r in ranked if r.get("_cov", 0.0) >= 0.999]
                if len(full) >= MIN_RESULTS:
                    ranked = full
        kept = [r for r in ranked if r.get("rerank_score", 0.0) >= MIN_RERANK_SCORE]
        results = (kept or ranked[:MIN_RESULTS])[:limit]
    else:
        results = candidates[:limit]
    elapsed_ms = (time.perf_counter() - t0) * 1000

    logger.info(
        "search: retrieval=%.0fms | mode=%s results=%d limit=%d filters=%s rerank=%s | q=%r",
        elapsed_ms,
        mode,
        len(results),
        limit,
        filters or {},
        "on" if reranker is not None else "off",
        q[:60],
    )
    return SearchResponse(
        query=q,
        results=[verse_from_record(r) for r in results],
        total=len(results),
    )
