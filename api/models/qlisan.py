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
    """A root sibling (naẓīr): another occurrence sharing the word's root.

    Lemma-scoped: `lemma`/`lemma_display` tag each entry so the UI can group the
    strip by lemma (never mixing homographic senses under one root).
    """

    ref: str  # "surah:ayah:word"
    word_uthmani: str = ""
    lemma: str | None = None
    lemma_display: str | None = None


class SarfiFeature(BaseModel):
    """One morphology feature row, fully Arabic (label + value), never a raw code."""

    label_ar: str
    value_ar: str


class SarfiSegment(BaseModel):
    """One morphological segment: its vocalized surface text + Arabic type label.

    `text` is the real segment form (e.g. «الـ», «رَحِيم», «وا»), re-vocalized from the
    aligned chakl surface; `type_ar` is the secondary type (بادئة/جذع/لاحقة). Order is
    reading order (prefix → stem → suffix, i.e. right → left)."""

    text: str
    type_ar: str


class Mizan(BaseModel):
    """الميزان الصرفي — the root projected onto ف-ع-ل, derived deterministically.

    `verified` mirrors the level badge: True ⇒ exact projection («معطى محقّق»);
    False ⇒ hollow/geminate/irregular surface, shown as an heuristic «اجتهادي» hint
    outside the badge. `bab` is the canonical verb-form pattern (فَعَلَ/فَعَّلَ/…) for
    verbs, else None.
    """

    available: bool = False
    wazn: str | None = None
    verified: bool = False
    bab: str | None = None


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
    pos: str = ""  # raw QAC code, kept as data (not rendered); pos_ar is the display source
    pos_ar: str = ""
    features: list[SarfiFeature] = []  # ordered Arabic {label_ar, value_ar}
    segments: list[SarfiSegment] = []  # per-segment vocalized text + Arabic type
    mizan: Mizan = Mizan()  # الميزان الصرفي (root projected onto ف-ع-ل)
    is_proper_noun: bool = False
    nazair: list[Nazair] = []


class NahwiLevel(BaseModel):
    """نحوي (syntax) — deterministic, from the dependency treebank.

    `iraab_ar` is the composed «الموقع الإعرابي» (relation function [+ case word]);
    `marker_ar` is the derived العلامة (الأصل) hint, present only where reliable.
    `role_ar` is kept for shape-compat but no longer populated. Raw `relation`/
    `relation_ar` stay in the payload as data (not rendered).
    """

    available: bool
    role_ar: str | None = None  # deprecated: no longer populated (kept for shape-compat)
    relation: str | None = None  # raw QAC code, kept as data (not rendered)
    relation_ar: str | None = None  # raw source label, kept as data (not rendered)
    iraab_ar: str | None = None
    marker_ar: str | None = None
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
