## ADDED Requirements

### Requirement: Acyclic package layering

The Python backend SHALL maintain a strict, acyclic dependency direction between
packages: `ingestion` → `indexing` → `retrieval` → (`generation` | `lisan` | `madar`)
→ `api`. A package MUST NOT import from a package above it in this order, and there
MUST be no import cycle between any two packages. All existing user-facing behavior
SHALL be preserved.

#### Scenario: retrieval does not import generation

- **WHEN** the import graph of the `retrieval` package is inspected
- **THEN** no module under `retrieval/` imports from `generation/`
- **AND** `retrieval/hyde.py` receives its LLM capability by injection (a callable/interface
  passed in) rather than importing `generation.llm_client`.

#### Scenario: api models do not reach into indexing

- **WHEN** the import graph of `api/models/` is inspected
- **THEN** no module under `api/models/` imports from `indexing/`
- **AND** the fully-vocalized (`text_ar_tashkil`) fill that previously called
  `indexing.corpus.chakl_by_ref` is provided through a service/helper the `api` layer owns.

#### Scenario: no cross-package private imports

- **WHEN** the backend import graph is inspected
- **THEN** no module imports an underscore-prefixed (`_name`) symbol from a different
  package; any cross-package helper (e.g. the clitic-alif candidate helper used by `lisan/`)
  is exposed under a public name.

#### Scenario: behavior parity after relayering

- **WHEN** the backend test suite and retrieval eval harness are run before and after the
  relayering
- **THEN** the HTTP contracts, retrieval results, and eval metrics are unchanged.

### Requirement: Single typed configuration source

Backend configuration SHALL be read through one typed settings object rather than ad-hoc
`os.getenv` calls scattered across modules. Environment-variable reads MUST NOT occur at
module import time in a way that freezes a per-process toggle before the settings object
is constructed. The set of supported variables and their defaults SHALL match the current
`.env.example` so existing deployments keep working.

#### Scenario: settings are centralized

- **WHEN** the backend is searched for configuration reads
- **THEN** environment variables are resolved through the single settings module
- **AND** the previously import-time `SEARCH_*` constants in `api/routers/search.py` are
  read through that settings object, not at import.

#### Scenario: defaults preserved

- **WHEN** the app starts with no environment overrides
- **THEN** every toggle and value resolves to the same default it has today
  (`ROOT_CHANNEL_ENABLED=1`, `QUERY_PROCESSOR_ENABLED=1`, `HYDE_ENABLED=0`,
  `RERANK_ENABLED=0`, `QAC_STEMMER_FALLBACK=0`, ports, model names, etc.).

### Requirement: Consistent import bootstrapping

Modules SHALL NOT rely on the repeated `sys.path.insert(0, str(Path(__file__).resolve().
parents[N]))` idiom for intra-project imports. The project SHALL be importable as a package
(or via a single entrypoint bootstrap) so that scripts and modules run from any working
directory without per-file path manipulation.

#### Scenario: modules import without path hacks

- **WHEN** a backend module or a `scripts/` entrypoint is run from an arbitrary directory
- **THEN** its intra-project imports resolve without that module performing its own
  `sys.path.insert` root computation.

### Requirement: Unified root-resolution service and wiring

The four root-facing surfaces — `/lexical`, `/lisan`, `/madar`, `/verse-lookup` — SHALL
resolve a word to its root(s) through one shared resolution service rather than
independent copies of the resolution logic. The `lisan`/`madar` router services SHALL be
constructed at application startup into `app.state`, consistent with the other routers,
instead of being lazily imported inside request handlers. The naming collision between
`generation/lexical_analyzer.py` (which describes itself as "Lisan Analysis") and the
`lisan/` package SHALL be resolved so each name denotes exactly one feature.

#### Scenario: shared root resolution

- **WHEN** any of the four root-facing endpoints resolves a word to root(s)
- **THEN** it calls the shared root-resolution service
- **AND** homograph words return the same set of roots across all four surfaces.

#### Scenario: services built at startup

- **WHEN** the application starts
- **THEN** the `lisan` and `madar` services are instantiated in the FastAPI lifespan and
  exposed via `app.state`, and their routers read them from `app.state` (no in-handler
  `from lisan… import` / `from madar… import`).

#### Scenario: unambiguous feature naming

- **WHEN** the codebase is read for the term "Lisan Analysis"
- **THEN** exactly one feature owns that name, and the other feature is named distinctly.

### Requirement: Resolve the legacy morphology backend

The legacy tashaphyne/camel/heuristic root builder (`ingestion/morphology.py`), currently
reachable only through the off-by-default `QAC_STEMMER_FALLBACK`, SHALL be either removed
or explicitly retained behind a documented, tested fallback path. Dead code MUST NOT be
left in an ambiguous state.

#### Scenario: legacy backend decision is explicit

- **WHEN** the change is applied
- **THEN** `ingestion/morphology.py` is either deleted (with the `QAC_STEMMER_FALLBACK`
  branch removed) or kept with a test that exercises the fallback and a doc note explaining
  when it is used — not left unused-but-present without a decision.
