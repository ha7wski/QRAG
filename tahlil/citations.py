"""
citations.py — the cite-or-omit gate. THE structural guarantee of the Tahlil page.

Every prior LLM attempt in this repo failed the same way: `lisan/` produced fluent Arabic
that contradicted the attested root sense (the synthesis was deleted and replaced by a
template), `madar/`'s synthesis is env-gated off after ~50% of witness-root outputs came
back problematic, and the mīzān produced a confident, complete, WRONG answer for lafẓ
al-jalāla that no coverage rate could see.

So the question this module answers is not "can the model write a تعليل" — it can,
fluently, and that is the danger. It is: **what structural guarantee stops a
fluent-but-false sentence from reaching the page?** The answer is that the model never
supplies facts, only prose over an evidence bundle assembled deterministically, and every
sentence it emits must resolve to a citation *here, in code*, or be dropped before render.

A prompt instruction to "only cite the given sources" is a request. A validator is a
guarantee. That distinction is the whole design, because the failure is invisible from the
page: nobody reading «توحي بحركة منسابة متواصلة» can tell whether the letter dataset
actually says that.

WHAT THIS MODULE DOES *NOT* DO — state it plainly, because misreading it is the main risk:
it bounds **provenance**, never **truth**. A claim can cite the right letter row and still
be a bad reading. That is why the badges say «غير مُحقَّق» in words, why acceptance requires
per-source human inspection (task 12.4), and why nothing here is called "verification".

Three outcomes, not two:
  * KEPT       — renders as-is.
  * DOWNGRADED — renders, with a weaker badge. Exactly ONE reason does this
    (`sense-selection-unanchored`): the provenance is real but *under-determines* the
    claim, so the honest response is a weaker badge, not silence.
  * DROPPED    — never renders; no provenance at all.

Pure stdlib: no fastapi, no pydantic, no network, no model. Importable and testable on its
own, which is the point — the adversarial claim-set tests (task 5.7) run before any
generator exists.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# 1. The three badges. Labels are CONTRACT, not UI choice (design.md §3b): a badge
#    read as a quality mark defeats the guarantee, so «مُولَّد» carries «غير مُحقَّق»
#    in its own tooltip text.
# ─────────────────────────────────────────────────────────────────────────────
BADGE_VERIFIED = "محقّق"
BADGE_GENERATED = "مُولَّد"
BADGE_INTERPRETIVE = "تأويلي"

BADGES = (BADGE_VERIFIED, BADGE_GENERATED, BADGE_INTERPRETIVE)

BADGE_LABELS = {
    BADGE_VERIFIED: "معطى محقّق",
    BADGE_GENERATED: "مُولَّد",
    BADGE_INTERPRETIVE: "تأويلي",
}

BADGE_TOOLTIPS = {
    BADGE_VERIFIED: "معطى محقّق من الإعراب/الصرف",
    BADGE_GENERATED: "مُولَّد ومُسنَد إلى شواهد، غير مُحقَّق",
    BADGE_INTERPRETIVE: "تأويلي: إطار نظري مُختلَف فيه (دلالة الحروف / المقارنة البلاغية)",
}

# The mention that rides on every un-reviewed generated block (design.md §3b).
UNVERIFIED_MENTION = "غير مُحقَّق"

# ─────────────────────────────────────────────────────────────────────────────
# 2. The CLOSED reason set. An unknown reason must fail the sweep (task 12.2), same
#    contract as `qac_labels.translate_features` raising on an unmapped code: silent
#    drift is the thing being prevented, so there is no "other" bucket.
# ─────────────────────────────────────────────────────────────────────────────
R_NO_CITATION = "no-citation"
R_UNRESOLVED = "unresolved-citation"
R_CLAIMED_VERIFIED = "generated-claimed-verified"
R_NON_ARABIC = "non-arabic-output"
R_UNCHECKED_CONTRAST = "unchecked-contrast"
R_SENSE_UNSELECTED = "form-sense-unselected"
R_SENSE_UNANCHORED = "sense-selection-unanchored"
R_TARKIB_UNSUPPORTED = "tarkib-unsupported-by-levels"
R_TARKIB_SINGLE = "tarkib-single-level"
R_INSUFFICIENT_LEVELS = "insufficient-levels"
R_UNSUPPORTED_RELATION = "unsupported-lexical-relation"
R_VERSE_UNANCHORED = "verse-claim-unanchored"

REASONS = frozenset({
    R_NO_CITATION, R_UNRESOLVED, R_CLAIMED_VERIFIED, R_NON_ARABIC,
    R_UNCHECKED_CONTRAST, R_SENSE_UNSELECTED, R_SENSE_UNANCHORED,
    R_TARKIB_UNSUPPORTED, R_TARKIB_SINGLE, R_INSUFFICIENT_LEVELS,
    R_UNSUPPORTED_RELATION, R_VERSE_UNANCHORED,
})

# The ONLY reason that re-badges instead of dropping. Kept as a set of one so the
# invariant is machine-checkable (task 5.7 asserts it) rather than a comment.
DOWNGRADE_REASONS = frozenset({R_SENSE_UNANCHORED})

OUTCOME_KEPT, OUTCOME_DOWNGRADE, OUTCOME_DROP = "kept", "downgrade", "drop"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Evidence-id grammar. Ids are MINTED BY THE OWNING MODULE and copied verbatim by
#    evidence.py (tasks.md 4.2) — this module only reads their kind prefix, so a change
#    to a page-range or version token downstream cannot break the gate.
# ─────────────────────────────────────────────────────────────────────────────
KIND_LETTER, KIND_NAZIR, KIND_SIGHA = "letter", "nazir", "sigha"
KIND_CONTRAST, KIND_MAQAYIS, KIND_QAC = "contrast", "maqayis", "qac"

KINDS = (KIND_LETTER, KIND_NAZIR, KIND_SIGHA, KIND_CONTRAST, KIND_MAQAYIS, KIND_QAC)

# Citations that anchor a claim IN THE CORPUS — the Quran's own usage (a naẓīr) or a
# syntactic fact of this very verse (a qac field). These are what makes a multi-sense
# selection مُولَّد rather than تأويلي: they show the sense *in use*, where a KB row only
# shows the sense *exists*.
#
# **`qac` stays in this set — settled decision, not an oversight.** It was raised as an open
# question: a `qac:` cite is available on 98.98 % of words, so leaving it in makes the one
# downgrade erasable almost everywhere. Removing it was rejected, and the reason is about
# MEASUREMENT as much as about labelling. تأويلي means «contested theoretical framework»
# — the letters doctrine, a بلاغة comparison. A word's grammatical role and its head are
# neither: they are read off the treebank, and nobody disputes them. A reading anchored on
# one is anchored on a *fact*, so badging it تأويلي would file a fact under «contested» —
# and §12 judges the prompt by the badge distribution, so that mislabelling would corrupt
# the measurement at its source. The downgrade is therefore deliberately narrow: it fires
# when a multi-sense selection cites **neither** the Quran's usage **nor** a syntactic fact
# of the verse — i.e. when it rests on the KB row alone, which proves only that the sense
# exists.
CORPUS_DISAMBIGUATORS = frozenset({KIND_NAZIR, KIND_QAC})

# Interpretive by construction: the letter framework is contested scholarship, and a
# contrast («أبلغ من X») is a comparison, interpretive even when both forms are facts.
# This set is the WHOLE definition of تأويلي-by-source; anything outside it that reaches
# تأويلي does so only through the unanchored-selection rule below.
INTERPRETIVE_KINDS = frozenset({KIND_LETTER, KIND_CONTRAST})

BLOCKS = ("huruf", "sarfi", "nahwi", "dalali", "tarkib")

# Latin word-characters and CJK — the qwen drift post-check proven in madar_service.py.
# A fluent-but-corrupted paragraph is worse than none, so a leak voids the claim.
_LATIN_RE = re.compile(r"[A-Za-z]")
_CJK_RE = re.compile(r"[　-鿿가-퟿]")

# Arabic absence markers. **NOT the gate's rule** — see `states_absence` below and the
# exact-containment check in `_contrast_admissible`. Kept only as a display-side
# diagnostic; nothing on the trust path reads this tuple.
_ABSENCE_MARKERS = ("لم ترد", "لم يرد", "لم تأت", "لم يأت", "غير واردة", "غير وارد", "لا ترد")

# The one tolerance the absence check grants: a re-wrapped line. Everything else about the
# sentence is compared verbatim.
_WS_RE = re.compile(r"\s+")

# Where `validate` stashes the badge the GENERATOR asked for, before it rewrites `badge`
# to the licensed one. Read back by `_event`, so a claim dropped by a LATER composition
# rule (تركيب/verse) still logs what the generator wanted rather than what the gate
# allowed — otherwise every such row reads «تأويلي -> …» and the signal the log exists to
# carry (how often the prompt stops supplying a disambiguator) is erased.
BADGE_ASKED_KEY = "_badge_asked"

# Stand-in for a cite that is not a string at all. It carries no ":" so `kind_of` returns
# None and the claim is forced down the unresolved path — a hostile `cites: [{"id": …}]`
# must be a DROP, never a TypeError out of the gate.
_NON_STR_CITE = "<non-str {}>"


def kind_of(cite_id: str) -> str | None:
    """The evidence kind of an id, or None if it does not follow the grammar."""
    if not isinstance(cite_id, str) or ":" not in cite_id:
        return None
    prefix = cite_id.split(":", 1)[0]
    return prefix if prefix in KINDS else None


def is_arabic_clean(text: str) -> bool:
    """True when `text` is a non-blank string carrying no Latin word-character and no CJK.

    Digits, Arabic punctuation and the Arabic-Indic numerals are fine — this rejects a
    model that switched language mid-sentence, not a سورة number.

    A NON-STRING is False, not an exception: `text_ar: 123` is exactly the kind of shape
    hostile/broken model output takes, and the gate exists to absorb it. Blank text is
    False for the same reason a missing citation is — an empty claim renders as an empty
    bullet, which reads as content the page never had.
    """
    if not isinstance(text, str):
        return False
    if not text.strip():
        return False
    return not _LATIN_RE.search(text) and not _CJK_RE.search(text)


def states_absence(text: str) -> bool:
    """True when `text` carries one of the Arabic absence markers.

    **NOT the citation gate's rule, and must never become it again.** A marker scan is
    defeated twice over: a claim can state the absence at the WRONG GRANULARITY («ولم ترد
    أفعَلَ من هذا الجذر» — false for سرع, whose اسم تفضيل أَسْرَع does occur), and a claim
    can DENY the absence and still contain the marker («لا يصحّ أن يقال إنّ صيغة أفعَلَ لم
    ترد، فقد وردت»). Both rendered through the shipped gate. The gate now requires the
    evidence layer's own computed sentence verbatim — see `_contrast_admissible`.

    Survives as a display/diagnostic helper only.
    """
    if not isinstance(text, str):
        return False
    return any(marker in text for marker in _ABSENCE_MARKERS)


def _normalize_ws(text: str) -> str:
    """Collapse every whitespace run to one space and strip.

    The single tolerance the absence check grants: a generator that re-wraps a line must
    not flip a verdict. Nothing else is folded — no diacritic stripping, no synonym
    matching — because every tolerance added here is a way for a wrong sentence to pass.
    """
    return _WS_RE.sub(" ", text).strip()


def _display_text(value: object) -> str:
    """A claim's text as it goes into the LOG (never into the page).

    Non-strings are `repr`'d rather than blanked: a row reading `123` tells the triage
    sweep what the generator actually emitted, where an empty cell says only that
    something was dropped.
    """
    if isinstance(value, str):
        return value
    return "" if value is None else repr(value)


def _as_cite_list(value: object) -> list[str]:
    """Coerce a claim's `cites` into a list of STRINGS — total over hostile shapes.

    Every non-string element becomes an unresolvable placeholder instead of being passed
    to `id in items`, where a dict would raise `TypeError: unhashable type`. The claim then
    drops as `unresolved-citation`, which is the correct verdict: a cite that is not an
    evidence id resolves to nothing.
    """
    if value is None:
        return []
    seq = list(value) if isinstance(value, (list, tuple)) else [value]
    return [c if isinstance(c, str) else _NON_STR_CITE.format(type(c).__name__) for c in seq]


def _asked_badge(claim: dict) -> str:
    """The badge the GENERATOR asked for, even after `validate` rewrote `badge`."""
    asked = claim.get(BADGE_ASKED_KEY, claim.get("badge"))
    return asked if isinstance(asked, str) else ""


def _event(claim: dict, reason: str, outcome: str, badge_after: str | None = None) -> dict:
    """One log row. Total over hostile claims: a non-dict claim yields an empty row rather
    than raising, because the gate's whole job is to absorb malformed output."""
    claim = claim if isinstance(claim, dict) else {}
    block = claim.get("block")
    return {
        "block": block if isinstance(block, str) else "",
        "reason": reason,
        "outcome": outcome,
        "badge_before": _asked_badge(claim),
        "badge_after": badge_after or "",
        "text": _display_text(claim.get("text_ar")),
        "cites": _as_cite_list(claim.get("cites")),
    }


def _claim_key(claim: dict) -> tuple:
    """Identity of a claim for matching it against its own log events."""
    block = claim.get("block")
    return (block if isinstance(block, str) else "",
            _display_text(claim.get("text_ar")),
            tuple(_as_cite_list(claim.get("cites"))))


def _event_key(event: dict) -> tuple:
    return (event.get("block", ""), event.get("text", ""), tuple(event.get("cites") or ()))


def surviving_downgrades(downgraded: list[dict], kept: list[dict]) -> list[dict]:
    """Drop downgrade events whose claim did NOT survive the composition rules.

    ONE claim must produce ONE outcome. A تركيب that `validate` downgraded and the
    composition rules then dropped would otherwise be reported twice, with contradictory
    verdicts — it renders (downgraded) *and* it never renders (dropped) — and the sweep
    would count it in both columns.

    Factored out so that every composition validator built on top of `validate` filters:
    `validate_tarkib` did and `validate_verse` did not, which is exactly the omission a
    shared helper makes impossible to repeat.
    """
    keys = {_claim_key(c) for c in kept}
    return [d for d in downgraded if _event_key(d) in keys]


_TASHKEEL_RE = re.compile(r"[ً-ْٰـ]")


def _bare(text: str) -> str:
    """Arabic text with tashkīl and tatweel removed — for MATCHING only, never for display.

    A generator writing its own denial will not reproduce the KB's vocalization of a باب
    («فَعَّلَ» vs «فعل»), so a verbatim comparison would miss it.
    """
    return _TASHKEEL_RE.sub("", text)


def _denies_an_attested_form(item: dict, normalized_text: str) -> bool:
    """True when a claim appears to state that an ATTESTED contrast form does NOT occur.

    Closes the spec scenario «a claim citing the attested candidate cannot state that it is
    absent». Per-candidate ids fixed the realistic path — denying target A while citing
    target B now fails to resolve — but a claim that cites the attested candidate's OWN id
    and denies it anyway was still kept, because `attested is True` returned admissible
    unconditionally. On root عبد that renders «ولم ترد صيغة فَعَّلَ فعلاً من هذا الجذر»
    while the corpus holds عَبَّدتَّ at 26:22:6: a false absence, badged and rendered.

    The check is **exact containment of the evidence layer's own `denial_sentence_ar`** —
    symmetric with the licensing direction, and deterministic. A heuristic was tried first
    (an absence marker anywhere + this باب named anywhere) and is WRONG: a claim that
    legitimately enumerates «يقابله بابا فَعَّلَ وأَفْعَلَ» and denies only the second names
    the attested باب too, so the heuristic dropped a correct claim. Tashkīl is folded on
    both sides because a generator will not reproduce the KB's vocalization exactly.

    Known limit, stated rather than papered over: a denial *paraphrased* away from the
    computed sentence is not caught here. The mitigation is the one the whole change
    relies on — per-source human inspection (task 12.4) — not a cleverer pattern, because
    a pattern that can be fooled in the licensing direction is worse than none.
    """
    denial = item.get("denial_sentence_ar")
    if not isinstance(denial, str) or not denial.strip():
        return False
    return _bare(_normalize_ws(denial)) in _bare(normalized_text)


def _contrast_admissible(item: dict, normalized_text: str) -> bool:
    """Is a claim allowed to cite THIS contrast item?

    Three cases, and the third is the whole point:

      * no `attested` key       — the bundle never checked this candidate. Inadmissible:
        the forbidden third case of design decision 4, a contrast asserted with no
        attestation verdict either way.
      * `attested is True`      — admissible; the form occurs, there is no absence to state.
      * anything else           — treated as UNATTESTED, and admissible only when the claim
        CONTAINS the evidence layer's own computed absence sentence, verbatim (modulo
        whitespace). Not "contains an absence marker": that denylist is defeated by the
        wrong granularity and by a denial (see `states_absence`). The evidence layer
        already computed the one correct sentence for this candidate, so requiring it
        verbatim takes natural-language interpretation out of the trust path entirely.

    A non-boolean `attested` falls into the third case deliberately — fail closed, since
    the only safe reading of a value the contract does not define is "not proven present".
    An unattested item with no absence sentence to check is inadmissible for the same
    reason: there is nothing the gate could verify, and an unverifiable absence is the
    exact claim this rule exists to stop.
    """
    if "attested" not in item:
        return False
    if item.get("attested") is True:
        return not _denies_an_attested_form(item, normalized_text)
    scope = item.get("absence_scope_ar")
    if not isinstance(scope, str):
        return False
    scope = _normalize_ws(scope)
    if not scope:
        return False
    return scope in normalized_text


def _admissible_badge(kinds: set[str], multi_sense_unanchored: bool) -> str:
    """The badge the CITATIONS license — never the badge the model asked for.

    Order matters and is load-bearing:
      1. an unanchored multi-sense selection is تأويلي (it chose, without corpus support);
      2. any interpretive citation (letter دلالة, contrast) makes the whole claim تأويلي —
         an interpretive ingredient cannot be laundered by pairing it with a naẓīr;
      3. otherwise corpus/lexicon citations license مُولَّد.
    """
    if multi_sense_unanchored:
        return BADGE_INTERPRETIVE
    if kinds & INTERPRETIVE_KINDS:
        return BADGE_INTERPRETIVE
    return BADGE_GENERATED


def validate(claims: list[dict], bundle: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Gate a generator's claim list against the bundle that produced it.

    Returns ``(kept, downgraded, dropped)``. `kept` carries render-ready claims (a
    downgraded claim appears in BOTH `kept` — with its weakened badge — and `downgraded`,
    which holds the log events, because it does render). `dropped` holds log events only.

    A claim is ``{block, text_ar, cites: [id], badge}``. The bundle is
    ``{"items": {cite_id: {...}}, ...}`` — see evidence.py.

    **Total over hostile input.** Model output is untrusted by construction, so no shape
    may crash the gate: a non-dict claim, a non-string `text_ar`, `cites: None`, and cites
    that are ints or dicts all resolve to a DROP with a reason from the closed set. A gate
    that raises is a gate that is bypassed — the 500 replaces the honest stub.

    Checks, in order (each returns a reason from the CLOSED set):
      1. non-Arabic output              -> drop  (the madar post-check, per claim). A
         non-string `text_ar` lands here: it is not Arabic text.
      2. empty cites                    -> drop
      3. any unresolvable cite id       -> drop. A non-string cite is unresolvable by
         construction (`_as_cite_list`).
      4. badge == محقّق from a generator -> drop, NEVER re-badge: a generator asking for
         محقّق is a defect to be seen, not silently corrected
      5. contrast rules                 -> drop when the candidate was never checked, or
         when an unattested candidate is asserted without the candidate's OWN computed
         absence sentence, verbatim (`_contrast_admissible`)
      6. multi-sense sigha row with no corpus disambiguator -> DOWNGRADE to تأويلي
      7. badge admissibility            -> the licensed badge always wins over the asked-for
         one; a claim that asked for مُولَّد over interpretive evidence renders as تأويلي
    """
    bundle = bundle if isinstance(bundle, dict) else {}
    items = bundle.get("items")
    items = items if isinstance(items, dict) else {}
    kept: list[dict] = []
    downgraded: list[dict] = []
    dropped: list[dict] = []

    for raw in (claims if isinstance(claims, (list, tuple)) else []):
        # A claim that is not a dict has no text and no cites; it falls through the same
        # checks as an empty one and drops, instead of raising on `.get`.
        claim = dict(raw) if isinstance(raw, dict) else {}
        text = claim.get("text_ar")
        cites = _as_cite_list(claim.get("cites"))
        # Both are written back so that everything downstream — the composition
        # validators, the log rows, the renderer — sees the coerced values, never the
        # hostile originals.
        claim["cites"] = cites
        claim[BADGE_ASKED_KEY] = _asked_badge(claim)

        if not is_arabic_clean(text):
            dropped.append(_event(claim, R_NON_ARABIC, OUTCOME_DROP))
            continue

        if not cites:
            dropped.append(_event(claim, R_NO_CITATION, OUTCOME_DROP))
            continue

        unresolved = [c for c in cites if c not in items or kind_of(c) is None]
        if unresolved:
            ev = _event(claim, R_UNRESOLVED, OUTCOME_DROP)
            # De-duplicated: a claim repeating one bad id fifty times is one defect, and a
            # fifty-fold row makes the log harder to read, not more informative.
            seen = list(dict.fromkeys(unresolved))
            ev["text"] = f"{text} [unresolved: {','.join(seen)}]"
            dropped.append(ev)
            continue

        if claim.get("badge") == BADGE_VERIFIED:
            dropped.append(_event(claim, R_CLAIMED_VERIFIED, OUTCOME_DROP))
            continue

        kinds = {kind_of(c) for c in cites}

        # ── contrast: the attestation verdict is OURS, never the model's ──────
        normalized = _normalize_ws(text)
        bad_contrast = any(
            not _contrast_admissible(items.get(c) or {}, normalized)
            for c in cites if kind_of(c) == KIND_CONTRAST
        )
        if bad_contrast:
            dropped.append(_event(claim, R_UNCHECKED_CONTRAST, OUTCOME_DROP))
            continue

        # ── multi-sense selection: the one downgrade in the gate ──────────────
        # Citing a KB row proves the sense EXISTS in the KB, never that it HOLDS here.
        multi = any(
            kind_of(c) == KIND_SIGHA and (items.get(c) or {}).get("multi_sense")
            for c in cites
        )
        unanchored = multi and not (kinds & CORPUS_DISAMBIGUATORS)

        licensed = _admissible_badge(kinds, unanchored)
        if unanchored:
            # `badge_before` must record what the generator asked for, not what we allowed
            # it — otherwise every downgrade row reads «تأويلي -> تأويلي» and erases the
            # signal the log exists to carry: how often the prompt stops supplying a
            # disambiguator (task 12.4). Logging before the rewrite is not enough on its
            # own, because a LATER composition rule builds its own event from this same
            # (already rewritten) dict; `BADGE_ASKED_KEY`, stashed at the top of the loop,
            # is what makes that event honest too.
            downgraded.append(_event(claim, R_SENSE_UNANCHORED, OUTCOME_DOWNGRADE,
                                     badge_after=licensed))
        claim["badge"] = licensed
        kept.append(claim)

    return kept, downgraded, dropped


def validate_tarkib(tarkib_claims: list[dict], kept_by_block: dict[str, list[dict]],
                    bundle: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """The تركيب's extra rules, on top of `validate`.

    The تركيب is the page's most interpretive output — the one place the model states a
    thesis — so it is held to composition rules the per-level claims are not:

      * it must cite surviving claims from **at least two** levels; citing one level is a
        restatement, not a synthesis (`tarkib-single-level`);
      * with fewer than two grounded levels beneath it, it is not produced at all
        (`insufficient-levels`) — omitted rather than weakened;
      * it may not introduce a fact absent from the four levels
        (`tarkib-unsupported-by-levels`).

    `kept_by_block` maps the four level ids to their surviving claims. Level provenance is
    read from the evidence kinds each level's surviving claims cite, so a تركيب "citing a
    level" means citing evidence that level actually used — not merely naming it in prose.
    """
    kept_by_block = kept_by_block if isinstance(kept_by_block, dict) else {}
    grounded = [b for b in ("huruf", "sarfi", "nahwi", "dalali") if kept_by_block.get(b)]
    if len(grounded) < 2:
        raw_claims = tarkib_claims if isinstance(tarkib_claims, (list, tuple)) else []
        events = [_event(c, R_INSUFFICIENT_LEVELS, OUTCOME_DROP) for c in raw_claims]
        return [], [], events

    # Which evidence ids each level actually stood on.
    level_of_cite: dict[str, str] = {}
    for block in grounded:
        for claim in kept_by_block.get(block) or []:
            for cite in _as_cite_list(claim.get("cites")):
                level_of_cite.setdefault(cite, block)

    kept, downgraded, dropped = validate(tarkib_claims, bundle)

    final_kept: list[dict] = []
    for claim in kept:
        levels = {level_of_cite.get(c) for c in claim.get("cites") or []}
        levels.discard(None)
        if not levels:
            dropped.append(_event(claim, R_TARKIB_UNSUPPORTED, OUTCOME_DROP))
            continue
        if len(levels) < 2:
            dropped.append(_event(claim, R_TARKIB_SINGLE, OUTCOME_DROP))
            continue
        final_kept.append(claim)

    return final_kept, surviving_downgrades(downgraded, final_kept), dropped


def validate_verse(verse_claims: list[dict], word_claim_refs: set[str],
                   bundle: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Verse-level claims: each must cite a WORD claim, by `surah:ayah:word`.

    The verse synthesis composes word analyses; it is never given the verse text as a
    source of meaning. So its anchors are word refs, not evidence ids, and a claim citing
    none of them is unanchored — it could only have come from the model's own reading of
    the verse, which is precisely what the founding constraint forbids.

    The anchor is the id's `@ref` suffix and ONLY that. A bare `23:61:2` cite never reaches
    this loop: it fails the id grammar and drops as `unresolved-citation` inside
    `validate`, so a second «or the whole cite is a ref» clause here would be unreachable
    trust code — a branch a reader believes is load-bearing and no test can ever exercise.
    """
    refs = (set(word_claim_refs)
            if isinstance(word_claim_refs, (set, frozenset, list, tuple)) else set())
    kept, downgraded, dropped = validate(verse_claims, bundle)
    final: list[dict] = []
    for claim in kept:
        anchors = [c for c in claim.get("cites") or [] if c.split("@")[-1] in refs]
        if not anchors:
            dropped.append(_event(claim, R_VERSE_UNANCHORED, OUTCOME_DROP))
            continue
        final.append(claim)
    # Same one-claim-one-outcome rule as the تركيب: a verse claim downgraded by `validate`
    # and then dropped here must NOT also be reported as rendered-with-a-weaker-badge.
    return final, surviving_downgrades(downgraded, final), dropped


def block_message(block: str, dropped_events: list[dict]) -> str | None:
    """The «قيد الإعداد» reason shown when every claim of a block was dropped.

    An honest stub beats an empty card: the reader learns the block had nothing that could
    be anchored, which is information, where a blank space is not.

    Three DISTINCT messages, one per family of causes, because «تعذّر عرض هذا المستوى» on
    its own tells the reader nothing they could act on:
      * only non-Arabic output      — the generator drifted out of Arabic;
      * only missing/unresolvable cites — the claims had no provenance;
      * anything else (or a mix)    — the claims failed a gate rule.
    Interchangeable wording would make the branches untestable, so each names its own cause.
    """
    reasons = {e.get("reason", "") for e in dropped_events or []
               if isinstance(e, dict) and e.get("block") == block}
    if not reasons:
        return None
    if reasons == {R_NON_ARABIC}:
        return "تعذّر عرض هذا المستوى: النص المولَّد لم يكن عربيًّا خالصًا."
    if reasons <= {R_NO_CITATION, R_UNRESOLVED}:
        return "تعذّر عرض هذا المستوى: لم تُسنَد الدعاوى إلى شواهد."
    return "تعذّر عرض هذا المستوى: لم تجتز الدعاوى شرط الإسناد."


if __name__ == "__main__":
    # The absence sentence the evidence layer computes for the pinned word's أفعَلَ
    # candidate. The gate requires THIS string, not a paraphrase of it.
    absence = "ولم ترد صيغة أَفْعَلَ فعلاً من هذا الجذر"
    contrast_id = "contrast:فَاعَلَ>أَفْعَلَ@0.1.0"   # narrowed to ONE target (tasks.md 4.2)
    bundle = {"items": {
        "letter:س@p110-113": {"kind": "letter"},
        "nazir:3:114:10": {"kind": "nazir"},
        "sigha:bab.III.mufaala@0.1.0": {"kind": "sigha", "multi_sense": True},
        contrast_id: {"kind": "contrast", "attested": False, "absence_scope_ar": absence,
                      "parent_cite_id": "contrast:فَاعَلَ@0.1.0"},
    }}
    claims = [
        {"block": "sarfi", "text_ar": "صيغة المفاعلة هنا للمبالغة",
         "cites": ["sigha:bab.III.mufaala@0.1.0"], "badge": BADGE_GENERATED},
        {"block": "sarfi", "text_ar": "صيغة المفاعلة هنا للمبالغة، بدليل نظيرتها",
         "cites": ["sigha:bab.III.mufaala@0.1.0", "nazir:3:114:10"], "badge": BADGE_GENERATED},
        {"block": "dalali", "text_ar": "دعوى بلا شاهد", "cites": [], "badge": BADGE_GENERATED},
        {"block": "huruf", "text_ar": "the letter siin", "cites": ["letter:س@p110-113"],
         "badge": BADGE_INTERPRETIVE},
        # Absence stated at ROOT granularity — false for سرع (أَسْرَع is an اسم تفضيل): drop.
        {"block": "sarfi", "text_ar": "أبلغ من «يُسرِعون»، ولم ترد أَفْعَلَ من هذا الجذر",
         "cites": [contrast_id], "badge": BADGE_INTERPRETIVE},
        # The candidate's own sentence, verbatim: kept.
        {"block": "sarfi", "text_ar": f"أبلغ من «يُسرِعون»، {absence}",
         "cites": [contrast_id], "badge": BADGE_INTERPRETIVE},
        # Hostile shapes the gate must absorb without raising.
        {"block": "sarfi", "text_ar": 123, "cites": [3, 114, 10], "badge": BADGE_GENERATED},
        None,
    ]
    kept, down, drop = validate(claims, bundle)
    print("kept:", [(c["block"], c["badge"]) for c in kept])
    print("downgraded:", [(d["reason"], d["badge_before"], "->", d["badge_after"]) for d in down])
    print("dropped:", [(d["block"], d["reason"]) for d in drop])
