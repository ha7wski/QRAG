"""
root_normalize.py — Root-safe Arabic normalization for the QAC root index.

This is DELIBERATELY separate from `ingestion.normalizer.normalize_text`.
`normalize_text` deletes the hamza (`ء`) and, because `pyarabic.normalize_hamza`
folds hamza-carriers to a bare hamza first, it also drops word-initial `أ إ آ`.
Applied to roots that path truncates ~8.4% of the QAC roots and merges distinct
roots into one key — catastrophic for a root index.

`normalize_root` is the ONLY normalization used for QAC root keys, and it is
applied IDENTICALLY on the index-key side (builder) and the query side
(resolver), so a typed word always folds to the same key that was stored.

Rules:
  1. Unicode NFC.
  2. Strip harakat / tashkeel (incl. the dagger alif `ٰ`) and tatweel (`ـ`).
  3. Fold hamza-carriers to a single canonical form — WITHOUT deleting anything:
        أ إ آ ٱ → ا   ;   ؤ → و   ;   ئ → ي
     The bare hamza `ء` is kept as `ء` (never removed).

Verified over all 1651 distinct QAC roots: this fold produces 1651 distinct
keys (zero collisions). See tests/test_root_normalize.py.
"""
from __future__ import annotations

import unicodedata

# Diacritics / harakat to strip (superset of normalizer._TASHKEEL, incl. the
# dagger alif U+0670 which appears in vocalized QAC forms).
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

# Hamza-carrier folding. NOTE: bare hamza `ء` (U+0621) is intentionally absent —
# it is kept as-is, never deleted.
_HAMZA_FOLD = {
    "أ": "ا",  # alif + hamza above  → ا
    "إ": "ا",  # alif + hamza below  → ا
    "آ": "ا",  # alif madda          → ا
    "ٱ": "ا",  # alif wasla          → ا
    "ؤ": "و",  # waw + hamza         → و
    "ئ": "ي",  # ya + hamza          → ي
}
_HAMZA_TABLE = {ord(k): v for k, v in _HAMZA_FOLD.items()}


def normalize_root(text: str) -> str:
    """Return the root-safe normalized form of an Arabic root or query word.

    Strips harakat/tatweel and lightly folds hamza-carriers; never deletes a
    hamza. Applied identically to index keys and query input.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_TASHKEEL_TABLE)   # strip harakat / dagger alif
    text = text.replace(_TATWEEL, "")         # strip tatweel
    text = text.translate(_HAMZA_TABLE)       # fold hamza-carriers (no delete)
    return unicodedata.normalize("NFC", text).strip()


if __name__ == "__main__":
    for r in ["أله", "قرأ", "نبأ", "حمد", "كرم", "حصحص", "كَرِيمٌ", "رحـم"]:
        print(f"  {r!r:>10} → {normalize_root(r)!r}")
