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
def word_function() -> dict:
    """`{"s:a:w": "أداة نداء" | "أداة استفهام" | "أداة شرط"}`.

    Only the words that ARE a tool are listed — absence means the word carries its
    own meaning, which is the overwhelming majority (297 of 50 342 are tools).
    """
    return _json("WORD_FUNCTION_JSON")


@functools.lru_cache(maxsize=1)
def word_prefixes() -> dict:
    """`{"s:a:w": "وَبِ"}` — the proclitics QAC declares, joined, in reading order.

    Only the 26 001 words that HAVE one are listed; absence means the word opens
    on its stem. An extract of `qac_words()`'s `segments_detail`, so that reading
    a word's proclitics costs 0.5 MB instead of that index's 248 MB resident.
    """
    return _json("WORD_PREFIXES_JSON")


@functools.lru_cache(maxsize=1)
def alignment_overrides() -> dict:
    """The 6 hand-resolved alignment cases the treebank build reads back."""
    return _json("OVERRIDES_JSON")


# ── offline similarity ────────────────────────────────────────────────────

SURAH_SIMILARITY_SCHEMA = 1


class UnknownSchema(ValueError):
    """A dataset written under a schema version this code does not read."""


@functools.lru_cache(maxsize=1)
def surah_similarity() -> dict:
    """The intra-surah similarity lookup (design D10, schema 1).

    `{"schema": 1, "build": {...}, "surahs": {"<n>": {"unscored": [int],
    "groups": [{"ayahs", "strength"}], "neighbours": {"<ayah>": [{"a", "s",
    "sem", "syn", "ce", "dense", "cov", "roots"}]}}}}`.

    Refuses a file whose `schema` it does not know, with the rebuild command:
    a reader that guessed at a newer layout would serve a wrong answer rather
    than no answer.
    """
    data = _json("SURAH_SIMILARITY_JSON")
    found = data.get("schema") if isinstance(data, dict) else None
    if found != SURAH_SIMILARITY_SCHEMA:
        raise UnknownSchema(
            f"SURAH_SIMILARITY_JSON ({paths.SURAH_SIMILARITY_JSON}) has schema "
            f"{found!r}, expected {SURAH_SIMILARITY_SCHEMA}. Rebuild it with:\n"
            f"    {MANIFEST['SURAH_SIMILARITY_JSON'].rebuild}"
        )
    return data


QURAN_SIMILARITY_SCHEMA = 1


@functools.lru_cache(maxsize=1)
def quran_similarity() -> dict:
    """The cross-surah similarity lookup (design D7, schema 1).

    `{"schema": 1, "build": {...}, "unscored": ["<s:a>"], "neighbours":
    {"<s:a>": [{"r", "s", "sem", "syn", "ce", "dense", "cov", "roots"}]}}`,
    a neighbour possibly carrying `"verbatim": true`.

    A separate file from `surah_similarity()` so a missing cross-surah build
    leaves the intra-surah view answering. Same schema refusal, same reason.
    """
    data = _json("QURAN_SIMILARITY_JSON")
    found = data.get("schema") if isinstance(data, dict) else None
    if found != QURAN_SIMILARITY_SCHEMA:
        raise UnknownSchema(
            f"QURAN_SIMILARITY_JSON ({paths.QURAN_SIMILARITY_JSON}) has schema "
            f"{found!r}, expected {QURAN_SIMILARITY_SCHEMA}. Rebuild it with:\n"
            f"    {MANIFEST['QURAN_SIMILARITY_JSON'].rebuild}"
        )
    return data


QURAN_PASSAGES_SCHEMA = 1


@functools.lru_cache(maxsize=1)
def quran_passages() -> dict:
    """The cross-surah shared passages (add-shared-passages design D5, schema 1).

    `{"schema": 1, "build": {...}, "passages": [{"a": "<s:a>", "b": "<s:a>",
    "wa": [i1, i2], "wb": [j1, j2], "k": int, "roots": [str]}]}`, `a` in the
    lower surah, sorted by `(a, b)`; word spans are 1-based and inclusive.

    A separate file from `quran_similarity()`: the two relations fail apart.
    Same schema refusal, same reason.
    """
    data = _json("QURAN_PASSAGES_JSON")
    found = data.get("schema") if isinstance(data, dict) else None
    if found != QURAN_PASSAGES_SCHEMA:
        raise UnknownSchema(
            f"QURAN_PASSAGES_JSON ({paths.QURAN_PASSAGES_JSON}) has schema "
            f"{found!r}, expected {QURAN_PASSAGES_SCHEMA}. Rebuild it with:\n"
            f"    {MANIFEST['QURAN_PASSAGES_JSON'].rebuild}"
        )
    return data


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
    """28 base letters: identity and phonetics (makhraj, ṣifāt, Ibn Jinnī note).

    Carries no meaning any more — a letter holds a bundle of senses, which lives
    in `letter_senses()` one row per (letter, sense).
    """
    return _csv_rows("ARABIC_LETTERS_CSV")


@functools.lru_cache(maxsize=1)
def letter_senses() -> list[dict]:
    """One row per (letter, sense): gloss, pole, axes, position, source, page.

    Returned raw and UNRANKED, in declaration order. Choosing among a letter's
    senses needs a root's attested core, which no loader knows.
    """
    return _csv_rows("LETTER_SENSES_CSV")


@functools.lru_cache(maxsize=1)
def letter_senses_lock() -> dict:
    """The freeze on `letter_senses.csv`: version, sha256 of its bytes, history.

    Read as data, never enforced here — `scripts/validate_lisan_datasets.py`
    recomputes the digest and fails when the sheet moved without the version
    being bumped. A loader that raised on a stale digest would make every Lisan
    request depend on a curation rule.
    """
    return _json("LETTER_SENSES_LOCK_JSON")


@functools.lru_cache(maxsize=1)
def physical_primitives() -> list[dict]:
    """One row per (physical feature, primitive) for the physics-first engine.

    Keyed on the ṣifāt feature vocabulary ALONE — no root, no root key, and no
    per-root exception, by construction. Every row carries a `status`:
    `attested` names an authority and real pages, `hypothesis` owns the claim
    and carries the uncontested tajwīd definition as its `physical_basis`.

    Returned raw and in declaration order: that order is the documented
    tie-break when two primitives of a letter share a letter-coverage count.
    """
    return _csv_rows("PHYSICAL_PRIMITIVES_CSV")


@functools.lru_cache(maxsize=1)
def physical_primitives_lock() -> dict:
    """The freeze on `physical_primitives.csv`: version, sha256, history.

    Read as data, never enforced here — the same rule `letter_senses_lock()`
    follows. `scripts/validate_concept_datasets.py` recomputes the digest; a
    loader that raised on a stale one would make every concept request depend
    on a curation rule.
    """
    return _json("PHYSICAL_PRIMITIVES_LOCK_JSON")


@functools.lru_cache(maxsize=1)
def concept_collision_probe() -> dict:
    """The §D13 gate record: the qualification table, then the probe verdict.

    Two blocks written at two different moments on purpose. `qualification`
    fixes which comparisons the probe is entitled to make, and is committed
    before any concept exists; `probe` is appended after. Reading them back in
    one document is convenient — writing them in one sitting would destroy the
    only property the file has.
    """
    return _json("CONCEPT_COLLISION_PROBE_JSON")


@functools.lru_cache(maxsize=1)
def concept_witness_set() -> dict:
    """The 40-root frozen holdout, its frame, strata, seed and draw procedure.

    The identity of the roots is public — a holdout can only be held out if it
    is known. What the file exists to make impossible is a set quietly re-rolled
    after the fact: `tests/test_concept_witness_set.py` replays the draw.
    """
    return _json("CONCEPT_WITNESS_SET_JSON")


@functools.lru_cache(maxsize=1)
def islambouli_letters() -> list[dict]:
    """Samer Islambouli's letter table as transcribed, 29 rows in poster order."""
    return _csv_rows("ISLAMBOULI_LETTERS_CSV")


@functools.lru_cache(maxsize=1)
def islambouli_letters_lock() -> dict:
    """The freeze on the Islambouli table — digest, version, sourced history."""
    return _json("ISLAMBOULI_LETTERS_LOCK_JSON")


@functools.lru_cache(maxsize=1)
def islambouli_letters_grid() -> dict:
    """The system check of the Islambouli table. Read by the validator only."""
    return _json("ISLAMBOULI_LETTERS_GRID_JSON")


@functools.lru_cache(maxsize=1)
def islambouli_wasf() -> list[dict]:
    """The closed مصدر → وصف table of the physical-stage assembly."""
    return _csv_rows("ISLAMBOULI_WASF_CSV")


@functools.lru_cache(maxsize=1)
def islambouli_wasf_lock() -> dict:
    """The freeze on the وصف table, with the assembly's segment notes."""
    return _json("ISLAMBOULI_WASF_LOCK_JSON")


@functools.lru_cache(maxsize=1)
def islambouli_citations() -> dict:
    """Islambouli's published root statements, each with its witness."""
    return _json("ISLAMBOULI_CITATIONS_JSON")


@functools.lru_cache(maxsize=1)
def islambouli_citations_lock() -> dict:
    """The freeze on the citations file."""
    return _json("ISLAMBOULI_CITATIONS_LOCK_JSON")


@functools.lru_cache(maxsize=1)
def islambouli_attestation() -> dict:
    """The Islambouli confrontation record — uses, then verdicts."""
    return _json("ISLAMBOULI_ATTESTATION_JSON")


@functools.lru_cache(maxsize=1)
def islambouli_witness_set() -> dict:
    """The second 40-root holdout, for the Islambouli letter table.

    Replayed from its own seed by `scripts/validate_islambouli_datasets.py`, which
    also checks that the first draw still reproduces.
    """
    return _json("ISLAMBOULI_WITNESS_SET_JSON")


@functools.lru_cache(maxsize=1)
def concept_attestation() -> dict:
    """The frozen expectation k/40 is judged against, root by root.

    `{"meta": {...}, "roots": {root: {uses_frozen_at, concept_recorded_at,
    uses: [{gloss, verse, verdict, reason}]}}}`. Returned raw; the caller
    validates. A root whose `uses[]` is absent is NOT a root that passed — it is
    a root nobody has judged, and `confront.verdict_for` reads it as
    `not_recorded` rather than letting an empty list read as full coverage.

    The file ships as a skeleton with `roots` empty: the records are written one
    at a time, each committed before that root's concept is generated, which is
    the only property the dataset has.
    """
    return _json("CONCEPT_ATTESTATION_JSON")


@functools.lru_cache(maxsize=1)
def root_cores() -> dict:
    """Curated attested semantic cores per canonical QAC root key (Ibn Fāris).

    `{"meta": {...}, "roots": {root: [core, ...]}}`. Returned raw; the caller
    validates. A root may hold several cores and they are never merged.
    """
    return _json("ROOT_CORES_JSON")


@functools.lru_cache(maxsize=1)
def semantic_axes() -> dict:
    """The CLOSED axis vocabulary both Lisan datasets tag against.

    `{"meta": {...}, "axes": [{"id", "label_ar", "antonym"?}, ...]}`. Closed
    because selection is a set intersection: with free-text axes, agreement
    would be an accident of wording.
    """
    return _json("SEMANTIC_AXES_JSON")


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
