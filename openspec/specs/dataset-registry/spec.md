# dataset-registry Specification

## Purpose

Define where every dataset lives, who may open one, and how a reader tells what is safe to
delete.

The rule needs stating because the alternative had already happened: ~20 modules each recomputed
`ROOT / "data" / ...` by hand, `quran-morphology.txt` had four independent readers, one dataset had
drifted out of `data/` altogether, and provenance was spread across three documents that only
partly agreed. None of it was broken — it was simply unanswerable. This capability makes the
`data/` tree state each file's nature rather than its history, gives paths and loaders one home,
and puts provenance in a machine-readable manifest that a test keeps honest.

## Requirements

### Requirement: `data/` is organized by the nature of each file, not by history

The `data/` tree SHALL have exactly four top-level buckets, each defined by what the files in it
*are* — not by which pipeline stage happened to write them:

| Bucket | Contents | Committed | Regenerable |
|---|---|---|---|
| `data/source/` | Third-party originals the project never rewrites: `quran.csv`, `quran_chakl.csv`, `quran-morphology.txt`, `treebank/quranic-treebank.csv`, and the git-ignored `maqayis/` download | yes, except `maqayis/` | no — re-obtainable only from upstream |
| `data/references/` | Curated scholarship carrying a human decision: `root_arbitration.json`, `maqayis_asl.csv`, `arabic_letters_dataset.csv`, `arabic_letter_semantics_hasan_abbas.json`, `bab_contrast.json`, `sigha_dalala.json`, and the incoming `mizan_patterns.json` | yes | no — regenerating one would discard the arbitration |
| `data/derived/` | Everything a script can rebuild: the pipeline's `verses_*.json`, `morphology.json`, `qac_*.json`, `word_index.json`, `root_graph.json`, `lemma_index.json`, `proper_nouns.json`, `roots_resolved.json`, `bm25_index.pkl`, and the fetched `translations/` | no | yes |
| `data/runtime/` | Mutable state the running app owns: `app.db`, `qdrant/`, `tahlil_coverage.tsv` | no | yes (as empty state) |

This replaces the `raw/` + `processed/` + `references/` + `translations/` + `runtime/` split, in which
`raw/` mixed committed originals with a git-ignored download directory, `references/` mixed curated
datasets with a PDF pitch deck, and `translations/` was a top-level bucket for two regenerable files.

`data/references/` and `data/runtime/` keep their exact current paths — renaming a bucket whose meaning
is already right would move tracked files for no gain. Only `raw/` → `source/` (the name `raw` reads as
"pipeline stage zero" when the point is "not ours, never rewritten"), `processed/` → `derived/`, and
`translations/` → `derived/translations/` actually move.

`.gitignore` SHALL express the rule in three entries — `data/derived/`, `data/runtime/`,
`data/source/maqayis/` — instead of five scattered ones with a `.gitkeep` exception. `maqayis/` is the
one documented departure from its bucket's committed-ness: it is a large re-downloadable original
(`build_maqayis_dataset.py --fetch`) whose curated derivative `maqayis_asl.csv` is what the repo ships.

#### Scenario: A reader can tell what is safe to delete

- **WHEN** a developer needs to reclaim disk space or resolve a corrupt artefact
- **THEN** deleting `data/derived/` and `data/runtime/` in full SHALL be safe and recoverable by
  running the documented rebuild steps
- **AND** no file under `data/source/` or `data/references/` SHALL be reproducible by any script in the
  repo, so nothing in those two buckets is ever a rebuild target

#### Scenario: The stray dataset comes home

- **WHEN** `mizan_patterns.json` is loaded
- **THEN** it SHALL be read from `data/references/mizan_patterns.json`
- **AND** the directory `analysis/data/` SHALL NOT exist

#### Scenario: Committed files nothing reads are dropped

- **WHEN** the change is complete
- **THEN** `data/source/treebank/` SHALL contain only `quranic-treebank.csv`
- **AND** `Quran.csv`, `Quranic.rar`, `RelLabels.csv`, `pos.csv` and
  `zero_theory_pitch_deck.pdf` SHALL no longer be tracked
- **AND** the manifest entry for the treebank SHALL name the upstream archive those files came from,
  so provenance survives their removal

### Requirement: One module is the only authority on dataset paths

A package `quran_data/` SHALL declare every dataset path as a named constant, and no other module
SHALL construct a path into `data/` by hand. The ~20 modules that today each recompute
`ROOT / "data" / ...` (`indexing/corpus.py`, `indexing/bm25_index.py`, `indexing/build_index.py`,
`retrieval/lexical_retriever.py`, `retrieval/verse_lookup.py`, `ingestion/*`, `analysis/qlisan_data.py`,
`analysis/mizan.py`, `analysis/fassila.py`, `tahlil/huruf.py`, `tahlil/form_kb.py`, `tahlil/coverage.py`,
`lisan/letter_lexicon.py`, `madar/maqayis_store.py`, `api/store.py`, `scripts/*`) SHALL import the
constant instead.

The package is named `quran_data`, **not** `datasets`: `pytest.ini` sets `pythonpath = .`, which puts
the repo root ahead of `site-packages`, so a top-level `datasets/` package would shadow HuggingFace's
`datasets` — an optional dependency of `transformers` and `sentence-transformers` that is not installed
today but can be pulled in by any future upgrade, producing an import failure with no obvious cause.

Paths SHALL remain anchored on `ROOT = Path(__file__).resolve().parents[N]` as the project already
requires, so any module runs from any working directory. Env overrides that exist today
(`APP_DB_PATH`, `QDRANT_PATH`) SHALL keep working and SHALL be read in the registry, not at each
call site.

#### Scenario: A dataset moves without a code sweep

- **WHEN** a dataset file is relocated on disk
- **THEN** exactly one constant in `quran_data` changes
- **AND** no consumer module is edited

#### Scenario: No hand-built data paths survive

- **WHEN** the repo is searched for the string `"data"` used as a path segment outside `quran_data/`
- **THEN** production modules under `api/`, `indexing/`, `ingestion/`, `retrieval/`, `generation/`,
  the domain packages and `scripts/` SHALL yield no path construction into `data/`
- **AND** remaining occurrences SHALL be prose in comments or docstrings only

### Requirement: Each dataset has exactly one loader, cached and shared

`quran_data` SHALL expose one loader per dataset, each parsing the file **once per process** and
returning a shared object — the pattern `indexing/corpus.py` already established with `chakl_by_ref()`,
`load_verses()` and `verses_by_id()`, extended to every dataset.

In particular `quran-morphology.txt`, parsed today by four independent readers
(`analysis/fassila.py`, `ingestion/qac_morphology.py`, `ingestion/root_resolver.py`, `tahlil/huruf.py`),
SHALL have exactly one parser. Where those readers need different projections of the same file, the
projections SHALL be built from one parse rather than by re-reading it.

Loaders SHALL be lazy: importing `quran_data` SHALL NOT read any file. The lazy-model discipline the
backend relies on — a backend serving only the lexical paths holds no model memory — SHALL extend to
data, so a request touching one dataset never pays to parse another.

#### Scenario: The morphology file is parsed once

- **WHEN** a process uses Fassila, Tahlīl and the ingestion pipeline in turn
- **THEN** `quran-morphology.txt` SHALL be read from disk exactly once
- **AND** each consumer SHALL receive the projection it needs from that single parse

#### Scenario: Import is free

- **WHEN** `quran_data` is imported
- **THEN** no dataset file SHALL be opened
- **AND** `GET /health` SHALL continue to answer without loading any dataset or model

#### Scenario: Loaders honour existing env overrides

- **WHEN** `APP_DB_PATH` or `QDRANT_PATH` is set
- **THEN** the registry SHALL resolve it against `ROOT` and return that location
- **AND** an empty `QDRANT_PATH` SHALL continue to read as unset

### Requirement: A manifest records provenance, producer and consumers

`quran_data` SHALL carry a machine-readable manifest with one entry per dataset, stating: its bucket,
its origin (upstream project and URL, or the script that fetches it), the pipeline step that produces
it, the modules that consume it, and whether it is regenerable.

The manifest SHALL be the source of the documentation currently spread across `CLAUDE.md`,
`scripts/README.md` and module docstrings, so provenance has one home rather than four
partially-agreeing ones.

#### Scenario: Provenance is answerable without reading code

- **WHEN** a developer asks where `roots_resolved.json` comes from
- **THEN** the manifest SHALL name `ingestion/root_resolver.py` as its producer, `data/source/` and
  `data/references/root_arbitration.json` as its inputs, and mark it regenerable

#### Scenario: A missing dataset fails with an actionable message

- **WHEN** a loader is called for a file that is absent
- **THEN** the error SHALL name the dataset, its expected path, and — for a regenerable one — the exact
  command that rebuilds it
- **AND** for a non-regenerable one, the error SHALL name the upstream source instead of suggesting a rebuild

#### Scenario: The manifest cannot silently drift

- **WHEN** the test suite runs
- **THEN** a test SHALL assert that every path constant in `quran_data` has a manifest entry, and every
  manifest entry names an existing constant
