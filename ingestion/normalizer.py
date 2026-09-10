"""
normalizer.py — Stage 2 of the ingestion pipeline.

Fills each verse's `text_ar_clean`. The source CSV carries no harakat, but the
text is normalized anyway so the indexed field is consistent and exact search is
predictable.

The normalization itself is `arabic_text.normalize_text` — this module is the
STAGE, not the rule. Which of the three normalizers to use, and what each does
to hamza, is documented in `arabic_text/`; `normalize_text` is the one that
DELETES hamza, and it must never be applied to a root or to a search query.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arabic_text import normalize_text  # noqa: E402


def run(verses: list[dict]) -> list[dict]:
    """Fill `text_ar_clean` for each verse (in place) and return the list."""
    from arabic_text.normalize import _HAS_PYARABIC

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
