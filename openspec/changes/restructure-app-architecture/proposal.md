## Why

The system works, but the codebase has accumulated structural debt that slows every
change: the backend has package-level dependency cycles and no central configuration,
four overlapping "word → root" surfaces, the frontend re-implements the same verse and
Arabic rendering three or four ways, and the repo carries two divergent launchers plus
tens of megabytes of stale scratch files and out-of-date design docs. This refactor
establishes clear, enforced boundaries and a single source of truth for structure,
tooling, and docs — **without changing any user-facing behavior**.

## What Changes

**Backend layering & boundaries**
- Break the `generation ⇄ retrieval` package cycle: `retrieval/hyde.py` must stop importing
  `generation.llm_client` (inject the LLM callable instead of importing up).
- Stop `api/models/verse.py` reaching into `indexing.corpus`; move the chakl fill behind a
  service/helper the API layer owns.
- Stop `lisan/` importing the private `retrieval.lexical_retriever._clitic_alif_candidates`;
  promote it to a public helper.
- Consolidate the four overlapping root-facing surfaces (`/lexical`, `/lisan`, `/madar`,
  `/verse-lookup`) onto one shared root-resolution service; resolve the `lexical_analyzer`
  "Lisan Analysis" ↔ `lisan/` naming collision.
- Build `lisan`/`madar` services at startup into `app.state` like every other router
  (drop the in-handler lazy imports).
- Add a single typed **Settings** module; replace scattered import-time and runtime
  `os.getenv` reads across 8+ files. Replace the `sys.path.insert(...parents[N])` hack
  repeated in ~20 modules with a proper installable package / single entrypoint.
- Decide and act on legacy `ingestion/morphology.py` (dead except the off-by-default
  `QAC_STEMMER_FALLBACK`).

**Frontend architecture**
- One Arabic-text renderer (collapse `ArabicText` component vs `.arabic-text` CSS vs
  `font-arabic` utility into a single source of truth).
- One verse renderer: reuse `VerseCard` in Verse Study and the surah page instead of the
  3–4 bespoke inline verse blocks.
- Route every backend call through `lib/api.ts` (the `/lisan/analyze` inline `fetch` moves
  in); **remove** dead `lexical()` / `LexicalResponse` / `components/LexicalResult.tsx`.
- Extract a shared fetch/loading/error hook (copy-pasted across 5 places); de-duplicate
  `toArabicDigits`; add the missing `test` npm script.

**Scripts, docs, and repo hygiene**
- Consolidate the two launchers (`scripts/run.sh` @8000 vs `local-dev/start.sh` @8001) into
  one canonical committed entry + one documented local superset; reconcile the port
  inconsistency across compose/Dockerfile/docs. Remove the trivial `start_dev.sh` /
  `ingest.sh` wrappers.
- **Remove** stale scratch: `.DS_Store` (×10), `__pycache__`/`.pytest_cache`,
  `local-dev/backups/` (~5.8 MB), `local-dev/logs/`, `data/raw/eqtb/` (~40 MB unwired,
  incl. `Quranic.rar` double-storage). Harden `.gitignore` so they don't return.
- Establish one source of truth for design docs: reconcile `architecture.md` /
  `project_summary.md` (both French, ahead of code, describe dropped features) with the
  actual system; document the undocumented `madar`/`lisan` features; collapse the
  overlapping `plans/` files.

**Non-goals:** no change to retrieval quality, prompts, models, data pipeline outputs, or
any HTTP contract; no new features. This is behavior-preserving restructuring.

## Capabilities

### New Capabilities
- `backend-architecture`: Enforced package layering (dependency direction, no cycles),
  a single typed Settings/config source, unified root-resolution service, and consistent
  router/service wiring for the Python backend.
- `frontend-architecture`: Single Arabic + verse rendering source of truth, a centralized
  typed API client, a shared data-fetching hook, and removal of dead UI code.
- `dev-workflow`: One canonical launcher and script set, reconciled ports/config, repo
  hygiene (ignored artifacts never committed), and a single source of truth for design docs.

### Modified Capabilities
<!-- None. The refactor preserves all existing behavior, including the `verse-study` spec. -->

## Impact

- **Affected backend:** `api/` (models, routers, `main.py`), `generation/`, `retrieval/`
  (`hyde.py`, `lexical_retriever.py`), `indexing/`, `ingestion/`, `lisan/`, `madar/`;
  a new `config`/settings module; all modules' path-bootstrap.
- **Affected frontend:** `frontend/src/components/`, `frontend/src/lib/`,
  `frontend/src/app/{lexical,verse-study,surah}`, `package.json`, `tsconfig`.
- **Affected tooling/docs:** `scripts/`, `local-dev/`, `docker-compose.yml`, `Dockerfile`,
  `.gitignore`, `README.md`, `architecture.md`, `project_summary.md`, `plans/`,
  `documentation/`.
- **Risk area:** import-graph and config changes touch startup wiring — mitigated by the
  behavior-preserving constraint and the existing pytest + Vitest + eval harnesses, which
  must pass unchanged before/after.
- **No API/data contract changes; no dependency additions expected** beyond an optional
  settings library.
