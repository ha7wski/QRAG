"""Chat endpoints: non-streaming JSON and streaming SSE."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.models.chat import ChatRequest, ChatResponse
from api.models.verse import verse_from_record

router = APIRouter(tags=["chat"])


def _split_messages(req: ChatRequest, store=None) -> tuple[str, list[dict]]:
    """Return (question, history). The last user message is the question.

    History comes from the inline `messages`. When the client sends only the
    new question (no prior turns) but a known `session_id`, the server-persisted
    history is used as a fallback — this is what makes `session_id` honored
    across devices / after a localStorage wipe.
    """
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")
    last = req.messages[-1]
    if last.role != "user":
        raise HTTPException(status_code=400, detail="last message must be from 'user'")
    history = [{"role": m.role, "content": m.content} for m in req.messages[:-1]]
    if not history and req.session_id and store is not None:
        history = store.get_history(req.session_id)
    return last.content, history


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """Run the RAG pipeline and return the full answer with sources."""
    engine = request.app.state.engine
    store = request.app.state.store
    question, history = _split_messages(req, store)
    session_id = req.session_id or str(uuid.uuid4())
    result = engine.chat(question, filters=req.filters or None, history=history)
    sources = [verse_from_record(s) for s in result["sources"]]
    store.append_turn(
        session_id, question, result["answer"], [s.model_dump() for s in sources]
    )
    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        session_id=session_id,
    )


@router.post("/chat/stream")
def chat_stream(req: ChatRequest, request: Request) -> StreamingResponse:
    """Stream the answer token-by-token as Server-Sent Events.

    Event payloads (JSON in each `data:` line):
      {"type": "token",   "content": "..."}     repeated
      {"type": "sources", "sources": [Verse]}   once, after tokens
      {"type": "done",    "session_id": "..."}  final
    """
    engine = request.app.state.engine
    store = request.app.state.store
    question, history = _split_messages(req, store)
    session_id = req.session_id or str(uuid.uuid4())

    def event_stream():
        answer_parts: list[str] = []
        for chunk in engine.stream_chat(
            question, filters=req.filters or None, history=history
        ):
            answer_parts.append(chunk)
            yield _sse({"type": "token", "content": chunk})
        sources = [verse_from_record(s) for s in engine.last_sources]
        yield _sse(
            {"type": "sources", "sources": [s.model_dump() for s in sources]}
        )
        # Persist the completed turn so history survives a localStorage wipe.
        store.append_turn(
            session_id, question, "".join(answer_parts),
            [s.model_dump() for s in sources],
        )
        yield _sse({"type": "done", "session_id": session_id})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
