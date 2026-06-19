"""
evaluate.py — Retrieval quality evaluation against tests/eval/qa_dataset.json.

For each reference question it runs the retriever and computes:
  - recall@k : fraction of the gold verses found in the top-k
  - hit@k    : 1 if at least one gold verse is in the top-k
  - RR       : reciprocal rank of the first gold verse (0 if none)

It reports per-question rows, a per-language breakdown (recall@k, hit-rate,
MRR for ar / fr / en / mixed), and the overall macro-averages.

Usage:
    python tests/eval/evaluate.py                 # baseline hybrid retrieval
    python tests/eval/evaluate.py --rerank        # with cross-encoder rerank
    python tests/eval/evaluate.py --top-k 10
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from retrieval.retriever import Retriever  # noqa: E402

DATASET = Path(__file__).resolve().parent / "qa_dataset.json"


def _score_one(gold: set[str], retrieved: list[str]) -> tuple[float, float, float, str]:
    """Return (recall, hit, reciprocal_rank, first_relevant_label)."""
    found = [vid for vid in retrieved if vid in gold]
    recall = len(set(found)) / len(gold) if gold else 0.0
    hit = 1.0 if found else 0.0
    rr, first = 0.0, "-"
    for rank, vid in enumerate(retrieved, start=1):
        if vid in gold:
            rr = 1.0 / rank
            first = f"{vid} @{rank}"
            break
    return recall, hit, rr, first


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def evaluate(top_k: int, rerank: bool) -> None:
    data = json.load(open(DATASET, encoding="utf-8"))
    questions = data["questions"]

    reranker = None
    if rerank:
        from retrieval.reranker import Reranker

        reranker = Reranker()
    retriever = Retriever(reranker=reranker)

    print(f"\nEvaluation — top_k={top_k}, rerank={rerank}, n={len(questions)}")
    print("-" * 74)
    print(f"{'id':<16}{'lang':<7}{'recall@k':>10}{'hit@k':>7}{'RR':>7}   first relevant")
    print("-" * 74)

    # Aggregates, overall and per language.
    by_lang: dict[str, dict[str, list]] = defaultdict(
        lambda: {"recall": [], "hit": [], "rr": []}
    )
    overall = {"recall": [], "hit": [], "rr": []}

    for q in questions:
        gold = set(q["relevant_verse_ids"])
        results = retriever.retrieve(q["question"], top_k=top_k)
        retrieved = [r["id"] for r in results]
        recall, hit, rr, first = _score_one(gold, retrieved)

        lang = q["language"]
        for metric, val in (("recall", recall), ("hit", hit), ("rr", rr)):
            by_lang[lang][metric].append(val)
            overall[metric].append(val)
        print(f"{q['id']:<16}{lang:<7}{recall:>10.2f}{hit:>7.0f}{rr:>7.2f}   {first}")

    # Per-language breakdown.
    print("-" * 74)
    print(f"{'PER LANGUAGE':<16}{'n':>5}{'recall@k':>12}{'hit-rate':>11}{'MRR':>8}")
    for lang in ("ar", "fr", "en", "mixed"):
        if lang not in by_lang:
            continue
        m = by_lang[lang]
        print(f"{lang:<16}{len(m['recall']):>5}{_mean(m['recall']):>12.3f}"
              f"{_mean(m['hit']):>11.3f}{_mean(m['rr']):>8.3f}")

    # Overall.
    print("-" * 74)
    print(f"{'OVERALL':<16}{len(overall['recall']):>5}{_mean(overall['recall']):>12.3f}"
          f"{_mean(overall['hit']):>11.3f}{_mean(overall['rr']):>8.3f}")
    print("-" * 74)
    print(f"  config        : top_k={top_k}, rerank={rerank}")
    print(f"  mean recall@{top_k} : {_mean(overall['recall']):.3f}")
    print(f"  hit-rate@{top_k}    : {_mean(overall['hit']):.3f}")
    print(f"  MRR              : {_mean(overall['rr']):.3f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate retrieval quality.")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--rerank", action="store_true", help="Enable cross-encoder rerank")
    args = ap.parse_args()
    evaluate(args.top_k, args.rerank)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
