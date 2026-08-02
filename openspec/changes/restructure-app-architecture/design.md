## Context

The system (a Quran RAG chatbot + Arabic-root study tools) is functional but carries
structural debt that raises the cost of every change. Concretely, three independent maps of
the tree surfaced:

- **Backend:** intended layering is `ingestion → indexing → retrieval → generation/lisan/madar
  → api`, but `retrieval/hyde.py` imports `generation.llm_client` (a `generation ⇄ retrieval`
  cycle), `api/models/verse.py` reaches into `indexing.corpus`, and `lisan/` imports a private
  `retrieval.lexical_retriever._clitic_alif_candidates`. Config is read via ad-hoc `os.getenv`
  in 8+ files (some at import time), there is no Settings object, and ~20 modules repeat a
  `sys.path.insert(...parents[N])` hack. Four surfaces (`/lexical`, `/lisan`, `/madar`,
  `/verse-lookup`) each resolve word→root with their own glue, `lisan`/`madar` routers lazy-import
  their services in-handler, and `generation/lexical_analyzer.py` calls itself "Lisan Analysis"
  while a separate `lisan/` package also exists. `ingestion/morphology.py` is legacy, reachable
  only via the off-by-default `QAC_STEMMER_FALLBACK`.
- **Frontend:** Arabic text is rendered three ways (`ArabicText` component, `.arabic-text` CSS,
  `font-arabic` utility); verses are re-implemented inline in Verse Study (3 variants) and the
  surah page rather than reusing `VerseCard`; the Lisan page bypasses `lib/api.ts` with an inline
  `fetch` while `api.ts`'s `lexical()` + `LexicalResponse` + `components/LexicalResult.tsx` are
  dead; `toArabicDigits` is duplicated; fetch/loading/error scaffolding is copy-pasted across 5
  places; response types are hand-mirrored across three files; no `test` npm script.
- **Tooling/docs:** two divergent launchers (`scripts/run.sh` @8000 `next dev` + Docker Ollama vs
  `local-dev/start.sh` @8001 prod build + native Ollama), trivial wrappers (`start_dev.sh`,
  `ingest.sh`), ~46 MB of scratch (`local-dev/backups/`, `data/raw/eqtb/` incl. `Quranic.rar`),
  `.DS_Store`/`__pycache__`/logs on disk, and stale French design docs (`architecture.md`,
  `project_summary.md`) that describe dropped features (PostgreSQL store, `/themes`) and omit
  `lisan`/`madar`.

**Hard constraint:** this is behavior-preserving. No HTTP contract, retrieval result, prompt,
model, or data-pipeline output may change. The published git repo is product-only; several
touched paths (`plans/`, `local-dev/`, `CLAUDE.md`, `architecture.md`, tests) are local-only and
git-ignored — cleanup there is on-disk, not a repo change.

## Goals / Non-Goals

**Goals:**
- Enforce an acyclic package layering and remove the known layering violations.
- Introduce one typed Settings source; eliminate scattered/import-time `os.getenv`.
- Make the project importable as a package so the `sys.path.insert` idiom disappears.
- Unify the four root-facing surfaces on one root-resolution service; wire `lisan`/`madar` at
  startup; resolve the "Lisan Analysis" naming collision.
- Give the frontend one Arabic renderer, one verse component, one API client, one fetch hook,
  one owner per response type; delete dead UI.
- Collapse to one canonical launcher + one documented local superset; reconcile ports; purge
  scratch and harden `.gitignore`; make design docs match reality.

**Non-Goals:**
- No new features, no retrieval-quality or prompt/model changes, no data re-ingestion.
- No forced framework swaps (stay on FastAPI + Next.js 14; no new state/data library).
- Not adopting OpenAPI codegen in this change if hand-owned shared types suffice (kept as an
  option, not a requirement).
- Not re-litigating dropped scope (F3/F5/F6) — docs simply stop describing them.

## Decisions

**D1 — Break the retrieval→generation cycle by dependency injection.**
`retrieval/hyde.py` will accept an LLM callable/interface via its constructor instead of
`from generation.llm_client import LLMClient`. `generation/chat_engine.py` (which already owns
the LLM) passes it in. *Alternative considered:* move `llm_client.py` into a neutral lower
package — rejected as a larger move that drags provider config downward; injection is minimal and
matches how the `root_ranker` is already injected into `hybrid_search`.

**D2 — API owns its vocalization helper.**
Introduce a thin `api`-level accessor (or pass the chakl loader in at startup via `app.state`) so
`api/models/verse.py` stops importing `indexing.corpus`. *Alternative:* leave it as a "data-only"
leak — rejected; it's the seam that makes the model layer untestable without the corpus.

**D3 — Promote the private clitic helper.**
Rename `retrieval.lexical_retriever._clitic_alif_candidates` to a public name and export it; `lisan`
imports the public symbol. Trivial, removes the encapsulation break.

**D4 — One root-resolution service.**
Extract the shared word→root resolution (already centered on `LexicalRetriever` and reused by
`verse_lookup`, `similar_verses`/`root_channel`, and `LisanService`) behind one service interface
that all four surfaces call. `madar` continues to build on `lisan`, but both reach roots through
the shared service, not private glue. This is a consolidation of existing logic, not a rewrite —
the resolution algorithm is unchanged, so homograph results stay identical.

**D5 — Typed Settings via pydantic-settings, read once at startup.**
A single `config`/`settings` module (pydantic `BaseSettings`) defines every variable currently in
`.env.example` with identical defaults. Modules receive settings (injected or imported from the one
module) instead of calling `os.getenv`. Import-time constants in `api/routers/search.py` move to
runtime reads off the settings object. *Alternative:* a plain dataclass hand-parsing `os.environ` —
rejected; pydantic-settings gives typing/validation for free and `.env` is already loaded via
python-dotenv. This is the one candidate new dependency; if undesirable, a dataclass fallback keeps
the same interface.

**D6 — Make the project an installable package to kill `sys.path.insert`.**
Add packaging metadata (`pyproject.toml`) and install editable (`pip install -e .`) in setup, so
intra-project imports resolve without per-file root computation. Entry scripts under `scripts/` use
console entrypoints or a single bootstrap. *Alternative:* a single `conftest`/`sitecustomize` shim —
rejected as implicit; explicit packaging is the durable fix.

**D7 — `lisan`/`madar` services built in the FastAPI lifespan.**
Instantiate both in `api/main.py`'s lifespan into `app.state`, matching every other router; drop
the in-handler `from lisan… / from madar…` lazy imports. Startup cost is bounded (both are
deterministic/light; `madar` LLM synthesis stays env-gated and off by default).

**D8 — Naming: `lisan/` keeps "Lisan Analysis"; `generation/lexical_analyzer.py` is renamed.**
The deterministic letter-symbolism feature is the one users see as "Lisan Analysis" (the `/lexical`
route renders `LisanResult`). The LLM root-analysis module in `generation/` is renamed to reflect
what it is (root/lexical LLM analysis) so the term "Lisan Analysis" denotes exactly one feature.
Frontend route slug `/lexical` is realigned to the feature name as part of D12.

**D9 — Legacy `morphology.py`: keep behind a tested, documented fallback (default: remove).**
Preferred path is deletion plus removing the `QAC_STEMMER_FALLBACK` branch, since QAC roots are the
verified source of truth and the fallback is off by default. If the maintainer wants to retain it,
it stays only with a test exercising the fallback and a one-line doc note. Flagged as an open
question because it's a judgment call, not a mechanical fix.

**D10 — Frontend: one `ArabicText`, one verse component.**
`ArabicText` becomes the sole Arabic renderer (owns dir/lang/font/line-height); `.arabic-text` CSS
and inline `font-arabic`+`dir` usages are migrated to it. `VerseCard` (or a small `VerseBody`
primitive it composes) becomes the sole verse renderer, adopted by Verse Study and the surah page.
Visual parity is the acceptance bar.

**D11 — Frontend: everything through `lib/api.ts`; delete dead code.**
Add a `lisanAnalyze()` client function; the Lisan page calls it instead of inline `fetch`. Remove
`lexical()`, `LexicalResponse`, and `components/LexicalResult.tsx`. Extract a `useApi`/`useFetch`
hook for loading/error/data; move `toArabicDigits` to a single `lib/` export. Add `"test": "vitest run"`
to `package.json`. Response types get one owner per shape (shared module); OpenAPI codegen remains an
option but is not required here.

**D12 — Tooling: one canonical launcher + documented local superset; central port value.**
Factor the shared bring-up steps (prereq checks, `wait_http`, cleanup trap, `.env` handling,
browser open) into one sourced helper used by both the committed launcher and the local superset,
so they can't drift. The port is defined once and consumed by compose/Dockerfile/launcher/docs; the
local-only 8001 difference (if kept) is stated in exactly one place. Remove `start_dev.sh` and
`ingest.sh`.

**D13 — Hygiene + docs.**
Delete the scratch/artifact paths and extend `.gitignore` to cover them. Rewrite `architecture.md`
and `project_summary.md` in English against the real system, add `lisan`/`madar`, and collapse the
overlapping `plans/` narratives into a single status source.

## Risks / Trade-offs

- **Import-graph refactor breaks startup wiring** → Do it in small, independently-verifiable steps
  (one violation at a time); run pytest + Vitest + the eval harness after each; keep behavior parity
  as the gate.
- **Settings centralization silently changes a default** → Pin defaults to the current `.env.example`
  and add a test asserting each resolved default; diff `.env.example` before/after.
- **pydantic-settings as a new dependency** → Interface is written so a plain-dataclass implementation
  can back it if the dependency is rejected (Open Question OQ2).
- **Consolidating four root surfaces alters a homograph result** → Extract without touching the
  algorithm; assert identical root sets on a sample of homographs before/after.
- **Frontend visual regressions from renderer unification** → Migrate incrementally with screenshot/eye
  parity per page; Arabic line-height and ayah-marker rendering are the sensitive spots.
- **Deleting `morphology.py` removes a fallback someone relied on** → Gated by OQ1; default keeps a
  tested path if retained.
- **Deleting scratch loses local-only history** (`local-dev/backups/`, `data/raw/eqtb/`) → These are
  superseded snapshots and unwired exploration; confirm with the maintainer (OQ3) before removing the
  larger `eqtb/` set.
- **Docs rewrite drifts again** → Point CLAUDE.md at the single canonical status doc and delete the
  duplicative ones so there's one place to update.

## Migration Plan

Sequenced so each step is behavior-preserving and independently checkable (see tasks.md):
1. Hygiene + `.gitignore` (no code risk) → establishes a clean baseline.
2. Settings module + packaging (`pyproject.toml`), replacing `os.getenv` and `sys.path.insert`
   incrementally, test after each package.
3. Break the three layering violations (D1–D3) one at a time.
4. Consolidate root resolution + startup wiring + naming (D4, D7, D8); parity-check homographs and
   all four endpoints.
5. Resolve `morphology.py` per OQ1.
6. Frontend: renderers → API client → hook/utils → dead-code deletion (D10–D11), page by page.
7. Launcher/port consolidation (D12), then docs rewrite (D13).

**Rollback:** every step is a separate commit on a branch; revert the offending step. No data
migrations, so rollback is purely code/tree-level.

## Open Questions

- **OQ1:** Delete `ingestion/morphology.py` and the `QAC_STEMMER_FALLBACK` branch outright, or retain
  it behind a tested fallback? (Default: delete.)
- **OQ2:** Is adding `pydantic-settings` acceptable, or should the Settings object be a hand-rolled
  dataclass over `os.environ`?
- **OQ3:** Confirm `data/raw/eqtb/` (~40 MB, unwired) and `local-dev/backups/` can be removed from
  disk — any intent to revisit the Extended Quranic Treebank exploration?
- **OQ4:** Keep the local-only 8001 backend port, or standardize everything on 8000?
- **OQ5:** Adopt OpenAPI→TS type generation now, or keep one hand-owned shared types module for this
  change and defer codegen?
