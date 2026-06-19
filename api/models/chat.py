"""Pydantic models for the chat endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field

from api.models.verse import Verse


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
