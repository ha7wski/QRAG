"""Unit tests for root lexical lookup (retrieval/lexical_retriever.py).

Builds a LexicalRetriever via __new__ with an injected in-memory morphology
index, so the tests never load data/processed files or the morphology backend
(no disk, no network, fast).
"""
from retrieval.lexical_retriever import LexicalRetriever, _sample_evenly


def _retriever(index: dict) -> LexicalRetriever:
    lr = LexicalRetriever.__new__(LexicalRetriever)  # bypass disk-loading __init__
    lr.index = index
    lr.verses_by_id = {}
    lr._get_root = lambda w: ""  # backend stub (unused on the tested paths)
    return lr


def test_sample_evenly_returns_all_when_smaller_than_k():
    assert _sample_evenly([1, 2, 3], 5) == [1, 2, 3]


def test_sample_evenly_spreads_across_the_list():
    out = _sample_evenly(list(range(100)), 10)
    assert len(out) == 10
    assert out[0] == 0
    assert out == sorted(out)  # order preserved


def test_retrieve_known_root():
    lr = _retriever(
        {"ر-ح-م": {"forms_found": ["رحمة", "رحيم"], "verses": ["1:1", "1:3"], "count": 2}}
    )
    r = lr.retrieve_by_root("ر-ح-م")
    assert r["occurrences_count"] == 2
    assert r["forms"] == ["رحمة", "رحيم"]
    assert r["verse_ids"] == ["1:1", "1:3"]


def test_retrieve_unknown_root_returns_empty_structure():
    r = _retriever({}).retrieve_by_root("xyz")
    assert r["occurrences_count"] == 0
    assert r["forms"] == []
    assert r["verses"] == []
    assert r["verse_ids"] == []


def test_extract_root_empty_input():
    lr = _retriever({"ر-ح-م": {}})
    assert lr.extract_root("") == ""
    assert lr.extract_root("   ") == ""


def test_extract_root_accepts_already_canonical_form():
    lr = _retriever({"ر-ح-م": {"verses": [], "forms_found": [], "count": 0}})
    assert lr.extract_root("ر-ح-م") == "ر-ح-م"


def test_extract_root_joins_bare_consonant_root():
    # "رحم" → "ر-ح-م" when that joined key exists in the index.
    lr = _retriever({"ر-ح-م": {"verses": [], "forms_found": [], "count": 0}})
    assert lr.extract_root("رحم") == "ر-ح-م"
