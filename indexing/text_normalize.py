"""
text_normalize.py — Search-time Arabic normalization (hamza-safe).

Used by the BM25 index build AND the query side, identically, so a user-typed
word folds to the same token that was indexed. This deliberately does NOT use
`ingestion.normalizer.normalize_text`, which DELETES hamza (أشده → شده) and folds
hamza-initial alif inconsistently — that asymmetry made the most distinctive
query terms fail to match (a plain-alif query "اشده" never met the corpus token
"شده"). See indexing/bm25_index.py.

Rules (built on the hamza-safe `normalize_root` core):
  1. NFC, strip harakat/tashkeel and tatweel, fold hamza carriers WITHOUT
     deleting (أ إ آ ٱ → ا ; ؤ → و ; ئ → ي ; keep bare ء).   [normalize_root]
  2. Strip Quranic annotation / waqf marks (U+06D6–U+06ED, e.g. ۖ ۚ), which
     otherwise survive as standalone noise tokens.
  3. Fold for matching: alif-maqsura ى → ي, ta-marbuta ة → ه.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.root_normalize import normalize_root  # noqa: E402  (hamza-safe core)

# Quranic annotation / small high marks (waqf signs, sajda, etc.): U+06D6–U+06ED.
_QURANIC_MARKS = {cp: None for cp in range(0x06D6, 0x06ED + 1)}

# Extra folds that help lexical matching (not roots): alif-maqsura, ta-marbuta.
_MATCH_FOLD = {ord("ى"): "ي", ord("ة"): "ه"}


def normalize_search(text: str) -> str:
    """Hamza-safe normalization for BM25 indexing and query tokenization."""
    if not text:
        return ""
    text = normalize_root(text)          # NFC + harakat/tatweel + hamza fold
    text = text.translate(_QURANIC_MARKS)  # drop waqf / annotation marks
    text = text.translate(_MATCH_FOLD)     # ى → ي, ة → ه
    return text


if __name__ == "__main__":
    for s in ["أشده", "اشده", "آتيناه", "ولما", "موسى", "صلاة", "الإنسان ۖ"]:
        print(f"  {s!r:14} → {normalize_search(s)!r}")
