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
# The only witness of the Islambouli table: the ORIGINAL poster image (1132×1646).
# A truncated first deposit was replaced by it before any row was transcribed.
ISLAMBOULI_POSTER_PNG = SOURCE / "islambouli_letters_poster.png"
# The two witnesses of Islambouli's cited root statements: video screenshots of
# the programme «مفاهيم» (ضرب: physical + cultural stage; كتب: labelled «مفهوم»),
# supplied by the user with no episode reference.
ISLAMBOULI_MAFAHIM_DRB_PNG = SOURCE / "islambouli_mafahim_drb.png"
ISLAMBOULI_MAFAHIM_KTB_PNG = SOURCE / "islambouli_mafahim_ktb.png"
QURAN_CHAKL_CSV = SOURCE / "quran_chakl.csv"
QAC_MORPHOLOGY_TXT = SOURCE / "quran-morphology.txt"
TREEBANK_CSV = SOURCE / "treebank" / "quranic-treebank.csv"
MAQAYIS_SOURCE_TXT = SOURCE / "maqayis" / "maqayis_shamela.txt"

# ── references: curated scholarship ───────────────────────────────────────
ROOT_ARBITRATION_JSON = REFERENCES / "root_arbitration.json"
MAQAYIS_ASL_CSV = REFERENCES / "maqayis_asl.csv"
ARABIC_LETTERS_CSV = REFERENCES / "arabic_letters_dataset.csv"
# The Lisan constrained-reading triple. `letter_senses.csv` is the sense sheet
# `arabic_letters_dataset.csv` no longer carries: a letter holds a BUNDLE of
# senses, and the phonetic sheet stays one row per letter beside it.
LETTER_SENSES_CSV = REFERENCES / "letter_senses.csv"
# The freeze on the sheet above: a version tag plus the sha256 of its bytes.
# Root curation runs against a FIXED letter dataset, so a root that matches
# nothing is a result to record rather than a reason to retouch a letter.
LETTER_SENSES_LOCK_JSON = REFERENCES / "letter_senses.lock.json"
# The physics-first concept engine's frozen input layer. The table maps the
# CLOSED ṣifāt feature vocabulary onto at most 15 primitives; the lock is its
# sha256, taken BEFORE the first root was composed. A root that reads badly is
# never a reason to edit the table — that is what the freeze is for.
PHYSICAL_PRIMITIVES_CSV = REFERENCES / "physical_primitives.csv"
PHYSICAL_PRIMITIVES_LOCK_JSON = REFERENCES / "physical_primitives.lock.json"
# The 40-root holdout k/40 is measured on, drawn with seed 20260925 before the
# table existed. Committed rather than left under `tests/`, which is git-ignored:
# a metric nobody cloning the repo can re-derive is not a published metric.
CONCEPT_WITNESS_SET_JSON = REFERENCES / "concept_witness_set.json"
# The SECOND holdout, for the Islambouli letter table: 40 roots drawn with seed
# 20260928 from the same frame minus the 40 above (whose uses have been read), and
# committed BEFORE a single row of that table was transcribed.
ISLAMBOULI_WITNESS_SET_JSON = REFERENCES / "islambouli_witness_set.json"
# The Islambouli confrontation record: per root of the second holdout, uses
# written BLIND to the table and frozen before any reading was generated, then
# per-use verdicts; `ضرب` carries its closed-run uses unchanged plus a blind copy
# (`uses_blind`) that calibrates the writer and counts in no k.
ISLAMBOULI_ATTESTATION_JSON = REFERENCES / "islambouli_attestation.json"
# Samer Islambouli's letter table, transcribed from the poster below and never
# curated: each row is the printed text, plus a copy of it that differs only in
# whitespace. `status` is `transcribed_from_poster` for every row, because no page
# of the book has been read.
ISLAMBOULI_LETTERS_CSV = REFERENCES / "islambouli_letters.csv"
# The system check of that table: each gloss decomposed into action / intensity /
# ending with the poster's own words, and the verdict (system / partial system /
# list) recomputed by the validator. An analysis, never an input: no module of the
# Islambouli engine may name it.
# The freeze on that table: version, sha256 of its bytes, and a sourced history
# whose first entry carries the witness digest and the poster's printed imprint.
ISLAMBOULI_LETTERS_LOCK_JSON = REFERENCES / "islambouli_letters.lock.json"
ISLAMBOULI_LETTERS_GRID_JSON = REFERENCES / "islambouli_letters_grid.json"
# The closed مصدر → وصف table the physical-stage assembly applies to position 2,
# admitted by ONE morphological criterion (one unvocalized spelling for both
# participles), and its lock — which also carries the segment notes, kept out of
# islambouli_letters.csv because that file's digest is cited by the measurement.
ISLAMBOULI_WASF_CSV = REFERENCES / "islambouli_wasf.csv"
ISLAMBOULI_WASF_LOCK_JSON = REFERENCES / "islambouli_wasf.lock.json"
# Statements Islambouli published for a root (physical / cultural stage), each
# transcribed from its witness image, and the lock on that file.
ISLAMBOULI_CITATIONS_JSON = REFERENCES / "islambouli_citations.json"
ISLAMBOULI_CITATIONS_LOCK_JSON = REFERENCES / "islambouli_citations.lock.json"
# The §D13 collision-probe record. Its `qualification` block is committed BEFORE
# a single concept is composed — that is what fixes the test's denominator before
# its numerator — and the `probe` block is appended only afterwards, carrying the
# digest of the qualification it ran against so a retro-edit is detectable.
CONCEPT_COLLISION_PROBE_JSON = REFERENCES / "concept_collision_probe.json"
# The confrontation record: per witness root, the Quranic uses frozen BEFORE its
# concept was generated, each with a gloss, a verse and a per-use verdict. The
# ORDER is the whole dataset — uses written after the sentence has been read
# shape themselves around it — so every record carries `uses_frozen_at` and
# `concept_recorded_at`, and the validator refuses to print k/40 when one root
# has them the wrong way round.
CONCEPT_ATTESTATION_JSON = REFERENCES / "concept_attestation.json"
ROOT_CORES_JSON = REFERENCES / "root_cores.json"
SEMANTIC_AXES_JSON = REFERENCES / "semantic_axes.json"
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
WORD_FUNCTION_JSON = DERIVED / "word_function.json"
WORD_PREFIXES_JSON = DERIVED / "word_prefixes.json"
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
