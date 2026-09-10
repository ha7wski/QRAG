"""
fassila.py — Pausal-form fāṣila (فاصلة) derivation over the Uthmānī corpus.

The fāṣila is the letter that closes an āya *in pause* (وقفًا): the last letter of
the last word once tashkīl is removed, tanwīn neutralized, and `ة → ه`, `ى → ا`,
dagger alif `ٰ → ا` folded. Its distribution and its run-structure across a sūra are
the object of the `/fassila` page.

Everything here is pure and offline — one linear pass over `quran_chakl.csv` (via the
shared `quran_data.corpus.chakl_by_ref()` loader) plus the two QAC projections this module
needs, taken from `quran_data.qac` (which builds them from a SINGLE pass over
`quran-morphology.txt`; this module used to open that 6 MB file twice by itself). No ML,
no LLM, no network. Results are `@lru_cache`d per process, same pattern as
`quran_data/corpus.py`.

**Words come from the QAC treebank, not from `quran_chakl.csv`** — the single most
important thing to know about this module. The two corpora use different orthographies
and the fāṣila depends on which: `quran_chakl.csv` is imlāʾī (modern plene) while QAC
carries the Uthmānī rasm. Reading the plene form gets 43 āyāt wrong, most of Sūrat
Ṭā-Hā among them (`فَاعْبُدْنِي` → `ي`, where the rasm `فَٱعْبُدْنِى` → `ا`). See
`qac_ayah_words()`. Sourcing from QAC also makes word indices definitionally aligned
with the `s:a:w` spine and sidesteps the Basmala that `quran_chakl.csv` prepends to
āya 1 of 113 sūras (QAC does not carry it). `quran_chakl.csv` is still consulted, but
only for sūra names.

Two further corpus properties the derivation must handle:

- **Āyāt do not reliably end in a letter**: waqf and recitation marks appear inline,
  the sajda mark `۩` closes 15 āyāt in the vocalized text, and most āyāt end in a
  bare combining ḥaraka.
- **The dagger alif `ٰ` (U+0670) is a letter, not an ornament** — a word closing on it
  (`مُوسَىٰ`, `ٱلْهُدَىٰ`) rhymes on `ا`, so it must be read before marks are stripped.

Muqaṭṭaʿāt āyāt (āyāt made *only* of disconnected letters) carry no fāṣila and are
excluded from every count. They are detected from the QAC `INL` tag rather than a
hardcoded list of combinations — see `muqattaat_refs()`.
"""
from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quran_data.corpus import chakl_by_ref  # noqa: E402
from quran_data import qac  # noqa: E402

# Tashkīl + Qurʾānic annotation marks.
#
# The U+064B–U+065F block is spelled out as a single range on purpose: splitting it
# (e.g. `[ؐ-ً]` + `[ٚ-ٰ]`) silently drops U+064C–U+0659 —
# dammatan, kasratan, fatḥa, ḍamma, kasra, shadda, sukūn, madda and the two hamza
# marks. That gap makes stripping *look* correct on undiacritized text while failing
# on everything vocalized.
_TASHKIL = (
    "ؐ-ؚ"  # Qurʾānic annotation signs
    "ً-ٟ"  # tanwīn, ḥarakāt, shadda, sukūn, madda, hamza above/below
    "ٰ"         # dagger alif (superscript alef)
    "ۖ-ۜ"  # small high waqf / recitation marks
    "۟-ۨ"
    "۪-ۭ"
)
_MARKS_RE = re.compile(f"[{_TASHKIL}ـ]")  # + tatweel

# Non-letter symbols that may close an āya but are never the fāṣila.
_ANNOTATION_SYMBOLS_RE = re.compile("[ۖ-ۭ۩࣢؞؟]")

_TANWIN = "ًٌٍ"          # fatḥatān, dammatān, kasratān
_DAGGER_ALIF = "ٰ"
_ALIF_MAQSURA = "ى"
_TA_MARBUTA = "ة"
_ALIF = "ا"
_HA = "ه"


def strip_marks(text: str) -> str:
    """Remove tashkīl, tatweel and Qurʾānic annotation marks from `text`."""
    return _MARKS_RE.sub("", text)


def fasila_of(word: str) -> str:
    """Return the pausal-form fāṣila letter of a single vocalized `word`.

    Rules, in order: drop trailing non-letters → note whether the word ended in
    tanwīn over a written alif → remove all marks → fold `ة → ه`, `ى → ا`, and a
    final dagger alif → take the last character.
    """
    word = _ANNOTATION_SYMBOLS_RE.sub("", word).strip()
    if not word:
        return ""

    # A dagger alif closing the word is pronounced as a long ā in pause
    # (`مُوسَىٰ`, `ٱلْهُدَىٰ`), so it *is* the fāṣila — record it before marks are stripped.
    ends_in_dagger_alif = word.rstrip()[-1] == _DAGGER_ALIF

    letters = strip_marks(word)
    if not letters:
        return _ALIF if ends_in_dagger_alif else ""

    last = letters[-1]

    if ends_in_dagger_alif:
        # `مُوسَىٰ` → bare `موسى`; the dagger alif overrides the maqṣūra beneath it.
        return _ALIF
    if last == _TA_MARBUTA:
        return _HA
    if last == _ALIF_MAQSURA:
        return _ALIF
    return last


def muqattaat_refs() -> frozenset[tuple[int, int]]:
    """`{(surah, ayah)}` for āyāt composed *only* of disconnected letters.

    Detected from the QAC treebank: an āya qualifies iff **every** one of its words
    carries the `INL` (Qurʾānic initials) tag. This is preferred over matching a
    hardcoded list of known combinations because it needs no Basmala-strip and no
    mark-order normalization, and because āyāt that merely *open* with initials but
    continue with ordinary words (الر, المر, طس, ص, ق, ن) fall out as non-excluded
    with no special-casing.

    Yields exactly 20 āyāt across 19 sūras; `tests/test_fassila.py` freezes the list.

    No cache of its own: `quran_data.qac` caches the projection, and it is shared with
    `qac_ayah_words()` — the same single pass over the source produces both.
    """
    return qac.initial_only_ayat()


@functools.lru_cache(maxsize=1)
def qac_ayah_words() -> dict[tuple[int, int], list[str]]:
    """`{(surah, ayah): [word_1, word_2, …]}` in Uthmānī rasm, from the QAC treebank.

    Each word is its morphological segments concatenated back into the orthographic
    form, with alif waṣla folded to a plain alif for display.

    **This — not `quran_chakl.csv` — is the source of the fāṣila.** The two corpora
    use different orthographies and the fāṣila depends on which: `quran_chakl.csv` is
    imlāʾī (modern plene) and writes `فَاعْبُدْنِي`, `صَادِقِينَ`, `الْعَالَمِينَ`, whereas the
    Uthmānī rasm writes `فَٱعْبُدْنِى`, `صَٰدِقِينَ`, `ٱلْعَٰلَمِينَ`. Reading the plene form
    yields `ي` where the rhyme is `ا` — 43 āyāt diverge, most of Sūrat Ṭā-Hā among them.

    Sourcing words here also makes word indices *definitionally* aligned with the
    `s:a:w` spine, and sidesteps the Basmala that `quran_chakl.csv` prepends to āya 1
    (QAC does not carry it).

    The words come from `quran_data.qac.ayah_words()` exactly as the corpus writes
    them; the alif-waṣla → plain-alif fold applied here is **this module's own display
    decision**, not the corpus's, which is why the registry hands back the unfolded
    form and the fold stays on this side.
    """
    return {
        ref: [word.replace("ٱ", _ALIF) for word in words]
        for ref, words in qac.ayah_words().items()
    }


# `maxsize=128` is **load-bearing**, not a round number: 128 ≥ 114 means `overview()`
# can fan out over the whole muṣḥaf and stay memoized end-to-end (0.22 s cold, ~9 µs
# warm). Lowering it below 114 silently turns every overview request into a full
# re-derivation.
@functools.lru_cache(maxsize=128)
def analyse_surah(surah: int) -> dict:
    """Full fāṣila analysis of one sūra.

    Percentages are computed over **analysed** āyāt (muqaṭṭaʿāt excluded from the
    denominator), never over the sūra's total āya count.
    """
    corpus = qac_ayah_words()
    excluded_refs = muqattaat_refs()

    ayah_numbers = sorted(a for (s, a) in corpus if s == surah)
    if not ayah_numbers:
        raise ValueError(f"Surah {surah} not found in the corpus")

    # Sūra names live only in the vocalized CSV; the QAC treebank carries none.
    surah_name = chakl_by_ref()[(surah, 1)]["surah_name"]
    ayahs: list[dict] = []

    for ayah in ayah_numbers:
        is_muq = (surah, ayah) in excluded_refs
        words = corpus[(surah, ayah)]
        last_word = words[-1] if words else ""
        ayahs.append(
            {
                "ayah": ayah,
                "fasila": None if is_muq else fasila_of(last_word),
                "word": last_word,
                "word_ref": f"{surah}:{ayah}:{len(words)}" if words else "",
                "is_muqattaat": is_muq,
            }
        )

    analysed = [a for a in ayahs if not a["is_muqattaat"]]
    n_analysed = len(analysed)

    counts: dict[str, int] = {}
    first_appearance: list[str] = []
    for a in analysed:
        letter = a["fasila"]
        if letter not in counts:
            first_appearance.append(letter)
        counts[letter] = counts.get(letter, 0) + 1

    # Descending count; ties broken by first-appearance index so the order is stable
    # across processes (Arabic `sorted()` on letters would be locale-flavoured).
    by_frequency = sorted(
        counts, key=lambda l: (-counts[l], first_appearance.index(l))
    )

    def pct(n: int) -> float:
        return round(n / n_analysed * 100, 1) if n_analysed else 0.0

    dominant = by_frequency[0] if by_frequency else None

    return {
        "surah": surah,
        "surah_name": surah_name,
        "total_ayahs": len(ayahs),
        "analysed_ayahs": n_analysed,
        "excluded_ayahs": len(ayahs) - n_analysed,
        "distinct_count": len(counts),
        "dominant": (
            {
                "letter": dominant,
                "count": counts[dominant],
                "percentage": pct(counts[dominant]),
            }
            if dominant
            else None
        ),
        "counts": [
            {"letter": l, "count": counts[l], "percentage": pct(counts[l])}
            for l in by_frequency
        ],
        "first_appearance": first_appearance,
        "ayahs": ayahs,
    }


SURAH_COUNT = 114


def surah_summary(surah: int) -> dict:
    """Compact per-sūra record for the cross-sūra reading.

    Every field is *read off* `analyse_surah`, never re-derived — the summary is a
    projection of the single-sūra analysis, so a correction to the derivation reaches
    both readings at once.

    `fawasil` is the sūra's distinct fāṣila letters in the same descending-count order
    `counts` already uses (ties broken by first appearance), so the two endpoints cannot
    disagree about how a sūra's fawāṣil are ordered. It is not reconstructible from the
    other fields — `distinct_count` is a number and `dominant` names one letter — and the
    comparison page needs it to report which fawāṣil a *selection* of sūras covers.
    """
    r = analyse_surah(surah)
    return {
        "surah": r["surah"],
        "surah_name": r["surah_name"],
        "total_ayahs": r["total_ayahs"],
        "analysed_ayahs": r["analysed_ayahs"],
        "excluded_ayahs": r["excluded_ayahs"],
        "distinct_count": r["distinct_count"],
        "fawasil": [c["letter"] for c in r["counts"]],
        "dominant": r["dominant"],
    }


@functools.lru_cache(maxsize=1)
def overview() -> dict:
    """The fāṣila read across the whole muṣḥaf: 114 summaries plus corpus aggregates.

    A pure fan-out over `analyse_surah`, whose cache holds more sūras than the muṣḥaf
    has — so this costs one shared pass of the QAC treebank and is free afterwards.

    Aggregates are computed here rather than client-side so the rounding rule lives in
    one place and the figures are assertable in a test. The mean uses the same one-decimal
    convention as the percentages.

    Buckets are **contiguous** from the observed minimum to the observed maximum: a
    distinct-count attained by no sūra still yields a zero-count bucket, so the client
    plots a distribution instead of reconstructing the missing steps. Today the range is
    1 → 12 with no gaps.
    """
    summaries = [surah_summary(s) for s in range(1, SURAH_COUNT + 1)]
    distincts = [s["distinct_count"] for s in summaries]

    tally: dict[int, int] = {}
    for d in distincts:
        tally[d] = tally.get(d, 0) + 1
    lo, hi = min(tally), max(tally)

    return {
        "surah_count": len(summaries),
        "mean_distinct": round(sum(distincts) / len(distincts), 1),
        "mono_fasila_count": tally.get(1, 0),
        "max_distinct": hi,
        "max_distinct_surahs": [
            s["surah"] for s in summaries if s["distinct_count"] == hi
        ],
        "buckets": [
            {
                "distinct": d,
                "surah_count": tally.get(d, 0),
                # Shipped rather than divided client-side, so the one-decimal rounding
                # rule stays in this module with the percentages it matches.
                "percentage": round(tally.get(d, 0) / len(summaries) * 100, 1),
            }
            for d in range(lo, hi + 1)
        ],
        "surahs": summaries,
    }


if __name__ == "__main__":  # pragma: no cover - smoke test
    import json

    target = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    result = analyse_surah(target)
    print(f"sūra {result['surah']} · {result['surah_name']}")
    print(
        f"  {result['total_ayahs']} āyāt "
        f"({result['analysed_ayahs']} analysed, {result['excluded_ayahs']} excluded)"
    )
    print(f"  {result['distinct_count']} distinct fawāṣil")
    if result["dominant"]:
        d = result["dominant"]
        print(f"  dominant: {d['letter']} — {d['count']} ({d['percentage']}%)")
    print("  first appearance:", " ".join(result["first_appearance"]))
    print("  top:", json.dumps(result["counts"][:5], ensure_ascii=False))
    print(f"  muqaṭṭaʿāt corpus-wide: {len(muqattaat_refs())} āyāt")

    ov = overview()
    print(f"\ncorpus overview · {ov['surah_count']} sūras")
    print(f"  mean distinct fawāṣil: {ov['mean_distinct']}")
    print(f"  mono-fāṣila sūras: {ov['mono_fasila_count']}")
    print(
        f"  maximum: {ov['max_distinct']} — "
        + ", ".join(
            f"{s['surah_name']} ({s['surah']})"
            for s in ov["surahs"]
            if s["surah"] in ov["max_distinct_surahs"]
        )
    )
    print(
        "  buckets:",
        " ".join(f"{b['distinct']}:{b['surah_count']}" for b in ov["buckets"]),
    )
    peak = next(s for s in ov["surahs"] if s["distinct_count"] == ov["max_distinct"])
    print(f"  {peak['surah_name']} fawāṣil: {' '.join(peak['fawasil'])}")
