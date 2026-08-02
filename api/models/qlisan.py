"""Pydantic models for the QLisan per-word analysis endpoints.

The `/qlisan/word` fiche keeps four levels in a fixed order — صوتي → صرفي → نحوي →
دلالي — each an independently-labelled sub-model carrying its own `available` flag
(mirrors Madār's field-per-layer shape). صرفي + نحوي are served 100%
deterministically from the parsed on-disk treebank (no LLM); صوتي + دلالي are stubs
in this increment (`available:false`, explanatory message).

`/qlisan/verse/{surah}/{ayah}` returns the vocalized verse plus QAC-aligned token
boundaries so the UI's token index equals the QAC `word_id` by construction.
"""
from __future__ import annotations

from pydantic import BaseModel


class QlisanWordRequest(BaseModel):
    surah: int
    ayah: int
    word: int  # 1-based QAC word_id


class Nazair(BaseModel):
    """A root sibling (naẓīr): another occurrence sharing the word's root."""

    ref: str  # "surah:ayah:word"
    word_uthmani: str = ""


class SawtiLevel(BaseModel):
    """صوتي (phonetic) — stub in this increment."""

    available: bool = False
    message: str


class SarfiLevel(BaseModel):
    """صرفي (morphology) — deterministic, from the QAC word index."""

    available: bool
    root: str | None = None
    root_display: str | None = None
    lemma: str | None = None
    lemma_display: str | None = None
    pos: str = ""
    pos_ar: str = ""
    features: dict = {}
    segments: list[str] = []
    is_proper_noun: bool = False
    nazair: list[Nazair] = []


class NahwiLevel(BaseModel):
    """نحوي (syntax) — deterministic, from the dependency treebank."""

    available: bool
    role_ar: str | None = None
    relation: str | None = None
    relation_ar: str | None = None
    head_ref: str | None = None
    message: str | None = None


class DalaliLevel(BaseModel):
    """دلالي (semantic) — stub in this increment."""

    available: bool = False
    message: str


class QlisanWordResponse(BaseModel):
    ref: str  # "surah:ayah:word"
    surah: int
    ayah: int
    word: int
    word_uthmani: str = ""
    word_imlaai: str = ""
    levels_order: list[str] = ["sawti", "sarfi", "nahwi", "dalali"]
    sawti: SawtiLevel
    sarfi: SarfiLevel
    nahwi: NahwiLevel
    dalali: DalaliLevel


class QlisanToken(BaseModel):
    """One selectable word token, aligned to a char span in the vocalized verse."""

    word: int  # 1-based QAC word_id
    uthmani: str = ""
    imlaai: str = ""
    char_start: int  # offset into the verse `text`
    char_end: int    # exclusive
    aligned: bool     # false ⇒ span is a best-effort fallback


class QlisanVerseResponse(BaseModel):
    surah: int
    ayah: int
    surah_name_ar: str = ""
    text: str                       # vocalized chakl verse (rendered as-is, RTL)
    tokens: list[QlisanToken] = []
