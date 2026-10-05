"""Pydantic model for GET /verse/{surah}/{ayah}/similar — close verses in the other surahs.

One verse and its ranked close verses across the rest of the Quran. A neighbour
is the same `SimilarNeighbour` the intra-surah anchor view uses: its `Verse`
already carries `surah_number` and `surah_name_ar`, which is all a card needs
once it leaves the anchor's surah. Every verse is built through
`verse_from_record`, so it carries `text_ar_tashkil` with the Basmala stripped
like every other verse the API emits.
"""
from __future__ import annotations

from pydantic import BaseModel

from api.models.surah_similarity import SimilarNeighbour
from api.models.verse import Verse


class VerseQuranSimilarityResponse(BaseModel):
    """The anchor view across surahs: one verse and its close verses, in dataset (score) order.

    `unscored: true` with no neighbours means the anchor carries no content word
    and was not compared; `unscored: false` with no neighbours means it was
    compared and nothing in another surah passed both gates.
    """

    surah_number: int
    surah_name_ar: str = ""
    ayah_count: int
    anchor: Verse
    unscored: bool
    neighbours: list[SimilarNeighbour]


# ── the surah × surah map: GET /quran-similarity/matrix, /pairs/{a}/{b} ────


class SurahName(BaseModel):
    """One surah of an axis: its number and Arabic name."""

    number: int
    name_ar: str = ""


class SimilarityCell(BaseModel):
    """One non-empty cell `(a, b)`, `a < b`: its close verse pairs and the verses on each side."""

    a: int
    b: int
    pairs: int
    verses_a: int                     # distinct verses of surah `a` taking part
    verses_b: int                     # distinct verses of surah `b` taking part


class QuranSimilarityMatrixResponse(BaseModel):
    """The whole map, sparse: all 114 surahs to name, and only the non-empty cells.

    The client draws the mirror `(b, a)` and the empty background itself.
    `total_pairs` equals the sum of `cells[].pairs`; `max_pairs` is the largest.
    """

    surahs: list[SurahName]           # all 114, mushaf order
    cells: list[SimilarityCell]       # a < b, ordered by (a, b)
    total_pairs: int
    max_pairs: int


class SimilarPair(BaseModel):
    """One close verse pair of a cell: `u` in the lower-numbered surah, `v` in the other."""

    u: Verse
    v: Verse
    score: float
    roots: list[str]


class QuranSimilarityCellResponse(BaseModel):
    """One cell's pairs, normalised so `a < b`, in score order then (u, v).

    An empty cell answers `pairs: []` (and zero verses on each side), not an error.
    """

    a: int
    b: int
    surah_name_a: str = ""
    surah_name_b: str = ""
    verses_a: int
    verses_b: int
    pairs: list[SimilarPair]
