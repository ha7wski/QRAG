"""
build_index_ar.py — Build the Arabic dense collection (`QDRANT_COLLECTION_AR`).

A SEPARATE collection from `quran_verses`, which this script never opens for writing:
same point ids, same payload and payload indexes (so the chat path can later query it
by name), plus `emb_model` / `emb_format` on every point — the contract a reader checks
before trusting a vector. Text formatting lives in `indexing/embedder_ar.py`.

Like build_index.py it needs the embedded Qdrant lock: stop the backend first.

Usage:
    python indexing/build_index_ar.py [--rebuild]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indexing import embedder_ar  # noqa: E402
from indexing.qdrant_store import (  # noqa: E402
    DEFAULT_COLLECTION,
    UPSERT_BATCH_SIZE,
    QuranQdrant,
    _payload,
    point_id,
)

CHUNK_SIZE = 200


def collection_names() -> tuple[str, str]:
    """(Arabic collection, existing collection) as the backend would resolve them."""
    return (
        os.getenv("QDRANT_COLLECTION_AR", embedder_ar.DEFAULT_COLLECTION),
        os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION),
    )


def check_names(ar: str, existing: str) -> None:
    """Refuse any name that would make this build touch the existing collection."""
    if not ar or ar in (existing, DEFAULT_COLLECTION):
        raise SystemExit(
            f"QDRANT_COLLECTION_AR={ar!r} names the existing collection "
            f"({existing!r}); choose another name — this build never writes there."
        )


def check_model(model_name: str) -> None:
    if model_name != embedder_ar.EXPECTED_MODEL:
        raise SystemExit(
            f"The embedder loaded {model_name!r}, not {embedder_ar.EXPECTED_MODEL!r} "
            f"(the model format {embedder_ar.FORMAT!r} was measured with). Refusing to build."
        )


def point_payload(verse: dict, model_name: str) -> dict:
    return {**_payload(verse), "emb_model": model_name, "emb_format": embedder_ar.FORMAT}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the Arabic dense collection.")
    ap.add_argument("--rebuild", action="store_true",
                    help="Recreate the Arabic collection if it exists.")
    args = ap.parse_args()

    ar, existing = collection_names()
    check_names(ar, existing)

    from qdrant_client.http import models as qm

    from indexing.embedder import Embedder
    from quran_data.corpus import load_verses

    verses = sorted(load_verses(), key=lambda v: (v["surah_number"], v["ayah_number"]))
    embedder = Embedder()
    check_model(embedder.model_name)
    store = QuranQdrant(collection=ar, vector_size=embedder.dimension)
    store.require_connection()
    if store.client.collection_exists(ar) and not args.rebuild:
        raise SystemExit(f"Collection {ar!r} already exists; pass --rebuild to recreate it.")
    store.create_collection(recreate=args.rebuild)

    # One encode call over the whole corpus, as the benchmark encoded it (the call's
    # length grouping is then the measured one).
    all_vectors = embedder.embed_texts([embedder_ar.passage_text(v) for v in verses])
    for start in range(0, len(verses), CHUNK_SIZE):
        chunk = verses[start:start + CHUNK_SIZE]
        vectors = all_vectors[start:start + CHUNK_SIZE]
        for i in range(0, len(chunk), UPSERT_BATCH_SIZE):
            store.client.upsert(collection_name=ar, points=[
                qm.PointStruct(id=point_id(v["surah_number"], v["ayah_number"]), vector=vec,
                               payload=point_payload(v, embedder.model_name))
                for v, vec in zip(chunk[i:i + UPSERT_BATCH_SIZE], vectors[i:i + UPSERT_BATCH_SIZE])
            ])
        print(f"  {start + len(chunk)}/{len(verses)}")

    count = store.client.count(ar, exact=True).count
    print(f"Arabic dense collection complete: {count} points in {ar!r} "
          f"({embedder.model_name}, {embedder_ar.FORMAT}).")
    return 0 if count == len(verses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
