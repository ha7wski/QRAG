"""
Root index endpoints: «فهرس الجذور», every Quranic root browsable by its first letter.

Read-only and LLM-free. Nothing here counts anything: the figures of a root are
`VerseLookup.root_forms(root)` read back — the method «الكلمة في الآيات» and «تحليل
اللسان» already share — so the grammatical-tool filter and the canonical root keys
come with it and the three pages give one answer per root. The sūras are derived
from those āya refs, never from `morphology.json`.

**Which roots** (design D1): the `morphology.json` keys whose `count` is above
zero. A key that exists only as an ALTERNATE reading (نوس for ٱلنَّاس, طمن) has a
non-empty `root_forms`, because the lemma groups reach the word through it; listing
it would show the same occurrences under two roots. `count` already tallies the
primary only, so it is the criterion, not a curated list.

**Grouping** (D2): by first radical, with bare alif and every hamza seat in ONE
group labelled «أ». `fold_carrier` alone is not that key — it sends ؤ to و and ئ to
ي — so the seats are named explicitly and the fold handles the rest. Inside a group
the order is hijāʾī letter by letter under the carrier fold, the exact spelling
breaking ties, so it is total and reproduces in any process.

**The reading** (D5) is `assemble(root)` — the project's mechanical junction of the
root's three Islambouli rows — called with no signed choice, always. This router
never opens the reader's store, so no path exists by which a stored choice could
collapse an «أو» group here. Islambouli's own published sentences and the cultural
stage are not read at all. A frozen table that fails its lock removes the readings
of the whole letter and nothing else.

Each letter is built on first request and memoised on `app.state` (D3): ~60 roots
at ~10 ms of `root_forms` each is cheap, and a derived dataset would be one more
thing able to drift from `root_forms`.
"""
from __future__ import annotations

import functools
from typing import Callable

from fastapi import APIRouter, HTTPException, Request

from api.models.roots import RootLetterResponse, RootLettersResponse
from arabic_text import fold_carrier
from quran_data import loaders

router = APIRouter(tags=["roots"])

# The 28 letter groups, in hijāʾī order. The first is labelled «أ»: it gathers
# bare alif and every hamza seat.
GROUPS: tuple[str, ...] = tuple("أبتثجحخدذرزسشصضطظعغفقكلمنهوي")
_ALIF_GROUP = GROUPS[0]
# Every spelling of a first radical that belongs to the «أ» group. Named, because
# the carrier fold maps ؤ → و and ئ → ي, which is right for comparing roots and
# wrong for grouping them: both are hamza.
_HAMZA_SEATS = frozenset("اأإآٱءؤئ")

# In-group comparison: hijāʾī rank of each carrier-folded letter. The bare hamza
# (kept by the fold) ranks with alif; anything unexpected sorts after ي, by
# codepoint, so the key stays total whatever a future key holds.
_ORDER = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"
_RANK = {ch: i for i, ch in enumerate(_ORDER)} | {"ء": 0}


# ── pure shaping (no FastAPI, no disk) ─────────────────────────────────────

def group_of(letter: str) -> str | None:
    """The group label a single letter falls into, or None for anything else."""
    if not letter or len(letter) != 1:
        return None
    if letter in _HAMZA_SEATS:
        return _ALIF_GROUP
    folded = fold_carrier(letter)
    return folded if folded in GROUPS else None


def sort_key(root: str) -> tuple:
    """Hijāʾī letter by letter under the carrier fold; the exact spelling breaks ties."""
    ranks = tuple(_RANK.get(ch, len(_ORDER) + ord(ch)) for ch in fold_carrier(root))
    return ranks, root


def listed_roots(morphology: dict) -> list[str]:
    """The roots the index lists: the primary ones, `count > 0` (D1)."""
    return [root for root, entry in morphology.items() if entry.get("count", 0) > 0]


def group_roots(roots: list[str]) -> dict[str, list[str]]:
    """`{label: [root, …]}` for all 28 labels in hijāʾī order, each list sorted."""
    groups: dict[str, list[str]] = {label: [] for label in GROUPS}
    for root in roots:
        label = group_of(root[:1])
        if label is not None:
            groups[label].append(root)
    for members in groups.values():
        members.sort(key=sort_key)
    return groups


def letter_counts(morphology: dict) -> list[dict]:
    """The 28 groups with their root counts; a letter beginning no root shows 0."""
    groups = group_roots(listed_roots(morphology))
    return [{"letter": label, "count": len(groups[label])} for label in GROUPS]


def surah_list(verse_ids: list[str], names: dict[int, str]) -> list[dict]:
    """The distinct sūras of a root's āya refs, ascending, with their Arabic names."""
    numbers = sorted({int(ref.split(":", 1)[0]) for ref in verse_ids})
    return [{"number": n, "name_ar": names.get(n, "")} for n in numbers]


def root_entry(forms: dict, names: dict[int, str]) -> dict:
    """One root's figures, read off `root_forms` — nothing is recounted here."""
    verse_ids = list(forms["verse_ids"])
    suras = surah_list(verse_ids, names)
    return {
        "root": forms["root"],
        "words": forms["words"],
        "ayat": forms["ayat"],
        "surahs": len(suras),
        "verse_ids": verse_ids,
        "surah_list": suras,
        "forms": list(forms["forms"]),
        "reading": None,
        "reading_refusal": None,
        "letters": root_letters(forms["root"]),
    }


def root_letters(root: str) -> list[dict]:
    """The root's letter cards — name, مخرج, position and Islambouli's gloss.

    Exactly what «تحليل اللسان» shows, built by the same calls: the core-first
    engine's `decompose` + `identities` (phonetics only — the sense bundle and the
    Ibn Jinnī note are never forwarded) and the `/lisan` router's
    `_with_islambouli` join for the gloss — verbatim, or "" for every letter when
    his table fails its lock. No core is read and no sense selected.
    """
    from api.routers.lisan import _with_islambouli
    from linguistics.lisan.lisan_service import LisanService

    letters = LisanService.identities(root, LisanService.decompose(root))
    return _with_islambouli({"letters": letters})["letters"]


def attach_readings(entries: list[dict]) -> bool:
    """Set each entry's mechanical reading or refusal; False if a table moved.

    `assemble` is imported here, lazily, as `api/routers/lisan.py` does, and is
    called with the root alone: no choice between alternatives can enter.
    """
    from linguistics.lisan.harness.guard import WitnessRootComposed
    from linguistics.lisan.islambouli.assemble import assemble
    from linguistics.lisan.islambouli.table import TableNotFrozen
    from linguistics.lisan.islambouli.wasf import WasfNotFrozen

    readings: list[tuple[str | None, str | None]] = []
    try:
        for entry in entries:
            root = entry["root"]
            try:
                a = assemble(root)
            except WitnessRootComposed:
                # Raised only under a test runner, for a root of the Islambouli
                # holdout: leaving its reading out is what the guard asks for.
                readings.append((None, None))
                continue
            # The reason is Arabic at its source; the code is an identifier and is
            # never shown, so it is not a fallback.
            readings.append((None, a.refusal_reason)
                            if a.refused else (a.sentence, None))
    except (TableNotFrozen, WasfNotFrozen):
        # Nothing is shown from a table that is no longer the frozen one — for
        # ANY root, so the page carries one notice instead of a partial letter.
        return False
    for entry, (reading, refusal) in zip(entries, readings):
        entry["reading"], entry["reading_refusal"] = reading, refusal
    return True


@functools.lru_cache(maxsize=1)
def surah_names() -> dict[int, str]:
    """`{surah number: Arabic name}` from the verse corpus `GET /surahs` reads."""
    from quran_data.corpus import load_verses

    names: dict[int, str] = {}
    for verse in load_verses():
        names.setdefault(int(verse["surah_number"]), verse.get("surah_name_ar", ""))
    return names


def build_letter(label: str, root_forms: Callable[[str], dict],
                 morphology: dict | None = None,
                 names: dict[int, str] | None = None) -> dict:
    """One group's full payload. `label` must already be a group label."""
    morphology = loaders.morphology() if morphology is None else morphology
    names = surah_names() if names is None else names
    roots = group_roots(listed_roots(morphology))[label]
    entries = [root_entry(root_forms(root), names) for root in roots]
    available = attach_readings(entries)
    return {"letter": label, "count": len(entries),
            "readings_available": available, "roots": entries}


# ── routes ─────────────────────────────────────────────────────────────────

@router.get("/roots", response_model=RootLettersResponse)
def roots_letters() -> dict:
    """The 28 letter groups, in hijāʾī order, each with its number of roots."""
    letters = letter_counts(loaders.morphology())
    return {"total": sum(x["count"] for x in letters), "letters": letters}


@router.get("/roots/letter/{letter}", response_model=RootLetterResponse)
def roots_by_letter(letter: str, request: Request) -> dict:
    """One group's roots, in order, with their figures and readings.

    `{letter}` is the group label or any letter folding into it (ا, ء, ؤ … all
    answer the «أ» group); anything else is a 404.
    """
    label = group_of(letter.strip())
    if label is None:
        raise HTTPException(status_code=404, detail=f"unknown letter: {letter!r}")
    cache = getattr(request.app.state, "root_index_letters", None)
    if cache is None:
        cache = request.app.state.root_index_letters = {}
    if label not in cache:
        cache[label] = build_letter(label, request.app.state.verse_lookup.root_forms)
    return cache[label]
