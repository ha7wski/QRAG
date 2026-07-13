"""Pydantic models for the Lisan Analysis (letter-symbolism) endpoint."""
from __future__ import annotations

from pydantic import BaseModel


class LisanRequest(BaseModel):
    word: str
    lang: str = "ar"          # "ar" | "fr" | "en"


class LisanLetter(BaseModel):
    letter: str
    name: str
    makhraj: str
    sifat: list[str]
    meaning: str
    keywords: list[str]
    ibn_jinni_note: str
    confidence: str


class SequentialItem(BaseModel):
    index: int
    letter: str
    meaning: str


class IshtiqaqItem(BaseModel):
    form: str
    gloss: str


class LisanResponse(BaseModel):
    word: str
    root: str | None
    root_source: str | None = None      # "qac" | "fallback" | None
    letters: list[LisanLetter] = []
    sequential_reading: list[SequentialItem] = []
    synthesis: str = ""
    ishtiqaq_akbar: list[IshtiqaqItem] = []
    disclaimer: str
    sources: dict[str, str] = {}
    message: str | None = None          # set when root could not be resolved
