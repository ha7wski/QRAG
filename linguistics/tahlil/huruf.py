"""
huruf.py — Block 1 of Tahlil: the Hasan Abbas letters table, read through ONE loader.

Three problems this module exists to prevent, all of them silent:

**1. A dropped root letter.** The dataset keys hāʾ as `هـ` (U+0647 + U+0640 tatweel) while
every root key in the corpus uses the bare `ه`. Matching the raw keys therefore misses ه
entirely: measured over `root_graph.json`, 117 of 1 642 roots (4 698 of 49 967 rooted
words, 9.4 %) contain a letter that does not resolve. Nothing raises — the الحروف block
would just compose a three-letter root's core sense from two letters, and no coverage rate
can see it, because a two-of-three synthesis looks exactly like a complete one. The key
fold below is therefore **load-bearing, not cosmetic**, and `describe` **raises** on an
unresolvable letter rather than skipping it, so the truncation can only ever surface as a
failure.

This is the deliberate opposite of `lisan/letter_lexicon.py::describe`, which returns a
neutral placeholder for an unknown letter and never raises. That is right *there*: `/lexical`
renders a standalone per-letter reading, so a blank row is visibly blank and costs the reader
nothing. Here the per-letter دلالة is composed into one root-level synthesis, and a missing
letter does not leave a hole — it silently changes the claim. Loud beats lenient when the
output is a synthesis.

**2. A hamza radical read as الألف اللينة.** Worse than a dropped letter, because the block
looks complete. The processed corpus stores roots hamza-folded onto alif (`normalize_root`
folds أ إ آ ٱ → ا), so `qac_words` gives `امن`, `اله`, `شيا` and `root_display` is identical
to `root` for all 49 967 rooted words. `decompose` used to normalize its input and split
*that*, which meant the seat was already destroyed before the seat-fold below could ever
fire: **the fold was dead code on the real path**, alive only for a letter passed directly to
`describe`. The dataset holds **ء (الهمزة, p94-95)** and **ا (الألف اللينة, p96)** as two
distinct entries with distinct meanings and distinct page citations, so a folded root
attributed الألف's reading — *and الألف's page* — to a hamza radical: measured, 133 of the
1 642 corpus roots and 9 780 of the 49 967 rooted words (19.6 %), silently. Twice the hāʾ
truncation, same failure class.

`unfolded_root()` recovers the seat from the raw QAC source, whose `ROOT:` field preserves it
(`ROOT:أمن`, `ROOT:شيأ`). The recovery is deterministic: over all 1 651 raw roots the map
`normalize_root(raw) -> raw` has **zero collisions**, so nothing is guessed. **Removing the
resolver silently restores the 19.6 % corruption** — the block would still render, still cite
a page, and cite the wrong one; the corpus sweep in `tests/test_tahlil_huruf.py` pins the
count so the regression cannot pass unnoticed.

**3. A fact laundered into an interpretation (or the reverse).** `sifat` (مخرج, جهر/همس,
شدّة/رخاوة, إطباق/استعلاء, صفات مميّزة) is established tajwīd classification → badge محقّق.
`dalala` (Hasan Abbas's reading, with the page it came from) is a contested theoretical
framework → badge تأويلي, **never** محقّق. They are returned as two disjoint dicts, each with
its badge label attached (design decision 3b), precisely so no downstream code can flatten
them into one sentence by accident and let the fact lend its authority to the reading.

The disclaimer the UI shows is **this module's own, in Arabic**. The dataset's `honesty_flags`
and part of its `source` block are written in French; rendering them would break the
Arabic-only rule and trip the Latin-purity gate that voids a block. The raw dataset meta stays
available for auditing under `source_meta()[AUDIT_KEY]`, which is never rendered.

Root-related normalization goes through `arabic_text.normalize_root` (the
project-wide rule — `normalizer.normalize_text` deletes hamza and must never touch a root).
Pure stdlib + two on-disk files: no LLM, no network.
"""
from __future__ import annotations

import copy
import functools
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linguistics.analysis.qlisan_data import canonical_root, root_graph
from arabic_text import normalize_root
from quran_data import loaders, paths, qac

# The single source of truth. The byte-identical `data/derived/` copy was deleted with
# this change: two copies of a table are a future divergence, and the divergence would be
# invisible (both parse, both look complete).
#
# It stays a module-level name rather than a call into the registry at each use because it
# is also this module's INJECTION POINT: a caller (the suite, exercising the validation)
# rebinds it to a synthetic dataset. `_dataset()` honours that rebinding; when it still
# names the shipped file, the bytes come from the registry's shared loader.
LETTERS_PATH = paths.LETTER_SEMANTICS_JSON

# The only artifact in the repo that still carries the hamza SEAT of a root. The processed
# QAC artifacts do not (see docstring §2). Parsed by `quran_data.qac`, which serves every
# reader of the file from one pass; this module keeps the name for its error messages.
QAC_MORPHOLOGY_PATH = paths.QAC_MORPHOLOGY_TXT

# The shape of a `ROOT:` field in the QAC morphology. `quran_data.qac` now does the
# reading, so nothing here parses with it — it stays because it is this module's stated
# reading of the source, and the suite checks the registry's projection against it.
_ROOT_FIELD_RE = re.compile(r"ROOT:([^|\t\r\n]+)")

_TATWEEL = "ـ"  # U+0640 — decorative elongation; carries no phonetic identity.

# Hamza carriers → the bare `ء` entry, the same convention as
# `lisan/letter_lexicon.py::_HAMZA_SEATS`. This fold only ever fires on a root because
# `decompose` now resolves the root through `unfolded_root()` FIRST; on the normalized
# index key it is dead code (`normalize_root` has already folded أ إ آ ٱ → ا, ؤ → و, ئ → ي,
# and the dataset has its own `ا` / `و` / `ي` entries, distinct from `ء`).
_HAMZA_SEATS = {"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء", "آ": "ء", "ٱ": "ء"}

# Position labels, in root order. Displayed verbatim (Arabic is the display truth).
_FIRST, _MIDDLE, _LAST = "أول", "وسط", "آخر"

# The two returned structures are BUILT from these tuples — they are the single source of
# truth for the fact/interpretation split, not documentation of it.
_SIFAT_FIELDS = (
    "makhraj", "jahr_hams", "shidda_rakhawa", "itbaq", "istila", "sifat_mumayyiza",
)
_DALALA_FIELDS = ("core_meaning", "position_notes", "pages", "source_verified")

_BOOL_FIELDS = frozenset({"itbaq", "istila", "source_verified"})
_LIST_FIELDS = frozenset({"sifat_mumayyiza"})

# Per-row completeness, checked at load. `position_notes` is deliberately absent: د, ذ and ط
# legitimately carry none (see `has_position_notes`). `pages` is here because an empty page
# mints the well-formed-LOOKING citation `letter:س@p`, which resolves in the gate and cites
# nothing.
_REQUIRED_ROW_FIELDS = (
    "letter", "name", "sense_category", "makhraj", "jahr_hams", "shidda_rakhawa",
)
_REQUIRED_DALALA_FIELDS = ("core_meaning", "pages")

# --- badges (design.md decision 3b: labels are contract, not a UI choice) ------------
# `badge` is the provenance class the citation gate compares against; `label` is the exact
# display string. صفات is a corpus/tajwīd fact; دلالة is a contested framework and must never
# be confusable with it — different label TEXT, so the distinction survives greyscale.
#
# IMPORTED, never re-declared: `citations.py` owns the badge vocabulary because it is the
# module that ENFORCES it. A second literal copy here would be the same "two tables drift
# apart invisibly" failure this module's own loader exists to prevent — and it would drift
# in the worst possible direction, since a letter claim whose badge string stopped matching
# the gate's would be silently rejected as un-badged.
from linguistics.tahlil.citations import (  # noqa: E402  (placed with the constants it defines)
    BADGE_INTERPRETIVE as BADGE_DALALA,
    BADGE_VERIFIED as BADGE_SIFAT,
    BADGE_LABELS as _BADGE_LABELS,
)

BADGE_SIFAT_LABEL = _BADGE_LABELS[BADGE_SIFAT]
BADGE_DALALA_LABEL = _BADGE_LABELS[BADGE_DALALA]

# --- the module's OWN Arabic disclaimer (the dataset's is French — never rendered) ---
SOURCE_AR = {
    "author": "حسن عبّاس",
    "title": "خصائص الحروف العربية ومعانيها",
    "publisher": "اتحاد الكتّاب العرب — دمشق",
    "year": "1998",
    "scope": "الباب الثاني: معاني الحروف العربية على واقع المعاجم اللغوية (ص 53–229)",
}

DISCLAIMER_AR = (
    "الصفات الصوتية معطى محقّق من علم التجويد. "
    "أمّا الدلالة فمنقولة بأمانة عن حسن عبّاس مع رقم الصفحة، وهي إطار نظري مُختلَف فيه "
    "(مدرسة معاني الحروف)، تُعرَض بوسم «تأويلي» ولا تُوسَم «محقّق» أبداً، "
    "وتُعرض في سطر مستقل عن الصفات فلا تُدمج معها. "
    "ويجب التحقّق من خلاصة الجذر في ضوء الاستعمال القرآني (النظائر)."
)

# Everything under these keys of `source_meta()` is rendered on the page and is therefore
# Arabic-only by construction (module-owned strings). Everything else — notably AUDIT_KEY —
# is not renderable.
RENDERABLE_KEYS = ("source", "disclaimer", "badges")
AUDIT_KEY = "dataset_meta_raw"

# Roots whose seat could not be recovered, accumulated so the miss is observable (the
# coverage-log pattern) instead of silently passing through. Read via `unresolved_roots()`.
_UNRESOLVED_ROOTS: set[str] = set()


class NotARootError(ValueError):
    """`decompose()` was handed something that is not an attested corpus root.

    Distinct from the `KeyError` an unresolvable *letter* raises: this one means the input
    was a surface form (or a typo), and decomposing it would produce a plausible-looking
    letter reading of a word rather than of its root — exactly what the spec forbids
    («SHALL NOT decompose the surface form's letters as a substitute»).
    """


def _normalize_letter(letter: str) -> str:
    """Fold a single glyph to its dataset key: NFC, drop tatweel, seats → `ء`.

    Applied identically to the dataset keys (at load time) and to lookup input, so the
    `هـ` row and a bare `ه` query can never miss each other.
    """
    glyph = unicodedata.normalize("NFC", letter or "").replace(_TATWEEL, "").strip()
    return _HAMZA_SEATS.get(glyph, glyph)


def _coerce(field: str, value) -> object:
    """Normalize one dataset value to its declared type (and copy, never alias)."""
    if field in _BOOL_FIELDS:
        return bool(value)
    if field in _LIST_FIELDS:
        # Copied, not aliased: the cached row must stay pristine for the next caller.
        return list(value or [])
    return "" if value is None else str(value)


def _validate_row(row: dict) -> None:
    """Raise unless one dataset row carries every field the block cites. Names the letter.

    A partial row does not fail at render time — it renders *emptily*: a missing `pages`
    yields the citation `letter:س@p`, which is well-formed enough to pass a syntactic check
    and points at no page at all. Fail at load, where the offending letter can be named.
    """
    label = str(row.get("letter") or "؟")
    for field in _REQUIRED_ROW_FIELDS:
        if not str(row.get(field) or "").strip():
            raise ValueError(
                f"{LETTERS_PATH.name}: letter {label!r} is missing `{field}` — a partial "
                "row renders as a complete-looking block with an empty field."
            )
    dalala = row.get("dalala_hasan_abbas")
    if not isinstance(dalala, dict):
        raise ValueError(
            f"{LETTERS_PATH.name}: letter {label!r} has no `dalala_hasan_abbas` object."
        )
    for field in _REQUIRED_DALALA_FIELDS:
        if not str(dalala.get(field) or "").strip():
            raise ValueError(
                f"{LETTERS_PATH.name}: letter {label!r} is missing `dalala.{field}` — "
                "without it the block would mint the empty citation "
                f"'letter:{label}@p'."
            )
    if not isinstance(dalala.get("source_verified"), bool):
        raise ValueError(
            f"{LETTERS_PATH.name}: letter {label!r} has no boolean "
            "`dalala.source_verified` — an unverified transcription must be stated, "
            "not defaulted."
        )


def _read_dataset() -> dict:
    """The letters JSON, unvalidated.

    The shipped dataset comes from the registry's shared loader (one parse per process,
    one resident copy). A `LETTERS_PATH` pointing anywhere else is a caller's deliberate
    injection and is read directly — the registry serves the datasets the repo ships, it
    does not own an arbitrary file a caller hands this module.
    """
    if LETTERS_PATH == paths.LETTER_SEMANTICS_JSON:
        return loaders.letter_semantics()
    if not LETTERS_PATH.exists():
        raise FileNotFoundError(
            f"{LETTERS_PATH} not found — the Tahlil الحروف block cannot be assembled "
            "without the letters dataset."
        )
    with LETTERS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def _dataset() -> dict:
    """Parse the letters JSON once. Raises loudly on anything that would degrade quietly."""
    data = _read_dataset()

    meta = data.get("meta") or {}
    # The version participates in the Tahlil cache key (design §7): an unversioned table
    # would silently serve stale generated prose after an edit.
    if not meta.get("version"):
        raise ValueError(f"{LETTERS_PATH}: meta.version is required (cache-key field).")
    if not data.get("letters"):
        raise ValueError(f"{LETTERS_PATH}: no `letters` rows.")
    for row in data["letters"]:
        _validate_row(row)
    return data


@functools.lru_cache(maxsize=1)
def _by_letter() -> dict[str, dict]:
    """Lookup table keyed by the NORMALIZED glyph — the fold documented at module top."""
    table: dict[str, dict] = {}
    for row in _dataset()["letters"]:
        glyph = _normalize_letter(row.get("letter", ""))
        if not glyph:
            raise ValueError(f"{LETTERS_PATH}: a row has no `letter`.")
        # Two rows folding to one key would make the winner arbitrary (e.g. a future
        # bare `ه` row added beside `هـ`). Refuse rather than pick.
        if glyph in table:
            raise ValueError(
                f"{LETTERS_PATH}: duplicate letter key {glyph!r} after normalization."
            )
        table[glyph] = row
    return table


@functools.lru_cache(maxsize=1)
def _qac_root_map() -> dict[str, str]:
    """`normalize_root(raw) -> raw` over every `ROOT:` field of the raw QAC morphology.

    The one place the hamza seat of a root survives. The raw spellings come from
    `quran_data.qac.root_spellings()`, which hands them back with the seat intact and
    applies no fold of its own — folding is this module's decision, and so is what a
    collision under that fold *means*. Built once; raises on an ambiguous key rather than
    picking a winner — measured, the map is collision-free over all 1 651 raw roots, so an
    ambiguity means the source changed and the recovery stopped being deterministic.
    """
    if not QAC_MORPHOLOGY_PATH.exists():
        # The registry raises its own «obtain it upstream» error a moment later; this one
        # is kept because it names the CONSEQUENCE, which is the part a reader needs.
        raise FileNotFoundError(
            f"{QAC_MORPHOLOGY_PATH} not found — without it a hamza radical is read as "
            "الألف اللينة with the wrong page for 19.6 % of rooted words, silently."
        )
    mapping: dict[str, str] = {}
    for raw in qac.root_spellings():
        key = normalize_root(raw)
        seen = mapping.setdefault(key, raw)
        if seen != raw:
            raise ValueError(
                f"{QAC_MORPHOLOGY_PATH.name}: root key {key!r} is ambiguous — both "
                f"{seen!r} and {raw!r} fold onto it, so the seat cannot be recovered "
                "deterministically."
            )
    if not mapping:
        raise ValueError(f"{QAC_MORPHOLOGY_PATH}: no `ROOT:` field found.")
    return mapping


@functools.lru_cache(maxsize=None)
def unfolded_root(root: str) -> str:
    """Normalized/index root → the raw QAC root that still carries its hamza seat.

    `امن` → `أمن`, `شيا` → `شيأ`, `سرع` → `سرع` (nothing to recover). An input the QAC
    source does not know comes back **unchanged** — it is either already unfolded or not a
    QAC root — and is recorded in `unresolved_roots()` so the fallback is observable rather
    than silent (measured: 5 of the 1 642 corpus roots, which the treebank roots differently
    from the morphology file, e.g. `طمن` vs `ROOT:طمأن`).
    """
    key = normalize_root(root)
    raw = _qac_root_map().get(key)
    if raw is None:
        # Record ONLY genuine corpus roots. A caller-supplied non-root (a typo, or an
        # `allow_unattested=True` experiment) is not a coverage miss, and counting it here
        # would make the production coverage log over-report — the log would then blame the
        # corpus for what a caller did, which is the opposite of what it is read for.
        if canonical_root(key):
            _UNRESOLVED_ROOTS.add(key)
        return root
    return raw


def unresolved_roots() -> tuple[str, ...]:
    """Roots seen so far whose seat could not be recovered — for the coverage log."""
    return tuple(sorted(_UNRESOLVED_ROOTS))


def letters_version() -> str:
    """Dataset version (`meta.version`), a component of the Tahlil cache key."""
    return str(_dataset()["meta"]["version"])


def source_meta() -> dict:
    """Arabic source citation + Arabic framework disclaimer + the two badge labels.

    Everything under `RENDERABLE_KEYS` is **Arabic-only and owned by this module**: the
    dataset writes its `honesty_flags` and part of its `source` block in French, and a
    French string on the page both breaks the Arabic-only rule and trips the Latin-purity
    gate, which voids the whole block. The dataset's own meta is still returned verbatim
    under `AUDIT_KEY` — for auditing the transcription, never for rendering.
    """
    meta = _dataset()["meta"]
    return {
        "version": str(meta["version"]),
        "source": dict(SOURCE_AR),
        "disclaimer": DISCLAIMER_AR,
        "badges": {
            "sifat": {"badge": BADGE_SIFAT, "label": BADGE_SIFAT_LABEL},
            "dalala": {"badge": BADGE_DALALA, "label": BADGE_DALALA_LABEL},
        },
        # NOT renderable — French. Kept so the transcription can be audited against the
        # dataset's own honesty flags without opening the file.
        AUDIT_KEY: copy.deepcopy(meta),
    }


def describe(letter: str) -> dict:
    """Return one letter's fact row + interpretation row, or **raise**.

    RAISES `KeyError` when the glyph resolves to no dataset entry. Never returns a
    placeholder, never returns None — see the module docstring: a skipped letter would
    quietly compose a root's core sense from fewer letters than the root has.

    The returned `sifat` and `dalala` are disjoint dicts and must stay that way: the
    former is badged محقّق, the latter تأويلي, and `badges` carries both labels so no
    consumer has to re-derive the split.
    """
    glyph = _normalize_letter(letter)
    row = _by_letter().get(glyph)
    if row is None:
        raise KeyError(
            f"letter {letter!r} (normalized {glyph!r}) has no entry in {LETTERS_PATH.name}; "
            f"{len(_by_letter())} letters are known. Refusing to skip it — a dropped root "
            "letter corrupts the الحروف synthesis silently."
        )

    dalala_row = row.get("dalala_hasan_abbas") or {}
    dalala = {field: _coerce(field, dalala_row.get(field)) for field in _DALALA_FIELDS}
    return {
        "letter": glyph,
        "name": row.get("name", ""),
        "sense_category": row.get("sense_category", ""),
        # FACT — established phonetic/tajwīd classification. Badge محقّق.
        "sifat": {field: _coerce(field, row.get(field)) for field in _SIFAT_FIELDS},
        # INTERPRETATION — Hasan Abbas's framework, transcribed with its page. Badge تأويلي.
        "dalala": dalala,
        # Machine-readable provenance, so the محقّق/تأويلي split is read off the structure
        # instead of re-derived by every consumer (design decision 3b).
        "badges": {
            "sifat": {"badge": BADGE_SIFAT, "label": BADGE_SIFAT_LABEL},
            "dalala": {"badge": BADGE_DALALA, "label": BADGE_DALALA_LABEL},
        },
        # Position readings exist for most letters but not all (measured: د, ذ, ط carry
        # none). The flag exists so a caller states a position claim only where the
        # dataset has one, instead of generalizing a neighbour's.
        "has_position_notes": bool(dalala_row.get("position_notes")),
        # Minted HERE and copied verbatim by `evidence.py` (tasks 4.2). `<pages>` is a
        # page RANGE — every row of this dataset carries one, and the loader refuses a row
        # without it, so `letter:س@p` can never be minted.
        "cite_id": f"letter:{glyph}@p{dalala['pages']}",
    }


def decompose(root: str, *, allow_unattested: bool = False) -> list[dict]:
    """Decompose `root` into one `describe()` entry per letter, **in root order**.

    Each entry adds `index` (1-based) and `position` (أول / وسط / آخر) — the framework
    holds that a letter's دلالة shifts with its position, so the position must come from
    the actual slot, never be inferred.

    The input is normalized with `normalize_root` (the project-wide root rule) so a
    vocalized or tatweel-carrying root decomposes the same as its index key, then resolved
    through `unfolded_root()` so a hamza radical reaches the الهمزة entry instead of
    الألف اللينة (docstring §2).

    Raises:
      - `NotARootError` when the input is not a root of `root_graph()` — a surface form
        («الرحمن») must never be decomposed as a substitute for its root, and a rootless
        word is the caller's business: the block renders unavailable.
        `allow_unattested=True` is the deliberate escape hatch for a *legitimate* root that
        the Quran does not attest (a lexicon/KB root, a fixture): the caller then owns the
        claim that the string is a root, and the seat recovery may not apply to it.
      - `KeyError` (via `describe`) rather than returning a short list.
    """
    key = normalize_root(root)
    if not key:
        raise ValueError("decompose() needs a non-empty root (rootless words have no الحروف block).")
    # root_graph keys are the EXACT spelling now (`أمن`, not `امن`), so membership is
    # asked through canonical_root: it accepts any folded spelling a caller may hold
    # and answers with the stored one. That spelling already carries its hamza seat,
    # which is what `unfolded_root` had to reconstruct from the raw source before.
    canon = canonical_root(root) or canonical_root(key)
    if not allow_unattested and canon is None:
        raise NotARootError(
            f"{root!r} (normalized {key!r}) is not a root in root_graph.json — refusing to "
            "decompose a surface form as a substitute for its root. Pass "
            "allow_unattested=True only for a root you know is legitimate but unattested."
        )

    letters = list(canon or unfolded_root(key))
    last = len(letters) - 1
    out: list[dict] = []
    for i, ch in enumerate(letters):
        entry = describe(ch)
        # A 2-letter root has a first and a last and no middle; a 1-letter root is its
        # own first.
        entry["index"] = i + 1
        entry["position"] = _FIRST if i == 0 else (_LAST if i == last else _MIDDLE)
        out.append(entry)
    return out


def letter_count() -> int:
    """Number of dataset entries (29 = 28 letters + الهمزة)."""
    return len(_by_letter())


if __name__ == "__main__":
    print(f"letters: {letter_count()}  ·  version {letters_version()}")
    src = source_meta()["source"]
    print(f"source : {src['author']} — {src['title']} ({src['year']})")
    # pinned word · hāʾ path (the key fold) · hamza-seat path (the unfolding resolver)
    for r in ("سرع", "فهم", "امن", "شيا"):
        print(f"\n{r} → {unfolded_root(r)}:")
        for e in decompose(r):
            notes = "position-notes" if e["has_position_notes"] else "NO position-notes"
            print(
                f"  {e['index']}. {e['letter']} ({e['name']}) [{e['position']}] "
                f"{e['sifat']['jahr_hams']}/{e['sifat']['shidda_rakhawa']} "
                f"{e['sifat']['sifat_mumayyiza']}  {notes}  {e['cite_id']}"
            )
    print("\nhamza seat أ →", describe("أ")["letter"], "·", describe("أ")["cite_id"])
    print("unresolved roots so far:", unresolved_roots())
    try:
        describe("x")
    except KeyError as exc:
        print("unresolvable letter raises:", str(exc)[:70], "…")
    try:
        decompose("الرحمن")
    except NotARootError as exc:
        print("surface form raises  :", str(exc)[:70], "…")
