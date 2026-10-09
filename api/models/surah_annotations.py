"""Pydantic models for GET /surah/{number}/annotations — the reading page's closeness cues.

Per annotated ayah of one surah: the other members of its intra-surah group
(`surah_similarity.json`), and its cross-surah partners (`quran_close_verses.json`)
in ONE list `cross`, whatever relation produced each pair (change
`unify-cross-closeness-cue`, D8 — the `whole` / `passage` split is gone).
Every partner verse the bubble lists travels once in `verses`, built through
`verse_from_record`, so its `text_ar_tashkil` is Basmala-stripped like every
other verse the API emits — which is the text the spans index.
"""
from __future__ import annotations

from pydantic import BaseModel

from api.models.verse import Verse


class AnnotationPartner(BaseModel):
    """One cross-surah partner of an ayah, as seen from that ayah.

    `spans_self` lists half-open `[start, end)` character spans in THIS ayah's
    `text_ar_tashkil`, `spans_other` in the partner's — one per run of coloured
    words, ascending; `words` is the common part's matched content-word count.
    The three are null together when the pair has no common part (never for a
    passage) — such a pair colours the orange marker alone.
    """

    ref: str                          # "s:a"
    score: float
    words: int | None = None
    spans_self: list[tuple[int, int]] | None = None
    spans_other: list[tuple[int, int]] | None = None


class AnnotatedAyah(BaseModel):
    """One ayah carrying at least one cue."""

    ayah: int
    group: list[int]                  # other members of its group(s), mushaf order
    cross: list[AnnotationPartner]    # every cross pair: score desc, ties mushaf order


class SurahAnnotationsResponse(BaseModel):
    """A surah's annotated ayahs (ayah ascending) and every partner verse, once."""

    surah: int
    ayahs: list[AnnotatedAyah]
    verses: dict[str, Verse]          # keyed "s:a"
