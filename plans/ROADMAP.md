# Roadmap — What's left to finish the app

Ordered by priority. The MVP (F1 chat + F2 lexical) works end to end; the items below harden
it and build the remaining features (F3–F6) and the production/ops layer. File pointers are
relative to repo root.

---

## P0 — Harden the working MVP

- [x] **Unit tests (safety net).** Vitest in `frontend/` (`conversations.test.ts`, 17 cases) +
  pytest in `tests/` (`test_normalizer.py`, `test_rrf.py`, `test_lexical.py`, 22 cases): pure logic,
  offline, no Qdrant/Ollama/network. Light CI in `.github/workflows/test.yml`. _(2026-06-17)_
  Follow-ups: parser-schema tests, and a component test for `ChatInterface` (RTL harness is wired).
- [x] **Conversation persistence (frontend).** Multi-conversation history in `localStorage`
  (`frontend/src/lib/conversations.ts`): auto-restore on load, auto-titled, conversation switcher
  + delete + "New", sources persisted too. Streaming/backend untouched. _(2026-06-17)_
- [x] **Conversation persistence (backend).** SQLite store (`api/store.py`, default
  `data/runtime/app.db`): each chat turn (question + answer + cited sources) is appended under
  `session_id`. The chat router honors `session_id` as a history fallback when the client sends
  no inline history (multi-device / localStorage wipe), and `GET /sessions/{id}` reads it back.
  The frontend reuses its conversation id as the `session_id`. _(2026-06-19)_
- [x] **Frontend resilience.** `HealthBanner` polls `/health` and surfaces `degraded`/`starting`/
  unreachable states; assistant turns with no retrieved verses show a "general answer" note;
  streaming failures persist the partial answer and offer a **Retry**. _(2026-06-19)_
- [x] **Feedback signal (👍/👎).** `POST /feedback` (+ `GET /feedback/stats`) persisted to SQLite,
  keyed by `(session_id, message_index)` with upsert; thumbs UI under each completed answer.
  _(2026-06-19)_
- ~~**Fill `transliteration`.**~~ **Removed from scope** _(2026-06-19)_: the data has no harakat
  and no transliteration source, and no current UI consumes the field. Re-introduce alongside F5
  (study mode), which is its only real consumer.

## P1 — Complete the planned API surface

- [x] **`GET /verse/{surah}/{ayah}`** — single verse + neighbor context (`window`) + adjacent
  verse ids, via `Retriever.get_by_ref`/`prev_next` (`api/routers/verse.py`). Frontend page
  `/verse/[surah]/[ayah]` with prev/next navigation. _(2026-06-19)_
- [x] **`GET /surah/{number}`** — full surah (ordered verses + metadata) via `Retriever.get_surah`.
  Frontend page `/surah/[number]` with surah-to-surah navigation. _(2026-06-19)_
- [x] **Deep-linking wired:** `VerseCard` reference `[s:a]` links to the verse page and the surah
  name to the surah page (by number, not text). _(2026-06-19)_
- ~~**F4 — Translation comparison.**~~ **Removed from scope** _(2026-06-19)_ at the user's
  request. FR/EN translations remain ingested/indexed and are shown inline on each `VerseCard`;
  a dedicated side-by-side compare view is not planned.

## P2 — F3 Thematic exploration

- [ ] **Theme enrichment.** `themes` is empty (`[]`) on every verse. Tag verses with themes
  (curated list or clustering) in `ingestion/enricher.py`; re-run pipeline + `build_index --rebuild`.
- [ ] **`GET /themes`** endpoint (themes with counts + representative verses) and theme-filtered
  search (Qdrant payload filter on `themes`).
- [ ] **Frontend `/themes`** page: theme map, theme→verses browse, and makki/madani distribution
  visualization for a theme.

## P3 — F5 Study mode & F6 Export/share

- [ ] **F5 — Study/memorization:** verse selection, auto flashcards (Arabic + transliteration),
  context quiz ("previous/next verse?"), progress tracking.
- [ ] **F6 — Export/share:** formatted citation copy (verse + translation + reference), PDF export
  of a session, shareable result links.

## P4 — Retrieval quality

- [ ] **Attack the hard abstract-theme cases** flagged in `tests/eval/EVAL_REPORT.md`
  (`fr-creation`, `en-judgment`, `en-parents`, `ar-jannah`, `fr-jugement`, `fr-priere`): these
  return nothing in both configs. Levers: more aggressive query expansion, HyDE on by default for
  abstract queries, gold-set refinement.
- [ ] **Reranker policy.** It improves every metric but is off for cost (~2.3 GB + CPU latency).
  Decide: enable by default, switch to `bge-reranker-base`, or gate by query type. Track the
  P95 < 5s target from `project_summary.md`.
- [ ] **Grow the eval set** beyond 50 questions; keep gold sets verified (`verify_gold.py`).

## P5 — Production / ops

- [ ] **Dockerfiles are missing.** `docker-compose.yml` references `build: .` and `build: ./frontend`
  but neither `Dockerfile` exists, so the containerized backend/frontend won't build. Either add
  them (for deployment) or trim the compose file to the infra services (Qdrant/Ollama) that
  `local-dev` actually uses.
- [ ] **Auth + rate limiting.** `api/middleware.py` does logging only; `architecture.md` notes
  auth/rate-limiting as "future".
- [ ] **CI** (lint + tests + an eval smoke run) and basic observability/analytics.
- [ ] **Deployment target** — pick where this runs (GPU for the LLM/reranker changes the cost
  math) and document it.

---

### Suggested next 3

P0 and P1 are now complete (F4 and `transliteration` removed from scope). Remaining, in order:

1. P2 theme enrichment (unblocks F3, the biggest unbuilt feature).
2. P4 retrieval quality — attack the abstract-theme cases that return empty + decide the
   reranker policy (P95 < 5s).
3. P5 ops — add the missing Dockerfiles (or trim `docker-compose.yml` to infra services), then CI.
