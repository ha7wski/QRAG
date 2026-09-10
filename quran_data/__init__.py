"""
quran_data — the single authority on every dataset this project reads.

Four modules, each with one job:

    paths.py      where every dataset lives; the only place a `data/` path is built
    corpus.py     the verse corpus, and the single Basmala choke point
    loaders.py    one lazy, process-cached loader per dataset
    qac.py        the one reader of `quran-morphology.txt`, which had four
    manifest.py   what each dataset is, where it came from, who reads it

**Importing this package opens no file.** Every loader is lazy, so a request that
touches one dataset never pays to parse another — the same discipline that keeps
a backend serving only the lexical paths holding no model memory, applied to data.

**Why `quran_data` and not `datasets`.** `pytest.ini` sets `pythonpath = .`, which
puts the repo root ahead of `site-packages`. A top-level `datasets/` package would
shadow HuggingFace's `datasets` — not installed today, but an optional dependency
of `transformers` and `sentence-transformers`, so a future upgrade would fail with
an import error pointing at neither package.

**This package imports nothing from the project.** It sits at the bottom of the
dependency order, so any layer may use it and it can never create a cycle.

Typical use:

    from quran_data import loaders
    roots = loaders.morphology()          # parsed once per process, shared

    from quran_data.paths import VERSES_FINAL_JSON   # writers need the path
"""
from __future__ import annotations

from quran_data import corpus, loaders, manifest, paths, qac
from quran_data.loaders import (
    DatasetMissing,
    alignment_overrides,
    arabic_letters,
    bab_contrast,
    lemma_index,
    letter_semantics,
    maqayis_asl,
    mizan_patterns,
    morphology,
    proper_nouns,
    qac_resolution,
    qac_syntax,
    qac_words,
    root_arbitration,
    root_graph,
    roots_resolved,
    sigha_dalala,
    translation_en,
    translation_fr,
    word_index,
)
from quran_data.corpus import (
    basmala_text,
    chakl_by_ref,
    load_verses,
    strip_leading_basmala,
    surah_basmala,
    verses_by_id,
)
from quran_data.paths import ROOT, app_db_path, qdrant_path, tahlil_coverage_path

__all__ = [
    "DatasetMissing",
    "ROOT",
    "alignment_overrides",
    "app_db_path",
    "arabic_letters",
    "bab_contrast",
    "basmala_text",
    "chakl_by_ref",
    "corpus",
    "lemma_index",
    "letter_semantics",
    "loaders",
    "manifest",
    "maqayis_asl",
    "mizan_patterns",
    "morphology",
    "paths",
    "proper_nouns",
    "qac",
    "qac_resolution",
    "qac_syntax",
    "qac_words",
    "qdrant_path",
    "root_arbitration",
    "root_graph",
    "roots_resolved",
    "load_verses",
    "sigha_dalala",
    "strip_leading_basmala",
    "surah_basmala",
    "tahlil_coverage_path",
    "translation_en",
    "translation_fr",
    "verses_by_id",
    "word_index",
]
