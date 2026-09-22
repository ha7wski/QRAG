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

from api.models.lisan import LisanRequest, LisanResponse

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
