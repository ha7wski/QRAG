"""
hybrid_search.py — Dense + sparse fusion via Reciprocal Rank Fusion (RRF).

Combines Qdrant dense vector results with BM25 sparse results:

    score(doc) = 1/(K + rank_dense) + 1/(K + rank_sparse)     with K = 60

It takes the top-20 from each retriever, fuses them, and returns the top-K.
Result payloads are completed from `verses_final.json` so callers always get
full verse metadata, even for docs found only by BM25.
"""
from __future__ import annotations

from indexing.bm25_index import BM25Index
from indexing.corpus import verses_by_id
from indexing.embedder import Embedder
from indexing.qdrant_store import QuranQdrant

RRF_K = 60
CANDIDATES_PER_RETRIEVER = 20


def _rrf_scores(ranked_ids: list[str], k: int = RRF_K) -> dict[str, float]:
    """Map verse_id → RRF contribution given a ranked id list (rank starts at 0)."""
    return {vid: 1.0 / (k + rank) for rank, vid in enumerate(ranked_ids)}


class HybridSearch:
    def __init__(
        self,
        embedder: Embedder | None = None,
        qdrant: QuranQdrant | None = None,
        bm25: BM25Index | None = None,
    ):
        self.embedder = embedder or Embedder()
        # Align the Qdrant vector size with the loaded embedding model.
        self.qdrant = qdrant or QuranQdrant(vector_size=self.embedder.dimension)
        self.bm25 = bm25 or BM25Index.load()
        self._verses = verses_by_id()  # shared, cached {id: verse} lookup

    def search(
        self, query: str, top_k: int = 5, filters: dict | None = None
    ) -> list[dict]:
        """Run hybrid retrieval and return the top-k verses with scores."""
        # Dense branch (Qdrant, supports payload filters).
        query_vec = self.embedder.embed_query(query)
        dense_hits = self.qdrant.search(
            query_vec, filters=filters, top_k=CANDIDATES_PER_RETRIEVER
        )
        dense_ids = [h["id"] for h in dense_hits]

        # Sparse branch (BM25, no native filters → post-filter below).
        sparse_hits = self.bm25.search(query, top_k=CANDIDATES_PER_RETRIEVER)
        sparse_ids = [vid for vid, _ in sparse_hits]
        if filters:
            sparse_ids = [vid for vid in sparse_ids if self._passes(vid, filters)]

        # Fuse with RRF.
        dense_scores = _rrf_scores(dense_ids)
        sparse_scores = _rrf_scores(sparse_ids)
        fused: dict[str, float] = {}
        for vid in set(dense_scores) | set(sparse_scores):
            fused[vid] = dense_scores.get(vid, 0.0) + sparse_scores.get(vid, 0.0)

        ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        return [self._format(vid, score) for vid, score in ranked]

    def _passes(self, vid: str, filters: dict) -> bool:
        v = self._verses.get(vid)
        if not v:
            return False
        for key in ("surah_number", "period", "juz"):
            if filters.get(key) is not None and v.get(key) != filters[key]:
                return False
        return True

    def _format(self, vid: str, score: float) -> dict:
        v = self._verses.get(vid, {"id": vid})
        return {
            "id": vid,
            "score": round(score, 6),
            "surah_number": v.get("surah_number"),
            "surah_name_ar": v.get("surah_name_ar"),
            "surah_name_en": v.get("surah_name_en"),
            "ayah_number": v.get("ayah_number"),
            "text_ar": v.get("text_ar"),
            "period": v.get("period"),
            "juz": v.get("juz"),
        }


if __name__ == "__main__":
    hs = HybridSearch()
    for r in hs.search("الرحمن الرحيم", top_k=5):
        print(f"{r['id']:>7}  score={r['score']:.4f}  {r['text_ar']}")
