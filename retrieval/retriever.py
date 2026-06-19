"""
retriever.py — Main hybrid retriever for the RAG pipeline.

Wraps the dense+sparse HybridSearch and returns full verse records. It can
also expand each hit with its immediate neighbors (the verses just before and
after, within the same surah), since a verse's meaning often depends on its
surrounding context.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indexing.corpus import load_verses  # noqa: E402
from indexing.hybrid_search import HybridSearch  # noqa: E402


# How many candidates to pull from hybrid search before reranking.
CANDIDATE_K = 20


class Retriever:
    def __init__(self, hybrid: HybridSearch | None = None, reranker=None):
        self.hybrid = hybrid or HybridSearch()
        self.reranker = reranker  # optional retrieval.reranker.Reranker
        self._verses = self._load_ordered()
        self._pos = {v["id"]: i for i, v in enumerate(self._verses)}

    @staticmethod
    def _load_ordered() -> list[dict]:
        # sorted() returns a NEW list (over the shared verse dicts) so we never
        # mutate the cached corpus in place. Canonical order by (surah, ayah)
        # for neighbor lookups.
        return sorted(
            load_verses(), key=lambda v: (v["surah_number"], v["ayah_number"])
        )

    def retrieve(
        self, query: str, top_k: int = 5, filters: dict | None = None
    ) -> list[dict]:
        """Return the top-k full verse records (with a `score` field).

        When a reranker is configured, a wider candidate set (CANDIDATE_K) is
        retrieved and reordered by the cross-encoder before truncation.
        """
        fetch_k = CANDIDATE_K if self.reranker is not None else top_k
        hits = self.hybrid.search(query, top_k=fetch_k, filters=filters)
        results = []
        for h in hits:
            v = self._full(h["id"])
            if v is not None:
                results.append({**v, "score": h["score"]})

        if self.reranker is not None:
            results = self.reranker.rerank(query, results, top_k=top_k)
        else:
            results = results[:top_k]
        return results

    def neighbors(self, verse_id: str, window: int = 1) -> list[dict]:
        """Return verses within `window` positions, same surah, ordered."""
        if verse_id not in self._pos:
            return []
        idx = self._pos[verse_id]
        surah = self._verses[idx]["surah_number"]
        lo, hi = max(0, idx - window), min(len(self._verses), idx + window + 1)
        return [v for v in self._verses[lo:hi] if v["surah_number"] == surah]

    def retrieve_with_context(
        self,
        query: str,
        top_k: int = 5,
        window: int = 1,
        filters: dict | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """Return (hits, context_verses).

        `hits` are the ranked matches. `context_verses` is the deduplicated,
        canonically ordered union of the hits and their neighbors — this is
        what gets sent to the LLM.
        """
        hits = self.retrieve(query, top_k=top_k, filters=filters)
        seen: dict[str, dict] = {}
        for h in hits:
            for n in self.neighbors(h["id"], window=window):
                seen.setdefault(n["id"], n)
        context = sorted(
            seen.values(),
            key=lambda v: (v["surah_number"], v["ayah_number"]),
        )
        return hits, context

    def _full(self, verse_id: str) -> dict | None:
        pos = self._pos.get(verse_id)
        return self._verses[pos] if pos is not None else None

    # ── Direct lookups (P1 deep-linking; no retrieval involved) ──────────
    def get_by_ref(self, surah_number: int, ayah_number: int) -> dict | None:
        """Return the full verse record for a (surah, ayah), or None."""
        return self._full(f"{surah_number}:{ayah_number}")

    def get_surah(self, surah_number: int) -> list[dict]:
        """Return every verse of a surah, ordered by ayah."""
        return [v for v in self._verses if v["surah_number"] == surah_number]

    def list_surahs(self) -> list[dict]:
        """Return all 114 surahs as {number, name_ar/en/fr, ayah_count}, ordered."""
        out: list[dict] = []
        cur: dict | None = None
        for v in self._verses:  # already sorted by (surah, ayah)
            sn = v["surah_number"]
            if cur is None or cur["number"] != sn:
                cur = {
                    "number": sn,
                    "name_ar": v.get("surah_name_ar", ""),
                    "name_en": v.get("surah_name_en", ""),
                    "name_fr": v.get("surah_name_fr", ""),
                    "ayah_count": 0,
                }
                out.append(cur)
            cur["ayah_count"] += 1
        return out

    def prev_next(self, verse_id: str) -> tuple[str | None, str | None]:
        """Return the (prev_id, next_id) within the same surah, or None at edges."""
        idx = self._pos.get(verse_id)
        if idx is None:
            return None, None
        surah = self._verses[idx]["surah_number"]
        prev_v = self._verses[idx - 1] if idx > 0 else None
        next_v = self._verses[idx + 1] if idx + 1 < len(self._verses) else None
        prev_id = prev_v["id"] if prev_v and prev_v["surah_number"] == surah else None
        next_id = next_v["id"] if next_v and next_v["surah_number"] == surah else None
        return prev_id, next_id


if __name__ == "__main__":
    r = Retriever()
    hits, ctx = r.retrieve_with_context("الصبر", top_k=3, window=1)
    print(f"{len(hits)} hits, {len(ctx)} context verses")
    for h in hits:
        print(f"  hit {h['id']}  score={h['score']:.4f}  {h['text_ar']}")
