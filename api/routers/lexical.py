"""Lexical endpoint: linguistic analysis of an Arabic root (feature F2)."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.models.lexical import LexicalRequest, LexicalResponse
from api.models.verse import verse_from_record

router = APIRouter(tags=["lexical"])


@router.post("/lexical", response_model=LexicalResponse)
def lexical(req: LexicalRequest, request: Request) -> LexicalResponse:
    """Resolve a word's root and return a full linguistic analysis + verses."""
    analyzer = request.app.state.lexical_analyzer
    if not req.word.strip():
        raise HTTPException(status_code=400, detail="word must not be empty")
    out = analyzer.analyze(req.word, language=req.language)
    return LexicalResponse(
        word=out["word"],
        root=out["root"],
        forms=out["forms"],
        occurrences_count=out["occurrences_count"],
        analysis=out["analysis"],
        key_verses=[verse_from_record(v) for v in out["key_verses"]],
        found=out["found"],
    )


@router.post("/lexical/stream")
def lexical_stream(req: LexicalRequest, request: Request) -> StreamingResponse:
    """Stream the analysis as SSE; metadata and verses follow at the end."""
    analyzer = request.app.state.lexical_analyzer
    if not req.word.strip():
        raise HTTPException(status_code=400, detail="word must not be empty")

    def event_stream():
        for chunk in analyzer.stream_analyze(req.word, language=req.language):
            yield _sse({"type": "token", "content": chunk})
        result = analyzer.last_result
        verses = [verse_from_record(v).model_dump() for v in result["verses"]]
        yield _sse(
            {
                "type": "meta",
                "word": req.word,
                "root": result["root"],
                "forms": result["forms"],
                "occurrences_count": result["occurrences_count"],
                "key_verses": verses,
                "found": result["occurrences_count"] > 0,
            }
        )
        yield _sse({"type": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
