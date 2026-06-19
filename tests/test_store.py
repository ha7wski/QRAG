"""Unit tests for the SQLite session/feedback store (api/store.py).

Pure stdlib (sqlite3) — no FastAPI, network, or ML stack. Each test uses an
isolated temp DB.
"""
import pytest

from api.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.db")
    yield s
    s.close()


def test_append_turn_orders_messages(store):
    store.append_turn("s1", "Q1", "A1", [{"id": "2:153"}])
    store.append_turn("s1", "Q2", "A2")
    msgs = store.get_messages("s1")
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert [m["content"] for m in msgs] == ["Q1", "A1", "Q2", "A2"]


def test_assistant_turn_keeps_sources(store):
    store.append_turn("s1", "Q", "A", [{"id": "1:1"}, {"id": "1:2"}])
    msgs = store.get_messages("s1")
    assert msgs[0]["sources"] == []          # user turn never has sources
    assert [v["id"] for v in msgs[1]["sources"]] == ["1:1", "1:2"]


def test_get_history_strips_sources(store):
    store.append_turn("s1", "Q", "A", [{"id": "1:1"}])
    hist = store.get_history("s1")
    assert hist == [
        {"role": "user", "content": "Q"},
        {"role": "assistant", "content": "A"},
    ]


def test_sessions_are_isolated(store):
    store.append_turn("a", "Qa", "Aa")
    store.append_turn("b", "Qb", "Ab")
    assert len(store.get_messages("a")) == 2
    assert store.get_messages("a")[0]["content"] == "Qa"
    assert store.get_messages("unknown") == []


def test_feedback_upsert_and_stats(store):
    store.record_feedback("s1", 1, "up")
    store.record_feedback("s1", 3, "down")
    assert store.feedback_stats() == {"up": 1, "down": 1, "total": 2}
    # Re-rating the same answer overwrites rather than double-counting.
    store.record_feedback("s1", 1, "down")
    assert store.feedback_stats() == {"up": 0, "down": 2, "total": 2}


def test_feedback_rejects_bad_rating(store):
    with pytest.raises(ValueError):
        store.record_feedback("s1", 0, "meh")


def test_history_survives_reopen(tmp_path):
    path = tmp_path / "persist.db"
    s1 = Store(path)
    s1.append_turn("s1", "Q", "A", [{"id": "2:255"}])
    s1.close()
    # A new Store over the same file sees the persisted turn.
    s2 = Store(path)
    assert s2.get_messages("s1")[1]["sources"][0]["id"] == "2:255"
    s2.close()
