"""Pydantic models for the Fāṣila (rhyme-letter) endpoint.

The response carries both orderings the page needs, because they are different and
neither can be derived from the other client-side without replaying the sūra:

  - `counts`            → frequency order (descending), drives the bar chart & table,
  - `first_appearance`  → order of first occurrence, drives the line chart's Y axis
                          (bottom to top).

Percentages are computed over `analysed_ayahs` — muqaṭṭaʿāt āyāt are excluded from the
denominator. Those āyāt still appear in `ayahs`, flagged and with `fasila = None`, so
the client can account for them without re-deriving the exclusion list.

The overview models below serve the cross-sūra comparison. Two shape decisions:

  - **the aggregates travel pre-computed** (mean, mono-fāṣila count, maximum, buckets)
    rather than being derived client-side, so the rounding rule lives in one place and
    the figures are assertable in a backend test instead of only through the DOM;
  - **`fawasil` cannot be dropped as redundant.** `distinct_count` is a number and
    `dominant` names a single letter; neither can produce the union of letters covering
    a *selection* of sūras, which is what the comparison page reports under its list.
"""
from __future__ import annotations

from pydantic import BaseModel


class FassilaAyah(BaseModel):
    """One āya: its fāṣila, and the final word it was read from."""

    ayah: int
    fasila: str | None          # None for muqaṭṭaʿāt āyāt
    word: str                   # final word, Uthmānī rasm (vocalized)
    word_ref: str               # "surah:ayah:word" — aligned with the QAC spine
    is_muqattaat: bool


class FassilaCount(BaseModel):
    """One distinct fāṣila and its share of the analysed āyāt."""

    letter: str
    count: int
    percentage: float           # over analysed āyāt, 1 decimal


class FassilaDominant(BaseModel):
    letter: str
    count: int
    percentage: float


class FassilaResponse(BaseModel):
    surah: int
    surah_name: str
    total_ayahs: int
    analysed_ayahs: int
    excluded_ayahs: int
    distinct_count: int
    dominant: FassilaDominant | None
    counts: list[FassilaCount]          # descending frequency
    first_appearance: list[str]         # order of first occurrence
    ayahs: list[FassilaAyah]


class FassilaSurahSummary(BaseModel):
    """One sūra as the cross-sūra comparison reads it — no per-āya detail."""

    surah: int
    surah_name: str
    total_ayahs: int
    analysed_ayahs: int
    excluded_ayahs: int
    distinct_count: int
    fawasil: list[str]          # distinct letters, same order as `FassilaResponse.counts`
    dominant: FassilaDominant | None


class FassilaBucket(BaseModel):
    """How many sūras carry a given number of distinct fawāṣil.

    Buckets are contiguous from the observed minimum to the observed maximum — a value
    no sūra attains still ships with `surah_count = 0`, so the client plots a
    distribution rather than reconstructing the missing steps.
    """

    distinct: int
    surah_count: int
    percentage: float           # of the 114 sūras, 1 decimal


class FassilaOverviewResponse(BaseModel):
    """The whole muṣḥaf read at once: 114 summaries plus the corpus aggregates."""

    surah_count: int
    mean_distinct: float            # one decimal, same convention as the percentages
    mono_fasila_count: int
    max_distinct: int
    max_distinct_surahs: list[int]  # sūra number(s) attaining `max_distinct`
    buckets: list[FassilaBucket]
    surahs: list[FassilaSurahSummary]
