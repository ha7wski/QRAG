## Context

The repo runs correctly; nothing here fixes a bug. What has drifted is the *map*. An audit of the
current tree against what the nine frontend pages actually call found:

- **22 mounted routes, 15 consumed.** `POST /lexical`, `POST /lexical/stream`, `POST /madar/analyze`,
  `POST /chat`, `POST /tahlil/verse`, `GET /sessions/{id}`, `GET /feedback/stats` have no caller.
- **A dead object holding live wiring.** `app.state.lexical_analyzer` exists for `/lexical` — a route
  no page calls — yet it owns the `LexicalRetriever` that `/lisan`, `/madar`, `VerseLookup` and
  `SimilarVerses` all borrow. The naive cleanup (delete the route and its analyzer) breaks four
  features; the naive audit (it's on `app.state`, it must be used) keeps a dead route forever.
- **~20 hand-rolled data paths**, 4 independent parsers of `quran-morphology.txt`, 6 modules touching
  `quran_chakl.csv`, and the diacritic-stripping table written out three times
  (`ingestion/normalizer.py`, `ingestion/root_normalize.py`, `indexing/corpus.py`).
- **A layering inversion.** `analysis/`, `tahlil/` and `retrieval/` import `indexing.corpus` to read a
  verse — analysis packages importing the *indexer* to get at data.
- **A private name crossing a package boundary.** `lisan/lisan_service.py` imports
  `retrieval.lexical_retriever._clitic_alif_candidates`.
- **~9.5 MB of committed files nothing reads** (`Quran.csv`, `Quranic.rar`, `RelLabels.csv`, `pos.csv`,
  `zero_theory_pitch_deck.pdf`), one dataset outside `data/` (`analysis/data/mizan_patterns.json`), and
  three untracked `.bak-preuv` scratch files.

Constraints that shape everything below:

- **`data/derived/` is 69 MB whose rebuild costs an embedding run** over 6236 verses. The change must
  *move* it, never regenerate it.
- **Qdrant embedded takes an exclusive file lock.** The backend and `build_index.py` cannot both hold
  `data/runtime/qdrant`. Any step that touches it requires the backend stopped.
- **The test suite is local-only and partial.** 37 pytest files, but only 6 exercise the API through
  `TestClient`. Tests alone cannot prove the app still works.
- **`tests/`, `plans/`, `local-dev/`, `CLAUDE.md`, `architecture.md` are git-ignored** — they live on
  disk but never ship. They must still be migrated, or the local workflow breaks silently while CI
  (also local-only) shows nothing.

## Goals / Non-Goals

**Goals:**

- The mounted HTTP surface equals the consumed surface, and a test keeps it that way.
- One authority for dataset paths, one loader per dataset, one manifest for provenance.
- A `data/` tree whose shape states what is safe to delete.
- Package grouping that distinguishes pipeline from domain, with enforced import direction.
- Every import in the repo — shipped and local-only — updated in the same change, app running at
  the end of every step.

**Non-Goals:**

- No retrieval, ranking, generation or rendering behaviour changes. Byte-identical output is the
  acceptance bar, not an aspiration.
- No dependency upgrades, no Qdrant/Ollama topology change, no new features.
- No deletion of off-by-default quality levers (HyDE, rerankers, root channel, gated stemmer).
- No deletion of Madār. It is quarantined, and quarantine is reversible.
- No public-repo policy change: what is git-ignored today stays git-ignored.

## Decisions

### D1 — Introduce the registry with the *old* paths, then flip one constant

The obvious order (move the files, then fix the code) makes a 69 MB move and a ~20-module sweep land
in one unverifiable step: if the app breaks afterwards, the cause could be either.

Instead: build `quran_data/` first with its constants pointing at **today's** locations
(`data/raw/…`, `data/processed/…`). Sweep every consumer onto the registry. Verify the app is
byte-identical — nothing has moved, so any difference is a sweep bug and nothing else. *Then* move the
files on disk and change the constants, in one small commit whose entire blast radius is one file.

This buys the single most valuable property in a migration: **at every checkpoint, exactly one class of
thing has changed.**

*Alternative considered:* compatibility symlinks from old paths to new. Rejected — symlinks would
survive into the tree and quietly re-permit hand-built paths, defeating the requirement.

### D2 — `quran_data`, not `datasets`

`pytest.ini` sets `pythonpath = .`, putting the repo root ahead of `site-packages`. A top-level
`datasets/` package would shadow HuggingFace's `datasets` — not installed today, but an optional
dependency of `transformers` and `sentence-transformers`, so any future upgrade could pull it in and
fail with an import error pointing at neither package. `quran_data` cannot collide.

The same reasoning rules out `data/` as a package name (it would collide with the `data/` directory)
and `corpus/` (already the name of the module being absorbed, `indexing/corpus.py`).

### D3 — `arabic_text/` holds all three normalizers, and one diacritic table

The project's most repeated footgun is choosing the wrong normalizer: `normalize_text` deletes hamza
(أشده → شده) and must never touch roots or matching; `normalize_search` folds carriers without
deleting; `normalize_root` folds but never deletes. Today they live in three packages
(`ingestion/`, `indexing/`, `ingestion/`), so nothing puts the choice in front of the reader.

Putting all three in one package with a comparison table in the package docstring makes the wrong
choice visible at the moment it is made. The hamza-fold primitives `fold_blind` / `fold_carrier` move
with them, out of the pipeline stage `root_resolver.py` that currently exports them to two runtime
consumers.

The diacritic class is defined **once** and stays `\u`-escaped: a literal Arabic class is unreviewable
under bidi reordering and silently eats letters — a hazard the repo already guards in
`tests/test_basmala_strip.py`.

*Alternative considered:* leave the normalizers where they are and only deduplicate the table.
Rejected — the duplication is a symptom; the scattering is the defect.

### D4 — `linguistics/` groups the four engines; pipeline packages do not move

Ten sibling directories give no clue that `tahlil/` is a feature engine while `indexing/` is a pipeline
stage. Grouping the four linguistic engines under `linguistics/` (keeping their internal module names)
makes the distinction legible and costs one mechanical rewrite: 47 production import sites, 29 test
files.

Pipeline packages keep their names and positions — `ingestion → indexing → retrieval → generation → api`
already reads as the order it is. Moving them would multiply the blast radius for no legibility gain.

*Alternative considered:* move everything under `src/` or `quran_rag/`. Rejected as the larger,
riskier change for a benefit (namespace hygiene) this project does not need — it is not packaged or
installed, and `pythonpath = .` already works.

### D5 — Quarantine is a documented state, not a deletion or a comment

Madār is complete, tested, and was integrated into Verse Study (commit `bc14808`) before being pulled
when the LLM synthesis proved unreliable on witness roots. Deleting it discards sound
sourced-`aṣl` machinery; leaving it mounted keeps a route with no caller.

Quarantine = router retained but unmounted, models retained, service and tests retained, frontend
components deleted, and a docstring in `linguistics/madar/__init__.py` stating the state, the reason,
and the exact rebranch step. Rebranching costs one `include_router` line.

The curated `data/references/maqayis_asl.csv` stays: it is reference scholarship, not a build artefact
of a dormant feature.

### D6 — The oracle is a recorded route-parity snapshot, not the test suite

Only 6 of 37 test files touch the API. Tests cannot prove "the app still works" for a change of this
shape. Before touching anything, record real responses for a fixed request set covering all 15
consumed endpoints — including the awkward ones the project has already been bitten by: a Basmala-
prefixed āya 1 (`2:1`), al-Fātiḥa where the Basmala genuinely *is* āya 1, at-Tawba which has none, a
hamzated root (`لؤلؤ`), a contested root (ٱلنَّاس → `أنس`/`نوس`), and a multi-root phrase query that
exercises the `/search` AND-coverage path.

Replay after each checkpoint and diff. This catches exactly what a refactor breaks and unit tests miss:
a shifted highlight offset, a Basmala re-appearing, a root resolving through the wrong fold.

The pool caps in `api/routers/search.py` are load-bearing for quality (shrinking the reranked pool
craters Hit@10 from 1.00 to 0.78), so the snapshot must include `/search` results in order, not just
status codes.

### D7 — `data/references/` and `data/runtime/` keep their exact paths

Only `raw/` → `source/`, `processed/` → `derived/`, `translations/` → `derived/translations/` move.
`references/` already says what it holds; renaming it to match a singular-plural convention would move
7 tracked files for aesthetics. `runtime/` keeping its path is worth more: `QDRANT_PATH=data/runtime/qdrant`
and `APP_DB_PATH` in every `.env` on every machine stay valid, so no developer has to touch their
environment and the embedded Qdrant collection is never relocated under its own lock.

### D8 — Deletions are staged by reversibility

Removing routes and orphaned components is cheap to undo (git) and independently verifiable, so it goes
**first** — it shrinks the surface the rest of the migration has to carry. Untracked scratch files
(`*.bak-preuv`) go with it. Untracking the ~9.5 MB of unread committed data goes **last**, after the
manifest exists to record the provenance those files currently carry by existing.

## Risks / Trade-offs

**[The 69 MB derived set is lost or half-moved, forcing an embedding rebuild]** → Move with `mv`, never
`cp` + delete, and never a rebuild. Verify the file count and total size before and after. Take a
`data/derived/` inventory (name + size + mtime) as part of the pre-change snapshot. The backend must be
stopped for the move — Qdrant's exclusive lock makes a live move a corruption risk.

**[A moved module keeps its old `parents[N]` and silently resolves to the wrong root]** → This is the
single most likely breakage: `linguistics/tahlil/huruf.py` is one level deeper than `tahlil/huruf.py`,
so `parents[1]` must become `parents[2]`. It fails as "dataset not found" — or worse, finds nothing and
returns empty. Mitigation: a test asserting every module's computed `ROOT` equals the repo root, added
*before* any package moves.

**[Import direction regresses later]** → The enforced-direction test (spec `module-layout`) is written
as part of this change, not left as a convention.

**[A route removal breaks something the audit missed]** → The audit covered `lib/api.ts`, all raw
`fetch` calls, and every page and component. The residual risk is an external caller. There is none:
the repo ships the only frontend, and `CORS_ORIGINS` is `http://localhost:3000`. Removals are one
commit, revertible on its own.

**[Local-only files (`tests/`, `plans/`, `local-dev/`) are forgotten because CI is also local-only]** →
`.github/workflows/test.yml` never runs on GitHub, so nothing external catches a broken local suite.
The migration sweep must run over the whole working tree, not `git ls-files`.

**[Collision with the in-flight `migrate-llm-qwen-to-jais` change]** → It touches
`generation/llm_client.py`; `generation/` does not move here. The overlap is `POST /chat`, removed here.
Sequence: land this change's route removals first, or rebase that change onto the reduced surface —
do not run both against `api/routers/chat.py` concurrently.

**[Trade-off: churn for a repo with one developer]** → The change touches most of the tree while adding
no feature. Accepted deliberately: the cost compounds with every feature written against a map that no
longer matches the territory, and the audit found the gap already wide enough to hide a dead route
holding live wiring.

## Migration Plan

Six checkpoints. **The app must start and serve all 15 consumed routes at the end of each one**, and the
route-parity snapshot (D6) is replayed at each. Each checkpoint is one commit, independently revertible.

0. **Snapshot.** Record route-parity responses for the fixed request set; record the `data/` inventory;
   record `pytest -q` and `npx vitest run` baselines (including which tests already fail, if any).
1. **Remove.** Unmount and delete the 6 unreachable routes and their models; quarantine Madār; delete
   the 3 orphaned frontend components, the 2 dead `lib/api.ts` clients, the `LexicalResult` string
   entry, the stale Madār assertions in `verse-study/page.test.tsx`, and the `.bak-preuv` files.
   Publish the shared `LexicalRetriever` on `app.state` under its own name *before* touching
   `lexical_analyzer` — this is the step where the dead-object-holding-live-wiring trap fires.
2. **Registry, old paths.** Add `quran_data/` (constants + loaders + manifest) pointing at current
   locations. Sweep all ~20 consumers onto it. Collapse the 4 QAC morphology parsers into one. Add the
   manifest-coverage test and the `ROOT`-depth test. *Nothing has moved on disk.*
3. **Move the data.** Backend stopped. `git mv data/raw → data/source`, `mv data/processed → data/derived`,
   `mv data/translations → data/derived/translations`, `git mv analysis/data/mizan_patterns.json →
   data/references/`. Update the constants in `quran_data` and the paths in `.gitignore`, `Dockerfile`,
   `docker-compose.yml`, `scripts/*.sh`, `local-dev/*.sh`, `.env.example`.
4. **`arabic_text/`.** Extract the three normalizers and the fold primitives; define the diacritic table
   once. Absorb `indexing/corpus.py`'s loaders into `quran_data`, keeping `strip_leading_basmala` /
   `surah_basmala` with the chakl loader so the Basmala choke point stays a single point.
5. **`linguistics/`.** Move the four domain packages; rewrite all 47 production import sites and 29 test
   files; correct every `parents[N]`; promote `_clitic_alif_candidates`; add the import-direction test.
6. **Docs and dead weight.** Update `CLAUDE.md`, `README.md`, `scripts/README.md`, `architecture.md`.
   Untrack the ~9.5 MB of unread committed files, provenance now recorded in the manifest.

**Rollback.** Checkpoints 1, 2, 4, 5, 6 are pure git reverts. Checkpoint 3 additionally needs the
reverse `mv` for the git-ignored `data/derived/` and `data/runtime/` trees — write those exact commands
into the commit message, because git will not restore them.

## Resolved Questions

**R1 — `scripts/start_dev.sh` is reduced to Ollama only.** The 8-line helper runs
`docker compose up -d qdrant ollama` unconditionally. With `QDRANT_PATH` set — the current `.env` — that
starts a Qdrant container the backend will not use, re-creating the Docker Desktop memory reservation
documented as the cause of a hard machine freeze. Both real launchers already skip it correctly.
Decided: keep the shortcut, drop the trap. The script starts Ollama only, with a comment saying why
Qdrant is no longer there.

**R2 — `eval/` is deleted in full.** 1.2 GB on disk: a vendored virtualenv (`.venv-camel`), 98 MB of
per-source comparison dumps (`work/`), 32 MB of downloaded `sources/`, and 148 KB of scripts. It is
git-ignored, so the published repo is unaffected, and the cross-source investigation it served is
concluded — the verdict was that QAC alone suffices and no majority vote is needed.

⚠️ **Carry this into the deletion step:** the 148 KB `eval/roots/scripts/` directory is 0.01% of the
size but holds `build_arbitration.py` and `validate_arbitration.py`, which produce and **validate**
`data/references/root_arbitration.json` — a file that ships. `ingestion/root_resolver.py` *raises*
rather than writing when a disagreement is unarbitrated, so any corpus update will force new
arbitration entries with no validator left to check them. Deleting `work/`, `sources/`, `.venv-camel/`
and the bulk TSV/JSON dumps reclaims essentially all 1.2 GB; keeping the scripts costs 148 KB. The
implementer SHALL surface this trade-off once more before the irreversible step, and defer to the
user's answer then.

**R3 — the two `documentation/` files are kept and indexed.** Both are substantive and current:
`root-lookup.md` (211 lines) documents the «Word in Verses» pipeline end to end, and
`root-highlight-alignment-issue.md` (127 lines) holds the full diagnostic and measurements for an
**unresolved, deliberately reverted** highlighting bug (`فتى` lists 12:30 but does not highlight
`فَتَاهَا`), explicitly preserved "for whoever picks the subject up". Nothing is deleted; the defect is
only that `CLAUDE.md` never points at them, so they are invisible. Decided: add an index line.

**R4 — `httpx` stays; no dependency is removed.** It is absent from production imports but required by
FastAPI's `TestClient`: `tests/test_madar.py`, `tests/test_fassila_overview.py` and others guard on
`pytest.importorskip("httpx")`, and the route-parity harness in step 0 needs it too. `transformers` is a
legitimate transitive pin for `sentence-transformers`. `requirements.txt` is left alone.

## Open Questions

1. **`api/models/lexical.py`** — delete with its routes, or retain like the Madār models? The Madār
   models are retained because the feature is quarantined for possible return; the lexical route is
   superseded by `/lisan/analyze`, which suggests deletion. Assumed: delete.
