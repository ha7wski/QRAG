"""
root_channel.py — Root-aware retrieval as a third RRF channel (P4).

The hybrid retriever fuses a dense (E5) and a sparse (BM25) ranked list via
Reciprocal Rank Fusion. This adds a THIRD list ranked purely by *shared Arabic
root* — the signal that directly serves تفسير القرآن بالقرآن (studying the Quran
through itself): a verse is promoted when it shares the query's content-word
roots, even if neither the surface form (BM25) nor the multilingual embedding
(dense) surfaced it.

It deliberately reuses the machinery already proven in the "Similar Verses" tab:
`SimilarVerses` cleans the query (drops function words, resolves each content
word to its QAC root with clitic/pronoun stripping) and ranks verses by
IDF-weighted root coverage — a verse matching more, and rarer, query roots ranks
higher. Here we take that ranking as the channel's ordered verse-id list; RRF
then blends it with dense+sparse by rank, so no score calibration is needed.

The channel ABSTAINS (returns []) when the query has no resolvable content root
(e.g. a purely function-word query): RRF simply sees an empty list and the result
is identical to plain dense+sparse. **ON by default** (`ROOT_CHANNEL_ENABLED=1`) —
unlike the reranker/HyDE levers it is cheap (no ML) and improves every eval metric,
so it earns the default; set `ROOT_CHANNEL_ENABLED=0` to disable. Wired in
`retrieval.retriever.Retriever` and measured by `tests/eval/evaluate.py
--root-channel` on `root_concordance_qa.json` (its objective yardstick).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class RootChannel:
    """Callable third RRF channel: (query, top_k, filters) → ranked verse ids.

    Thin adapter over `SimilarVerses.candidates_for`, which returns verse records
    ordered by IDF-weighted query-root coverage. Returns at most `top_k` ids, or
    [] when the query yields no content root (channel abstains)."""

    def __init__(self, similar_verses):
        self.sv = similar_verses

    def __call__(
        self, query: str, top_k: int, filters: dict | None = None
    ) -> list[str]:
        candidates = self.sv.candidates_for(query, filters=filters)
        if not candidates:
            return []
        return [c["id"] for c in candidates[:top_k]]


def _enabled() -> bool:
    # ON by default: cheap (dict lookups, no ML), improves every eval metric, and
    # is the core تفسير القرآن بالقرآن signal. Set ROOT_CHANNEL_ENABLED=0 to disable.
    return os.getenv("ROOT_CHANNEL_ENABLED", "1").lower() in ("1", "true", "yes")


def maybe_build() -> RootChannel | None:
    """Build the root channel if `ROOT_CHANNEL_ENABLED` is truthy, else None.

    Imports (and the ~1651-root morphology index they load) are lazy so the
    channel costs nothing when disabled."""
    if not _enabled():
        return None
    from retrieval.lexical_retriever import LexicalRetriever
    from retrieval.similar_verses import SimilarVerses

    return RootChannel(SimilarVerses(LexicalRetriever()))


if __name__ == "__main__":
    from retrieval.lexical_retriever import LexicalRetriever
    from retrieval.similar_verses import SimilarVerses

    ch = RootChannel(SimilarVerses(LexicalRetriever()))
    for q in ["الصبر عند الشدائد", "صبر", "من في على"]:
        ids = ch(q, top_k=8)
        print(f"{q!r} → {len(ids)} ids: {ids}")
