"""Pydantic models for the unified cross-surah relation «close verses».

GET /verse/{surah}/{ayah}/similar (one verse and its close verses across the
rest of the Quran), GET /quran-similarity/matrix and
GET /quran-similarity/pairs/{a}/{b} (the surah × surah map) — change
`unify-close-verses`, design D7. A neighbour's `Verse` already carries
`surah_number` and `surah_name_ar`, which is all a card needs once it leaves
the anchor's surah. Every verse is built through `verse_from_record`, so it
carries `text_ar_tashkil` with the Basmala stripped like every other verse the
API emits — and that displayed text is what the common part's character spans
index into.
"""
from __future__ import annotations

from pydantic import BaseModel

from api.models.verse import Verse


class QuranNeighbour(BaseModel):
    """One close verse of the anchor in another surah.

    `words` is the common part's matched word count and `span` its half-open
    `[start, end)` character span in THIS verse's `text_ar_tashkil` (the
    neighbour's, not the anchor's: the anchor's span differs per neighbour).
    Both are null together when the pair has no common part. A separate model
    from the intra-surah `SimilarNeighbour`, which has no common part.
    """

    verse: Verse
    score: float
    roots: list[str]
    words: int | None = None
    span: tuple[int, int] | None = None


class VerseQuranSimilarityResponse(BaseModel):
    """The anchor view across surahs: EVERY pair holding the verse, score desc then ref.

    Not capped at K: the list is exactly the map's pairs holding this verse.
    `unscored: true` with no neighbours means the anchor carries no content word
    and was not compared; `unscored: false` with no neighbours means no verse of
    another surah is close to it or shares a passage with it.
    """

    surah_number: int
    surah_name_ar: str = ""
    ayah_count: int
    anchor: Verse
    unscored: bool
    neighbours: list[QuranNeighbour]


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
    """One close verse pair of a cell: `u` in the lower-numbered surah, `v` in the other.

    `words`, `span_u`, `span_v` are the common part — its matched word count and
    its half-open `[start, end)` character span in `u`'s and `v`'s
    `text_ar_tashkil` — and are null together when the pair has none.
    """

    u: Verse
    v: Verse
    score: float
    roots: list[str]
    words: int | None = None
    span_u: tuple[int, int] | None = None
    span_v: tuple[int, int] | None = None


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
