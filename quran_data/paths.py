"""
paths.py — the only place in the repo that knows where a dataset lives.

Every dataset is a named constant here. No other module builds a path into
`data/` by hand: before this package there were ~20 modules each recomputing
`ROOT / "data" / ...`, so relocating one file meant a repo-wide sweep and
`mizan_patterns.json` had drifted out of `data/` altogether without anyone
noticing.

Paths stay anchored on `ROOT = Path(__file__).resolve().parents[N]`, the
project convention, so every module runs from any working directory.

Three datasets accept an environment override. Those are **functions**, not
constants, because the override must be read when the caller asks — a constant
frozen at import time cannot be monkeypatched by a test and cannot see a
variable exported after the module loaded. The default location is still a
constant, so the manifest has something to name.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"

# Buckets. `data/` is organized by what a file *is*, not by which pipeline stage
# happened to write it:
#   SOURCE      third-party originals the project never rewrites
#   REFERENCES  curated scholarship carrying a human decision
#   DERIVED     anything a script can rebuild
#   RUNTIME     mutable state the running app owns
#
# `references/` and `runtime/` keep their exact paths: the first already says what
# it holds, and the second keeps `QDRANT_PATH=data/runtime/qdrant` and `APP_DB_PATH`
# valid in every developer's `.env`, so nobody has to touch their environment and
# the embedded Qdrant collection is never relocated under its own exclusive lock.
# Only `raw/` -> `source/` ("raw" read as pipeline stage zero, when the point is
# "not ours, never rewritten"), `processed/` -> `derived/`, and `translations/`
# into `derived/` actually moved.
SOURCE = DATA / "source"
REFERENCES = DATA / "references"
DERIVED = DATA / "derived"
RUNTIME = DATA / "runtime"
TRANSLATIONS = DERIVED / "translations"

# ── source: third-party originals ─────────────────────────────────────────
QURAN_CSV = SOURCE / "quran.csv"
QURAN_CHAKL_CSV = SOURCE / "quran_chakl.csv"
QAC_MORPHOLOGY_TXT = SOURCE / "quran-morphology.txt"
TREEBANK_CSV = SOURCE / "treebank" / "quranic-treebank.csv"
MAQAYIS_SOURCE_TXT = SOURCE / "maqayis" / "maqayis_shamela.txt"

# ── references: curated scholarship ───────────────────────────────────────
ROOT_ARBITRATION_JSON = REFERENCES / "root_arbitration.json"
MAQAYIS_ASL_CSV = REFERENCES / "maqayis_asl.csv"
ARABIC_LETTERS_CSV = REFERENCES / "arabic_letters_dataset.csv"
LETTER_SEMANTICS_JSON = REFERENCES / "arabic_letter_semantics_hasan_abbas.json"
BAB_CONTRAST_JSON = REFERENCES / "bab_contrast.json"
SIGHA_DALALA_JSON = REFERENCES / "sigha_dalala.json"
# The one dataset that lived outside `data/` entirely, in `analysis/data/`.
MIZAN_PATTERNS_JSON = REFERENCES / "mizan_patterns.json"

# ── derived: everything a script rebuilds ─────────────────────────────────
VERSES_RAW_JSON = DERIVED / "verses_raw.json"
VERSES_ENRICHED_JSON = DERIVED / "verses_enriched.json"
VERSES_FINAL_JSON = DERIVED / "verses_final.json"
MORPHOLOGY_JSON = DERIVED / "morphology.json"
QAC_RESOLUTION_JSON = DERIVED / "qac_resolution.json"
LEMMA_INDEX_JSON = DERIVED / "lemma_index.json"
PROPER_NOUNS_JSON = DERIVED / "proper_nouns.json"
ROOTS_RESOLVED_JSON = DERIVED / "roots_resolved.json"
QAC_WORDS_JSON = DERIVED / "qac_words.json"
QAC_SYNTAX_JSON = DERIVED / "qac_syntax.json"
ROOT_GRAPH_JSON = DERIVED / "root_graph.json"
WORD_INDEX_JSON = DERIVED / "word_index.json"
OVERRIDES_JSON = DERIVED / "overrides.json"
QLISAN_ALIGNMENT_AUDIT_JSON = DERIVED / "qlisan_alignment_audit.json"
BM25_INDEX_PKL = DERIVED / "bm25_index.pkl"
# Not a dataset — the resumable marker `build_index.py` writes so an interrupted
# embedding run picks up where it stopped. It lives with what it tracks.
BUILD_INDEX_CHECKPOINT = DERIVED / ".checkpoint"

TRANSLATION_FR_JSON = TRANSLATIONS / "fr_hamidullah.json"
TRANSLATION_EN_JSON = TRANSLATIONS / "en_sahih.json"

# ── runtime: mutable state, each with an environment override ─────────────
DEFAULT_APP_DB = RUNTIME / "app.db"
DEFAULT_QDRANT_DIR = RUNTIME / "qdrant"
DEFAULT_TAHLIL_COVERAGE_TSV = RUNTIME / "tahlil_coverage.tsv"


def _anchored(raw: str | os.PathLike[str]) -> Path:
    """Resolve a possibly-relative override against ROOT, never the cwd.

    The project convention everywhere else: the backend and the indexer must
    agree on a directory no matter where either was launched from. An absolute
    path is taken as given.
    """
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def app_db_path() -> Path:
    """Where the SQLite store lives. `APP_DB_PATH` overrides the default."""
    raw = os.getenv("APP_DB_PATH")
    return _anchored(raw) if raw else DEFAULT_APP_DB


def qdrant_path() -> Path | None:
    """The embedded-Qdrant directory, or None to use a server at `QDRANT_URL`.

    An **empty** `QDRANT_PATH` reads as unset — that is the documented way to
    ask for server mode, and `.env.example` ships it empty. Returning a Path for
    `""` would silently open an embedded store in the repo root.

    Returns None when the variable is absent or empty; the caller then falls
    back to `QDRANT_URL`. This mirrors `QdrantStore.__init__` exactly, which is
    the point: the rule now has one home instead of being re-derived there.
    """
    raw = os.getenv("QDRANT_PATH")
    return _anchored(raw) if raw else None


def tahlil_coverage_path() -> Path:
    """The Tahlīl coverage log. `TAHLIL_COVERAGE_LOG` overrides the default.

    The override is what keeps a test run off the real runtime file.
    """
    raw = os.getenv("TAHLIL_COVERAGE_LOG")
    return _anchored(raw) if raw else DEFAULT_TAHLIL_COVERAGE_TSV
