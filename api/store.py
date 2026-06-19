"""
store.py — SQLite-backed persistence for chat sessions and answer feedback.

Two concerns, one small embedded database (no extra infra — chosen over Redis
for the local/single-node deployment this project targets):

  - **Sessions:** each chat turn (user question, assistant answer + its cited
    sources) is appended under a `session_id`. This lets history survive a
    cleared/quota-exceeded browser localStorage and be read back from another
    device. The frontend still resends history per request; the server-side copy
    is a durable fallback, honored when a request carries a `session_id` but no
    inline history.

  - **Feedback:** thumbs up/down on an assistant answer (a KPI from
    project_summary.md), keyed by `(session_id, message_index)`.

The DB lives at `data/runtime/app.db` by default (override with `APP_DB_PATH`).
A single connection is shared across threads (`check_same_thread=False`) and
guarded by a lock, which is ample for this workload; WAL mode keeps reads from
blocking the occasional write.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "runtime" / "app.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    session_id TEXT    NOT NULL,
    idx        INTEGER NOT NULL,
    role       TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    sources    TEXT    NOT NULL DEFAULT '[]',
    created_at REAL    NOT NULL,
    PRIMARY KEY (session_id, idx)
);
CREATE TABLE IF NOT EXISTS feedback (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT    NOT NULL,
    message_index INTEGER NOT NULL,
    rating        TEXT    NOT NULL,
    question      TEXT    NOT NULL DEFAULT '',
    answer        TEXT    NOT NULL DEFAULT '',
    created_at    REAL    NOT NULL,
    UNIQUE (session_id, message_index)
);
"""


class Store:
    """Durable conversation history + feedback over a local SQLite file."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or os.getenv("APP_DB_PATH", DEFAULT_DB))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ── Sessions ────────────────────────────────────────────────────────
    def append_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        sources: list[dict] | None = None,
    ) -> None:
        """Append a (user, assistant) message pair to a session's history."""
        sources_json = json.dumps(sources or [], ensure_ascii=False)
        now = time.time()
        with self._lock:
            cur = self._conn.execute(
                "SELECT COALESCE(MAX(idx), -1) AS m FROM messages WHERE session_id=?",
                (session_id,),
            )
            base = cur.fetchone()["m"] + 1
            self._conn.executemany(
                "INSERT OR REPLACE INTO messages "
                "(session_id, idx, role, content, sources, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (session_id, base, "user", question, "[]", now),
                    (session_id, base + 1, "assistant", answer, sources_json, now),
                ],
            )
            self._conn.commit()

    def get_messages(self, session_id: str) -> list[dict]:
        """Return a session's messages in order: {role, content, sources}."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT role, content, sources FROM messages "
                "WHERE session_id=? ORDER BY idx",
                (session_id,),
            ).fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "role": r["role"],
                    "content": r["content"],
                    "sources": json.loads(r["sources"]),
                }
            )
        return out

    def get_history(self, session_id: str) -> list[dict]:
        """History as plain {role, content} (no sources) for LLM context."""
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self.get_messages(session_id)
        ]

    # ── Feedback ────────────────────────────────────────────────────────
    def record_feedback(
        self,
        session_id: str,
        message_index: int,
        rating: str,
        question: str = "",
        answer: str = "",
    ) -> None:
        """Upsert a thumbs rating for one assistant answer."""
        if rating not in ("up", "down"):
            raise ValueError("rating must be 'up' or 'down'")
        with self._lock:
            self._conn.execute(
                "INSERT INTO feedback "
                "(session_id, message_index, rating, question, answer, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id, message_index) DO UPDATE SET "
                "rating=excluded.rating, created_at=excluded.created_at",
                (session_id, message_index, rating, question, answer, time.time()),
            )
            self._conn.commit()

    def feedback_stats(self) -> dict:
        """Aggregate counts for the KPI: {up, down, total}."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT rating, COUNT(*) AS n FROM feedback GROUP BY rating"
            ).fetchall()
        counts = {r["rating"]: r["n"] for r in rows}
        up, down = counts.get("up", 0), counts.get("down", 0)
        return {"up": up, "down": down, "total": up + down}

    def close(self) -> None:
        with self._lock:
            self._conn.close()


if __name__ == "__main__":
    # Smoke test against a throwaway DB.
    import tempfile

    path = Path(tempfile.mkdtemp()) / "smoke.db"
    s = Store(path)
    s.append_turn("sess1", "What is patience?", "Sabr is...", [{"id": "2:153"}])
    s.append_turn("sess1", "And gratitude?", "Shukr is...")
    print("history:", s.get_history("sess1"))
    s.record_feedback("sess1", 1, "up", "What is patience?", "Sabr is...")
    s.record_feedback("sess1", 1, "down")  # overwrite
    print("stats:", s.feedback_stats())
