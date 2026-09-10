## 0. Snapshot the baseline (nothing changes yet)

- [ ] 0.1 Write a replayable route-parity harness covering all 15 consumed endpoints, with the cases the project has already been bitten by: `2:1` (Basmala-prefixed āya 1), `1:1` (al-Fātiḥa, where the Basmala genuinely is āya 1), sūra 9 (no Basmala), a hamzated root (`لؤلؤ`), a contested root (ٱلنَّاس → `أنس`/`نوس`), a multi-root `/search` phrase exercising the AND-coverage path, and a `/verse-lookup` with highlight offsets
- [ ] 0.2 Record the baseline responses (ordered results, not just status codes — the `/search` pool caps are load-bearing for quality) into a snapshot file outside the repo tree
- [ ] 0.3 Record a `data/` inventory: every file with size and mtime, plus per-bucket totals
- [ ] 0.4 Record baselines for `python -m pytest -q` and `cd frontend && npx vitest run`, noting any test already failing so a pre-existing failure is never mistaken for a regression
- [ ] 0.5 Confirm the backend is stopped before any step that touches `data/runtime/qdrant` (embedded Qdrant holds an exclusive file lock)

## 1. Remove what the app does not reach

- [ ] 1.1 Publish the shared `LexicalRetriever` on `app.state` under its own name in the lifespan, and repoint `/lisan`, `/madar`, `VerseLookup` and `SimilarVerses` at it — **before** touching `lexical_analyzer` (this is the step where the dead-object-holding-live-wiring trap fires)
- [ ] 1.2 Verify exactly one `LexicalRetriever` is still constructed at startup and the QAC morphology index is parsed once
- [ ] 1.3 Unmount and delete `api/routers/lexical.py` (`POST /lexical`, `POST /lexical/stream`) and `api/models/lexical.py`; drop `LexicalAnalyzer` from the lifespan
- [ ] 1.4 Remove `POST /chat` (non-stream) from `api/routers/chat.py`, keeping `POST /chat/stream` and its per-turn persistence under `session_id`
- [ ] 1.5 Remove `POST /tahlil/verse` from `api/routers/tahlil.py`
- [ ] 1.6 Unmount and delete `api/routers/sessions.py` (`GET /sessions/{id}`)
- [ ] 1.7 Remove `GET /feedback/stats`, keeping `POST /feedback` and the `Store` writes behind it
- [ ] 1.8 Quarantine Madār: unmount `api/routers/madar.py` in `api/main.py`, retain the router and `api/models/madar.py`, and write the quarantine docstring (state, reason, exact rebranch step) into `madar/__init__.py`
- [ ] 1.9 Delete `frontend/src/components/MadarAslCard.tsx`, `StatusBadge.tsx` and `LexicalResult.tsx`
- [ ] 1.10 Delete `lexical()` and `madarAnalyze()` from `frontend/src/lib/api.ts` and the `LexicalResult` entry from `lib/strings.ts`
- [ ] 1.11 Remove the stale Madār assertions from `frontend/src/app/verse-study/page.test.tsx`
- [ ] 1.12 Delete the untracked scratch files `requirements.txt.bak-preuv`, `requirements-test.txt.bak-preuv`, `scripts/setup.sh.bak-preuv`, and the stray `.DS_Store` files under `data/`
- [ ] 1.13 Add the surface-parity test: mounted routes equal the endpoints the frontend calls, plus `GET /health`
- [ ] 1.14 Add a test asserting the frontend component tree is fully reachable from the nine pages and every `lib/api.ts` export has a caller
- [ ] 1.15 Checkpoint: replay 0.2, run both test suites, confirm `next build` succeeds and the six removed endpoints answer 404

## 2. Build the dataset registry against today's paths

- [ ] 2.1 Create `quran_data/` with a path constant for every dataset, pointing at **current** locations (`data/raw/…`, `data/processed/…`, `data/references/…`, `data/runtime/…`, `data/translations/…`)
- [ ] 2.2 Read `APP_DB_PATH` and `QDRANT_PATH` in the registry (resolved against `ROOT`, empty `QDRANT_PATH` still reading as unset) instead of at each call site
- [ ] 2.3 Add one lazy, process-cached loader per dataset; assert importing `quran_data` opens no file
- [ ] 2.4 Write the manifest: bucket, origin, producing step, consuming modules, regenerable — one entry per dataset
- [ ] 2.5 Make loader errors actionable: name the dataset and path, give the rebuild command for a regenerable one, name the upstream source for a non-regenerable one
- [ ] 2.6 Add the manifest-coverage test (every constant has an entry, every entry names a constant)
- [ ] 2.7 Add the `ROOT`-depth test asserting every module's computed `ROOT` is the repo root — **before** any package moves, so step 5 has a net
- [ ] 2.8 Collapse the four `quran-morphology.txt` parsers (`analysis/fassila.py`, `ingestion/qac_morphology.py`, `ingestion/root_resolver.py`, `tahlil/huruf.py`) into one loader, serving each consumer its projection from a single parse
- [ ] 2.9 Sweep every consumer onto the registry: `indexing/{corpus,bm25_index,build_index}.py`, `retrieval/{lexical_retriever,verse_lookup}.py`, `ingestion/*`, `analysis/{qlisan_data,mizan,fassila}.py`, `tahlil/{huruf,form_kb,coverage}.py`, `lisan/letter_lexicon.py`, `madar/maqayis_store.py`, `api/store.py`, `scripts/*`
- [ ] 2.10 Verify no production module builds a path into `data/` any more (remaining hits are prose only)
- [ ] 2.11 Checkpoint: replay 0.2 — nothing has moved on disk, so any diff is a sweep bug and nothing else

## 3. Move the data on disk

- [ ] 3.1 Stop the backend (embedded Qdrant lock)
- [ ] 3.2 `git mv data/raw data/source`, then `git mv data/source/eqtb data/source/treebank`
- [ ] 3.3 `mv data/processed data/derived` and `mv data/translations data/derived/translations` — **move, never copy-and-delete, never rebuild**: `data/derived/` is 69 MB whose regeneration costs an embedding run
- [ ] 3.4 `git mv analysis/data/mizan_patterns.json data/references/` and remove the now-empty `analysis/data/`
- [ ] 3.5 Update the constants in `quran_data` to the new locations — this file is the entire code-side blast radius of the move
- [ ] 3.6 Rewrite `.gitignore` to the three-entry rule: `data/derived/`, `data/runtime/`, `data/source/maqayis/`
- [ ] 3.7 Update data paths in `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `scripts/run.sh`, `scripts/ingest.sh`, `scripts/setup.sh`, `local-dev/start.sh`, `local-dev/stop.sh`, `.env.example`
- [ ] 3.8 Confirm `QDRANT_PATH=data/runtime/qdrant` and `APP_DB_PATH` still resolve — `data/runtime/` deliberately does not move, so no developer `.env` needs editing
- [ ] 3.9 Re-run the 0.3 inventory and diff: same file count, same total size, nothing under `data/derived/` regenerated
- [ ] 3.10 Checkpoint: restart the backend, replay 0.2, run both test suites

## 4. Extract the shared text primitives

- [ ] 4.1 Create `arabic_text/` and move `normalize_text` (from `ingestion/normalizer.py`), `normalize_search` (from `indexing/text_normalize.py`) and `normalize_root` (from `ingestion/root_normalize.py`) into it
- [ ] 4.2 Move the hamza-fold primitives `fold_blind` and `fold_carrier` out of the pipeline stage `ingestion/root_resolver.py` into `arabic_text/`; leave `root_resolver.py` with its stage duties only (arbitration cascade, invariants, writing `roots_resolved.json`, `load_resolved` / `same_root`)
- [ ] 4.3 Leave `ingestion/normalizer.py` with its pipeline stage `run()` only, importing `normalize_text` from `arabic_text/`
- [ ] 4.4 Define the diacritic-stripping table **once** (it is currently written out in `ingestion/normalizer.py`, `ingestion/root_normalize.py` and `indexing/corpus.py`), `\u`-escaped only — never a literal Arabic character class
- [ ] 4.5 Write the package docstring with the three-normalizer comparison table: what each does to hamza, what it is for, what it must never touch
- [ ] 4.6 Absorb `indexing/corpus.py`'s loaders into `quran_data`, keeping `strip_leading_basmala` and `surah_basmala` beside the chakl loader so the Basmala choke point stays a single point
- [ ] 4.7 Verify `chakl_by_ref()` is still **never** stripped — `analysis/qlisan_data.word_index()` and `analysis/mizan._vocalized_surface` address its rows by character offset (`2:1:1` sits at `[39, 42)`), and stripping in the loader would shift every one
- [ ] 4.8 Verify each normalizer's output is byte-identical to the pre-change output across the whole corpus
- [ ] 4.9 Checkpoint: replay 0.2 (watch the `/verse-lookup` highlight offsets and every Basmala case), run both test suites including `test_basmala_strip.py`, `test_normalizer.py`, `test_root_normalize.py`

## 5. Group the domain packages

- [ ] 5.1 Create `linguistics/` and move `analysis/`, `lisan/`, `madar/`, `tahlil/` under it, preserving every internal module name
- [ ] 5.2 Correct `parents[N]` in every moved module for its new depth — a moved module keeping its old `N` resolves to the wrong root and finds no data
- [ ] 5.3 Rewrite the 47 production import sites across `api/routers/*`, `api/models/*`, `api/main.py` and the domain packages themselves
- [ ] 5.4 Rewrite imports in the 29 local-only test files and in `tests/eval/*`; sweep the whole working tree, not `git ls-files` — `tests/`, `plans/` and `local-dev/` are git-ignored and CI is local-only, so nothing external catches a break
- [ ] 5.5 Update `pytest.ini`, `Dockerfile`, `docker-compose.yml` and the launcher scripts for the new package paths
- [ ] 5.6 Promote `retrieval.lexical_retriever._clitic_alif_candidates` to a public function and repoint `linguistics/lisan/lisan_service.py` at it
- [ ] 5.7 Verify no `from <package> import _name` remains anywhere in production code
- [ ] 5.8 Repoint the domain packages off `indexing.corpus` onto `quran_data`, ending the analysis→indexer inversion
- [ ] 5.9 Add the import-direction test over the project's own packages (shared → pipeline → api; domain may use shared and `retrieval/`, never `api/`; nothing imports `linguistics/` except `api/`)
- [ ] 5.10 Verify the `ROOT`-depth test from 2.7 still passes for every moved module
- [ ] 5.11 Checkpoint: start the backend, replay 0.2, run both test suites, and open each of the nine pages to confirm identical rendering

## 6. Documentation and dead weight

- [ ] 6.1 Rewrite the affected sections of `CLAUDE.md`: package tree, dataset paths, the three normalizers, the `app.state` wiring, the served surface, the quarantine convention
- [ ] 6.2 Update `README.md`, `scripts/README.md` and `architecture.md` for the new layout and commands
- [ ] 6.3 Point provenance documentation at the manifest instead of repeating it in module docstrings
- [ ] 6.4 Untrack `data/source/treebank/{Quran.csv,Quranic.rar,RelLabels.csv,pos.csv}` and `data/references/zero_theory_pitch_deck.pdf` (~9.5 MB), only after the manifest records the upstream archive they came from
- [ ] 6.5 Reduce `scripts/start_dev.sh` to Ollama only (decision R1), with a comment stating that Qdrant runs embedded under `QDRANT_PATH` and that starting its container re-creates the Docker memory reservation documented as the cause of a hard machine freeze
- [ ] 6.6 Add an index line to `CLAUDE.md` pointing at `documentation/root-lookup.md` and `documentation/root-highlight-alignment-issue.md` (decision R3) — neither file is deleted; the second holds the live diagnostic for the unresolved highlight-alignment bug
- [ ] 6.7 Leave `requirements.txt` untouched (decision R4): `httpx` is required by FastAPI's `TestClient` and by the step-0 parity harness, `transformers` is a legitimate transitive pin
- [ ] 6.8 Delete `eval/` (decision R2, 1.2 GB, git-ignored, cross-source investigation concluded) — **before running the irreversible step, surface once more that `eval/roots/scripts/` is only 148 KB yet holds `build_arbitration.py` and `validate_arbitration.py`, which produce and validate the shipped `data/references/root_arbitration.json`; `ingestion/root_resolver.py` raises rather than writing on an unarbitrated disagreement, so a future corpus update needs them. Deleting `work/`, `sources/`, `.venv-camel/` and the bulk dumps reclaims essentially all 1.2 GB. Then do what the user says.**
- [ ] 6.9 Confirm after the deletion that `data/references/root_arbitration.json` is still present and tracked, and that `python -m pytest -q` is unaffected

## 7. Final verification

- [ ] 7.1 Fresh-clone check: confirm the shipped repo still builds from what is committed, with no reference to a git-ignored path
- [ ] 7.2 Cold-start check: `GET /health` answers with `models: {embedder: false, search_reranker: false}` — the lazy-model discipline survives the restructure and a backend serving only the lexical paths holds no model memory
- [ ] 7.3 Full replay of 0.2 against the finished tree: every response identical to the baseline
- [ ] 7.4 Walk all nine frontend pages and the six nav entries; confirm identical behaviour, including the `/surah` resume position and the deep links from `VerseCard`
- [ ] 7.5 Confirm the quarantine holds: `POST /madar/analyze` returns 404 while `python -m pytest tests/test_madar.py` passes
- [ ] 7.6 Confirm the toggles still work: `RERANK_ENABLED=1`, `HYDE_ENABLED=1`, `QAC_STEMMER_FALLBACK=1`, `ROOT_CHANNEL_ENABLED=0` each change behaviour as documented
- [ ] 7.7 Verify `python ingestion/run_pipeline.py` and `python indexing/build_index.py` still run end-to-end against the new layout — with the backend stopped, and into a scratch copy so the 69 MB derived set is never overwritten by the test
- [ ] 7.8 Sequence against the in-flight `migrate-llm-qwen-to-jais` change: it touches `generation/llm_client.py` and overlaps `POST /chat` — land these removals first or rebase it, never run both against `api/routers/chat.py` concurrently
