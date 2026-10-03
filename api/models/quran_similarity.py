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
