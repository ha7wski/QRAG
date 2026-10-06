"""Pydantic models for «فهرس الجذور», the browsable root index.

Every figure on a root entry is `VerseLookup.root_forms` read back — the same
computation «الكلمة في الآيات» and «تحليل اللسان» show — so the three pages
cannot disagree on a root. `reading` is the project's mechanical assembly of the
root's three Islambouli rows with no signed choice; the label that says so lives
in the frontend (`lib/strings.ts`), shared with `/lexical`, and is not sent here.
"""
from __future__ import annotations

from pydantic import BaseModel

from api.models.lisan import LetterIdentity


class RootLetter(BaseModel):
    """One letter group: its label and how many roots it holds (zero allowed)."""

    letter: str
    count: int


class RootLettersResponse(BaseModel):
    total: int
    letters: list[RootLetter]          # always 28, in hijāʾī order


class RootSurah(BaseModel):
    number: int
    name_ar: str


class RootEntry(BaseModel):
    """One root: its DISTINCT counts, its āya refs, its sūras and its reading.

    Exactly one of `reading` / `reading_refusal` is set, unless the readings are
    unavailable for the whole letter (a frozen table failed its lock), in which
    case both are null and the response says so once.
    """

    root: str
    words: int                         # مواضع, after the grammatical-tool filter
    ayat: int
    surahs: int
    verse_ids: list[str]               # "s:a", canonical order
    surah_list: list[RootSurah]
    forms: list[str]                   # النظائر: distinct written forms, `root_forms` order
    reading: str | None = None
    reading_refusal: str | None = None
    letters: list[LetterIdentity] = []  # the /lexical letter cards, gloss included


class RootLetterResponse(BaseModel):
    letter: str
    count: int
    readings_available: bool
    roots: list[RootEntry]
