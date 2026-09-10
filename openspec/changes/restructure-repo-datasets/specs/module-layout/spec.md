## ADDED Requirements

### Requirement: Packages are grouped by role, and the grouping is visible from the tree

The repo SHALL distinguish three kinds of Python package at the top level:

- **Pipeline packages** — the request path and the build path, in order: `ingestion/`, `indexing/`,
  `retrieval/`, `generation/`, `api/`. These keep their current names and positions; the names already
  state the order.
- **Domain packages** — the linguistic-study engines, grouped under one parent `linguistics/`:
  `linguistics/analysis/` (fassila, mizan, qac_labels, qlisan_data, word_analysis),
  `linguistics/lisan/`, `linguistics/madar/`, `linguistics/tahlil/`. Their internal module names are
  preserved; only the parent is added.
- **Shared packages** — `quran_data/` (dataset paths, loaders, manifest) and `arabic_text/` (the text
  and root normalization primitives), which any layer may import.

Ten sibling directories at the root give no clue that `tahlil/` is a feature engine while `indexing/`
is a pipeline stage. The grouping SHALL make that legible without a doc.

#### Scenario: The tree answers "what is this package"

- **WHEN** a developer lists the repo root
- **THEN** the four linguistic engines SHALL appear as one entry, `linguistics/`
- **AND** the pipeline packages SHALL remain siblings in their existing names

#### Scenario: Domain module names survive the move

- **WHEN** `tahlil/huruf.py` is relocated
- **THEN** it SHALL be `linguistics/tahlil/huruf.py`
- **AND** its module name, public functions and behaviour SHALL be unchanged

### Requirement: Imports flow one way, and no layer reaches upward

Dependencies SHALL be directed. `quran_data/` and `arabic_text/` SHALL import from no project package.
Pipeline packages SHALL import from shared packages and from pipeline packages earlier in the order.
Domain packages SHALL import from shared packages, and from `retrieval/` for verse lookup — never from
`api/`. No package SHALL import from `linguistics/` except `api/`.

Today three domain packages import `indexing.corpus` to read a verse — an *analysis* package importing
the *indexer* to get at data. That inversion disappears once the corpus loaders live in `quran_data/`.

#### Scenario: Analysis no longer imports the indexer

- **WHEN** `linguistics/analysis/fassila.py`, `linguistics/analysis/mizan.py`,
  `linguistics/analysis/word_analysis.py` and `linguistics/tahlil/evidence.py` need vocalized verses
- **THEN** they SHALL import the loader from `quran_data`
- **AND** no domain package SHALL import from `indexing/`

#### Scenario: The direction is enforced, not just documented

- **WHEN** the test suite runs
- **THEN** a test SHALL assert the allowed import directions over the project's own packages
- **AND** an import that reverses the order SHALL fail that test

### Requirement: No package imports another package's private names

A name prefixed with `_` SHALL be private to its defining module. Where a private helper is genuinely
needed by another package, it SHALL be promoted to a documented public function rather than imported
through the underscore.

`lisan/lisan_service.py` currently imports `_clitic_alif_candidates` from
`retrieval/lexical_retriever.py` — a private clitic-peeling helper reached across a package boundary,
so a rename inside the retriever silently breaks Lisān with no signal at the call site.

#### Scenario: The leaked clitic helper becomes public

- **WHEN** `linguistics/lisan/lisan_service.py` needs clitic-alif candidates
- **THEN** it SHALL call a public function on the retrieval package
- **AND** no `from <package> import _name` SHALL remain anywhere in production code

### Requirement: The three Arabic normalizers live side by side, each stating what it is for

`arabic_text/` SHALL hold all three normalizers, with a package docstring stating which to use when —
because choosing wrong is silent and has already caused bugs:

| Function | Hamza | Use for | Never for |
|---|---|---|---|
| `normalize_text` (from `ingestion/normalizer.py`) | **deletes** it | the ingestion pipeline's normalized field | matching, roots |
| `normalize_search` (from `indexing/text_normalize.py`) | **folds** carriers, keeps hamza | BM25 index + query tokenization, display matching | roots |
| `normalize_root` (from `ingestion/root_normalize.py`) | folds carriers, **never deletes** | root keys and root comparison | free text |

The hamza-fold primitives `fold_blind` and `fold_carrier`, today exported by the pipeline stage
`ingestion/root_resolver.py` and imported at runtime by `analysis/qlisan_data.py` and
`retrieval/lexical_retriever.py`, SHALL move to `arabic_text/` with them. `root_resolver.py` SHALL
import them from there and keep only its stage responsibilities (arbitration cascade, invariants,
writing `roots_resolved.json`, and the `load_resolved` / `same_root` lookups over its own output).

Likewise `ingestion/normalizer.py` SHALL keep only its pipeline stage (`run`), taking `normalize_text`
from `arabic_text/`.

The diacritic-stripping table is currently written out three times — in `ingestion/normalizer.py`,
`ingestion/root_normalize.py` and `indexing/corpus.py` — and SHALL be defined **once** in
`arabic_text/`. It SHALL continue to be written with `\u` escapes only: a literal Arabic character
class is unreviewable under bidirectional reordering and can silently swallow letters.

#### Scenario: Picking the wrong normalizer becomes hard

- **WHEN** a developer opens `arabic_text/`
- **THEN** all three normalizers SHALL be present with the table above
- **AND** each function's docstring SHALL state what it does to hamza and what it must not be used for

#### Scenario: Behaviour is byte-identical after the move

- **WHEN** each normalizer is applied to the corpus after relocation
- **THEN** its output SHALL be identical to the pre-change output for every verse
- **AND** the existing `test_normalizer.py` and `test_root_normalize.py` suites SHALL pass unchanged
  except for their import lines

#### Scenario: One diacritic class, escape-written

- **WHEN** the diacritic-stripping table is defined
- **THEN** exactly one definition SHALL exist in the repo
- **AND** it SHALL contain no literal Arabic combining marks, only `\u` escapes

### Requirement: A shared resource is wired as itself, not through an unrelated owner

Where several features share a component, `api/main.py` SHALL publish that component on `app.state`
under its own name. A router SHALL NOT reach a dependency through an object that exists to serve a
different feature.

`app.state.lexical_analyzer` today owns the `LexicalRetriever` that `/lisan`, `/madar`, `VerseLookup`
and `SimilarVerses` all borrow — so the analyzer for a route being removed is load-bearing for four
live consumers, and its removal looks safe while being fatal.

#### Scenario: The retriever is published under its own name

- **WHEN** the lifespan builds the shared components
- **THEN** the `LexicalRetriever` SHALL be published as its own `app.state` entry
- **AND** every consumer SHALL take it from there
- **AND** removing the lexical-analysis routes SHALL leave those consumers untouched

#### Scenario: The retriever is still built once

- **WHEN** the backend starts
- **THEN** exactly one `LexicalRetriever` SHALL be constructed
- **AND** the QAC morphology index behind it SHALL be parsed once, as today

### Requirement: Every import in the repo moves with the structure

Relocating a package SHALL update every reference in the same change: production modules, the 37
local-only pytest files (29 of which import the domain packages), `tests/eval/` scripts, `pytest.ini`,
`scripts/*.sh`, `local-dev/*.sh`, `Dockerfile`, `docker-compose.yml`, and the `__main__` smoke tests
embedded in modules.

The `ROOT = Path(__file__).resolve().parents[N]` anchoring pattern SHALL be preserved, with `N`
corrected for each module's new depth — a moved module that keeps its old `parents[N]` resolves to the
wrong root and finds no data.

#### Scenario: The app runs at the end of the change

- **WHEN** the backend is started after the restructure
- **THEN** it SHALL start with no import error
- **AND** every route the frontend calls SHALL answer as before
- **AND** each of the nine frontend pages SHALL render the same content as before

#### Scenario: Depth changes are caught

- **WHEN** a module moves one level deeper
- **THEN** its `parents[N]` SHALL be incremented accordingly
- **AND** a test SHALL assert that every module's computed `ROOT` is the repo root
