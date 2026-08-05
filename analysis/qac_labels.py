"""qac_labels.py — Shared QAC-tag → Arabic mapping for the QLisan fiche.

Pure stdlib. **No** LLM / network / fastapi / pydantic imports — importable and
testable in isolation.

This module is the single source of truth that turns the *raw* QAC codes carried
in ``qac_words.json`` (feature values such as ``ACC`` / ``M`` / ``IMPF`` /
``SP:kaAn`` and segment codes ``STEM`` / ``PREFIX`` / ``SUFFIX``) and the syntax
labels in ``qac_syntax.json`` (``relation_ar`` such as the Latin ``root`` or the
bare case word ``مجرور``) into Arabic the fiche can render directly.

Design invariants (see ``openspec/changes/fix-qlisan-fiche-display``):

* **Every** feature key present in the corpus (12 of them) and **every** value it
  takes is mapped here — there is **no raw passthrough**. An unmapped code makes
  :func:`translate_features` raise, which the corpus-wide sweep test turns into a
  failure.
* **No POS table** — ``pos_ar`` is already populated for 100 % of records and
  stays the sole part-of-speech source.
* ``pgn`` is decomposed by **character set** (never positionally) and merged with
  any standalone ``person`` / ``gender`` / ``number`` columns, which are
  authoritative.
* ``relation_ar`` is normalised through :data:`RELATION_AR_OVERRIDE` so it is
  never emitted as ASCII (``root``) nor as a bare case word (``مجرور``).
* The case marker (العلامة) is a **derived** heuristic: emitted only for a
  declinable singular triptote and omitted (never fabricated) for dual / plural /
  proper-noun genitives.
"""
from __future__ import annotations

import sys
import unicodedata
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# `verb_marker` (section 5b) gates one of its omissions on the root's weak-letter
# class. `analysis.mizan` already owns that classification and is the project's
# single definition of it; importing it here keeps one definition rather than a
# second copy free to drift. The dependency costs this module nothing it did not
# already promise: `mizan` is pure stdlib with lazy file loaders — no LLM, no
# network, no ML — so `qac_labels` stays importable and testable in isolation.
#
# The import is **guarded**, and that guard is load-bearing rather than defensive
# habit: `classify_root` / `CLASS_NAQIS` / `CLASS_LAFIF` are contributed by a
# *sibling* change (`harden-mizan-irregular-roots`), while `analysis/word_analysis.py`
# imports this module at module level — so a bare `from … import` here would take
# the entire /qlisan fiche down with an ImportError the day that change is reverted
# or lands out of order. Non-fatal must not mean invisible: with the classifier
# gone `verb_marker` cannot tell a معتلّ الآخر jussive from a صحيح one, so it
# **widens the omission** to every non-أفعال-خمسة مجزوم and warns once (see
# :func:`_warn_root_classifier_unavailable`). It never assumes صحيح — that
# assumption is precisely the confident-and-wrong output this module exists to
# refuse.
try:
    from analysis.mizan import CLASS_LAFIF, CLASS_NAQIS, classify_root
except ImportError:  # pragma: no cover - forced by the test's import blocker
    CLASS_LAFIF = CLASS_NAQIS = None  # type: ignore[assignment]
    classify_root = None  # type: ignore[assignment]
    _ROOT_CLASSIFIER_AVAILABLE = False
else:
    _ROOT_CLASSIFIER_AVAILABLE = True

# ─────────────────────────────────────────────────────────────────────────────
# 1. Value tables — one per feature key present in the corpus, plus segments.
#    (Corpus-verified enumeration: 12 feature keys + 3 segment codes.)
# ─────────────────────────────────────────────────────────────────────────────

# nominal_case ∈ {NOM, ACC, GEN}
NOMINAL_CASE_AR: dict[str, str] = {
    "NOM": "مرفوع",
    "ACC": "منصوب",
    "GEN": "مجرور",
}

# gender ∈ {M, F}
GENDER_AR: dict[str, str] = {
    "M": "مذكّر",
    "F": "مؤنّث",
}

# number ∈ {S, D, P}
NUMBER_AR: dict[str, str] = {
    "S": "مفرد",
    "D": "مثنّى",
    "P": "جمع",
}

# nominal_state ∈ {INDEF} in the corpus; DEF included for completeness.
NOMINAL_STATE_AR: dict[str, str] = {
    "INDEF": "نكرة",
    "DEF": "معرفة",
}

# verb_aspect ∈ {PERF, IMPF, IMPV}
VERB_ASPECT_AR: dict[str, str] = {
    "PERF": "ماضٍ",
    "IMPF": "مضارع",
    "IMPV": "أمر",
}

# verb_voice ∈ {PASS} in the corpus (active is unmarked).
VERB_VOICE_AR: dict[str, str] = {
    "PASS": "مبني للمجهول",
    "ACT": "مبني للمعلوم",
}

# verb_mood ∈ {MOOD:JUS, MOOD:SUBJ}
VERB_MOOD_AR: dict[str, str] = {
    "MOOD:JUS": "مجزوم",
    "MOOD:SUBJ": "منصوب",
    "MOOD:IND": "مرفوع",
}

# verb_form ∈ {(II) … (XII)} in the corpus (form I is unmarked).
VERB_FORM_AR: dict[str, str] = {
    "(I)": "الوزن الأول",
    "(II)": "الوزن الثاني",
    "(III)": "الوزن الثالث",
    "(IV)": "الوزن الرابع",
    "(V)": "الوزن الخامس",
    "(VI)": "الوزن السادس",
    "(VII)": "الوزن السابع",
    "(VIII)": "الوزن الثامن",
    "(IX)": "الوزن التاسع",
    "(X)": "الوزن العاشر",
    "(XI)": "الوزن الحادي عشر",
    "(XII)": "الوزن الثاني عشر",
}

# derived_nouns ∈ {ACT_PCPL, PASS_PCPL, VN}
DERIVED_NOUNS_AR: dict[str, str] = {
    "ACT_PCPL": "اسم الفاعل",
    "PASS_PCPL": "اسم المفعول",
    "VN": "مصدر",
}

# special_group — raw Buckwalter after stripping the "SP:" prefix.
# Corpus values: SP:<in~ / SP:kaAn / SP:kaAd.
SPECIAL_GROUP_AR: dict[str, str] = {
    "<in~": "من أخوات إنّ",
    "kaAn": "من أخوات كان",
    "kaAd": "من أخوات كاد",
}

# person ∈ {1, 2, 3} (as strings, both standalone and inside pgn).
PERSON_AR: dict[str, str] = {
    "1": "متكلّم",
    "2": "مخاطب",
    "3": "غائب",
}

# segment ∈ {STEM, PREFIX, SUFFIX}
SEGMENT_AR: dict[str, str] = {
    "STEM": "جذع",
    "PREFIX": "بادئة",
    "SUFFIX": "لاحقة",
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. FEATURE_LABEL_AR — Arabic row label for every feature key (never the raw key)
# ─────────────────────────────────────────────────────────────────────────────

FEATURE_LABEL_AR: dict[str, str] = {
    "nominal_case": "الحالة الإعرابية",
    "gender": "الجنس",
    "number": "العدد",
    "nominal_state": "التعريف",
    "verb_aspect": "الزمن",
    "verb_form": "الوزن",
    "verb_mood": "حالة الفعل",
    "verb_voice": "البناء",
    "derived_nouns": "المشتقّات",
    "person": "الشخص",
    "special_group": "المجموعة",
    # `pgn` has no row label of its own — it is decomposed into
    # person / gender / number, which carry the labels above.
}


# ─────────────────────────────────────────────────────────────────────────────
# 3. relation_ar override — never ASCII, never a bare case word.
#    Corpus sweep of `qac_syntax.json` distinct `relation_ar`: the ONLY ASCII
#    value is "root" (12,897 rows); the ONLY bare case word is "مجرور" (relation
#    `gen`, 10,510 rows). `voc`'s relation_ar is already «منادى».
# ─────────────────────────────────────────────────────────────────────────────

RELATION_AR_OVERRIDE: dict[str, str] = {
    "root": "عمدة الجملة",  # relation `root` — Latin token in the source
    "مجرور": "اسم مجرور",  # relation `gen` — bare case word → full function name
    # "منادى" (relation `voc`) is already Arabic and correct; no override needed.
}


def relation_ar_display(relation_ar: str | None) -> str | None:
    """Normalise a ``relation_ar`` for display.

    Replaces the Latin ``root`` and the bare case word ``مجرور`` with proper
    Arabic function names; every other ``relation_ar`` is already Arabic and
    passes through unchanged. Returns ``None`` unchanged (unavailable نحوي).
    """
    if relation_ar is None:
        return None
    return RELATION_AR_OVERRIDE.get(relation_ar, relation_ar)


# ─────────────────────────────────────────────────────────────────────────────
# 4. relation → canonical case, for the assembler's consistency guard (task 3.2).
#    Keyed by the *displayed* Arabic function name (post-override) because that is
#    what a trailing case word must agree with — this is what catches the 83
#    `Subj`-tagged-as-«مفعول به» source mislabels (2:80:4): «مفعول به» → ACC, but
#    the word is NOM ⇒ mismatch ⇒ show the function name alone, never
#    «مفعول به مرفوع».
#
#    A bare case word that is fully expressed by the override («مجرور»/«اسم مجرور»)
#    is deliberately absent → returns None → no second case word is appended
#    («اسم مجرور», never «اسم مجرور مجرور»). Non-case-bearing relations
#    (متعلق/صلة/شرط/particles/…) are simply absent.
#
#    اسم/خبر of كان-and-sisters vs إنّ-and-sisters are resolved by family:
#      كان-family (+ ليس/ما/عسى/كاد…): اسمها مرفوع، خبرها منصوب
#      إنّ-family (إن/أن/لكن/كأن/ليت/لعل/لا): اسمها منصوب، خبرها مرفوع
# ─────────────────────────────────────────────────────────────────────────────

# إنّ and its sisters (relation_ar remainder after «اسم »/«خبر »):
# اسمها منصوب، خبرها مرفوع.
_INNA_SISTERS: frozenset[str] = frozenset(
    {"إن", "أن", "لكن", "لاكن", "كأن", "ليت", "لعل", "لا"}
)

# كان and its sisters + ليس/ما (عمل ليس) + أفعال المقاربة (كاد/عسى…), enumerated
# from the corpus `relation_ar` remainders: اسمها مرفوع، خبرها منصوب.
_KAANA_SISTERS: frozenset[str] = frozenset(
    {
        "كان", "كانت", "كن", "كون", "اكون", "نكون", "يكون", "تكون",
        "يكن", "تكن", "نكن", "اكن", "يك", "نك", "ك",
        "أصبح", "تصبح", "يصبح", "ظل", "ليس", "ما", "عسى",
        "زال", "يزال", "برح", "دام", "دم", "تفتاء",
        "كاد", "يكاد", "تكاد", "اكاد",
    }
)

# Base table for case-bearing functions that are NOT اسم/خبر compounds.
_RELATION_CANONICAL_CASE_BASE: dict[str, str] = {
    # ── مرفوعات ──
    "فاعل": "NOM",
    "نائب فاعل": "NOM",
    "مبتدأ": "NOM",
    "خبر": "NOM",
    "عمدة الجملة": "NOM",  # override target for relation `root`
    "root": "NOM",  # raw, in case the guard reads pre-override
    # ── منصوبات ──
    "مفعول به": "ACC",
    "مفعول مطلق": "ACC",
    "المفعول لأجله": "ACC",
    "حال": "ACC",
    "تمييز": "ACC",
    "مستثني": "ACC",  # corpus spelling (with ى written ي)
    # ── مجرورات ──
    "مضاف إليه": "GEN",
    # NB: «مجرور»/«اسم مجرور» intentionally omitted (override already expresses
    # the case) → relation_canonical_case returns None → no appended case word.
    # NB: «منادى» intentionally omitted — the assembler treats voc specially
    # (no lafẓī case word / marker).
}


def relation_canonical_case(relation_ar: str | None) -> str | None:
    """Canonical ``nominal_case`` (``NOM``/``ACC``/``GEN``) for a function name.

    Accepts the raw or overridden ``relation_ar``. Returns ``None`` for
    relations that bear no fixed case, that already express their case in the
    name, or that are non-composable — in all of which the assembler appends no
    case word.
    """
    if relation_ar is None:
        return None
    name = RELATION_AR_OVERRIDE.get(relation_ar, relation_ar)
    if name in _RELATION_CANONICAL_CASE_BASE:
        return _RELATION_CANONICAL_CASE_BASE[name]
    # اسم/خبر of كان / إنّ and their sisters, resolved by family. Only fires when
    # the remainder is a recognised sister — so «اسم مجرور» is NOT misread here.
    for prefix, is_ism in (("اسم ", True), ("خبر ", False)):
        if name.startswith(prefix):
            rest = name[len(prefix):].strip()
            if rest in _INNA_SISTERS:
                return "ACC" if is_ism else "NOM"  # اسم إنّ منصوب / خبر إنّ مرفوع
            if rest in _KAANA_SISTERS:
                return "NOM" if is_ism else "ACC"  # اسم كان مرفوع / خبر كان منصوب
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. case_marker — العلامة الإعرابية for a DECLINABLE SINGULAR TRIPTOTE only.
# ─────────────────────────────────────────────────────────────────────────────

_CASE_MARKER_AR: dict[str, str] = {
    "NOM": "الضمة",
    "ACC": "الفتحة",
    "GEN": "الكسرة",
}


def case_marker(word: dict) -> str | None:
    """Primary case marker (الأصل) for a declinable singular triptote, else None.

    ``word`` may be the full صرفي/word record (with a ``features`` dict and an
    ``is_proper_noun`` flag) or a bare ``features`` dict.

    Omitted (returns ``None``, never fabricated) when:
      * there is no ``nominal_case`` (مبني words carry no lafẓī marker);
      * ``number`` ∈ {D, P} (dual/sound-plural markers are الألف/الياء/الواو,
        not the primary ḥarakah — the الأصل would be wrong);
      * the word is a proper-noun **genitive** (diptote-suspect: a diptote takes
        الفتحة in the genitive, not الكسرة).
    """
    features = word.get("features", word) if isinstance(word, dict) else {}
    if not isinstance(features, dict):
        features = {}
    case = features.get("nominal_case")
    if not case:
        return None
    if features.get("number") in {"D", "P"}:
        return None
    is_proper = bool(word.get("is_proper_noun", False)) if isinstance(word, dict) else False
    if case == "GEN" and is_proper:
        return None
    return _CASE_MARKER_AR.get(case)


# ─────────────────────────────────────────────────────────────────────────────
# 5b. verb_marker — العلامة for a مضارع, the verbal counterpart of `case_marker`.
#
# `case_marker` above is nominal-only, so the reference analysis of 23:61:2
# («فعل مضارع مرفوع وعلامته ثبوت النون») had no deterministic source and the
# claim would have had to be asserted by a generator. It *is* derivable from QAC,
# so it belongs to the «معطى محقّق» layer — and it is derived with the same
# conservatism as the nominal marker: emitted only when the corpus **shows** the
# marker, omitted (never guessed) in every other case.
#
# Scope. Of the 19 356 verbs, only the 8 330 tagged `IMPF` are معرب; الماضي
# (9 150) and الأمر (1 876) are مبني and carry no lafẓī marker at all, so they
# return None rather than a fabricated one.
#
# `verb_mood` on those 8 330: absent 5 582 · MOOD:JUS 1 418 · MOOD:SUBJ 1 330.
# **Absent means indicative, not unknown.** The raw treebank
# (`data/raw/eqtb/quranic-treebank.csv`) carries a `verb_mood` *column* on every
# row and writes the treebank's null token `_` on exactly those 5 582 words —
# measured, not assumed: the column's IMPF distribution there is
# {'_': 5582, 'MOOD:JUS': 1418, 'MOOD:SUBJ': 1330}. The QAC tagset's own name for
# that null is `MOOD:IND`, so an ingestion that normalised the column instead of
# dropping it would hand this module `MOOD:IND` where it sees `None` today.
# **Both spellings therefore mean the same thing here, everywhere** — the lookup
# below folds the absent case onto `MOOD:IND` through the existing
# :data:`VERB_MOOD_AR`, and the أفعال خمسة branch tests `mood in (None, _MOOD_IND)`
# rather than `mood is None`. Testing identity with `None` alone would have made
# the two spellings disagree: on a re-ingest every indicative أفعال خمسة verb —
# 2 541 markers, the pinned 23:61:2 among them — would silently return None,
# with no error to notice it by.
#
# The only marker QAC lets us *read* is نون الرفع, which is why الأفعال الخمسة
# are the only forms that get a «وعلامته …» clause. الضمة / الفتحة / السكون on a
# singular مضارع would have to be assumed from the tag, and for a معتل الآخر verb
# the assumption is wrong — hence the mood word alone elsewhere, and silence for
# the one case where a bare mood word would still mislead.
#
# **What the bare mood word claims, stated once.** Outside الأفعال الخمسة this
# function returns الحالة alone (مرفوع / منصوب / مجزوم), and that string asserts
# **the case, never the marker**. On a معتل الآخر verb the ḥarakah is مقدَّرة, so
# «مرفوع» is true of يَدْعُو and «منصوب» of يَدْعُوَ even though neither shows a ضمة
# or a فتحة — which is why the very same ناقص/لفيف roots keep the bare mood word
# in مرفوع (737 words) and منصوب (218) while their jussive is withheld (209).
# That is not an inconsistency but the one case where الحالة and العلامة cannot be
# held apart: «مجزوم» read in an العلامة field means بالسكون, and a معتل الآخر
# jussive is marked by حذف حرف العلة — a *deletion the surface shows*
# (فَلْيَدْعُ, وَلْيَخْشَ, يَأْتِ), not a مقدَّر ḥarakah the surface merely fails to
# show. Asserting السكون there contradicts the visible word; asserting رفع on
# يَدْعُو does not. Hence the rule: **the bare mood word is الحالة only, and it is
# withheld exactly where the surface would contradict it** — no behaviour change,
# and the counts below stay reproducible.
# ─────────────────────────────────────────────────────────────────────────────

# الأفعال الخمسة — the مضارع forms that carry نون الرفع: (2nd/3rd person) ×
# (dual | masculine plural), plus 2FS (ياء المخاطبة). Enumerated from the `pgn`
# codes the corpus actually puts on a مضارع rather than from a general rule:
# 3MP 2 137 · 2MP 1 338 · 2D 48 · 3MD 35 · 2FS 7 · 2FD 2 · 2MD 1 · 3FD 1.
# 3FP/2FP are deliberately absent — their ن is نون النسوة, see below.
_KHAMSA_PGN: frozenset[str] = frozenset(
    {"3MP", "2MP", "2D", "3MD", "2MD", "2FD", "3FD", "2FS"}
)

# نون النسوة (54 words). A مضارع carrying it is **مبني على السكون** في محل
# رفع/نصب/جزم, so it has no lafẓī marker to report. QAC still tags a syntactic
# mood on 22 of them (يَغْضُضْنَ is `MOOD:JUS`, يَحْزَنَّ `MOOD:SUBJ`) — that is a
# *محلّي* mood, and printing «مجزوم» for a مبني verb is exactly the confident,
# complete, wrong output this module refuses to produce.
_NUN_NISWA_PGN: frozenset[str] = frozenset({"3FP", "2FP"})

# The subject pronoun نون الرفع attaches to: واو الجماعة / ألف الاثنين /
# ياء المخاطبة. Reading the letter *before* a final ن is what separates نون الرفع
# (يُسَارِعُ+ونَ) from a نون التوكيد sitting straight on the stem (تُؤْمِنُ+نَّ).
_SUBJECT_LETTERS: frozenset[str] = frozenset("واي")

# Root classes whose لام is a حرف علة: their jussive is marked **بحذف حرف العلة**,
# not بالسكون (فَلْيَدْعُ 96:17:1, وَلْيَخْشَ 4:9:1, يَأْتِ 2:148:10). Empty when the
# classifier could not be imported — the guard then fires on *every* non-khamsa
# jussive instead (see :func:`_needs_root_class_omission`), which costs 658
# markers (the whole «مجزوم» bucket) but never mis-asserts one.
_MUTALL_AL_AKHIR: frozenset[str] = (
    frozenset({CLASS_NAQIS, CLASS_LAFIF}) if _ROOT_CLASSIFIER_AVAILABLE else frozenset()
)

_SHADDA = "ّ"
_MOOD_IND = "MOOD:IND"

# The dependency named in the warning, spelled out so the message is actionable.
_ROOT_CLASSIFIER_DEP = "analysis.mizan (CLASS_NAQIS / CLASS_LAFIF / classify_root)"

# Warn once per process, never once per word: 861 مضارع records reach the guard
# that consults the classifier, and 861 identical warnings would bury the one
# line that matters.
_root_classifier_warned = False


def _warn_root_classifier_unavailable() -> None:
    """Emit the single warning that names the missing root classifier."""
    global _root_classifier_warned
    if _root_classifier_warned:
        return
    _root_classifier_warned = True
    warnings.warn(
        f"{_ROOT_CLASSIFIER_DEP} is unavailable (ImportError): verb_marker cannot "
        "tell a defective-final (naqis/lafif) jussive from a sound one, so it "
        "omits the marker for every non-khamsa jussive rather than implying "
        "sukun. Restore analysis.mizan to get those markers back.",
        RuntimeWarning,
        stacklevel=3,
    )


def _needs_root_class_omission(root: str | None) -> bool:
    """Is this jussive's marker unsafe to state — or unknowable without mizan?"""
    if not _ROOT_CLASSIFIER_AVAILABLE:
        _warn_root_classifier_unavailable()
        return True
    return classify_root(root) in _MUTALL_AL_AKHIR

# Display strings — the composed «الحالة + العلامة» the fiche renders verbatim.
_MARKER_JOIN = " وعلامته "
_NUN_THABITA = "ثبوت النون"
_NUN_MAHDHUFA = "حذف النون"


def _arabic_letters(text: str) -> str:
    """The consonant skeleton of `text` — Unicode letters (category ``Lo``) only.

    Everything else goes: ḥarakāt and the dagger alif (``Mn``), and the Uthmani
    small wāw/yāʾ plus tatwīl (``Lm``). Dropping the small wāw is load-bearing,
    not cosmetic — keeping it hides the نون الرفع of يَلْوُۥنَ (3:78:4) behind a
    letter that is not pronounced, and the marker then reads as absent.
    """
    return "".join(ch for ch in text or "" if unicodedata.category(ch) == "Lo")


def _is_vocalized(text: str) -> bool:
    """Does this segment carry any diacritic at all?

    186 of the 8 330 مضارع records have a diacritic-stripped ``uthmani``, and on
    those the shadda test below cannot run — so they answer «cannot tell», which
    the caller turns into an omission.
    """
    return any(unicodedata.category(ch) == "Mn" for ch in text or "")


def _subject_region(word: dict) -> tuple[str, str]:
    """``(letters up to and including the subject suffix, that suffix verbatim)``.

    QAC segments a مضارع as ``PREFIX* STEM SUFFIX*`` where the **first** SUFFIX is
    the subject pronoun (يُسرعُ + ون) and any further one is an object pronoun or
    نون الوقاية. Stopping at the first suffix is load-bearing: تَكْفُرُونِ (2:152:6)
    is مجزوم بحذف النون and the ن a reader sees belongs to the *following* نون
    الوقاية segment — scanning past the subject would find a ن that is not نون
    الرفع and flip the verdict.
    """
    letters: list[str] = []
    suffix: str | None = None
    for segment in word.get("segments_detail") or []:
        if not isinstance(segment, dict):
            continue
        raw = segment.get("uthmani", "") or ""
        if segment.get("type") == "SUFFIX":
            if suffix is not None:
                break
            suffix = raw
        letters.append(_arabic_letters(raw))
    return "".join(letters), (suffix or "")


def _require_word_record(record: object) -> dict:
    """Return ``record`` if it is a QAC word record, else raise ``TypeError``.

    A word record is identified by its ``pos`` key, which all 77 429 records
    carry. **Wrong shapes raise instead of returning ``None``** — the one design
    decision this helper exists for. ``None`` is how :func:`verb_marker` says
    «the corpus does not show a marker here», so a caller who passes a bare
    ``features`` dict (accepted by :func:`case_marker`, useless here: the verbal
    path also reads ``pos``, ``root`` and ``segments_detail``) would get a
    silence indistinguishable from a grammatical omission — and that silence
    would then be rendered, logged and reconciled as a *deliberate* one.

    A raise is chosen over the alternative (``None`` plus a one-time warning)
    because this is a programming error, not a data condition: it is
    deterministic, it is always wrong, it cannot be fixed by better data, and a
    warning is emitted once and then routinely filtered out of a running
    service — exactly the invisibility being fixed.
    """
    if isinstance(record, dict) and "pos" in record:
        return record
    shown = sorted(record)[:6] if isinstance(record, dict) else type(record).__name__
    raise TypeError(
        "verb_marker() needs a full QAC word record with keys "
        "pos / features / root / segments_detail; got "
        f"{shown!r}. A bare `features` dict is accepted by case_marker() but not "
        "here: returning None for it would be indistinguishable from a "
        "grammatical omission, which is the one ambiguity the verified-datum "
        "badge cannot carry."
    )


def verb_marker(record: dict) -> str | None:
    """«الحالة + العلامة» for a مضارع — «مرفوع وعلامته ثبوت النون» — else None.

    ``record`` is a full QAC word record (``pos`` / ``features`` / ``root`` /
    ``segments_detail``) — the parameter is named as the written contract names
    it (tasks.md §3.1, ``verb_marker(record)``); there is no alias. Its
    ``features`` key is duck-typed exactly as in :func:`case_marker` (features
    may sit inline on the record), but unlike the nominal marker this one cannot
    work from a *bare* ``features`` dict, and it does not pretend otherwise:
    a wrong shape raises ``TypeError`` rather than returning ``None``
    (see :func:`_require_word_record` for why a raise and not a warning).

    Emitted:
      * **الأفعال الخمسة** get the full clause, because نون الرفع is the one
        marker the corpus actually *shows*: «مرفوع وعلامته ثبوت النون» /
        «مجزوم وعلامته حذف النون» / «منصوب وعلامته حذف النون».
      * every other مضارع gets the **mood word alone** (مرفوع / منصوب / مجزوم).
        الضمة / الفتحة / السكون would have to be inferred from the tag, and this
        module states only what it can read.

    Omitted — ``None``, never a guess — in six cases, each of which would
    otherwise produce a confident, complete, wrong line:

    1. **الماضي / الأمر** (11 026 words) are مبني: no lafẓī marker exists.
    2. **نون النسوة** (54): مبني على السكون في محل رفع/نصب/جزم — QAC's mood tag
       there is محلّي (it tags one on 22 of the 54), and rendering it as an إعراب
       marker is simply false.
    3. **نون / ألف التوكيد** (256 + 3): a مضارع joined to it is مبني على الفتح
       **and** its نون الرفع is gone, so 3:81:17 لَتُؤْمِنُنَّ (2MP, indicative)
       would come out «مرفوع وعلامته ثبوت النون» — asserting a نون that the word
       deleted. Detected on the shadda: نون التوكيد الثقيلة carries one and نون
       الرفع never does (4:16:2 يَأْتِيَانِهَا, «ٰنِ», is the one un-shadda'd bare
       ن and is correctly kept). An unvocalized record cannot be told apart, so
       it is omitted too — which is what makes this the largest guard: of the 256
       words it drops, 88 carry the shadda and 168 are diacritic-stripped
       «cannot tell» records. The ألف of نون التوكيد الخفيفة on a form with no
       subject suffix (96:15:5 لَنَسْفَعًۢا, 12:32:17 وَلَيَكُونًا) is 3 more.
    4. **The tag and the surface disagree** on an أفعال خمسة verb (22). QAC's mood
       is not always right and the نون is *visible*, so the surface arbitrates:
       4 words like 2:85:16 يَأْتُوكُمْ are tagged indicative but are فعل الشرط
       with the نون deleted, and 18 words like 2:272:28 تُظْلَمُونَ are tagged
       `MOOD:JUS` with the نون plainly there. Both directions are dropped rather
       than resolved.
    5. **A مجزوم whose root is ناقص/لفيف** (203). Here even the bare mood word
       misleads: printed in an «العلامة» field, «مجزوم» reads as بالسكون, while a
       معتل الآخر jussive is marked **بحذف حرف العلة** (فَلْيَدْعُ, وَلْيَخْشَ,
       يَأْتِ). Silence is the honest answer; :func:`classify_root` decides. The
       معتل الآخر jussive *population* is 209; 203 is what this guard drops,
       the other 6 having already been dropped by case 2 (5 نون النسوة) and
       case 3 (1 نون التوكيد). When `analysis.mizan` is unavailable the class
       cannot be read at all, and the guard then drops **every** non-khamsa
       jussive (658 more markers lost) and warns once — never assuming صحيح.
    6. Any ``verb_mood`` value outside the three mapped in :data:`VERB_MOOD_AR`.

    7 792 of the 8 330 مضارع verbs (93.5 %) produce a marker. The 538 omissions
    split across the guards as نون التوكيد 256 · ناقص/لفيف مجزوم 203 · نون النسوة
    54 · tag-vs-surface 22 · ألف التوكيد 3 — pinned by the tests so the split
    cannot drift silently, in either direction.
    """
    record = _require_word_record(record)
    if record.get("pos") != "V":
        return None
    features = record.get("features", record)
    if not isinstance(features, dict) or features.get("verb_aspect") != "IMPF":
        return None

    pgn = features.get("pgn")
    if pgn in _NUN_NISWA_PGN:
        return None

    # Absent `verb_mood` is the indicative: the raw column's null token `_`,
    # dropped by the ingestion, whose QAC tagset name is `MOOD:IND`.
    mood = features.get("verb_mood")
    mood_ar = VERB_MOOD_AR.get(mood or _MOOD_IND)
    if mood_ar is None:
        return None

    is_khamsa = pgn in _KHAMSA_PGN
    region, suffix = _subject_region(record)
    suffix_letters = _arabic_letters(suffix)

    # نون / ألف التوكيد — see case 3 of the docstring.
    if suffix_letters == "ن" and (_SHADDA in suffix or not _is_vocalized(suffix)):
        return None
    if not is_khamsa and suffix_letters == "ا":
        return None

    if is_khamsa:
        # نون الرفع can only sit on the subject pronoun, so read the last two
        # letters of the verb+subject region rather than the word's final letter
        # (which is an object pronoun in يَسْـَٔلُونَكَ).
        nun_present = (
            len(region) >= 2
            and region[-1] == "ن"
            and region[-2] in _SUBJECT_LETTERS
        )
        # مرفوع keeps نون الرفع; منصوب/مجزوم delete it. Both spellings of the
        # indicative are accepted — absent (today's ingestion) *and* the explicit
        # `MOOD:IND` a re-ingest would preserve — because the normalisation two
        # lines above already treats them as one and a bare `mood is None` here
        # would silently return None for all 2 541 of them.
        expects_nun = mood in (None, _MOOD_IND)
        if expects_nun != nun_present:
            return None  # tag vs. surface — case 4 of the docstring
        return mood_ar + _MARKER_JOIN + (_NUN_THABITA if nun_present else _NUN_MAHDHUFA)

    if mood == "MOOD:JUS" and _needs_root_class_omission(record.get("root")):
        return None  # مجزوم بحذف حرف العلة — case 5 of the docstring
    return mood_ar


# ─────────────────────────────────────────────────────────────────────────────
# 6. decompose_pgn — character-set classification (never positional).
# ─────────────────────────────────────────────────────────────────────────────

_PGN_PERSONS: frozenset[str] = frozenset({"1", "2", "3"})
_PGN_GENDERS: frozenset[str] = frozenset({"M", "F"})
_PGN_NUMBERS: frozenset[str] = frozenset({"S", "D", "P"})


def decompose_pgn(pgn: str | None) -> dict[str, str]:
    """Decompose a ``pgn`` code into its present raw parts by character set.

    Person ∈ {1,2,3}, gender ∈ {M,F}, number ∈ {S,D,P}, in any subset — so all
    25 corpus forms (``M``, ``F``, ``P``, ``2D``, ``3D``, ``3MS``, …) decompose
    correctly where a positional parser would break. Returns a dict with only the
    parts that are present, e.g. ``"3MS" -> {"person":"3","gender":"M","number":"S"}``,
    ``"M" -> {"gender":"M"}``, ``"2D" -> {"person":"2","number":"D"}``.

    The character sets are disjoint, so this round-trips: reassembling the parts
    in person→gender→number order reproduces the original code.
    """
    out: dict[str, str] = {}
    if not pgn:
        return out
    for ch in pgn:
        if ch in _PGN_PERSONS:
            out["person"] = ch
        elif ch in _PGN_GENDERS:
            out["gender"] = ch
        elif ch in _PGN_NUMBERS:
            out["number"] = ch
        else:
            raise ValueError(f"unmapped pgn character {ch!r} in {pgn!r}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 7. translate_features — ordered Arabic [{label_ar, value_ar}] list; raises on
#    any unmapped code (no raw passthrough).
# ─────────────────────────────────────────────────────────────────────────────

# Value-table lookup per feature key (special_group handled separately: strip SP:).
_VALUE_TABLES: dict[str, dict[str, str]] = {
    "nominal_case": NOMINAL_CASE_AR,
    "nominal_state": NOMINAL_STATE_AR,
    "verb_aspect": VERB_ASPECT_AR,
    "verb_form": VERB_FORM_AR,
    "verb_mood": VERB_MOOD_AR,
    "verb_voice": VERB_VOICE_AR,
    "derived_nouns": DERIVED_NOUNS_AR,
    "person": PERSON_AR,
    "gender": GENDER_AR,
    "number": NUMBER_AR,
}

# Fixed presentation order of feature rows.
_FEATURE_ORDER: tuple[str, ...] = (
    "nominal_case",
    "nominal_state",
    "verb_aspect",
    "verb_form",
    "verb_mood",
    "verb_voice",
    "derived_nouns",
    "special_group",
    "person",
    "gender",
    "number",
)


def _translate_special_group(value: str) -> str:
    """Strip the ``SP:`` prefix and map the Buckwalter token to Arabic."""
    token = value[3:] if value.startswith("SP:") else value
    try:
        return SPECIAL_GROUP_AR[token]
    except KeyError as exc:
        raise ValueError(f"unmapped special_group code {value!r}") from exc


def _translate_value(key: str, value: str) -> str:
    """Map a single feature value to Arabic, raising on any unmapped code."""
    if key == "special_group":
        return _translate_special_group(value)
    table = _VALUE_TABLES.get(key)
    if table is None:
        raise ValueError(f"unmapped feature key {key!r}")
    try:
        return table[value]
    except KeyError as exc:
        raise ValueError(f"unmapped {key} value {value!r}") from exc


def translate_features(features: dict) -> list[dict]:
    """Translate a raw QAC ``features`` dict into an ordered Arabic list.

    Returns ``[{"label_ar": ..., "value_ar": ...}, ...]`` in :data:`_FEATURE_ORDER`.

    * ``pgn`` is decomposed by character set and **merged** with any standalone
      ``person`` / ``gender`` / ``number`` — the standalone columns are
      authoritative and ``pgn`` only fills gaps, so «مذكّر / مفرد» appears once,
      never «pgn: M» + «gender: M».
    * **Every** key and value is mapped; an unmapped code raises ``ValueError``
      (no raw passthrough).
    """
    features = features or {}

    # Merge pgn into person/gender/number (standalone authoritative).
    pgn_parts = decompose_pgn(features.get("pgn"))
    merged: dict[str, str] = {}
    for part in ("person", "gender", "number"):
        if part in features:
            merged[part] = features[part]
        elif part in pgn_parts:
            merged[part] = pgn_parts[part]

    # Validate that no key is silently dropped (guard against corpus drift).
    known = set(_FEATURE_ORDER) | {"pgn"}
    for key in features:
        if key not in known:
            raise ValueError(f"unmapped feature key {key!r}")

    rows: list[dict] = []
    for key in _FEATURE_ORDER:
        if key in ("person", "gender", "number"):
            value = merged.get(key)
        else:
            value = features.get(key)
        if value is None:
            continue
        rows.append(
            {
                "label_ar": FEATURE_LABEL_AR[key],
                "value_ar": _translate_value(key, value),
            }
        )
    return rows


def translate_segments(segments: list | None) -> list[str]:
    """Map morphological segment codes to Arabic, raising on any unmapped code."""
    out: list[str] = []
    for seg in segments or []:
        try:
            out.append(SEGMENT_AR[seg])
        except KeyError as exc:
            raise ValueError(f"unmapped segment code {seg!r}") from exc
    return out


if __name__ == "__main__":
    from analysis.qlisan_data import qac_words

    words = qac_words()
    # One line per behaviour worth eyeballing: the pinned أفعال خمسة case, the two
    # deleted-nūn moods, a plain singular, and each family that is deliberately
    # silent (ماضٍ, أمر, نون النسوة, نون التوكيد, مجزوم معتلّ الآخر, tag≠surface).
    samples = [
        ("23:61:2", "أفعال خمسة مرفوع"),
        ("2:11:5", "أفعال خمسة مجزوم"),
        ("9:16:4", "أفعال خمسة منصوب"),
        ("1:5:2", "مضارع مفرد"),
        ("1:7:3", "ماضٍ"),
        ("1:6:1", "أمر"),
        ("2:228:2", "نون النسوة"),
        ("3:81:17", "نون التوكيد"),
        ("96:17:1", "مجزوم معتلّ الآخر"),
        ("2:272:28", "الوسم يخالف الظاهر"),
    ]
    for ref, note in samples:
        record = words[ref]
        print(f"{ref:10} {record.get('uthmani'):20} {note:22} -> {verb_marker(record)}")
    print()
    print("13:12:8 case_marker ->", case_marker(words["13:12:8"]))
    print("1:2:4   case_marker ->", case_marker(words["1:2:4"]))
    print()

    # The two observable failure modes, shown rather than described: a wrong
    # argument shape, and the root classifier being unavailable.
    print("root classifier available ->", _ROOT_CLASSIFIER_AVAILABLE)
    try:
        verb_marker(words["23:61:2"]["features"])
    except TypeError as exc:
        print("bare features dict ->", type(exc).__name__)
    _ROOT_CLASSIFIER_AVAILABLE = False
    _MUTALL_AL_AKHIR = frozenset()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        degraded = [verb_marker(words[ref]) for ref in ("23:61:2", "96:17:1", "2:6:9")]
    print("no classifier -> 23:61:2", degraded[0], "· 96:17:1", degraded[1],
          "· 2:6:9 (صحيح مجزوم)", degraded[2], f"· warnings={len(caught)}")
