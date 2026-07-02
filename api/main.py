"""
main.py — FastAPI application for the Quran RAG backend.

Builds a single shared ChatEngine at startup (it loads the embedding model,
Qdrant client, BM25 index, and LLM client) and exposes it to the routers via
`app.state.engine`.

Run locally:
    uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from api.middleware import RequestLoggingMiddleware  # noqa: E402
from api.routers import chat as chat_router  # noqa: E402
from api.routers import feedback as feedback_router  # noqa: E402
from api.routers import lexical as lexical_router  # noqa: E402
from api.routers import search as search_router  # noqa: E402
from api.routers import sessions as sessions_router  # noqa: E402
from api.routers import verse as verse_router  # noqa: E402
from api.routers import verse_lookup as verse_lookup_router  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("quran_rag.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build heavy components once at startup, share them via app.state."""
    from generation.chat_engine import ChatEngine
    from generation.lexical_analyzer import LexicalAnalyzer

    from api.store import Store
    from retrieval.verse_lookup import VerseLookup

    logger.info("Initializing ChatEngine (embedder, Qdrant, BM25, LLM)...")
    app.state.engine = ChatEngine()
    # Reuse the engine's LLM client for lexical analysis.
    app.state.lexical_analyzer = LexicalAnalyzer(llm=app.state.engine.llm)
    # Verse Lookup (exhaustive, vocalized, no LLM) reuses the lexical analyzer's
    # morphology index + root extractor; it only adds the diacritized CSV.
    app.state.verse_lookup = VerseLookup(retriever=app.state.lexical_analyzer.retriever)
    # Root-based candidate generation for GET /search ("Similar Verses"): cleans
    # the query to content-word roots and pulls verses by IDF-weighted root
    # coverage — a tight, noise-free pool the reranker then orders. Reuses the
    # already-loaded QAC index (no model, cheap).
    from retrieval.similar_verses import SimilarVerses

    app.state.similar_verses = SimilarVerses(app.state.lexical_analyzer.retriever)
    # Optional cross-encoder reranker for GET /search ("Similar Verses" tab).
    # Gated by SEARCH_RERANK_ENABLED (off by default: the model is ~2.3 GB). It
    # reorders a wider fused candidate pool by true query↔verse relevance,
    # demoting the noisy dense-branch hits (basmala/short openers).
    app.state.search_reranker = None
    if os.getenv("SEARCH_RERANK_ENABLED", "0") == "1":
        from retrieval.reranker import Reranker

        logger.info("Loading search reranker (SEARCH_RERANK_ENABLED=1)...")
        app.state.search_reranker = Reranker()
        # Warm up: the first cross-encoder predict compiles the MPS/GPU graph
        # (~10s cold), which would otherwise land on the first user search.
        try:
            warm = [{"id": f"0:{i}", "text_ar": "الحمد لله رب العالمين"} for i in range(32)]
            app.state.search_reranker.rerank("الحمد لله", warm, top_k=1)
            logger.info("Search reranker warmed up.")
        except Exception as exc:  # pragma: no cover
            logger.warning("Reranker warmup skipped: %s", exc)
    # Durable session history + feedback (SQLite).
    app.state.store = Store()
    logger.info(
        "Engine ready (LLM provider=%s, model=%s); lexical analyzer ready.",
        app.state.engine.llm.provider,
        app.state.engine.llm.model,
    )
    yield
    app.state.store.close()
    logger.info("Shutting down.")


app = FastAPI(title="Quran RAG API", version="0.1.0", lifespan=lifespan)

# CORS
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(chat_router.router)
app.include_router(search_router.router)
app.include_router(lexical_router.router)
app.include_router(verse_router.router)
app.include_router(verse_lookup_router.router)
app.include_router(feedback_router.router)
app.include_router(sessions_router.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Report backend readiness: Qdrant reachable and LLM available."""
    engine = getattr(app.state, "engine", None)
    if engine is None:
        return {"status": "starting", "qdrant": False, "llm": False}
    qdrant_ok = engine.retriever.hybrid.qdrant.ping()
    llm_ok = engine.llm.health()
    status = "ok" if (qdrant_ok and llm_ok) else "degraded"
    return {"status": status, "qdrant": qdrant_ok, "llm": llm_ok}
