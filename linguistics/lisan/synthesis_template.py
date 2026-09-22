"""
synthesis_template.py — Deterministic Arabic synthesis for the Lisan feature.

Composed from a root's ATTESTED CORE plus the letter senses that core selected —
never from letter data alone. The former version chained one frozen gloss per
letter in root order, which is how `خ-ي-ر` came to read
«القذارة والخشونة والخواء … فساد» against Ibn Fāris' «أصله العطف والميل»: nothing
in that path knew what the root meant, so nothing could prefer one sense of a
letter over another. The paragraph now OPENS on the citation it is built on, so
a reader can check the reading against the aṣl printed beside it.

No model. The Lisan synthesis was an LLM step until a local model (qwen2.5:7b)
both corrupted tokens (a Latin fragment injected mid-word, `الدفGdańskية`) and
generated fluent prose contradicting the attested sense. For a Quranic tool a
fluent-but-false reading is worse than a plain one.

`render_synthesis` is a PURE function and states only what the data says:

  * it names ONLY the letters a core actually selected a sense for. An
    `unmatched` letter is named as carrying no admitted sense and is given no
    meaning — filling that gap is exactly the behaviour being removed;
  * it never merges two cores. A root with two aṣl gets two calls and two
    paragraphs, because which aṣl convinces the reader is a scholarly judgement
    the tool presents, not one it makes;
  * it returns "" when there is no core, so the uncovered path cannot
    accidentally acquire a paragraph.

Arabic is the only output language; all code and comments are English.
"""
from __future__ import annotations

# Opening: the citation the whole reading rests on, in Ibn Fāris' own words.
# Two forms, because `gloss` is a curated CONDENSATION of `verbatim` and on a
# short aṣl the two are the same string — ظلم's «خلاف الضياء والنور» is both.
# Printing them side by side then reads as a stutter, so the gloss is dropped
# when it adds nothing. The citation is never the part dropped.
_CORE_SENTENCE = "أصلُ الجذر «{root}» عند ابن فارس هو {gloss}: «{verbatim}»."
_CORE_SENTENCE_BARE = "أصلُ الجذر «{root}» عند ابن فارس: «{verbatim}»."

# The constrained chain — one clause per letter the core actually admitted.
_READING_SENTENCE = "وعلى هذا الأصل تُقرأ حروفه: {clauses}."
_CLAUSE = "{glyph} ({name}) على {gloss}"
# A bare "؛ " and no conjunction: the clauses open on a LETTER GLYPH, and an
# Arabic "و" prefixes the following word without a space — so "؛ و" + "م" renders
# as «وم», which reads as a word rather than as the letter م being described.
_CLAUSE_JOIN = "؛ "

# Named, but deliberately given no meaning. `_NONE_MATCHED` is the whole-root
# case (ظلم's first aṣl selects nothing), where the reading is the citation and
# an admission — not an empty string, which would read as a missing feature.
# Two forms: Arabic agreement is not optional, and «للحرف: ي، ر … عليه» reads as
# a grammatical error to the reader this page is written for.
_UNMATCHED_ONE = (
    "ولم يوافق هذا الأصلَ معنًى مُثبَتٌ للحرف {letters}، فلا يُحمَّل عليه شيء."
)
_UNMATCHED_MANY = (
    "ولم يوافق هذا الأصلَ معنًى مُثبَتٌ للحروف: {letters}، فلا يُحمَّل عليها شيء."
)
_NONE_MATCHED_SENTENCE = (
    "ولم يوافق هذا الأصلَ معنًى مُثبَتٌ لأيٍّ من حروف الجذر، "
    "فلا تُبنى عليه قراءةٌ حرفية."
)
_LETTERS_JOIN = "، "

# The interpretive caveat. Travels in every paragraph, unchanged.
CAVEAT = (
    "وهذه قراءةٌ تأويليةٌ لدلالات الحروف، لا تعريفًا معجميًّا، "
    "وقد تخالف المعنى المُثبَت في المعاجم."
)


def render_synthesis(
    root: str,
    core: dict,
    letter_readings: list[dict],
    identities: list[dict] | None = None,
) -> str:
    """Compose ONE core's Arabic reading paragraph, deterministically.

    `core` is one entry of `root_cores.json` (`gloss` / `verbatim` / …).
    `letter_readings` is the selection result for that core, one entry per root
    letter, each carrying `letter`, `selected` (a sense dict or None) and
    `selection_rule`. `identities` optionally supplies the letters' Arabic names
    (the `letter_lexicon.describe()` rows, same order) — the glyph is used alone
    when a name is not available, so the paragraph never depends on the phonetic
    sheet being present.

    Returns "" when `core` is falsy: with no attested aṣl there is nothing to
    constrain the letters against, and a paragraph composed anyway would be the
    defect this module exists to remove.
    """
    if not core:
        return ""

    names = {}
    for row in identities or []:
        glyph = (row.get("letter") or "").strip()
        if glyph:
            names.setdefault(glyph, (row.get("name") or "").strip())

    clauses: list[str] = []
    unmatched: list[str] = []
    for reading in letter_readings:
        glyph = (reading.get("letter") or "").strip()
        selected = reading.get("selected")
        if not selected:
            unmatched.append(glyph)
            continue
        gloss = (selected.get("gloss_ar") or "").strip()
        if not gloss:                      # a sense with no text asserts nothing
            unmatched.append(glyph)
            continue
        name = names.get(glyph) or glyph
        clauses.append(_CLAUSE.format(glyph=glyph, name=name, gloss=gloss))

    gloss = (core.get("gloss") or "").strip()
    verbatim = (core.get("verbatim") or "").strip()
    if gloss and gloss != verbatim:
        opening = _CORE_SENTENCE.format(root=root, gloss=gloss, verbatim=verbatim)
    else:
        opening = _CORE_SENTENCE_BARE.format(root=root, verbatim=verbatim)
    parts = [opening]
    if clauses:
        parts.append(_READING_SENTENCE.format(clauses=_CLAUSE_JOIN.join(clauses)))
        if unmatched:
            template = _UNMATCHED_ONE if len(unmatched) == 1 else _UNMATCHED_MANY
            parts.append(template.format(letters=_LETTERS_JOIN.join(unmatched)))
    else:
        parts.append(_NONE_MATCHED_SENTENCE)

    return " ".join(parts) + "\n" + CAVEAT


if __name__ == "__main__":
    demo_core = {
        "gloss": "العطف والميل",
        "verbatim": "الخاء والياء والراء أصله العطف والميل، ثم يحمل عليه",
    }
    demo_readings = [
        {"letter": "خ", "selection_rule": "axis-match",
         "selected": {"gloss_ar": "الرقة والنضارة (الخاء المرققة بلا خنخنة)"}},
        {"letter": "ي", "selection_rule": "unmatched", "selected": None},
        {"letter": "ر", "selection_rule": "unmatched", "selected": None},
    ]
    print(render_synthesis("خير", demo_core, demo_readings,
                           [{"letter": "خ", "name": "الخاء"}]))
