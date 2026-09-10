"""Pydantic models for the chat endpoint.

Request only: `POST /chat/stream` answers as Server-Sent Events, whose payloads
are framed by the router, so there is no response model to declare. `ChatResponse`
went with the non-streaming `POST /chat` it existed for.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str                     # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    session_id: str | None = None
    # Optional retrieval filters: surah_number (int), period (str), juz (int).
    filters: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    sources: list[Verse]
    session_id: str
