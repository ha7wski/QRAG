"""
letter_lexicon.py — Per-letter interpretive meanings for the Lisan feature.

Loads the curated letter dataset ONCE (cached) and exposes `describe(letter,
lang)`: the interpretive meaning, keywords, classical makhraj/sifat, and an Ibn
Jinni sound-imitation note for a single Arabic letter, in the requested language.

Data source (loaded in place, never moved/duplicated):
    data/references/arabic_letters_dataset.csv
28 rows, one per base letter, columns:
    letter, name_ar, name_translit, translit, makhraj_en, makhraj_ar,
    sifat, sifat_ar, abbas_meaning, abbas_meaning_ar, abbas_keywords,
    abbas_keywords_ar, ibn_jinni_note, ibn_jinni_note_ar, confidence

Language rule (per the feature spec): `ar` reads the `_ar` fields; `fr`/`en`
read the English source fields — French prose is produced later by the LLM
synthesis step, so only English source text is stored here.

Hamza-seat aware: the seats أ إ ؤ ئ آ ٱ all map to the base `ء` entry. A letter
absent from the dataset (e.g. the bare alif ا, which is not a base consonant in
the framework) does NOT crash — `describe` returns a neutral placeholder so the
sequential reading of a root always has one entry per letter.
"""
from __future__ import annotations

import csv
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATASET_CSV = ROOT / "data" / "references" / "arabic_letters_dataset.csv"

# Hamza carriers → the base bare-hamza entry `ء`. Root keys are already
# hamza-safe-normalized (seats folded to ا/و/ي, bare ء kept), so in practice a
# decomposed root rarely carries a seat; this keeps `describe` correct if one
# is passed directly.
_HAMZA_SEATS = {"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء", "آ": "ء", "ٱ": "ء"}


def _split_list(value: str) -> list[str]:
    """Split a ';'-separated dataset cell into a trimmed, non-empty list."""
    return [part.strip() for part in (value or "").split(";") if part.strip()]


@lru_cache(maxsize=1)
def _load() -> dict[str, dict]:
    """Load the CSV once, keyed by the `letter` glyph. Cached for the process."""
    by_letter: dict[str, dict] = {}
    with DATASET_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            letter = (row.get("letter") or "").strip()
            if letter:
                by_letter[letter] = row
    return by_letter


def _placeholder(letter: str) -> dict:
    """Neutral entry for a letter absent from the dataset — never raises."""
    return {
        "letter": letter,
        "name": letter,
        "makhraj": "",
        "sifat": [],
        "meaning": "",
        "keywords": [],
        "ibn_jinni_note": "",
        "confidence": "unknown",
    }


def describe(letter: str, lang: str = "ar") -> dict:
    """Return the interpretive description of a single Arabic `letter`.

    `lang`: "ar" reads the Arabic (`_ar`) fields; anything else reads English.
    Hamza seats fold to the base `ء` entry. Missing letters get a placeholder.
    """
    glyph = _HAMZA_SEATS.get(letter, letter)
    row = _load().get(glyph)
    if row is None:
        return _placeholder(letter)

    if lang == "ar":
        makhraj = row.get("makhraj_ar", "")
        sifat = _split_list(row.get("sifat_ar", ""))
        meaning = row.get("abbas_meaning_ar", "")
        keywords = _split_list(row.get("abbas_keywords_ar", ""))
        ibn_jinni = row.get("ibn_jinni_note_ar", "")
    else:
        makhraj = row.get("makhraj_en", "")
        sifat = _split_list(row.get("sifat", ""))
        meaning = row.get("abbas_meaning", "")
        keywords = _split_list(row.get("abbas_keywords", ""))
        ibn_jinni = row.get("ibn_jinni_note", "")

    return {
        "letter": glyph,
        "name": row.get("name_ar") if lang == "ar" else row.get("name_translit", ""),
        "makhraj": makhraj,
        "sifat": sifat,
        "meaning": meaning,
        "keywords": keywords,
        "ibn_jinni_note": ibn_jinni,
        "confidence": (row.get("confidence") or "unknown").strip(),
    }


def letter_count() -> int:
    """Number of base letters loaded (28 for the curated dataset)."""
    return len(_load())


if __name__ == "__main__":
    for ch in "رحم":
        d = describe(ch, "en")
        print(f"{ch} ({d['name']}): {d['meaning']}  [{d['confidence']}]")
    print("hamza seat أ →", describe("أ", "en")["letter"])
    print("missing ا →", describe("ا", "en"))
    print("total letters:", letter_count())
