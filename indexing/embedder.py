"""
embedder.py — Dense embedding generation.

Wraps a sentence-transformers model to embed verses (passages) and user
queries. The model follows the E5 instruct convention, so passages are
prefixed with "passage: " and queries with "query: ".

Primary model : intfloat/multilingual-e5-large-instruct (1024 dims)
Light fallback : sentence-transformers/paraphrase-multilingual-mpnet-base-v2
                 (768 dims) — used automatically if the primary model fails
                 to load (e.g. not enough RAM).

Device is auto-detected: CUDA → MPS (Apple Silicon) → CPU.
"""
from __future__ import annotations

import os

DEFAULT_MODEL = "intfloat/multilingual-e5-large-instruct"
FALLBACK_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
DEFAULT_BATCH_SIZE = 32


def _resolve_device(requested: str) -> str:
    """Resolve the embedding device, honoring an explicit request or 'auto'."""
    import torch

    if requested and requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _passage_text(verse: dict) -> str:
    """Build the text to embed for a verse.

    Translations are empty in phase 1, so this naturally reduces to the
    clean Arabic text; it already supports French/English once they are
    added in phase 2.
    """
    parts = [
        verse.get("text_ar_clean", ""),
        verse.get("translation_fr", ""),
        verse.get("translation_en", ""),
    ]
    body = " ".join(p for p in parts if p).strip()
    return f"passage: {body}"


class Embedder:
    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int | None = None,
    ):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)
        self.device = _resolve_device(device or os.getenv("EMBEDDING_DEVICE", "auto"))
        self.batch_size = int(
            batch_size or os.getenv("EMBEDDING_BATCH_SIZE", DEFAULT_BATCH_SIZE)
        )

        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
        except Exception as exc:
            print(
                f"⚠️  Failed to load '{self.model_name}' ({exc}). "
                f"Falling back to '{FALLBACK_MODEL}'."
            )
            self.model_name = FALLBACK_MODEL
            self.model = SentenceTransformer(self.model_name, device=self.device)

        # `get_embedding_dimension` is the current name; fall back to the
        # older `get_sentence_embedding_dimension` for compatibility.
        if hasattr(self.model, "get_embedding_dimension"):
            self.dimension = self.model.get_embedding_dimension()
        else:
            self.dimension = self.model.get_sentence_embedding_dimension()
        print(
            f"Embedder ready: {self.model_name} "
            f"(dim={self.dimension}, device={self.device})"
        )

    def embed_texts(self, texts: list[str], show_progress: bool = False):
        """Embed an arbitrary list of texts; returns a list of float vectors."""
        vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,  # cosine-ready
            convert_to_numpy=True,
        )
        return vectors.tolist()

    def embed_passages(self, verses: list[dict], show_progress: bool = True):
        """Embed a list of verse dicts (using their passage text)."""
        return self.embed_texts(
            [_passage_text(v) for v in verses], show_progress=show_progress
        )

    def embed_query(self, query: str):
        """Embed a single user query; returns one float vector."""
        return self.embed_texts([f"query: {query}"])[0]


if __name__ == "__main__":
    emb = Embedder()
    v = emb.embed_query("الرحمن الرحيم")
    print(f"query vector dim = {len(v)}")
