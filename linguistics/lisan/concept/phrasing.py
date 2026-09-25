"""
phrasing.py — the optional LLM re-wording, and the veto that stands over it.

**The model is a RENDERER with a veto over it, never an author.** It is handed a
finished sentence and a closed word list and asked to say the same thing better;
anything it returns that names something outside that list is discarded unread by
the reader, and the deterministic template's sentence is shown instead. That is
the whole of the contract, and it is written this way because the repository has
already paid for the alternative twice:

  * `POST /madar/analyze` is **quarantined** — the router, the models and the
    engine still exist and still pass their tests, and the route is simply not
    mounted — because the LLM synthesis of the مدار was unreliable on roughly
    half the witness roots. The sourced half of that feature was sound; the
    generated half is what cost it its route.
  * `linguistics/lisan/synthesis_template.py` lost its LLM step for the same
    reason one storey down: a local model both corrupted tokens mid-word and
    produced fluent prose contradicting the attested sense it was built on. Its
    docstring's verdict is the one this module inherits — for a Quranic tool a
    fluent-but-false reading is worse than a plain one.

So there is no configuration under which a phrasing reaches the page without
passing `contained`, and no flag that softens the check. §D6 of the design is
explicit that the engine's sentence reads more bluntly than a scholar's,
permanently, and that the containment rule is «exactly what forbids closing that
gap, by template or by LLM».

**Off by default.** `CONCEPT_LLM_PHRASING` absent, empty, `0` or `false` means
off, and when it is off `phrase()` returns the template's sentence and **never
constructs a client** — no import of a provider, no socket, no model resident.

─────────────────────────────────────────────────────────────────────────────
WHAT «CONTAINED» MEANS, AND WHICH FOLD DECIDES IT

Every content word of the model's sentence must map to a declared lemma of a
**realised** primitive of THIS concept. Realised, not carried: the sentence says
what the composition put in it, and a word licensed by a primitive that ranked
below the window would be the reader being told something the مفهوم does not
claim.

The comparison runs through **`arabic_text.normalize_search`**, and that choice
is the kind this repository gets wrong silently, so it is argued rather than
asserted. Read the table in `arabic_text/__init__.py` first; then:

  * **`normalize_text` is excluded outright — it DELETES the hamza.** `خَفاء`
    would fold to `خفا` and `أَصْل` to `اصل` on both sides, which does not merely
    lose a letter: it makes genuinely different words compare equal, so the check
    would start *accepting* words no primitive declares. A veto that grows more
    permissive under its own normalizer is not a veto.
  * **`normalize_root` is the wrong question.** Its own docstring says not to use
    it on free text — it leaves `ة` and `ى` standing — and a model's sentence is
    free text, not a root key. Matching `مُلامسة` against a model's `ملامسه`
    is exactly the job `normalize_search` adds those two folds for.
  * **`normalize_search` is right and it is the layered one**: it is
    `normalize_root` — NFC, harakāt and tanwīn and the dagger alif stripped,
    tatweel dropped, hamza carriers folded and **no hamza ever deleted** — plus
    waqf marks stripped and `ى → ي`, `ة → ه`. The declared lemmas carry ḥarakāt
    (`حِدّة`, `أَصْل`, `مَدّ`) and a model's output will not reproduce them
    byte for byte; the ḥaraka is the part that must fold, and the hamza is the
    part that must not.

Verified, and pinned by a test: every one of the twenty primitives' own names
folds onto one of its row's declared lemmas. The primitive name is therefore NOT
added to the allowed set as a convenience — if a curator ever dropped it from a
`lemmas` cell, the template's own sentence would stop passing its own check, and
a test asserting exactly that is a better place to find out than a quiet special
case here.

**Function words are subtracted from a closed set declared in `template.py`** —
`FUNCTION_WORDS`, plus the `PROCLITICS` and `ARTICLE` a word may carry on its
front. Every word subtracted beyond that set is a word the veto stops looking at,
so the set is the template's own and is not re-spelled here. A proclitic is
peeled only when what remains is itself a declared lemma, which is the rule
`retrieval/verse_lookup.py` learned the hard way: a leading letter stripped on
sight turns `وَلَد` into `لد`. Here a mistaken peel can only fail to match, never
manufacture one.

─────────────────────────────────────────────────────────────────────────────
WHAT A REJECTION IS, AND WHAT IT IS NOT

A rejected phrasing is **not shown**. `phrase()` returns the template's sentence,
`source` = `SENTENCE_SOURCE_TEMPLATE`, and a non-empty `rejection` naming the
words that were not licensed — named, because «rejected» without the offending
word tells an operator nothing about whether the prompt drifted or the veto is
too tight.

`rejection` is empty for every OTHER outcome: the pass being off, no client, a
timeout, a provider error, an empty answer. Those are failures to produce, and a
failure recorded as a rejection would make «the model invented something» and
«the model was not running» read identically in the response. Every one of them
degrades to the template; none of them raises.

The rejection string is English, alone among this package's reader-facing text,
and deliberately: it is a runtime diagnostic about a sentence that was never
shown, addressed to whoever enabled the pass. It is not a reading of the root,
and the مفهوم — the thing written for the reader — stays the Arabic one.

─────────────────────────────────────────────────────────────────────────────
THE SEAM

`generate_phrasing` is the only function here that touches the model, the only
one that is not pure, and the single place a test replaces. `allowed_lemmas`,
`contained` and — when the toggle is off — `phrase` itself run with no network,
no disk beyond the already-cached primitive table, and no clock.

Blindness holds through this module as it does through its siblings: it reads the
frozen table's `lemmas` column and the letters' composed result, and it cannot
name, import or reach anything that records what a root means.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from arabic_text import normalize_search  # noqa: E402
from llm_client import LLMClient  # noqa: E402

from linguistics.lisan.concept import template  # noqa: E402
from linguistics.lisan.concept.compose import (  # noqa: E402
    Concept,
    SENTENCE_SOURCE_PHRASING,
    SENTENCE_SOURCE_TEMPLATE,
)
from linguistics.lisan.concept.primitives import primitive_table  # noqa: E402

# The toggle. Named as a constant so a caller, a test and the documentation all
# spell it once.
CONCEPT_LLM_PHRASING_ENV = "CONCEPT_LLM_PHRASING"

# What counts as ON. Everything else — absent, empty, "0", "false", "no", a typo
# — is OFF, which is the safe direction for a switch that turns a model loose on
# a Quranic reading.
_ENABLED_VALUES = frozenset({"1", "true", "yes", "on"})

# Punctuation mapped to a space before splitting. Listed rather than matched by a
# character class: a class over "everything that is not an Arabic letter" is the
# unreviewable-under-bidi construct `arabic_text/marks.py` forbids, and it would
# also swallow the marks the fold is supposed to handle.
_PUNCTUATION = "،؛؟.,;:!?()[]{}«»\"'…—–-/\\|*_\n\r\t"
_PUNCTUATION_TABLE = {ord(character): " " for character in _PUNCTUATION}

# How many offending words a rejection names before it stops. A model that has
# drifted entirely produces a whole sentence of them, and a rejection the length
# of a paragraph is a rejection nobody reads.
_MAX_NAMED = 5

# Terse and imperative, in Arabic, for the reason `linguistics/tahlil/prompts.py`
# records: a local model drifts into Latin fragments on long chatty prompts, and
# here a single Latin fragment is an automatic rejection — so verbosity in the
# prompt is paid for in discarded answers.
#
# Note what the prompt does NOT do. It never says what the root means, never
# offers an example, and never asks for an improvement in substance. It cannot:
# the containment check would refuse whatever it produced, and a prompt inviting
# something the veto must then destroy is a prompt that guarantees a wasted call.
PHRASING_SYSTEM = (
    "أنت مُصِيغٌ لا مؤلِّف. تُعيد صياغةَ جملةٍ عربيةٍ مُعطاةٍ بألفاظٍ مُعطاة، "
    "ولا تزيد عليها معنًى من عندك.\n"
    "قواعد ملزمة:\n"
    "١) أجب بجملةٍ عربيةٍ واحدةٍ فقط، بلا مقدمةٍ ولا شرحٍ ولا أسوارِ شفرة.\n"
    "٢) لا تستعمل إلا الألفاظَ المعطاةَ في القائمة، وحروفَ العطف «و» و«ثمّ» "
    "و«حتّى» و«الفاء»، وأداةَ التعريف «ال». وأيُّ لفظٍ سواها تسقط به الجملةُ "
    "كلُّها ولا تُعرَض.\n"
    "٣) لا تُدخِل مثالًا ولا شاهدًا قرآنيًّا ولا تفسيرًا ولا اسمَ جذرٍ ولا "
    "لفظًا يدلُّ على أثرٍ أو على طرفٍ ثانٍ؛ ليس في القائمة ما يأذن بشيءٍ من ذلك.\n"
    "٤) اجعلها جملةً اسميةً مرفوعةً كالأصل، واحفَظ ترتيبَ الألفاظ كما هو.\n"
    "٥) اكتب بالعربية وحدها: لا حرفَ لاتينيًّا ولا رقمًا ولا علامةً أعجمية."
)

PHRASING_PROMPT = (
    "الصياغةُ الأصلية، وهي الأصلُ الذي تُعيد صياغتَه:\n"
    "{sentence}\n"
    "الألفاظُ المأذونُ بها كلُّها، ولا تخرج عنها:\n"
    "{words}\n"
    "اكتب الجملةَ الواحدة."
)


@dataclass(frozen=True)
class PhrasingResult:
    """What the caller shows, who wrote it, and what was thrown away.

    `sentence` is always something displayable: the phrasing when it passed, the
    template's own sentence in every other case. There is no state in which this
    dataclass carries an unchecked model output.

    `source` is `SENTENCE_SOURCE_TEMPLATE` or `SENTENCE_SOURCE_PHRASING`, from
    `compose.py` — the same two strings `Concept.sentence_source` holds, so the
    result folds back in without a translation step.

    `rejection` is non-empty only when a phrasing was produced and refused. See
    the module docstring: a failure to produce is not a rejection.
    """

    sentence: str
    source: str
    rejection: str


def enabled() -> bool:
    """Whether the phrasing pass may run at all. Off unless explicitly turned on."""
    return os.getenv(CONCEPT_LLM_PHRASING_ENV, "0").strip().lower() in _ENABLED_VALUES


def allowed_lemmas(concept: Concept) -> frozenset[str]:
    """Every word the frozen table declares for this concept's REALISED primitives.

    Pure. Reads the table's `lemmas` column — the column that exists for exactly
    this check, so that the permitted vocabulary can never be a list assembled
    somewhere else and quietly widened.

    Keyed on each hit's FEATURE rather than on its primitive name, because that
    is how the table is keyed: `musta'liya` and `mutbaqa` both yield `ضَخامة`, and
    looking up by primitive would need a reverse index that does not exist and
    would have to choose between two rows that happen to agree today.

    Empty for a refused root — there are no positions, so nothing is licensed,
    and `contained` then refuses every non-empty sentence, which is correct.
    """
    table = primitive_table()
    lemmas: set[str] = set()
    for reading in concept.positions:
        for hit in reading.realised:
            row = table.for_feature(hit.feature)
            if row is None:
                continue
            lemmas.update(row.lemmas)
    return frozenset(lemma for lemma in lemmas if lemma)


def _words(sentence: str) -> list[str]:
    """The sentence's tokens, punctuation turned to whitespace first."""
    return sentence.translate(_PUNCTUATION_TABLE).split()


def _candidates(folded: str) -> list[str]:
    """The folded token and the forms it could be under a declared proclitic.

    Whole token first, so a word that IS a lemma is never peeled — `وَسَط` starts
    with a coordinator and must not be read as `و` + `سط`. Then one coordinator,
    then the article, then both: four candidates at most, each a peel the template
    itself could have written.

    A peel is only ever *offered*; the caller accepts it only if what remains is a
    declared lemma, so a wrong peel fails to match rather than inventing a match.
    """
    forms = [folded]
    for proclitic in template.PROCLITICS:
        if folded.startswith(proclitic) and len(folded) > len(proclitic):
            rest = folded[len(proclitic):]
            forms.append(rest)
            if rest.startswith(template.ARTICLE) and len(rest) > len(template.ARTICLE):
                forms.append(rest[len(template.ARTICLE):])
    if folded.startswith(template.ARTICLE) and len(folded) > len(template.ARTICLE):
        forms.append(folded[len(template.ARTICLE):])
    return forms


def contained(sentence: str, concept: Concept) -> tuple[bool, str]:
    """Does every content word of `sentence` map to a realised primitive's lemma?

    Pure. Returns `(True, "")` or `(False, reason)`, the reason naming the words
    that were not licensed.

    A blank sentence is refused rather than passed: a phrasing that says nothing
    is not a rendering of nine primitives. `phrase()` never asks — it treats an
    empty answer as a failure to produce, one step earlier — but a caller running
    the check directly should not get a pass for an empty string.
    """
    if not sentence.strip():
        return False, "the phrasing is empty: it renders none of the realised primitives"

    permitted = {normalize_search(lemma) for lemma in allowed_lemmas(concept)}
    permitted |= {normalize_search(word) for word in template.FUNCTION_WORDS}
    permitted.discard("")

    intruders: list[str] = []
    for word in _words(sentence):
        folded = normalize_search(word)
        if not folded:
            continue
        if any(candidate in permitted for candidate in _candidates(folded)):
            continue
        if word not in intruders:
            intruders.append(word)

    if not intruders:
        return True, ""

    named = intruders[:_MAX_NAMED]
    more = len(intruders) - len(named)
    listed = ", ".join(f"«{word}»" for word in named) + (f" (+{more} more)" if more else "")
    return False, (
        f"the phrasing introduces {listed}, which no realised primitive of "
        f"«{concept.root}» declares as a lemma"
    )


def generate_phrasing(concept: Concept, template_sentence: str) -> str:
    """Ask the model for one re-worded sentence. **The only impure function here.**

    Constructed on the call, never at import and never when the pass is off, so a
    backend that only serves the deterministic concept holds no client and no
    provider import at all. Raising is fine: `phrase()` catches everything and
    degrades to the template.

    This is the single seam a test replaces. Everything the veto does happens
    around it, in pure code, so a test can drive any output through the check
    without a model anywhere near the process.
    """
    words = "، ".join(sorted(allowed_lemmas(concept)))
    message = PHRASING_PROMPT.format(sentence=template_sentence, words=words)
    return LLMClient().chat(PHRASING_SYSTEM, [{"role": "user", "content": message}])


def phrase(concept: Concept, template_sentence: str) -> PhrasingResult:
    """The pass, with its veto. Returns something displayable in every case.

    Order of the guards is the contract:

      1. nothing to re-word — a refused root, or an all-silent concept — returns
         the template's own output without reaching the toggle. A model asked to
         re-word an empty string has nothing to do and everything to invent.
      2. the toggle is off (the default) — the template, and no client is built.
      3. the call fails in any way — no provider, a timeout, an error, an empty
         answer — the template, with `rejection` left EMPTY. That was a failure
         to produce, not a refusal.
      4. the answer fails containment — the template, with the rejection naming
         the words. The answer itself is discarded here and is never returned to
         a caller, let alone rendered.
      5. the answer passes — it is returned, sourced as a phrasing.
    """
    fallback = PhrasingResult(
        sentence=template_sentence,
        source=SENTENCE_SOURCE_TEMPLATE,
        rejection="",
    )
    if concept.refused or not template_sentence.strip():
        return fallback
    if not enabled():
        return fallback

    try:
        # Broad on purpose. The providers raise their own exception families —
        # connection errors, timeouts, authentication, a model that is not
        # pulled — and this module's promise is that none of them reaches a
        # caller. An unreachable model degrades the sentence's prose; it must
        # never cost the reader the concept.
        candidate = (generate_phrasing(concept, template_sentence) or "").strip()
    except Exception:
        return fallback
    if not candidate:
        return fallback

    ok, reason = contained(candidate, concept)
    if not ok:
        return PhrasingResult(
            sentence=template_sentence,
            source=SENTENCE_SOURCE_TEMPLATE,
            rejection=reason,
        )
    return PhrasingResult(
        sentence=candidate,
        source=SENTENCE_SOURCE_PHRASING,
        rejection="",
    )


if __name__ == "__main__":
    from linguistics.lisan.concept.compose import compose

    print(f"{CONCEPT_LLM_PHRASING_ENV}={os.getenv(CONCEPT_LLM_PHRASING_ENV, '')!r} "
          f"-> enabled={enabled()}")
    for probe in ("ضرب", "أنس", "اول", "برزخ"):
        built = compose(probe)
        result = phrase(built, built.sentence)
        print(f"\n{probe} [{result.source}] {result.sentence or '—'}")
        if result.rejection:
            print(f"   rejected: {result.rejection}")
        print(f"   lemmas licensed: {len(allowed_lemmas(built))}")
        print(f"   template contained: {contained(built.sentence, built)}"
              if built.sentence else "   template contained: n/a (no sentence)")
