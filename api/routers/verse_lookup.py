"""Verse Lookup endpoint: exhaustive, vocalized root lookup (no LLM).

Isolated from the existing routers. Resolves an Arabic word to its root via the
shared morphology index and returns every verse containing that root or any of
its derivatives, with full diacritics for display.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api.models.verse_lookup import VerseLookupRequest, VerseLookupResponse

router = APIRouter(tags=["verse-lookup"])


@router.post("/verse-lookup", response_model=VerseLookupResponse)
def verse_lookup(req: VerseLookupRequest, request: Request) -> VerseLookupResponse:
    """Return every vocalized verse whose root matches the input word."""
    if not req.word.strip():
        raise HTTPException(status_code=400, detail="word must not be empty")
    return VerseLookupResponse(**request.app.state.verse_lookup.lookup(req.word.strip()))
