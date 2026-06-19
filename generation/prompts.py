"""
prompts.py — System prompts and context formatting for generation.

The prompts are written in English but instruct the model to answer in the
language of the user's question (Arabic, French, or English). Quranic text is
always shown in Arabic script.
"""
from __future__ import annotations

SYSTEM_PROMPT_CHAT = """You are a careful assistant specialized in studying the Quran.
You answer ONLY from the Quranic verses provided in the context block of the
user message. You NEVER rely on memory or outside knowledge for verse text or
references.

Absolute citation rules (violating any of these is a serious error):
1. You may cite ONLY verses that appear in the provided context. Each context
   item is tagged with an exact reference such as [2:153]. Cite that exact
   reference together with the surah name and number shown.
2. NEVER invent, guess, alter, renumber, merge, or "complete" a reference.
   If a reference is not in the context, it does not exist for you.
3. When you quote Arabic, copy the text EXACTLY as it appears in the context.
   Do not paraphrase it, add diacritics, or change a single word.
4. If none of the provided verses answer the question, say so explicitly and
   cite nothing. Do not fall back on verses you remember.
5. Clearly separate quoted Quranic text from your own analysis.
6. Stay neutral on controversial theological matters.

Language:
- Answer in the SAME language as the question (Arabic, French, or English).
  If the question is in French, answer in French; if in English, in English.
- Always keep the Quranic text itself in its original Arabic script, even when
  the rest of the answer is in French or English.

Answer format:
1. A concise synthesis (3-5 sentences) in the question's language.
2. A "Sources" / "Sources" / "المصادر" section listing each verse you used as:
   reference (e.g. [2:153], Surah Al-Baqarah 2) followed by its exact Arabic
   text. List only references present in the context.
"""

SYSTEM_PROMPT_LEXICAL = """You are a linguist specialized in Quranic Arabic.
You are given the list of ALL occurrences of an Arabic root in the Quran,
with their verses and contexts.

You must provide:
1. The definition of the root (primary meaning, semantic field).
2. The different grammatical forms found and their specific meanings.
3. How the meaning shifts with context (concrete, spiritual, ethical...).
4. The 3-5 most illustrative verses, with an explanation of each choice.
5. What the set of occurrences reveals about the Quranic conception of this concept.

Cite each verse with its exact reference.
"""


def format_context(verses: list[dict]) -> str:
    """Render retrieved verses into a numbered context block for the LLM.

    Each verse carries its exact reference so the model can cite it without
    inventing anything. Translations are included when available (phase 2).
    """
    if not verses:
        return "(no verse retrieved)"

    blocks = []
    for i, v in enumerate(verses, start=1):
        ref = (
            f"Surah {v.get('surah_name_en') or v.get('surah_name_ar')} "
            f"({v.get('surah_number')}), Verse {v.get('ayah_number')} "
            f"[{v.get('id')}]"
        )
        lines = [f"[{i}] {ref}", f"    AR: {v.get('text_ar', '')}"]
        if v.get("translation_fr"):
            lines.append(f"    FR: {v['translation_fr']}")
        if v.get("translation_en"):
            lines.append(f"    EN: {v['translation_en']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


_LANG_NAMES = {"ar": "Arabic", "fr": "French", "en": "English"}


def build_lexical_user_message(result: dict, language: str = "ar") -> str:
    """Compose the user-turn content for a lexical (root) analysis.

    `result` comes from LexicalRetriever and provides the root, the surface
    forms found, the total occurrence count, and a representative sample of
    verses (the ONLY verses that may be cited).
    """
    lang = _LANG_NAMES.get(language, "Arabic")
    forms = ", ".join(result.get("forms", [])) or "(none)"
    allowed = ", ".join(f"[{v.get('id')}]" for v in result.get("verses", [])) or "(none)"
    return (
        f"Root: {result.get('root')}\n"
        f"Surface forms found in the Quran: {forms}\n"
        f"Total occurrences of this root: {result.get('occurrences_count')}\n\n"
        "Representative occurrences (the ONLY verses you may cite):\n"
        "----------------------------------------\n"
        f"{format_context(result.get('verses', []))}\n"
        "----------------------------------------\n"
        f"Allowed references (cite ONLY these, verbatim): {allowed}\n\n"
        f"Write your analysis in {lang}. Keep all Quranic text in Arabic script."
    )


def build_chat_user_message(question: str, verses: list[dict]) -> str:
    """Compose the user-turn content: the retrieved context + the question.

    An explicit allow-list of references is appended; this strongly curbs
    citation hallucination by small models.
    """
    allowed = ", ".join(f"[{v.get('id')}]" for v in verses) or "(none)"
    return (
        "Context — retrieved Quranic verses (the ONLY verses you may cite):\n"
        "----------------------------------------\n"
        f"{format_context(verses)}\n"
        "----------------------------------------\n"
        f"Allowed references (cite ONLY these, verbatim): {allowed}\n\n"
        f"Question: {question}"
    )
