"""
qdrant_store.py — Thin wrapper around the official Qdrant client.

Named `qdrant_store` (not `qdrant_client`) to avoid shadowing the installed
`qdrant_client` PyPI package on sys.path when scripts in this directory run.

Manages the `quran_verses` collection: creation, batched upserts, and
filtered vector search. Point IDs are derived deterministically from the
verse reference: id = surah_number * 1000 + ayah_number.
"""
from __future__ import annotations

import os
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_COLLECTION = "quran_verses"
DEFAULT_URL = "http://localhost:6333"
UPSERT_BATCH_SIZE = 100


def point_id(surah_number: int, ayah_number: int) -> int:
    """Stable integer point ID for a verse."""
    return surah_number * 1000 + ayah_number


class QuranQdrant:
    def __init__(
        self,
        url: str | None = None,
        collection: str | None = None,
        vector_size: int = 1024,
        path: str | None = None,
    ):
        """Open the store, in embedded or server mode.

        Embedded mode (`path`, or the QDRANT_PATH env var) runs Qdrant inside
        this process against a local directory — no server, no Docker VM. The
        corpus is ~24 MB of vectors, far below anything that needs a server.
        An explicit `url` wins over QDRANT_PATH: a caller asking for a server
        gets a server.

        Caveat: embedded mode takes an exclusive file lock on the directory, so
        build_index.py and the API cannot hold it at the same time.
        """
        self.collection = collection or os.getenv(
            "QDRANT_COLLECTION", DEFAULT_COLLECTION
        )
        self.vector_size = vector_size

        raw_path = path or (None if url else os.getenv("QDRANT_PATH"))
        if raw_path:
            # Project convention: resolve against ROOT, never the cwd, so the
            # backend and the indexer agree on the directory from anywhere.
            self.path = Path(raw_path)
            if not self.path.is_absolute():
                self.path = ROOT / self.path
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.url = None
            self.embedded = True
            self.client = QdrantClient(path=str(self.path))
        else:
            self.path = None
            self.url = url or os.getenv("QDRANT_URL", DEFAULT_URL)
            self.embedded = False
            self.client = QdrantClient(url=self.url, timeout=30.0)

    @property
    def location(self) -> str:
        """Human-readable description of where this store lives."""
        return f"{self.path} (embedded)" if self.embedded else str(self.url)

    def ping(self) -> bool:
        """Return True if the Qdrant store is usable."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def require_connection(self) -> None:
        """Raise a clear error if Qdrant is not reachable."""
        if self.ping():
            return
        if self.embedded:
            raise ConnectionError(
                f"Cannot open the embedded Qdrant store at {self.path}. "
                "Embedded mode takes an exclusive lock — check that no other "
                "process (the API, or build_index.py) is already holding it."
            )
        raise ConnectionError(
            f"Cannot reach Qdrant at {self.url}. "
            "Start it with `docker compose up -d qdrant` and confirm the "
            "port (6333) is exposed."
        )

    def create_collection(self, recreate: bool = False) -> None:
        """Create the collection and payload indexes (idempotent)."""
        exists = self.client.collection_exists(self.collection)
        if exists and not recreate:
            return
        if exists and recreate:
            self.client.delete_collection(self.collection)

        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qm.VectorParams(
                size=self.vector_size, distance=qm.Distance.COSINE
            ),
        )

        # Payload indexes used for filtering.
        self.client.create_payload_index(
            self.collection, "surah_number", qm.PayloadSchemaType.INTEGER
        )
        self.client.create_payload_index(
            self.collection, "period", qm.PayloadSchemaType.KEYWORD
        )
        self.client.create_payload_index(
            self.collection, "juz", qm.PayloadSchemaType.INTEGER
        )

    def upsert_verses(self, verses: list[dict], vectors: list[list[float]]) -> int:
        """Upsert verses with their vectors in batches of 100. Returns count."""
        if len(verses) != len(vectors):
            raise ValueError("verses and vectors must have the same length")

        total = 0
        for start in range(0, len(verses), UPSERT_BATCH_SIZE):
            chunk_v = verses[start : start + UPSERT_BATCH_SIZE]
            chunk_vec = vectors[start : start + UPSERT_BATCH_SIZE]
            points = [
                qm.PointStruct(
                    id=point_id(v["surah_number"], v["ayah_number"]),
                    vector=vec,
                    payload=_payload(v),
                )
                for v, vec in zip(chunk_v, chunk_vec)
            ]
            self.client.upsert(collection_name=self.collection, points=points)
            total += len(points)
        return total

    def search(
        self,
        query_vector: list[float],
        filters: dict | None = None,
        top_k: int = 20,
    ) -> list[dict]:
        """Vector search with optional payload filters.

        `filters` accepts keys: surah_number (int), period (str), juz (int).
        Returns a list of {id, score, payload} dicts.
        """
        qfilter = _build_filter(filters)
        # query_points is the current API (replaces the deprecated `search`).
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=qfilter,
            limit=top_k,
            with_payload=True,
        )
        return [
            {"id": h.payload.get("id"), "score": h.score, "payload": h.payload}
            for h in response.points
        ]


def _payload(v: dict) -> dict:
    """Project the verse fields stored in Qdrant payload."""
    return {
        "id": v["id"],
        "surah_number": v["surah_number"],
        "surah_name_ar": v["surah_name_ar"],
        "surah_name_en": v["surah_name_en"],
        "surah_name_fr": v["surah_name_fr"],
        "ayah_number": v["ayah_number"],
        "text_ar": v["text_ar"],
        "text_ar_clean": v["text_ar_clean"],
        "translation_fr": v["translation_fr"],
        "translation_en": v["translation_en"],
        "period": v["period"],
        "juz": v["juz"],
    }


def _build_filter(filters: dict | None):
    """Translate a plain dict of filters into a Qdrant Filter object."""
    if not filters:
        return None
    must = []
    for key in ("surah_number", "period", "juz"):
        if filters.get(key) is not None:
            must.append(
                qm.FieldCondition(
                    key=key, match=qm.MatchValue(value=filters[key])
                )
            )
    return qm.Filter(must=must) if must else None
