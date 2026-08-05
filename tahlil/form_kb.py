"""
form_kb.py — the versioned دلالة الصيغة knowledge base and the باب contrast table.

**Why a curated file and not a prompt.** Asking a model «ما دلالة صيغة المفاعلة؟» yields
fluent, sourceless Arabic — the exact failure mode that killed `lisan/`'s synthesis and
that `madar/` gates off by default. A KB row instead carries a *named* صرف/نحو/بلاغة
provenance, so a form claim resolves to a citation a reader can check. That is the whole
value of the table, which is why both loaders **raise** on a row with no provenance and on
a file with no `meta.version`: an unsourced row is a silent wrong-answer generator, and an
unversioned file silently poisons the analysis cache (the key folds `kb_version()` in).

**Why senses are a list, always.** المفاعلة means المشاركة *or* المبالغة/طلب الفعل; باب
استفعل means الطلب *or* التحوّل *or* اعتقاد الصفة. Collapsing a multi-sense form to one
asserted meaning would turn a reading into a lookup, and the citation gate could no longer
tell the two apart. So the KB never asserts «this form means X»; it enumerates the
alternatives, marks the row `multi_sense`, and leaves the *selection* to a claim that must
pay for it with a corpus disambiguator (design decision 3 / spec §5.3). `multi_sense` is
the flag that drives that badge rule downstream — it is computed here, from the data,
never carried in the file.

**Why the keys are never re-typed.** A KB key must byte-match what `analysis/mizan.py`
emits, and a missing ḥarakah is invisible on screen while making the row permanently
unreachable. The shipped `key` values are therefore generated *from* `mizan._VERB_BAB_AR`,
`qac_labels.VERB_ASPECT_AR` and `qac_labels.DERIVED_NOUNS_AR`, and a drift guard in the
test suite re-checks them against what `compute_mizan` actually produces over the corpus.

**Routing.** Verbs go on باب + الزمن; nominals on the derived-noun feature + the mīzān
(باب is `None` for 100 % of nouns — 61.3 % of rooted words — so a باب-only KB would leave
the nominal صرفي block permanently empty). The two routes never mix, and the collision is
measured rather than hypothetical: **371 verbs project to a mīzān that is also a shipped
nominal wazn key** — 247 to «أَفْعَل» (e.g. 2:22:8 أَنزَلَ) and 124 to «فَعِل» (e.g.
2:38:10, 2:62:13). Letting them cross would hand the form-IV verb أَنزَلَ an اسم تفضيل
reading and the form-I verb تَبِعَ a صفة مشبهة one. Note that «فَعَل» — where a form-I
past verb lands — is *not* a shipped wazn key, so that string is not the hazard; the two
above are.

Pure stdlib + local reference files (no LLM, no network, no fastapi/pydantic).
"""
from __future__ import annotations

import copy
import functools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.qac_labels import DERIVED_NOUNS_AR, VERB_ASPECT_AR

REFERENCES = ROOT / "data" / "references"
SIGHA_PATH = REFERENCES / "sigha_dalala.json"
CONTRAST_PATH = REFERENCES / "bab_contrast.json"

# Presentation order of matched rows: «most specific first». باب and المشتقّ *name* the
# word's صيغة outright; الوزن is a projection several صيغ can share (فَعِيل is صفة مشبهة
# and مبالغة and بمعنى مفعول); الزمن is cross-cutting and qualifies whatever صيغة it sits
# on. So a caller reading top-down meets the identity of the form before its qualifiers.
_KEY_TYPE_ORDER: tuple[str, ...] = ("bab", "derived_noun", "wazn", "aspect")
KEY_TYPES: frozenset[str] = frozenset(_KEY_TYPE_ORDER)

# Tanwīn marks + the accusative-indefinite alif that carries fatḥatān. Stripped from a
# projected mīzān before it is used as a KB key: nunation is iʿrāb, not part of the
# pattern, and the corpus splits one pattern across both spellings (1 441 words project
# to «فَعِيل» and a further 595 to «فَعِيلًا»). Keying on the raw string would make the
# second group silently miss every wazn row. Measured over the whole corpus, **703
# nominal words owe their wazn row to this fold alone** — فَعِيلًا 595 · فَعُولًا 71 ·
# فَعِلًا 26 · مَفْعَلًا 6 · مِفْعَالًا 5 — and losing them raises no error, so the count
# is pinned in the test suite.
_TANWIN = "ًٌٍ"


# ─────────────────────────────────────────────────────────────────────────────
# Loading + validation
# ─────────────────────────────────────────────────────────────────────────────


def validate_kb(data: dict, source: str = "<memory>") -> dict:
    """Return `data` unchanged, or raise if it is not a shippable KB.

    Exposed (rather than buried in the loaders) so the contract can be tested against a
    synthetic dict with no file on disk. Two checks, both fatal by design:

    * **`meta.version`** — the version participates in every `cite_id` and in the analysis
      cache key. A file that bumps its rows without bumping its version would serve stale
      cached prose under new evidence, and nothing downstream could detect it.
    * **`provenance` on every row** — the KB's only reason to exist is that its claims are
      attributable. A row with none is indistinguishable from invented content once it has
      been cited.
    """
    if not isinstance(data, dict):
        raise ValueError(f"{source}: KB must be a JSON object, got {type(data).__name__}")
    meta = data.get("meta")
    version = meta.get("version") if isinstance(meta, dict) else None
    if not version or not str(version).strip():
        raise ValueError(f"{source}: KB has no meta.version — refusing to load")
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{source}: KB has no rows")
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{source}: row {i} is not an object")
        row_id = row.get("id") or f"#{i}"
        if not (row.get("provenance") or "").strip():
            raise ValueError(f"{source}: row {row_id!r} has no provenance — refusing to load")
    return data


def _read(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — the دلالة الصيغة KB ships with the repo.")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def load_sigha() -> dict:
    """The دلالة الصيغة KB, validated. Read-only: callers must not mutate it."""
    data = validate_kb(_read(SIGHA_PATH), str(SIGHA_PATH))
    for row in data["rows"]:
        key_type = row.get("key_type")
        if key_type not in KEY_TYPES:
            raise ValueError(f"{SIGHA_PATH}: row {row.get('id')!r} has key_type {key_type!r}")
        if not (row.get("senses") or []):
            raise ValueError(f"{SIGHA_PATH}: row {row.get('id')!r} has no senses")
    return data


def validate_contrast(data: dict, source: str = "<memory>") -> dict:
    """Return `data` unchanged, or raise if it is not a shippable contrast table.

    Exposed like `validate_kb` so the contract is testable on a synthetic dict. On top of
    the generic checks, the contrast-specific ones — all fatal:

    * **`bab` present and non-empty.** `_contrast_index()` keys rows on it and would
      otherwise **silently drop** an unkeyed row: a misspelled or missing باب makes the
      whole row unreachable, and the باب it was written for then looks, downstream, like a
      باب the tradition opposes to nothing.
    * **`against` non-empty.** Same failure with the same signature — an empty list is
      indistinguishable from «no opposition exists».
    * **every target carries `bab`, `pos` and `verb_form`.** Those are exactly the
      granularity the §4.6 attestation check needs; a target missing one forces the check
      back to the root, which is the check that inverts the pinned word's verdict.
      `verb_form` may be `None` (form I is unmarked in QAC) — the **key** must be present,
      not the value.
    """
    validate_kb(data, source)
    for i, row in enumerate(data["rows"]):
        row_id = row.get("id") or f"#{i}"
        if not (row.get("bab") or "").strip():
            raise ValueError(f"{source}: contrast row {row_id!r} has no bab — it would be unreachable")
        against = row.get("against")
        if not isinstance(against, list) or not against:
            raise ValueError(f"{source}: contrast row {row_id!r} has no against targets")
        for target in against:
            if not isinstance(target, dict):
                raise ValueError(f"{source}: contrast row {row_id!r} has a non-object target")
            if not (target.get("bab") or "").strip():
                raise ValueError(f"{source}: contrast row {row_id!r} has a target with no bab")
            if not (target.get("pos") or "").strip():
                raise ValueError(f"{source}: contrast row {row_id!r} has a target with no pos")
            if "verb_form" not in target:
                raise ValueError(f"{source}: contrast row {row_id!r} has a target with no verb_form")
    return data


@functools.lru_cache(maxsize=1)
def load_contrast() -> dict:
    """The باب contrast table, validated. Candidates only — attestation is not in here."""
    return validate_contrast(_read(CONTRAST_PATH), str(CONTRAST_PATH))


def sigha_version() -> str:
    return str(load_sigha()["meta"]["version"])


def contrast_version() -> str:
    return str(load_contrast()["meta"]["version"])


def kb_version() -> str:
    """The combined KB version that participates in the analysis cache key.

    Combined rather than two fields because a Tahlil analysis is invalidated by an edit to
    *either* table, and one opaque string makes that impossible to get half-right.
    """
    return f"sigha{sigha_version()}+contrast{contrast_version()}"


# ─────────────────────────────────────────────────────────────────────────────
# Row matching
# ─────────────────────────────────────────────────────────────────────────────


@functools.lru_cache(maxsize=1)
def _sigha_index() -> dict[tuple[str, str], list[dict]]:
    index: dict[tuple[str, str], list[dict]] = {}
    for row in load_sigha()["rows"]:
        index.setdefault((row["key_type"], row["key"]), []).append(row)
    return index


def wazn_key(wazn: str | None) -> str | None:
    """The KB lookup key for a projected mīzān — the pattern without its nunation.

    See `_TANWIN`: this fold is coverage, not cosmetics. It is deliberately the *only*
    normalization applied; anything more (stripping pronoun suffixes, folding ḥarakāt)
    would let a word match a pattern it does not actually realise.
    """
    if not wazn:
        return None
    key = wazn.strip()
    if key.endswith("ًا"):  # fatḥatān + the alif that carries it
        key = key[:-2]
    while key and key[-1] in _TANWIN:
        key = key[:-1]
    return key or None


def _public(row: dict) -> dict:
    """The caller-facing shape of a row: file fields + the two derived ones.

    `multi_sense` is derived here, never stored, so a row that gains a second sense in a
    later KB version cannot keep an unanchored selection badged مُولَّد by omission.

    The senses are **deep-copied**, not aliased. `load_sigha()` is `lru_cache`d, so the
    row objects live for the life of the process; handing a caller the very dicts the
    cache holds means one caller editing a `sense_ar` in place rewrites the KB for every
    later request — a sourced claim would then be cited against text the reference never
    said, with the provenance still attached and nothing to detect it.

    `cite_id` carries **`sigha_version()` — this file's own version**, never the combined
    `kb_version()`, which exists only for the analysis cache key (tasks.md 4.2: an id is
    minted by the module that owns the evidence and copied verbatim downstream).
    """
    senses = copy.deepcopy(row.get("senses") or [])
    return {
        "id": row["id"],
        "key_type": row["key_type"],
        "key": row["key"],
        "senses": senses,
        "provenance": row.get("provenance", ""),
        "notes": row.get("notes", ""),
        "multi_sense": len(senses) > 1,
        "cite_id": f"sigha:{row['id']}@{sigha_version()}",
    }


def match(record: dict, mizan: dict) -> list[dict]:
    """The KB rows that apply to this word, most specific first.

    `record` is a `qac_words.json` record (pos / features / root / lemma); `mizan` is the
    output of `analysis.mizan.compute_mizan`. Returns `[]` — never a fabricated row — when
    nothing matches; the caller is expected to *say* that no form row matched rather than
    render an empty صرفي block, since a silently empty block reads as «no form meaning
    here» instead of «we have no row for this form».

    Two disjoint routes (see the module docstring on why they must not mix):

    * **verbs** — الباب (from `mizan["bab"]`, present for 100 % of the 19 356 verbs) then
      الزمن (`verb_aspect`, mapped through `qac_labels` so the KB stays Arabic-keyed and
      no Buckwalter code can reach a caller).
    * **nominals** — the derived-noun feature (`ACT_PCPL` / `PASS_PCPL` / `VN`, read
      straight off the treebank) then the mīzān pattern.

    The wazn route requires `mizan["verified"]`: an اجتهادي projection is explicitly
    outside the «معطى محقّق» badge, and keying a sourced sense off a guessed pattern would
    launder that guess into a citation. **Kept as policy, not as a live filter** — after
    the mīzān hardening the gate rejects 0 words today (no اجتهادي nominal projection
    lands on a shipped wazn key), so it is pinned against a synthetic اجتهادي mīzān in the
    test suite rather than by a corpus word.
    """
    record = record or {}
    mizan = mizan or {}
    features = record.get("features") or {}
    index = _sigha_index()
    hits: list[dict] = []

    def add(key_type: str, key: str | None) -> None:
        if key:
            hits.extend(index.get((key_type, key), ()))

    if record.get("pos") == "V":
        add("bab", mizan.get("bab"))
        add("aspect", VERB_ASPECT_AR.get(features.get("verb_aspect") or ""))
    else:
        add("derived_noun", DERIVED_NOUNS_AR.get(features.get("derived_nouns") or ""))
        if mizan.get("available") and mizan.get("verified"):
            add("wazn", wazn_key(mizan.get("wazn")))

    # The sort is the *only* thing that states the presentation order: the two `add()`
    # sequences above happen to already run most-specific-first, so re-ordering them would
    # silently change what a reader meets first. Kept (rather than left implicit in the
    # call order) and pinned two ways in the suite: on a real corpus word matching two key
    # types, and on a deliberately out-of-order index.
    seen: set[str] = set()
    ordered: list[dict] = []
    for row in sorted(hits, key=lambda r: _KEY_TYPE_ORDER.index(r["key_type"])):
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        ordered.append(_public(row))
    return ordered


# ─────────────────────────────────────────────────────────────────────────────
# Contrast candidates
# ─────────────────────────────────────────────────────────────────────────────


@functools.lru_cache(maxsize=1)
def _contrast_index() -> dict[str, dict]:
    return {row["bab"]: row for row in load_contrast()["rows"] if row.get("bab")}


def _roman(target: dict) -> str:
    """The form number used in a candidate's id. Form I is unmarked in QAC (`verb_form`
    absent), so a missing value means I — not «unknown»."""
    form = (target.get("verb_form") or "").strip()
    return form.strip("()") or "I"


def contrast_candidates(mizan: dict, record: dict) -> list[dict]:
    """The أبواب this word's باب is classically opposed to — **candidates only**.

    Deliberately carries **no** attestation field. Whether the opposed form actually occurs
    is a corpus question computed downstream at `(lemma, POS/باب)` granularity by
    `tahlil/evidence.py`; answering it here, or at root granularity anywhere, inverts the
    verdict on the pinned word — root `سرع` *does* contain أَسْرَع, but as an اسم تفضيل
    (6:62), not as a verb of باب أفعَلَ, so «ولم ترد صيغة أفعَلَ فعلاً من هذا الجذر» is true
    while a root-level check would call it false. Every target therefore ships its own
    `pos` **and** `verb_form`, because those two are exactly the granularity the check
    needs.

    Returns `[]` for nominals: v0.1.0 of the table opposes verb أبواب only, so a nominal
    would only ever get a row this باب router could not reach (stated in the file's meta).
    `[]` is also what باب فَعْلَلَ gets — and, once attestation runs, what contrast.IX's
    form-XI target amounts to; both gaps are **named in the file's `meta.coverage_gaps`**
    so an empty contrast list is always traceable to a stated reason rather than read as
    «the tradition opposes this باب to nothing».

    `cite_id` carries `contrast_version()` — **this table's own version**, never the
    combined `kb_version()` (tasks.md 4.2).
    """
    mizan = mizan or {}
    if (record or {}).get("pos") != "V":
        return []
    bab = mizan.get("bab")
    if not bab:
        return []
    row = _contrast_index().get(bab)
    if not row:
        return []
    version = contrast_version()
    out: list[dict] = []
    for tgt in row.get("against") or []:
        out.append(
            {
                "id": f"{row['id']}.vs.{_roman(tgt)}",
                "bab": bab,
                "target": {
                    "bab": tgt.get("bab"),
                    "pos": tgt.get("pos"),
                    "verb_form": tgt.get("verb_form"),
                },
                "rationale_ar": tgt.get("rationale_ar", ""),
                "provenance": row.get("provenance", ""),
                "cite_id": f"contrast:{bab}@{version}",
            }
        )
    return out


if __name__ == "__main__":  # smoke test — mirrors mizan.py / qlisan_data.py
    from analysis.mizan import compute_mizan
    from analysis.qlisan_data import qac_words

    print(f"kb_version: {kb_version()}")
    print(f"sigha rows: {len(load_sigha()['rows'])}  contrast rows: {len(load_contrast()['rows'])}")
    words = qac_words()
    for ref in ("23:61:2", "2:202:7", "1:7:3", "1:4:1", "23:61:3"):
        record = words.get(ref)
        if not record:
            continue
        mizan = compute_mizan(record, ref)
        rows = match(record, mizan)
        print(f"\n{ref}  pos={record.get('pos')}  bab={mizan.get('bab')}  wazn={mizan.get('wazn')}")
        for row in rows:
            senses = "، ".join(s["sense_ar"] for s in row["senses"])
            print(f"  [{row['key_type']}] {row['key']} → {senses}"
                  f"  (multi_sense={row['multi_sense']}, {row['cite_id']})")
        for cand in contrast_candidates(mizan, record):
            print(f"  ضدّ {cand['target']['bab']} "
                  f"({cand['target']['pos']} {cand['target']['verb_form']}) — {cand['id']}")
