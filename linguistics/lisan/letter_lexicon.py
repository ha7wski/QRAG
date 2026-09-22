"""
letter_lexicon.py — a letter's phonetic identity joined to its BUNDLE of senses.

Reads the two letter sheets through `quran_data.loaders` and exposes
`describe(letter)`: the classical makhraj/ṣifāt, an Ibn Jinnī sound-imitation
note, and EVERY sense the framework attributes to that letter — as a list, in
declaration order, unranked.

**This module never picks a sense, and that is the whole point.** It used to
return one frozen `abbas_meaning_ar` per letter, which the synthesis then
concatenated in root order; on `خ-ي-ر` that produced «القذارة والخشونة
والخواء … فساد» against Ibn Fāris' «أصله العطف والميل». There is no single
correct gloss for `خ`: the negative one is right for `خ-ب-ث` and wrong for
`خ-ي-ر`. Which member of the bundle applies depends on the ROOT's attested
core — something a per-letter lexicon cannot know — so choosing, ranking or
defaulting a sense here would only relocate the same defect. Selection is the
caller's step (`sense_selection.select_for_letter`, constrained by a core from
`root_core_store`); the lexicon's contract is to hand over the whole bundle
with nothing marked selected or preferred.

Datasets (both read through the registry, never opened here):
  * ARABIC_LETTERS_CSV — 28 rows, identity and phonetics ONLY. The
    `abbas_meaning*` / `abbas_keywords*` columns were dropped with the old
    behaviour; there is no `meaning` and no `keywords` key any more.
  * LETTER_SENSES_CSV  — one row per (letter, sense): sense_id, gloss_ar, pole,
    axes (`;`-separated ids), position, gesture_ar, source, page, confidence.

The Lisan feature is Arabic-only, so only the `_ar` columns of the phonetic
sheet are read; the English ones stay on file for auditing.

Hamza-seat aware: أ إ ؤ ئ آ ٱ all fold to the base `ء` entry. A letter absent
from the dataset (e.g. the bare alif ا, not a base consonant in the framework)
does NOT raise — `describe` returns a neutral placeholder so a root reading
always has one entry per letter.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402

# Hamza carriers → the base bare-hamza entry `ء`.
#
# This is the NORMAL path, not a defensive edge case, and the distinction
# matters: QAC root keys are stored in their EXACT, hamza-bearing spelling, so
# **138 of the 1 656 roots decompose into a letter that is a seat** (أبب، أبد،
# أبو، أتي، …) against exactly ONE carrying a bare ء (هاء). Deleting this map —
# which an earlier comment here invited, by claiming a decomposed root "rarely
# carries a seat" — would silently drop all 138 to the zero-sense placeholder:
# no exception, no warning, just 138 roots whose letters stop having senses.
_HAMZA_SEATS = {"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء", "آ": "ء", "ٱ": "ء"}

# The sense keys, in the order `api.models.lisan.LetterSense` declares them.
# Kept as one list so a column rename in the CSV fails here, loudly, instead of
# reaching the API as a silently missing field.
_SENSE_FIELDS = (
    "sense_id", "gloss_ar", "pole", "axes",
    "position", "position_kind", "gesture_ar", "source", "page", "confidence",
)


def _split_list(value: str) -> list[str]:
    """Split a ';'-separated dataset cell into a trimmed, non-empty list."""
    return [part.strip() for part in (value or "").split(";") if part.strip()]


@lru_cache(maxsize=1)
def _letters() -> dict[str, dict]:
    """Key the registry's phonetic rows by the `letter` glyph. Cached per process."""
    by_letter: dict[str, dict] = {}
    for row in loaders.arabic_letters():
        letter = (row.get("letter") or "").strip()
        if letter:
            by_letter[letter] = row
    return by_letter


@lru_cache(maxsize=1)
def _senses() -> dict[str, list[dict]]:
    """Group the sense rows by letter, PRESERVING CSV row order.

    Declaration order is load-bearing: it is the last term of the selection
    ranking, so ties fall to the curator's own ordering rather than to whatever
    order a dict happened to iterate in.
    """
    by_letter: dict[str, list[dict]] = {}
    for row in loaders.letter_senses():
        letter = (row.get("letter") or "").strip()
        if not letter:
            continue
        sense = {f: (row.get(f) or "").strip() for f in _SENSE_FIELDS}
        sense["axes"] = _split_list(row.get("axes", ""))
        # A SET of positions, not one: Ḥasan ʿAbbās states «في الآخر والوسط»
        # as a single predicate over two positions. A blank cell means `any`.
        sense["position"] = _split_list(row.get("position", "")) or ["any"]
        by_letter.setdefault(letter, []).append(sense)
    return by_letter


def _placeholder(letter: str) -> dict:
    """Neutral entry for a letter absent from the dataset — never raises.

    Carries an empty bundle rather than a fabricated sense: a letter the
    framework does not treat as a base consonant asserts nothing, and the
    reading shows the gap instead of filling it.
    """
    return {
        "letter": letter,
        "name": letter,
        "makhraj": "",
        "sifat": [],
        "ibn_jinni_note": "",
        "confidence": "unknown",
        "senses": [],
    }


def describe(letter: str) -> dict:
    """Return one Arabic `letter`'s phonetic identity plus its whole sense bundle.

    `senses` is every sense on file for the letter, in CSV declaration order,
    with none selected, ranked or marked preferred — see the module docstring:
    picking one needs a root's attested core, which this module does not have.
    Hamza seats fold to the base `ء` entry; a missing letter gets a neutral
    placeholder with an empty bundle.
    """
    glyph = _HAMZA_SEATS.get(letter, letter)
    row = _letters().get(glyph)
    if row is None:
        return _placeholder(letter)

    return {
        "letter": glyph,
        "name": row.get("name_ar", ""),
        "makhraj": row.get("makhraj_ar", ""),
        "sifat": _split_list(row.get("sifat_ar", "")),
        "ibn_jinni_note": row.get("ibn_jinni_note_ar", ""),
        "confidence": (row.get("confidence") or "unknown").strip(),
        # Copied out of the process-wide cache on every call: a caller that
        # annotated a sense in place (the selection step hands these dicts
        # straight to the API layer) would otherwise poison every later request.
        "senses": [
            dict(s, axes=list(s["axes"]), position=list(s["position"]))
            for s in _senses().get(glyph, ())
        ],
    }


def letter_count() -> int:
    """Number of base letters loaded (28 for the curated dataset)."""
    return len(_letters())


if __name__ == "__main__":
    for ch in "خير":
        d = describe(ch)
        print(f"{ch} ({d['name']}, {d['makhraj']}) — {len(d['senses'])} sense(s):")
        for s in d["senses"]:
            print(f"    [{s['sense_id']}] {s['gloss_ar']}")
            print(f"        pole={s['pole']} axes={','.join(s['axes'])} "
                  f"position={s['position']} confidence={s['confidence']}")
    print("hamza seat أ →", describe("أ")["letter"],
          f"({len(describe('أ')['senses'])} senses)")
    print("missing ا →", describe("ا"))
    print("total letters:", letter_count())
