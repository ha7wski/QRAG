"""
reranker.py — Cross-encoder reranking of retrieval candidates.

A bi-encoder (the embedder) is fast but coarse; a cross-encoder scores each
(query, verse) pair jointly and is far more precise. We retrieve a wider set
(e.g. top-20) with hybrid search, then rerank down to the best few.

Model: BAAI/bge-reranker-v2-m3 — a multilingual (XLM-RoBERTa) cross-encoder
that handles Arabic, French, and English, so it actually improves ranking on
this corpus (unlike the English-only ms-marco model, which lowered recall).
It is larger (~2.3 GB); a lighter multilingual option is BAAI/bge-reranker-base.
If the model cannot be loaded, reranking degrades gracefully to a no-op
(the input order is preserved).
"""
from __future__ import annotations

import os

DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"


def _resolve_device(requested: str | None) -> str | None:
    """Resolve the device: explicit request, else CUDA → MPS → CPU."""
    if requested:
        return requested
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return None  # let sentence-transformers decide (CPU)


def _passage_text(verse: dict) -> str:
    parts = [
        verse.get("text_ar_clean") or verse.get("text_ar", ""),
        verse.get("translation_fr", ""),
        verse.get("translation_en", ""),
    ]
    return " ".join(p for p in parts if p).strip()


class Reranker:
    def __init__(self, model_name: str | None = None, device: str | None = None):
        self.model_name = model_name or os.getenv("RERANK_MODEL", DEFAULT_MODEL)
        self.device = _resolve_device(device)
        self.available = False
        self.model = None
        try:
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(self.model_name, device=self.device)
            self.available = True
            print(f"Reranker ready: {self.model_name} (device={self.device or 'auto'})")
        except Exception as exc:  # pragma: no cover
            print(f"⚠️  Reranker unavailable ({exc}); falling back to no-op.")

    def rerank(self, query: str, verses: list[dict], top_k: int = 5) -> list[dict]:
        """Return the top-k verses reordered by cross-encoder relevance.

        Each returned verse gets a `rerank_score` field. If the model is not
        available, the original order is preserved (truncated to top_k).
        """
        if not verses:
            return []
        if not self.available or self.model is None:
            return verses[:top_k]

        pairs = [(query, _passage_text(v)) for v in verses]
        scores = self.model.predict(pairs)
        ranked = sorted(
            zip(verses, scores), key=lambda vs: float(vs[1]), reverse=True
        )
        out = []
        for v, s in ranked[:top_k]:
            out.append({**v, "rerank_score": float(s)})
        return out


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from retrieval.retriever import Retriever

    r = Retriever()
    rr = Reranker()
    hits = r.retrieve("patience in hardship", top_k=20)
    print(f"retrieved {len(hits)} candidates; reranking to 5:")
    for v in rr.rerank("patience in hardship", hits, top_k=5):
        print(f"  [{v['id']}] rerank={v.get('rerank_score', 0):.3f}  {v['text_ar']}")
