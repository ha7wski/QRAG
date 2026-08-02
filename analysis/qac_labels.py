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
