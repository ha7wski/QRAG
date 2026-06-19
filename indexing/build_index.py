"""
build_index.py — Build the dense (Qdrant) and sparse (BM25) indexes.

Steps:
  1. Load verses from data/processed/verses_final.json
  2. Verify Qdrant is reachable (clear error otherwise)
  3. Create/ensure the collection
  4. Embed verses and upsert them into Qdrant in chunks, with a checkpoint
     for resumable runs
  5. Build and persist the BM25 sparse index

Checkpoint: the index of the last verse successfully upserted is written to
data/processed/.checkpoint, so an interrupted run resumes where it stopped.
Use --rebuild to recreate the collection and ignore the checkpoint.

Usage:
    python indexing/build_index.py [--rebuild]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indexing.bm25_index import BM25Index  # noqa: E402
from indexing.embedder import Embedder  # noqa: E402
from indexing.qdrant_store import QuranQdrant  # noqa: E402

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(it, **kwargs):  # type: ignore
        return it

ROOT = Path(__file__).resolve().parents[1]
VERSES_FINAL = ROOT / "data" / "processed" / "verses_final.json"
CHECKPOINT = ROOT / "data" / "processed" / ".checkpoint"

CHUNK_SIZE = 200  # verses embedded + upserted per checkpointed chunk


def _load_verses() -> list[dict]:
    if not VERSES_FINAL.exists():
        raise FileNotFoundError(
            f"{VERSES_FINAL} not found. Run `python ingestion/run_pipeline.py` first."
        )
    return json.load(open(VERSES_FINAL, encoding="utf-8"))


def _read_checkpoint() -> int:
    if CHECKPOINT.exists():
        try:
            return int(CHECKPOINT.read_text().strip())
        except ValueError:
            return 0
    return 0


def _write_checkpoint(index: int) -> None:
    CHECKPOINT.write_text(str(index))


def build_dense(verses: list[dict], rebuild: bool) -> None:
    embedder = Embedder()
    qdrant = QuranQdrant(vector_size=embedder.dimension)
    qdrant.require_connection()
    qdrant.create_collection(recreate=rebuild)

    start = 0 if rebuild else _read_checkpoint()
    if start:
        print(f"Resuming from checkpoint at verse index {start}.")

    total = len(verses)
    for chunk_start in tqdm(
        range(start, total, CHUNK_SIZE), desc="indexing (dense)", unit="chunk"
    ):
        chunk = verses[chunk_start : chunk_start + CHUNK_SIZE]
        vectors = embedder.embed_passages(chunk, show_progress=False)
        qdrant.upsert_verses(chunk, vectors)
        _write_checkpoint(chunk_start + len(chunk))

    print(f"Dense index complete: {total} verses in '{qdrant.collection}'.")


def build_sparse(verses: list[dict]) -> None:
    idx = BM25Index().build(verses)
    idx.save()
    print(f"Sparse BM25 index complete: {len(verses)} verses.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Quran RAG indexes.")
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="Recreate the Qdrant collection and ignore the checkpoint.",
    )
    args = ap.parse_args()

    print("=" * 60)
    print("Quran RAG — index build")
    print("=" * 60)
    verses = _load_verses()
    print(f"Loaded {len(verses)} verses.")

    try:
        build_dense(verses, rebuild=args.rebuild)
    except ConnectionError as exc:
        print(f"\n❌ {exc}")
        return 1

    build_sparse(verses)

    if CHECKPOINT.exists():
        CHECKPOINT.unlink()  # clean slate after a successful full run
    print("=" * 60)
    print("Done. Test it with:")
    print('  python -c "from indexing.hybrid_search import HybridSearch; '
          "print(HybridSearch().search('الرحمن الرحيم', top_k=5))\"")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
