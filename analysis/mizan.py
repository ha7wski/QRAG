"""
mizan.py — Deterministic صرفي mīzān (الميزان الصرفي) for the QLisan fiche.

Given a word's QAC root and its fully-vocalized surface form, project the root
radicals onto ف-ع-ل (and a second ل for quadriliterals: فَعْلَل) while copying every
non-radical letter and every diacritic (ḥarakah / sukūn / shadda) verbatim. The
method is uniform for nouns and verbs, so a cleanly-projected mīzān is a *verified*
(«معطى محقّق») derivation of the corpus.

**Scope decision — the mīzān is computed on the STEM**, i.e. the fully-vocalized word
minus separable proclitics (the article ال and the conjunction/preposition clitics
و/ف/ب/ك/ل/س) and pronoun suffixes. The imperfective prefix (ي/ت/أ/ن) is part of the
QAC STEM segment, so it is *kept* — giving يَرْتَعْ → يَفْعَل. The article is *dropped*
(with its sun-letter assimilation shadda) — giving السَّحَاب → فَعَال. This is the one
consistent rule that matches both anchors.

**Confidence flag.** When every root radical is matched, in order, against the stem
letters, the projection is exact → `verified=True` (stays under the «معطى محقّق»
badge). When a radical is missing or transformed on the surface — hollow verbs whose
weak radical surfaced as a different letter (قِيلَ, root قول), or geminated roots whose
last two radicals merged under a shadda (مَدَّ, root مدد) — the projection is a
best-effort → `verified=False` (rendered as an heuristic «اجتهادي» hint, not under the
verified badge). Sound hamzated roots (سأل → تَفْعَلُوا) and quadriliterals
(سنبل → فَعَالِل) project cleanly and stay verified.

Pure stdlib + local corpus indexes (no LLM, no network). QAC source data is never
altered — the mīzān is derived here at assembler time.
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.qlisan_data import word_index
from indexing.corpus import chakl_by_ref

# Combining marks we copy verbatim onto the mīzān (ḥarakāt, tanwīn, shadda, sukūn,
# dagger alif). Detection also falls back to the Unicode "Mn" (nonspacing mark)
# category so any stray combining mark is treated as a diacritic, not a letter.
_SHADDA = "ّ"
_SUKUN = "ْ"
_HARAKAT = set("ًٌٍَُِّْٰ")

# Separable proclitics stripped from the front of the stem (single-letter clitics).
_PROCLITICS = set("وفبكلس")

# The mīzān targets: ف ع ل, plus a repeated ل for quadriliteral roots (فَعْلَل).
_TARGETS = ["ف", "ع", "ل", "ل"]  # ف ع ل ل

# باب (verb form) canonical patterns. QAC marks forms II–XII in `verb_form`; form I is
# unmarked (a verb with no `verb_form`).
_VERB_BAB_AR = {
    "I": "فَعَلَ",              # فَعَلَ
    "(II)": "فَعَّلَ",     # فَعَّلَ
    "(III)": "فَاعَلَ",    # فَاعَلَ
    "(IV)": "أَفْعَلَ",  # أَفْعَلَ
    "(V)": "تَفَعَّلَ",  # تَفَعَّلَ
    "(VI)": "تَفَاعَلَ",  # تَفَاعَلَ
    "(VII)": "اِنْفَعَلَ",  # اِنْفَعَلَ
    "(VIII)": "اِفْتَعَلَ",  # اِفْتَعَلَ
    "(IX)": "اِفْعَلَّ",  # اِفْعَلَّ
    "(X)": "اِسْتَفْعَلَ",  # اِسْتَفْعَلَ
    "(XI)": "اِفْعَالَّ",  # اِفْعَالَّ
    "(XII)": "اِفْعَوْعَلَ",  # اِفْعَوْعَلَ
}


def _is_letter(ch: str) -> bool:
    return ch not in _HARAKAT and unicodedata.category(ch) != "Mn"


def _fold(ch: str) -> str:
    """Fold surface letter variants so a radical matches its stored (normalized) form.

    QAC stores roots with hamza folded onto alif (سأل → سال, نشأ → نشا), so the
    surface hamza forms must fold the same way for the in-order match to succeed.
    """
    if ch in "أإآٱ":  # أ إ آ ٱ → ا
        return "ا"
    if ch == "ة":  # ة → ت
        return "ت"
    if ch == "ى":  # ى → ي
        return "ي"
    return ch


def _tokenize(text: str) -> list[list]:
    """Split a vocalized string into `[letter, [diacritics...]]` groups."""
    out: list[list] = []
    for ch in text:
        if _is_letter(ch):
            out.append([ch, []])
        elif out:
            out[-1][1].append(ch)
    return out


def _strip_proclitics(groups: list[list], segments: list[str]) -> list[list]:
    """Drop leading separable proclitics (article ال + و/ف/ب/ك/ل/س), guided by the
    number of QAC PREFIX segments. The article's sun-letter assimilation shadda on the
    following stem letter is removed (it is the assimilated ل, not a doubled radical)."""
    n_prefix = segments.count("PREFIX")
    i = 0
    stripped = 0
    while stripped < n_prefix and i < len(groups):
        letter = groups[i][0]
        # definite article ال : consume ا + ل, normalise sun-letter shadda
        if letter == "ا" and i + 1 < len(groups) and groups[i + 1][0] == "ل":
            i += 2
            stripped += 1
            if i < len(groups) and _SHADDA in groups[i][1]:
                groups[i][1] = [d for d in groups[i][1] if d != _SHADDA]
            continue
        if letter in _PROCLITICS:
            i += 1
            stripped += 1
            continue
        break
    return groups[i:]


def _vocalized_surface(surah: int, ayah: int, word: int) -> str | None:
    """The fully-vocalized surface of the word from the aligned chakl verse text."""
    rec = word_index().get(f"{surah}:{ayah}:{word}")
    entry = chakl_by_ref().get((surah, ayah))
    if not rec or not entry:
        return None
    text = entry.get("text", "")
    start = rec.get("chakl_char_start", 0)
    end = rec.get("chakl_char_end", 0)
    if end <= start:
        return None
    return text[start:end]


_SEGMENT_TYPE_AR = {"PREFIX": "بادئة", "STEM": "جذع", "SUFFIX": "لاحقة"}
_TATWIL = "ـ"  # U+0640, appended to the article for readability: الـ
_ARTICLE_DISPLAY = "ال" + _TATWIL


def _strip_trailing_mark(groups: list[list]) -> list[list]:
    """Drop one trailing ḥarakah/sukūn (not shadda) from the last letter of a segment
    so a segment reads as its pattern, not its boundary/iʿrāب vowel (رَحِيمِ → رَحِيم)."""
    if groups and groups[-1][1]:
        diac = groups[-1][1]
        if diac[-1] in _HARAKAT and diac[-1] != _SHADDA:
            groups[-1] = [groups[-1][0], diac[:-1]]
    return groups


def segment_breakdown(record: dict, ref: str) -> list[dict]:
    """The البنية الصرفية breakdown: the vocalized TEXT of each QAC segment + its
    Arabic type, in reading order (prefix → stem → suffix, i.e. right → left).

    Each entry is `{text, type_ar}`. The segmentation and letter boundaries come
    verbatim from QAC (`segments_detail`); the vocalization is taken from the aligned
    chakl surface (QAC's per-segment vocalization is partial), sliced at those letter
    boundaries. The definite article is shown as «الـ» (with tatwīl) and its sun-letter
    assimilation shadda is removed from the following stem. Falls back to the raw QAC
    per-segment text when there is no aligned surface or the letter counts disagree.
    """
    detail = record.get("segments_detail") or []
    if not detail:
        return []

    def _fallback() -> list[dict]:
        out = []
        for seg in detail:
            raw = seg.get("uthmani", "")
            if not raw:
                continue
            typ = seg.get("type", "")
            text = _ARTICLE_DISPLAY if typ == "PREFIX" and _norm_article(raw) else raw
            out.append({"text": text, "type_ar": _SEGMENT_TYPE_AR.get(typ, typ)})
        return out

    try:
        surah, ayah, word = (int(p) for p in ref.split(":"))
    except (ValueError, AttributeError):
        return _fallback()
    surface = _vocalized_surface(surah, ayah, word)
    if not surface:
        return _fallback()

    groups = _tokenize(surface)
    counts = [sum(1 for c in seg.get("uthmani", "") if _is_letter(c)) for seg in detail]
    if sum(counts) != len(groups):
        return _fallback()

    out: list[dict] = []
    i = 0
    for seg, n in zip(detail, counts):
        chunk = [list(g) for g in groups[i:i + n]]
        i += n
        typ = seg.get("type", "")
        letters = "".join(_fold(g[0]) for g in chunk)
        if typ == "PREFIX" and letters == "ال":
            # sun-letter assimilation: the shadda on the next segment's first letter is
            # the assimilated ل, not a stem gemination — drop it from the stem display.
            if i < len(groups) and _SHADDA in groups[i][1]:
                groups[i] = [groups[i][0], [d for d in groups[i][1] if d != _SHADDA]]
            text = _ARTICLE_DISPLAY
        else:
            text = "".join(l + "".join(d) for l, d in _strip_trailing_mark(chunk))
        out.append({"text": text, "type_ar": _SEGMENT_TYPE_AR.get(typ, typ)})
    return out


def _norm_article(raw: str) -> bool:
    """True when a raw prefix token is the definite article ال (any alif variant)."""
    return "".join(_fold(c) for c in raw if _is_letter(c)) == "ال"


def verb_bab(pos: str | None, verb_form: str | None, root: str | None = None) -> str | None:
    """The باب (canonical verb-form pattern, e.g. فَعَلَ) for a verb, else None.

    Form I is unmarked in QAC (a verb with no `verb_form`). A quadriliteral root with
    no `verb_form` is the base rubāʿī pattern فَعْلَلَ (not the triliteral فَعَلَ)."""
    if pos != "V":
        return None
    form = (verb_form or "").strip()
    if not form:
        return "فَعْلَلَ" if root and len(root) == 4 else _VERB_BAB_AR["I"]  # فَعْلَلَ / فَعَلَ
    return _VERB_BAB_AR.get(form)


def compute_mizan(record: dict, ref: str) -> dict:
    """Assemble the mīzān level for a word record at `ref` ("surah:ayah:word").

    Returns `{available, wazn, verified, bab}`:
      - `available`: False when there is no root or no aligned vocalized surface.
      - `wazn`: the projected mīzān string (e.g. «يَفْعَل», «فَعَال»).
      - `verified`: True when every radical matched in order (exact projection) and
        the root is not geminated; False for hollow/geminate/irregular surfaces
        (rendered as an heuristic «اجتهادي» hint, outside the «معطى محقّق» badge).
      - `bab`: the canonical verb-form pattern for verbs (فَعَلَ / فَعَّلَ / …), else None.
    """
    root = record.get("root")
    bab = verb_bab(
        record.get("pos"),
        (record.get("features", {}) or {}).get("verb_form"),
        root,
    )
    if not root:
        return {"available": False, "wazn": None, "verified": False, "bab": bab}

    try:
        surah, ayah, word = (int(p) for p in ref.split(":"))
    except (ValueError, AttributeError):
        return {"available": False, "wazn": None, "verified": False, "bab": bab}

    surface = _vocalized_surface(surah, ayah, word)
    if not surface:
        return {"available": False, "wazn": None, "verified": False, "bab": bab}

    segments = record.get("segments", []) or []
    groups = _strip_proclitics(_tokenize(surface), segments)

    radicals = list(root)
    targets = _TARGETS[: len(radicals)]
    out: list[str] = []
    ptr = 0
    matched = 0
    for letter, diacritics in groups:
        if ptr < len(radicals) and _fold(letter) == _fold(radicals[ptr]):
            out.append(targets[ptr] + "".join(diacritics))
            ptr += 1
            matched += 1
        else:
            out.append(letter + "".join(diacritics))

    verified = matched == len(radicals) and ptr == len(radicals)
    # Geminated roots (last two radicals identical) merge under a shadda on the
    # surface, so the projection is ambiguous — mark heuristic.
    if len(radicals) >= 2 and radicals[-1] == radicals[-2]:
        verified = False

    wazn = "".join(out)
    # Drop the single trailing inflectional mark (iʿrāب ḥarakah / sukūn) on the last
    # radical so the mīzān shows the pattern, not the sentence-position case — but only
    # when no pronoun suffix follows (then the trailing mark belongs to the suffix).
    if "SUFFIX" not in segments and wazn and wazn[-1] in _HARAKAT and wazn[-1] != _SHADDA:
        wazn = wazn[:-1]

    return {"available": bool(wazn), "wazn": wazn, "verified": verified, "bab": bab}
