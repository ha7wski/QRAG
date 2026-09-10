"""
evidence.py — the evidence bundle: **the only thing the generator will ever see**.

Design decision 1 in one sentence: the model never supplies facts, only prose over a bundle
assembled deterministically from disk. It is never handed the free corpus, never handed the
verse "to interpret", never asked what a verse means. Everything it may say must already be
in here, carrying an id, or the gate in `citations.py` drops the sentence.

That makes this module the *vocabulary* of the whole page. Five things in it are
load-bearing, and each one has a measured failure behind it:

**1. The analysed surface comes from the vocalized (chakl) corpus, never from QAC's
`uthmani` field.** `qac_words()["23:61:2"]["uthmani"]` is «يُسرعُون» — the alif of the
مفاعلة is simply **not there** — while the chakl text reads «يُسَارِعُونَ». Every claim the
الحروف/صوتي layer makes is a claim about letters, so reading the QAC field would make the
pinned exemplar analyse a word the Quran does not contain, and the block would look
complete while doing it. The surface is therefore read through the **existing** token
alignment (`word_index.json`'s `chakl_char_start/end` into `chakl_by_ref()`), exactly as
`analysis/word_analysis.py::verse_tokens` does — one alignment path, not two.

**2. Ids are COPIED from the module that owns the evidence, never re-derived.**
`huruf.py` mints `letter:…` (with a page **range**, `letter:ء@p94-95`); `form_kb.py` mints
`sigha:…`/`contrast:…` with the **owning file's** version, not the combined `kb_version()`.
This module copies those verbatim and mints only the three it owns: `nazir:<s>:<a>:<w>`,
`maqayis:<root>`, `qac:<field>@<ref>`. An id re-typed here would drift from its owner
silently — the claim would still render, still look cited, and resolve to nothing. The one
exception tasks.md 4.2 grants is a *narrowing* — never a re-derivation: a `contrast:` id is
**split** on its `@`, so the source باب and the version token stay the owner's bytes and only
the target is added (§3).

**3. Contrast attestation is computed at `(lemma, POS/باب)` granularity, never at the
root's — and ONE CANDIDATE IS ONE CITABLE ITEM.** This is the correction that makes or
breaks the pinned exemplar. Root `سرع` *does* contain أَسْرَع (6:62:11) — but as an **اسم
تفضيل**, POS `N`, not as a verb of باب أفعَلَ. A root-level check sees the string, calls the
أفعَلَ contrast *attested*, and turns the exemplar's strongest sentence — «ولم ترد صيغة
أفعَلَ **فعلاً** من هذا الجذر» — into a falsehood. So a candidate is attested **iff the
corpus holds a word of that POS and that باب/verb-form under this root**, and the lemmas
that attest it are reported by name.

`form_kb` mints one id per **source** باب (`contrast:فَعَلَ@0.1.0`) while a باب is opposed to
several أبواب whose verdicts *differ*: re-derived over the 19 356 corpus verbs, 876 have
every candidate attested, **6 992 a mixed set**, 11 474 none attested, 14 no candidate at
all. A single boolean on that id cannot be true of all of them, so this module takes the
narrowing exception tasks.md 4.2 grants — `contrast:<source>><target>@<version>`, the
owner's version token kept and the owner's id recorded as `parent_cite_id` — and mints
**one item per candidate**. The aggregate it replaces was not merely coarse, it was false
on real words: on root عبد (1:5:2) the aggregated item reported `attested=False` with an
absence sentence naming only أَفْعَلَ, so a claim asserting that **فَعَّلَ** does not occur
— it does, at 26:22:6 — cited that id and passed the gate. An id must name exactly what its
boolean is about.

**4. `qac:` ids are minted for SYNTACTIC facts of this verse only — and the inflection
marker is NOT one of them.** The gate treats every `qac:` cite as a *corpus disambiguator*
— the thing that turns an unanchored multi-sense selection from تأويلي back into مُولَّد
(`citations.CORPUS_DISAMBIGUATORS`). Minting `qac:bab@…` or `qac:wazn@…` would hand the
generator a free disambiguator that is **circular by construction**: the باب is precisely
what *routed* the KB row, so it cannot discriminate between that row's senses.

`marker` was minted here and no longer is, because both objections apply to it too. A
case/mood inflection («مرفوع وعلامته ثبوت النون») says nothing about *which sense of a form*
holds —
it is the same string on every مضارع مرفوع of the أفعال الخمسة, whatever it means — and for
a verb it is read off the very morphology record that routed the KB row, so citing it
re-badges an unanchored selection with zero semantic content. `relation` and `head_ref`
stay: they are facts of **this verse's syntax** (what the word is doing, and to what), which
the spec names as an admissible disambiguator.

Dropping it costs no coverage, measured over the whole corpus: 76 639 of 77 429 words
(98.98 %) carry a `qac:` item, and that figure is **identical** before and after — the
marker is the sole `qac:` item for exactly **0** words, because a word with a marker always
has an iʿrāب relation too. What it costs is a semantically empty anchor.

The marker still **reaches the page**, as a deterministic fact rather than a citation:
`bundle["nahwi_facts"]["marker_ar"]` carries it (verb path *and* nominal path) beside the
fiche's own `nahwi.marker_ar`, and `display_strings` sweeps it. Nothing rendered was
removed; only the citation was.

`_QAC_FIELDS` is the closed set, and minting outside it **raises** — `_qac_items` asserts
that before the loop, so the guarantee this docstring states is a line of code and not a
sentence.

**5. Absence is stated at the candidate's own granularity, and the gate matches it
verbatim.** `absence_scope_ar` names the missing باب **and** its POS («ولم ترد صيغة
أَفْعَلَ فعلاً من هذا الجذر»), because the bare «لم ترد أفعَلَ» would be false in the
presence of أَسْرَع. The gate requires that exact sentence inside an unattested contrast
claim (spec: exact containment, not a marker denylist), which is why an unattested item may
never carry an EMPTY scope string: with one, no contrast claim can ever be admitted and the
whole layer disappears silently — and under any looser reading of «contains», the empty
string is found everywhere and every claim is admitted. `bundle_for_claims` refuses such an
item at the seam, in both directions (an attested item may carry no scope at all).

**Naẓāʾir ranking.** Selection is **deterministic corpus order**, lemma-scoped first with a
same-root fallback tagged by lemma — reused from the fiche (`analyze_word`), never
re-derived. 41 204 rooted words have ≥10 siblings and the bundle carries `NAZAIR_CAP`, so a
better *selection* is worth having; but `retrieval/similar_verses.py` is an ML path and this
package is pure stdlib by contract. The reranker is therefore a **documented seam**: pass
`rank=` and the service injects it, the same shape as `HybridSearch`'s `root_ranker`. The
seam is validated — an injected ranker may reorder and drop, never invent, so it cannot
smuggle a ref into the citation vocabulary.

**Maqāyīs is reused, not re-parsed** (`madar/maqayis_store.py`). Honest coverage, measured
two ways because they differ: a *plain* CSV lookup — what the change's baseline measured and
what a re-parse would have reproduced — reaches 1 142/1 642 roots (37 844 words, 75.7 %),
while the store's geminate bridge (`اب` ↔ `ابب`) recovers 141 roots / 4 106 words more, for
1 283/1 642 (41 950 words, 84.0 %). Reuse is not just less code here; it is more evidence.

Pure stdlib + on-disk artifacts: no LLM, no network, no fastapi/pydantic.
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linguistics.analysis import qac_labels
from linguistics.analysis.qlisan_data import qac_words, root_graph, word_index
from linguistics.analysis.word_analysis import analyze_word
from quran_data.corpus import chakl_by_ref
from linguistics.madar.maqayis_store import MaqayisStore
from linguistics.tahlil import form_kb, huruf
from linguistics.tahlil.citations import (
    KIND_CONTRAST,
    KIND_LETTER,
    KIND_MAQAYIS,
    KIND_NAZIR,
    KIND_QAC,
    KIND_SIGHA,
    KINDS,
    kind_of,
)

# How many naẓāʾir enter the bundle. Eight is not arbitrary: it is the size of the pinned
# word's same-lemma sibling set (23:61:2 has exactly 8, and the spec's «a same-lemma naẓīr
# among the 8» names them), and it is what a prompt can carry with each sibling's full
# vocalized verse attached without the evidence drowning the contract.
NAZAIR_CAP = 8

# How many attesting refs a contrast candidate carries. A candidate needs *witnesses*, not
# a concordance; the full count travels beside them as `attested_count` so a truncated list
# can never read as the whole population.
ATTEST_REFS_CAP = 8

# ─────────────────────────────────────────────────────────────────────────────
# The `qac:` vocabulary — CLOSED, and closed for a reason (docstring §4).
# ─────────────────────────────────────────────────────────────────────────────
# Every id minted here is read by the gate as a corpus disambiguator, so this set may hold
# only facts of *this verse's syntax*: the word's iʿrāب position and what it attaches to.
# Morphological identity (root/lemma/pos), the KB routing keys (bab/wazn/aspect/
# derived-noun) and the inflection MARKER are deliberately absent — see the docstring §4.
# `QAC_MARKER` survives as the field NAME (the service reads the same vocabulary and its
# `nahwi_facts` key is derived from it); it is simply not in the citable set.
QAC_RELATION, QAC_HEAD, QAC_MARKER = "relation", "head_ref", "marker"
_QAC_FIELDS: tuple[str, ...] = (QAC_RELATION, QAC_HEAD)

# ─────────────────────────────────────────────────────────────────────────────
# Bundle notes — the CLOSED set of stated reasons for anything absent.
# ─────────────────────────────────────────────────────────────────────────────
# «Degrade honestly at every level: no evidence → block absent with a stated reason, never
# filled» (design.md, Goals). A note is machine-triageable (`code`) *and* renderable
# (`message_ar`); the closed set is asserted by the corpus sweep, same contract as the
# gate's closed reason set, so a new silent failure mode cannot appear without a name.
NOTE_ROOTLESS = "rootless-word"
NOTE_NO_ASL = "no-lexical-anchor"
NOTE_NO_NAZIR = "no-nazir"
NOTE_NAZAIR_CROSS_LEMMA = "nazair-cross-lemma"
NOTE_NAZAIR_CAPPED = "nazair-capped"
NOTE_NO_SIGHA_ROW = "no-form-row"
NOTE_NO_CONTRAST = "no-contrast-candidates"
NOTE_NO_SYNTAX = "no-syntax-record"
NOTE_SURFACE_UNALIGNED = "surface-unaligned"

NOTE_CODES: frozenset[str] = frozenset({
    NOTE_ROOTLESS, NOTE_NO_ASL, NOTE_NO_NAZIR, NOTE_NAZAIR_CROSS_LEMMA,
    NOTE_NAZAIR_CAPPED, NOTE_NO_SIGHA_ROW, NOTE_NO_CONTRAST, NOTE_NO_SYNTAX,
    NOTE_SURFACE_UNALIGNED,
})

_NOTE_MESSAGES_AR: dict[str, str] = {
    NOTE_ROOTLESS: "لا جذر لهذه الكلمة في المدوّنة، فلا يُبنى لها مستوى الحروف ولا أصلٌ معجميّ.",
    NOTE_NO_ASL: "لم يرد لهذا الجذر أصلٌ في «مقاييس اللغة»، فالمعنى المحوريّ بلا مِرْساة معجميّة.",
    NOTE_NO_NAZIR: "لم يرد لهذه الكلمة نظير في المصحف؛ لم يأتِ هذا الجذر إلّا هنا.",
    NOTE_NAZAIR_CROSS_LEMMA: "النظائر دون ثلاثة من اللفظ نفسه، فأُكمِلت من الجذر نفسه بألفاظ أخرى، وكلٌّ منها موسوم بلفظه.",
    NOTE_NAZAIR_CAPPED: "النظائر أكثر من الحدّ المعروض، فعُرِض أوّلها على ترتيب المصحف.",
    NOTE_NO_SIGHA_ROW: "لم يطابق هذه الصيغة صفٌّ في قاعدة دلالة الصيغة.",
    NOTE_NO_CONTRAST: "لا مقابلة بابيّة لهذه الصيغة في هذه النسخة من جدول المقابلة.",
    NOTE_NO_SYNTAX: "لا يوجد تحليل نحوي محفوظ لهذه الكلمة في الشجرة الإعرابية.",
    NOTE_SURFACE_UNALIGNED: "تعذّرت محاذاة الكلمة بالنصّ المشكول، فالصورة المعروضة تقريبيّة.",
}

# POS → the Arabic word that names the *kind* of the absent form. The whole point of §4.7:
# «لم ترد أفعَلَ» is FALSE for root سرع (أَسْرَع is there, as an اسم تفضيل);
# «لم ترد أفعَلَ **فعلاً**» is true. Closed vocabulary — an unmapped POS raises rather than
# producing a scope word by guesswork, the same contract as
# `qac_labels.translate_features` raising on an unmapped code.
#
# The nominal entries are kept although `attestation` currently refuses a nominal target
# (see its docstring): they are the vocabulary the deferred nominal contrast table will
# need, and keeping them is what lets an unknown POS (`PN`) and a *deferred* POS (`N`) fail
# with two different, accurate messages instead of one misleading one.
_POS_SCOPE_AR: dict[str, str] = {
    "V": "فعلاً",
    "N": "اسماً",
    "ADJ": "صفةً",
}

# The POS values `attestation` can answer for today. A verb is identified in the corpus by
# a fact QAC records — `verb_form` — so «is there a verb of this باب under this root?» is a
# lookup. A nominal صيغة is identified by its WAZN, which the corpus does not record: it is
# a projection (`analysis/mizan.py`, `verified=False` on hollow/geminate/irregular roots,
# and an open hardening change against it), so crediting or denying a nominal candidate
# would rest on a guess. Refuse instead — see `attestation`.
_ATTESTABLE_POS: frozenset[str] = frozenset({"V"})

# A ranker reorders (and may drop) naẓīr candidates; it can never add one. See the
# docstring: the seam exists so `retrieval/similar_verses.py` can select without this
# package importing an ML path.
NazairRanker = Callable[[str, list[dict]], list[dict]]


@functools.lru_cache(maxsize=1)
def _maqayis() -> MaqayisStore:
    """The shared Maqāyīs reader. Reused, never re-parsed (task 4.5)."""
    return MaqayisStore()


def _note(code: str, **extra) -> dict:
    """One stated reason. Raises on an unknown code — the closed set is the contract."""
    if code not in NOTE_CODES:
        raise ValueError(f"unknown bundle note code {code!r}; the note set is closed")
    return {"code": code, "message_ar": _NOTE_MESSAGES_AR[code], **extra}


# ─────────────────────────────────────────────────────────────────────────────
# 1. The vocalized surface — from chakl, through the existing alignment
# ─────────────────────────────────────────────────────────────────────────────


def surface_vocalized(surah: int, ayah: int, word: int) -> tuple[str, bool]:
    """`(vocalized surface, aligned)` for one word, read from the chakl corpus.

    Returns the slice of the **fully vocalized verse** that the QAC token occupies,
    using `word_index.json`'s `chakl_char_start/end` — the alignment
    `analysis/word_analysis.py::verse_tokens` already publishes. This is a *read* of that
    alignment, not a second one: no boundary is recomputed here.

    **Never** `qac_words()[ref]["uthmani"]`. That field is not reliably vocalized and, for
    the pinned word, is not even the right consonantal skeleton: «يُسرعُون» has lost the
    alif of the مفاعلة that «يُسَارِعُونَ» carries. A letters analysis run over it would be
    an analysis of a word the Quran does not contain — and would look complete.

    The second element is the alignment flag; `False` means the span is a best-effort
    fallback and the caller must say so (`NOTE_SURFACE_UNALIGNED`) rather than present a
    guess as the text. Measured: 0 of the corpus's 77 429 words are unaligned today, which
    is exactly why the flag must be carried — an alignment regression would otherwise be
    invisible.
    """
    rec = word_index().get(f"{surah}:{ayah}:{word}")
    entry = chakl_by_ref().get((surah, ayah))
    if not rec or not entry:
        return "", False
    text = entry.get("text", "")
    start, end = rec.get("chakl_char_start", 0), rec.get("chakl_char_end", 0)
    if end <= start:
        return "", False
    return text[start:end], bool(rec.get("aligned", False))


def _verse_text(surah: int, ayah: int) -> tuple[str, str]:
    """`(vocalized verse text, surah name)` — the naẓīr's context, in Arabic."""
    entry = chakl_by_ref().get((surah, ayah)) or {}
    return entry.get("text", ""), entry.get("surah_name", "")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Contrast attestation — at (lemma, POS/باب) granularity, never the root's
# ─────────────────────────────────────────────────────────────────────────────


def attestation(root: str | None, target: dict) -> dict:
    """Does the corpus hold a word of **this** POS and **this** باب under `root`?

    Returns
    ``{attested, attested_refs, attested_lemmas, attested_count, absence_scope_ar}``.

    The occurrences come from `root_graph()` — exhaustive by construction, which is why
    design decision 6 refuses a vector index here — and are then filtered on **two** axes
    that a root-level check collapses:

    * **POS** — a noun, an elative or a participle of the root never attests a *verb* of a
      given باب, and a verb never attests a nominal صيغة;
    * **verb form** — the باب itself. QAC leaves form I unmarked, so an absent `verb_form`
      *is* form I, not «unknown»; both sides fold `""` → `None` so the two spellings cannot
      miss each other.

    The lemmas that attest are reported by name, because the granularity the design fixes
    is `(lemma, POS/باب)`: naming them is what lets a reader check the verdict instead of
    trusting it.

    On root `سرع` with the أفعَلَ **verb** target this returns `attested=False`, although
    أَسْرَع sits at 6:62:11 — it is `pos='N'`, an اسم تفضيل. That single distinction is the
    difference between the exemplar's best sentence and a false one.

    Raises `ValueError` twice, both refusals rather than guesses:

    * **an unmapped target POS** (no entry in `_POS_SCOPE_AR`): without a scope word the
      absence clause degrades to the bare «لم ترد أفعَلَ», which this whole function exists
      to prevent;
    * **a NOMINAL target** (any POS outside `_ATTESTABLE_POS`). The promised granularity is
      `(lemma, POS/باب)`, and for a nominal the باب slot is the **wazn** — which the two
      axes above cannot express. POS + `verb_form` alone would credit *any* nominal of the
      root as attesting *any* nominal صيغة: root عبد would report a synthetic مِفْعَال
      candidate «attested» on the strength of عَبْد, and the corresponding absence sentence
      would be equally unfounded. The honest fix is a wazn match, but a wazn is a
      **projection** (`compute_mizan`, `verified=False` for hollow/geminate/irregular roots
      and an open hardening change against it), not a corpus fact, so it cannot carry a
      verdict that decides whether a «لم ترد» sentence reaches the page. Nothing ships that
      needs it: `bab_contrast.json` v0.1.0 is verb-only by construction (100 % of its
      targets are `pos='V'`, and `contrast_candidates` routes on `mizan["bab"]`, `None` for
      every nominal). So this refuses until the nominal contrast table ships with the wazn
      the granularity requires — the same refuse-rather-than-guess contract as the unmapped
      POS above, and as `qac_labels.translate_features` on an unmapped code.
    """
    pos = (target or {}).get("pos")
    scope_word = _POS_SCOPE_AR.get(pos or "")
    if scope_word is None:
        raise ValueError(
            f"contrast target POS {pos!r} has no Arabic scope word; without one the "
            "absence clause cannot name the granularity and would be false."
        )
    if pos not in _ATTESTABLE_POS:
        raise ValueError(
            f"contrast target POS {pos!r} is nominal: attestation at (lemma, POS/باب) "
            "granularity needs the target's WAZN, which the corpus does not record and "
            "`compute_mizan` only projects. Matching on POS alone would credit a different "
            "nominal pattern of the same root. Refused until the nominal contrast table "
            "ships a wazn."
        )
    want_form = (target or {}).get("verb_form") or None
    bab = (target or {}).get("bab") or ""

    refs: list[str] = []
    lemmas: list[str] = []
    words = qac_words()
    for ref in root_graph().get(root or "", ()):
        rec = words.get(ref) or {}
        if rec.get("pos") != pos:
            continue
        if ((rec.get("features") or {}).get("verb_form") or None) != want_form:
            continue
        refs.append(ref)
        display = rec.get("lemma_display") or rec.get("lemma")
        if display and display not in lemmas:
            lemmas.append(display)

    attested = bool(refs)
    return {
        "attested": attested,
        "attested_refs": refs[:ATTEST_REFS_CAP],
        "attested_lemmas": lemmas,
        "attested_count": len(refs),
        # Empty when the form IS attested: there is no absence to scope.
        "absence_scope_ar": "" if attested else f"ولم ترد صيغة {bab} {scope_word} من هذا الجذر",
        # The SAME sentence, computed for the attested case too — the one the claim must
        # NOT contain. It exists so the gate can refuse a denial of an attested form by
        # exact containment, exactly as it licenses an absence by exact containment. A
        # heuristic here (an absence marker anywhere + the باب named anywhere) was tried
        # and is wrong: a claim legitimately enumerating «فَعَّلَ و أَفْعَلَ» while denying
        # only the second names the attested باب too, and the heuristic dropped it.
        "denial_sentence_ar": f"ولم ترد صيغة {bab} {scope_word} من هذا الجذر" if attested else "",
    }


def _narrow_contrast_id(parent_cite_id: str, target_bab: str) -> str:
    """`contrast:<source>@<v>` + a target باب → `contrast:<source>><target>@<v>`.

    The ONE narrowing exception tasks.md 4.2 grants to the copy-verbatim rule, and it is
    required rather than cosmetic: `form_kb` mints one id per **source** باب covering
    several targets whose attestation verdicts differ (6 992 of 19 356 verbs), so a single
    boolean on that id is false of at least one of them.

    The owner's id is not re-derived: it is *split*, so the version token and the source
    باب are the owner's bytes, and only the target is added. A parent that does not carry a
    version token, or a target باب that would corrupt the grammar, raises — an id the gate
    cannot parse back to one candidate is exactly what this narrowing exists to prevent.
    """
    head, sep, version = parent_cite_id.rpartition("@")
    if not sep or not head or not version:
        raise ValueError(
            f"contrast parent id {parent_cite_id!r} carries no @version token; it cannot be "
            "narrowed to one target without re-deriving its owner's grammar."
        )
    if not target_bab or ">" in target_bab or "@" in target_bab:
        raise ValueError(f"contrast target باب {target_bab!r} is not a usable id component")
    return f"{head}>{target_bab}@{version}"


def _contrast_entries(mizan: dict, record: dict, root: str | None) -> list[dict]:
    """The باب contrast candidates, each carrying **our** attestation verdict and its OWN id.

    The candidates come from `form_kb.contrast_candidates` verbatim; this adds the verdict
    (attestation is a corpus question and the KB file ships candidates only) and narrows the
    owner's `cite_id` to the single target the verdict is about, recording the owner's id as
    `parent_cite_id`.

    Why the entry's own `cite_id` is the narrowed one rather than an extra field beside the
    parent: this list is what the renderer walks, one claim per candidate, and a claim must
    cite the id whose boolean it stands on. Leaving the parent here would have every
    per-candidate sentence cite an id that is true of some other candidate.
    """
    out: list[dict] = []
    for candidate in form_kb.contrast_candidates(mizan, record):
        entry = dict(candidate)
        entry["target"] = dict(candidate["target"])
        parent = candidate["cite_id"]          # minted by form_kb.py
        entry["parent_cite_id"] = parent
        entry["cite_id"] = _narrow_contrast_id(parent, entry["target"].get("bab") or "")
        entry.update(attestation(root, candidate["target"]))
        out.append(entry)
    return out


def _contrast_item(entry: dict) -> dict:
    """The gate's view of ONE contrast candidate — one id, one target, one verdict.

    Replaces an aggregate over every candidate sharing the owner's باب id, which was not
    merely coarse but false on real words. On root عبد (1:5:2) the aggregate carried
    `attested=False` (`all()` over a mixed set) and an absence sentence naming only
    أَفْعَلَ, so a claim asserting that **فَعَّلَ** does not occur — it does, at 26:22:6 —
    cited that id, matched the gate's absence check, and rendered. `any()` would have been
    worse in the mirror direction. Neither direction is fixable: two candidates with
    different verdicts cannot share one honest boolean.

    The item carries exactly what the gate reads, plus what makes the verdict checkable:
    the target it is about, the refs that attest it, the absence sentence the gate now
    requires **verbatim** in an unattested claim, and the parent id it was narrowed from.
    """
    return {
        "kind": KIND_CONTRAST,
        "attested": entry["attested"],
        "attested_refs": list(entry["attested_refs"]),
        "absence_scope_ar": entry["absence_scope_ar"],
        "denial_sentence_ar": entry.get("denial_sentence_ar", ""),
        "target": dict(entry["target"]),
        "source_bab": entry["bab"],
        "parent_cite_id": entry["parent_cite_id"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Naẓāʾir
# ─────────────────────────────────────────────────────────────────────────────


def _nazair_totals_for(fiche: dict) -> dict:
    """`nazair_totals` for a fiche — the bundle-level convenience wrapper."""
    sarfi = fiche.get("sarfi") or {}
    return nazair_totals(sarfi.get("root"), sarfi.get("lemma"))


def nazair_totals(root: str | None, lemma: str | None) -> dict:
    """`{"root": n, "same_lemma": n}` — the TRUE sibling populations, from the corpus.

    Derived from `root_graph` + the word index, independent of every cap above: the fiche's
    30-entry naẓāʾir list, `NAZAIR_CAP`, and any injected ranker. It exists because a
    consumer that counts the bundle's naẓāʾir list is counting the *cap*, not the corpus —
    and the دلالي block renders that count under the **محقّق** badge. A verified-badged
    «جملة النظائر: 8» beside a root with 1 721 occurrences is a claim about the corpus that
    the corpus does not support, which inverts this project's first rule.

    Both totals exclude the queried word itself.
    """
    if not root:
        return {"root": 0, "same_lemma": 0}
    refs = root_graph().get(root, ())
    words = qac_words()
    same = sum(1 for r in refs if (words.get(r) or {}).get("lemma") == lemma) if lemma else 0
    return {"root": max(len(refs) - 1, 0), "same_lemma": max(same - 1, 0)}


def _nazair(fiche: dict, self_ref: str, rank: NazairRanker | None) -> tuple[list[dict], list[dict]]:
    """`(bundle naẓāʾir, notes)` — lemma-scoped first, capped, each with its verse.

    The **selection policy is the fiche's**, not a second implementation: `analyze_word`
    already returns same-lemma siblings first and falls back to other lemmas of the root —
    tagged by lemma — when fewer than three exist (measured: 3.5 % of rooted words have no
    same-lemma sibling, 8.2 % have fewer than three). Task 4.1 is explicit that this module
    *composes on top of* the fiche; re-deriving the policy here would be a second source of
    truth for the one thing the دلالي block stands on.

    Order is **deterministic corpus order** unless a `rank` is injected (see the module
    docstring's seam). The ranker may reorder and drop; a ref it did not receive raises,
    because the bundle's naẓīr ids are the citation vocabulary and a seam that could add to
    them would be a hole straight through the cite-or-omit guarantee.
    """
    notes: list[dict] = []
    candidates = list(fiche["sarfi"].get("nazair") or [])
    lemma = fiche["sarfi"].get("lemma")
    root = fiche["sarfi"].get("root")

    if not candidates:
        if root:
            notes.append(_note(NOTE_NO_NAZIR))
        return [], notes

    # Population BEFORE any ranking. Computed here, and from the corpus rather than from
    # `candidates`, because both layers above us truncate: the fiche caps its naẓāʾir list
    # at 30, and an injected ranker may drop to the cap. Deriving the truncation note from
    # the post-rank list let the module's own documented seam suppress it — a reranker
    # selecting the top 8 of 1 617 produced a bundle with `notes == []`, i.e. the cap
    # silently hiding evidence, which is precisely what it must never do.
    totals = nazair_totals(root, lemma)
    pre_rank = len(candidates)

    if rank is not None:
        allowed = {c["ref"] for c in candidates}
        ranked = list(rank(self_ref, [dict(c) for c in candidates]))
        seen: set[str] = set()
        for item in ranked:
            ref = item.get("ref")
            if ref not in allowed:
                raise ValueError(
                    f"naẓīr ranker returned {ref!r}, which is not among the "
                    f"{len(allowed)} candidates — a ranker may reorder or drop, never add."
                )
            if ref in seen:
                raise ValueError(f"naẓīr ranker returned {ref!r} twice")
            seen.add(ref)
        candidates = ranked

    # Fire on the TRUE population, not on what survived ranking: `shown` is what the bundle
    # carries, and the totals are what the corpus holds. A ranker that drops to the cap must
    # still leave the truncation stated.
    shown = min(len(candidates), NAZAIR_CAP)
    # Fire on TRUNCATION, never on POLICY. `pre_rank > shown` catches the cap and any
    # ranker that dropped; `same_lemma > shown` catches the fiche's own 30-entry cap hiding
    # same-lemma siblings. The root total is deliberately NOT a trigger: other-lemma
    # siblings are excluded because the block is lemma-scoped, not because anything was
    # cut — and a note claiming truncation where none occurred is as false as a missing one.
    if pre_rank > shown or totals["same_lemma"] > shown:
        notes.append(_note(NOTE_NAZAIR_CAPPED, shown=shown,
                           root_siblings=totals["root"],
                           same_lemma_siblings=totals["same_lemma"]))

    out: list[dict] = []
    cross_lemma = False
    for candidate in candidates[:NAZAIR_CAP]:
        ref = candidate["ref"]
        surah, ayah, word = (int(p) for p in ref.split(":"))
        vocalized, _aligned = surface_vocalized(surah, ayah, word)
        verse_text, surah_name = _verse_text(surah, ayah)
        same_lemma = candidate.get("lemma") == lemma
        cross_lemma = cross_lemma or not same_lemma
        out.append({
            "cite_id": f"{KIND_NAZIR}:{ref}",
            "ref": ref,
            "surah": surah,
            "ayah": ayah,
            "word": word,
            "surah_name_ar": surah_name,
            "lemma": candidate.get("lemma"),
            "lemma_display": candidate.get("lemma_display"),
            # Load-bearing tag: a same-root/other-lemma naẓīr is root-level evidence and the
            # claim standing on it must say so (spec: «cross-lemma evidence is labelled»).
            "same_lemma": same_lemma,
            "word_vocalized": vocalized,
            "verse_text": verse_text,
        })

    if cross_lemma:
        notes.append(_note(NOTE_NAZAIR_CROSS_LEMMA))
    return out, notes


# ─────────────────────────────────────────────────────────────────────────────
# 4. The bundle
# ─────────────────────────────────────────────────────────────────────────────


def _qac_items(fiche: dict, record: dict,
               self_ref: str) -> tuple[dict[str, dict], dict, list[dict]]:
    """`(citable items, rendered-but-uncitable facts, notes)` for this verse's syntax.

    Two outputs, because two different guarantees apply to the same three values.

    **Citable** (`qac:<field>@<ref>`, closed to `_QAC_FIELDS`): الموقع الإعرابي and
    المتعلَّق. The gate reads any `qac:` cite as a corpus disambiguator, so this set may
    hold only facts that could *discriminate one sense of a form from another* — what the
    word is doing in this verse, and what it attaches to. The closure is enforced, not
    documented: an unknown key raises before the loop (module docstring §4), the same
    contract as `translate_features` on an unmapped code. A field with no value is
    **omitted**, never emitted empty — an id that resolves to nothing is worse than a
    missing id, because it passes the gate.

    **Rendered, not citable**: العلامة. It is a case/mood inflection, identical on every
    مضارع مرفوع of الأفعال الخمسة whatever the verb means, so it can license no sense
    selection; and for a verb it is derived from the same morphology record that routed the
    KB row, which is the circularity that already excluded bab/wazn. It is still the fact
    §3 of this change adds, still badged محقّق on the page, so it travels in
    `nahwi_facts` — where the renderer reads it and `display_strings` sweeps it, but no
    claim can spend it as an anchor. Verb path: `verb_marker` (the fiche's `case_marker`
    returns `None` for 23:61:2). Nominal path: read **from the fiche**, so a محقّق string
    can never differ between Tahlil and QLisan.
    """
    nahwi = fiche.get("nahwi") or {}
    notes: list[dict] = []
    if not nahwi.get("available"):
        notes.append(_note(NOTE_NO_SYNTAX))

    values = {
        QAC_RELATION: nahwi.get("iraab_ar"),
        QAC_HEAD: nahwi.get("head_ref"),
    }
    unknown = sorted(set(values) - set(_QAC_FIELDS))
    if unknown:
        raise ValueError(
            f"qac field(s) {unknown} are outside the closed set {list(_QAC_FIELDS)}. "
            "Every qac id is read by the gate as a corpus disambiguator, so widening this "
            "set silently re-badges unanchored sense selections."
        )
    items: dict[str, dict] = {}
    for field in _QAC_FIELDS:
        value = values.get(field)
        if not value:
            continue
        items[f"{KIND_QAC}:{field}@{self_ref}"] = {
            "kind": KIND_QAC, "field": field, "ref": self_ref, "value_ar": value,
        }
    facts = {f"{QAC_MARKER}_ar": qac_labels.verb_marker(record) or nahwi.get("marker_ar") or ""}
    return items, facts, notes


def build(surah: int, ayah: int, word: int, *, rank: NazairRanker | None = None) -> dict:
    """Assemble the evidence bundle for the word at `surah:ayah:word`.

    Composes **on top of** `analysis.word_analysis.analyze_word` (task 4.1): the fiche is
    carried whole under `fiche` and its deterministic facts are never re-derived here.

    Returns a JSON-serialisable dict:

    ``ref``/``surah``/``ayah``/``word``   the position
    ``surface_vocalized``                 from chakl, **never** the QAC `uthmani` field
    ``fiche``                             the QLisan four-level fiche, verbatim
    ``items``                             ``{cite_id: item}`` — the citation vocabulary the
                                          gate resolves against; every key's kind is one of
                                          the six, so no commentary source is reachable
    ``letters``/``nazair``/``sigha_rows``/``contrast``/``maqayis``   the evidence, in
                                          render order, each entry carrying its `cite_id`
                                          (a contrast entry's is narrowed to **its own**
                                          target, with the owner's id under
                                          `parent_cite_id`)
    ``nahwi_facts``                       deterministic نحوي values that are rendered but
                                          NOT citable — today العلامة
    ``versions``                          letters / sigha / contrast / kb — the cache key's
                                          components
    ``notes``                             stated reasons for everything absent

    Raises `ValueError` on non-positive indices and `KeyError` on a position the corpus does
    not hold (both from `analyze_word`). A root letter that resolves to no dataset row
    raises out of `huruf.describe` and is **not** caught: that is the 4 698-word silent
    truncation the letters loader exists to make loud, and swallowing it here would restore
    it one layer up.
    """
    fiche = analyze_word(surah, ayah, word)
    self_ref = fiche["ref"]
    record = qac_words()[self_ref]
    sarfi = fiche["sarfi"]
    root = sarfi.get("root")
    mizan = sarfi.get("mizan") or {}

    notes: list[dict] = []
    items: dict[str, dict] = {}

    # --- the surface under analysis -------------------------------------------------
    vocalized, aligned = surface_vocalized(surah, ayah, word)
    if not aligned:
        notes.append(_note(NOTE_SURFACE_UNALIGNED))

    # --- الحروف ----------------------------------------------------------------------
    letters: list[dict] = []
    if root:
        letters = huruf.decompose(root)
        for entry in letters:
            cite_id = entry["cite_id"]          # minted by huruf.py — copied VERBATIM
            item = items.get(cite_id)
            if item is None:
                items[cite_id] = {
                    "kind": KIND_LETTER,
                    "letter": entry["letter"],
                    "name": entry["name"],
                    "sense_category": entry["sense_category"],
                    "sifat": entry["sifat"],
                    "dalala": entry["dalala"],
                    "badges": entry["badges"],
                    "has_position_notes": entry["has_position_notes"],
                    # A geminate root (مدد) repeats a letter, so one id covers two slots.
                    # Both positions are kept: the framework reads a letter's دلالة off its
                    # position, and dropping the second slot would silently halve a
                    # doubled radical's contribution.
                    "positions": [entry["position"]],
                }
            else:
                item["positions"].append(entry["position"])
    else:
        notes.append(_note(NOTE_ROOTLESS))

    # --- النظائر ---------------------------------------------------------------------
    nazair, nazair_notes = _nazair(fiche, self_ref, rank)
    notes.extend(nazair_notes)
    for entry in nazair:
        items[entry["cite_id"]] = {
            "kind": KIND_NAZIR,
            "ref": entry["ref"],
            "lemma": entry["lemma"],
            "lemma_display": entry["lemma_display"],
            "same_lemma": entry["same_lemma"],
            "word_vocalized": entry["word_vocalized"],
            "verse_text": entry["verse_text"],
            "surah_name_ar": entry["surah_name_ar"],
        }

    # --- دلالة الصيغة ----------------------------------------------------------------
    sigha_rows = form_kb.match(record, mizan)
    if not sigha_rows:
        notes.append(_note(NOTE_NO_SIGHA_ROW))
    for row in sigha_rows:
        items[row["cite_id"]] = {                # minted by form_kb.py — copied VERBATIM
            "kind": KIND_SIGHA,
            "id": row["id"],
            "key_type": row["key_type"],
            "key": row["key"],
            "senses": row["senses"],
            "provenance": row["provenance"],
            "notes": row["notes"],
            # The gate reads this to decide whether the claim needs a disambiguator.
            "multi_sense": row["multi_sense"],
        }

    # --- المقابلة البابية -------------------------------------------------------------
    contrast = _contrast_entries(mizan, record, root)
    if not contrast:
        notes.append(_note(NOTE_NO_CONTRAST))
    for entry in contrast:
        cite_id = entry["cite_id"]
        if cite_id in items:
            # Two candidates narrowing to one id would restore the aggregate's defect one
            # layer down: one boolean over two targets. The table has no such row today;
            # the guard is here so a future one fails loudly instead of silently.
            raise ValueError(
                f"contrast id {cite_id!r} was minted twice — an id must name exactly one "
                "candidate, or its `attested` boolean is not true of what it names."
            )
        items[cite_id] = _contrast_item(entry)

    # --- مقاييس اللغة -----------------------------------------------------------------
    maqayis = None
    entry = _maqayis().lookup(root) if root else None
    # `has_asl` is the STATUS, not the presence of a row: 171 roots parse as
    # `parse_uncertain` and one as `no_asl`, and treating «we have a row» as «we have an
    # aṣl» would cite an empty string as a lexical anchor.
    if entry is not None and entry.asl_status == "has_asl" and entry.asl_list():
        maqayis = {
            "cite_id": f"{KIND_MAQAYIS}:{root}",
            "root": root,
            "has_asl": True,
            **entry.to_dict(),
        }
        items[maqayis["cite_id"]] = {
            "kind": KIND_MAQAYIS,
            "root": root,
            "asl_text": maqayis["asl_text"],
            "asl_preamble": maqayis["asl_preamble"],
            "asl_count": maqayis["asl_count"],
            "asl_status": maqayis["asl_status"],
            "source": maqayis["source"],
            "edition": maqayis["edition"],
        }
    elif root:
        notes.append(_note(NOTE_NO_ASL))

    # --- the verse's own syntax --------------------------------------------------------
    qac_items, nahwi_facts, qac_notes = _qac_items(fiche, record, self_ref)
    items.update(qac_items)
    notes.extend(qac_notes)

    return {
        "ref": self_ref,
        "surah": fiche["surah"],
        "ayah": fiche["ayah"],
        "word": fiche["word"],
        "surface_vocalized": vocalized,
        "fiche": fiche,
        "items": items,
        "letters": letters,
        "nazair": nazair,
        # Unconditional, corpus-derived, cap-independent. A consumer that needs "how many
        # naẓāʾir are there" must read THIS, never `len(nazair)` — that length is the cap.
        # The دلالي block renders the total under the محقّق badge, so an inferred count
        # would be a verified claim about the corpus that the corpus does not support.
        "nazair_totals": _nazair_totals_for(fiche),
        "sigha_rows": sigha_rows,
        "contrast": contrast,
        "maqayis": maqayis,
        # Deterministic نحوي values that are RENDERED (badged محقّق) but deliberately NOT
        # citable — today just العلامة. See `_qac_items`: a case/mood inflection cannot
        # disambiguate one sense of a form from another, and for a verb it is read off the
        # record that routed the KB row. Dropping it from the citable set costs 0 words of
        # `qac:` coverage (76 639/77 429 either way) and removes an empty anchor.
        "nahwi_facts": nahwi_facts,
        "versions": {
            "letters": huruf.letters_version(),
            "sigha": form_kb.sigha_version(),
            "contrast": form_kb.contrast_version(),
            "kb": form_kb.kb_version(),
        },
        "notes": notes,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. The gate's view of the bundle
# ─────────────────────────────────────────────────────────────────────────────


def bundle_for_claims(bundle: dict) -> dict:
    """The projection `tahlil.citations.validate(claims, bundle)` consumes — checked.

    The gate resolves a claim's cites against `bundle["items"]`, reads `multi_sense` off a
    `sigha:` item, and reads `attested` **plus `absence_scope_ar`** off a `contrast:` item.
    Those expectations are the interface between two modules built independently, so they
    are **asserted here rather than assumed**, and both directions of the contrast contract
    fail dangerously rather than loudly:

    * a `contrast:` item that lost its `attested` key would not crash the gate — it would
      take the `unchecked-contrast` branch and silently delete every contrast claim on the
      page, which is precisely the kind of failure this design refuses to let pass as «the
      model just didn't say much»;
    * an **unattested** item with an EMPTY `absence_scope_ar` is the same failure in the
      other direction. The gate admits such a claim only by finding that exact sentence
      inside it, so an empty one can never be found: every contrast claim on the page is
      deleted, silently, and reads as «the model just didn't say much». (The gate refuses
      an empty scope explicitly rather than treating it as the empty substring — which is
      the reason to keep BOTH checks: this one guarantees the emitted item is usable, that
      one guarantees no reading of it can rubber-stamp a claim.) An attested item must
      carry no scope at all — there is no absence to state, and a claim quoting one would
      be false.

    Raises `ValueError` on any violation. Returns `{"items": …}` — deliberately *only* the
    items, so nothing else in the bundle can be reached from the validation path by
    accident.
    """
    items = (bundle or {}).get("items")
    if not isinstance(items, dict):
        raise ValueError("bundle has no `items` mapping — the gate has nothing to resolve against")
    for cite_id, item in items.items():
        kind = kind_of(cite_id)
        if kind is None:
            raise ValueError(
                f"evidence id {cite_id!r} does not follow the id grammar; "
                f"known kinds are {', '.join(KINDS)}"
            )
        if item.get("kind") != kind:
            raise ValueError(
                f"evidence id {cite_id!r} declares kind {item.get('kind')!r} "
                f"but its prefix says {kind!r}"
            )
        if kind == KIND_CONTRAST:
            if not isinstance(item.get("attested"), bool):
                raise ValueError(
                    f"contrast item {cite_id!r} carries no boolean `attested` — the gate "
                    "would drop every claim citing it as `unchecked-contrast`."
                )
            scope = item.get("absence_scope_ar")
            if not isinstance(scope, str):
                raise ValueError(
                    f"contrast item {cite_id!r} carries no `absence_scope_ar` string"
                )
            if not item["attested"] and not scope.strip():
                raise ValueError(
                    f"unattested contrast item {cite_id!r} carries an EMPTY "
                    "`absence_scope_ar`: the gate admits such a claim by finding that "
                    "sentence inside it, and every claim contains the empty string."
                )
            if item["attested"] and scope:
                raise ValueError(
                    f"attested contrast item {cite_id!r} carries an absence sentence "
                    f"{scope!r} — there is no absence to state, and a claim quoting it "
                    "would be false."
                )
        if kind == KIND_SIGHA and not isinstance(item.get("multi_sense"), bool):
            raise ValueError(
                f"sigha item {cite_id!r} carries no boolean `multi_sense` — the gate could "
                "not tell a sense selection from a lookup."
            )
    return {"items": items}


def display_strings(bundle: dict) -> list[str]:
    """Every string of the bundle that is **rendered to a reader**, flattened.

    Enumerated explicitly rather than walked generically, and that is the point: the bundle
    also carries *data* that is Latin by nature — raw QAC codes (`pos: "V"`,
    `relation: "Pred"`, `verb_form: "(III)"`), version strings, and the cite ids themselves
    — none of which is ever shown. A generic walk would either fail on those or force them
    to be laundered. Listing the display fields here makes «is this shown?» a decision
    recorded in code, so adding a rendered field without adding it to this list is a
    reviewable omission instead of an invisible one.

    That cuts both ways, and one omission was live: the `qac:` item **values** — الموقع
    الإعرابي, المتعلَّق, and (now via `nahwi_facts`) العلامة — are rendered by
    `tahlil_service._nahwi_claims` as «الموقع الإعرابي: خبر.» and «العلامة: مرفوع وعلامته
    ثبوت النون.», i.e. they are the whole visible نحوي block, yet the sweep never saw them.
    A purity sweep that skips a rendered field is a sweep that cannot fail on it. They are
    listed below.

    Used by the Arabic-purity sweep: a Latin word-character in a display value is the
    `lisan/` failure (a Latin fragment injected mid-word) reaching the page.
    """
    out: list[str] = [bundle.get("surface_vocalized", "")]
    out += [n.get("message_ar", "") for n in bundle.get("notes") or []]

    # The نحوي block, rendered: the citable syntactic facts + the uncitable marker.
    for item in (bundle.get("items") or {}).values():
        if item.get("kind") == KIND_QAC:
            out.append(item.get("value_ar", ""))
    out += [str(v) for v in (bundle.get("nahwi_facts") or {}).values() if isinstance(v, str)]

    for entry in bundle.get("letters") or []:
        out += [entry.get("name", ""), entry.get("sense_category", ""), entry.get("position", "")]
        out += [str(v) for v in (entry.get("sifat") or {}).values() if isinstance(v, str)]
        for value in (entry.get("sifat") or {}).values():
            if isinstance(value, list):
                out += [str(v) for v in value]
        dalala = entry.get("dalala") or {}
        out += [dalala.get("core_meaning", ""), dalala.get("position_notes", ""),
                dalala.get("pages", "")]

    for entry in bundle.get("nazair") or []:
        out += [entry.get("surah_name_ar", ""), entry.get("word_vocalized", ""),
                entry.get("verse_text", ""), entry.get("lemma_display") or ""]

    for row in bundle.get("sigha_rows") or []:
        out += [row.get("key", ""), row.get("provenance", ""), row.get("notes", "")]
        for sense in row.get("senses") or []:
            out += [sense.get("sense_ar", ""), sense.get("note_ar", "")]

    for entry in bundle.get("contrast") or []:
        out += [entry.get("rationale_ar", ""), entry.get("provenance", ""),
                entry.get("absence_scope_ar", ""), (entry.get("target") or {}).get("bab") or "",
                entry.get("bab", "")]
        out += [lemma for lemma in entry.get("attested_lemmas") or []]

    maqayis = bundle.get("maqayis") or {}
    out += list(maqayis.get("asl_text") or [])
    out.append(maqayis.get("asl_preamble", ""))

    return [s for s in out if s]


if __name__ == "__main__":  # smoke test — mirrors huruf.py / form_kb.py
    import json

    # 1:5:2 is the MIXED case (root عبد: فَعَّلَ attested at 26:22:6, أَفْعَلَ absent) — the
    # word whose aggregated contrast item used to deny an attested باب. One line per
    # candidate now, each with its own id and its own verdict.
    for position in ((23, 61, 2), (23, 61, 3), (1, 1, 2), (1, 5, 2)):
        bundle = build(*position)
        print(f"\n=== {bundle['ref']}  «{bundle['surface_vocalized']}» "
              f"(uthmani on disk: «{bundle['fiche']['word_uthmani']}») ===")
        print("  letters :", " · ".join(f"{e['letter']}{e['position']}" for e in bundle["letters"]) or "—")
        print("  nazair  :", ", ".join(e["ref"] for e in bundle["nazair"]) or "—")
        print("  sigha   :", ", ".join(r["cite_id"] for r in bundle["sigha_rows"]) or "—")
        print("  marker  :", bundle["nahwi_facts"]["marker_ar"] or "—", "(rendered, not citable)")
        for entry in bundle["contrast"]:
            verdict = ("وارد في " + "، ".join(entry["attested_refs"])) if entry["attested"] \
                else entry["absence_scope_ar"]
            print(f"  contrast: {entry['cite_id']:<34} {verdict}")
        print("  maqayis :", (bundle["maqayis"] or {}).get("asl_text") or "—")
        print("  items   :", len(bundle["items"]), "→",
              sorted({i["kind"] for i in bundle["items"].values()}))
        print("  notes   :", [n["code"] for n in bundle["notes"]] or "—")
        json.dumps(bundle, ensure_ascii=False)  # must stay serialisable
        bundle_for_claims(bundle)               # must satisfy the gate's contract
