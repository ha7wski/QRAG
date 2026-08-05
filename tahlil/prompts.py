"""
prompts.py — what the Tahlil generator is allowed to SEE, and what it is allowed to SAY.

This module is the seam where an untrusted component meets a proved gate, so it is written
from the gate backwards: everything here exists to make `tahlil/citations.py` able to reach
a verdict, never to persuade the model to behave. A prompt instruction is a request; the
validator is the guarantee (`citations.py`, module docstring). Where the two disagree the
validator wins, and the prompt's only job is to stop the model from producing output the
validator would have to refuse *for a reason that carries no information* — a mass drop
tells the operator nothing except that the prompt is broken.

Four decisions carry the module, each the answer to a measured failure mode:

  1. **HANDLES, NOT IDS.** The model is shown `[3]`, never `sigha:bab.III.mufaala@0.1.0`.
     Evidence ids are Latin-heavy by construction (kind prefixes, version tokens, page
     ranges), and the one post-check this project has already proved necessary — the
     Arabic-purity void inherited from `madar_service` — fires on Latin word-characters in
     the *rendered text*. Filling an Arabic prompt with Latin tokens the model is asked to
     copy verbatim is the cheapest possible way to induce exactly the drift that voids the
     claim. A one- or two-digit handle also survives a re-tokenization that a 30-character
     id does not.

  2. **THE BLOCK IS STAMPED, NOT ASKED FOR.** Generation is per block (tasks.md 7.3), so
     the model never writes `"block": "sarfi"` — the generator stamps it from the call it
     made. That removes a whole failure class (a claim addressed to a block that does not
     exist) at the source rather than logging it afterwards, and removes the last Latin
     *value* from the contract. `SERVICE_LOG_REASONS`'s `generator-unknown-block` stays in
     the service because the service accepts ANY generator, not because this one can trip
     it.

  3. **THE SENSE SELECTION IS A FIELD, NOT A SENTENCE TO PARSE.** A claim citing a
     multi-sense KB row must carry `sense_ar`, copied verbatim from the row. The obvious
     alternative — scan the prose for "did it enumerate or choose?" — is wrong in the
     direction that matters: the reference exemplar's own wording («ليست على بابها في
     المشاركة، بل تفيد المبالغة») names BOTH senses of the row, so any "contains ≥2 senses
     ⇒ unselected" rule drops the very claim this change exists to produce. Same principle
     as the contrast gate: take natural-language interpretation out of the trust path.

  4. **THE ABSENCE SENTENCE IS QUOTED, NEVER PARAPHRASED.** `_contrast_admissible` admits
     an unattested contrast only by finding the evidence layer's own computed sentence
     inside the claim, verbatim modulo whitespace. So the prompt hands that sentence over
     as a string to copy and says so twice. A paraphrase is a silent, total loss of the
     contrastive clause — the exemplar's «أبلغ من يُسرِعون» — with `unchecked-contrast` as
     the only trace.

WHAT THE PROMPT NEVER DOES, and this is a spec requirement, not a style choice
(`tahlil-dalali`: «The prompt carries no verse interpretation»): it never asks what the
verse means, never supplies a translation, and never invites recall. It carries the
evidence bundle's own strings and the output contract. Every sentence the model writes is
prose *over data it was handed*, which is the only sense in which تفسير القرآن بالقرآن can
be enforced by a machine rather than promised by a paragraph.

Pure stdlib: no model, no network, no fastapi. `tahlil_service` imports `PROMPT_VERSION`
and `tarkib_enabled` from here lazily, so the service keeps working when this module is
absent — and the moment it lands, every cache entry keyed on the stub version misses by
construction.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tahlil import citations  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# 1. Version — participates in the cache key (tasks.md 7.1)
# ─────────────────────────────────────────────────────────────────────────────
# Bump on ANY change to the system contract, a block brief, or the slice composition:
# all three change what the model was shown, so a cached claim produced under the old one
# is prose about a different question. The cache key carries this value precisely so the
# invalidation is automatic rather than remembered.
PROMPT_VERSION = "1.4.1"

# The verse synthesis is versioned SEPARATELY, and that separation is the point. Its prompt
# is additive: `SYSTEM_PROMPT`, every `BLOCK_TASK` brief and every word-level slice are
# untouched by it, so a word analysis cached — or a gold answer frozen — under a given
# `PROMPT_VERSION` is still an answer to the same question. Folding the two into one number
# would invalidate every word recording each time the verse brief is reworded, which costs
# hours of live model calls to re-earn nothing.
VERSE_PROMPT_VERSION = "1.0.0"

BLOCK_HURUF, BLOCK_SARFI, BLOCK_NAHWI, BLOCK_DALALI, BLOCK_TARKIB = citations.BLOCKS

# ─────────────────────────────────────────────────────────────────────────────
# 2. The تركيب kill switch (tasks.md 8.4)
# ─────────────────────────────────────────────────────────────────────────────
# Lives HERE rather than in the generator because `tahlil_service` must be able to state
# «التركيب معطّل» as the block's reason, and the service is pure stdlib — it cannot import
# a module that pulls in `ollama`. This module is the only pure-stdlib half of the
# generation layer, so it owns the switch and both sides read the same function.
TARKIB_ENV = "TAHLIL_TARKIB_ENABLED"


def tarkib_enabled() -> bool:
    """The تركيب is ON by default *within* generation, and separately switchable off.

    Default-on is deliberate and is not a weakening: `TAHLIL_GENERATION_ENABLED` already
    gates the whole prose layer off by default, so nothing is produced until an operator
    opts in. This second switch exists so a bad تركيب can be silenced without losing the
    per-level تعليل — the composition rules are the newest and least measured part of the
    gate, and the four levels beneath them are useful on their own.
    """
    return os.getenv(TARKIB_ENV, "1") == "1"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Handles
# ─────────────────────────────────────────────────────────────────────────────
# A handle the bundle does not carry becomes THIS, and the shape is chosen so the gate
# refuses it: `unknown` is not one of `citations.KINDS`, so `kind_of` returns None and the
# claim drops as `unresolved-citation` with the offending token printed in the log. The
# alternative — silently discarding an unknown handle — would let a claim that cited
# nothing real render as a claim that cited nothing at all, i.e. it would convert a
# *fabrication* into a *formatting slip* and hide it under `no-citation`.
UNKNOWN_HANDLE = "unknown:handle-{}"

# ٠١٢٣٤٥٦٧٨٩ → 0123456789, and the Extended-Arabic (Persian/Urdu) forms ۰۱۲۳۴۵۶۷۸۹ with
# them. A model writing Arabic prose reaches for Arabic-Indic digits; the handle map is
# keyed in ASCII. Folding is total and unambiguous — see `resolve_cites`.
_ARABIC_DIGITS = {**{0x0660 + i: ord("0") + i for i in range(10)},
                  **{0x06F0 + i: ord("0") + i for i in range(10)}}

# Prompt-side caps. These bound the PROMPT, never the page: the bundle keeps everything,
# and `nazair_totals` still reports the corpus figures. Stated in the prompt as a sample
# (the `madar` convention) so the model is never led to believe it sees the whole set.
_NAZAIR_IN_PROMPT = 6
_NAZAIR_IN_NAHWI = 2

# The naẓīra snippet is a window CENTRED ON THE WORD, not a prefix of the verse — and the
# first live recording is why. `verse_text[:120]` cut 3:114 at «وَيُسَارِعُونَ فِي», one word
# before «الْخَيْرَاتِ»; it cut 5:41 mid-word at «بِأَفْوَاهِهِ» and 5:52 at «فَعَسَى ال».
#
# For a verb the whole contextual reading is the complement — يسارعون **في الخيرات** against
# يسارعون **في الكفر** against يسارعون **في الإثم**. A prefix window deletes exactly that, and
# then asks the model what the word means in context: the model supplied the missing
# complement out of nothing («ويتأهبون للإيمان» against 3:114). It also showed the verse's
# OPENING, where the word usually is not, so «what does this word do here» was answered by
# summarising a verse the word had not yet appeared in.
#
# Cutting mid-word compounds it: a snippet ending in «يَعْم» or «ال» is not Arabic, and prose
# built on mangled evidence comes back mangled (a نحوي claim quoted 3:114 as «ونهى عن
# المنكر»). The window therefore snaps to whitespace, marks each elided side with «…», and
# grows FORWARD twice per backward step so the complement survives a tight budget.
_VERSE_SNIPPET = 160
_TASHKIL = "".join(chr(c) for c in
                   (*range(0x064B, 0x0653), 0x0640, 0x0670, 0x06DF, 0x06E0, 0x0653, 0x0654,
                    0x0655))

# Below this many naẓāʾir the حقل الدلالي is not asked for at all — «A thin occurrence set
# yields no field» (tahlil-dalali). Asking anyway and dropping the answer would spend a
# model call to produce a log row.
_FIELD_MIN_NAZAIR = 3


# ─────────────────────────────────────────────────────────────────────────────
# 4. The system contract
# ─────────────────────────────────────────────────────────────────────────────
# Terse and imperative, in Arabic, for the reason `madar/synthesis_prompt.py` records:
# qwen2.5:7b drifts into Latin/CJK fragments on long chatty prompts, and a drifted claim is
# voided by the purity check — so verbosity here is paid for in dropped claims.
SYSTEM_PROMPT = (
    "أنت باحثٌ لغويٌّ دقيق. تكتب تعليلًا لغويًّا لكلمةٍ قرآنية اعتمادًا **فقط** على "
    "الشواهد المرقّمة المعطاة لك، ولا شيء غيرها.\n"
    "قواعد ملزمة:\n"
    "١) أجب بمصفوفة JSON فقط، بلا أيّ نصٍّ قبلها أو بعدها، وبلا أسوار شفرة.\n"
    "٢) كلّ عنصر: "
    '{"text_ar": "...", "cites": [أرقام الشواهد], "badge": "مُولَّد" أو "تأويلي"'
    '[, "sense_ar": "..."]}\n'
    "٣) «text_ar» هو **نصّ الدعوى كاملًا**: جملةٌ مفيدةٌ تُعلِّل، لا عنوانٌ ولا لفظٌ "
    "مفرد ولا اسمُ صيغةٍ ولا نسخةٌ من نصّ الشاهد. ودعوى تكتفي بإعادة لفظ الشاهد تُحذف.\n"
    "٤) «sense_ar» ليس مكان التعليل؛ هو حقلٌ تقنيٌّ لا تضع فيه إلا المعنى المنقول "
    "حرفيًّا من الشاهد المتعدّد المعاني.\n"
    "٥) كلّ دعوى لا بدّ لها من رقم شاهدٍ واحدٍ على الأقلّ من القائمة المعطاة. "
    "ودعوى بلا شاهدٍ تُحذف، فلا تكتبها.\n"
    "٦) لا تستعمل الوسم «محقّق» أبدًا؛ فهو للمعطيات المقروءة من المدوّنة لا للمولَّد.\n"
    "٧) اكتب بالعربية الفصحى وحدها: لا حرفَ لاتينيًّا ولا صينيًّا ولا علامةَ ترقيمٍ "
    "أعجميّة (نحو «。») في نصّ الدعوى، ولا ترقيمَ الشواهد داخل النصّ.\n"
    "٨) لا تُضِف معلومةً من خارج الشواهد: لا تفسيرَ للآية، ولا سببَ نزول، ولا نقلَ عن "
    "مفسِّر، ولا اشتقاقًا لم يُعطَ لك. أنت تُعلِّل الصيغة واللفظ، لا تشرح مراد الآية.\n"
    "٩) إن كان للشاهد معانٍ متعدّدة، فاختر واحدًا منها، وانسخه حرفيًّا في الحقل "
    "«sense_ar»، واذكر رقم الشاهد الذي رجّح هذا المعنى مع رقم الصيغة.\n"
    "١٠) الأرقام في «cites» أرقامُ الشواهد المرقّمة أعلاه فقط، بالصورة التي تراها "
    "بين المعقوفين (1، 2، 3…)، لا بالأرقام الهنديّة، وليست أرقامَ الآيات ولا مواضعَها.\n"
    "١١) اجعل كلّ دعوى جملةً واحدةً موجزة، ولا تُكرّر دعوى بنصّها. "
    "ولا تُعِد ما في الشواهد؛ علِّله.\n"
    "\nمثالٌ على الشكل المطلوب — من جذرٍ آخر، لا تنقل منه لفظًا:\n"
    '{"text_ar": "اختيارُ صيغة الاستفعال هنا يفيد طلبَ الفعل وتكلّفَه لا وقوعَه، '
    'فناسب مقامَ المبالغة", "cites": [3, 5], "badge": "مُولَّد", "sense_ar": "طلب الفعل"}\n'
    "لاحِظ: «text_ar» جملةٌ تامّةٌ تُعلِّل وتُجيب «لماذا»، و«sense_ar» لفظٌ منقولٌ من "
    "الشاهد وحده. ولو كان «text_ar» لفظًا مثل «يستفعلون» أو «يستفعلون في الأمر» "
    "لكانت الدعوى ساقطةً، لأنّها تسمية لا تعليل."
)

# The worked example above is itself a fabrication risk: it is fluent Arabic the model has
# been shown, and `check_quotation` compares a claim only against the EVIDENCE lines, so a
# claim that copies the example would sail through the gate wearing real citations. The
# example is worth that risk — an abstract field contract did not land on qwen2.5:7b twice
# running, and its second failure emptied four blocks — but the hole it opens is closed by
# `generator.check_prompt_echo`, which refuses any claim containing this span.
EXAMPLE_CLAIM_AR = ("اختيارُ صيغة الاستفعال هنا يفيد طلبَ الفعل وتكلّفَه لا وقوعَه، "
                    "فناسب مقامَ المبالغة")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Per-block briefs — the وصف is already on the page; this asks for the تعليل
# ─────────────────────────────────────────────────────────────────────────────
# Each brief names the ONE thing the block adds over the deterministic layer, because the
# facts (الجذر, الوزن, الإعراب, العلامة, النظائر, صفات الحروف, نصّ الأصل) are rendered
# beneath these claims already, badged محقّق. A model asked to restate them produces
# duplicates that no gate rule refuses — they cite correctly — and the reader meets the
# same sentence twice, once verified and once not.
BLOCK_TASK = {
    BLOCK_HURUF: (
        "المطلوب: خلاصةٌ واحدةٌ للمعنى المحوري للجذر، مبنيّةٌ على دلالات حروفه "
        "بترتيبها في الجذر.\n"
        "- اذكر في «cites» أرقامَ حروف الجذر **كلَّها** دون استثناء؛ فخلاصةٌ تترك حرفًا "
        "تُحذف.\n"
        "- ثمّ اعرِض الخلاصة على الاستعمال القرآني: إن عضّدها أصلٌ معجميٌّ أو نظيرةٌ "
        "معطاةٌ لك، فاذكر رقمها في «cites» أيضًا.\n"
        "- الوسم: «تأويلي»."
    ),
    BLOCK_SARFI: (
        "المطلوب: تعليلُ اختيار هذه الصيغة.\n"
        "- ما المعنى الذي تفيده الصيغة في هذا الموضع؟ اختره من معاني الصيغة المعطاة، "
        "وانسخه في «sense_ar»، واستشهد بنظيرةٍ أو بأثرٍ نحويٍّ من الآية يرجّحه.\n"
        "- ثمّ المقابلة: بمَ تكون هذه الصيغة أبلغَ من الصيغة المقابلة المعطاة؟ "
        "دعوًى واحدةٌ لكلّ مقابلة، ولا تجمع مقابلتين في دعوى.\n"
        "- الوسم: «مُولَّد» للمعنى المُسنَد إلى نظيرة، و«تأويلي» للمقابلة."
    ),
    BLOCK_NAHWI: (
        "المطلوب: ماذا يضيف هذا الموقعُ الإعرابيُّ وهذا الزمنُ إلى المعنى؟\n"
        "- لا تُعِد الإعراب؛ فهو مذكورٌ محقَّقًا. علِّل أثرَه: ما الذي أفاده وقوعُ الكلمة "
        "في هذا الموقع، وما الذي أفاده الزمن؟\n"
        "- استشهد برقم الموقع الإعرابي أو رقم الزمن؛ فعليهما مدارُ الدعوى.\n"
        "- النظائر هنا للتعضيد وحده: لا تشرحها، ولا تحكِ مضمونها، ولا تنقل منها لفظًا.\n"
        "- الوسم: «مُولَّد»."
    ),
    BLOCK_DALALI: (
        "المطلوب: دعوَيان لا أكثر — المعنى المحوري، ثمّ المعنى السياقي.\n"
        "- المعنى المحوري: قراءةٌ في الأصل المعجمي المعطى (إن وُجد) مع دلالات الحروف. "
        "وإن لم يُعطَ أصلٌ، فصرّح بأنّ المعنى مبنيٌّ على الحروف والاستعمال وحدهما، "
        "والوسم حينئذٍ «تأويلي».\n"
        "- المعنى السياقي: دعوًى واحدةٌ تجمع النظائر كلَّها: ما الذي يشترك فيه اللفظ "
        "حيثما وقع، وبمَ تعلَّق؟ واستشهد بنظيرتين على الأقلّ.\n"
        "- لا تشرح نظيرةً نظيرةً، ولا تُلخّص آيةً؛ لا تُفسّر الآية، والدعوى عن اللفظ "
        "لا عن الآية. ودعوى تقوم على نظيرةٍ واحدةٍ تُحذف.\n"
        "- الوسم: «مُولَّد» لما أُسنِد إلى نظيرةٍ أو إلى الأصل."
    ),
    BLOCK_TARKIB: (
        "المطلوب: أطروحةٌ واحدةٌ تجمع ما تقدّم — القيمة الزائدة التي لا تتحقّق لو قيل "
        "غيرُ هذا اللفظ.\n"
        "- لا بدّ أن تستشهد بأرقامٍ من **مستويين مختلفين على الأقلّ** من المستويات "
        "المعطاة؛ وأطروحةٌ تستند إلى مستوًى واحدٍ تُحذف.\n"
        "- لا تُدخِل معلومةً جديدةً ليست في الدعاوى المعطاة.\n"
        "- دعوًى واحدةٌ أو دعويان لا أكثر. الوسم: «تأويلي»."
    ),
}

# The one line appended IN CODE — never asked of the model — when a letters synthesis was
# not corroborated by usage. tasks.md 7.6: «mark it weak with an explicit statement». The
# statement has to be a guarantee, and a sentence the model was *asked* to add is a
# request; a sentence the code appends is the thing itself.
WEAK_SYNTHESIS_SUFFIX = " — ولم يَعضُد هذه الخلاصةَ أصلٌ معجميٌّ ولا نظيرةٌ من الاستعمال القرآني."

# The label a cross-lemma naẓīr carries in the prompt (tahlil-dalali: «Cross-lemma evidence
# is labelled»). The claim's own statement of it is the model's job; making the input
# unlabelled would make that impossible rather than merely unlikely.
_CROSS_LEMMA_TAG = "من لفظٍ آخر من الجذر"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Evidence lines — one per item, Arabic, self-describing
# ─────────────────────────────────────────────────────────────────────────────
def _letter_line(entry: dict) -> str:
    sifat = entry.get("sifat") or {}
    dalala = entry.get("dalala") or {}
    traits = "، ".join(t for t in (sifat.get("jahr_hams"), sifat.get("shidda_rakhawa"))
                       if t)
    extra = "، ".join(m for m in (sifat.get("sifat_mumayyiza") or []) if m)
    if extra:
        traits = f"{traits}، وفيها {extra}" if traits else f"فيها {extra}"
    line = (f"حرف «{entry.get('letter', '')}» ({entry.get('position', '')} الجذر) — "
            f"{traits}؛ دلالته: {dalala.get('core_meaning', '')}")
    # The position note is offered ONLY when the dataset carries one (د, ذ, ط carry none):
    # the framework reads a letter's sense off its slot, so lending it a neighbour's note
    # would put a fabricated reading behind a real citation.
    if entry.get("has_position_notes") and dalala.get("position_notes"):
        line += f"؛ وفي هذا الموضع: {dalala['position_notes']}"
    return line


def _undiacritic(token: str) -> str:
    return "".join(c for c in token if c not in _TASHKIL)


def _locate(tokens: list[str], index: int, word: str) -> int:
    """Index of `word` among `tokens` — by position first, then by matching.

    The recorded position is trusted only when it actually holds the word. It usually
    does, but `quran_chakl.csv` prepends the Basmala to āya 1, which shifts every index in
    that āya by four; a window centred on the wrong token would be a *plausible* snippet of
    the wrong part of the verse, which is worse than an obvious failure. Matching the
    vocalized surface — then the bare form, since the naẓīra may carry a clitic the corpus
    token does not — recovers the right slot, and an unmatched word falls back to the
    recorded position clamped into range rather than raising.
    """
    i = index - 1
    if 0 <= i < len(tokens) and word and tokens[i] == word:
        return i
    if word:
        for j, tok in enumerate(tokens):
            if tok == word:
                return j
        bare = _undiacritic(word)
        for j, tok in enumerate(tokens):
            if _undiacritic(tok) == bare:
                return j
    return min(max(i, 0), max(len(tokens) - 1, 0))


def _focus_window(text: str, index: int, word: str, budget: int = _VERSE_SNIPPET) -> str:
    """A whole-word window of `text` centred on `word`, at most `budget` characters.

    Grows forward twice per backward step: for a verb the complement carries the reading,
    so when the budget forces a choice, what FOLLOWS the word is kept.
    """
    tokens = text.split()
    if not tokens:
        return ""
    joined = " ".join(tokens)
    if len(joined) <= budget:
        return joined
    lo = hi = _locate(tokens, index, word)
    used = len(tokens[lo])
    while True:
        grew = False
        for _ in range(2):
            if hi + 1 < len(tokens) and used + 1 + len(tokens[hi + 1]) <= budget:
                hi += 1
                used += 1 + len(tokens[hi])
                grew = True
        if lo > 0 and used + 1 + len(tokens[lo - 1]) <= budget:
            lo -= 1
            used += 1 + len(tokens[lo])
            grew = True
        if not grew:
            break
    out = " ".join(tokens[lo:hi + 1])
    if lo > 0:
        out = f"… {out}"
    if hi + 1 < len(tokens):
        out = f"{out} …"
    return out


def _nazir_line(entry: dict) -> str:
    text = _focus_window(entry.get("verse_text") or "",
                         entry.get("word") or 0,
                         entry.get("word_vocalized") or "")
    tag = "" if entry.get("same_lemma") else f" [{_CROSS_LEMMA_TAG}: {entry.get('lemma_display') or ''}]"
    return (f"نظيرة {entry.get('ref', '')} ({entry.get('surah_name_ar', '')}) — "
            f"«{entry.get('word_vocalized', '')}»{tag}: {text}")


def _sigha_line(row: dict) -> str:
    senses = [s.get("sense_ar", "") for s in (row.get("senses") or []) if s.get("sense_ar")]
    head = f"صيغة «{row.get('key', '')}»"
    if len(senses) > 1:
        body = "؛ ".join(f"({i}) {s}" for i, s in enumerate(senses, 1))
        # The instruction is repeated at the point of use, not only in the system contract:
        # an unanchored selection costs the claim its مُولَّد badge (§5.3), and the log row
        # that records it (`sense-selection-unanchored`) is the ONE downgrade in the gate.
        return (f"{head} — معانٍ متعدّدة: {body}. اختر واحدًا وانسخه في «sense_ar»، "
                f"واذكر معه رقمَ الشاهد الذي رجّحه.")
    return f"{head} — دلالتها: {senses[0] if senses else ''}."


def _contrast_line(entry: dict) -> str:
    target = (entry.get("target") or {}).get("bab", "")
    line = (f"مقابلة: «{entry.get('bab', '')}» في هذا الموضع تقابلها «{target}» — "
            f"{entry.get('rationale_ar', '')}")
    if entry.get("attested"):
        refs = "، ".join((entry.get("attested_refs") or [])[:3])
        return line + (f" وهذه الصيغة **واردة** من هذا الجذر في {refs}؛ "
                       f"فلا تقل إنّها لم ترد." if refs else "")
    scope = (entry.get("absence_scope_ar") or "").strip()
    if not scope:
        return line
    # Verbatim or nothing: `_contrast_admissible` finds this exact sentence or refuses the
    # claim. Said twice, and given as a quoted string, because a paraphrase here is a total
    # and silent loss of the contrastive clause.
    return line + (f"\n    ⟵ انسخ هذه الجملة **حرفيًّا** داخل نصّ الدعوى، بلا تغيير: "
                   f"«{scope}»")


def _maqayis_line(maqayis: dict) -> str:
    asl = maqayis.get("asl_text")
    if isinstance(asl, list):
        asl = " ".join(a for a in asl if a)
    return f"أصل الجذر «{maqayis.get('root', '')}» عند ابن فارس: «{asl or ''}»"


_QAC_LABELS = {"relation": "الموقع الإعرابي", "head_ref": "المتعلَّق"}

# The four Zero-Theory relations, when that layer is present (`add-nahwi-zero-relations`).
ZERO_FIELDS = ("zero_relation", "zero_role", "zero_reason", "zero_verified")


def zero_info(bundle: dict) -> dict | None:
    """The Zero relation for this word, or None when the layer is absent (tasks.md 7.5).

    The layer ships in a separate change that is **not implemented**, so this returns None
    for every word today and the نحوي prompt simply carries no relation line — «omit it and
    log `zero-layer-absent`». It is read through one accessor rather than inlined so that
    both branches are reachable from a test with a synthetic fiche: forward-compatible code
    no test can exercise is code a reader believes and nobody has checked.

    `zero_verified` is carried through and shown as «غير محقّقة» when false. That labelling
    is for the model's benefit, not for the badge: a generated claim can never be محقّق
    under any circumstance (the gate drops one that asks), so an unverified minted relation
    is already unable to reach the page as a verified fact.
    """
    nahwi = ((bundle.get("fiche") or {}).get("nahwi") or {})
    relation = nahwi.get("zero_relation")
    if not relation:
        return None
    return {f: nahwi.get(f) for f in ZERO_FIELDS}


def _qac_line(item: dict, zero: dict | None = None) -> str:
    label = _QAC_LABELS.get(item.get("field", ""), item.get("field", ""))
    line = f"من إعراب الآية — {label}: {item.get('value_ar', '')}"
    if zero and item.get("field") == "relation":
        line += f"؛ والعلاقة: {zero.get('zero_relation', '')}"
        if zero.get("zero_role"):
            line += f" ({zero['zero_role']})"
        if zero.get("zero_reason"):
            line += f" — السبب: {zero['zero_reason']}"
        if not zero.get("zero_verified"):
            line += " [غير محقّقة]"
    return line


# ─────────────────────────────────────────────────────────────────────────────
# 7. Slices — what each block may cite
# ─────────────────────────────────────────────────────────────────────────────
def _sigha_rows(bundle: dict, key_types: tuple[str, ...]) -> list[dict]:
    return [r for r in (bundle.get("sigha_rows") or []) if r.get("key_type") in key_types]


def _qac_entries(bundle: dict) -> list[dict]:
    return [i for i in (bundle.get("items") or {}).values() if i.get("kind") == "qac"]


def _entry(cite_id: str, line: str) -> dict:
    return {"cite_id": cite_id, "line_ar": line}


def evidence_slice(bundle: dict, block: str) -> list[dict]:
    """The evidence entries block `block` may cite, in prompt order.

    Slices are **narrow on purpose**. A model shown everything cites everything, and the
    result passes the gate — every id resolves — while saying nothing: a نحوي claim citing
    a letter row is formally anchored and substantively empty, and no validator can tell
    the difference. Narrowing the input is the only place that distinction can be made.

    Two slices deliberately overlap. The aspect row (مضارع → التجدّد والاستمرار) is in both
    صرفي and نحوي because the exemplar reads it in the نحوي block («المضارع يفيد التجدّد»)
    while it is morphological data; and the naẓāʾir reach four blocks because a naẓīr is
    this project's only *empirical* anchor — it is what makes a selection مُولَّد rather
    than تأويلي (`CORPUS_DISAMBIGUATORS`), so withholding it from صرفي would guarantee the
    downgrade the gate exists to report only when it is real.
    """
    letters = bundle.get("letters") or []
    nazair = bundle.get("nazair") or []
    maqayis = bundle.get("maqayis") or {}
    entries: list[dict] = []

    if block == BLOCK_HURUF:
        # Every letter, uncapped: a synthesis citing fewer letters than the root has is
        # dropped, so a cap here would manufacture that failure.
        seen: set[str] = set()
        for e in letters:
            if e["cite_id"] not in seen:
                seen.add(e["cite_id"])
                entries.append(_entry(e["cite_id"], _letter_line(e)))
        if maqayis.get("cite_id"):
            entries.append(_entry(maqayis["cite_id"], _maqayis_line(maqayis)))
        entries += [_entry(n["cite_id"], _nazir_line(n)) for n in nazair[:_NAZAIR_IN_PROMPT]]

    elif block == BLOCK_SARFI:
        entries += [_entry(r["cite_id"], _sigha_line(r))
                    for r in _sigha_rows(bundle, ("bab", "aspect"))]
        entries += [_entry(c["cite_id"], _contrast_line(c))
                    for c in (bundle.get("contrast") or []) if "attested" in c]
        entries += [_entry(n["cite_id"], _nazir_line(n)) for n in nazair[:_NAZAIR_IN_PROMPT]]
        entries += [_entry(f"qac:{i['field']}@{i['ref']}", _qac_line(i))
                    for i in _qac_entries(bundle)]

    elif block == BLOCK_NAHWI:
        # The Zero relation rides on the الموقع الإعرابي entry rather than becoming a
        # numbered شاهد of its own: it has no evidence id (it is a fiche field, not a
        # bundle item), so a separate line would be content the model may read and cannot
        # cite — and everything readable must be citable, or the slice stops meaning
        # «these and only these».
        zero = zero_info(bundle)
        entries += [_entry(f"qac:{i['field']}@{i['ref']}", _qac_line(i, zero))
                    for i in _qac_entries(bundle)]
        entries += [_entry(r["cite_id"], _sigha_line(r)) for r in _sigha_rows(bundle, ("aspect",))]
        entries += [_entry(n["cite_id"], _nazir_line(n)) for n in nazair[:_NAZAIR_IN_NAHWI]]

    elif block == BLOCK_DALALI:
        if maqayis.get("cite_id"):
            entries.append(_entry(maqayis["cite_id"], _maqayis_line(maqayis)))
        entries += [_entry(n["cite_id"], _nazir_line(n)) for n in nazair[:_NAZAIR_IN_PROMPT]]
        seen = set()
        for e in letters:
            if e["cite_id"] not in seen:
                seen.add(e["cite_id"])
                entries.append(_entry(e["cite_id"], _letter_line(e)))

    return entries


def slice_lines(bundle: dict, block: str) -> dict[str, str]:
    """`{cite_id: line_ar}` for ONE block — **the text that block's model call was shown**.

    Per block, not per bundle, and the distinction is load-bearing: `generator`'s quotation
    check compares a claim against the evidence it could have copied from, and drawing that
    from every block's slice would make the نحوي check depend on the الحروف slice. A single
    malformed letter entry would then fail all five levels instead of the two that actually
    read the letters — re-coupling exactly what tasks.md 7.3 isolates. A block's claims can
    only cite what that block was offered anyway, so the narrow map is also the complete
    one.
    """
    return {e["cite_id"]: e["line_ar"] for e in evidence_slice(bundle, block)}


def evidence_lines(bundle: dict) -> dict[str, str]:
    """`{cite_id: line_ar}` across the four levels — the تركيب's view, and only its view.

    The تركيب composes all four levels by nature, so it is the one consumer entitled to a
    bundle-wide map; every other caller wants `slice_lines`.
    """
    return {cid: line
            for b in (BLOCK_HURUF, BLOCK_SARFI, BLOCK_NAHWI, BLOCK_DALALI)
            for cid, line in slice_lines(bundle, b).items()}


def tarkib_slice(bundle: dict, level_claims: dict[str, list[dict]]) -> list[dict]:
    """The تركيب may cite ONLY what a surviving level claim already stood on.

    `validate_tarkib` reads level membership off the evidence ids the level claims cite,
    and requires two distinct levels. Offering the تركيب the whole bundle would let it
    anchor on evidence no level used — formally resolvable, and `tarkib-unsupported-by-
    levels` by construction. The slice is therefore built from `level_claims`, not from the
    bundle, and the bundle is consulted only for each id's display line.
    """
    lines = evidence_lines(bundle)
    out: list[dict] = []
    seen: set[str] = set()
    for block in (BLOCK_HURUF, BLOCK_SARFI, BLOCK_NAHWI, BLOCK_DALALI):
        for claim in level_claims.get(block) or []:
            for cite in claim.get("cites") or []:
                if cite in seen or cite not in lines:
                    continue
                seen.add(cite)
                out.append(_entry(cite, lines[cite]))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 8. The user turn
# ─────────────────────────────────────────────────────────────────────────────
def _header(bundle: dict) -> list[str]:
    """The word under analysis, and nothing about what its verse means.

    The surface is read from `surface_vocalized` — chakl, never the QAC `uthmani` field,
    which for the pinned word is «يُسرِعُون» (no alif) and would put a form the reader
    never sees at the head of every prompt about it.
    """
    fiche = bundle.get("fiche") or {}
    sarfi = fiche.get("sarfi") or {}
    lines = [f"الكلمة: «{bundle.get('surface_vocalized', '')}» — الموضع {bundle.get('ref', '')}"]
    root = sarfi.get("root_display") or sarfi.get("root")
    if root:
        lines.append(f"الجذر: {root}")
    return lines


def build_user_message(bundle: dict, block: str, *,
                       level_claims: dict[str, list[dict]] | None = None,
                       ) -> tuple[str, dict[str, str]]:
    """`(user_message, {handle: cite_id})` for one block.

    Returns the handle map alongside the text because the two must be produced together:
    a map built by a second pass over the bundle could number differently from the prompt
    the model actually saw, and every cite would resolve to the wrong evidence — the one
    failure mode that produces *plausible* citations, which is worse than none.

    An empty slice returns `("", {})`: there is nothing to cite, so nothing may be said,
    and the caller must not spend a model call on it.
    """
    if block == BLOCK_TARKIB:
        entries = tarkib_slice(bundle, level_claims or {})
    else:
        entries = evidence_slice(bundle, block)
    if not entries:
        return "", {}

    handles = {str(i): e["cite_id"] for i, e in enumerate(entries, 1)}
    lines = _header(bundle)

    if block == BLOCK_TARKIB:
        lines.append("\nالدعاوى التي ثبتت في المستويات السابقة:")
        titles = {BLOCK_HURUF: "الحروف", BLOCK_SARFI: "صرفي",
                  BLOCK_NAHWI: "نحوي", BLOCK_DALALI: "دلالي"}
        for b, title in titles.items():
            for claim in (level_claims or {}).get(b) or []:
                lines.append(f"- ({title}) {claim.get('text_ar', '')}")

    lines.append("\nالشواهد المرقّمة (لا تستشهد بغيرها):")
    lines += [f"[{i}] {e['line_ar']}" for i, e in enumerate(entries, 1)]

    lines.append("\n" + BLOCK_TASK[block])

    if block == BLOCK_DALALI and len(bundle.get("nazair") or []) < _FIELD_MIN_NAZAIR:
        # Stated rather than silently skipped: the reader's block will say the field was
        # omitted, and the model must not fill the gap from its own knowledge.
        lines.append("- النظائر أقلُّ من أن يُستخرَج منها حقلٌ دلالي، فلا تذكر حقلًا دلاليًّا.")

    return "\n".join(lines), handles


def resolve_cites(raw_cites: object, handles: dict[str, str]) -> list[str]:
    """Model handles → evidence ids. Unknown handles become UNRESOLVABLE, never dropped.

    Silently discarding an unknown handle would let a claim that cited `[97]` — a number
    the prompt never showed — arrive at the gate as a claim with an empty `cites` list, and
    be logged `no-citation`: a *fabricated citation* filed under *forgot to cite*. The
    placeholder keeps the two distinguishable in the coverage log, which is the only place
    the difference can be seen.

    Total over hostile shapes for the same reason the gate is: `cites` arrives from a
    model, so it may be a string, a number, a nested list, or absent.

    Arabic-Indic digits are folded to ASCII before lookup. A model writing Arabic prose
    emits «٣» for three, and the handles are keyed «3» — so an intended, correct citation
    would resolve to `unknown:handle-٣` and take its claim down as a *fabrication*. That is
    a self-inflicted loss of exactly the kind `extract_json_array` already absorbs for code
    fences, and the fold is total and unambiguous, not a guess about meaning. (The prompt
    also asks for ASCII digits and shows them; this is the belt to that brace — PROMPT_VERSION
    1.4.0 shipped an example written «[٣، ٥]», which would have voided every claim that
    imitated it.)
    """
    if raw_cites is None:
        return []
    seq = raw_cites if isinstance(raw_cites, (list, tuple)) else [raw_cites]
    out: list[str] = []
    for raw in seq:
        key = str(raw).strip().translate(_ARABIC_DIGITS)
        resolved = handles.get(key)
        out.append(resolved if resolved else UNKNOWN_HANDLE.format(key[:40]))
    # De-duplicated, order preserved: a model repeating one handle is not two citations,
    # and the repetition would inflate every per-claim citation count in the sweep.
    return list(dict.fromkeys(out))


# ─────────────────────────────────────────────────────────────────────────────
# 9. The verse synthesis (tasks.md §11)
# ─────────────────────────────────────────────────────────────────────────────
VERSE_TASK = (
    "المطلوب: أطروحةٌ واحدةٌ تجمع ما ثبت عن كلمات هذه الآية — ماذا تُضيف هذه الألفاظُ "
    "مجتمعةً؟\n"
    "- لا بدّ أن تستشهد بأرقام دعاوى من كلمتين مختلفتين على الأقلّ.\n"
    "- نصُّ الآية ليس بين يديك، ولا تستحضره: الدعوى مبنيّةٌ على ما تحته من دعاوى "
    "الكلمات وحدَها، لا على قراءتك للآية.\n"
    "- لا تُفسّر الآية، ولا تُلخّص معناها، ولا تحكِ قصّتها.\n"
    "- الوسم: «مُولَّد» أو «تأويلي»."
)


def verse_lines(items: dict) -> dict[str, str]:
    """`{cite_id: line}` — one readable line per surviving word claim."""
    return {
        cite_id: (f"«{item.get('word_vocalized', '')}» ({item.get('ref', '')}) — "
                  f"{item.get('text_ar', '')}")
        for cite_id, item in (items or {}).items()
    }


def build_verse_message(items: dict, *, surah: object = "", ayah: object = "",
                        capped_note: str = "") -> tuple[str, dict[str, str]]:
    """The verse-synthesis message + its handle map, or `("", {})` for no evidence.

    **The verse text is never in this message.** That is the founding constraint made
    mechanical rather than promised: a model shown the آية can read it directly and then
    decorate the reading with citations, and no downstream check can tell that apart from a
    synthesis. What it is shown is the surviving word claims, numbered.

    `capped_note` is passed through verbatim when the verse was truncated, so the model is
    never led to believe it is summarising the whole verse (tasks.md 11.3).
    """
    lines_by_id = verse_lines(items)
    if not lines_by_id:
        return "", {}
    header = [f"الآية: {surah}:{ayah} — دعاوى كلماتها المرقّمة (لا تستشهد بغيرها):"]
    if capped_note:
        header.append(capped_note)
    handles: dict[str, str] = {}
    body: list[str] = []
    for i, (cite_id, line) in enumerate(lines_by_id.items(), 1):
        handles[str(i)] = cite_id
        body.append(f"[{i}] {line}")
    message = "\n".join(header) + "\n\n" + "\n".join(body) + "\n\n" + VERSE_TASK
    return message, handles


if __name__ == "__main__":  # smoke test — mirrors evidence.py / citations.py
    from tahlil.evidence import build

    for position in ((23, 61, 2), (23, 61, 3)):
        bundle = build(*position)
        print(f"\n{'=' * 70}\n=== {bundle['ref']}  «{bundle['surface_vocalized']}» ===")
        for block in citations.BLOCKS:
            if block == BLOCK_TARKIB:
                continue
            msg, handles = build_user_message(bundle, block)
            print(f"\n--- [{block}] {len(handles)} شاهدًا ---")
            print(msg or "(لا شواهد — لا يُستدعى النموذج)")
