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

from analysis.qlisan_data import qac_syntax, qac_words, root_graph
from indexing.corpus import chakl_by_ref

# Fixed presentation order of the four levels (شرط العقد: never reorder).
LEVELS_ORDER = ["sawti", "sarfi", "nahwi", "dalali"]

# Naẓāʾir (root siblings) cap — enough to show breadth without flooding the fiche.
_NAZAIR_CAP = 30

_SAWTI_MESSAGE = "التحليل الصوتي غير متوفر بعد."
_DALALI_MESSAGE = "التحليل الدلالي غير متوفر بعد."
_NAHWI_UNAVAILABLE_MESSAGE = "لا يوجد تحليل نحوي محفوظ لهذه الكلمة."


def _nazair(root: str | None, self_ref: str) -> list[dict]:
    """Up to `_NAZAIR_CAP` root siblings (refs sharing `root`), excluding `self_ref`.

    Each entry is `{ref, word_uthmani}`; `word_uthmani` is looked up from the same
    morphology index (empty string if a sibling ref is somehow absent).
    """
    if not root:
        return []
    words = qac_words()
    out: list[dict] = []
    for ref in root_graph().get(root, []):
        if ref == self_ref:
            continue
        rec = words.get(ref, {})
        out.append({"ref": ref, "word_uthmani": rec.get("uthmani", "")})
        if len(out) >= _NAZAIR_CAP:
            break
    return out


def _sarfi(record: dict, self_ref: str) -> dict:
    """The صرفي (morphology) level — verbatim from the QAC word record."""
    root = record.get("root")
    return {
        "available": True,
        "root": root,
        "root_display": record.get("root_display"),
        "lemma": record.get("lemma"),
        "lemma_display": record.get("lemma_display"),
        "pos": record.get("pos", ""),
        "pos_ar": record.get("pos_ar", ""),
        "features": record.get("features", {}) or {},
        "segments": record.get("segments", []) or [],
        "is_proper_noun": bool(record.get("is_proper_noun", False)),
        "nazair": _nazair(root, self_ref),
    }


def _nahwi(self_ref: str) -> dict:
    """The نحوي (syntax) level — verbatim from the dependency index, or unavailable.

    Words with no treebank annotation are absent from `qac_syntax.json`; for them
    the level is `available:false` (never fabricated)."""
    rec = qac_syntax().get(self_ref)
    if rec is None:
        return {
            "available": False,
            "role_ar": None,
            "relation": None,
            "relation_ar": None,
            "head_ref": None,
            "message": _NAHWI_UNAVAILABLE_MESSAGE,
        }
    return {
        "available": True,
        "role_ar": rec.get("role_ar"),
        "relation": rec.get("relation"),
        "relation_ar": rec.get("relation_ar"),
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
        "nahwi": _nahwi(self_ref),
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
