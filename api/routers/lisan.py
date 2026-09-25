"""
Lisan endpoint: letter-symbolism reading of an Arabic word's root.

Arabic-only and LLM-free. The reading is built CORE-FIRST: the root's attested
aṣl (Ibn Fāris) is resolved before the letters are read, and it is what selects
among each letter's bundle of sourced senses — see
`linguistics/lisan/sense_selection.py`. The response publishes the constraint,
not just the conclusion: the core verbatim, the axes each sense matched, and
every sense that was dropped with the reason.

Interpretive (Ḥasan ʿAbbās' sound-symbolism + Ibn Jinnī), NOT lexicography — the
disclaimer travels in every response, and a root with no attested aṣl gets a
warning and an unselected inventory rather than a composed paragraph.

Pure pipeline logic lives in `linguistics/lisan/`; this layer only validates
input and lazily builds the shared `LisanService` from the already-loaded QAC
resolver (so app startup / main.py wiring is a single include_router line, no
lifespan change). The resolver is also what canonicalizes a root before the core
lookup: `root_cores.json` is keyed on the exact, hamza-bearing spelling.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request

from api.models.lisan import (
    ConceptRequest,
    ConceptResponse,
    LisanRequest,
    LisanResponse,
)

router = APIRouter(tags=["lisan"])

# Any Arabic-script character (incl. the bare hamza ء) makes the input valid.
_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿ]")


def _service(request: Request):
    """Lazily build and cache the LisanService on app.state, reusing the shared
    QAC resolver (LexicalRetriever) — no LLM, no new heavy components."""
    svc = getattr(request.app.state, "lisan_service", None)
    if svc is None:
        from linguistics.lisan.lisan_service import LisanService

        svc = LisanService(
            resolver=request.app.state.lexical_retriever,
        )
        request.app.state.lisan_service = svc
    return svc


@router.post("/lisan/analyze", response_model=LisanResponse)
def lisan_analyze(req: LisanRequest, request: Request) -> LisanResponse:
    """Read a word's root against its attested aṣl and return the constrained
    letter reading.

    Arabic-only: no `lang` parameter (any sent is ignored). Input validation is
    unchanged by the core-first rewrite: 422 on empty / non-Arabic input, and
    200 with `root: null` plus a helpful Arabic `message` when nothing resolves
    (never 500). A resolved root with no curated core is also a 200 — with
    `constrained: false` and a `warning`, which is a normal outcome for a large
    minority of roots, not an error."""
    word = (req.word or "").strip()
    if not word:
        raise HTTPException(status_code=422, detail="word must not be empty")
    if not _ARABIC_RE.search(word):
        raise HTTPException(
            status_code=422, detail="word must be written in Arabic script"
        )

    return _service(request).analyze(word)


# ── the physics-first engine, mounted beside the core-first one ──────────────
#
# `POST /lisan/analyze` above is CORE-FIRST and is untouched by this route: the
# attested aṣl selects among each letter's sourced senses. `POST /lisan/concept`
# is the inverse — the مفهوم is composed from the tajwīd description of the
# root's letters and from nothing else, and Ibn Fāris arrives afterwards as the
# TEST rather than as the input. Two engines, side by side, until the comparison
# is done; neither is labelled correct anywhere in this file.
#
# The orchestration lives HERE rather than in a service under
# `linguistics/lisan/concept/`, and that is a boundary decision, not laziness. A
# module inside that package may not reach the aṣl — `tests/test_import_direction.py`
# enforces it, and a concept module that imported `confront` would inherit
# everything `confront` reads and be reported as reaching it. So the only place
# the two halves may legally be joined is a layer above the package. `api/` is
# that layer: it already imports `linguistics/`, and nothing imports it back.


def _confront(root: str):
    """`confront.confront(root)` — composed blind, then set beside the aṣl.

    Imported inside the function for the same reason `_service` builds lazily:
    importing at module scope would read the primitive table, the letter sheet,
    the Maqāyīs CSV and the attestation record at app import time, and
    `tests/test_served_surface.py` imports the app to count routes.
    """
    from linguistics.lisan.concept import confront as confront_mod

    return confront_mod.confront(root)


def _hits(hits) -> list[dict]:
    return [
        {
            "primitive": hit.primitive,
            "feature": hit.feature,
            "gloss_ar": hit.gloss_ar,
            "status": hit.status,
            "coverage": hit.coverage,
            "declaration_index": hit.declaration_index,
        }
        for hit in hits
    ]


def _concept_payload(concept) -> dict:
    """The composed concept as the wire sees it, field for field.

    Nothing is computed here. In particular the realised primitives are NOT
    regrouped, re-ordered or re-worded on the way out: `sentence` and
    `realised_primitives` leave exactly as `compose()` produced them, because
    they are what the record stores and what `k / 40` is measured on. Grouping
    the nine primitives by position for readability is the PAGE's job (§D6), and
    it groups what is sent rather than receiving a grouping.
    """
    return {
        "root": concept.root,
        "refused": concept.refused,
        "refusal_code": concept.refusal_code,
        "refusal_reason": concept.refusal_reason,
        "positions": [
            {
                "position": reading.position,
                "letter": reading.letter,
                "sheet_letter": reading.sheet_letter,
                "makhraj_ar": reading.makhraj_ar,
                "features": list(reading.features),
                "ordered": _hits(reading.ordered),
                "realised": _hits(reading.realised),
                "carried": _hits(reading.carried),
                "silent": reading.silent,
                "silent_reason": reading.silent_reason,
            }
            for reading in concept.positions
        ],
        "realised_primitives": list(concept.realised_primitives),
        "sentence": concept.sentence,
        "sentence_source": concept.sentence_source,
        "phrasing_rejection": concept.phrasing_rejection,
        "partial": concept.partial,
        "silent_letters": list(concept.silent_letters),
        "lock_version": concept.lock_version,
    }


def _confrontation_payload(report) -> dict:
    return {
        "cores": [dict(core) for core in report.cores],
        "core_status": report.core_status,
        "occurrences": report.occurrences,
        "verses": list(report.verses),
        "uses": [
            {
                "gloss": use.gloss,
                "verse": use.verse,
                "verdict": use.verdict,
                "reason": use.reason,
            }
            for use in report.uses
        ],
        "verdict": report.verdict,
        "uses_frozen_at": report.uses_frozen_at,
        "concept_recorded_at": report.concept_recorded_at,
        "in_witness_set": report.in_witness_set,
        "counts_toward_k": report.counts_toward_k,
    }


@router.post("/lisan/concept", response_model=ConceptResponse)
def lisan_concept(req: ConceptRequest, request: Request) -> ConceptResponse:
    """Compose a root's مفهوم from its letters' physics, then show the aṣl beside it.

    Input validation mirrors `/lisan/analyze` exactly — 422 on empty or
    non-Arabic input, 200 with `root: null` and an Arabic `message` when nothing
    resolves — so the two engines behave identically on everything that is not
    the reading itself. The root resolver is the SAME one, reached through the
    already-built `LisanService`: two engines resolving a word differently would
    make the comparison a comparison of two roots.

    A refused root (quadriliteral) is a **200 carrying a refusal**, not a 404.
    The statement «this rule covers three positions only» is the answer, and a
    page that received an error would show an empty panel where a reason belongs.
    """
    word = (req.word or "").strip()
    if not word:
        raise HTTPException(status_code=422, detail="word must not be empty")
    if not _ARABIC_RE.search(word):
        raise HTTPException(
            status_code=422, detail="word must be written in Arabic script"
        )

    from linguistics.lisan.concept.compose import WINDOW_RESERVATION_AR
    from linguistics.lisan.lisan_service import DISCLAIMER

    resolved = _service(request).resolve_root(word)
    root = resolved["root"]
    if not root:
        return ConceptResponse(
            word=word,
            root=None,
            root_source=None,
            metric_reservation=WINDOW_RESERVATION_AR,
            disclaimer=DISCLAIMER,
            message="لم يُعرَف لهذه الكلمة جذرٌ في مدوَّنة القرآن.",
        )

    report = _confront(root)
    return ConceptResponse(
        word=word,
        root=root,
        root_source=resolved["root_source"],
        concept=_concept_payload(report.concept),
        confrontation=_confrontation_payload(report),
        # Sent on every answer, including the refusals and the roots with no
        # record. §D11 requires it wherever a coverage verdict is published, and
        # `confrontation.verdict` is one; sending it only when it happens to look
        # relevant is how it ends up absent from the response that matters.
        metric_reservation=WINDOW_RESERVATION_AR,
        disclaimer=DISCLAIMER,
    )
