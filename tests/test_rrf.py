"""Unit tests for Reciprocal Rank Fusion (indexing/hybrid_search.py).

Tests the pure scoring/fusion math only — no embedder, Qdrant, or BM25.
"""
from indexing.hybrid_search import RRF_K, _rrf_scores


def test_score_follows_1_over_k_plus_rank():
    scores = _rrf_scores(["a", "b", "c"])
    assert scores["a"] == 1.0 / (RRF_K + 0)
    assert scores["b"] == 1.0 / (RRF_K + 1)
    assert scores["c"] == 1.0 / (RRF_K + 2)


def test_scores_strictly_decrease_with_rank():
    scores = _rrf_scores(["a", "b", "c"])
    assert scores["a"] > scores["b"] > scores["c"]


def test_empty_list_yields_no_scores():
    assert _rrf_scores([]) == {}


def test_custom_k():
    assert _rrf_scores(["x"], k=10) == {"x": 1.0 / 10}


def test_fusion_rewards_documents_present_in_both_lists():
    # Reproduce hybrid_search's fusion: a doc ranked by both retrievers should
    # outscore docs ranked by only one.
    dense = _rrf_scores(["a", "b"])
    sparse = _rrf_scores(["b", "c"])
    fused = {}
    for vid in set(dense) | set(sparse):
        fused[vid] = dense.get(vid, 0.0) + sparse.get(vid, 0.0)
    assert max(fused, key=fused.get) == "b"  # the only doc in both lists


def test_equal_ranks_give_equal_contributions():
    # Ties: same rank in two independent lists → identical RRF contribution.
    left = _rrf_scores(["a", "x"])
    right = _rrf_scores(["b", "y"])
    assert left["a"] == right["b"]  # both at rank 0
    assert left["x"] == right["y"]  # both at rank 1
