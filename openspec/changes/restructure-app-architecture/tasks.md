## 1. Baseline & hygiene (no code risk)

- [ ] 1.1 Capture a behavior baseline: run backend pytest, `frontend` Vitest, and the retrieval eval (`tests/eval/evaluate.py`), and save the outputs to compare against after each later step.
- [ ] 1.2 Remove OS/build scratch from the tree: all `.DS_Store` (×10), every `__pycache__/`, and `.pytest_cache/`.
- [ ] 1.3 Remove runtime/dev scratch: `local-dev/logs/` and `local-dev/backups/` (`bm25_index.pre-hamza-fix.pkl`, `morphology.pre-qac.json`).
- [ ] 1.4 Confirm (OQ3) then remove the unwired `data/raw/eqtb/` (~40 MB, incl. `Quranic.rar` + extracted CSVs).
- [ ] 1.5 Harden `.gitignore` so every path in 1.2–1.4 stays ignored; verify with `git status --ignored`.

## 2. Configuration & packaging foundation

- [ ] 2.1 Decide OQ2 (pydantic-settings vs dataclass) and add a single `config`/settings module defining every variable in `.env.example` with identical defaults.
- [ ] 2.2 Add a test asserting each toggle/value resolves to today's default with no env overrides (`ROOT_CHANNEL_ENABLED=1`, `QUERY_PROCESSOR_ENABLED=1`, `HYDE_ENABLED=0`, `RERANK_ENABLED=0`, `QAC_STEMMER_FALLBACK=0`, ports, model names).
- [ ] 2.3 Migrate `api/main.py`, `api/store.py`, `generation/llm_client.py`, `generation/chat_engine.py`, `indexing/qdrant_store.py`, `indexing/embedder.py`, `retrieval/{lexical_retriever,reranker,root_channel}.py`, and `madar/madar_service.py` to read from the settings module instead of `os.getenv`.
- [ ] 2.4 Move the import-time `SEARCH_*` constants in `api/routers/search.py` to runtime reads off the settings object.
- [ ] 2.5 Add `pyproject.toml` packaging metadata; install editable in `scripts/setup.sh`.
- [ ] 2.6 Remove the per-module `sys.path.insert(0, ...parents[N])` idiom now that the project is importable; run any module `__main__` smoke tests from an arbitrary cwd to confirm.

## 3. Backend layering fixes (one violation at a time)

- [ ] 3.1 D1: make `retrieval/hyde.py` take an injected LLM callable; have `generation/chat_engine.py` pass it; remove the `generation.llm_client` import from `retrieval/`.
- [ ] 3.2 D2: give the `api` layer its own vocalization accessor so `api/models/verse.py` no longer imports `indexing.corpus`.
- [ ] 3.3 D3: rename `retrieval.lexical_retriever._clitic_alif_candidates` to a public symbol; update the `lisan/` import.
- [ ] 3.4 Verify no package imports upward and no cycle remains (import-graph check / `grep`); re-run the baseline suites for parity.

## 4. Root-facing consolidation & wiring

- [ ] 4.1 D4: extract the shared word→root resolution behind one service interface; route `/lexical`, `/lisan`, `/madar`, `/verse-lookup` through it without changing the algorithm.
- [ ] 4.2 Parity-check: assert identical root sets for a sample of homographs across all four surfaces, before vs after.
- [ ] 4.3 D7: build the `lisan` and `madar` services in the FastAPI lifespan into `app.state`; remove the in-handler lazy imports from `api/routers/{lisan,madar}.py`.
- [ ] 4.4 D8: rename `generation/lexical_analyzer.py` so "Lisan Analysis" denotes only the `lisan/` feature; update references.
- [ ] 4.5 OQ1: delete `ingestion/morphology.py` + the `QAC_STEMMER_FALLBACK` branch, OR retain it with a test exercising the fallback and a doc note.

## 5. Frontend rendering unification

- [ ] 5.1 D10: make `ArabicText` the sole Arabic renderer (owns dir/lang/font/line-height); migrate `.arabic-text` CSS usages and inline `font-arabic`+`dir` markup to it; keep visual parity.
- [ ] 5.2 D10: adopt `VerseCard` (or a shared `VerseBody` primitive) in `app/verse-study/page.tsx` (Similar Verses, `SurahCard`/`HighlightedVerse`) and `app/surah/[number]/page.tsx`; remove the inline verse blocks incl. the `﴿n﴾` marker.
- [ ] 5.3 Eyeball each affected page for parity (highlighting, vocalization, clickable refs, Arabic line-height).

## 6. Frontend API client, hooks & dead-code removal

- [ ] 6.1 D11: add `lisanAnalyze()` to `lib/api.ts`; switch `app/lexical/page.tsx` from inline `fetch` to it (preserve the 422-detail error handling).
- [ ] 6.2 D11: delete dead `lexical()` + `LexicalResponse` from `lib/api.ts` and `components/LexicalResult.tsx`.
- [ ] 6.3 D11: extract a shared `useFetch`/`useApi` hook and replace the copy-pasted loading/error/data scaffolding in the 3 Verse Study tabs and both dynamic route pages.
- [ ] 6.4 D11: move `toArabicDigits` to a single `lib/` export; remove the inline copy in `app/surah/[number]/page.tsx`.
- [ ] 6.5 D11: give each backend response shape one owner across `types.ts`/`lisanTypes.ts`/`madarTypes.ts` (OQ5: shared module now, codegen deferred unless adopted).
- [ ] 6.6 Add `"test": "vitest run"` to `frontend/package.json`; realign the `/lexical` route slug to the Lisan feature name (update nav/home/links).

## 7. Launchers, ports & Docker

- [ ] 7.1 D12: factor shared bring-up steps (prereq checks, `wait_http`, cleanup trap, `.env` handling, browser open) into one sourced helper used by both the committed launcher and the local superset.
- [ ] 7.2 D12: remove `scripts/start_dev.sh` and `scripts/ingest.sh` (document their one step inline / in `scripts/README.md`).
- [ ] 7.3 D12 + OQ4: define the backend port once and consume it in `docker-compose.yml`, `Dockerfile`, the launcher, and docs; state any local-only 8001 difference in exactly one place.

## 8. Documentation single source of truth

- [ ] 8.1 D13: rewrite `architecture.md` in English against the real system — drop the PostgreSQL morphology store and `/themes`; add `lisan` and `madar`.
- [ ] 8.2 D13: rewrite/trim `project_summary.md` in English; remove dropped-scope features (F3/F4/F5/F6).
- [ ] 8.3 D13: collapse the overlapping `plans/` docs into one canonical status source; update the "last reviewed" date; fix the `local-dev/README.md` Ollama (Docker vs native) inconsistency.
- [ ] 8.4 Update `CLAUDE.md` to point at the single canonical status doc and reflect the new structure (settings module, packaging, renamed modules, unified renderers).

## 9. Final verification

- [ ] 9.1 Re-run backend pytest, `frontend` Vitest, and the retrieval eval; diff against the 1.1 baseline — metrics and contracts unchanged.
- [ ] 9.2 Smoke-test the live app via the canonical launcher: chat, Verse Study (all tabs), Lisan, Madār, surah/verse pages — all behave as before.
- [ ] 9.3 Run `openspec validate --change restructure-app-architecture` and confirm all spec scenarios are satisfied.
