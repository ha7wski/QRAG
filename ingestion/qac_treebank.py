"""
qac_treebank.py — QLisan foundation: token-alignment spine + per-word indexes.

Parses the on-disk QAC dependency treebank
(`data/raw/eqtb/quranic-treebank.csv`, TAB-separated, 139376 data rows) into the
four keyed artifacts every downstream QLisan level (صرفي / نحوي / دلالي) keys off:

  * `qac_words.json`   — "surah:ayah:word" -> morphology (root / lemma / pos /
                         features / segments / is_proper_noun).
  * `qac_syntax.json`  — "surah:ayah:word" -> dependency role (role_ar /
                         relation / relation_ar / head_ref). Words with no usable
                         relation are OMITTED (=> nahwi.available=false).
  * `root_graph.json`  — normalized_root -> [occurrence refs] (for nazair).
  * `word_index.json`  — THE ALIGNMENT SPINE: "surah:ayah:word" -> {uthmani,
                         imlaai, chakl_char_start, chakl_char_end, aligned}.
                         Maps QAC's canonical word segmentation onto the displayed
                         vocalized rasm (`quran_chakl.csv`), merge-only.

Design notes (verified against the real data):
  * A QAC "word" spans several rows (PREFIX / STEM / SUFFIX segments) sharing
    (chapter_id, verse_id, word_id). Whole-word forms concatenate uthmani_token /
    imlaai_token in tok_id order. Morphology is taken from the STEM segment (the
    first STEM when a word carries several — 486 compound words do).
  * Pseudo-tokens (location == '_', word_id == 0: elided heads '(*)' and
    parenthesized pro-drop pronouns) are EXCLUDED from word counts and every
    index. Verse word count = max(word_id) over real rows.
  * `token_id` is per-SENTENCE, not global (only 233 distinct values). `ref_token_id`
    (the dependency head pointer) is therefore resolved within (sentence_id,
    token_id); heads pointing at a pseudo-token resolve to null.
  * Roots use `normalize_root` (hamza-safe) for the KEY; `*_display` keeps the raw
    QAC Arabic. Proper nouns (pos == 'PN') are flagged `is_proper_noun`; a PN that
    still carries a genuine QAC root (e.g. اللَّه -> اله) keeps it — this is more
    useful for nazair than nulling it, and most PNs are rootless (root_ar == 'ـ')
    so they null out naturally. This is a documented, deliberate reading of the
    "PN typically has no root" note in the task.

Alignment cascade (merge-only; the display only ever OVER-segments — 0 verses have
fewer content tokens than QAC):
  1. Whitespace-tokenize the chakl "aya", tracking each token's [start,end) offsets.
  2. Drop mark-only tokens (empty after stripping tashkil / waqf / sajda / tatweel).
  3. Drop a prepended basmala on ayah 1 (surahs other than 1 and 9).
  4. Merge a bare vocative/attention particle (يا / ويا / فيا / ها / وها / فها)
     into the following content token (span-union). Verified safe: NO QAC word
     normalizes to يا or ها alone, so this never under-segments an aligned verse.
  5. If the remaining content-token count == max(word_id), map 1:1 (aligned=true).
     Else consult `overrides.json` (explicit ordered per-word [start,end] spans).
     Else emit a best-effort even split (aligned=false) and record it in the audit.

Result on the real corpus: 6233/6236 verses align by cascade (99.95%); the last 3
(20:94, 37:130, 72:16) are resolved by hand-curated overrides -> 6236/6236 (100%).

Run: `python ingestion/qac_treebank.py`
"""
from __future__ import annotations

import csv
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.root_normalize import normalize_root  # noqa: E402
from indexing.text_normalize import normalize_search  # noqa: E402

# --- Paths --------------------------------------------------------------------
TREEBANK_CSV = ROOT / "data" / "raw" / "eqtb" / "quranic-treebank.csv"
CHAKL_CSV = ROOT / "data" / "raw" / "quran_chakl.csv"
PROCESSED = ROOT / "data" / "processed"

QAC_WORDS = PROCESSED / "qac_words.json"
QAC_SYNTAX = PROCESSED / "qac_syntax.json"
ROOT_GRAPH = PROCESSED / "root_graph.json"
WORD_INDEX = PROCESSED / "word_index.json"
OVERRIDES = PROCESSED / "overrides.json"
AUDIT = PROCESSED / "qlisan_alignment_audit.json"

# --- Constants ----------------------------------------------------------------
# Tokens the QAC uses for "empty" in root / lemma / feature columns.
NULL_TOKENS = {"_", "", "ـ", "-", "(*)"}

# Morphological feature columns; a feature is emitted only when non-null.
FEATURE_COLS = [
    "verb_form", "verb_aspect", "verb_mood", "verb_voice",
    "nominal_state", "nominal_case", "special_group", "derived_nouns",
    "pgn", "person", "gender", "number", "prefix", "suffix",
]

# rel_label values that are NOT a usable syntactic relation -> word is omitted
# from qac_syntax (nahwi.available=false downstream). 'root' IS usable (it is the
# dependency-tree root role).
UNUSABLE_RELATIONS = {"NonRel", "", "-", "_"}

# Alignment: bare vocative / attention particles that the display splits off but
# QAC fuses into the following word. Merged into the next content token.
MERGE_PARTICLES = {"يا", "ويا", "فيا", "ها", "وها", "فها"}

# Characters that make a chakl token "mark-only" (drop it when nothing else left).
_MARK_RANGES = [
    (0x0610, 0x061A),  # Arabic honorifics / small high marks
    (0x064B, 0x065F),  # harakat + extended
    (0x0670, 0x0670),  # superscript (dagger) alif
    (0x06D6, 0x06ED),  # Quranic annotation / waqf / sajda / hizb marks
    (0x0640, 0x0640),  # tatweel
]

_BASMALA_WORDS = ["بسم", "الله", "الرحمن", "الرحيم"]


def _is_mark(cp: int) -> bool:
    return any(a <= cp <= b for a, b in _MARK_RANGES)


def _strip_marks(tok: str) -> str:
    return "".join(c for c in tok if not _is_mark(ord(c)))


def _null(v: str) -> bool:
    return v is None or v.strip() in NULL_TOKENS


# ============================================================================
# 1) Parse the treebank into an in-memory word model
# ============================================================================
def _parse_treebank() -> tuple[dict, dict, dict]:
    """Return (words, verse_wordcount, tokmap).

    words:  (s,a,w) -> {
        'segments': [(tok_id, segment)],
        'uthmani_parts': [(tok_id, uthmani_token)],
        'imlaai_parts':  [(tok_id, imlaai_token)],
        'stem': {row-fields} | None,   # first STEM segment
    }
    verse_wordcount: (s,a) -> max word_id over real rows
    tokmap: (sentence_id, token_id) -> "s:a:w" | None (pseudo)
    """
    if not TREEBANK_CSV.exists():
        raise FileNotFoundError(
            f"{TREEBANK_CSV} not found — cannot build QLisan indexes."
        )

    words: dict[tuple[int, int, int], dict] = {}
    verse_wordcount: dict[tuple[int, int], int] = {}
    tokmap: dict[tuple[str, str], str | None] = {}

    with TREEBANK_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            sid = row["sentence_id"]
            tid = row["token_id"]
            location = row["location"]
            if location == "_":
                # pseudo-token: register in tokmap (as unresolvable head) only.
                tokmap.setdefault((sid, tid), None)
                continue

            s = int(row["chapter_id"])
            a = int(row["verse_id"])
            w = int(row["word_id"])
            wref = f"{s}:{a}:{w}"
            tokmap.setdefault((sid, tid), wref)

            vk = (s, a)
            if w > verse_wordcount.get(vk, 0):
                verse_wordcount[vk] = w

            key = (s, a, w)
            entry = words.get(key)
            if entry is None:
                entry = {
                    "segments": [],
                    "uthmani_parts": [],
                    "imlaai_parts": [],
                    "stem": None,
                }
                words[key] = entry

            tok_id = int(row["tok_id"])
            seg = row["segment"]
            entry["segments"].append((tok_id, seg))
            entry["uthmani_parts"].append((tok_id, row["uthmani_token"]))
            entry["imlaai_parts"].append((tok_id, row["imlaai_token"]))
            if seg == "STEM" and entry["stem"] is None:
                entry["stem"] = row  # first STEM wins (compound words)

    return words, verse_wordcount, tokmap


def _join_parts(parts: list[tuple[int, str]]) -> str:
    return "".join(t for _, t in sorted(parts, key=lambda p: p[0]))


def _build_features(stem: dict) -> dict:
    feats: dict[str, str] = {}
    for col in FEATURE_COLS:
        v = stem.get(col, "")
        if not _null(v):
            feats[col] = v.strip()
    return feats


# ============================================================================
# 2) qac_words + qac_syntax + root_graph
# ============================================================================
def _build_word_indexes(words: dict, tokmap: dict):
    qac_words: dict[str, dict] = {}
    qac_syntax: dict[str, dict] = {}
    root_graph: dict[str, list] = defaultdict(list)

    for (s, a, w) in sorted(words):
        ref = f"{s}:{a}:{w}"
        entry = words[(s, a, w)]
        stem = entry["stem"]

        uthmani = _join_parts(entry["uthmani_parts"])
        imlaai = _join_parts(entry["imlaai_parts"])
        segments = [seg for _, seg in sorted(entry["segments"], key=lambda p: p[0])]

        pos = ""
        pos_ar = ""
        root = None
        root_display = None
        lemma = None
        lemma_display = None
        features: dict = {}
        is_pn = False

        if stem is not None:
            pos = stem.get("pos", "").strip()
            pos_ar = stem.get("pos_ar", "").strip()
            is_pn = pos == "PN"
            root_ar = stem.get("root_ar", "")
            if not _null(root_ar):
                root_display = root_ar.strip()
                root = normalize_root(root_display)
            lemma_ar = stem.get("lemma_ar", "")
            if not _null(lemma_ar):
                lemma_display = lemma_ar.strip()
                lemma = normalize_root(lemma_display)
            features = _build_features(stem)

        qac_words[ref] = {
            "uthmani": uthmani,
            "imlaai": imlaai,
            "root": root,
            "root_display": root_display,
            "lemma": lemma,
            "lemma_display": lemma_display,
            "pos": pos,
            "pos_ar": pos_ar,
            "features": features,
            "segments": segments,
            "is_proper_noun": is_pn,
        }

        if root:
            root_graph[root].append(ref)

        # --- syntax (omit words with no usable relation) ---
        if stem is not None:
            rel = stem.get("rel_label", "").strip()
            if rel not in UNUSABLE_RELATIONS:
                rel_ar = stem.get("rel_label_ar", "").strip()
                head_ref = None
                ref_tok = stem.get("ref_token_id", "").strip()
                if ref_tok not in ("", "0", "-"):
                    head_ref = tokmap.get((stem["sentence_id"], ref_tok))
                # A head resolving to the word itself means the syntactic head is a
                # word-internal proclitic segment (e.g. the preposition in لِلَّهِ).
                # Keep the relation, but null the head so نحوي never renders
                # "depends on itself" — the API/UI already handle head_ref=None.
                if head_ref == ref:
                    head_ref = None
                qac_syntax[ref] = {
                    "role_ar": pos_ar or None,
                    "relation": rel,
                    "relation_ar": rel_ar or None,
                    "head_ref": head_ref,
                }

    root_graph_sorted = {
        r: sorted(refs, key=_ref_sort_key) for r, refs in root_graph.items()
    }
    return qac_words, qac_syntax, root_graph_sorted


def _ref_sort_key(ref: str) -> tuple[int, int, int]:
    s, a, w = ref.split(":")
    return int(s), int(a), int(w)


# ============================================================================
# 3) Alignment spine (word_index)
# ============================================================================
def _tokenize_offsets(aya: str) -> list[tuple[int, int, str]]:
    """Whitespace-tokenize `aya`, returning (start, end, text) per token."""
    out = []
    i, n = 0, len(aya)
    while i < n:
        while i < n and aya[i].isspace():
            i += 1
        if i >= n:
            break
        st = i
        while i < n and not aya[i].isspace():
            i += 1
        out.append((st, i, aya[st:i]))
    return out


def _content_spans(aya: str, surah: int, ayah: int) -> list[list[int]]:
    """Apply the merge-only cascade, returning ordered [start,end] content spans."""
    toks = [(s, e, t) for (s, e, t) in _tokenize_offsets(aya) if _strip_marks(t)]

    # Drop a prepended basmala on ayah 1 (all surahs except al-Fatiha & at-Tawba).
    if ayah == 1 and surah not in (1, 9):
        i = 0
        while (
            i < len(toks)
            and i < 4
            and normalize_search(toks[i][2]) == normalize_search(_BASMALA_WORDS[i])
        ):
            i += 1
        if i == 4:
            toks = toks[4:]

    # Merge bare vocative / attention particles into the following content token.
    spans: list[list[int]] = []
    i = 0
    while i < len(toks):
        nrm = normalize_search(toks[i][2])
        if nrm in MERGE_PARTICLES and i + 1 < len(toks):
            spans.append([toks[i][0], toks[i + 1][1]])
            i += 2
        else:
            spans.append([toks[i][0], toks[i][1]])
            i += 1
    return spans


def _even_split(spans: list[list[int]], n: int) -> list[list[int]]:
    """Best-effort merge of `len(spans)` content spans into `n` groups (aligned=false).

    Contiguous, order-preserving; distributes the extra spans across the first
    groups. Only used when a verse neither aligns by cascade nor has an override.
    """
    m = len(spans)
    if m <= n:
        # cannot split fewer into more; pad by reusing the last span's end.
        return spans + [[spans[-1][1], spans[-1][1]]] * (n - m) if spans else [[0, 0]] * n
    # group sizes: distribute m spans into n contiguous buckets as evenly as possible
    base, extra = divmod(m, n)
    out = []
    idx = 0
    for g in range(n):
        size = base + (1 if g < extra else 0)
        grp = spans[idx: idx + size]
        out.append([grp[0][0], grp[-1][1]])
        idx += size
    return out


def _load_overrides() -> dict:
    """Read overrides.json (seed as {} if missing). Skip `_`-prefixed doc keys."""
    if not OVERRIDES.exists():
        OVERRIDES.write_text("{}\n", encoding="utf-8")
        return {}
    with OVERRIDES.open(encoding="utf-8") as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _build_word_index(words: dict, verse_wordcount: dict):
    chakl = _load_chakl()
    overrides = _load_overrides()

    word_index: dict[str, dict] = {}
    residual = []
    aligned_by_cascade = 0
    aligned_by_override = 0
    not_aligned = 0

    for (s, a) in sorted(verse_wordcount):
        n = verse_wordcount[(s, a)]
        aya = chakl.get((s, a))
        if aya is None:
            # No display text — emit unaligned zero spans so downstream still works.
            not_aligned += 1
            residual.append({"ref": f"{s}:{a}", "chakl_tokens": 0, "qac_words": n})
            spans = [[0, 0]] * n
            aligned_flag = False
        else:
            spans = _content_spans(aya, s, a)
            key = f"{s}:{a}"
            if len(spans) == n:
                aligned_flag = True
                aligned_by_cascade += 1
            elif key in overrides:
                ov = overrides[key]
                if len(ov) == n:
                    spans = [list(x) for x in ov]
                    aligned_flag = True
                    aligned_by_override += 1
                else:
                    aligned_flag = False
                    not_aligned += 1
                    residual.append(
                        {"ref": key, "chakl_tokens": len(spans), "qac_words": n,
                         "note": "override length mismatch"}
                    )
                    spans = _even_split(spans, n)
            else:
                aligned_flag = False
                not_aligned += 1
                residual.append(
                    {"ref": key, "chakl_tokens": len(spans), "qac_words": n}
                )
                spans = _even_split(spans, n)

        for w in range(1, n + 1):
            ref = f"{s}:{a}:{w}"
            entry = words.get((s, a, w))
            st, en = spans[w - 1]
            word_index[ref] = {
                "uthmani": _join_parts(entry["uthmani_parts"]) if entry else "",
                "imlaai": _join_parts(entry["imlaai_parts"]) if entry else "",
                "chakl_char_start": st,
                "chakl_char_end": en,
                "aligned": aligned_flag,
            }

    total = len(verse_wordcount)
    fully = aligned_by_cascade + aligned_by_override
    audit = {
        "total_verses": total,
        "verses_fully_aligned": fully,
        "pct_aligned": round(100.0 * fully / total, 4) if total else 0.0,
        "verses_aligned_by_cascade": aligned_by_cascade,
        "verses_aligned_by_override": aligned_by_override,
        "verses_not_aligned": not_aligned,
        "residual": residual,
    }
    return word_index, audit


def _load_chakl() -> dict[tuple[int, int], str]:
    if not CHAKL_CSV.exists():
        raise FileNotFoundError(f"{CHAKL_CSV} not found — needed for display alignment.")
    rows: dict[tuple[int, int], str] = {}
    with CHAKL_CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows[(int(row["num_soura"]), int(row["num_aya"]))] = unicodedata.normalize(
                "NFC", row["aya"]
            )
    return rows


# ============================================================================
# Orchestration
# ============================================================================
def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=0, separators=(",", ":"))
        f.write("\n")


def run() -> dict:
    """Build all four QLisan foundation artifacts. Returns the audit dict."""
    words, verse_wordcount, tokmap = _parse_treebank()
    qac_words, qac_syntax, root_graph = _build_word_indexes(words, tokmap)
    word_index, audit = _build_word_index(words, verse_wordcount)

    _write_json(QAC_WORDS, qac_words)
    _write_json(QAC_SYNTAX, qac_syntax)
    _write_json(ROOT_GRAPH, root_graph)
    _write_json(WORD_INDEX, word_index)
    _write_json(AUDIT, audit)
    # Ensure overrides.json exists (seed if absent) so the artifact set is complete.
    if not OVERRIDES.exists():
        _write_json(OVERRIDES, {})

    print("QLisan foundation built:")
    print(f"  qac_words.json  : {len(qac_words):>6} words   -> {QAC_WORDS}")
    print(f"  qac_syntax.json : {len(qac_syntax):>6} words   -> {QAC_SYNTAX}")
    print(f"  root_graph.json : {len(root_graph):>6} roots   -> {ROOT_GRAPH}")
    print(f"  word_index.json : {len(word_index):>6} words   -> {WORD_INDEX}")
    print(
        f"  alignment       : {audit['verses_fully_aligned']}/{audit['total_verses']} "
        f"verses ({audit['pct_aligned']}%) "
        f"[cascade {audit['verses_aligned_by_cascade']} + "
        f"override {audit['verses_aligned_by_override']}]"
    )
    if audit["residual"]:
        print(f"  residual        : {len(audit['residual'])} verses -> {AUDIT}")
    return audit


if __name__ == "__main__":
    run()
