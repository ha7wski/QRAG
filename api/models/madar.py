"""Pydantic models for the Madar (sourced lexical reading) endpoint.

The response deliberately keeps three epistemic layers apart:
  - `maqayis`         → CITED (Ibn Fāris' aṣl, with source + edition),
  - `occurrences`     → PROOF (the root's Quranic occurrences),
  - `madar_synthesis` → GENERATED (optional LLM pivot, flagged + disclaimed).
"""
from __future__ import annotations

from pydantic import BaseModel


class MadarRequest(BaseModel):
    word: str
    # Arabic-only feature; any `lang` sent by an old client is ignored.


class MaqayisCitation(BaseModel):
    """Ibn Fāris' aṣl — verified citation, never a paraphrase."""

    asl_text: list[str] = []          # [] when asl_status == "no_asl"
    asl_count: int = 0
    asl_status: str                    # "has_asl" | "no_asl" | "parse_uncertain"
    source: str
    edition: str


class Occurrence(BaseModel):
    surface: str
    surah: int | None = None
    ayah: int | None = None
    context: str = ""                  # the verse text (short grounding context)


class MadarResponse(BaseModel):
    word: str
    root: str | None
    root_source: str | None = None     # "qac" | "fallback" | None
    maqayis: MaqayisCitation | None = None          # CITED
    occurrences: list[Occurrence] = []              # PROOF (sample)
    occurrences_count: int = 0                       # true total
    verse_ids: list[str] = []                        # all refs "s:a" (proof)
    madar_synthesis: str | None = None               # GENERATED (or null)
    synthesis_source: str = "qwen2.5:7b-local"
    synthesis_disclaimer: str
    convergence_note: str | None = None              # optional lisan bridge
    message: str | None = None
