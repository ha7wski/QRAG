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

**Three layers, in order.** A bare letter-walk is exact only for sound roots whose
radicals surface unchanged, so two layers run ahead of it:

1. **Classify the root** — `classify_root` gives the weak-letter class (حرف علة is و/ي
   only), and `hamza_positions` the hamzated radicals as a *separate* attribute, since a
   root is frequently both (آلاء, QAC root الو, is ناقص with a hamzated فاء — not لفيف).
   The class gates every إعلال rule: a sound root reaches none of them, which is what
   keeps regular words projecting exactly as they always did.
2. **Match a curated wazn pattern** (`analysis/data/mizan_patterns.json`) — a جمع تكسير
   is a *template*, not a projection of the root, so the letter-walk can only get it
   wrong: for آلاء it binds the ء to the لام slot and reports «فعَال». A pattern hit
   emits its canonical mīzān (أَفْعَال) and stops.
3. **Project**, now tolerant of إعلال/إبدال: a weak radical may have turned into another
   letter (قَالَ, root قول), vanished (يَعِدُ/يَدْعُ/قُلْ), or merged with its twin under a
   shadda (مَدَّ, root مدد). Each acceptance is named in `rules`.

**Confidence flag.** `verified=True` when a pattern matched, or the projection resolved
every radical — possibly through a recorded rule. `verified=False` only when the word is
genuinely uncovered, and it is then rendered as an heuristic «اجتهادي» hint outside the
«معطى محقّق» badge. Because a verified mīzān carries the badge, the bar for claiming it is
deliberately conservative: an alignment that needed **two** different إعلال rules to close
is rejected (`_plausible`), and the assimilated تاء الافتعال (مُتَّقِين, root وقي) is left
uncovered rather than guessed, since one surface letter there stands for two mīzān letters.
An honest اجتهادي beats a confidently wrong mīzān under the badge.

Pure stdlib + local corpus indexes (no LLM, no network). QAC source data is never
altered — the mīzān is derived here at assembler time.
"""
from __future__ import annotations

import functools
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.qlisan_data import word_index
from ingestion.root_normalize import normalize_root
from indexing.corpus import chakl_by_ref

# Combining marks we copy verbatim onto the mīzān (ḥarakāt, tanwīn, shadda, sukūn,
# dagger alif). Detection also falls back to the Unicode "Mn" (nonspacing mark)
# category so any stray combining mark is treated as a diacritic, not a letter.
_SHADDA = "ّ"
_SUKUN = "ْ"
_FATHA = "َ"
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

    **Every hamza carrier folds — the seats ؤ/ئ and the bare ء alike.** A hamza written on
    a wāw or yāʾ seat, or on the line, is the same hamza; the seat is an orthographic
    choice driven by the surrounding vowels, not a mutated radical. Omitting the seats
    made مُؤْمِنِين (root امن) match *zero* radicals and emit itself verbatim; omitting the
    bare ء left every مهموز اللام stranded (شَيْء, root شيا → «فَعْء» instead of «فَعْل»).
    This is deliberately **not** modelled as إعلال بالقلب: it is spelling normalization,
    it needs no root class to license it, and keeping it here avoids inflating the
    traced-rule set with an orthographic detail.
    """
    if ch in "أإآٱؤئء":  # أ إ آ ٱ ؤ ئ ء → ا
        return "ا"
    if ch == "ة":  # ة → ت
        return "ت"
    if ch == "ى":  # ى → ي
        return "ي"
    return ch


# --- root classification ------------------------------------------------------
# A حرف علة is و or ي — **and nothing else**. Hamza is not one: آلاء (QAC root الو) is
# ناقص واوي whose فاء happens to be hamzated, not لفيف. Since the class is exposed in the
# result, it must be a defensible label, so hamza is reported as a *separate* attribute
# (`hamza_positions`) rather than as a rival class — a root is frequently both.

_WEAK_LETTERS = frozenset("وي")

# In a QAC *root*, an alif is always a folded hamza (roots are stored hamza-folded:
# سأل → سال, نشأ → نشا, آلاء → الو); Arabic has no bare-alif radical. The seated forms
# are listed too so the function works on an unfolded root as well.
_ROOT_HAMZA = frozenset("ءأإآٱئؤا")

CLASS_SALIM = "صحيح سالم"
CLASS_MUDAAF = "مضاعف"     # radical₂ == radical₃
CLASS_MITHAL = "مثال"      # radical₁ weak
CLASS_AJWAF = "أجوف"       # radical₂ weak
CLASS_NAQIS = "ناقص"       # radical₃ weak
CLASS_LAFIF = "لفيف"       # two weak radicals
CLASS_RUBAI = "رباعي"      # quadriliteral

# Classes that license an إعلال rule (the D2/D3 guardrail): a sound root must never
# reach a قلب/حذف path, which is what keeps regular words regular.
WEAK_CLASSES = frozenset({CLASS_MITHAL, CLASS_AJWAF, CLASS_NAQIS, CLASS_LAFIF})


def classify_root(root: str | None) -> str:
    """The root's weak-letter class — one of the CLASS_* constants above.

    Precedence is fixed and load-bearing (overlaps must resolve the same way every
    time): **لفيف → مضاعف → أجوف → ناقص → مثال → صحيح سالم**, with رباعي short-circuiting
    on four-letter roots. لفيف comes first because two weak radicals also satisfy the
    single-position tests; مضاعف precedes the positional tests so a doubled root is never
    reported as أجوف/ناقص.

    Hamza plays no part here — see `hamza_positions`.
    """
    letters = list(root or "")
    if len(letters) == 4:
        return CLASS_RUBAI
    if len(letters) != 3:
        return CLASS_SALIM
    weak = [i for i, ch in enumerate(letters) if ch in _WEAK_LETTERS]
    if len(weak) >= 2:
        return CLASS_LAFIF
    if letters[1] == letters[2]:
        return CLASS_MUDAAF
    if 1 in weak:
        return CLASS_AJWAF
    if 2 in weak:
        return CLASS_NAQIS
    if 0 in weak:
        return CLASS_MITHAL
    return CLASS_SALIM


def hamza_positions(root: str | None) -> tuple[int, ...]:
    """0-based radical positions carrying a hamza — orthogonal to `classify_root`.

    Reported for traceability/display only; it deliberately gates **no** إعلال rule,
    because hamza needs none: `_fold` reconciles every hamza carrier with the folded
    root form, so a hamzated radical matches by the ordinary path.
    """
    return tuple(i for i, ch in enumerate(root or "") if ch in _ROOT_HAMZA)


# --- radical ↔ surface matching ----------------------------------------------
# Every acceptance path is named, so a mīzān can say *how* each radical was resolved.
# Rules beyond the plain match are **gated on the root class**: that gate is the whole
# safety story — a صحيح سالم root can never reach a قلب/حذف path, so regular words keep
# projecting exactly as they did before.

RULE_DIRECT = "مطابقة"           # the letter is the radical (or a folded variant of it)
RULE_QALB = "إعلال بالقلب"       # a weak radical surfaced as a different letter

# Post-fold surface letters a weak (و/ي) radical may have turned into: ا (قَالَ, root قول),
# ى, ء (دُعَاء and آلاء, roots دعو/الو), or the other weak letter (قِيلَ, root قول).
# `_fold` already maps ى→ي and every hamza carrier→ا, so this set is small.
_QALB_SURFACE = frozenset("اويء")

RULE_HADHF = "إعلال بالحذف"      # a weak radical is deleted on the surface
RULE_IDGHAM = "إدغام"            # a geminate's twin radicals merge under one shadda

# The pre-إدغام أصل of a geminate triliteral, kept for display/traceability: مَدَّ is
# فَعَّ on the surface and فَعَلَ underneath (أصله مَدَدَ). The emitted mīzān is the fused
# form — it is what the module's verbatim-vocalization contract produces, and it is the
# only form that composes with the rest of the word (رَبِّهِمْ → فَعِّهِمْ, رَبَّكُمُ →
# فَعَّكُمُ); un-fusing the stem while its suffix still carries the fused vowel would
# emit something no reader could match against the surface.
IDGHAM_ASL = "فَعَلَ"

# Classes whose weak radical may vanish entirely: the فاء of a مثال in the مضارع
# (يَعِدُ < وعد), the عين of an أجوف in the jussive/imperative and before a consonant-
# initial suffix (قُلْ, كُنْتُمْ < قول/كون), the لام of a ناقص in the jussive/imperative
# (يَدْعُ < دعو), and either of a لفيف's two weak radicals (يُوحَ < وحي).
_ELISION_CLASSES = frozenset({CLASS_MITHAL, CLASS_AJWAF, CLASS_NAQIS, CLASS_LAFIF})

# Imperfective prefixes. A مثال loses its فاء in the مضارع, so the stem then opens with
# one of these (يَعِدُ, تَعِدُ, نَعِدُ, أَعِدُ) — or with the عين itself, in the imperative
# (عِدْ, قِ). Used to license فاء-deletion; see `_elision_allowed`.
_IMPF_PREFIXES = frozenset("يتأن")


def _elision_allowed(
    radical: str, root_class: str, position: int,
    groups: list[list], radicals: list[str],
) -> bool:
    """May this radical be consumed with no surface letter (إعلال بالحذف)?

    The عين/لام case is licensed by class alone. The **فاء** case is narrower: a weak
    فاء disappears in the مضارع/أمر of a مثال, where the stem opens with an imperfective
    prefix or directly with the عين. Without that condition the rule also fired on
    form-VIII participles, where the فاء is *assimilated into* the تاء الافتعال rather
    than deleted (مُتَّقِين, root وقي) — producing a complete-looking but wrong alignment
    that then claimed `verified`. Those words are left honestly اجتهادي instead.
    """
    # Through the fold, like every curated root list: these entries are written
    # `راي` while the corpus now stores `رأي`. Matching raw would silently drop the
    # يَرَى exception and weigh نَرَىٰ as نَفَى instead of نَفَل.
    curated = normalize_root("".join(radicals)) in {
        normalize_root(r) for r in hamza_elision_roots()
    }
    if radical in _ROOT_HAMZA and curated:
        pass  # a named exception: يَرَى drops its عين, كُلْ/خُذْ/مُرْ their فاء
    elif radical not in _WEAK_LETTERS or root_class not in _ELISION_CLASSES:
        return False
    if position == 0:
        if not groups:
            return False
        first = _fold(groups[0][0])
        opens_with_ayn = len(radicals) > 1 and first == _fold(radicals[1])
        return first in _IMPF_PREFIXES or opens_with_ayn
    return True


def _match_radical(
    letter: str,
    radical: str,
    root_class: str,
    position: int,
    n_radicals: int,
    in_pattern: bool = False,
) -> tuple[bool, str | None]:
    """Does `letter` realise `radical`? Returns (matched, rule name).

    `position` is the radical's 0-based index and `n_radicals` the root length; both are
    passed so a rule can be restricted to the ف/ع/ل slot it actually licenses.

    `in_pattern` relaxes the فاء restriction below. Inside a curated template the فاء
    slot is *pinned* by the fixed letters around it (the م and ا of مِفْعَال), so قلب
    there cannot wander onto a prefix the way it does in the free projection.
    """
    if _fold(letter) == _fold(radical):
        return True, RULE_DIRECT
    # إعلال بالقلب — licensed only when *this radical* is a حرف علة and the root is in a
    # weak class. A sound root has no weak radical, so it can never reach this branch:
    # that is the guardrail that keeps regular words projecting exactly as before.
    #
    # Never at the فاء (`position == 0`). قلب is a property of the عين and the لام
    # (قَالَ, بَاعَ, دَعَا, رَمَى); a weak فاء is instead either present, deleted
    # (إعلال بالحذف — يَعِدُ), or assimilated (إبدال — اتَّقَى). Allowing it here made the
    # imperfective prefix ي/ت/أ/ن get eaten as if it were the radical: يَعِدُ (root وعد)
    # came out «فَعِل» and يُوحَ (root وحي) «فُوع», both wrongly `verified` — a mīzān that
    # is confidently wrong under the badge, which is worse than an honest اجتهادي.
    if root_class in WEAK_CLASSES and radical in _WEAK_LETTERS and (position > 0 or in_pattern):
        if _fold(letter) in _QALB_SURFACE:
            return True, RULE_QALB
    return False, None


def _stem_end(groups: list[list], record: dict) -> int:
    """Index just past the last stem letter — radicals never live in a SUFFIX.

    `groups` has already had its proclitics stripped, so only the trailing pronoun /
    subject suffixes remain to be excluded. Falls back to the full length whenever the
    QAC segment letter counts do not reconcile with the surface, so a mis-segmented word
    degrades to the previous behaviour rather than losing letters.
    """
    detail = record.get("segments_detail") or []
    if not detail:
        return len(groups)
    counts = {"PREFIX": 0, "STEM": 0, "SUFFIX": 0}
    for seg in detail:
        n = sum(1 for ch in seg.get("uthmani", "") if _is_letter(ch))
        counts[seg.get("type", "STEM")] = counts.get(seg.get("type", "STEM"), 0) + n
    if counts["STEM"] + counts["SUFFIX"] != len(groups):
        return len(groups)
    return len(groups) - counts["SUFFIX"]


def _align_radicals(
    groups: list[list], radicals: list[str], root_class: str,
    stem_end: int | None = None, allow_idgham: bool = True,
) -> tuple[dict[int, tuple[int, str]], list[str], int]:
    """Map each radical to the surface group that realises it.

    Returns `({group_index: (radical_index, rule)}, [rule names], resolved_count)`.
    Radicals are consumed in order, so the mapping is always increasing. `resolved_count`
    includes radicals accounted for by **إعلال بالحذف** — deleted on the surface and
    consumed with no output letter — which have no group index at all.

    Scanning is **earliest-first**, which reproduces the historical greedy behaviour
    exactly — with one exception. The *final* radical of a ناقص/لفيف root is scanned
    **from the end** when it is weak, because a word-final weak radical is realised by
    the last letter, not the first plausible one. Without that, دُعَاء (root دعو) would
    bind its و to the lengthening alif of the فُعَال pattern and emit «فُعَلء»; scanning
    backwards binds the ء that actually *is* the mutated و, giving «فُعَال». Same for
    سَمَاء (root سمو). Non-final radicals keep earliest-first, so قَالُوا still resolves
    ق→ف, ا→ع, ل→ل rather than skipping ahead to the suffix و.
    """
    slots: dict[int, tuple[int, str]] = {}
    rules: list[str] = []
    n = len(radicals)
    limit = len(groups) if stem_end is None else stem_end
    cursor = 0
    resolved = 0
    skip_next = False
    for i, radical in enumerate(radicals):
        if skip_next:  # consumed by the preceding letter's إدغام
            skip_next = False
            continue
        window = range(cursor, limit)
        # word-final weak radical ⇒ scan backwards (see docstring)
        if (i == n - 1 and radical in _WEAK_LETTERS
                and root_class in (CLASS_NAQIS, CLASS_LAFIF)):
            window = reversed(window)
        for j in window:
            hit, rule = _match_radical(groups[j][0], radical, root_class, i, n)
            if hit:
                slots[j] = (i, rule)
                cursor = j + 1
                resolved += 1
                if rule and rule != RULE_DIRECT and rule not in rules:
                    rules.append(rule)
                # إدغام — a geminate root writes its identical last two radicals as ONE
                # letter carrying a shadda (مَدَّ < مَدَدَ, رَبِّهِمْ < رَبِبِهِمْ). That
                # letter realises both, so consume the twin here instead of leaving it
                # stranded. Deterministic, not a guess: the mīzān of a geminate is known.
                if (allow_idgham and i + 1 < n and radicals[i + 1] == radical
                        and _SHADDA in groups[j][1]):
                    skip_next = True
                    resolved += 1
                    if RULE_IDGHAM not in rules:
                        rules.append(RULE_IDGHAM)
                break
        else:
            # إعلال بالحذف — the radical is nowhere in the remaining window. For a weak
            # radical in a class that licenses deletion (يَعِدُ drops its فاء, يَدْعُ and
            # يُوحَ their لام) that absence *is* the derivation, so consume it with no
            # output letter and carry on. Note this fires only after the whole window
            # came up empty, so a radical that is actually present is never "deleted".
            if _elision_allowed(radical, root_class, i, groups, radicals):
                resolved += 1
                if RULE_HADHF not in rules:
                    rules.append(RULE_HADHF)
                continue
            break  # radical unresolved — the projection is incomplete
    return slots, rules, resolved


def _plausible(rules: list[str]) -> bool:
    """Reject an alignment that leaned on more than one إعلال rule to close.

    Stacking قلب *and* حذف on a single triliteral means the walk bent the word twice to
    make the radicals fit, and the results were not trustworthy: تَقِيًّا (root وقي) came
    out «تَعِيًّل», emitting a letter after the word-final tanwīn, yet claimed `verified`.
    Nine words corpus-wide are affected and they now stay honestly اجتهادي — the whole
    point of the flag is that a reader can trust what carries the «معطى محقّق» badge, so
    a handful of uncovered words costs far less than a confidently wrong mīzān.
    """
    return sum(1 for rule in rules if rule.startswith("إعلال")) <= 1


def _slot_diacritics(letter: str, diacritics: list[str], rule: str) -> str:
    """The diacritics the mīzān slot carries for a radical realised by `letter`.

    Verbatim, with one exception: a radical that surfaced as a **bare alif** through
    إعلال بالقلب. An alif cannot carry a ḥarakah — it *is* a lengthened fatḥah, and the
    vowel it lengthens sits on the preceding letter. Copying "nothing" would emit قَالَ →
    «فَعل» with a vowelless عين; restoring the fatḥah gives the taught «فَعَلَ» (and
    قَالُوا → «فَعَلُوا»). Restricted to alif because و/ي *can* bear a vowel, so a bare one
    is genuinely unvocalized rather than a stand-in for a missing ḥarakah.
    """
    if rule == RULE_QALB and not diacritics and _fold(letter) == "ا":
        return _FATHA
    return "".join(diacritics)


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


# --- curated wazn patterns ----------------------------------------------------

RULE_PATTERN = "مطابقة وزن"      # a curated wazn pattern matched the stem

_PATTERNS_PATH = ROOT / "analysis" / "data" / "mizan_patterns.json"
_MADDA = "آ"
_SLOT_LETTERS = ("ف", "ع", "ل")
_SHORT_VOWELS = frozenset("َُِ")


@functools.lru_cache(maxsize=1)
def _pattern_file() -> dict:
    if not _PATTERNS_PATH.exists():
        return {}
    with _PATTERNS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def patterns() -> tuple[dict, ...]:
    """The curated wazn table, in file order (first hit wins). Empty if absent."""
    return tuple(_pattern_file().get("patterns") or [])


@functools.lru_cache(maxsize=1)
def hamza_elision_roots() -> frozenset[str]:
    """Roots whose hamza radical is simply dropped (يَرَى, كُلْ, خُذْ, مُرْ).

    A curated closed class, deliberately not a general rule: deletion is otherwise
    reserved for و/ي radicals, and licensing it for hamza everywhere would let it fire
    on any hamzated root that came up short.
    """
    special = _pattern_file().get("special_cases") or {}
    return frozenset((special.get("hamza_elision_roots") or {}).get("roots") or ())


@functools.lru_cache(maxsize=1)
def _not_weighed() -> tuple[dict, ...]:
    special = _pattern_file().get("special_cases") or {}
    return tuple(special.get("not_weighed") or ())


def is_weighed(record: dict, root: str | None) -> bool:
    """False for words the mīzān does not apply to (الأعلام لا توزن).

    A curated list, not a POS-wide rule: most proper nouns are rootless in QAC and never
    reach the mīzān anyway, so only the named entries are excluded.
    """
    for entry in _not_weighed():
        # Compare through the fold: the curated list is written in whichever spelling
        # its author used (`اله`), while the corpus now stores the exact one (`أله`).
        # Matching on the raw strings would silently let لفظ الجلالة back onto the mīzān.
        if entry.get("root") and normalize_root(entry["root"]) != normalize_root(root or ""):
            continue
        if entry.get("lemma") and entry["lemma"] != record.get("lemma"):
            continue
        if entry.get("pos") and entry["pos"] != record.get("pos"):
            continue
        return False
    return True


def _expand_madda(groups: list[list]) -> list[list]:
    """Rewrite آ as the two letters it stands for: أ followed by a quiescent ا.

    Alif-madda is a *ligature* — أَ + ءْ/ا collapsed into one glyph. آلاء is أَءْلَاو
    underneath, so a five-slot template like أَفْعَال can never align with its four
    written letters until the madda is expanded. Only used for pattern matching; the
    raw projection keeps working on the written letters.
    """
    out: list[list] = []
    for letter, diacritics in groups:
        if letter == _MADDA:
            out.append(["أ", [d for d in diacritics if d in _SHORT_VOWELS] or [_FATHA]])
            out.append(["ا", []])
        else:
            out.append([letter, list(diacritics)])
    return out


def _template_slots(mizan_text: str) -> list[list]:
    """Tokenize a canonical mīzān; its ف/ع/ل letters are the radical slots."""
    return _tokenize(mizan_text)


def _match_pattern(
    pattern: dict, groups: list[list], radicals: list[str], root_class: str
) -> bool:
    """Does this stem realise the pattern, with its radicals in the ف/ع/ل slots?

    Letters must match exactly (folded): that is what keeps a pattern from swallowing an
    unrelated word. Short vowels must agree wherever both sides carry one, except on the
    final letter, whose ḥarakah is iʿrāب and varies with sentence position. Sukūn/tanwīn
    differences are ignored for the same reason.
    """
    template = _template_slots(pattern.get("mizan", ""))
    if len(template) != len(groups):
        return False
    slot = 0
    last = len(template) - 1
    for i, ((t_letter, t_diacritics), (s_letter, s_diacritics)) in enumerate(
        zip(template, groups)
    ):
        if t_letter in _SLOT_LETTERS and slot < len(radicals):
            hit, _ = _match_radical(
                s_letter, radicals[slot], root_class, slot, len(radicals), in_pattern=True
            )
            if not hit:
                return False
            slot += 1
        elif _fold(t_letter) != _fold(s_letter):
            return False
        if i != last:
            t_vowel = {d for d in t_diacritics if d in _SHORT_VOWELS}
            s_vowel = {d for d in s_diacritics if d in _SHORT_VOWELS}
            if t_vowel and s_vowel and t_vowel != s_vowel:
                return False
    return slot == len(radicals)


def _pattern_mizan(
    groups: list[list], radicals: list[str], root_class: str, number: str | None
) -> str | None:
    """First matching pattern's canonical mīzān, or None.

    Candidates are *ordered* by the QAC `number` feature — a word tagged `"P"` tries the
    جمع تكسير templates first — which is what separates the singular كِتَاب from the
    plural رِجَال when both surface as فِعَال. Ordering only: the other family stays
    reachable, so a record with a missing or unexpected `number` still matches rather
    than failing. Never tested against `"S"`: singulars carry no `number` at all.
    """
    table = patterns()
    if not table:
        return None
    plural_first = number == "P"
    ordered = sorted(table, key=lambda p: (p.get("family") == "plural") != plural_first)
    expanded = _expand_madda(groups)
    for pattern in ordered:
        for candidate in (groups, expanded):
            if _match_pattern(pattern, candidate, radicals, root_class):
                return pattern.get("mizan")
    return None


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
    base = {
        "available": False,
        "wazn": None,
        "verified": False,
        "bab": bab,
        "root_class": classify_root(root) if root else None,
        "hamza_positions": list(hamza_positions(root)) if root else [],
        "rules": [],
        "asl": None,
    }
    if not root or not is_weighed(record, root):
        # الأعلام لا توزن — a علم has no mīzān to report, so the row is omitted rather
        # than filled with a heuristic guess (لفظ الجلالة was emitting «لَّه» as اجتهادي).
        return base

    try:
        surah, ayah, word = (int(p) for p in ref.split(":"))
    except (ValueError, AttributeError):
        return base

    surface = _vocalized_surface(surah, ayah, word)
    if not surface:
        return base

    segments = record.get("segments", []) or []
    groups = _strip_proclitics(_tokenize(surface), segments)

    radicals = list(root)
    root_class = base["root_class"]
    targets = _TARGETS[: len(radicals)]

    # Layer 2b — curated patterns run BEFORE the projection. A broken plural is a
    # template, not a linear projection of the root, so the letter-walk can only get it
    # wrong: for آلاء it binds the ء to the لام slot and reports «فعَال» as verified.
    # A pattern hit emits its canonical mīzān and stops.
    hit = _pattern_mizan(
        groups, radicals, root_class, (record.get("features") or {}).get("number")
    )
    if hit:
        return {**base, "available": True, "wazn": hit, "verified": True,
                "rules": [RULE_PATTERN]}
    # Prefer an alignment confined to the stem — radicals belong there, and without the
    # cap the backward scan happily binds a suffix letter (اشْتَرَوُا would take the ا of
    # the subject وا as its لام). But the cap cannot be absolute: QAC sometimes puts the
    # segment boundary *inside* a geminated letter, so the final radical is counted in
    # the suffix (لَعَنَّا = STEM «لَعَ» + SUFFIX «نَّآ», where نّ carries the ن radical).
    # So: try the stem window, and fall back to the whole word when that leaves radicals
    # unresolved. Any word that resolved before still resolves.
    # Attempts are ordered by how much licence they take, and the first one that resolves
    # every radical wins. Two preferences are encoded:
    #   * stem window before the whole word — radicals belong to the stem;
    #   * no-إدغام before إدغام — a shadda is not always root gemination. In form II/V it
    #     is the *pattern* doubling the عين (عَدَّدَهُ, root عدد, is فَعَّلَهُ), and letting
    #     إدغام fire there swallowed the لام and emitted «فَعَّدَهُ».
    # When nothing resolves fully we keep the widest, most conservative reading, which is
    # what the projection produced before this layer existed.
    stem_end = _stem_end(groups, record)
    full = len(groups)
    attempts = [(stem_end, False), (stem_end, True), (full, False), (full, True)]
    slots, rules, resolved = _align_radicals(groups, radicals, root_class, full, False)
    for window, idgham in attempts:
        cand_slots, cand_rules, cand_resolved = _align_radicals(
            groups, radicals, root_class, window, idgham
        )
        if cand_resolved == len(radicals) and _plausible(cand_rules):
            slots, rules, resolved = cand_slots, cand_rules, cand_resolved
            break
    out: list[str] = []
    for j, (letter, diacritics) in enumerate(groups):
        if j in slots:
            radical_index, rule = slots[j]
            out.append(targets[radical_index] + _slot_diacritics(letter, diacritics, rule))
        else:
            out.append(letter + "".join(diacritics))

    verified = resolved == len(radicals) and _plausible(rules)
    base["rules"] = rules
    if RULE_IDGHAM in rules and len(radicals) == 3:
        # The fused form is what we emit; the أصل is kept so the UI can show «أصله فَعَلَ».
        base["asl"] = IDGHAM_ASL
    wazn = "".join(out)
    # Drop the single trailing inflectional mark (iʿrāب ḥarakah / sukūn) on the last
    # radical so the mīzān shows the pattern, not the sentence-position case — but only
    # when no pronoun suffix follows (then the trailing mark belongs to the suffix).
    if "SUFFIX" not in segments and wazn and wazn[-1] in _HARAKAT and wazn[-1] != _SHADDA:
        wazn = wazn[:-1]

    return {**base, "available": bool(wazn), "wazn": wazn, "verified": verified}
