"""
tahlil_service.py — the Tahlil orchestrator: evidence bundle → (generate) → gate → five
blocks in one fixed order.

This is the *machine* that will receive the generator, built and proved while the
generator is still stubbed (tasks.md §6; §7 turns prose on). Everything it can do without
a model, it does: the deterministic corpus facts and **every KB table lookup** — a lookup
is not generation, so the دلالة الصيغة rows and the باب contrast candidates render on a
machine with no Ollama at all (design decision 8). What disappears without a model is only
the free prose: the per-level تعليل and the تركيب thesis, each stating *why* it is absent.

Five rules run through the whole file, and each one is the scar of a measured failure:

  1. **Fixed block order, taken from `citations.BLOCKS`, never re-declared here.** A second
     copy of an ordered vocabulary is the "two tables drift apart" failure this change has
     already been bitten by twice (the badge strings, the letters dataset). The order is
     الحروف → صرفي → نحوي → دلالي → تركيب and it is presentation contract: the reader meets
     sound before form before syntax before meaning, and only then the synthesis.

  2. **Never fabricate a block.** A block with no evidence renders `available=False` with a
     *stated reason* — «قيد الإعداد» with a cause, the honest-stub contract QLisan already
     uses. An empty card teaches the reader nothing; a card that says «لا جذر لهذه الكلمة»
     teaches them why.

  3. **Never mutate what we were handed.** The bundle's `fiche` is the very object
     `linguistics/analysis/word_analysis.py` returned, and its sub-dicts reach into the process-lifetime
     `qac_words()` cache. Editing one in place would rewrite the QLisan fiche for every
     later request in the process — a silent, global corruption of the page this change
     promised to leave untouched. Every claim is built by *reading*; nothing here writes
     into `bundle`.

  4. **A cap is never rendered as a total, and a stated reason is never discarded.** The
     bundle carries `nazair_totals` (corpus-wide, cap-independent) and `notes` (the closed
     set of reasons the evidence layer mints for everything absent) *precisely* so the page
     cannot present a truncated set as a whole one. Rendering `len(bundle["nazair"])` as
     «جملة النظائر» printed «٨» under the **محقّق** badge for a root with 1 721 occurrences
     — a verified claim about the corpus that the corpus does not support — on 88.3 % of
     rooted words, while the `nazair-capped` note that says so was thrown away. Both halves
     of that failure are fixed here: the total comes from `nazair_totals`, and every note is
     appended to the block that owns it (`NOTE_BLOCK`).

  5. **Only what the MODEL produced is cached; the deterministic half is re-assembled on
     every read.** The cache key carries the prompt/KB/letters/model versions — nothing
     about the corpus, `linguistics/analysis/mizan.py`,
     `linguistics/analysis/qac_labels.py` or `evidence.py`. So a
     cached *whole response* would keep serving a stale مِيزان wazn after a corpus or
     projection change (exactly what the in-flight `harden-mizan-irregular-roots` does to
     258 of 405 sampled words) with a **محقّق** badge on it and nothing able to detect the
     contradiction. The cache therefore stores only the generated claims + the gate's log
     events; every deterministic fact is re-read per request, which is what makes a
     verified claim a claim about the CURRENT corpus. It costs ~0 ms: every lookup beneath
     it is `lru_cache`d.

Degradation is honest at every seam, including the seam with our own dependency:
`linguistics/tahlil/evidence.py` is imported lazily and defensively, so a missing or broken evidence
layer produces a stated reason rather than an exception or, worse, a page assembled from
nothing.

Pure stdlib (no fastapi, no pydantic, no network): the API layer maps this to HTTP, and
this module stays importable and testable on its own.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linguistics.tahlil import citations, coverage  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# 1. The five blocks, in the ONE order they may ever be rendered.
# ─────────────────────────────────────────────────────────────────────────────
BLOCK_HURUF, BLOCK_SARFI, BLOCK_NAHWI, BLOCK_DALALI, BLOCK_TARKIB = citations.BLOCKS

# IMPORTED, never re-declared — see rule 1 in the module docstring. `citations.BLOCKS` is
# the owner because it is the module that ENFORCES block membership (the تركيب composition
# rules read it). A literal copy here would drift silently the first time either side gains
# a block.
BLOCKS_ORDER: tuple[str, ...] = citations.BLOCKS

BLOCK_TITLES = {
    BLOCK_HURUF: "الحروف",
    BLOCK_SARFI: "صرفي",
    BLOCK_NAHWI: "نحوي",
    BLOCK_DALALI: "دلالي",
    BLOCK_TARKIB: "تركيب",
}

# The four levels the تركيب composes. It is not one of them: a thesis about itself is
# not a thesis.
LEVEL_BLOCKS: tuple[str, ...] = tuple(b for b in BLOCKS_ORDER if b != BLOCK_TARKIB)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Generation gate. Mirrors `linguistics/madar/madar_service.py::_synthesis_enabled` — the
#    project's opt-in convention for anything a model writes.
# ─────────────────────────────────────────────────────────────────────────────
GENERATION_ENV = "TAHLIL_GENERATION_ENABLED"

# Cache-key component when `linguistics/tahlil/prompts.py` does not exist yet (§7 owns it). Named
# «stub» on purpose: the day the real PROMPT_VERSION lands, every entry cached under this
# value misses BY CONSTRUCTION, which is exactly the invalidation the design asks for.
PROMPT_VERSION_STUB = "0-stub"

# Model identity for the cache key when the generator does not name itself.
MODEL_ID_ENV = "TAHLIL_MODEL_ID"
MODEL_ID_UNSET = "unset"

# ── Arabic messages. Arabic-only by construction: these are user-facing strings, and a
# Latin fragment here would both break the Arabic-only rule and trip the purity gate that
# voids a block. Notably, the env-var NAME never appears in a message shown to a reader.
_MSG_GEN_DISABLED = "التعليل المولَّد معطّل؛ ما يظهر هنا معطياتٌ محقّقة وجداولُ مصدرية فقط."
_MSG_GEN_UNAVAILABLE = "التعليل المولَّد غير متاح: نموذج اللغة غير جاهز."
_MSG_GEN_FAILED = "التعليل المولَّد غير متاح: تعذّر توليد النص."
# Distinct from the three above ON PURPOSE: the model DID answer, and every claim it made
# was refused for want of a citation. Collapsing this into «تعذّر توليد النص» would hide a
# prompt regression behind what reads like a transport failure.
_MSG_GEN_NOTHING_USABLE = (
    "التعليل المولَّد غير معروض: لم تجتز أيّ دعوى شرطَ الإسناد إلى الشواهد."
)
# Stated ONLY when generation is off — with it on, the sentence is simply false, and a false
# reason is worse than none: it tells the reader to switch on something already switched on
# while the real cause (the composition rules refused the thesis) goes unsaid.
_MSG_TARKIB_NEEDS_GEN = "التركيب لا يُنتَج إلا بالتوليد."
# The تركيب has its own kill switch (tasks.md 8.4), so it has its own reason. Collapsing it
# into «لم يُنتَج تركيبٌ يجتاز الشروط» would tell the reader the composition rules refused a
# thesis that was never asked for — a false statement about the one block whose absence is
# most likely to be deliberate.
_MSG_TARKIB_DISABLED = "التركيب معطّل في هذا التشغيل؛ وبقيّة المستويات تعمل."
_MSG_TARKIB_NONE = "لم يُنتَج لهذه الكلمة تركيبٌ يجتاز شروط التأليف بين المستويات."

_MSG_NO_EVIDENCE = "تعذّر تجميع الشواهد لهذه الكلمة، فلا يُعرض تحليل."
_MSG_NO_ROOT = "لا جذر لهذه الكلمة، فلا يُعرض هذا المستوى، ولا تُحلَّل حروف الكلمة بديلاً عن حروف جذرها."
_MSG_NO_SARFI = "لم تتوفّر معطيات صرفية محقّقة لهذه الكلمة."
_MSG_NO_NAHWI = "لا يوجد تحليل نحوي محفوظ لهذه الكلمة."
_MSG_NO_DALALI = "لم يتوفّر أصلٌ معجمي ولا نظائرُ لهذه الكلمة."

# ── Coverage-log reasons owned by THIS layer. Deliberately outside `citations.REASONS`:
# that set is closed over *claim verdicts* reached by the gate (drop/downgrade), while these
# record a **transport** failure — the request never produced a claim the gate could judge.
# The same way the specs put `zero-layer-absent` and `verse-word-cap` in the log without
# putting them in the gate. `SERVICE_LOG_REASONS` exists so the §12.2 sweep can assert the
# gate's closed set over gate verdicts *and* still recognise these, instead of a reader of
# the log having to guess which strings are legitimate.
R_GENERATION_UNAVAILABLE = "generation-unavailable"
R_MALFORMED_CLAIM = "generator-malformed-claim"
R_UNKNOWN_BLOCK = "generator-unknown-block"
# Long verses are capped before analysis (mean 12.4 words, max 128 — 2:282). The cap is
# LOGGED and STATED in the payload, never applied quietly: a silent truncation reads as
# full coverage, which is the one thing a synthesis over «the verse» must not claim
# falsely (tasks.md 11.3).
R_WORD_CAP = "verse-word-cap"

SERVICE_LOG_REASONS: frozenset[str] = frozenset({
    R_GENERATION_UNAVAILABLE, R_MALFORMED_CLAIM, R_UNKNOWN_BLOCK, R_WORD_CAP,
})

# Naẓāʾir listed inline in the دلالي claim. The full list stays in the bundle; the claim
# quotes a readable head of it and states BOTH how many it shows and the corpus totals, so a
# truncation can never read as the whole (the lesson of every "silent cap" in this project).
_NAZAIR_INLINE = 8

# ─────────────────────────────────────────────────────────────────────────────
# 2b. Bundle notes → the block that owns them.
# ─────────────────────────────────────────────────────────────────────────────
# The evidence layer mints a note for everything it could not supply, or supplied only in
# part. Discarding them (as this module did) is the silent-cap failure one layer up: the
# `nazair-capped` note is the ONE thing that tells a reader the eight naẓāʾir on the page are
# a window onto 1 721, and `no-lexical-anchor` the one thing that says the core sense rests
# on letters alone. Every note therefore lands on a block, and the mapping is *this* module's
# job: `evidence.py` knows what is missing, only the renderer knows where a reader will look
# for it.
#
# The codes are mirrored as literals rather than imported, because `linguistics.tahlil.evidence` is
# imported lazily and defensively (a missing evidence layer must degrade, not break import).
# The drift is pinned by a test asserting `set(NOTE_BLOCK) == evidence.NOTE_CODES` — the same
# contract as the `qac:` field vocabulary below.
NOTE_ROOTLESS = "rootless-word"
NOTE_NO_ASL = "no-lexical-anchor"
NOTE_NO_NAZIR = "no-nazir"
NOTE_NAZAIR_CROSS_LEMMA = "nazair-cross-lemma"
NOTE_NAZAIR_CAPPED = "nazair-capped"
NOTE_NO_SIGHA_ROW = "no-form-row"
NOTE_NO_CONTRAST = "no-contrast-candidates"
NOTE_NO_SYNTAX = "no-syntax-record"
NOTE_SURFACE_UNALIGNED = "surface-unaligned"

NOTE_BLOCK: dict[str, str] = {
    NOTE_ROOTLESS: BLOCK_HURUF,
    NOTE_SURFACE_UNALIGNED: BLOCK_HURUF,
    NOTE_NO_SIGHA_ROW: BLOCK_SARFI,
    NOTE_NO_CONTRAST: BLOCK_SARFI,
    NOTE_NO_SYNTAX: BLOCK_NAHWI,
    NOTE_NO_ASL: BLOCK_DALALI,
    NOTE_NO_NAZIR: BLOCK_DALALI,
    NOTE_NAZAIR_CAPPED: BLOCK_DALALI,
    NOTE_NAZAIR_CROSS_LEMMA: BLOCK_DALALI,
}

# Source lines (the citation strip of task 10.4), Arabic-only.
_SRC_TREEBANK = "المدوّنة الصرفية-النحوية للقرآن (QAC)"
_SRC_MAQAYIS = "معجم مقاييس اللغة لابن فارس"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Environment / version accessors
# ─────────────────────────────────────────────────────────────────────────────
def generation_enabled() -> bool:
    """Prose generation is OFF unless `TAHLIL_GENERATION_ENABLED=1`.

    Mirrors `MADAR_SYNTHESIS_ENABLED`: every layer a model writes is opt-in in this
    project, because every one of them has been measured wrong at least once. Read per
    call, never cached, so a test (or an operator) can flip it without a restart.
    """
    return os.getenv(GENERATION_ENV, "0") == "1"


def prompt_version() -> str:
    """The prompt version that participates in the cache key.

    Imported lazily from `linguistics/tahlil/prompts.py` because §7 has not written it yet, and NOT
    cached: the moment that module lands, the next request keys on the real version and
    every stub-keyed entry becomes unreachable — invalidation by construction rather than
    by anyone remembering to purge a table.
    """
    try:
        from linguistics.tahlil.prompts import PROMPT_VERSION  # type: ignore[attr-defined]

        return str(PROMPT_VERSION)
    except Exception:
        return PROMPT_VERSION_STUB


def tarkib_enabled() -> bool:
    """Whether the تركيب is switched on *within* generation (tasks.md 8.4).

    Owned by `linguistics/tahlil/prompts.py` — the only pure-stdlib half of the generation layer — and
    read here lazily for the same reason `prompt_version` is: this module must stay
    importable, and the page must stay renderable, on a machine where the generation layer
    is absent entirely. Absent ⇒ True, so the block never *claims* to be switched off when
    nothing is there to switch: an absent generation layer is already stated by
    `_MSG_GEN_DISABLED`/`_MSG_GEN_UNAVAILABLE`, and two reasons for one cause is one reason
    too many.
    """
    try:
        from linguistics.tahlil.prompts import tarkib_enabled as _te

        return bool(_te())
    except Exception:
        return True


def kb_version() -> str:
    """Combined دلالة-الصيغة + contrast version, owned by `form_kb`."""
    from linguistics.tahlil.form_kb import kb_version as _kb

    return _kb()


def letters_version() -> str:
    """Letters-dataset version, owned by `huruf`."""
    from linguistics.tahlil.huruf import letters_version as _lv

    return _lv()


def model_id_of(generator: object | None) -> str:
    """The model identity that goes into the cache key.

    A generator that names itself wins; otherwise the env, otherwise «unset». The point is
    only that switching models cannot serve the previous model's prose — so the value must
    *change* when the model changes, not that it be pretty.
    """
    named = getattr(generator, "model_id", None)
    if named:
        return str(named)
    return os.getenv(MODEL_ID_ENV, MODEL_ID_UNSET)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Evidence bundle — lazily, defensively
# ─────────────────────────────────────────────────────────────────────────────
def default_evidence_builder():
    """Return `linguistics.tahlil.evidence.build`, or raise with a reason we can render.

    Imported *inside the call* rather than at module import so that (a) the API can start
    before the evidence layer exists, and (b) the failure is per-request and observable
    instead of a module-level ImportError that takes the whole router down. The caller
    turns the raise into a stated reason on every block — never into a fabricated one.
    """
    from linguistics.tahlil.evidence import build  # noqa: PLC0415  (deliberate: see docstring)

    return build


_warned: set[str] = set()


def _warn_once(detail: str) -> None:
    """Report a technical failure to the operator ONCE, on stderr.

    The reader's message stays Arabic-only — a Python exception name in a rendered string
    would break the Arabic-only rule and trip the very Latin-purity gate that voids a block.
    But the cause must not vanish either, so it goes where technical detail belongs.
    """
    if detail in _warned:
        return
    _warned.add(detail)
    print(f"[tahlil.service] {detail}", file=sys.stderr)


def _build_bundle(builder, surah: int, ayah: int, word: int) -> tuple[dict | None, str | None]:
    """`(bundle, reason)` — exactly one of the two is None. **Never raises.**

    The indices and the position are validated by `analyze_word` BEFORE this is called
    (against `qac_words()`, the same index the fiche is read from), so by the time the
    builder runs the request is known to be well-formed and to name a word the corpus
    holds. **Every** exception from here down is therefore an internal fault of the evidence
    layer, and none of them may be re-mapped onto a user error.

    That is not a stylistic preference; re-raising `ValueError`/`KeyError` cost two real
    guarantees:

      * the router turned them into 400 «bad indices» / 404 «word position not found» for a
        word `/qlisan/word` renders perfectly well — a false statement about the corpus,
        made in the one place the reader cannot check it;
      * it swallowed the **deliberate alarm of task 1.3**: `huruf.describe` raises `KeyError`
        on a root letter it cannot resolve, precisely so the 4 698-word silent truncation
        cannot recur. Dressed as a 404, the loudest signal in the letters layer read as
        «that word does not exist».

    So the fault is reported where technical detail belongs (stderr, once per position) and
    the reader gets a normal response whose blocks state that the evidence could not be
    assembled — which is what actually happened.
    """
    try:
        bundle = builder(surah, ayah, word)
    except Exception as exc:  # evidence layer missing / broken — ALWAYS internal, see above
        _warn_once(f"evidence.build failed for {surah}:{ayah}:{word}: "
                   f"{type(exc).__name__}: {exc}")
        return None, _MSG_NO_EVIDENCE
    if not isinstance(bundle, dict):
        _warn_once(f"evidence.build returned {type(bundle).__name__}, expected dict")
        return None, _MSG_NO_EVIDENCE
    return bundle, None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Claim helpers
# ─────────────────────────────────────────────────────────────────────────────
def _claim(text: str, badge: str, cites: list[str], sources: list[str]) -> dict:
    return {
        "text_ar": text,
        "badge": badge,
        "cites": list(cites),
        "sources": [s for s in sources if s],
    }


def _resolves(items: dict, cite_id: str | None) -> bool:
    """True when `cite_id` is an id the bundle actually carries.

    Deterministic claims are held to the same cite-or-omit standard as generated ones: a
    claim whose citation does not resolve is not rendered. Anything else would put a
    citation strip under a fact pointing at nothing — the exact appearance of provenance
    without the substance, which is worse than no strip at all.
    """
    return bool(cite_id) and cite_id in (items or {})


# The evidence layer's نحوي field vocabulary, mirrored here for lookup and pinned against
# its owner by a drift test. The CITABLE half (`qac:` ids) is closed to the syntactic facts
# of THIS verse and deliberately excludes the morphological routing keys (root / lemma /
# bab / wazn) *and* العلامة: the gate reads every `qac:` cite as a *corpus disambiguator*,
# and `qac:bab@…` would be circular by construction — the باب is precisely what ROUTED the
# KB row, so it cannot discriminate between that row's senses — while an inflection marker
# discriminates nothing at all. Minting either would silently re-badge every unanchored
# selection as مُولَّد and erase the gate's one downgrade. All three facts still reach the
# page: they arrive under `nahwi_facts`/`fiche` and the deterministic layer below renders
# them as محقّق, attributed to the treebank in words rather than by an id a generator could
# spend as an anchor.
QAC_RELATION, QAC_HEAD, QAC_MARKER = "relation", "head_ref", "marker"


def _qac_cite(items: dict, ref: str, field: str) -> list[str]:
    """`[qac:<field>@<ref>]` when the bundle carries it, else `[]`.

    Ids are minted by the module that OWNS the evidence (tasks.md 4.2) and copied verbatim;
    this only *looks one up*. A miss costs the claim its machine citation — never invents
    one, and never points a citation strip at an id that resolves to nothing.
    """
    cid = f"qac:{field}@{ref}"
    return [cid] if _resolves(items, cid) else []


def _sifat_text(entry: dict) -> str:
    """One letter's phonetic classification as a sentence — fact row, badge محقّق."""
    sifat = entry.get("sifat") or {}
    parts = [p for p in (sifat.get("makhraj"), sifat.get("jahr_hams"),
                         sifat.get("shidda_rakhawa")) if p]
    mumayyiza = [m for m in (sifat.get("sifat_mumayyiza") or []) if m]
    if sifat.get("itbaq"):
        mumayyiza.append("مُطبَقة")
    if sifat.get("istila"):
        mumayyiza.append("مستعلية")
    if mumayyiza:
        parts.append("وفيها " + "، ".join(mumayyiza))
    return f"«{entry.get('letter', '')}» ({entry.get('name', '')}): " + "، ".join(parts) + "."


def _dalala_text(entry: dict) -> str:
    """One letter's meaning per Hasan Abbas — interpretation row, badge تأويلي.

    The position line is emitted ONLY for letters whose dataset entry carries
    `position_notes` (د, ذ and ط carry none). A position reading is never generalized from
    a neighbouring letter: the framework holds that the sense shifts with the slot, so
    borrowing another letter's note would be a fabricated reading wearing a real citation.
    """
    dalala = entry.get("dalala") or {}
    text = f"«{entry.get('letter', '')}» ({entry.get('position', '')}): {dalala.get('core_meaning', '')}"
    if entry.get("has_position_notes") and dalala.get("position_notes"):
        text += f" — في هذا الموضع: {dalala['position_notes']}"
    return text


def _letter_source(entry: dict, with_page: bool) -> str:
    """The citation strip line for a letter row: author + work (+ page, task 10.4)."""
    from linguistics.tahlil.huruf import SOURCE_AR

    line = f"{SOURCE_AR['author']} — {SOURCE_AR['title']}"
    pages = (entry.get("dalala") or {}).get("pages") or ""
    if with_page and pages:
        line += f"، ص {pages}"
    return line


# ─────────────────────────────────────────────────────────────────────────────
# 6. The four deterministic blocks + the KB lookups
# ─────────────────────────────────────────────────────────────────────────────
def _huruf_claims(bundle: dict) -> tuple[list[dict], str | None]:
    """الحروف: two claims per root letter — صفات (محقّق) and دلالة (تأويلي), never fused.

    Keeping them apart is not layout, it is the guarantee: merged into one sentence, the
    established tajwīd fact silently lends its authority to a contested framework, and the
    reader has no way to tell which half we actually checked (design decision 3).
    """
    letters = bundle.get("letters") or []
    if not letters:
        return [], _MSG_NO_ROOT
    items = bundle.get("items") or {}
    claims: list[dict] = []
    for entry in letters:
        cid = entry.get("cite_id")
        if not _resolves(items, cid):
            continue
        claims.append(_claim(_sifat_text(entry), citations.BADGE_VERIFIED, [cid],
                             [_letter_source(entry, with_page=False), _SRC_TREEBANK]))
        claims.append(_claim(_dalala_text(entry), citations.BADGE_INTERPRETIVE, [cid],
                             [_letter_source(entry, with_page=True)]))
    if not claims:
        return [], _MSG_NO_ROOT
    return claims, None


def _sigha_claims(bundle: dict) -> list[dict]:
    """The دلالة الصيغة rows that matched — a TABLE LOOKUP, so it renders with no model.

    Badged مُولَّد, and the text lists the row's senses as **alternatives**, because that
    is what the row is. Choosing one of them is a reading, not a lookup, and belongs to the
    generated layer where the gate can weigh whether the choice was anchored (§5.3).
    """
    items = bundle.get("items") or {}
    out: list[dict] = []
    for row in bundle.get("sigha_rows") or []:
        cid = row.get("cite_id")
        if not _resolves(items, cid):
            continue
        senses = [s.get("sense_ar", "") for s in (row.get("senses") or []) if s.get("sense_ar")]
        if not senses:
            continue
        joined = " أو ".join(senses)
        prefix = "من معاني هذه الصيغة" if len(senses) > 1 else "دلالة هذه الصيغة"
        text = f"{prefix} «{row.get('key', '')}»: {joined}."
        if len(senses) > 1:
            text += " وهي بدائلُ يُنتقى منها بالسياق، لا معنًى واحدٌ مقطوعٌ به."
        out.append(_claim(text, citations.BADGE_GENERATED, [cid],
                          [row.get("provenance", ""), f"{row.get('id', '')} · {cid}"]))
    return out


def _contrast_claims(bundle: dict) -> list[dict]:
    """The باب contrast candidates — table lookup + OUR attestation verdict.

    A candidate the bundle did not check is **not rendered**. That is the forbidden third
    case of design decision 4: a contrast asserted without an attestation verdict either
    way. Rendering it and hoping the generator words it carefully is precisely the "prompt
    instruction instead of a validator" the whole change exists to refuse.

    An unattested candidate states its absence **at its own granularity** — «فعلاً» when
    the missing candidate is a verb — because a bare «لم ترد أفعَلَ» is false for root سرع,
    which does attest أَسْرَع as an اسم تفضيل (6:62).
    """
    items = bundle.get("items") or {}
    out: list[dict] = []
    for cand in bundle.get("contrast") or []:
        cid = cand.get("cite_id")
        if not _resolves(items, cid):
            continue
        if "attested" not in cand:
            continue  # never checked → never rendered
        attested = cand.get("attested")
        target = cand.get("target") or {}
        target_bab = target.get("bab", "")
        text = f"يقابل بابَ «{cand.get('bab', '')}» في هذا الموضع بابُ «{target_bab}»"
        rationale = (cand.get("rationale_ar") or "").strip().rstrip(".،؛")
        if rationale:
            text += f"؛ {rationale}"
        if attested:
            refs = list(cand.get("attested_refs") or [])
            total = cand.get("attested_count", len(refs))
            text += (f"، وقد وردت هذه الصيغة من هذا الجذر في {'، '.join(refs[:3])}"
                     f" (جملة المواضع: {total})." if refs else ".")
        else:
            # The absence sentence is COPIED from the candidate when its owner minted one —
            # the same verbatim rule as the ids. It states the missing باب *and* its POS
            # («ولم ترد صيغة أَفْعَلَ فعلاً من هذا الجذر»); a bare «لم ترد أفعَلَ» would be
            # false for root سرع, which does attest أَسْرَع as an اسم تفضيل (6:62).
            absence = (cand.get("absence_scope_ar") or "").strip()
            if not absence:
                qualifier = "فعلاً " if target.get("pos") == "V" else ""
                absence = f"ولم ترد صيغة {target_bab} {qualifier}من هذا الجذر"
            text += f"، {absence} في القرآن."
        out.append(_claim(text.strip(), citations.BADGE_INTERPRETIVE, [cid],
                          [cand.get("provenance", ""), cid]))
    return out


def _sarfi_claims(bundle: dict) -> tuple[list[dict], str | None]:
    """صرفي: the treebank facts (محقّق) then the KB lookups (مُولَّد / تأويلي).

    الجذر / الوزن / الباب carry **no `cites`** and that is deliberate, not an omission:
    the evidence layer mints no `qac:` id for the morphological routing keys, precisely so
    a generator cannot cite the باب as the disambiguator that anchors a sense selected off
    the row the باب itself routed. Their provenance is structural — this code path read the
    treebank — and it is stated in `sources` in words. Every claim is attributed; only the
    citable ones carry an id.
    """
    fiche = bundle.get("fiche") or {}
    sarfi = fiche.get("sarfi") or {}
    claims: list[dict] = []

    root = sarfi.get("root_display") or sarfi.get("root")
    if root:
        text = f"الجذر «{root}»"
        lemma = sarfi.get("lemma_display") or sarfi.get("lemma")
        if lemma:
            text += f"، والمادّة المعجمية «{lemma}»"
        pos_ar = sarfi.get("pos_ar")
        if pos_ar:
            text += f"، والقسم: {pos_ar}"
        claims.append(_claim(text + ".", citations.BADGE_VERIFIED, [], [_SRC_TREEBANK]))

    mizan = sarfi.get("mizan") or {}
    # `verified` is the mīzān's own badge: an اجتهادي projection is explicitly outside
    # «معطى محقّق», and dressing a guessed pattern as a corpus fact is the lafẓ al-jalāla
    # failure — confident, complete, wrong, invisible in any rate.
    if mizan.get("available") and mizan.get("verified") and mizan.get("wazn"):
        text = f"الوزن «{mizan['wazn']}»"
        if mizan.get("bab"):
            text += f"، والباب «{mizan['bab']}»"
        claims.append(_claim(text + ".", citations.BADGE_VERIFIED, [], [_SRC_TREEBANK]))

    claims.extend(_sigha_claims(bundle))
    claims.extend(_contrast_claims(bundle))
    if not claims:
        return [], _MSG_NO_SARFI
    return claims, None


def _nahwi_claims(bundle: dict) -> tuple[list[dict], str | None]:
    """نحوي: الموقع الإعرابي, العلامة and المتعلَّق — read, never derived here.

    Each value is looked up in three places, in this order, and the order is load-bearing:

      1. the `qac:<field>@<ref>` **item**, when the evidence layer minted one — then the
         claim also carries the id, so the fact is citable;
      2. `bundle["nahwi_facts"]`, which carries the deterministic نحوي values that are
         **rendered but not citable**. العلامة lives here: the evidence layer deliberately
         keeps it out of the `qac:` vocabulary, because the gate reads every `qac:` cite as
         a *corpus disambiguator* and an inflection marker discriminates nothing (it is the
         same string on every مضارع مرفوع of الأفعال الخمسة, and for a verb it is read off
         the very morphology record that routed the KB row). Rendered, not spendable;
      3. the fiche.

    Reading the fiche first would drop the exemplar's own العلامة: `analyze_word` resolves
    it through `case_marker`, which returns `None` for 23:61:2, while the verb path gives
    «مرفوع وعلامته ثبوت النون» — the fact §3 of this change exists to add.
    """
    fiche = bundle.get("fiche") or {}
    nahwi = fiche.get("nahwi") or {}
    items = bundle.get("items") or {}
    facts = bundle.get("nahwi_facts") or {}
    ref = bundle.get("ref", "")
    if not nahwi.get("available"):
        return [], nahwi.get("message") or _MSG_NO_NAHWI
    claims: list[dict] = []

    def fact(field: str, label: str, fallback) -> None:
        cite = _qac_cite(items, ref, field)
        value = (items.get(cite[0]) or {}).get("value_ar") if cite else None
        value = value or facts.get(f"{field}_ar") or fallback
        if value:
            claims.append(_claim(f"{label}: {value}.", citations.BADGE_VERIFIED, cite,
                                 [_SRC_TREEBANK]))

    fact(QAC_RELATION, "الموقع الإعرابي", nahwi.get("iraab_ar"))
    fact(QAC_MARKER, "العلامة", nahwi.get("marker_ar"))
    fact(QAC_HEAD, "المتعلَّق", nahwi.get("head_ref"))

    if not claims:
        return [], _MSG_NO_NAHWI
    return claims, None


def _dalali_claims(bundle: dict) -> tuple[list[dict], str | None]:
    """دلالي: Ibn Fāris' cited aṣl (محقّق) + the naẓāʾir list (محقّق).

    The aṣl is quoted, never paraphrased — a paraphrase of a cited lexicon entry is a
    generated claim wearing a citation.

    **The naẓāʾir claim separates what is SHOWN from what the CORPUS HOLDS**, and the two
    numbers come from different places on purpose. The shown count is a fact about this
    page; the totals are facts about the corpus and are read from `nazair_totals`, which the
    evidence layer computes from `root_graph` independently of every cap above it (the
    fiche's own 30-entry list, `NAZAIR_CAP`, and any injected ranker). Counting
    `bundle["nazair"]` instead counts the **cap**: for 2:8:4 (root قول) it printed «جملة
    النظائر: 8» under the **محقّق** badge beside 1 721 corpus occurrences, and for 2:255:1
    «8» beside 2 850. Both are claims about the corpus that the corpus refutes, badged as
    verified — the exact inversion of this project's first rule, on 88.3 % of rooted words.

    A bundle with no `nazair_totals` (an old or hand-built one) states the shown count and
    **says nothing about the total** rather than inferring one: silence is recoverable, a
    wrong verified number is not.
    """
    items = bundle.get("items") or {}
    claims: list[dict] = []

    maqayis = bundle.get("maqayis") or {}
    asl = maqayis.get("asl_text")
    if isinstance(asl, list):
        asl = " ".join(a for a in asl if a)
    cid = maqayis.get("cite_id")
    if asl and _resolves(items, cid):
        claims.append(_claim(f"أصل المادّة عند ابن فارس: «{asl}».", citations.BADGE_VERIFIED,
                             [cid], [_SRC_MAQAYIS]))

    nazair = [n for n in (bundle.get("nazair") or []) if _resolves(items, n.get("cite_id"))]
    if nazair:
        shown = nazair[:_NAZAIR_INLINE]
        refs = [n.get("ref", "") for n in shown]
        text = f"من نظائر هذا الجذر في القرآن: {'، '.join(refs)}"
        totals = bundle.get("nazair_totals")
        if isinstance(totals, dict) and totals.get("root") is not None:
            text += (f" (المعروض منها {len(shown)}، وجملةُ مواضع هذا الجذر في المصحف "
                     f"{totals['root']}، منها {totals.get('same_lemma', 0)} من اللفظ نفسه).")
        else:
            _warn_once("bundle carries no nazair_totals; the naẓāʾir claim states only what "
                       "is shown — a total would be the cap, not the corpus")
            text += f" (المعروض منها {len(shown)}؛ ولم تُحصَ جملتها في المصحف)."
        claims.append(_claim(text, citations.BADGE_VERIFIED,
                             [n["cite_id"] for n in nazair], [_SRC_TREEBANK]))

    if not claims:
        return [], _MSG_NO_DALALI
    return claims, None


_DETERMINISTIC = {
    BLOCK_HURUF: _huruf_claims,
    BLOCK_SARFI: _sarfi_claims,
    BLOCK_NAHWI: _nahwi_claims,
    BLOCK_DALALI: _dalali_claims,
}


# ─────────────────────────────────────────────────────────────────────────────
# 7. Generation (stubbed here; §7 supplies the real generator)
# ─────────────────────────────────────────────────────────────────────────────
def _transport_event(reason: str, claim: object, block: str = "") -> dict:
    """A coverage-log row for output the gate never got to judge (see `SERVICE_LOG_REASONS`).

    `text` carries a *bounded* repr of whatever arrived, because the whole point is to be
    able to see what the generator actually emitted — «a string» is not triageable, and the
    raw object may be arbitrarily large.
    """
    return {
        "block": block,
        "reason": reason,
        "outcome": citations.OUTCOME_DROP,
        "badge_before": "",
        "badge_after": "",
        "text": f"{type(claim).__name__}: {claim!r}"[:300],
        "cites": [],
    }


def _generate(generator, bundle: dict) -> tuple[dict[str, list[dict]], list[dict], str | None]:
    """Run the generator and put its claims THROUGH THE GATE.

    Returns `(kept_by_block, log_events, failure_message)`. A generator that raises, that is
    unreachable, that returns a non-list, **or that returns malformed elements** gives a
    stated reason and/or logged drops — never an exception escaping into the request path,
    because an LLM outage (or an LLM having a bad day with JSON) must degrade the page, not
    break it.

    Malformed elements are the ordinary case, not the exotic one: a model asked for a JSON
    array of objects returns an array of **strings** more often than it returns anything
    else, and `["…"]`, `[1, 2]`, `['{"block": …}']` (the nested-JSON-string shape) and
    `[[…]]` all used to reach `claim.get("block")` and take the whole request down with an
    `AttributeError` — a 500 for a word whose deterministic blocks were sitting right there,
    assembled and correct. Each bad element is now dropped *individually* and written to the
    coverage log with what it was, so the page degrades to «the model wrote nothing usable»
    while the operator can see exactly what arrived.

    The gate is not optional and not a formality: **every** well-formed claim goes through
    `citations.validate`, and the تركيب additionally through `validate_tarkib` — which is a
    strictly stronger check, not a synonym (it adds the composition rules: ≥2 grounded
    levels, ≥2 cited levels, no fact absent from them). Bypassing either for "obviously
    fine" prose is how a fluent-but-false sentence reaches the page.
    """
    health = getattr(generator, "health", None)
    if callable(health):
        try:
            if not health():
                return {}, [], _MSG_GEN_UNAVAILABLE
        except Exception:
            return {}, [], _MSG_GEN_UNAVAILABLE

    # ONE try/except around the whole body: the gate, the block routing and the generator
    # call are all "things that can throw on hostile input", and none of them may throw into
    # the request path.
    try:
        raw = generator(bundle)
        if not isinstance(raw, list):
            _warn_once(f"generator returned {type(raw).__name__}, expected a list of claims")
            return {}, [], _MSG_GEN_FAILED

        by_block: dict[str, list[dict]] = {b: [] for b in BLOCKS_ORDER}
        events: list[dict] = []
        for claim in raw:
            if not isinstance(claim, dict):
                # A string / int / list / nested JSON string — never `.get`-able.
                events.append(_transport_event(R_MALFORMED_CLAIM, claim))
                continue
            block = claim.get("block")
            if block not in by_block:
                # Addressed to no block of this page. Logged rather than silently discarded:
                # a prompt that starts emitting «sawti» would otherwise thin the page with
                # nothing anywhere saying so.
                events.append(_transport_event(R_UNKNOWN_BLOCK, block))
                continue
            by_block[block].append(claim)

        kept_by_block: dict[str, list[dict]] = {}
        for block in LEVEL_BLOCKS:
            kept, downgraded, dropped = citations.validate(by_block[block], bundle)
            kept_by_block[block] = kept
            events.extend(downgraded)
            events.extend(dropped)

        tarkib_kept, tarkib_down, tarkib_drop = citations.validate_tarkib(
            by_block[BLOCK_TARKIB], kept_by_block, bundle
        )
        kept_by_block[BLOCK_TARKIB] = tarkib_kept
        events.extend(tarkib_down)
        events.extend(tarkib_drop)

        # The model answered, and NOTHING it said survived. That is not the same state as
        # «generation disabled» or «model unreachable», and the page must not render it as
        # silence: a reader seeing only محقّق facts with no message cannot tell whether the
        # تعليل was switched off, failed, or was refused wholesale by the gate. The refusals
        # go to the coverage log, which no reader sees — so without this the single most
        # likely malformed-LLM shape (a JSON array of strings) degrades to a page that looks
        # exactly like a healthy deterministic one.
        if events and not any(kept_by_block.get(b) for b in BLOCKS_ORDER):
            return kept_by_block, events, _MSG_GEN_NOTHING_USABLE
        return kept_by_block, events, None
    except Exception as exc:
        _warn_once(f"generation failed: {type(exc).__name__}: {exc}")
        return {}, [], _MSG_GEN_FAILED


def _as_claims(gate_claims: list[dict]) -> list[dict]:
    """Gate output → response claims. `block` is dropped: it is the key, not a field."""
    return [
        _claim(c.get("text_ar", ""), c.get("badge", ""), c.get("cites") or [],
               c.get("sources") or [])
        for c in gate_claims
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 8. Assembly
# ─────────────────────────────────────────────────────────────────────────────
def _block_attribution(block_id: str) -> dict | None:
    """The framework disclaimer a block must be rendered WITH, or None.

    Only الحروف carries one today, and it is not optional decoration: the letters block is
    the single place where a corpus fact (صفات, from tajwīd) and a contested framework
    (دلالة, حسن عبّاس) sit in the same card. The disclaimer is what stops the first from
    lending its authority to the second for a reader who does not already know the
    difference — the same reason the two are separate claims with separate badges.

    Served rather than hardcoded in the page, for the reason the badge vocabulary is: it is
    the module that OWNS the dataset which knows what must be said about it, and a frontend
    copy can drift from a dataset upgrade without anything failing.
    """
    if block_id != BLOCK_HURUF:
        return None
    try:
        from linguistics.tahlil.huruf import source_meta
    except Exception:                                   # pragma: no cover - dataset absent
        return None
    meta = source_meta()
    # RENDERABLE keys only. `source_meta` also returns the dataset's own meta under
    # AUDIT_KEY, which is FRENCH — putting it on the page would break the Arabic-only rule
    # and trip the Latin-purity gate, voiding the block it was meant to qualify.
    return {"source": meta["source"], "disclaimer": meta["disclaimer"]}


def _block(block_id: str, claims: list[dict], message: str | None) -> dict:
    return {
        "id": block_id,
        "title_ar": BLOCK_TITLES[block_id],
        "available": bool(claims),
        "message": message,
        "claims": claims,
        "attribution": _block_attribution(block_id),
    }


def _unavailable_response(ref: str, surah: int, ayah: int, word: int,
                          reason: str, gen_enabled: bool, reviewed: bool) -> dict:
    """Every block absent, every block SAYING why. Never an empty page, never a 500."""
    return {
        "ref": ref,
        "surah": surah,
        "ayah": ayah,
        "word": word,
        "word_vocalized": "",
        "blocks_order": list(BLOCKS_ORDER),
        "blocks": {b: _block(b, [], reason) for b in BLOCKS_ORDER},
        "reviewed": reviewed,
        "generation_enabled": gen_enabled,
    }


def review_key(model_id: str | None = None, generator: object | None = None) -> tuple:
    """`(prompt_version, kb_version, letters_version, model_id, generation_enabled)`.

    **What a review attests is a RENDERING, not a ref.** Keyed on the ref alone, one
    expert's approval of a page that carried zero generated claims silently transferred to
    every later rendering of that word: switch generation on — or bump the prompt, the KB or
    the model — and brand-new, never-read prose came back `reviewed=True`, losing the
    «غير مُحقَّق» mention that design decision 3b makes **mandatory** on un-reviewed
    generated blocks. That is the one failure the flag exists to prevent.

    So the review row carries the analysis's own key **plus** `generation_enabled`: the
    five-tuple alone cannot tell a deterministic-only page from a prose page produced by the
    same model under the same versions, and those are two different renderings — one a human
    read, one nobody has. Any mismatch reads as un-reviewed, which is the safe direction:
    over-warning costs a badge, under-warning costs the guarantee.
    """
    resolved = model_id_of(generator) if model_id is None else model_id
    return (prompt_version(), kb_version(), letters_version(), resolved, generation_enabled())


def _reviewed(store, ref: str, key: tuple) -> bool:
    """The review flag — best-effort, because review must NEVER block rendering.

    A store that is absent (a bare test app) or that throws still yields a page; it yields
    an *un-reviewed* page, which is the safe direction: un-reviewed generated content is
    marked as such, so failing closed here can only ever over-warn.
    """
    if store is None:
        return False
    try:
        return bool(store.tahlil_reviewed(ref, *key))
    except Exception:
        return False


def analyze_word(surah: int, ayah: int, word: int, *, store=None, generator=None,
                 evidence_builder=None, model_id: str | None = None) -> dict:
    """Assemble the five-block Tahlil analysis for the word at `surah:ayah:word`.

    `store` is the app's SQLite `Store` (cache + review state); `generator` is the §7 prose
    generator — any callable `(bundle) -> [claim]`, optionally exposing `health()` and
    `model_id`. Both are injected rather than built here, so this module stays pure stdlib
    and testable with no database and no model.

    Raises `ValueError` on a non-positive/non-integer index and `KeyError` on a position
    the corpus does not hold — the router maps them to 400 / 404, mirroring `qlisan.py`.
    **Those two are the only exceptions that leave this function, and both are decided
    HERE, before any evidence is built**, so the router's mapping can never re-label an
    internal fault as a user error (see `_build_bundle`).

    Every other failure — no evidence layer, a builder that raised, a model that is off,
    unreachable, failing, or answering with malformed JSON — returns a normal response whose
    blocks state their reason: a reader must never meet a 500 because a model was down, and
    must never meet a silently empty block either.
    """
    try:
        surah, ayah, word = int(surah), int(ayah), int(word)
    except (TypeError, ValueError) as exc:
        raise ValueError("surah, ayah, word must be integers") from exc
    if surah < 1 or ayah < 1 or word < 1:
        raise ValueError("surah, ayah, word must be positive (1-based)")
    ref = f"{surah}:{ayah}:{word}"

    # Existence is checked HERE, against the same word index the fiche is read from, and
    # not left to the evidence layer: without it, a request for a position the corpus does
    # not hold would come back 200-with-a-reason on any machine where `linguistics/tahlil/evidence.py`
    # is missing — telling the reader that a nonexistent word has no evidence, which is a
    # different and false statement. This is an index lookup, not a second alignment path:
    # selection still goes through `GET /qlisan/verse/{surah}/{ayah}`.
    from linguistics.analysis.qlisan_data import qac_words

    if ref not in qac_words():
        raise KeyError(ref)

    gen_enabled = generation_enabled()
    mid = model_id_of(generator) if model_id is None else model_id
    reviewed = _reviewed(store, ref, review_key(model_id=mid))

    # ── the deterministic half is rebuilt on EVERY request, cache hit or not ──
    builder = evidence_builder
    if builder is None:
        try:
            builder = default_evidence_builder()
        except Exception as exc:
            _warn_once(f"linguistics.tahlil.evidence unavailable: {type(exc).__name__}: {exc}")
            return _unavailable_response(ref, surah, ayah, word, _MSG_NO_EVIDENCE,
                                         gen_enabled, reviewed)
    bundle, no_evidence = _build_bundle(builder, surah, ayah, word)
    if bundle is None:
        return _unavailable_response(ref, surah, ayah, word, no_evidence or _MSG_NO_EVIDENCE,
                                     gen_enabled, reviewed)

    # ── generation: from the cache when the MODEL's output is still valid ────
    # The cache holds the generated claims and the gate's log events — nothing else. See
    # `_cache_put` for why the deterministic half must never enter it.
    cached = _cache_get(store, ref, mid) if (gen_enabled and store is not None) else None
    if cached is not None:
        kept_by_block, events = cached[0], cached[1]
        # DERIVED, never stored: a replay of an answer whose every claim was refused must
        # carry the same notice the first render did, or the page goes silent on exactly the
        # state it most needs to announce. Deriving it from the cached content (no kept
        # claims + logged events) keeps it impossible for the stored payload and the message
        # to disagree — a stored copy could drift; a derived one cannot.
        gen_message = (_MSG_GEN_NOTHING_USABLE
                       if events and not any(kept_by_block.get(b) for b in BLOCKS_ORDER)
                       else None)
        # The gate ran ONCE, when the prose was generated; a replay is not a second verdict,
        # so it is not written to the coverage log again. The events still travel with the
        # payload because the block messages below are built from them: a cached block whose
        # claims were all dropped must still say why.
    else:
        if not gen_enabled:
            kept_by_block, events, gen_message = {}, [], _MSG_GEN_DISABLED
        elif generator is None:
            kept_by_block, events, gen_message = {}, [], _MSG_GEN_UNAVAILABLE
        else:
            kept_by_block, events, gen_message = _generate(generator, bundle)

        if events:
            coverage.record(events, ref=ref)
        if gen_enabled and gen_message:
            # Only a request that WANTED prose and did not get it is logged. Logging the
            # env-disabled case would flood the log with a fact the operator already knows.
            coverage.record([{
                "block": "", "reason": R_GENERATION_UNAVAILABLE, "outcome": "drop",
                "badge_before": "", "badge_after": "", "text": gen_message, "cites": [],
            }], ref=ref)
        if _should_cache(gen_enabled, gen_message, store):
            _cache_put(store, ref, mid, kept_by_block, events)

    # Reasons the evidence layer stated, routed to the block a reader will look in.
    notes_by_block = _notes_by_block(bundle)
    # Reasons the GATE stated. Only drops: a downgraded claim renders, so it never explains
    # an absence.
    drops = [e for e in events if e.get("outcome") == citations.OUTCOME_DROP]

    # ── blocks, in the one fixed order ────────────────────────────────────
    blocks: dict[str, dict] = {}
    for block_id in BLOCKS_ORDER:
        if block_id == BLOCK_TARKIB:
            # The تركيب has no deterministic half at all: a thesis composing four levels is
            # exactly the free prose §7 turns on. It says so ONLY when generation is off —
            # with generation on, «التركيب لا يُنتَج إلا بالتوليد» is a false reason, and the
            # true one (the gate refused the thesis, or none was written) is stated below.
            deterministic = []
            if not gen_enabled:
                det_reason = _MSG_TARKIB_NEEDS_GEN
            elif not tarkib_enabled():
                det_reason = _MSG_TARKIB_DISABLED
            else:
                det_reason = None
        else:
            deterministic, det_reason = _DETERMINISTIC[block_id](bundle)
        generated = _as_claims(kept_by_block.get(block_id) or [])
        claims = deterministic + generated

        # Each absence is stated on its own line, and they are independent: what the
        # deterministic layer could not supply, what the GATE refused, what the model layer
        # could not do, and what the evidence layer had to leave out. Collapsing them would
        # leave the reader unable to tell a rootless word from a dead model from a claim
        # that cited nothing.
        parts: list[str] = []
        if not deterministic and det_reason:
            parts.append(det_reason)
        if not generated:
            # Design decision 2: «a block whose claims were all dropped renders with its
            # reason». Without this call the gate's verdicts never reached the page at all —
            # the block simply went quiet, which looks identical to a model that had nothing
            # to say.
            gate_reason = citations.block_message(block_id, drops)
            if gate_reason:
                parts.append(gate_reason)
            if gen_message:
                parts.append(gen_message)
        parts.extend(notes_by_block.get(block_id, ()))
        if not claims and not parts:
            # Rule 2: never an empty card with no reason.
            parts.append(_MSG_TARKIB_NONE if block_id == BLOCK_TARKIB else _MSG_NO_EVIDENCE)
        blocks[block_id] = _block(block_id, claims, " ".join(parts) or None)

    return {
        "ref": ref,
        "surah": surah,
        "ayah": ayah,
        "word": word,
        "word_vocalized": bundle.get("surface_vocalized", ""),
        "blocks_order": list(BLOCKS_ORDER),
        "blocks": blocks,
        "reviewed": reviewed,
        "generation_enabled": gen_enabled,
    }


def _notes_by_block(bundle: dict) -> dict[str, list[str]]:
    """`{block_id: [message_ar, …]}` — the evidence layer's stated reasons, routed.

    A note the renderer cannot place is **reported**, never silently swallowed: swallowing
    is the failure this function exists to fix, and a new note code appearing in
    `evidence.py` without a home here would otherwise re-create it in miniature. The drift
    test (`set(NOTE_BLOCK) == evidence.NOTE_CODES`) is the real guard; this is the runtime
    backstop.
    """
    out: dict[str, list[str]] = {}
    for note in bundle.get("notes") or []:
        if not isinstance(note, dict):
            continue
        code, message = note.get("code"), (note.get("message_ar") or "").strip()
        block = NOTE_BLOCK.get(code)
        if block is None:
            _warn_once(f"bundle note {code!r} has no block in NOTE_BLOCK; it is not rendered")
            continue
        if message and message not in out.setdefault(block, []):
            out[block].append(message)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 9. Cache
# ─────────────────────────────────────────────────────────────────────────────
def _should_cache(gen_enabled: bool, gen_message: str | None, store) -> bool:
    """Cache ONLY a successfully generated analysis.

    Two deliberate exclusions:

      * **generation disabled** — nothing was generated, so there is nothing to reuse; the
        page is a pure function of the corpus and is re-assembled per request anyway.
      * **generation failed** — a transient outage must not be frozen into the table and
        replayed as though it were the analysis.

    One deliberate INCLUSION, and the distinction is the point: a well-formed answer whose
    every claim the gate refused (`_MSG_GEN_NOTHING_USABLE`) is **not** a failure. The model
    was reachable and answered; the content simply could not be anchored, which is a
    property of the prompt and the evidence, not of the transport — so re-calling would
    almost certainly reproduce it. It is cached WITH its message, so the page keeps saying
    why the layer is empty on every replay. Treating it as a failure instead would both
    burn a model call per view and, worse, blur a prompt regression into what reads like an
    outage.
    """
    if not (gen_enabled and store is not None):
        return False
    return gen_message in (None, _MSG_GEN_NOTHING_USABLE)


def _cache_get(store, ref: str, model_id: str) -> tuple[dict, list[dict]] | None:
    """`(claims_by_block, log_events)` from the cache, or None. Never raises.

    A payload that does not carry the current shape (an entry written before this layout,
    or anything corrupt) is a **miss**, not an error: the request then regenerates, which
    is always safe, where trusting an unknown shape is not.
    """
    try:
        payload = store.get_tahlil(ref, prompt_version(), kb_version(), letters_version(),
                                   model_id)
    except Exception:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("claims"), dict):
        return None
    events = payload.get("events")
    return payload["claims"], events if isinstance(events, list) else []


def _cache_put(store, ref: str, model_id: str, claims_by_block: dict, events: list) -> None:
    """Store the MODEL's output only — never the assembled response.

    The key is `(ref, prompt_version, kb_version, letters_version, model_id)`. Read what is
    *not* in that tuple: the corpus, `linguistics/analysis/mizan.py`, `linguistics/analysis/qac_labels.py`,
    `linguistics/tahlil/evidence.py`. Caching the whole response therefore froze every **محقّق** fact
    under a key that cannot notice when the fact changes — bump the mīzān projection (what
    `harden-mizan-irregular-roots` does to 258 of 405 sampled words) and the page keeps
    serving the old wazn, badged verified, with nothing in the system able to detect the
    contradiction. A verified claim has to be a claim about the CURRENT corpus, so the
    deterministic half is never stored and never replayed; only the prose the model wrote —
    which the key *does* cover — is.
    """
    try:
        store.put_tahlil(ref, prompt_version(), kb_version(), letters_version(), model_id,
                         {"claims": claims_by_block, "events": events})
    except Exception:
        pass


if __name__ == "__main__":  # smoke test — mirrors mizan.py / form_kb.py
    print(f"blocks : {' → '.join(BLOCK_TITLES[b] for b in BLOCKS_ORDER)}")
    print(f"gen    : {generation_enabled()}  ·  prompt {prompt_version()}")
    try:
        print(f"versions: kb={kb_version()}  letters={letters_version()}")
    except Exception as exc:  # pragma: no cover
        print(f"versions: unavailable ({exc})")
    out = analyze_word(23, 61, 2)
    for bid in out["blocks_order"]:
        blk = out["blocks"][bid]
        print(f"\n[{blk['title_ar']}] available={blk['available']} · {blk['message'] or ''}")
        for c in blk["claims"]:
            print(f"  ({c['badge']}) {c['text_ar']}  ←  {', '.join(c['cites'])}")


# ─────────────────────────────────────────────────────────────────────────────
# 10. The verse layer (tasks.md §11)  ——  QUARANTINED
# ─────────────────────────────────────────────────────────────────────────────
# Everything from here to the end of this module is OFF the served surface.
# `POST /tahlil/verse` was unmounted in the repo restructure because no page
# called it: the Tahlil page uses /tahlil/word and /tahlil/review only.
#
# It is quarantined, not deleted, for the same reason madar/ is (see
# linguistics/madar/__init__.py, which states the convention): this is a
# complete, tested feature that was deliberately left unwired, not code that
# rotted. Its 201 lines of tests — §11 of tests/test_tahlil_service.py — still
# run and still guard it, so it cannot silently decay while dormant.
#
# WHAT IS DORMANT HERE: `analyze_verse` and everything it alone reaches —
# `verse_evidence`, `_verse_cite_id`, `_rooted_word_ids`, `_verse_claims`,
# VERSE_WORD_CAP, BLOCK_VERSE, VERSE_TITLE_AR and the _MSG_VERSE_* strings.
# The slice extends beyond this module: `prompts.build_verse_message` /
# `verse_lines` / `VERSE_TASK` / `VERSE_PROMPT_VERSION`,
# `generator.TahlilGenerator.verse()`, and `citations.validate_verse` /
# `R_VERSE_UNANCHORED` exist to serve this entry point and nothing else. Each
# keeps its own tests in its own suite.
#
# HOW TO REBRANCH IT: re-add the route to api/routers/tahlil.py —
#
#     @router.post("/tahlil/verse", response_model=TahlilVerseResponse)
#     def tahlil_verse(req: TahlilVerseRequest, request: Request) -> ...:
#         return analyze_verse(req.surah, req.ayah, store=..., generator=...)
#
# and restore TahlilVerseRequest / TahlilVerseResponse in api/models/tahlil.py.
# Both were removed with the route; git has them at 46d06e9^. The service below
# is unchanged and needs nothing done to it.
# ─────────────────────────────────────────────────────────────────────────────
# Mean verse length is 12.4 words and the longest is 128 (2:282). Analysing every word of
# 2:282 would be 128 word analyses plus a synthesis, which is not a latency problem so much
# as an honesty one: a synthesis over the first N words of a verse must not be presented as
# a synthesis over the verse. So the cap is explicit, STATED in the payload, and logged.
VERSE_WORD_CAP = 24

BLOCK_VERSE = "verse"
VERSE_TITLE_AR = "تركيب الآية"

_MSG_VERSE_NO_WORDS = "لا توجد في هذه الآية كلمةٌ ذاتُ جذرٍ يمكن تحليلها."
_MSG_VERSE_NO_CLAIMS = "لم تُنتِج كلماتُ الآية دعاوى ناجية، فلا خلاصةَ تُبنى عليها."
_MSG_VERSE_GEN_OFF = "التوليد معطّل؛ وخلاصةُ الآية لا تُنتَج إلا بالتوليد."
_MSG_VERSE_CAPPED = (
    "بُنيت هذه الخلاصة على أوّل {shown} كلمةً ذاتَ جذرٍ من {total}؛ "
    "وما بعدها لم يدخل في التحليل."
)


def _verse_cite_id(claim: dict, ref: str, index: int) -> str:
    """A verse-level evidence id for one surviving WORD claim: `{kind}:v{i}@{ref}`.

    The kind is chosen from the word claim's **BADGE**, not from its citation kinds, and the
    difference is not academic. The letters block emits two claims per letter that cite the
    SAME id: صفات, a tajwīd fact badged محقّق, and دلالة, a contested reading badged تأويلي.
    Keying on the cite kind would call both «letter» — an interpretive kind — so every verse
    synthesis resting on a phonetic fact would come out تأويلي. That errs on the cautious
    side, which is why it is not a correctness bug; it is a MEASUREMENT bug, and design
    decision 12 settled that one already: §12 judges the prompt by the badge distribution,
    so filing facts under «contested» corrupts the measurement at its source.

    So the badge decides, and the kind is picked to REPRODUCE it through `validate`:
    تأويلي → an interpretive kind, anything else → a corpus kind. Within each direction the
    kind the claim actually cited is preferred, so the id names a real source; the constants
    are only a fallback for a claim whose cites carry no usable kind.

    The `@{ref}` suffix is what `citations.validate_verse` anchors on, so an id minted here
    says both «evidence of kind K» and «from word REF».
    """
    kinds = [k for k in (citations.kind_of(c) for c in claim.get("cites") or []) if k]
    if claim.get("badge") == citations.BADGE_INTERPRETIVE:
        pool = [k for k in kinds if k in citations.INTERPRETIVE_KINDS]
        kind = (pool or [citations.KIND_LETTER])[0]
    else:
        pool = [k for k in kinds if k not in citations.INTERPRETIVE_KINDS]
        kind = (pool or [citations.KIND_QAC])[0]
    return f"{kind}:v{index}@{ref}"


def verse_evidence(word_analyses: list[dict]) -> tuple[dict, set[str]]:
    """`({cite_id: item}, {word_ref})` — the ONLY thing the verse synthesis may cite.

    Built from the word analyses' SURVIVING claims, never from the verse text: the founding
    constraint is that the verse's meaning is composed from what we could anchor about its
    words, so handing the model the verse itself would let it read the آية directly and
    then decorate the reading with citations.
    """
    items: dict[str, dict] = {}
    refs: set[str] = set()
    index = 0
    for analysis in word_analyses:
        ref = analysis.get("ref", "")
        for block_id in analysis.get("blocks_order") or ():
            block = (analysis.get("blocks") or {}).get(block_id) or {}
            for claim in block.get("claims") or ():
                index += 1
                cite_id = _verse_cite_id(claim, ref, index)
                items[cite_id] = {
                    "kind": citations.kind_of(cite_id),
                    "ref": ref,
                    "block": block_id,
                    "text_ar": claim.get("text_ar", ""),
                    "badge": claim.get("badge", ""),
                    "word_vocalized": analysis.get("word_vocalized", ""),
                }
                refs.add(ref)
    return items, refs


def _rooted_word_ids(surah: int, ayah: int) -> list[int]:
    """The verse's word ids that carry a root, in order.

    Rooted only, and the payload says so (tasks.md 11.3): a particle or a pronoun has no
    root, so الحروف has nothing to decompose and دلالي nothing to anchor, and counting them
    would let the synthesis report a coverage it never had. Read from `qac_words` — the same
    map the word pipeline routes on — rather than re-deriving, so «rooted» means here
    exactly what it means one layer down.
    """
    from linguistics.analysis.qlisan_data import qac_words
    from linguistics.analysis.word_analysis import verse_tokens

    words = qac_words()
    ids: list[int] = []
    for token in (verse_tokens(surah, ayah).get("tokens") or ()):
        word = token.get("word")
        record = words.get(f"{surah}:{ayah}:{word}") or {}
        if record.get("root"):
            ids.append(int(word))
    return ids


def analyze_verse(surah: int, ayah: int, *, store=None, generator=None,
                  model_id: str | None = None) -> dict:
    """One synthesis over the verse's analysed WORDS (tasks.md §11).

    Runs the word pipeline over the verse's rooted words — reusing `analyze_word`, so every
    cache hit is a cache hit — then makes ONE generation call whose evidence is the words'
    surviving claims. The verse text is never a source of meaning, and never reaches the
    model: `prompts.build_verse_message` is built from claims alone.

    Returns the same shape as `analyze_word` plus `words`, `word_total` and `capped`, so a
    client renders it with the machinery it already has. There is exactly ONE block, and it
    is not one of the five: `verse` / «تركيب الآية».

    Raises `ValueError` / `KeyError` on a bad or absent reference, decided before any work,
    exactly as `analyze_word` does.
    """
    from linguistics.analysis.word_analysis import verse_tokens

    verse_tokens(surah, ayah)                    # validates: ValueError / KeyError, early
    surah, ayah = int(surah), int(ayah)
    ref = f"{surah}:{ayah}"

    rooted = _rooted_word_ids(surah, ayah)
    total = len(rooted)
    capped = total > VERSE_WORD_CAP
    shown = rooted[:VERSE_WORD_CAP]
    events: list[dict] = []
    capped_note = ""
    if capped:
        capped_note = _MSG_VERSE_CAPPED.format(shown=len(shown), total=total)
        events.append({"block": BLOCK_VERSE, "reason": R_WORD_CAP,
                       "outcome": citations.OUTCOME_DROP, "badge_before": "",
                       "badge_after": "", "text": f"{ref}: {len(shown)}/{total}",
                       "cites": []})

    analyses = [analyze_word(surah, ayah, w, store=store, generator=generator,
                             model_id=model_id) for w in shown]
    items, refs = verse_evidence(analyses)

    gen_enabled = generation_enabled()
    if not shown:
        message, claims = _MSG_VERSE_NO_WORDS, []
    elif not items:
        message, claims = _MSG_VERSE_NO_CLAIMS, []
    elif not gen_enabled or generator is None:
        message, claims = _MSG_VERSE_GEN_OFF, []
    else:
        claims, gen_events = _verse_claims(items, refs, surah, ayah, capped_note, generator)
        events.extend(gen_events)
        message = None if claims else citations.block_message(BLOCK_VERSE, events)

    if capped_note:
        message = f"{capped_note} {message}" if message else capped_note
    if events:
        coverage.record(events, ref=ref)

    block = {
        "id": BLOCK_VERSE,
        "title_ar": VERSE_TITLE_AR,
        "available": bool(claims),
        "message": message,
        "claims": claims,
        "attribution": None,
    }
    return {
        "ref": ref,
        "surah": surah,
        "ayah": ayah,
        "word": 0,
        "word_vocalized": "",
        "blocks_order": [BLOCK_VERSE],
        "blocks": {BLOCK_VERSE: block},
        "reviewed": False,
        "generation_enabled": gen_enabled,
        "words": [a.get("ref", "") for a in analyses],
        "word_total": total,
        "capped": capped,
    }


def _verse_claims(items: dict, refs: set[str], surah: int, ayah: int,
                  capped_note: str, generator) -> tuple[list[dict], list[dict]]:
    """The one generation call, gated. Returns `(render_ready_claims, log_events)`."""
    from linguistics.tahlil import prompts

    message, handles = prompts.build_verse_message(
        items, surah=surah, ayah=ayah, capped_note=capped_note)
    if not message:
        return [], []
    lines = prompts.verse_lines(items)
    events: list[dict] = []
    raw = (generator.verse(message, handles, lines, events)
           if hasattr(generator, "verse") else [])
    claims = [c for c in raw if isinstance(c, dict)]
    events.extend(_transport_event(R_MALFORMED_CLAIM, c, BLOCK_VERSE)
                  for c in raw if not isinstance(c, dict))
    for claim in claims:
        claim["block"] = BLOCK_VERSE
    kept, downgraded, dropped = citations.validate_verse(claims, refs, {"items": items})
    events.extend(downgraded)
    events.extend(dropped)
    return _as_claims(kept), events
