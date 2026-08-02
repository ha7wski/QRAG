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

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis import mizan, qac_labels
from analysis.qlisan_data import qac_syntax, qac_words, root_graph
from indexing.corpus import chakl_by_ref

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


def _nazair(root: str | None, lemma: str | None, self_ref: str) -> list[dict]:
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
    refs = [ref for ref in root_graph().get(root, []) if ref != self_ref]

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
    return {
        "available": True,
        "root": root,
        "root_display": record.get("root_display"),
        "lemma": lemma,
        "lemma_display": record.get("lemma_display"),
        "pos": record.get("pos", ""),  # raw, kept as data (not rendered)
        "pos_ar": record.get("pos_ar", ""),
        "features": qac_labels.translate_features(record.get("features", {}) or {}),
        "segments": mizan.segment_breakdown(record, self_ref),
        "mizan": mizan.compute_mizan(record, self_ref),
        "is_proper_noun": bool(record.get("is_proper_noun", False)),
        "nazair": _nazair(root, lemma, self_ref),
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
