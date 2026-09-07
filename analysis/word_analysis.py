"""
word_analysis.py — Deterministic per-word QLisan fiche assembler (increment 0+1).

Given a word at `surah:ayah:word` (1-based QAC `word_id`), assemble the four-level
fiche in fixed order صوتي → صرفي → نحوي → دلالي:

  - **sarfi** (morphology)  — served verbatim from `qac_words.json`.
  - **nahwi** (syntax)      — served verbatim from `qac_syntax.json` (absent word ⇒
                              `available:false`, never fabricated).
  - **sawti** (phonetics)   — stub in this increment (`available:false`).
  - **dalali** (semantics)  — stub in this increment (`available:false`).

`nazair` (naẓāʾir — root siblings) come from `root_graph.json`, capped at ~30 and
excluding the word itself.

**Deterministic invariant:** every field here comes from the parsed on-disk index
(no LLM, no network). Pure stdlib — importable and testable without fastapi/pydantic.
Root/lemma keys are already `normalize_root`-normalized upstream (never
`normalize_text`, which deletes hamza).
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis import mizan, qac_labels
from analysis.qlisan_data import qac_syntax, qac_words, root_graph
from indexing.corpus import chakl_by_ref
from indexing.text_normalize import normalize_search

# Fixed presentation order of the four levels (شرط العقد: never reorder).
LEVELS_ORDER = ["sawti", "sarfi", "nahwi", "dalali"]

# Naẓāʾir (root siblings) cap — enough to show breadth without flooding the fiche.
_NAZAIR_CAP = 30

# Below this many same-lemma siblings the strip falls back to other lemmas under
# the same root, tagged by lemma so the UI can render them in labelled groups.
_NAZAIR_MIN_SAME_LEMMA = 3

_SAWTI_MESSAGE = "التحليل الصوتي غير متوفر بعد."
_DALALI_MESSAGE = "التحليل الدلالي غير متوفر بعد."
_NAHWI_UNAVAILABLE_MESSAGE = "لا يوجد تحليل نحوي محفوظ لهذه الكلمة."


def _nazair(root: str | None, lemma: str | None, self_ref: str,
            alternates: list[str] | None = None) -> list[dict]:
    """Up to `_NAZAIR_CAP` root siblings (refs sharing `root`), excluding `self_ref`.

    Filtered to the **same lemma** as the queried word (never mixing homographic
    senses under one root). When the same-lemma set is below
    `_NAZAIR_MIN_SAME_LEMMA`, other lemmas under the same root are appended so the
    strip is not near-empty — but **tagged by lemma** so the UI can render them in
    separate, labelled groups. Same-lemma entries always come first; order within
    each group follows the deterministic `root_graph` order.

    Each entry is `{ref, word_uthmani, lemma, lemma_display}`; the lemma tags let
    the frontend group the strip. Lookups come from the same morphology index
    (empty/None if a sibling ref is somehow absent).
    """
    if not root:
        return []
    words = qac_words()
    # A contested root gathers siblings under BOTH readings, so the strip does not
    # depend on which one the reader holds: ٱلْمَاعُون (primary معن, alternate عون) would
    # otherwise show no naẓīr at all, its primary being a hapax. Each ref once, in
    # root_graph order.
    graph = root_graph()
    seen: set[str] = {self_ref}
    refs: list[str] = []
    for rk in [root, *(alternates or [])]:
        for ref in graph.get(rk, []):
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)

    same = [ref for ref in refs if (words.get(ref) or {}).get("lemma") == lemma]
    if lemma is not None and len(same) < _NAZAIR_MIN_SAME_LEMMA:
        others = [ref for ref in refs if ref not in same]
        ordered = same + others  # same-lemma first, then other lemmas (grouped by tag)
    else:
        ordered = same

    out: list[dict] = []
    for ref in ordered:
        rec = words.get(ref, {})
        out.append(
            {
                "ref": ref,
                "word_uthmani": rec.get("uthmani", ""),
                "lemma": rec.get("lemma"),
                "lemma_display": rec.get("lemma_display"),
            }
        )
        if len(out) >= _NAZAIR_CAP:
            break
    return out


def _sarfi(record: dict, self_ref: str) -> dict:
    """The صرفي (morphology) level — from the QAC word record, translated to Arabic.

    Feature *values* and `segments` are raw QAC codes on disk; they are translated
    to an ordered Arabic `[{label_ar, value_ar}]` list and Arabic segment labels
    here (via `qac_labels`) so nothing Latin/Buckwalter is ever rendered. The raw
    `pos` is kept in the record (data) — `pos_ar` is the sole rendered POS source.
    """
    root = record.get("root")
    lemma = record.get("lemma")
    alternates = list(record.get("root_alternates") or [])
    return {
        "available": True,
        "root": root,
        "root_display": record.get("root_display"),
        # A root the two resources read differently (ٱلنَّاس: أنس / نوس). Shown as a
        # note, outside the «معطى محقّق» badge — an arbitrated root is a decision,
        # not a field taken verbatim from one source. Empty when uncontested.
        "root_alternates": alternates,
        # The root sits on one segment of a welded word (يَٰٓأَيُّهَا, يَوْمَئِذٍ), so the
        # fiche can say so instead of implying the whole word derives from it.
        "fused_compound": bool(record.get("fused_compound", False)),
        "lemma": lemma,
        "lemma_display": record.get("lemma_display"),
        "pos": record.get("pos", ""),  # raw, kept as data (not rendered)
        "pos_ar": record.get("pos_ar", ""),
        "features": qac_labels.translate_features(record.get("features", {}) or {}),
        "segments": mizan.segment_breakdown(record, self_ref),
        "mizan": mizan.compute_mizan(record, self_ref),
        "is_proper_noun": bool(record.get("is_proper_noun", False)),
        "nazair": _nazair(root, lemma, self_ref, alternates),
    }


def _compose_iraab(relation_ar: str | None, nominal_case: str | None) -> str | None:
    """The «الموقع الإعرابي» string: relation function [+ case word], composed safely.

    * `relation_ar` is normalised through the override map so it is never emitted as
      ASCII (`root`→«عمدة الجملة») nor a bare case word (`gen`→«اسم مجرور»).
    * The case word is appended **only** when the relation's canonical case matches
      the word's present `nominal_case` — guarding the 83 `Subj`-tagged-«مفعول به»
      mislabels (never «مفعول به مرفوع») and the `gen`/`root` cases (no stutter).
    * For مبني words (no `nominal_case`) the relation function alone is shown, with
      no fabricated lafẓī case word.
    """
    display = qac_labels.relation_ar_display(relation_ar)
    if display is None:
        return None
    if nominal_case:
        canonical = qac_labels.relation_canonical_case(relation_ar)
        if canonical is not None and canonical == nominal_case:
            case_word = qac_labels.NOMINAL_CASE_AR.get(nominal_case)
            if case_word:
                return f"{display} {case_word}"
    return display


def _nahwi(self_ref: str, record: dict) -> dict:
    """The نحوي (syntax) level — iʿrāب composed safely from the treebank + صرفي case.

    Words with no treebank annotation are absent from `qac_syntax.json`; for them
    the level is `available:false` (never fabricated). `iraab_ar` is the composed
    «الموقع الإعرابي»; `marker_ar` (العلامة) is a derived الأصل hint, omitted (never
    fabricated) where unreliable. `role_ar` is deprecated — the stale
    `role_ar = pos_ar` source field is no longer read (left `None`).
    """
    rec = qac_syntax().get(self_ref)
    if rec is None:
        return {
            "available": False,
            "role_ar": None,
            "relation": None,
            "relation_ar": None,
            "iraab_ar": None,
            "marker_ar": None,
            "head_ref": None,
            "message": _NAHWI_UNAVAILABLE_MESSAGE,
        }
    features = record.get("features", {}) or {}
    nominal_case = features.get("nominal_case")
    relation_ar = rec.get("relation_ar")
    return {
        "available": True,
        "role_ar": None,  # deprecated: stale `role_ar = pos_ar` source field not read
        "relation": rec.get("relation"),  # raw, kept as data (not rendered)
        "relation_ar": relation_ar,  # raw, kept as data (not rendered)
        "iraab_ar": _compose_iraab(relation_ar, nominal_case),
        "marker_ar": qac_labels.case_marker(record),
        "head_ref": rec.get("head_ref"),
        "message": None,
    }


def analyze_word(surah: int, ayah: int, word: int) -> dict:
    """Assemble the four-level fiche for the word at `surah:ayah:word`.

    Raises:
        ValueError: if any of `surah`/`ayah`/`word` is not a positive integer.
        KeyError:   if the position does not exist in the corpus.
    """
    try:
        surah, ayah, word = int(surah), int(ayah), int(word)
    except (TypeError, ValueError) as exc:
        raise ValueError("surah, ayah, word must be integers") from exc
    if surah < 1 or ayah < 1 or word < 1:
        raise ValueError("surah, ayah, word must be positive (1-based)")

    self_ref = f"{surah}:{ayah}:{word}"
    record = qac_words().get(self_ref)
    if record is None:
        raise KeyError(self_ref)

    return {
        "ref": self_ref,
        "surah": surah,
        "ayah": ayah,
        "word": word,
        "word_uthmani": record.get("uthmani", ""),
        "word_imlaai": record.get("imlaai", ""),
        "levels_order": list(LEVELS_ORDER),
        "sawti": {"available": False, "message": _SAWTI_MESSAGE},
        "sarfi": _sarfi(record, self_ref),
        "nahwi": _nahwi(self_ref, record),
        "dalali": {"available": False, "message": _DALALI_MESSAGE},
    }


# ── position-free lookup (the «تحليل نحوي» section of Lisan Analysis) ───────
#
# QAC annotates TOKENS IN CONTEXT: there is no form→morphology lexicon, every index
# in `qlisan_data` is keyed by `"surah:ayah:word"`. A word typed with no verse
# position is therefore read from ONE attested occurrence — the first in mushaf
# order — and only the fields that hold for *every* occurrence of that form are
# published — `النظائر` among them, since root and lemma decide it. The occurrence is
# returned as `ref` so the UI can cite it: the reader never chose it, so it must not
# look like a field about the word in the abstract.

# Feature rows stating the word's syntactic POSITION rather than its form: ٱلرَّحِيمِ
# is مجرور in 1:1:4 and مرفوع elsewhere; تُنذِرْ is مجزوم after لَمْ and مرفوع without it.
# Keyed by feature NAME and resolved to the Arabic label here, so a renamed label
# raises at import instead of silently letting a positional row through.
_POSITIONAL_FEATURE_LABELS = frozenset(
    qac_labels.FEATURE_LABEL_AR[k] for k in ("nominal_case", "verb_mood")
)

# Superscript (dagger) alef — QAC writes some forms with it (بَقَرَٰت) where the reader
# types a plene alef. `normalize_search` strips it as a diacritic, dropping the alef
# entirely, so it is folded on both sides first — the same reconciliation
# `retrieval/verse_lookup.py::_norm_match` makes, kept local so this module keeps its
# light treebank-only dependency set.
_SUPERSCRIPT_ALEF = "\u0670"

_FORM_UNATTESTED_MESSAGE = "لا يرد هذا اللفظ في المصحف، فلا تحليل صرفي محقّق له."
_FORM_EMPTY_MESSAGE = "أدخل كلمة عربية."


def _norm_form(text: str) -> str:
    """Hamza-safe match key for a surface word form (dagger alef → plene alef)."""
    return normalize_search(text.replace(_SUPERSCRIPT_ALEF, "ا"))


def _ref_sort_key(ref: str) -> tuple[int, int, int]:
    """Mushaf order for a `"surah:ayah:word"` ref (string order would put 10 before 2)."""
    surah, ayah, word = ref.split(":")
    return int(surah), int(ayah), int(word)


@functools.lru_cache(maxsize=1)
def _form_index() -> dict[str, str]:
    """Normalized word form → the FIRST ref carrying it, in mushaf order.

    Both the imlaai and the uthmani spelling are indexed, so a word typed either way
    resolves. Built from `qac_words()` (not `word_index()`), which guarantees every
    ref it hands back has a morphology record behind it.
    """
    words = qac_words()
    index: dict[str, str] = {}
    for ref in sorted(words, key=_ref_sort_key):
        record = words[ref]
        for surface in (record.get("imlaai"), record.get("uthmani")):
            key = _norm_form(surface or "")
            if key:
                index.setdefault(key, ref)  # first occurrence wins
    return index


def _form_unavailable(typed: str, message: str) -> dict:
    """The `available:false` shape — same keys as a hit, so the UI branches on one flag."""
    return {
        "word": typed,
        "available": False,
        "ref": None,
        "word_uthmani": "",
        "sarfi": {"available": False},
        "message": message,
    }


def analyze_form(word: str | None) -> dict:
    """The صرفي level of a word typed WITHOUT a verse position.

    Returns `{word, available, ref, word_uthmani, sarfi, message}`, where `sarfi` is
    the `analyze_word` morphology level minus its positional rows: the
    `الحالة الإعرابية` / `حالة الفعل` features, which state where the word stands in
    *this* sentence. `النظائر` stays — root and lemma decide it, and both hold for
    the form wherever it occurs.

    Never raises on reader input: empty, non-Arabic or unattested input comes back
    `available:false` carrying an Arabic message.
    """
    typed = (word or "").strip()
    if not typed:
        return _form_unavailable(typed, _FORM_EMPTY_MESSAGE)

    ref = _form_index().get(_norm_form(typed))
    if ref is None:
        return _form_unavailable(typed, _FORM_UNATTESTED_MESSAGE)

    record = qac_words()[ref]
    sarfi = _sarfi(record, ref)
    # Stripped AFTER `_sarfi`, never before: `segments` and `mizan` read the whole
    # record, so filtering its raw `features` upstream would perturb them.
    #
    # `nazair` is deliberately NOT stripped: it is decided by root + lemma, both
    # invariant for a given form, so it states something about the word rather than
    # about the position. `_sarfi` already leaves the cited occurrence out of its own
    # sibling list — the provenance line names it instead.
    sarfi["features"] = [
        f for f in sarfi["features"] if f["label_ar"] not in _POSITIONAL_FEATURE_LABELS
    ]

    return {
        "word": typed,
        "available": True,
        "ref": ref,
        "word_uthmani": record.get("uthmani", ""),
        "sarfi": sarfi,
        "message": None,
    }


def verse_tokens(surah: int, ayah: int) -> dict:
    """The selectable verse + QAC-aligned token boundaries for the QLisan page.

    Returns the vocalized chakl string and one token per QAC `word_id`, each with a
    char span into that string (end exclusive) and an `aligned` flag (`false` ⇒ the
    span is a best-effort fallback).

    Raises:
        ValueError: if `surah`/`ayah` is not a positive integer.
        KeyError:   if the verse does not exist.
    """
    try:
        surah, ayah = int(surah), int(ayah)
    except (TypeError, ValueError) as exc:
        raise ValueError("surah, ayah must be integers") from exc
    if surah < 1 or ayah < 1:
        raise ValueError("surah, ayah must be positive")

    entry = chakl_by_ref().get((surah, ayah))
    if entry is None:
        raise KeyError(f"{surah}:{ayah}")
    text = entry.get("text", "")

    from analysis.qlisan_data import word_index

    idx = word_index()
    tokens: list[dict] = []
    word = 1
    while True:
        rec = idx.get(f"{surah}:{ayah}:{word}")
        if rec is None:
            break
        tokens.append(
            {
                "word": word,
                "uthmani": rec.get("uthmani", ""),
                "imlaai": rec.get("imlaai", ""),
                "char_start": rec.get("chakl_char_start", 0),
                "char_end": rec.get("chakl_char_end", 0),
                "aligned": bool(rec.get("aligned", False)),
            }
        )
        word += 1

    return {
        "surah": surah,
        "ayah": ayah,
        "surah_name_ar": entry.get("surah_name", ""),
        "text": text,
        "tokens": tokens,
    }


if __name__ == "__main__":
    import json

    fiche = analyze_word(1, 1, 2)
    print(json.dumps(fiche, ensure_ascii=False, indent=1))
    vt = verse_tokens(1, 1)
    print("\nverse tokens:")
    for t in vt["tokens"]:
        surface = vt["text"][t["char_start"]:t["char_end"]]
        print(t["word"], repr(surface), "aligned" if t["aligned"] else "FALLBACK")
