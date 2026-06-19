"""Session endpoint: read back server-persisted chat history (multi-device)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from api.models.verse import Verse

router = APIRouter(tags=["sessions"])


@router.get("/sessions/{session_id}")
def get_session(session_id: str, request: Request) -> dict:
    """Return a session's stored messages (assistant turns include sources)."""
    store = request.app.state.store
    messages = store.get_messages(session_id)
    # Re-validate stored source dicts through the Verse model for a stable shape.
    for m in messages:
        if m.get("sources"):
            m["sources"] = [Verse(**s).model_dump() for s in m["sources"]]
    return {"session_id": session_id, "messages": messages}
