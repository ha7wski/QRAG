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


class LetterMeaningPosition(BaseModel):
    """One position of the letter in a word: أول (initial), وسط, آخر."""

    position: str                      # initial | medial | final
    divine_name: str | None = None     # null on a substitute-word position
    sense: str
    examples: list[str]
    origin: str                        # author | author_inferred | rule | substitute_word


class LetterMeaningSource(BaseModel):
    """One authority's reading; the authority's name is a frontend label."""

    key: str                           # AQ | IS | HA | BL | NJ | SM
    reading: str


class LetterMeaningDimension(BaseModel):
    letter: str
    sense: str


class LetterMeaning(BaseModel):
    """The letter's entry of the «معاني الحروف» sheet, Arabic fields only (تأويلي)."""

    letter: str
    name: str
    series: str                        # abu_qaisar | generalise
    core_sense: str
    drawing: str
    structure: str
    positions: list[LetterMeaningPosition]
    sources: list[LetterMeaningSource]
    dimensions: list[LetterMeaningDimension] = []


class RootLetterResponse(BaseModel):
    letter: str
    count: int
    readings_available: bool
    roots: list[RootEntry]
    maani: LetterMeaning | None = None  # null: the sheet has no entry or failed to load
