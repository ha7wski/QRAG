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
CREATE TABLE IF NOT EXISTS tahlil_cache (
    ref             TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    kb_version      TEXT NOT NULL,
    letters_version TEXT NOT NULL,
    model_id        TEXT NOT NULL,
    payload         TEXT NOT NULL,
    created_at      REAL NOT NULL,
    PRIMARY KEY (ref, prompt_version, kb_version, letters_version, model_id)
);
CREATE TABLE IF NOT EXISTS tahlil_review (
    ref             TEXT    NOT NULL,
    prompt_version  TEXT    NOT NULL,
    kb_version      TEXT    NOT NULL,
    letters_version TEXT    NOT NULL,
    model_id        TEXT    NOT NULL,
    generation      INTEGER NOT NULL,
    reviewer        TEXT    NOT NULL DEFAULT '',
    note            TEXT    NOT NULL DEFAULT '',
    reviewed_at     REAL    NOT NULL,
    PRIMARY KEY (ref, prompt_version, kb_version, letters_version, model_id, generation)
);
"""

# The columns `tahlil_review` must have. A pre-release database still carrying the
# ref-only version of that table is dropped and recreated rather than migrated: those rows
# attest a rendering nobody can identify any more (see `mark_tahlil_reviewed`), and the
# honest direction is to lose a review — which only over-warns — rather than to keep one
# that may silently mark generated prose as read. Only this table is ever touched.
_TAHLIL_REVIEW_COLUMNS = (
    "ref", "prompt_version", "kb_version", "letters_version", "model_id", "generation",
    "reviewer", "note", "reviewed_at",
)


class Store:
    """Durable conversation history + feedback over a local SQLite file."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or os.getenv("APP_DB_PATH", DEFAULT_DB))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._drop_stale_tahlil_review()
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def _drop_stale_tahlil_review(self) -> None:
        """Drop a pre-release `tahlil_review` whose key is not the current one.

        `CREATE TABLE IF NOT EXISTS` is a no-op against an existing table, so a local
        database carrying the ref-only review table would keep it and fail every insert.
        SQLite cannot ALTER a primary key, and the old rows are unmigratable in principle,
        not just in practice: they record «reviewed» against a rendering whose prompt, KB,
        letters and model versions were never stored, so nothing can say which page a
        reviewer actually read. Touches `tahlil_review` and nothing else.
        """
        cols = {r["name"] for r in
                self._conn.execute("PRAGMA table_info(tahlil_review)").fetchall()}
        if cols and cols != set(_TAHLIL_REVIEW_COLUMNS):
            self._conn.execute("DROP TABLE tahlil_review")

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

    # ── Tahlil analysis cache ───────────────────────────────────────────
    # Keyed on the FULL five-tuple (ref, prompt_version, kb_version,
    # letters_version, model_id) — it is the primary key of the table AND the
    # whole WHERE clause of the read. That is deliberate: invalidation must
    # happen *by construction*, not by anyone remembering to purge. Edit the
    # prompt, bump a KB, re-transcribe the letters dataset or switch models, and
    # the old row simply stops being addressable. Drop any one component from
    # either statement and a stale analysis is served under a new version, with
    # its badges and citations still attached and nothing to detect it.
    def get_tahlil(
        self,
        ref: str,
        prompt_version: str,
        kb_version: str,
        letters_version: str,
        model_id: str,
    ) -> dict | None:
        """The cached Tahlil analysis for this exact version tuple, else None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM tahlil_cache WHERE ref=? AND prompt_version=? "
                "AND kb_version=? AND letters_version=? AND model_id=?",
                (ref, prompt_version, kb_version, letters_version, model_id),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["payload"])

    def put_tahlil(
        self,
        ref: str,
        prompt_version: str,
        kb_version: str,
        letters_version: str,
        model_id: str,
        payload: dict,
    ) -> None:
        """Store one analysis under its version tuple (replacing an equal key)."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO tahlil_cache "
                "(ref, prompt_version, kb_version, letters_version, model_id, "
                "payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    ref,
                    prompt_version,
                    kb_version,
                    letters_version,
                    model_id,
                    json.dumps(payload, ensure_ascii=False),
                    time.time(),
                ),
            )
            self._conn.commit()

    # ── Tahlil review state ─────────────────────────────────────────────
    # Keyed on the ref AND the rendering: the same five-tuple the analysis is
    # cached under, plus whether prose was generated at all. A review attests
    # «a human read THIS page», and keying it on the ref alone silently
    # transferred that attestation to every later rendering of the word — approve
    # a deterministic-only page, switch generation on, and brand-new prose no one
    # has ever read comes back `reviewed=True`, dropping the «غير مُحقَّق»
    # mention that design decision 3b makes mandatory on un-reviewed generated
    # blocks. `generation` is part of the key because the five-tuple alone cannot
    # tell a deterministic page from a prose page produced by the same model under
    # the same versions, and those are two different things to have read.
    #
    # It stays strictly additive to rendering: nothing here can prevent a page
    # from being served (see `tahlil_service._reviewed`).
    def mark_tahlil_reviewed(
        self,
        ref: str,
        prompt_version: str,
        kb_version: str,
        letters_version: str,
        model_id: str,
        generation_enabled: bool,
        reviewer: str = "",
        note: str = "",
    ) -> dict:
        """Mark one *rendering* of one word reviewed (upsert); returns the stored row."""
        now = time.time()
        generation = int(bool(generation_enabled))
        with self._lock:
            self._conn.execute(
                "INSERT INTO tahlil_review (ref, prompt_version, kb_version, "
                "letters_version, model_id, generation, reviewer, note, reviewed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(ref, prompt_version, kb_version, letters_version, model_id, "
                "generation) DO UPDATE SET reviewer=excluded.reviewer, "
                "note=excluded.note, reviewed_at=excluded.reviewed_at",
                (ref, prompt_version, kb_version, letters_version, model_id, generation,
                 reviewer, note, now),
            )
            self._conn.commit()
        return {"ref": ref, "reviewer": reviewer, "note": note, "reviewed_at": now}

    def get_tahlil_review(
        self,
        ref: str,
        prompt_version: str,
        kb_version: str,
        letters_version: str,
        model_id: str,
        generation_enabled: bool,
    ) -> dict | None:
        """The review row for this exact rendering, or None when it was never reviewed."""
        with self._lock:
            row = self._conn.execute(
                "SELECT ref, reviewer, note, reviewed_at FROM tahlil_review "
                "WHERE ref=? AND prompt_version=? AND kb_version=? AND letters_version=? "
                "AND model_id=? AND generation=?",
                (ref, prompt_version, kb_version, letters_version, model_id,
                 int(bool(generation_enabled))),
            ).fetchone()
        if row is None:
            return None
        return {
            "ref": row["ref"],
            "reviewer": row["reviewer"],
            "note": row["note"],
            "reviewed_at": row["reviewed_at"],
        }

    def tahlil_reviewed(
        self,
        ref: str,
        prompt_version: str,
        kb_version: str,
        letters_version: str,
        model_id: str,
        generation_enabled: bool,
    ) -> bool:
        """False until an expert marks THIS rendering — the default the UI must warn about."""
        return self.get_tahlil_review(ref, prompt_version, kb_version, letters_version,
                                      model_id, generation_enabled) is not None

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
