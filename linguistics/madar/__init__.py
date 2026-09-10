"""
madar/ — Sourced lexical reading of an Arabic root (the *madār*, the pivot).

════════════════════════════════════════════════════════════════════════════
QUARANTINED — complete, tested, and deliberately OFF the served surface.
════════════════════════════════════════════════════════════════════════════

This subsystem is not reachable from the product. `POST /madar/analyze` answers
404 because `api/routers/madar.py` is imported but not mounted in `api/main.py`,
and the frontend keeps no Madar component or client function.

WHY it is dormant, precisely: the *LLM synthesis* of the pivot proved unreliable
on witness roots — roughly half of the sampled syntheses were problematic — so
the Verse Study integration that fronted it was pulled rather than shipped with a
generated reading a reader could mistake for a sourced one. The failure is in the
generation, not in the machinery: **the sourced-aṣl path is sound**. Ibn Fāris'
cited aṣl from `MaqayisStore`, the root's Quranic occurrences, the strict
separation of verified from generated — all of that is finished, tested
(`tests/test_madar.py`) and worth keeping. Synthesis is already off by default
(`MADAR_SYNTHESIS_ENABLED`), so the intact half runs on its own.

Quarantine, not deletion, is the point: this is working scholarship-backed code
whose UI question is unresolved, not code that was wrong.

WHAT IS DORMANT, EXACTLY — this package is NOT dead code, and the distinction
matters because deleting it would break a route that is served today.

    madar_service.py   DORMANT — nothing constructs MadarService except the
                       unmounted router and tests/test_madar.py.
    maqayis_store.py   **LIVE.** `linguistics/tahlil/evidence.py::_maqayis()`
                       builds a MaqayisStore on every Tahlil analysis, so it sits
                       on the POST /tahlil/word request path — a mounted, consumed
                       route. Ibn Faris' cited asl reaches the reader through
                       Tahlil even with Madar off the surface.

So: the ROUTE and the SERVICE are quarantined. The store beneath them is a
shared reference reader that Tahlil depends on. `data/references/maqayis_asl.csv`
is retained for the same reason, on top of being curated scholarship rather than
a build artefact of a dormant feature.

HOW TO REBRANCH IT — exactly one line. In `api/main.py`, next to the other
`include_router` calls, add:

    app.include_router(madar_router.router)

`madar_router` is already imported there. Nothing else moves: the router reads
the shared `app.state.lexical_retriever` and `app.state.engine.llm`, both of
which the lifespan already builds, so no lifespan change is needed either. The
frontend components and the `madarAnalyze` client were removed and would have to
be written again.

════════════════════════════════════════════════════════════════════════════

Epistemic sibling of `lisan/`, and its inverse: where `lisan/` gives an
INTERPRETIVE letter-symbolism reading, `madar/` gives a SOURCED lexical one —
Ibn Fāris' canonical *aṣl* (cited, verified) + the root's Quranic occurrences
(empirical proof) + an optional, clearly-flagged LLM synthesis of the pivot.

Strict separation of epistemic status is the whole point: the cited aṣl and the
generated synthesis never bleed into each other, in the data or the UI. This
package does not modify `lisan/`; it reuses the shared QAC resolver.
"""
