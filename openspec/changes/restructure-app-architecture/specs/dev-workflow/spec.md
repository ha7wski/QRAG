## ADDED Requirements

### Requirement: One canonical launcher and script set

The project SHALL provide one canonical, committed launcher plus at most one clearly
documented local-only superset, rather than two divergent implementations of the same
bring-up flow. The shared bring-up logic (prereq checks, `.env` handling, HTTP readiness
wait, cleanup trap, browser open) SHALL not be duplicated between them. Trivial wrapper
scripts that only re-invoke another command (`scripts/start_dev.sh`, `scripts/ingest.sh`)
SHALL be removed or folded into the canonical script.

#### Scenario: no duplicated bring-up logic

- **WHEN** the launcher scripts are inspected
- **THEN** there is one canonical committed launcher and at most one documented local
  superset
- **AND** the readiness-wait / prereq-check / cleanup logic exists in a single place, not
  copy-pasted across both.

#### Scenario: trivial wrappers removed

- **WHEN** the change is applied
- **THEN** `scripts/start_dev.sh` and `scripts/ingest.sh` are gone (their one step is
  documented inline or in the canonical script).

### Requirement: Reconciled port and service configuration

The backend port and Ollama placement SHALL be consistent across `docker-compose.yml`,
`Dockerfile`, the canonical launcher, and the docs — or, where a local variant deliberately
differs, that single difference SHALL be documented in exactly one place and derived from a
single configured value rather than hard-coded in several files.

#### Scenario: port is not contradicted across files

- **WHEN** the repo is searched for the backend port
- **THEN** the committed launcher, `docker-compose.yml`, `Dockerfile`, and their docs agree
  on the port
- **AND** any local-only port difference is stated once and clearly labeled as local-only.

### Requirement: Repo hygiene — no committed artifacts or scratch

Build artifacts, OS junk, runtime logs, backups, and unwired scratch data SHALL NOT live in
the tree, and `.gitignore` SHALL prevent their return. This covers `.DS_Store` files,
`__pycache__/`, `.pytest_cache/`, `local-dev/logs/`, `local-dev/backups/`, and the unwired
`data/raw/eqtb/` exploration (including the `Quranic.rar` archive duplicated by its extracted
CSVs).

#### Scenario: scratch removed and ignored

- **WHEN** the change is applied
- **THEN** the listed artifact/scratch paths are removed from the working tree
- **AND** `.gitignore` matches each of them so they are not re-added.

#### Scenario: nothing load-bearing is deleted

- **WHEN** scratch is removed
- **THEN** only files with no runtime or documented role are deleted; `requirements.txt` vs
  `requirements-test.txt` (a deliberate minimal subset) are both kept.

### Requirement: Single source of truth for design docs

Design documentation SHALL describe the system as it actually is. `architecture.md` and
`project_summary.md` (currently French, ahead of the code, and describing dropped features
such as the PostgreSQL morphology store, `/themes`, and translation/transliteration
comparison) SHALL be reconciled with the real system, written in English per the repo
convention, and the currently undocumented `lisan` and `madar` features SHALL be documented.
Overlapping status docs under `plans/` SHALL be collapsed so a fact lives in one place.

#### Scenario: docs match reality and are in English

- **WHEN** `architecture.md` and `project_summary.md` are read after the change
- **THEN** they describe only components that exist (no PostgreSQL morphology store, no
  `/themes`), are in English, and cover the `lisan` and `madar` features.

#### Scenario: status docs deduplicated

- **WHEN** the `plans/` docs are inspected
- **THEN** the overlapping feature/status narratives are consolidated so a given fact is
  stated in one canonical location, not repeated at differing staleness across four files.
