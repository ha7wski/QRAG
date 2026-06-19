"""
bm25_index.py — Sparse lexical index (BM25Okapi).

Builds a BM25 index over the concatenation of each verse's clean Arabic text
and its French/English translations (translations are empty in phase 1).
Tokenization is whitespace-based after light Arabic normalization, which
makes exact-term retrieval (e.g. root forms) effective.

Serialized to `data/processed/bm25_index.pkl`.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

from rank_bm25 import BM25Okapi

# Reuse the shared normalizer so BM25 and the dense path agree on text.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestion.normalizer import normalize_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "data" / "processed" / "bm25_index.pkl"


def _index_text(verse: dict) -> str:
    """Concatenate the searchable fields for a verse."""
    parts = [
        verse.get("text_ar_clean", ""),
        verse.get("translation_fr", ""),
        verse.get("translation_en", ""),
    ]
    return " ".join(p for p in parts if p)


def tokenize(text: str) -> list[str]:
    """Normalize then split on whitespace.

    For Arabic we also fold ta marbuta (ة → ه) and final alif-maqsura here,
    which helps exact matching of root forms without altering stored text.
    """
    norm = normalize_text(text)
    norm = norm.replace("ة", "ه")
    tokens = [t for t in norm.lower().split() if t]
    return tokens


class BM25Index:
    def __init__(self):
        self.bm25: BM25Okapi | None = None
        self.verse_ids: list[str] = []

    def build(self, verses: list[dict]) -> "BM25Index":
        """Build the index from verses (order defines the doc-id mapping)."""
        corpus = [tokenize(_index_text(v)) for v in verses]
        self.verse_ids = [v["id"] for v in verses]
        self.bm25 = BM25Okapi(corpus)
        return self

    def search(self, query: str, top_k: int = 20) -> list[tuple[str, float]]:
        """Return the top-k (verse_id, score) pairs for a query."""
        if self.bm25 is None:
            raise RuntimeError("BM25 index not built or loaded.")
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]
        return [(self.verse_ids[i], float(scores[i])) for i in ranked]

    def save(self, path: Path = INDEX_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump({"bm25": self.bm25, "verse_ids": self.verse_ids}, f)

    @classmethod
    def load(cls, path: Path = INDEX_PATH) -> "BM25Index":
        if not path.exists():
            raise FileNotFoundError(
                f"BM25 index not found at {path}. Run indexing/build_index.py first."
            )
        with path.open("rb") as f:
            data = pickle.load(f)
        obj = cls()
        obj.bm25 = data["bm25"]
        obj.verse_ids = data["verse_ids"]
        return obj


if __name__ == "__main__":
    import json

    verses = json.load(
        open(ROOT / "data" / "processed" / "verses_final.json", encoding="utf-8")
    )
    idx = BM25Index().build(verses)
    idx.save()
    print(f"BM25 index built over {len(verses)} verses → {INDEX_PATH}")
    print("Sample query 'الرحمن الرحيم':")
    for vid, score in idx.search("الرحمن الرحيم", top_k=5):
        print(f"  {vid}  score={score:.3f}")
