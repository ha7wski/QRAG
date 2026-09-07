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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load .env BEFORE importing anything that reads env (routers read their tuning
# constants at import time; the lifespan reads toggles at startup). The app must
# carry its own config regardless of how it is launched — previously only the
# launcher (local-dev/start.sh) exported these, so a bare `uvicorn api.main:app`
# silently ran with defaults (e.g. SEARCH_RERANK_ENABLED off → degraded /search).
# override=False: a var already set in the real environment still wins over .env.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from api.middleware import RequestLoggingMiddleware  # noqa: E402
from api.routers import chat as chat_router  # noqa: E402
from api.routers import fassila as fassila_router  # noqa: E402
from api.routers import feedback as feedback_router  # noqa: E402
from api.routers import lexical as lexical_router  # noqa: E402
from api.routers import lisan as lisan_router  # noqa: E402
from api.routers import madar as madar_router  # noqa: E402
from api.routers import qlisan as qlisan_router  # noqa: E402
from api.routers import search as search_router  # noqa: E402
from api.routers import tahlil as tahlil_router  # noqa: E402
from api.routers import sessions as sessions_router  # noqa: E402
from api.routers import verse as verse_router  # noqa: E402
from api.routers import verse_lookup as verse_lookup_router  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("quran_rag.api")


class LazyReranker:
    """Holds the GET /search cross-encoder, built on first use.

    The model is ~1.1 GB of wired Metal memory on Apple Silicon — memory macOS
    can neither compress nor swap. Building it in the lifespan charged every
    launch for it, including sessions that only ever used the Arabic study
    tools. `enabled` (SEARCH_RERANK_ENABLED) now means "allowed to load", not
    "load now": the first similar-verse search pays, once.

    A load failure degrades to no reranking rather than failing the request,
    and is not retried on every subsequent search.
    """

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self._model = None
        self._failed = False

    def get(self):
        """Return the reranker, building it on first call. None = no reranking."""
        if not self.enabled or self._failed:
            return None
        if self._model is None:
            from retrieval.reranker import Reranker

            logger.info("Loading search reranker on first use (~1.1 GB)...")
            try:
                self._model = Reranker()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Reranker unavailable, search will not rerank: %s", exc)
                self._failed = True
                return None
            logger.info("Search reranker ready.")
        return self._model

    @property
    def loaded(self) -> bool:
        """True once the model has actually been paid for."""
        return self._model is not None


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
    # Deliberately NOT built here: the provider hands the model over on the
    # first search that needs it. The old startup warmup is gone with it — it
    # only ever existed to move the cold-start cost off the first search, which
    # is now the very moment the model loads anyway.
    app.state.search_reranker_provider = LazyReranker(
        enabled=os.getenv("SEARCH_RERANK_ENABLED", "0") == "1"
    )
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
app.include_router(lisan_router.router)
app.include_router(madar_router.router)
app.include_router(qlisan_router.router)
app.include_router(tahlil_router.router)
app.include_router(verse_router.router)
app.include_router(verse_lookup_router.router)
app.include_router(fassila_router.router)
app.include_router(feedback_router.router)
app.include_router(sessions_router.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Report backend readiness: Qdrant reachable and LLM available."""
    engine = getattr(app.state, "engine", None)
    if engine is None:
        return {"status": "starting", "qdrant": False, "llm": False}
    hybrid = engine.retriever.hybrid
    # Neither probe loads a model: opening the Qdrant store no longer reads the
    # embedder's dimension, and llm.health() only lists Ollama's models.
    qdrant_ok = hybrid.qdrant.ping()
    llm_ok = engine.llm.health()
    provider = getattr(app.state, "search_reranker_provider", None)
    status = "ok" if (qdrant_ok and llm_ok) else "degraded"
    return {
        "status": status,
        "qdrant": qdrant_ok,
        "llm": llm_ok,
        # Which heavy models are resident right now. Both load on first use, so
        # a freshly started backend reports false/false and holds no model
        # memory at all — this is what makes that visible rather than assumed.
        "models": {
            "embedder": hybrid.models_loaded,
            "search_reranker": provider.loaded if provider is not None else False,
        },
        "qdrant_location": hybrid.qdrant.location,
    }
