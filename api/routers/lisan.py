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
    LisanReadingPut,
    LisanReadingResponse,
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
            # The one «الكلمة في الآيات» already answers with, so the المواضع
            # block on this page is the same computation, not a second one that
            # happens to agree today.
            lookup=request.app.state.verse_lookup,
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

    payload = _with_islambouli(_service(request).analyze(word))
    root = payload.get("root")
    if root:
        # Additive: an app built without the store (a test, a CLI) still analyses.
        store = getattr(request.app.state, "store", None)
        reading = store.get_lisan_reading(root) if store is not None else None
        payload["islambouli_assembly"] = _islambouli_assembly(root, reading)
        payload["cultural_stage"] = _cultural_stage(root, reading)
    return payload


def _with_islambouli(payload: dict) -> dict:
    """Attach Samer Islambouli's gloss to each root letter, verbatim.

    Joined HERE and not in `LisanService`: nothing under `linguistics/lisan/`
    outside `islambouli/` may import that package (`tests/test_import_direction.py`),
    and `api/` is the layer allowed to set two engines' outputs side by side. The
    letter → row mapping is the package's own `row_label` (hamza seats → «ء»,
    ه → «هـ», ا → «آ - ى»), so the page reads the row the measurement read.

    A table that no longer matches its lock is not published in his name: every
    gloss is left empty rather than failing the analysis it decorates.
    """
    from linguistics.lisan.islambouli.compose import row_label
    from linguistics.lisan.islambouli.table import TableNotFrozen, table

    try:
        rows = table().by_label()
    except TableNotFrozen:
        return payload
    for letter in payload.get("letters") or []:
        label = row_label(letter.get("letter", ""))
        row = rows.get(label) if label else None
        letter["islambouli"] = row.text if row else ""
    return payload


def _signed(reading: dict | None):
    """The ONLY place a choice between alternatives is built: from a stored,
    signed personal reading. Nothing in the request can reach it."""
    from linguistics.lisan.islambouli.assemble import SignedChoices

    if not reading or not reading.get("choices"):
        return None
    return SignedChoices(author=reading["author"], choices=dict(reading["choices"]))


def _islambouli_assembly(root: str, reading: dict | None) -> dict | None:
    """The project's junction of the root's three rows, beside what HE published.

    The assembly is not Islambouli's physical stage and the payload never says it
    is: `cited` carries his own sentence, when one exists, and `gap` names the
    words that differ. Any frozen table that moved suppresses the whole block —
    nothing is shown in his name from a table that is no longer his.
    """
    from linguistics.lisan.harness.guard import WitnessRootComposed
    from linguistics.lisan.islambouli.assemble import InvalidChoice, assemble
    from linguistics.lisan.islambouli.table import TableNotFrozen
    from linguistics.lisan.islambouli.wasf import WasfNotFrozen
    from linguistics.lisan.islambouli_citations import (
        CitationsNotFrozen,
        citations,
        word_gap,
    )

    try:
        try:
            a = assemble(root, _signed(reading))
        except InvalidChoice:
            # A stored choice the current table no longer supports: show every
            # alternative rather than guess which one was meant.
            a = assemble(root)
        cited = [c for c in citations().for_root(root) if c.stage == "physical"]
    except (TableNotFrozen, WasfNotFrozen, CitationsNotFrozen):
        return None
    except WitnessRootComposed:
        # Raised only under a test runner, for a root of the Islambouli holdout:
        # omitting the block is exactly what keeps its reading out of a test.
        return None
    out = {
        "sentence": a.sentence,
        "positions": [
            {"position": p.position, "letter": p.letter, "segment": p.segment,
             "alternatives": list(p.alternatives) if p.is_group else [],
             "rendered": p.rendered, "chosen": p.chosen}
            for p in a.positions
        ],
        "author": a.author,
        "wasf_version": a.wasf_version,
        "refused": a.refused,
        "refusal_code": a.refusal_code,
        "refusal_reason": a.refusal_reason,
        "cited": None,
        "gap": None,
    }
    if cited:
        c = cited[0]
        out["cited"] = _cited(c)
        if a.sentence:
            out["gap"] = word_gap(a.sentence, c.statement)
    return out


def _cited(c) -> dict:
    return {"id": c.id, "stage": c.stage, "label": c.label,
            "label_as_printed": c.label_as_printed, "text": c.text,
            "reading_note": c.reading_note, "source": c.source}


def _cultural_stage(root: str, reading: dict | None) -> dict | None:
    """Islambouli's cited cultural stage and/or the reader's signed one — or None.

    Never generated and never inferred: with neither source the field is null and
    the page renders no section at all.
    """
    from linguistics.lisan.islambouli_citations import CitationsNotFrozen, citations

    try:
        cited = [_cited(c) for c in citations().for_root(root) if c.stage == "cultural"]
    except CitationsNotFrozen:
        cited = []
    personal = None
    if reading and (reading.get("cultural_text") or "").strip():
        personal = {"author": reading["author"], "text": reading["cultural_text"],
                    "updated_at": reading["updated_at"]}
    if not cited and personal is None:
        return None
    return {"citations": cited, "personal": personal}


@router.get("/lisan/reading/{root}", response_model=LisanReadingResponse | None)
def lisan_reading_get(root: str, request: Request):
    """The reader's signed reading of `root`, or null."""
    return request.app.state.store.get_lisan_reading(root.strip())


@router.put("/lisan/reading/{root}", response_model=LisanReadingResponse)
def lisan_reading_put(root: str, body: LisanReadingPut, request: Request):
    """Store the reader's SIGNED reading of `root`.

    422 when unsigned, when `root` is not Arabic, or when a choice names a
    position without an alternative group or an alternative that is not there.
    """
    from linguistics.lisan.islambouli.assemble import (
        InvalidChoice,
        SignedChoices,
        assemble,
    )

    root = root.strip()
    if not _ARABIC_RE.search(root):
        raise HTTPException(status_code=422, detail="root must be written in Arabic script")
    if not body.author.strip():
        raise HTTPException(status_code=422, detail="a personal reading must be signed")
    if body.choices:
        try:
            a = assemble(root, SignedChoices(author=body.author, choices=body.choices))
        except InvalidChoice as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if a.refused:
            raise HTTPException(status_code=422, detail=a.refusal_reason)
    return request.app.state.store.put_lisan_reading(
        root, body.author, body.cultural_text, body.choices)
