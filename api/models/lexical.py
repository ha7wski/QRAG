"""Pydantic models for the lexical (root analysis) endpoint."""
from __future__ import annotations

from pydantic import BaseModel

from api.models.verse import Verse


class LexicalRequest(BaseModel):
    word: str
    language: str = "ar"          # "ar" | "fr" | "en"


class LexicalResponse(BaseModel):
    word: str
    root: str
    forms: list[str]
    occurrences_count: int
    analysis: str
    key_verses: list[Verse]
    found: bool = True
