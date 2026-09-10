"""
qac.py — the one reader of `quran-morphology.txt`.

Before this module the file had four independent readers — `linguistics/analysis/fassila.py`
(twice), `ingestion/qac_morphology.py`, `ingestion/root_resolver.py` and
`linguistics/tahlil/huruf.py` — each re-deriving the same four-column layout and each opening
the file again. A backend serving Fassila and Tahlīl paid three reads of 6 MB and
carried three copies of the format knowledge, so a change to the source would have
had to be found in four places.

**Format.** 130 030 lines, TAB-separated, exactly four columns on every line:

    1:1:1:2 \t سْمِ \t N \t ROOT:سمو|LEM:اسْم|M|GEN
    └ s:a:w:seg   └ form  └ tag  └ `|`-separated features

**What this module does and does not do.** It serves *data*: the corpus as it is
written. It applies no normalization, no folding and no linguistic judgement, and
it imports nothing from the project — that is the rule that keeps the registry at
the bottom of the dependency order. So the root projection hands back the raw
`ROOT:` spellings, hamza seat intact, and the caller that needs a folded key folds
them itself (`linguistics/tahlil/huruf.py` does, and raises on a collision).

**Two entry points, deliberately.**

`records()` streams and retains nothing — for the offline pipeline pass, which
needs every segment's full detail and runs once in its own process.

`ayah_words()`, `initial_only_ayat()` and `root_spellings()` are the runtime
projections. They are small, the API uses all three, and they are built together
from a **single pass** and cached: the first one asked for pays one read, the
other two are then free.

`word_roots()` is kept out of that bundle on purpose. It is ~77 000 keys, it is
used only by the offline `root_resolver` stage, and folding it into the shared
bundle would charge a backend that never calls it ~15 MB of resident memory —
against a memory budget this project takes seriously (see CLAUDE.md). It gets its
own cached pass instead. Net effect: the API process reads the file once where it
used to read it three times; the pipeline process still reads it twice, as before.
"""
from __future__ import annotations

import functools
import re
from typing import Iterator, NamedTuple

from quran_data.paths import QAC_MORPHOLOGY_TXT

# `ROOT:` runs to the next field separator. Written to match what the two
# existing readers used, character for character.
#
# One rule was tightened in the process, deliberately: this scans the FEATURES
# field and takes EVERY match, where `linguistics/tahlil/huruf.py` used to `re.search` the
# whole line and keep the first. The two agree over the corpus as it stands —
# 1651 identical root spellings, verified — because `ROOT:` only ever appears
# once, and only in column 4. They would diverge on a source that put a second
# `ROOT:` on a line, or one in another column; scanning the field a root is
# actually declared in is the rule that stays correct if that day comes.
_ROOT_FIELD_RE = re.compile(r"ROOT:([^|\t\r\n]+)")


class Record(NamedTuple):
    """One morphological segment, exactly as the file writes it."""

    surah: int
    ayah: int
    word: int
    segment: int
    form: str
    tag: str
    features: str


def _missing() -> FileNotFoundError:
    return FileNotFoundError(
        f"{QAC_MORPHOLOGY_TXT} not found. The Quranic Arabic Corpus morphology is a "
        "third-party source, not a build artefact: it cannot be regenerated. Obtain it "
        "from the mustafa0x/quran-morphology fork (see quran_data/manifest.py)."
    )


def parse_line(line: str) -> Record | None:
    """One raw line to a `Record`, or None to skip it.

    **The single place in the repo that knows this file's layout.** `records()`
    is this applied to a file; a caller with lines in memory — a test fixture,
    say — gets the same rule here rather than re-deriving the split, which is
    how four slightly different readers came to exist in the first place.

    Skipped: blanks, `#` comments, anything without four columns, and a location
    that is not four integers. The readers this replaces each guarded slightly
    differently; the file in fact contains none of these cases.
    """
    if not line.strip() or line.startswith("#"):
        return None
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 4:
        return None
    bits = parts[0].strip("()").split(":")
    if len(bits) != 4:
        return None
    try:
        surah, ayah, word, segment = (int(b) for b in bits)
    except ValueError:
        return None
    return Record(surah, ayah, word, segment, parts[1], parts[2], parts[3])


def records() -> Iterator[Record]:
    """Stream every segment of the corpus.

    Retains nothing, so a caller that needs the whole corpus in a shape of its own
    can build it without this module holding a second copy.
    """
    if not QAC_MORPHOLOGY_TXT.exists():
        raise _missing()
    with QAC_MORPHOLOGY_TXT.open(encoding="utf-8") as fh:
        for line in fh:
            record = parse_line(line)
            if record is not None:
                yield record


class _Runtime(NamedTuple):
    ayah_words: dict[tuple[int, int], tuple[str, ...]]
    initial_only_ayat: frozenset[tuple[int, int]]
    root_spellings: tuple[str, ...]


@functools.lru_cache(maxsize=1)
def _runtime() -> _Runtime:
    """Build the three runtime projections in one pass over the file."""
    words: dict[tuple[int, int], dict[int, str]] = {}
    initial: dict[tuple[int, int], dict[int, bool]] = {}
    # dict, not set: insertion order is the file's order, so the projection is
    # reproducible and diffable rather than hash-ordered.
    roots: dict[str, None] = {}

    for rec in records():
        ref = (rec.surah, rec.ayah)
        by_word = words.setdefault(ref, {})
        by_word[rec.word] = by_word.get(rec.word, "") + rec.form
        flags = initial.setdefault(ref, {})
        # A word counts as disconnected-letters if ANY of its segments is tagged INL.
        flags[rec.word] = flags.get(rec.word, False) or ("INL" in rec.features)
        for match in _ROOT_FIELD_RE.finditer(rec.features):
            raw = match.group(1).strip()
            if raw:
                roots.setdefault(raw, None)

    return _Runtime(
        ayah_words={ref: tuple(w[i] for i in sorted(w)) for ref, w in words.items()},
        initial_only_ayat=frozenset(
            ref for ref, flags in initial.items() if all(flags.values())
        ),
        root_spellings=tuple(roots),
    )


def ayah_words() -> dict[tuple[int, int], tuple[str, ...]]:
    """`{(surah, ayah): (word_1, word_2, …)}` in Uthmānī rasm, segments rejoined.

    Word indices are definitionally aligned with the `s:a:w` spine, and the QAC
    carries no Basmala prefix — the two reasons this, and not `quran_chakl.csv`,
    is what a caller reading word positions should use. Returned exactly as the
    corpus writes it, alif waṣla included; a caller wanting a display fold applies
    its own.
    """
    return _runtime().ayah_words


def initial_only_ayat() -> frozenset[tuple[int, int]]:
    """The āyāt made **entirely** of disconnected letters (muqaṭṭaʿāt).

    Every word tagged INL. An āya that merely opens with initials and continues
    with ordinary words (الر, المر, طس, ص, ق, ن) falls out with no special-casing.
    """
    return _runtime().initial_only_ayat


def root_spellings() -> tuple[str, ...]:
    """Every distinct `ROOT:` spelling in the corpus, in order of first appearance.

    **Raw** — the hamza seat is intact (`أمن`, `شيأ`, `لؤلؤ`). This module does not
    fold: folding is a text primitive and belongs to the caller, which is also the
    only party that can say what a collision under its own fold means.
    """
    return _runtime().root_spellings


@functools.lru_cache(maxsize=1)
def word_roots() -> dict[str, list[str]]:
    """`{"s:a:w": [root, …]}` in the file's own spelling, duplicates collapsed.

    Chain A of the root-resolution cascade. Its own pass, not part of the runtime
    bundle: ~77 000 keys that only the offline `root_resolver` stage ever reads.
    """
    out: dict[str, list[str]] = {}
    for rec in records():
        key = f"{rec.surah}:{rec.ayah}:{rec.word}"
        roots = out.setdefault(key, [])
        for match in _ROOT_FIELD_RE.finditer(rec.features):
            raw = match.group(1).strip()
            if raw and raw not in roots:
                roots.append(raw)
    return out
