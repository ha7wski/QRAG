"""
corpus.py — the verse corpus, and the one place the Basmala is dealt with.

`verses_final.json` (~6.8 MB, 6236 verses) is needed by several components in
the same backend process — `HybridSearch`, `Retriever`, and `LexicalRetriever`.
Loading it independently in each would hold 2–3 copies in RAM. These helpers
parse the file once per process (cached) and hand back a shared object.

**Read-only contract:** callers must not mutate the returned list/dict or the
verse dicts in place (everyone shares them). Need a different order? Use
`sorted(load_verses(), ...)`, which returns a new list over the same dicts.
"""
from __future__ import annotations

import csv
import functools
import json

from arabic_text import bare as _bare
from quran_data import paths

VERSES_FINAL = paths.VERSES_FINAL_JSON
QURAN_CHAKL_CSV = paths.QURAN_CHAKL_CSV


@functools.lru_cache(maxsize=1)
def load_verses() -> list[dict]:
    """Return the parsed verse list, loaded once per process and cached."""
    if not VERSES_FINAL.exists():
        raise FileNotFoundError(
            f"{VERSES_FINAL} not found. Run `python ingestion/run_pipeline.py` first."
        )
    with VERSES_FINAL.open(encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def verses_by_id() -> dict[str, dict]:
    """`{verse_id: verse}` view over the cached corpus (built once, shared)."""
    return {v["id"]: v for v in load_verses()}


@functools.lru_cache(maxsize=1)
def chakl_by_ref() -> dict[tuple[int, int], dict]:
    """`{(surah, ayah): {"text", "surah_name"}}` from `quran_chakl.csv`.

    The processed corpus `text_ar` has no harakat; this is the only source of
    fully diacritized (vocalized) verse text. Loaded once per process, shared
    by every feature that displays vocalized verses.

    **Rows are returned exactly as stored — do NOT strip the Basmala here.**
    The CSV prepends the Basmala to ayah 1 of 113 surahs, and these rows are
    addressed by CHARACTER OFFSET: `linguistics.analysis.qlisan_data.word_index()` records
    `chakl_char_start` / `chakl_char_end` computed against the Basmala-inclusive
    string (`2:1:1` is stored at `[39, 42)`), and both the QLisan word fiche and
    `linguistics.analysis.mizan._vocalized_surface` slice rows by those offsets. Stripping
    the prefix here would shift every one of them and silently return the wrong
    word. Display consumers call `strip_leading_basmala()` instead.
    """
    if not QURAN_CHAKL_CSV.exists():
        raise FileNotFoundError(
            f"{QURAN_CHAKL_CSV} not found. Vocalized verse display needs the "
            f"diacritized corpus."
        )
    rows: dict[tuple[int, int], dict] = {}
    # utf-8-sig: tolerate a BOM on the header row.
    with QURAN_CHAKL_CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = (int(row["num_soura"]), int(row["num_aya"]))
            rows[key] = {"text": row["aya"], "surah_name": row["name_soura"]}
    return rows


# ── Vocalized display helpers ─────────────────────────────────────────────
#
# `quran_chakl.csv` prepends the Basmala to ayah 1 of 113 surahs (every surah
# but at-Tawba; in al-Fatiha the Basmala genuinely IS ayah 1). That prefix is an
# artefact of the source file, not part of the ayah, and must be removed before
# the text is displayed — but NOT inside `chakl_by_ref()`, whose rows are
# addressed by character offset (see its docstring).

# `_bare` is `arabic_text.bare`: it drops every mark — harakat, waqf signs and
# tatweel — leaving letters and whitespace. A COMPARISON KEY, never a value to
# store or display. The character ranges behind it are defined once, in
# `arabic_text/marks.py`, and written with \u escapes only.


@functools.lru_cache(maxsize=1)
def basmala_text() -> str:
    """The vocalized Basmala, read from the corpus row for `1:1`.

    Never a literal typed into source: combining-mark order is not stable across
    this corpus, so a hand-typed Basmala that is visually identical matches 0 of
    the 114 first-ayah rows on an exact comparison.
    """
    entry = chakl_by_ref().get((1, 1))
    return entry["text"] if entry else ""


def strip_leading_basmala(surah: int, ayah: int, text: str) -> str:
    """`text` without the corpus-prepended Basmala, for display.

    Returns `text` unchanged when it cannot be a prefixed row: any ayah other
    than the first, and al-Fatiha, whose Basmala genuinely is ayah 1. The
    position guard also spares `27:30`, which *contains* the Basmala as part of
    Sulayman's letter, independently of what the matcher would say.

    Detection compares diacritic-stripped forms (see `_bare`). The bare prefix
    length is then mapped back into the raw string by walking it and counting
    the characters that survive stripping, so the harakat of the Basmala are
    consumed with it.
    """
    if ayah != 1 or surah == 1:
        return text
    prefix = _bare(basmala_text())
    if not prefix or not _bare(text).startswith(prefix):
        return text

    # Walk the raw text until `len(prefix)` non-diacritic characters are behind
    # us, then absorb the marks still hanging on that last letter and the space
    # separating the Basmala from the ayah.
    kept = 0
    i = 0
    while i < len(text) and kept < len(prefix):
        if _bare(text[i]):
            kept += 1
        i += 1
    while i < len(text) and not _bare(text[i]):
        i += 1
    return text[i:].lstrip()


def surah_basmala(surah: int) -> str:
    """The surah's opening Basmala, or `""` when it has none of its own.

    Empty for al-Fatiha (where the Basmala is ayah 1 and already in the verse
    list) and for at-Tawba (which carries none). The two exceptions are not
    hard-coded: the answer is derived by asking whether the corpus row for
    `(surah, 1)` actually carried a prefix.
    """
    entry = chakl_by_ref().get((surah, 1))
    if entry is None:
        return ""
    return basmala_text() if strip_leading_basmala(surah, 1, entry["text"]) != entry["text"] else ""
