"""
synthesis_template.py — Deterministic Arabic synthesis for the Lisan feature.

This replaces the former LLM synthesis step. A local model (qwen2.5:7b) both
corrupted tokens (a Latin fragment injected mid-word, e.g. `الدفGdańskية`) and
generated ungrounded prose that contradicted the attested root sense. For a
Quranic tool a fluent-but-false reading is worse than a plain one, so the
paragraph is now composed deterministically from the per-letter data — no model,
no network, no language branching.

`render_synthesis` is a PURE function. It states only what the data says: it
chains the supplied per-letter Arabic meanings in root order and presents the
union of their keywords as an emergent image. It never asserts a "core meaning"
that is not a concatenation of the letter meanings, and it always carries a
caveat that this is an interpretive letter-reading, not a lexical definition.

Arabic is the only output language; all user-facing strings are Arabic, all code
and comments are English (project rule).
"""
from __future__ import annotations

# The whole paragraph, filled from the letters. Arabic punctuation throughout.
_TEMPLATE = (
    "يُقرأ الجذر «{root}» بتتابع حروفه: {seq}. "
    "ويتحصّل من هذا التتابع صورةٌ عامة تجمع بين: {keywords}.\n"
    "وهذه قراءةٌ تأويليةٌ لدلالات الحروف، لا تعريفًا معجميًّا، "
    "وقد تخالف المعنى المُثبَت في المعاجم."
)

# One clause per root letter, chained in order.
_SEQ_JOIN = "؛ ثم "
# The de-duplicated keyword union.
_KEYWORDS_JOIN = "، "


def _name_of(letter: dict) -> str:
    """The letter's Arabic name. Reads the pipeline's describe() key `name`
    (Arabic-only now) or the raw dataset field `name_ar` if passed directly."""
    return (letter.get("name") or letter.get("name_ar") or "").strip()


def _meaning_of(letter: dict) -> str:
    """The letter's interpretive Arabic meaning (describe() `meaning`, i.e. the
    dataset's `abbas_meaning_ar`)."""
    return (letter.get("meaning") or letter.get("abbas_meaning_ar") or "").strip()


def _keywords_of(letter: dict) -> list[str]:
    """The letter's Arabic keywords as a list. describe() already returns a list
    under `keywords`; tolerate a raw ';'-separated `abbas_keywords_ar` string."""
    kws = letter.get("keywords")
    if kws is None:
        kws = letter.get("abbas_keywords_ar", "")
    if isinstance(kws, str):
        kws = [part.strip() for part in kws.split(";")]
    return [k.strip() for k in kws if k and k.strip()]


def render_synthesis(word: str, root: str, letters: list[dict]) -> str:
    """Compose the Lisan reading paragraph deterministically, in Arabic.

    `letters` is the ordered per-letter data (the pipeline's describe() output),
    one entry per root letter — so roots of any length (triliteral, quadriliteral)
    render every letter, nothing is hardcoded to three.

    Three parts:
      1. التتابع     — one clause per root letter, in order: glyph, name, meaning.
      2. الصورة المركّبة — the de-duplicated union of the letters' keywords.
      3. التنبيه     — the interpretive-not-lexical caveat (in the template tail).

    `word` is accepted for signature stability / future use; the reading is of
    the root's letters, so it does not appear in the current template.
    """
    seq_clauses: list[str] = []
    keywords: list[str] = []  # order-preserving; de-duplicated below
    for letter in letters:
        glyph = (letter.get("letter") or "").strip()
        name = _name_of(letter)
        meaning = _meaning_of(letter)
        seq_clauses.append(f"{glyph} ({name}) يدلّ على {meaning}")
        keywords.extend(_keywords_of(letter))

    # De-duplicate keywords while preserving first-seen order.
    unique_keywords = list(dict.fromkeys(keywords))

    return _TEMPLATE.format(
        root=root,
        seq=_SEQ_JOIN.join(seq_clauses),
        keywords=_KEYWORDS_JOIN.join(unique_keywords),
    )


if __name__ == "__main__":
    from lisan import letter_lexicon

    letters = [letter_lexicon.describe(ch) for ch in "رحم"]
    print(render_synthesis("رحمة", "رحم", letters))
