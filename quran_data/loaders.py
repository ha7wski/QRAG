"""
loaders.py — one loader per dataset, each parsing its file once per process.

The pattern `quran_data/corpus.py` established for the verse corpus, extended to
every dataset: a cached function returns a shared object, so a file needed by
three components in the same backend is not held three times over.

**Read-only contract.** Callers must not mutate what they get back — everyone
shares it. Need a different shape? Build one from the returned object.

**Lazy.** Importing `quran_data` opens nothing. A request that touches one
dataset never pays to parse another. This mirrors the lazy-model discipline the
backend already relies on: a backend serving only the lexical paths holds no
model memory, and now no unnecessary dataset either.

**Errors say what to do.** A missing file is reported with its dataset name, its
path, and either the exact rebuild command or the upstream source it must be
obtained from — read straight out of `manifest.py`, so the advice cannot drift
away from the provenance record.
"""
from __future__ import annotations

import csv
import functools
import json
from pathlib import Path

from quran_data import paths
from quran_data.manifest import MANIFEST


class DatasetMissing(FileNotFoundError):
    """A dataset is absent, with the concrete next step in its message."""


def _require(constant: str) -> Path:
    """Resolve a dataset constant to a present file, or raise with instructions."""
    path: Path = getattr(paths, constant)
    if path.exists():
        return path
    entry = MANIFEST.get(constant)
    if entry is None:  # pragma: no cover - the coverage test forbids this
        raise DatasetMissing(f"{constant} ({path}) is missing and has no manifest entry.")
    if entry.regenerable and entry.rebuild:
        advice = f"Rebuild it with:\n    {entry.rebuild}"
    else:
        advice = (
            "It cannot be rebuilt — it is not a build artefact. Obtain it from:\n"
            f"    {entry.origin}"
        )
    raise DatasetMissing(
        f"{constant} not found at {path}\n"
        f"  What it is: {entry.what}\n"
        f"  {advice}"
    )


def _json(constant: str):
    with _require(constant).open(encoding="utf-8") as fh:
        return json.load(fh)


def _csv_rows(constant: str) -> list[dict]:
    # utf-8-sig: tolerate a BOM on the header row.
    with _require(constant).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# ── chain A: from the QAC morphology source ───────────────────────────────

@functools.lru_cache(maxsize=1)
def morphology() -> dict:
    """`{root: {root, forms, verses, count}}` — the root index, VERSE granularity."""
    return _json("MORPHOLOGY_JSON")


@functools.lru_cache(maxsize=1)
def qac_resolution() -> dict:
    """`{form_to_roots, lem_to_roots}` — resolves a typed word to its root(s)."""
    return _json("QAC_RESOLUTION_JSON")


@functools.lru_cache(maxsize=1)
def lemma_index() -> dict:
    """`{root: [lemma, …]}`, dominant sense first."""
    return _json("LEMMA_INDEX_JSON")


@functools.lru_cache(maxsize=1)
def proper_nouns() -> dict:
    """Search-normalized lemma → proper-noun record, for the 62 rootless names."""
    return _json("PROPER_NOUNS_JSON")


@functools.lru_cache(maxsize=1)
def roots_resolved() -> dict:
    """`{"s:a:w": {primary, alternates, rule}}` — the arbitrated root of every word."""
    return _json("ROOTS_RESOLVED_JSON")


# ── chain B: from the dependency treebank ─────────────────────────────────

@functools.lru_cache(maxsize=1)
def qac_words() -> dict:
    """`{"s:a:w": morphology}` — root, lemma, POS, features, segments (29 MB)."""
    return _json("QAC_WORDS_JSON")


@functools.lru_cache(maxsize=1)
def qac_syntax() -> dict:
    """`{"s:a:w": dependency role}`. Words with no usable relation are ABSENT."""
    return _json("QAC_SYNTAX_JSON")


@functools.lru_cache(maxsize=1)
def root_graph() -> dict:
    """`{normalized_root: ["s:a:w", …]}` — occurrences at WORD granularity."""
    return _json("ROOT_GRAPH_JSON")


@functools.lru_cache(maxsize=1)
def word_index() -> dict:
    """The alignment spine: `{"s:a:w": {uthmani, imlaai, chakl_char_start/end}}`.

    Character offsets are computed against the **Basmala-inclusive** chakl rows.
    Anything that strips the Basmala before slicing by them returns the wrong word.
    """
    return _json("WORD_INDEX_JSON")


@functools.lru_cache(maxsize=1)
def alignment_overrides() -> dict:
    """The 6 hand-resolved alignment cases the treebank build reads back."""
    return _json("OVERRIDES_JSON")


# ── references: curated scholarship ───────────────────────────────────────

@functools.lru_cache(maxsize=1)
def root_arbitration() -> dict:
    """The recorded root verdicts, each with its deciding rule and authority."""
    return _json("ROOT_ARBITRATION_JSON")


@functools.lru_cache(maxsize=1)
def sigha_dalala() -> dict:
    """27 ṣīgha → possible senses. Returned raw; the caller validates."""
    return _json("SIGHA_DALALA_JSON")


@functools.lru_cache(maxsize=1)
def bab_contrast() -> dict:
    """11 bāb contrasts, verbs only. Returned raw; the caller validates."""
    return _json("BAB_CONTRAST_JSON")


@functools.lru_cache(maxsize=1)
def letter_semantics() -> dict:
    """Ḥasan ʿAbbās's per-letter dalāla with page citations, plus phonetic ṣifāt.

    Holds ء and ا as two distinct entries with distinct pages — the reason a
    hamza seat must survive root folding.
    """
    return _json("LETTER_SEMANTICS_JSON")


@functools.lru_cache(maxsize=1)
def arabic_letters() -> list[dict]:
    """28 base letters: makhraj, ṣifāt, ʿAbbās meaning, Ibn Jinnī note."""
    return _csv_rows("ARABIC_LETTERS_CSV")


@functools.lru_cache(maxsize=1)
def mizan_patterns() -> dict:
    """Curated awzān and broken-plural special cases for the mīzān."""
    return _json("MIZAN_PATTERNS_JSON")


@functools.lru_cache(maxsize=1)
def maqayis_asl() -> list[dict]:
    """4662 roots → Ibn Fāris's aṣl, as CSV rows."""
    return _csv_rows("MAQAYIS_ASL_CSV")


# ── translations ──────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def translation_fr() -> dict:
    """6236 French translations (Hamidullah)."""
    return _json("TRANSLATION_FR_JSON")


@functools.lru_cache(maxsize=1)
def translation_en() -> dict:
    """6236 English translations (Sahih International)."""
    return _json("TRANSLATION_EN_JSON")
