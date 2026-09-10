## Why

The repo has accumulated a second, invisible codebase: **7 backend routes no page calls**, three
orphaned frontend components, a lexical-analysis service kept alive only because it happens to hold
the retriever three live features borrow, ~20 modules each re-deriving `ROOT / "data" / ...` by hand,
the same QAC morphology file parsed by 4 independent readers, one dataset living outside `data/`
altogether, and ~9.5 MB of committed reference files nothing reads. Nothing is broken — which is
exactly the problem: the gap between what the app serves and what the repo carries is now wide enough
that a reader cannot tell them apart, and every new feature is written against a map that no longer
matches the territory.

## What Changes

### Remove what the app provably does not reach

Scope is deliberately narrow: only what **no page and no offline pipeline reaches**. Off-by-default
quality toggles (HyDE, rerankers, the gated legacy stemmer) are explicitly *kept* — they are dormant
levers, not dead code.

- **BREAKING (HTTP surface)** — unmount routes no frontend page calls: `POST /lexical`,
  `POST /lexical/stream`, `POST /chat` (non-stream), `POST /tahlil/verse`, `GET /sessions/{id}`,
  `GET /feedback/stats`. `POST /chat/stream` and `POST /feedback` stay — they are what the chat page
  actually uses.
- Delete orphaned frontend components: `LexicalResult.tsx` (its own string table already records
  «kept for the interim; the restructure deletes the component»), `MadarAslCard.tsx`,
  `StatusBadge.tsx` (reachable only through `MadarAslCard`), and the dead `lexical()` /
  `madarAnalyze()` clients in `lib/api.ts`.
- Delete untracked scratch files: `requirements.txt.bak-preuv`, `requirements-test.txt.bak-preuv`,
  `scripts/setup.sh.bak-preuv`, stray `.DS_Store` under `data/`.
- Stop committing reference files nothing reads: `data/raw/eqtb/{Quran.csv,Quranic.rar,RelLabels.csv,pos.csv}`
  (~9 MB) and `data/references/zero_theory_pitch_deck.pdf`. The treebank CSV they shipped alongside
  **is** read and stays; provenance is recorded in the manifest rather than by keeping the archive.

### Quarantine Madār

`madar/` is complete and tested but no page has called it since its Verse Study integration was
pulled. It is **not** deleted — it is moved off the production path and kept runnable:
the router is unmounted, its frontend components go, its service and tests stay. Rebranching later
costs one `include_router` line.

### Centralize the datasets

- One module becomes the **single source of truth** for every dataset path, and the only place a
  dataset is opened, parsed and cached. No module computes a data path by hand again.
- **`data/` is physically reorganized** into a layout that states each file's nature —
  source, derived, reference, runtime — instead of leaving the reader to infer it from `.gitignore`.
  The stray `analysis/data/mizan_patterns.json` moves in with the rest.
- A **manifest** records, per dataset: provenance, which step produces it, who consumes it, and
  whether it is regenerable. The 4 hand-rolled QAC morphology parsers collapse into one loader.

### Factor the codebase

- The four linguistic-analysis packages (`analysis/`, `lisan/`, `madar/`, `tahlil/`) move under one
  domain parent. `ingestion/`, `indexing/`, `retrieval/`, `generation/`, `api/` keep their place —
  they are the pipeline, and their names already say so.
- The shared text/root primitives those packages currently borrow from pipeline modules
  (`ingestion.root_normalize`, `indexing.text_normalize`, `indexing.corpus`) move to a neutral home,
  ending the inversion where an analysis package imports the *indexer* to read a verse.
- `lisan/lisan_service.py` reaches into `retrieval.lexical_retriever._clitic_alif_candidates` — a
  private function across a package boundary. It becomes a published API.
- The shared `LexicalRetriever` is exposed as its own `app.state` resource instead of being reached
  through `app.state.lexical_analyzer`, an object that exists to serve a route being removed.
- **Every import in the repo — production, tests, scripts, launchers, Docker — is updated in the same
  change.** The app must run at the end of it.

## Capabilities

### New Capabilities

- `dataset-registry`: the canonical `data/` layout, the single path/loader authority, the dataset
  manifest (provenance, producer, consumers, regenerability), and the rule that no module opens a
  dataset by hand.
- `module-layout`: the package topology (domain packages vs pipeline packages), where shared
  primitives live, the allowed import directions between layers, and the no-private-cross-package-import
  rule.
- `served-surface`: the HTTP surface the backend actually exposes, the rule tying every mounted route
  to a real consumer, and the quarantine convention for complete-but-unwired subsystems like Madār.

### Modified Capabilities

None. No existing spec's requirements change: every removed endpoint is one no spec documents, and
every page, nav entry and user-visible behaviour is preserved exactly. (`arabic-ui-locale` mentions
`/lexical` as a *frontend route* — that page stays; it calls `POST /lisan/analyze`, not the endpoint
being removed.)

## Impact

**Backend** — `api/main.py` (router mounts, `app.state` wiring), 6 routers unmounted or deleted,
their `api/models/*`; the four domain packages move (47 production import sites); `indexing/corpus.py`,
`indexing/text_normalize.py`, `ingestion/root_normalize.py` relocate; ~20 modules lose their hand-rolled
data paths.

**Frontend** — 3 components deleted, `lib/api.ts` loses 2 dead clients, `lib/strings.ts` loses the
`LexicalResult` entry. No page, route, nav entry or rendered output changes.

**Data on disk** — `data/` is reorganized. `data/processed/`, `data/runtime/`, `data/translations/`
are git-ignored and regenerable, but `data/processed/` is 69 MB whose rebuild costs an embedding run;
the change must **move** it, not force a rebuild. `.gitignore`, `Dockerfile`, `docker-compose.yml`,
`scripts/run.sh`, `scripts/ingest.sh`, `local-dev/start.sh`, `.env`/`.env.example` (`QDRANT_PATH`,
`APP_DB_PATH`) all carry data paths and must move with it.

**Tests (local-only)** — 37 pytest files, 29 of which import the moved domain packages; `pytest.ini`;
the frontend Vitest suites, including `verse-study/page.test.tsx` which still tests the removed Madār
integration.

**Docs** — `CLAUDE.md`, `README.md`, `scripts/README.md`, `architecture.md` all describe the old
layout and paths.

**Coordination** — the untracked in-flight change `migrate-llm-qwen-to-jais` touches
`generation/llm_client.py`. `generation/` does not move here, so the two do not collide, but the
removal of `POST /chat` (non-stream) overlaps its surface and must be sequenced.

**Explicitly out of scope** — no retrieval, ranking, generation or rendering behaviour changes; no
dependency upgrades; no Qdrant/Ollama topology change; no new features.
