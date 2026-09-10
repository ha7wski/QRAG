## ADDED Requirements

### Requirement: Every mounted route has a real consumer

A route SHALL be mounted only if something in the shipped product calls it: a frontend page, another
backend component, or a documented operational need. A route reachable only from a test, or only from
a client function no page imports, SHALL NOT be mounted.

The surface after this change is exactly what the nine frontend pages call:

| Route | Called by |
|---|---|
| `POST /chat/stream` | `ChatInterface` |
| `POST /feedback` | `ChatInterface` |
| `GET /health` | `HealthBanner` |
| `GET /search` | Verse Study → «آيات مشابهة» |
| `POST /verse-lookup` | Verse Study → «الكلمة في الآيات» |
| `GET /verse/{surah}/{ayah}` | Verse Study, `/verse/[surah]/[ayah]` |
| `GET /surah/{number}`, `GET /surahs` | `SurahReader`, Fassila, QLisan, Tahlīl, Verse Study |
| `GET /fassila/{surah}`, `GET /fassila/overview` | Fassila tabs |
| `POST /lisan/analyze` | «تحليل اللسان» page |
| `POST /qlisan/word`, `POST /qlisan/form`, `GET /qlisan/verse/{s}/{a}` | QLisan page, Tahlīl page, «تحليل اللسان» page |
| `POST /tahlil/word`, `POST /tahlil/review` | Tahlīl page |

`GET /health` is mounted on operational grounds — the frontend banner reads it, and it is the
documented readiness probe.

#### Scenario: The mounted surface matches the consumed surface

- **WHEN** the mounted routes are compared against the endpoints the frontend calls
- **THEN** the two sets SHALL be equal, apart from `GET /health`
- **AND** a test SHALL assert this so a route cannot be mounted without a consumer

#### Scenario: A page's behaviour is unchanged

- **WHEN** each of the nine pages is exercised after the change
- **THEN** every request it makes SHALL succeed
- **AND** its rendered output SHALL be identical to before

### Requirement: Routes no page calls are removed

The following SHALL be unmounted and their handlers deleted, because no page calls them:

- `POST /lexical` and `POST /lexical/stream` — the LLM lexical analysis. The «تحليل اللسان» page that
  appears to own them in fact calls `POST /lisan/analyze` by direct fetch.
- `POST /chat` — the non-streaming chat. The chat page uses `POST /chat/stream` only.
- `POST /tahlil/verse` — no page calls it; the Tahlīl page uses `/tahlil/word` and `/tahlil/review`.
- `GET /sessions/{session_id}` — no page reads it. Conversation history is kept client-side in
  `lib/conversations.ts`.
- `GET /feedback/stats` — no page reads it.

`POST /chat/stream` SHALL keep persisting each turn under `session_id`, and `POST /feedback` SHALL keep
writing to the store: the SQLite store and its `Store` class stay, unchanged. Only the read endpoints
over them go.

**BREAKING**: any client outside this repo calling those six endpoints will receive 404. There is no
such client today — the repo ships the only frontend, and it calls none of them.

#### Scenario: The removed endpoints are gone

- **WHEN** any of the six removed endpoints is requested
- **THEN** the backend SHALL answer 404

#### Scenario: Chat and feedback still persist

- **WHEN** a chat turn is streamed and feedback is submitted
- **THEN** both SHALL be written to the store as before
- **AND** `data/runtime/app.db` SHALL contain the same records it would have before the change

#### Scenario: Removing the lexical routes does not disturb the analyzer's borrowers

- **WHEN** `POST /lexical` and `POST /lexical/stream` are removed
- **THEN** `/lisan/analyze`, `/madar/analyze`'s successor state, `POST /verse-lookup` and `GET /search`
  SHALL keep working
- **AND** the shared `LexicalRetriever` they depend on SHALL still be built exactly once at startup

### Requirement: A complete but unwired subsystem is quarantined, not deleted

When a subsystem is finished and tested but no longer reachable from the product, it SHALL be
**quarantined**: taken off the production path while kept intact and runnable. Quarantine SHALL mean
the router is not mounted, its frontend components are removed, and its service package and tests stay
in the repo with a header stating why it is dormant and what rebranching costs.

Madār SHALL be quarantined — but the boundary matters, because reading it too widely would break a
route that is served. What is dormant is the **route and its service**: `api/routers/madar.py`,
`api/models/madar.py`, `linguistics/madar/madar_service.py` and `tests/test_madar.py`.
`linguistics/madar/maqayis_store.py` is **NOT** dormant: `linguistics/tahlil/evidence.py` builds a
`MaqayisStore` on every Tahlīl analysis, so it sits on the `POST /tahlil/word` request path. Ibn
Fāris' cited aṣl still reaches the reader through Tahlīl with Madār off the surface. The package
SHALL NOT be deleted as dead code. Its Verse Study integration was pulled after the LLM synthesis proved unreliable on
witness roots; the sourced-`aṣl` machinery behind it is sound and worth keeping.

`api/routers/madar.py` and `api/models/madar.py` SHALL be retained but unmounted, so rebranching is one
`include_router` line rather than a rewrite.

`data/references/maqayis_asl.csv` SHALL be retained: it is curated scholarship in the reference bucket,
not a build artefact, and `scripts/build_maqayis_dataset.py` remains its documented producer.

#### Scenario: Madār is off the surface but intact

- **WHEN** the backend starts
- **THEN** `POST /madar/analyze` SHALL answer 404
- **AND** `linguistics/madar/`, `api/routers/madar.py`, `api/models/madar.py` and `tests/test_madar.py`
  SHALL still exist
- **AND** `python -m pytest tests/test_madar.py` SHALL pass

#### Scenario: A second subsystem is quarantined on the same terms

- **WHEN** the Tahlīl verse layer is considered
- **THEN** `POST /tahlil/verse` SHALL be unmounted, no page having called it
- **AND** `tahlil_service.analyze_verse` and everything it alone reaches SHALL be retained intact,
  together with `prompts.build_verse_message`, `TahlilGenerator.verse()` and
  `citations.validate_verse`, which serve that entry point and nothing else
- **AND** its tests SHALL keep running, so a dormant feature cannot decay into one nobody can
  rebranch
- **AND** the notice at §10 of `linguistics/tahlil/tahlil_service.py` SHALL state the state, the
  reason and the exact rebranch step, including the two request/response models that must return
  with the route

#### Scenario: The quarantine states its own terms

- **WHEN** a developer opens `linguistics/madar/__init__.py`
- **THEN** its docstring SHALL state that the subsystem is quarantined, why, and the exact step to
  rebranch it

#### Scenario: The frontend keeps no trace of it

- **WHEN** the frontend is built
- **THEN** `MadarAslCard.tsx` and `StatusBadge.tsx` SHALL NOT exist
- **AND** `madarAnalyze` SHALL NOT exist in `lib/api.ts`
- **AND** no page SHALL reference Madār
- **AND** the stale Madār assertions in `verse-study/page.test.tsx` SHALL be removed with it

### Requirement: Off-by-default quality toggles are kept

A component that is disabled by an environment toggle SHALL NOT be treated as unused. HyDE
(`HYDE_ENABLED=0`), the retrieval reranker (`RERANK_ENABLED=0`), the `/search` cross-encoder
(`SEARCH_RERANK_ENABLED`), the root channel (`ROOT_CHANNEL_ENABLED=1`) and the gated legacy stemmer
(`QAC_STEMMER_FALLBACK=0`) SHALL all remain, with their toggles unchanged.

These are dormant levers with measured value — reranking improves every metric on the eval set and is
off for cost, not quality — and the offline evaluation harness under `tests/eval/` still exercises them.

#### Scenario: Toggled components survive the cleanup

- **WHEN** the change is complete
- **THEN** `retrieval/hyde.py`, `retrieval/reranker.py`, `retrieval/root_channel.py` and the gated
  stemmer path SHALL still exist and still be reachable through their toggles
- **AND** setting `RERANK_ENABLED=1` or `HYDE_ENABLED=1` SHALL work exactly as before

#### Scenario: The legacy stemmer keeps its gate

- **WHEN** `QAC_STEMMER_FALLBACK=1` is set and a word absent from the QAC corpus is resolved
- **THEN** the legacy stemmer path SHALL still be reached
- **AND** `tashaphyne` SHALL remain a declared dependency

### Requirement: Dead frontend code is removed with its backend counterpart

Frontend components and API-client functions that no page imports SHALL be deleted in the same change
as the endpoints they call, so neither side is left pointing at the other's absence.

`LexicalResult.tsx` (whose own string table already records that the restructure deletes it),
`MadarAslCard.tsx`, `StatusBadge.tsx` (reachable only through `MadarAslCard`), and the `lexical()` and
`madarAnalyze()` clients in `lib/api.ts` SHALL be removed, together with the `LexicalResult` entry in
`lib/strings.ts`.

#### Scenario: No orphaned component remains

- **WHEN** the frontend component tree is walked from the nine pages
- **THEN** every file under `frontend/src/components/` SHALL be reachable
- **AND** every exported function in `lib/api.ts` SHALL be called by at least one page or component

#### Scenario: The build and type-check stay clean

- **WHEN** `next build` runs after the deletions
- **THEN** it SHALL succeed with no unresolved import
- **AND** the Vitest suites SHALL pass
