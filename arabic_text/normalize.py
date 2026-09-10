"""
normalize.py — the three Arabic normalizers, side by side.

They lived in three packages, so nothing ever put the choice in front of the
reader. See the package docstring for the table that does.
"""
from __future__ import annotations

import unicodedata

from arabic_text.marks import (
    HARAKAT_TABLE,
    QURANIC_MARKS_TABLE,
    TATWEEL,
    strip_harakat,
)

try:
    import pyarabic.araby as araby

    _HAS_PYARABIC = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_PYARABIC = False


def backend() -> str:
    """Which implementation `normalize_text` is using, for a pipeline log line.

    Public so the ingestion stage can report it without reaching for a private
    flag across a package boundary. The two paths are equivalent on this corpus;
    the name is reported so a surprise is visible rather than silent.
    """
    return "pyarabic" if _HAS_PYARABIC else "internal fallback"


# Hamza-carrier folding. The bare hamza `ء` (U+0621) is deliberately ABSENT —
# it is kept as-is, never deleted. That single omission is the whole difference
# between a root index that works and one that merges distinct roots.
_HAMZA_FOLD = {
    "أ": "ا",  # alif + hamza above  → ا
    "إ": "ا",  # alif + hamza below  → ا
    "آ": "ا",  # alif madda          → ا
    "ٱ": "ا",  # alif wasla          → ا
    "ؤ": "و",  # waw + hamza         → و
    "ئ": "ي",  # ya + hamza          → ي
}
_HAMZA_TABLE = {ord(k): v for k, v in _HAMZA_FOLD.items()}

# Extra folds that help lexical matching (not roots): alif-maqsura, ta-marbuta.
_MATCH_FOLD = {ord("ى"): "ي", ord("ة"): "ه"}


def normalize_root(text: str) -> str:
    """Root-safe normalization. Folds hamza carriers, NEVER deletes a hamza.

    The ONLY normalization used for QAC root keys, applied identically on the
    index side and the query side, so a typed word always folds to the key that
    was stored.

    Do NOT use this for free text: it leaves ة and ى alone, which lexical
    matching needs folded.

    Verified over all 1651 distinct QAC roots: this fold yields 1651 distinct
    keys — zero collisions. See `tests/test_root_normalize.py`.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(HARAKAT_TABLE)   # harakat / dagger alif
    text = text.replace(TATWEEL, "")
    text = text.translate(_HAMZA_TABLE)    # fold carriers, delete nothing
    return unicodedata.normalize("NFC", text).strip()


def normalize_search(text: str) -> str:
    """Hamza-safe normalization for BM25 indexing and query tokenization.

    Built on `normalize_root`, then two things it adds: waqf marks are dropped
    (they otherwise survive as standalone noise tokens), and ى → ي, ة → ه are
    folded for matching.

    Applied IDENTICALLY to the index and the query, which is the point: a query
    typed «اشده» has to meet the corpus token «أشده». Using `normalize_text`
    here instead is what once made the most distinctive query terms fail to
    match, because it deletes hamza on one side only.

    Do NOT use this for root keys: ة → ه is wrong for a root.
    """
    if not text:
        return ""
    text = normalize_root(text)
    text = text.translate(QURANIC_MARKS_TABLE)
    return text.translate(_MATCH_FOLD)


def normalize_text(text: str) -> str:
    """The ingestion pipeline's `text_ar_clean`. **DELETES hamza.**

    Strips harakat and tatweel, folds every alif variant to ا, ى → ي, ؤ → و,
    ئ → ي, and REMOVES the bare hamza ء entirely.

    Never use this for roots or for matching. Applied to roots it truncates
    ~8.4 % of the QAC roots and merges distinct ones into a single key; applied
    to a search query it turns أشده into شده on one side of the comparison only.
    `normalize_root` and `normalize_search` exist because of exactly that.

    ta-marbuta ة is deliberately NOT folded here, so the readable text survives;
    that fold belongs to `normalize_search`.
    """
    if not text:
        return ""

    # 1. Unicode NFC first, to merge decomposed forms.
    text = unicodedata.normalize("NFC", text)

    # 2. Strip diacritics.
    if _HAS_PYARABIC:
        text = araby.strip_tashkeel(text)
        text = araby.strip_tatweel(text)
    else:
        text = strip_harakat(text)
        text = text.replace(TATWEEL, "")

    # 3. Letter normalization.
    if _HAS_PYARABIC:
        # normalize_hamza maps أ إ آ ؤ ئ back to simpler forms.
        text = araby.normalize_hamza(text)

    for ch in ("أ", "إ", "آ", "ٱ"):
        text = text.replace(ch, "ا")
    text = text.replace("ى", "ي")
    text = text.replace("ؤ", "و")
    text = text.replace("ئ", "ي")
    # Standalone hamza → removed. This line is what the other two normalizers
    # exist to avoid.
    text = text.replace("ء", "")

    # 4. Collapse whitespace.
    text = " ".join(text.split())

    # 5. Final NFC.
    return unicodedata.normalize("NFC", text)

