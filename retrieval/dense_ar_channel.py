"""
dense_ar_channel.py — Arabic dense candidates for GET /search (change
`arabic-retrieval-models`, configuration C-rrf).

A callable `(query, top_k, filters) -> [verse_id]` over the `QDRANT_COLLECTION_AR`
collection. It owns NO model and NO Qdrant client: it borrows the chat engine's
`HybridSearch.embedder` and `HybridSearch.qdrant.client`, so the process holds one E5
whichever path uses it first (and a second embedded client on the same directory would
hit Qdrant's exclusive lock anyway).

It ABSTAINS — returns [] and logs once — when the collection is missing, was built
with another model or text format, or anything fails: the route then builds its pool
exactly as it does without the channel.
"""
from __future__ import annotations

import logging
import os

from indexing import embedder_ar
from indexing.qdrant_store import _build_filter

logger = logging.getLogger("quran_rag.search")

class DenseArChannel:
    def __init__(self, hybrid, collection: str | None = None):
        self._hybrid = hybrid
        self.collection = collection or os.getenv(
            "QDRANT_COLLECTION_AR", embedder_ar.DEFAULT_COLLECTION
        )
        self._checked = False
        self._failed = False

    @property
    def available(self) -> bool:
        return self._checked and not self._failed

    def _abstain(self, reason: str) -> list[str]:
        if not self._failed:
            logger.warning("Arabic dense channel off for this process: %s", reason)
        self._failed = True
        return []

    def _check(self) -> str | None:
        """Why the collection cannot be trusted with the shared embedder, or None."""
        client = self._hybrid.qdrant.client
        if not client.collection_exists(self.collection):
            return (f"collection {self.collection!r} missing — build it with "
                    "`python indexing/build_index_ar.py` (backend stopped)")
        points, _ = client.scroll(self.collection, limit=1, with_payload=True)
        if not points:
            return f"collection {self.collection!r} is empty"
        payload = points[0].payload or {}
        model = self._hybrid.embedder.model_name
        if payload.get("emb_model") != model:
            return f"built with {payload.get('emb_model')!r}, shared embedder is {model!r}"
        if payload.get("emb_format") != embedder_ar.FORMAT:
            return f"built in format {payload.get('emb_format')!r}, expected {embedder_ar.FORMAT!r}"
        return None

    def __call__(self, query: str, top_k: int, filters: dict | None = None) -> list[str]:
        if self._failed:
            return []
        try:
            if not self._checked:
                reason = self._check()
                self._checked = True
                if reason:
                    return self._abstain(reason)
            vec = self._hybrid.embedder.embed_texts([embedder_ar.query_text(query)])[0]
            response = self._hybrid.qdrant.client.query_points(
                collection_name=self.collection,
                query=vec,
                query_filter=_build_filter(filters),
                limit=top_k,
                with_payload=["id"],
            )
            return [p.payload["id"] for p in response.points]
        except Exception as exc:  # degrade, never fail the request
            return self._abstain(f"{type(exc).__name__}: {exc}")
