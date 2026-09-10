"""Tahlil endpoints: the five-block per-word analysis (الحروف → صرفي → نحوي → دلالي → تركيب).

Two routes: `POST /tahlil/word` (the analysis) and `POST /tahlil/review` (an expert marking
one analysis reviewed).

The verse-level route is gone: no page ever called it, so it was unmounted with the rest of
the unconsumed surface. `tahlil_service.analyze_verse` — the synthesis itself, and its whole
gate — is untouched and still covered by `tests/test_tahlil_service.py`; only the HTTP door
in front of it was removed, so serving the verse synthesis again is a handler, not a rebuild.

**Word selection reuses `GET /qlisan/verse/{surah}/{ayah}`** — there is deliberately no
second alignment path here. That endpoint returns the vocalized verse with QAC-aligned
token spans, so the `word` index a client sends back IS the QAC `word_id` by construction;
a second aligner would be a second chance to disagree with the treebank.

Like `api/routers/qlisan.py`, this layer only validates input and maps errors to HTTP
status. `tahlil/` is pure stdlib and `analysis/word_analysis.py` is cached-dict-light, so
no heavy service goes on `app.state` — the router calls the service directly. The SQLite
`Store` (cache + review state) IS shared, and is read defensively: an app assembled without
one still serves analyses, uncached and un-reviewed.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api.models.tahlil import (
    TahlilReviewRequest,
    TahlilReviewResponse,
    TahlilWordRequest,
    TahlilWordResponse,
)
from tahlil.tahlil_service import analyze_word, review_key

router = APIRouter(tags=["tahlil"])


def _store(request: Request):
    """The shared SQLite store, or None. Absence degrades, never fails."""
    return getattr(request.app.state, "store", None)


def _generator():
    """The shared prose generator, or None. **Both routes must use this one accessor.**

    `review_key` carries `model_id`, and a review attests a *rendering*. If `/tahlil/word`
    resolved the model from a generator while `/tahlil/review` resolved it from «no
    generator» (the env fallback «unset»), every review would be written under a key no
    analysis can ever produce: `reviewed` would read False forever and the mandatory
    «غير مُحقَّق» mention would never come off a block an expert had actually read. The two
    routes therefore share `default_generator()`, and the import is lazy + defensive so a
    machine with no `ollama` package still serves the deterministic page — degraded, never
    500. `analyze_word` calls the generator only when `TAHLIL_GENERATION_ENABLED=1`; it
    reads `model_id` from it always, which is exactly why it is passed on both paths.
    """
    try:
        from tahlil.generator import default_generator

        return default_generator()
    except Exception:
        return None


@router.post("/tahlil/word", response_model=TahlilWordResponse)
def tahlil_word(req: TahlilWordRequest, request: Request) -> TahlilWordResponse:
    """The five-block analysis for one word.

    400 on non-positive/invalid indices; 404 when `surah:ayah:word` does not exist in the
    corpus (mirrors `/qlisan/word`).

    **These two mappings are safe only because `analyze_word` validates the indices and the
    position itself, before it touches any evidence, and never lets an internal fault out as
    `ValueError`/`KeyError`** (see `tahlil_service._build_bundle`). Without that invariant
    this handler re-labels internal faults as user errors: a `KeyError` from the evidence
    builder surfaced as 404 «word position not found» for a word `/qlisan/word` renders
    fine, and the deliberate `KeyError` alarm of task 1.3 — `huruf.describe` refusing to
    silently drop an unresolvable root letter — arrived here dressed as «that word does not
    exist». If either becomes reachable again, the answer is an internal fault (a warned
    degraded 200, or a 500), never a user error.

    Everything else returns **200 with a stated reason**: a missing evidence layer, a model
    that is off or unreachable, a generator that failed. A reader must never meet a 500
    because a model was down, and must never meet a silently empty block either.
    """
    try:
        analysis = analyze_word(req.surah, req.ayah, req.word, store=_store(request),
                                generator=_generator())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"word position not found: {req.surah}:{req.ayah}:{req.word}",
        ) from exc
    return TahlilWordResponse(**analysis)


@router.post("/tahlil/review", response_model=TahlilReviewResponse)
def tahlil_review(req: TahlilReviewRequest, request: Request) -> TahlilReviewResponse:
    """Mark one word's analysis reviewed by a named expert.

    400 on a malformed ref; 404 on a position the corpus does not hold — reviewing a word
    that does not exist would put an un-droppable row in the table under a ref nothing can
    ever render. 503 when no store is configured: the caller asked for something durable
    and we could not durably do it, which must not be answered with a cheerful 200.

    The row is recorded against `review_key()` — the *rendering* the reviewer saw, not just
    the word (versions + model + whether prose was generated). It is computed exactly as
    `analyze_word` computes it for this same request, **through the same `_generator()`
    accessor**, so the very next analysis under unchanged conditions reports
    `reviewed=True`, and any change to what the page would show reports it un-reviewed
    again. Resolving the model differently on the two routes is the one way this flag can
    be silently dead; see `_generator`.
    """
    parts = (req.ref or "").split(":")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="ref must be 'surah:ayah:word'")
    try:
        surah, ayah, word = (int(p) for p in parts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="ref must be 'surah:ayah:word'") from exc
    if surah < 1 or ayah < 1 or word < 1:
        raise HTTPException(status_code=400, detail="ref indices must be positive (1-based)")

    from analysis.qlisan_data import qac_words

    ref = f"{surah}:{ayah}:{word}"
    if ref not in qac_words():
        raise HTTPException(status_code=404, detail=f"word position not found: {ref}")

    store = _store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="review store unavailable")
    row = store.mark_tahlil_reviewed(ref, *review_key(generator=_generator()),
                                     reviewer=req.reviewer, note=req.note)
    return TahlilReviewResponse(ref=ref, reviewed=True, **{k: row[k] for k in
                                                           ("reviewer", "note", "reviewed_at")})
