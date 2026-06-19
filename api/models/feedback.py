"""Pydantic models for answer feedback (👍/👎)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    # Index of the assistant message within the session this rates.
    message_index: int = Field(..., ge=0)
    rating: Literal["up", "down"]
    # Optional context, stored for later review of low-rated answers.
    question: str = ""
    answer: str = ""


class FeedbackResponse(BaseModel):
    ok: bool = True
    stats: dict  # {"up": int, "down": int, "total": int}
