"""
normalizer.py — Stage 2 of the ingestion pipeline.

Normalizes the raw Arabic text of each verse and fills the `text_ar_clean`
field. The source CSV is already free of harakat, but we still apply full
normalization to guarantee consistency of the indexed text and to make
exact search easier.

Operations:
  1. Strip harakat / tashkeel (diacritics)
  2. Strip tatweel (ـ)
  3. Normalize alifs (أ إ آ ٱ → ا)
  4. Normalize ya (ى → ي)
  5. Normalize standalone hamza / waw-hamza / ya-hamza
  6. Unicode NFC normalization

Note: we do NOT normalize ta marbuta (ة → ه) in `text_ar_clean` so the
readable text is preserved. Aggressive ta-marbuta normalization is applied
separately at BM25 tokenization / search time.
"""
from __future__ import annotations

import unicodedata

try:
    import pyarabic.araby as araby

    _HAS_PYARABIC = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_PYARABIC = False


# Arabic diacritic (tashkeel) characters to strip.
_TASHKEEL = "".join(
    [
        "ؐ", "ؑ", "ؒ", "ؓ", "ؔ", "ؕ",
        "ؖ", "ؗ", "ؘ", "ؙ", "ؚ",
        "ً", "ٌ", "ٍ", "َ", "ُ", "ِ",
        "ّ", "ْ", "ٓ", "ٔ", "ٕ", "ٖ",
        "ٗ", "٘", "ٙ", "ٚ", "ٛ", "ٜ",
        "ٝ", "ٞ", "ٟ", "ٰ",
    ]
)
_TASHKEEL_TABLE = {ord(c): None for c in _TASHKEEL}

_TATWEEL = "ـ"


def _strip_tashkeel(text: str) -> str:
    return text.translate(_TASHKEEL_TABLE)


def normalize_text(text: str) -> str:
    """Normalize an Arabic text string (the `clean` version)."""
    if not text:
        return ""

    # 1. Unicode NFC first, to merge decomposed forms.
    text = unicodedata.normalize("NFC", text)

    # 2. Strip diacritics.
    if _HAS_PYARABIC:
        text = araby.strip_tashkeel(text)
        text = araby.strip_tatweel(text)
    else:
        text = _strip_tashkeel(text)
        text = text.replace(_TATWEEL, "")

    # 3. Letter normalization.
    if _HAS_PYARABIC:
        # normalize_hamza maps أ إ آ ؤ ئ back to simpler forms.
        # normalize_alef / normalize_teh also exist, but we keep explicit
        # and stable behavior below.
        text = araby.normalize_hamza(text)

    # Alifs → ا
    for ch in ("أ", "إ", "آ", "ٱ"):  # alif variants
        text = text.replace(ch, "ا")
    # Alif maqsura ى → ي
    text = text.replace("ى", "ي")
    # Hamza on waw / ya → simple forms
    text = text.replace("ؤ", "و")
    text = text.replace("ئ", "ي")
    # Standalone hamza → removed (rare in the raw text)
    text = text.replace("ء", "")

    # 4. Collapse whitespace.
    text = " ".join(text.split())

    # 5. Final NFC.
    return unicodedata.normalize("NFC", text)


def run(verses: list[dict]) -> list[dict]:
    """Fill `text_ar_clean` for each verse (in place) and return the list."""
    backend = "pyarabic" if _HAS_PYARABIC else "internal fallback"
    for v in verses:
        v["text_ar_clean"] = normalize_text(v["text_ar"])
    n_empty = sum(1 for v in verses if not v["text_ar_clean"])
    print(f"  normalizer : {len(verses)} verses normalized ({backend})"
          + (f", ⚠️ {n_empty} empty" if n_empty else ""))
    return verses


if __name__ == "__main__":
    samples = [
        "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        "إِنَّآ أَعْطَيْنَٰكَ ٱلْكَوْثَرَ",
    ]
    for s in samples:
        print(f"{s}\n  → {normalize_text(s)}\n")
