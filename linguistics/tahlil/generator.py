"""
generator.py — the Tahlil prose generator: five model calls, one per block, and every
answer treated as hostile input.

The mental model this module is written under, and it is the whole reason it looks the way
it does: **the generator is an adversarial input to a proved gate, not a component to
trust.** The question is never «did qwen write well?» — it is «do the gate and the
per-source inspection hold against what it produced?». So nothing here tries to make the
model correct. It makes the model's output *judgeable*: one block per call, one contract,
handles instead of ids, and every refusal written to the coverage log with what arrived.

Four things this module does that the gate cannot:

  1. **Per-block isolation** (tasks.md 7.3). Five calls, each with its own evidence slice
     and its own try/except. A model that emits garbage for صرفي must not cost the reader
     the دلالي block, and a single 4-block-in-one-call answer makes that impossible: one
     unparseable brace and the whole page is prose-free. Isolation is also what keeps each
     answer inside `llm_client`'s 512-token default budget, which is why this module can
     reuse that client **unchanged** as 7.2 requires.

  2. **The two post-checks the closed reason set cannot express.** `citations.REASONS` is
     closed (only `sense-selection-unanchored` was ever added to it), so the letters
     synthesis rules and the sense-selection contract live here, in
     `GENERATION_LOG_REASONS`, exactly as the service's transport reasons live in
     `SERVICE_LOG_REASONS`. They FILTER the generator's own output — and every filtered
     claim is logged with its reason. Silent filtering is the one thing forbidden: it would
     make a prompt regression look like a quiet model.

  3. **The تركيب composes over a PRE-GATED view of the levels.** `validate_tarkib` requires
     the thesis to cite evidence that *surviving* level claims stood on, so the thesis is
     written after the four levels and is shown only the level claims that pass
     `citations.validate`. Running the gate twice is free of consequence — it is pure and
     deterministic, so the service's verdict is identical — and it is the difference
     between a thesis anchored on what the page shows and one anchored on what the model
     wished it had said. **The pre-gate never filters what is RETURNED**: all claims go to
     the service, so every drop is logged once, by the authority.

  4. **The weak-synthesis sentence is appended in code.** tasks.md 7.6 requires an
     uncorroborated letters synthesis to *say so*. A sentence the model was asked to add is
     a request; a sentence appended after the fact is the statement itself.

The corroboration check is a check on ANCHORING, not on meaning — say it plainly, because
misreading it is the risk: it asks whether the synthesis cited the aṣl or a naẓīr, never
whether the reading is right. Nothing in this repository can decide the latter, which is
why acceptance needs per-source human inspection (task 12.4) and why no badge here says
«verified».
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linguistics.tahlil import citations, coverage, prompts  # noqa: E402

BLOCK_HURUF, BLOCK_SARFI, BLOCK_NAHWI, BLOCK_DALALI, BLOCK_TARKIB = citations.BLOCKS
LEVEL_BLOCKS: tuple[str, ...] = (BLOCK_HURUF, BLOCK_SARFI, BLOCK_NAHWI, BLOCK_DALALI)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Reasons owned by THIS layer
# ─────────────────────────────────────────────────────────────────────────────
# Deliberately outside `citations.REASONS`, which is closed over *gate verdicts*. These
# record what the generation layer itself refused or weakened — the same separation the
# service makes for its transport failures (`SERVICE_LOG_REASONS`). The §12.2 sweep asserts
# the union, so an unknown string still fails.
R_UNPARSEABLE = "generator-unparseable-json"
R_BLOCK_FAILED = "generator-block-failed"
R_SYNTHESIS_INCOMPLETE = "synthesis-incomplete"
R_SYNTHESIS_UNVALIDATED = "synthesis-unvalidated"
R_ZERO_ABSENT = "zero-layer-absent"
R_QUOTATION = "claim-is-quotation"
R_DUPLICATE = "duplicate-claim"
R_VERSE_GLOSS = "claim-is-verse-gloss"

# The verse synthesis is not one of the five blocks; it is its own, one storey up.
VERSE_BLOCK = "verse"
R_PROMPT_ECHO = "claim-echoes-the-example"

# `form-sense-unselected` is ALREADY in the gate's closed set (it was reserved there and
# never emitted, because the gate cannot see a selection — only this layer, which holds the
# claim contract, can). Imported rather than re-declared: two copies of a reason string is
# the drift this change has been bitten by three times.
R_SENSE_UNSELECTED = citations.R_SENSE_UNSELECTED

GENERATION_LOG_REASONS: frozenset[str] = frozenset({
    R_UNPARSEABLE, R_BLOCK_FAILED, R_SYNTHESIS_INCOMPLETE, R_SYNTHESIS_UNVALIDATED,
    R_ZERO_ABSENT, R_SENSE_UNSELECTED, R_QUOTATION, R_DUPLICATE, R_VERSE_GLOSS,
    R_PROMPT_ECHO,
})

# How much of a bad answer reaches the log. Bounded because a model can emit a very large
# string; long enough that «what did it actually send?» is answerable, which «unparseable»
# alone is not.
_RAW_IN_LOG = 300

_WS_RE = re.compile(r"\s+")


def _norm(text: object) -> str:
    return _WS_RE.sub(" ", text).strip() if isinstance(text, str) else ""


# ─────────────────────────────────────────────────────────────────────────────
# 2. Model identity — resolvable WITHOUT constructing a client
# ─────────────────────────────────────────────────────────────────────────────
def model_id_from_env() -> str:
    """`provider:model`, read from the environment alone.

    Deliberately independent of whether a client can be built: `analyze_word` reads
    `model_id` for the cache key **and** `review_key` before it ever calls the generator,
    and `/tahlil/review` reads it on a request that never generates anything. If the id
    came from a constructed client it would be «unset» on any machine where Ollama is down
    — so a review recorded during an outage would key differently from the analysis it
    attests, and silently never match.
    """
    from generation.llm_client import (
        DEFAULT_ANTHROPIC_MODEL, DEFAULT_OLLAMA_MODEL, DEFAULT_PROVIDER,
    )

    provider = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).lower()
    if provider == "anthropic":
        model = os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    else:
        model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    return f"{provider}:{model}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Parsing a model answer
# ─────────────────────────────────────────────────────────────────────────────
def extract_json_array(raw: object) -> list | None:
    """The first balanced JSON array in `raw`, or None.

    Not `json.loads(raw)`: an instruction-following model still wraps its answer in a code
    fence or prefixes «إليك المصفوفة», and losing an otherwise perfect answer to a stray
    line is a self-inflicted drop. The scan is brace-counting with string/escape awareness
    rather than a regex, because a claim's own text can contain `[` and `]`.

    A bare object is accepted and wrapped: «one claim, unwrapped» is the second most common
    malformed shape after the fenced array, and it is unambiguous. Anything else returns
    None and the caller logs the raw head — never a silent empty block.

    **The scan starts at whichever opener comes FIRST in the text, never at `[` by
    preference.** Trying arrays first looks harmless and is not: a bare object almost always
    contains an array (`"cites": [2, 3]`), so the array-first scan locks onto that inner
    list and returns `[2, 3]` — two integers, logged as malformed claims, with the real
    claim discarded and nothing anywhere saying a whole answer had been thrown away. The
    first live recording lost the الحروف and تركيب blocks of the pinned exemplar to exactly
    this, on both of the two blocks that answered with a bare object.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    openers = sorted(
        ((raw.find(o), o, c) for o, c in (("[", "]"), ("{", "}")) if raw.find(o) >= 0)
    )
    for start, opener, closer in openers:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(raw)):
            ch = raw[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(raw[start:i + 1])
                    except Exception:
                        break
                    if isinstance(parsed, list):
                        return parsed
                    if isinstance(parsed, dict):
                        return [parsed]
                    break
    return None


def _event(block: str, reason: str, outcome: str, text: object,
           cites: list[str] | None = None, badge_before: str = "",
           badge_after: str = "") -> dict:
    return {
        "block": block,
        "reason": reason,
        "outcome": outcome,
        "badge_before": badge_before,
        "badge_after": badge_after,
        "text": (text if isinstance(text, str) else repr(text))[:_RAW_IN_LOG],
        "cites": list(cites or ()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. The two post-checks the gate cannot make
# ─────────────────────────────────────────────────────────────────────────────
def _letter_ids(bundle: dict) -> set[str]:
    """The DISTINCT letter ids of the root — one per letter, not per slot.

    A geminate root (مدد) decomposes to three slots over two ids, so «cites every letter»
    has to mean every id: requiring three would make a correct synthesis for every doubled
    root impossible to write.
    """
    return {e["cite_id"] for e in (bundle.get("letters") or []) if e.get("cite_id")}


def check_synthesis(claims: list[dict], bundle: dict) -> tuple[list[dict], list[dict]]:
    """الحروف post-check: completeness (drop) then corroboration (weaken, never delete).

    A claim citing two or more letters IS the synthesis — it composes letters, which is the
    only thing the block asks for beyond the per-letter rows the deterministic layer already
    renders. Applying the rule to that shape rather than to a self-declared «this is the
    synthesis» field keeps it out of the model's control: a rule a generator can opt out of
    by omitting a flag is not a rule.

    Completeness is a **drop** (tahlil-huruf: «a synthesis citing fewer letters than the
    root has is dropped by the validator»): a core sense read off two of three radicals is
    not a weaker version of the synthesis, it is a different claim about a different root.

    Corroboration is **never** a drop, and never silent either — the spec forbids both
    («SHALL NOT be silently presented as if corroborated, and SHALL NOT be silently
    deleted»). The uncorroborated synthesis renders with the weakness stated in its own
    text, and the log carries `synthesis-unvalidated`.
    """
    letters = _letter_ids(bundle)
    kept: list[dict] = []
    events: list[dict] = []
    for claim in claims:
        if not isinstance(claim, dict):
            kept.append(claim)      # a bare string/int — the SERVICE's gate names it
            continue
        cites = claim.get("cites") or []
        cited_letters = {c for c in cites if citations.kind_of(c) == citations.KIND_LETTER}
        if len(cited_letters) < 2:
            kept.append(claim)                      # a per-letter claim, not a synthesis
            continue
        if letters and cited_letters != letters:
            events.append(_event(BLOCK_HURUF, R_SYNTHESIS_INCOMPLETE, citations.OUTCOME_DROP,
                                 claim.get("text_ar"), cites, claim.get("badge", "")))
            continue
        corroborated = any(citations.kind_of(c) in (citations.KIND_NAZIR,
                                                    citations.KIND_MAQAYIS) for c in cites)
        if not corroborated:
            text = claim.get("text_ar")
            if isinstance(text, str):
                claim["text_ar"] = text.rstrip(" .،؛") + prompts.WEAK_SYNTHESIS_SUFFIX
            events.append(_event(BLOCK_HURUF, R_SYNTHESIS_UNVALIDATED,
                                 citations.OUTCOME_DOWNGRADE, claim.get("text_ar"), cites,
                                 claim.get("badge", ""), citations.BADGE_INTERPRETIVE))
        kept.append(claim)
    return kept, events


def check_sense_selection(claims: list[dict], bundle: dict) -> tuple[list[dict], list[dict]]:
    """صرفي post-check: a multi-sense row must be *selected from*, by name.

    The contract asks for `sense_ar`, copied verbatim from the row. The obvious alternative
    — read the prose and decide whether it enumerated or chose — is wrong in the direction
    that matters, and the reference exemplar proves it: «ليست على بابها في المشاركة، بل
    تفيد المبالغة» names BOTH senses of the row while making a perfectly definite choice, so
    a «contains ≥2 senses ⇒ unselected» rule would delete the one claim this change exists
    to produce. Same principle as `_contrast_admissible`: exact match on a computed string,
    no natural-language interpretation on the trust path.

    A selection naming a sense the row does not carry is also unselected — it is worse, in
    fact: the model invented an option. Both land on `form-sense-unselected`, and the log
    row carries the text, so triage can tell them apart by reading it.

    This does NOT decide the badge. Whether the selection is anchored — and so whether it
    keeps مُولَّد or is downgraded to تأويلي — is the gate's call, on the citations, and it
    stays there (`sense-selection-unanchored`, the one downgrade).
    """
    items = bundle.get("items") or {}
    kept: list[dict] = []
    events: list[dict] = []
    for claim in claims:
        if not isinstance(claim, dict):
            kept.append(claim)      # a bare string/int — the SERVICE's gate names it
            continue
        cites = claim.get("cites") or []
        multi = [items.get(c) or {} for c in cites
                 if citations.kind_of(c) == citations.KIND_SIGHA
                 and (items.get(c) or {}).get("multi_sense")]
        if not multi:
            kept.append(claim)
            continue
        offered = {_norm(s.get("sense_ar")) for row in multi
                   for s in (row.get("senses") or [])}
        offered.discard("")
        if _norm(claim.get("sense_ar")) not in offered:
            events.append(_event(BLOCK_SARFI, R_SENSE_UNSELECTED, citations.OUTCOME_DROP,
                                 claim.get("text_ar"), cites, claim.get("badge", "")))
            continue
        kept.append(claim)
    return kept, events


# Edge punctuation only — quotation marks, a trailing full stop, a leading dash. Interior
# words are NEVER stripped, because "adds nothing" is the entire content of the rule: the
# moment a tolerance can absorb a word, «quotation + a little interpretation» starts
# passing as a quotation and the rule becomes the loophole it was added to close.
_EDGE_PUNCT = " \t\n«»\"'“”‘’.،؛:!؟?…-–—()[]{}"


def _quotable(text: str) -> str:
    """A claim's text prepared for the containment test — whitespace, tashkīl, edges.

    Tashkīl is folded on both sides for the reason `_bare` exists in the gate: a model
    re-vocalizes as it copies. Nothing else is folded — no synonym matching, no stemming —
    since every tolerance added here is a way for an *added* clause to survive the test.
    """
    return citations._bare(_norm(text)).strip(_EDGE_PUNCT)


def is_quotation(claim: dict, lines: dict[str, str]) -> bool:
    """True when the claim adds NOTHING to one of the sources it cites.

    Strict containment against the evidence line the model was actually shown: the whole
    claim, edge punctuation aside, must appear inside one cited line verbatim. Containment
    is tested against **one** line, never the concatenation of several — a join creates
    spans that exist in no source, and a claim spliced across such a span would be declared
    a quotation of something nobody wrote.

    Why the rule is sound in the direction it is used, which is the only reason it is here:
    a sentence that merely restates a Quranic verse (or a cited aṣl) cannot be false, so
    recognising it costs no true statement — the same words are already on the page under
    the **محقّق** badge, rendered by the deterministic layer. What the recognition removes
    is a *redundant restatement wearing the مُولَّد badge*, which is not information but
    which does inflate exactly the count §12 will read as «anchored readings produced».

    And why strictness is the whole safeguard: if a claim could append a clause of its own
    and still be called a quotation, the rule would become a way to launder an
    interpretation as «it's just the verse». It cannot: any added word breaks containment.

    **Containment is tested against every line the block was SHOWN, not only the lines the
    claim cites**, and the first live recording is why. A صرفي claim came back as the
    verbatim verse of naẓīr [7] while citing `qac:relation` and `qac:head_ref` — a pure
    restatement of source A wearing citations of source B. Restricting the check to cited
    sources let it through, and the original rationale for that restriction («otherwise a
    real reading that echoes unrelated evidence is refused») does not survive contact with
    strict containment: a real تعليل is never *wholly* contained in any single source line,
    so widening the search cannot reach one. Each line is still compared ALONE — never a
    concatenation.
    """
    text = _quotable(claim.get("text_ar") or "")
    if not text:
        return False
    return any(text in citations._bare(_norm(line)) for line in lines.values())


def check_quotation(claims: list[dict], lines: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """Drop the claims that only repeat their source; log each one.

    Applies to every block including the تركيب: a thesis that quotes a level's evidence
    back is the same non-statement, one layer up.

    `lines` is supplied BY THE CALLER — `prompts.slice_lines(bundle, block)` for a level,
    the تركيب's own slice for the thesis — rather than built here from the whole bundle.
    Building it here coupled every block to every other: one malformed letter entry failed
    all five levels instead of the two that read the letters, and the isolation test caught
    it immediately.

    Found by the first live qwen run, not by design: two claims survived the gate saying
    nothing — a bare «يُسَارِعُونَ» in دلالي and a near-verbatim naẓīr verse in نحوي — both
    citing resolvable naẓāʾir, so both correctly kept and correctly badged. **No coverage
    rate can see that**, which is precisely why it needed a rule rather than a note.
    """
    kept: list[dict] = []
    events: list[dict] = []
    seen_texts: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            kept.append(claim)      # a bare string/int — the SERVICE's gate names it
            continue
        # An EXACT duplicate within a block is not two claims. The first live recording
        # produced the same دلالي sentence twice, differing only in which naẓāʾir each cited;
        # the page printed one reading twice and the sweep counted two «anchored readings».
        # The comparison is on the normalized text alone — nothing is merged, the first
        # occurrence keeps its own citations, and the second is logged rather than vanishing.
        normalized = _norm(claim.get("text_ar"))
        if normalized and normalized in seen_texts:
            events.append(_event(claim.get("block", ""), R_DUPLICATE, citations.OUTCOME_DROP,
                                 claim.get("text_ar"), claim.get("cites") or [],
                                 claim.get("badge", "")))
            continue
        if normalized:
            seen_texts.add(normalized)
        if is_quotation(claim, lines):
            events.append(_event(claim.get("block", ""), R_QUOTATION, citations.OUTCOME_DROP,
                                 claim.get("text_ar"), claim.get("cites") or [],
                                 claim.get("badge", "")))
            continue
        kept.append(claim)
    return kept, events


def check_prompt_echo(claims: list[dict], block: str) -> tuple[list[dict], list[dict]]:
    """Drop a claim that copies the system prompt's worked example.

    PROMPT_VERSION 1.4.0 puts one complete claim in the system contract, because two live
    recordings showed that an abstract field contract does not land on qwen2.5:7b: it kept
    filing the reasoning under `sense_ar` and a bare quotation under `text_ar`, and the
    second time that emptied four blocks.

    An example is fluent Arabic the model has been SHOWN, and `check_quotation` compares a
    claim only against the evidence lines — so a copied example would pass the gate wearing
    real citations, which is a fabrication with a clean provenance record. This closes that
    door: containment against the example, in the rejecting direction only, exactly as the
    quotation rule works against the evidence.

    Block-agnostic: the example is in the SYSTEM prompt, so every block sees it.
    """
    kept: list[dict] = []
    events: list[dict] = []
    example = _quotable(prompts.EXAMPLE_CLAIM_AR)
    for claim in claims:
        if not isinstance(claim, dict):
            kept.append(claim)
            continue
        text = _quotable(claim.get("text_ar") or "")
        if example and text and (example in text or text in example):
            events.append(_event(block, R_PROMPT_ECHO, citations.OUTCOME_DROP,
                                 claim.get("text_ar"), claim.get("cites") or [],
                                 claim.get("badge", "")))
            continue
        kept.append(claim)
    return kept, events


def check_verse_gloss(claims: list[dict], block: str) -> tuple[list[dict], list[dict]]:
    """Drop a دلالي claim that stands on ONE naẓīra and nothing else.

    The first live recording produced five دلالي claims, one per naẓīra, each a summary of
    that verse rather than a reading of the word — and two of them said the OPPOSITE of
    their source: 5:41 «يسارعون في الكفر» came back as «يتركون الأفكار الكافرة ويتجهون نحو
    الإيمان». Every one of them cited correctly, so the gate kept them all and the coverage
    rate read 100%. That is the failure mode the design names: fluent, sourced, and wrong.

    The rule is STRUCTURAL, not semantic — it reads the citation shape, never the prose —
    and it runs only in the REJECTING direction, so it cannot launder anything. The block's
    contract admits exactly two claims: a محوري reading standing on the lexical aṣl and the
    letters, and ONE سياقي reading synthesised across the naẓāʾir (the brief now demands two
    of them). A claim resting on a single verse satisfies neither, whatever it says.

    Scoped to دلالي because only there is «one verse» a category error. The صرفي block
    anchors a form's sense on exactly one corroborating naẓīra by design, and نحوي may cite
    one in support of a claim whose weight is on the iʿrāb; widening this would delete both.
    """
    if block != prompts.BLOCK_DALALI:
        return claims, []
    kept: list[dict] = []
    events: list[dict] = []
    for claim in claims:
        if not isinstance(claim, dict):
            kept.append(claim)
            continue
        cites = [c for c in (claim.get("cites") or ()) if isinstance(c, str)]
        nazair = [c for c in cites if citations.kind_of(c) == citations.KIND_NAZIR]
        if len(cites) == 1 and len(nazair) == 1:
            events.append(_event(block, R_VERSE_GLOSS, citations.OUTCOME_DROP,
                                 claim.get("text_ar"), cites, claim.get("badge", "")))
            continue
        kept.append(claim)
    return kept, events


def zero_events(bundle: dict) -> list[dict]:
    """One log row when the Zero relation layer is absent for this word (tasks.md 7.5).

    The layer ships in a separate, unimplemented change (`add-nahwi-zero-relations`), so
    today this fires on every request — which is the point: «the نحوي block has no relation
    line» must be a *recorded* absence with a name, not a shape of the page nobody can
    account for. `prompts.zero_info` reads the fiche; when the layer lands, the same call
    starts returning a relation and this row stops appearing, with no other change here.
    """
    if prompts.zero_info(bundle) is not None:
        return []
    return [_event(BLOCK_NAHWI, R_ZERO_ABSENT, citations.OUTCOME_DROP, "", [])]


# ─────────────────────────────────────────────────────────────────────────────
# 5. The generator
# ─────────────────────────────────────────────────────────────────────────────
class TahlilGenerator:
    """A callable `(bundle) -> [claim]`, plus `health()` and `model_id`.

    Injected into `tahlil_service.analyze_word`; the service owns the gate, the cache and
    the coverage log for gate verdicts, and this owns the model calls and its own two
    post-checks. Nothing here writes to the page.
    """

    def __init__(self, llm=None, *, chat=None):
        """`llm` is an `LLMClient` (or anything with `.chat`/`.health`); `chat` is a bare
        callable `(system, user) -> str` for tests that need no client at all.

        Both are optional and the client is built LAZILY: constructing an `LLMClient`
        imports `ollama` and reads the environment, and this object is created at app
        startup, where an import error or a missing model must degrade the Tahlil page
        rather than take the API down.
        """
        self._llm = llm
        self._chat = chat
        self._built = llm is not None

    # ── plumbing ────────────────────────────────────────────────────────
    @property
    def model_id(self) -> str:
        return model_id_from_env()

    def _client(self):
        if not self._built:
            self._built = True
            try:
                from generation.llm_client import LLMClient

                self._llm = LLMClient()
            except Exception as exc:
                print(f"[tahlil.generator] LLM unavailable: {type(exc).__name__}: {exc}",
                      file=sys.stderr)
                self._llm = None
        return self._llm

    def verse(self, message: str, handles: dict[str, str],
              lines: dict[str, str] | None = None,
              events: list[dict] | None = None) -> list[dict]:
        """The verse synthesis: ONE call over the words' surviving claims.

        Isolated exactly as `_level` is — a failure costs the synthesis and nothing else,
        and it is REPORTED on stderr rather than read as «the model had nothing to say».

        The two block-scoped post-checks do not run: `check_synthesis` is about the letters
        block and `check_sense_selection` about a form row, and a verse claim can carry
        neither. `check_quotation` and `check_prompt_echo` DO run — a thesis that only
        repeats one word's claim back is the same non-statement one storey up, and the
        worked example sits in the system prompt for this call too. `lines` is the verse
        evidence as the model saw it, supplied by the caller for the same reason the level
        checks take a slice: containment must be tested against what THIS call was shown.
        """
        events = events if events is not None else []
        try:
            raw = self._ask(message)
        except Exception as exc:
            print(f"[tahlil.generator] verse failed: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            events.append(_event(VERSE_BLOCK, R_BLOCK_FAILED, citations.OUTCOME_DROP,
                                 f"{type(exc).__name__}: {exc}"))
            return []
        parsed = extract_json_array(raw)
        if parsed is None:
            events.append(_event(VERSE_BLOCK, R_UNPARSEABLE, citations.OUTCOME_DROP, raw))
            return []
        claims: list[dict] = []
        for element in parsed:
            if not isinstance(element, dict):
                claims.append(element)          # the SERVICE's gate names it
                continue
            claims.append({
                "block": VERSE_BLOCK,
                "text_ar": element.get("text_ar"),
                "cites": prompts.resolve_cites(element.get("cites"), handles),
                "badge": element.get("badge"),
            })
        # Every refusal is LOGGED. Discarding these events — which the first draft of this
        # method did, with `claims, _ = ...` — makes a refused thesis indistinguishable from
        # a model that had nothing to say, and silent filtering is the one thing this layer
        # forbids: it turns a prompt regression into a quiet page.
        claims, quoted = check_quotation(claims, lines or {})
        events.extend(quoted)
        claims, echoed = check_prompt_echo(claims, VERSE_BLOCK)
        events.extend(echoed)
        return claims

    def health(self) -> bool:
        """False rather than raising — the service turns it into a stated reason.

        A bare `chat` callable is considered healthy: it exists, so it can be called. There
        is nothing to probe.
        """
        if self._chat is not None:
            return True
        client = self._client()
        if client is None:
            return False
        try:
            return bool(client.health())
        except Exception:
            return False

    def _ask(self, user: str) -> str:
        if self._chat is not None:
            return self._chat(prompts.SYSTEM_PROMPT, user)
        client = self._client()
        if client is None:
            raise RuntimeError("no LLM client")
        return client.chat(prompts.SYSTEM_PROMPT, [{"role": "user", "content": user}])

    # ── one block ───────────────────────────────────────────────────────
    def _block(self, block: str, user: str, handles: dict[str, str],
               events: list[dict]) -> list[dict]:
        """One model call, fully isolated. Returns claims stamped with `block`.

        Every failure — transport, unparseable answer, a non-dict element — is caught HERE
        so that one block's collapse cannot cost another block its prose (tasks.md 7.3).
        The claims are stamped with the block the call was made for, so the model never
        names it and `generator-unknown-block` is unreachable from this generator.
        """
        try:
            raw = self._ask(user)
        except Exception as exc:
            events.append(_event(block, R_BLOCK_FAILED, citations.OUTCOME_DROP,
                                 f"{type(exc).__name__}: {exc}"))
            return []
        parsed = extract_json_array(raw)
        if parsed is None:
            events.append(_event(block, R_UNPARSEABLE, citations.OUTCOME_DROP, raw))
            return []
        out: list[dict] = []
        for element in parsed:
            if not isinstance(element, dict):
                # Left to the SERVICE's gate rather than dropped here: `generator-malformed
                # -claim` is its reason, its log row, and its already-proved branch. Two
                # layers refusing the same shape under two names would double-count it in
                # the sweep.
                out.append(element)
                continue
            claim = {
                "block": block,
                "text_ar": element.get("text_ar"),
                "cites": prompts.resolve_cites(element.get("cites"), handles),
                "badge": element.get("badge"),
            }
            if "sense_ar" in element:
                claim["sense_ar"] = element["sense_ar"]
            out.append(claim)
        return out

    def _level(self, block: str, bundle: dict, events: list[dict]) -> list[dict]:
        """One level, end to end — prompt, call, post-check — inside ONE isolation boundary.

        The isolation used to wrap the model call alone, and a real qwen answer proved that
        insufficient within minutes of the first live run: an array containing a bare `7`
        reached `check_sense_selection`, `7.get("cites")` raised `AttributeError`, the
        exception escaped past the per-block guard into the service's catch-all, and a page
        whose four deterministic blocks were sitting there assembled and correct came back
        as «تعذّر توليد النص» — with every event collected so far lost, so the coverage log
        could not even say what had happened.

        Both halves of that are fixed: the post-checks are now total over non-dict claims
        (they pass them to the service, which names them `generator-malformed-claim`), and
        the boundary now covers everything block-scoped — prompt assembly included, since a
        partial bundle can fail there too. The failure is still *reported*, on stderr and in
        the log, so a defect in a post-check cannot quietly read as «this block said
        nothing».
        """
        try:
            user, handles = prompts.build_user_message(bundle, block)
            if not user:
                # No evidence for this block — a rootless word's الحروف, a word with no
                # naẓīr and no aṣl. Spending a call would buy a claim that cannot cite.
                return []
            claims = self._block(block, user, handles, events)
            # Block-agnostic first: «this only repeats its source» is a more fundamental
            # verdict than «this synthesis is incomplete», and one claim gets one outcome.
            claims, block_events = check_quotation(claims, prompts.slice_lines(bundle, block))
            events.extend(block_events)
            claims, block_events = check_prompt_echo(claims, block)
            events.extend(block_events)
            if block == BLOCK_HURUF:
                claims, block_events = check_synthesis(claims, bundle)
                events.extend(block_events)
            elif block == BLOCK_SARFI:
                claims, block_events = check_sense_selection(claims, bundle)
                events.extend(block_events)
            elif block == BLOCK_DALALI:
                claims, block_events = check_verse_gloss(claims, block)
                events.extend(block_events)
            return claims
        except Exception as exc:
            print(f"[tahlil.generator] {block} failed: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            events.append(_event(block, R_BLOCK_FAILED, citations.OUTCOME_DROP,
                                 f"{type(exc).__name__}: {exc}"))
            return []

    # ── the five calls ──────────────────────────────────────────────────
    def __call__(self, bundle: dict) -> list[dict]:
        """Generate the four levels, then the تركيب over what survives a pre-gate.

        Returns EVERY claim produced, including ones the service's gate will refuse: the
        gate is the authority and its log is the record. The only claims withheld are the
        two this layer refuses itself, and each of those is logged here with its reason.
        """
        bundle = bundle if isinstance(bundle, dict) else {}
        ref = bundle.get("ref", "")
        events: list[dict] = list(zero_events(bundle))
        all_claims: list[dict] = []
        pre_gated: dict[str, list[dict]] = {}

        for block in LEVEL_BLOCKS:
            claims = self._level(block, bundle, events)
            all_claims.extend(claims)
            # The pre-gate: what the تركيب may compose over. Pure and identical to the
            # service's verdict; it filters the تركيب's INPUT, never this method's output.
            kept, _, _ = citations.validate(claims, bundle)
            pre_gated[block] = kept

        if prompts.tarkib_enabled():
            # Same boundary as a level, for the same reason: the تركيب prompt is assembled
            # from MODEL-produced claims, so its inputs are adversarial too — and §8.4
            # promises that a تركيب failure never affects blocks 1–4. An exception escaping
            # here would break that promise after the four levels had already succeeded.
            try:
                user, handles = prompts.build_user_message(bundle, BLOCK_TARKIB,
                                                           level_claims=pre_gated)
                if user:
                    lines = {e["cite_id"]: e["line_ar"]
                             for e in prompts.tarkib_slice(bundle, pre_gated)}
                    thesis, thesis_events = check_quotation(
                        self._block(BLOCK_TARKIB, user, handles, events), lines)
                    events.extend(thesis_events)
                    all_claims.extend(thesis)
            except Exception as exc:
                print(f"[tahlil.generator] tarkib failed: {type(exc).__name__}: {exc}",
                      file=sys.stderr)
                events.append(_event(BLOCK_TARKIB, R_BLOCK_FAILED, citations.OUTCOME_DROP,
                                     f"{type(exc).__name__}: {exc}"))

        if events:
            coverage.record(events, ref=ref)
        return all_claims


_default: TahlilGenerator | None = None


def default_generator() -> TahlilGenerator:
    """The process-wide generator, shared by `/tahlil/word` and `/tahlil/review`.

    Shared **because `review_key` must agree across the two routes**. A review attests a
    rendering, and the key carries `model_id`; if the word route resolved it from a
    generator and the review route from «no generator at all», every review would be
    recorded under a key no analysis can ever produce — the flag would read False forever,
    and the «غير مُحقَّق» mention that design decision 3b makes mandatory would never come
    off. One accessor makes the two impossible to disagree.
    """
    global _default
    if _default is None:
        _default = TahlilGenerator()
    return _default


if __name__ == "__main__":  # smoke test — no model required
    from linguistics.tahlil.evidence import build

    bundle = build(23, 61, 2)

    def fake(_system: str, user: str) -> str:
        """Answers whatever block it is shown, by citing handle 1 (and 2 when present)."""
        n = user.count("\n[")
        cites = [1, 2] if n > 1 else [1]
        return json.dumps([{"text_ar": "دعوى تجريبية للاختبار", "cites": cites,
                            "badge": "تأويلي"}], ensure_ascii=False)

    os.environ.setdefault("TAHLIL_COVERAGE_LOG", "/tmp/tahlil-smoke.tsv")
    gen = TahlilGenerator(chat=fake)
    print("model_id:", gen.model_id, "· health:", gen.health())
    for claim in gen(bundle):
        print(f"  [{claim.get('block')}] {claim.get('text_ar')}  ← {claim.get('cites')}")
