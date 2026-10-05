"""Pydantic models for GET /quran-passages/matrix and /quran-passages/pairs/{a}/{b}.

The shared-passage relation (change `add-shared-passages`, design D6). The matrix
has the similarity map's shape exactly, so its models are the similarity map's;
a cell's pair differs: it carries the number of matched words and, for each
verse, the passage's half-open CHARACTER span in that verse's `text_ar_tashkil`
(the displayed text, Basmala stripped) instead of a score. Every verse is built
through `verse_from_record`.
"""
from __future__ import annotations

from pydantic import BaseModel

from api.models.quran_similarity import QuranSimilarityMatrixResponse
from api.models.verse import Verse


class QuranPassagesMatrixResponse(QuranSimilarityMatrixResponse):
    """The passage map, sparse: all 114 surahs, the non-empty cells `a < b`, the totals.

    Same fields as the similarity map (`surahs`, `cells`, `total_pairs`,
    `max_pairs`); a cell's `pairs` counts the verse pairs sharing a passage.
    """


class PassagePair(BaseModel):
    """One shared passage: `u` in the lower-numbered surah, `v` in the other.

    `span_u` / `span_v` are `[start, end)` character offsets into `u` / `v`'s
    `text_ar_tashkil`, from the first aligned word's start to the last one's end.
    """

    u: Verse
    v: Verse
    words: int
    span_u: tuple[int, int]
    span_v: tuple[int, int]


class QuranPassagesCellResponse(BaseModel):
    """One cell's passages, normalised so `a < b`, matched words desc then (u, v).

    An empty cell answers `pairs: []` (and zero verses on each side), not an error.
    """

    a: int
    b: int
    surah_name_a: str = ""
    surah_name_b: str = ""
    verses_a: int
    verses_b: int
    pairs: list[PassagePair]
