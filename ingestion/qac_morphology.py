"""
qac_morphology.py — Stage 4 (QAC) of the ingestion pipeline.

Builds the Arabic root index that powers the Verse Study / lexical features
from the Quranic Arabic Corpus (QAC), `data/source/quran-morphology.txt`
(mustafa0x/quran-morphology fork), whose roots are manually verified. This
replaces the tashaphyne light-stemmer builder in `ingestion/morphology.py`,
which mis-roots words (e.g. كريم → ريم instead of كرم). The old builder is kept
in place, unmodified, so the two can be validated side by side.

Source format — one record per morphological SEGMENT (not per word). The file's
layout is read by `quran_data.qac`, which is the ONLY module that knows it; this
builder consumes `qac.records()` and reads the fields:
  - surah / ayah / word / segment, already split out of the LOCATION column
  - FEATURES = pipe-separated tokens; the root, WHEN PRESENT, is a token
    "ROOT:<arabic>" that may appear at ANY position. The lemma is "LEM:<arabic>".
  - Many segments have NO ROOT token (prefixes, DET, pronouns, particles,
    disconnected-letter openers). Those are skipped silently.

Design decisions (fixed):
  D1 — root keys are the RAW QAC root, root-safe normalized (D2), NOT hyphen-
       joined. Quadriliteral (4-letter) roots are handled natively.
  D2 — normalization comes from `ingestion.root_normalize.normalize_root`
       (never `normalizer.normalize_text`).
  D3 — resolution maps (form→roots, lemma→roots) are emitted for the resolver.
  D4 — this is a NEW, separate builder; `ingestion/morphology.py` is untouched.

Outputs:
  - data/derived/morphology.json     : root → {root, forms_found, verses, count}
  - data/derived/qac_resolution.json : {form_to_roots, lem_to_roots}
  - data/derived/lemma_index.json    : root → [{lemma, lemma_display, forms_found,
                                          verses, count}] (a root's occurrences split
                                          per lemma; powers the Verse Study grouping)
  - data/derived/proper_nouns.json   : search-normalized lemma → {lemma_display,
                                          forms_found, verses, count} for rootless
                                          proper nouns (لوط, إبراهيم …), which carry
                                          NO root in QAC and so are absent from the
                                          root index — this lets Verse Study find them
  - data/derived/verses_final.json   : verses with the `roots` field filled
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indexing.text_normalize import normalize_search  # noqa: E402
from ingestion.root_normalize import normalize_root  # noqa: E402
from ingestion.root_resolver import load_resolved, same_root  # noqa: E402
from quran_data import paths, qac  # noqa: E402
from quran_data.qac import Record  # noqa: E402

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(it, **kwargs):  # type: ignore
        return it

# The source this builder consumes. Named here only so callers can ask whether it
# is present; the file itself is read by `quran_data.qac`, never opened here.
QAC_MORPHOLOGY_TXT = paths.QAC_MORPHOLOGY_TXT

MORPHOLOGY_JSON = paths.MORPHOLOGY_JSON
RESOLUTION_JSON = paths.QAC_RESOLUTION_JSON
LEMMA_INDEX_JSON = paths.LEMMA_INDEX_JSON
PROPER_NOUNS_JSON = paths.PROPER_NOUNS_JSON
VERSES_FINAL_JSON = paths.VERSES_FINAL_JSON


class Segment:
    """A parsed, root-bearing QAC segment (pure data)."""

    __slots__ = ("verse_id", "word_ref", "form", "root", "lemma", "lemma_raw")

    def __init__(self, verse_id: str, form: str, root: str, lemma: str,
                 lemma_raw: str = "", word_ref: str = ""):
        self.verse_id = verse_id  # "sura:aya"
        self.word_ref = word_ref  # "sura:aya:word" — the resolver's key
        self.form = form          # raw, diacritized FORM (kept for display)
        self.root = root          # the source's own root spelling, unfolded
        self.lemma = lemma        # root-safe normalized lemma ("" if absent)
        self.lemma_raw = lemma_raw  # raw, diacritized LEM (for display; "" if absent)


def _as_record(item: Record | str) -> Record | None:
    """A `Record` for either a real record or a single raw line.

    The corpus arrives as `quran_data.qac.Record`s and passes straight through.
    A raw LINE is accepted only so the pure builder below can be driven by an
    in-memory fixture (that is what the unit tests do) without a corpus on disk,
    and it is handed to `qac.parse_line` — so the file's layout is known in
    exactly one place, which is the whole point of collapsing the four readers.
    """
    return item if isinstance(item, Record) else qac.parse_line(item)


def parse_line(line: str) -> Segment | None:
    """Line-taking form of `parse_segment`, for in-memory fixtures."""
    rec = _as_record(line)
    return parse_segment(rec) if rec is not None else None


def parse_segment(rec: Record) -> Segment | None:
    """Turn one QAC record into a Segment, or None to skip it.

    Returns None for the common case: a segment with no ROOT token. Where the
    location and the four columns come from is `quran_data.qac`'s business —
    this reads FEATURES only. The ROOT token is found by PREFIX SCAN over the
    pipe-split FEATURES, never by position (which varies from line to line).
    """
    raw_root = ""
    raw_lemma = ""
    for token in rec.features.split("|"):
        if token.startswith("ROOT:"):
            raw_root = token[len("ROOT:"):]
        elif token.startswith("LEM:"):
            raw_lemma = token[len("LEM:"):]
    if not raw_root:
        return None

    return Segment(
        verse_id=f"{rec.surah}:{rec.ayah}",
        word_ref=f"{rec.surah}:{rec.ayah}:{rec.word}",
        form=rec.form,
        # NOT normalized: the fold is a lookup key, never a stored value. The
        # canonical spelling is decided per word by the resolver in build().
        root=raw_root.strip(),
        lemma=normalize_root(raw_lemma) if raw_lemma else "",
        lemma_raw=raw_lemma,
    )


def parse_proper_noun(item: Record | str) -> tuple[str, str, str, str] | None:
    """Parse a ROOTLESS proper-noun (PN) segment → (verse_id, form, lemma_key,
    lemma_raw), or None to skip. Takes a record, or a raw line for fixtures.

    Quranic proper nouns of foreign origin (لوط, إبراهيم, موسى …) carry a LEM but
    NO ROOT in QAC, so `parse_segment` skips them and the root index never sees
    them. This picks them up for a name index. Selection: has a LEM, is tagged PN,
    and has NO ROOT (PN *with* a root — e.g. صالح — stays in the root index). The
    key is `normalize_search`-folded (ى→ي, ة→ه) so name spelling variants match."""
    rec = _as_record(item)
    if rec is None:
        return None
    tokens = rec.features.split("|")
    if any(t.startswith("ROOT:") for t in tokens):
        return None                         # has a root → handled by parse_segment
    if "PN" not in tokens:
        return None                         # only proper nouns (not particles)
    raw_lemma = ""
    for t in tokens:
        if t.startswith("LEM:"):
            raw_lemma = t[len("LEM:"):]
    if not raw_lemma:
        return None
    key = normalize_search(raw_lemma)
    if not key:
        return None
    return f"{rec.surah}:{rec.ayah}", rec.form, key, raw_lemma


def build(records, resolved: dict | None = None) -> tuple[dict, dict, dict, dict, dict]:
    """Build the index + resolution maps + verse→roots map + lemma/PN indexes.

    `records` is any iterable of `quran_data.qac.Record` — the corpus itself —
    or, for tests, of raw lines in the same layout.

    Returns (index, resolution, verse_roots, lemma_index, proper_nouns):
      - index         : root → {root, forms_found, verses, count}
      - resolution    : {"form_to_roots": {...}, "lem_to_roots": {...}}
      - verse_roots   : verse_id → sorted[roots]   (to fill each verse's `roots`)
      - lemma_index   : root → [ {lemma, lemma_display, forms_found, verses, count} ]
                        splitting a root's occurrences per lemma, ordered by
                        verse count desc (dominant sense first).
      - proper_nouns  : search-normalized lemma → {lemma, lemma_display, forms_found,
                        verses, count} for ROOTLESS proper nouns (لوط, إبراهيم …).
    """
    # Pure by default: no disk read here. `run()` passes the resolved artifact in.
    # A word absent from `resolved` falls back to folding its own root, so build()
    # stays usable on a synthetic line list (tests) without touching the corpus.
    resolved = resolved or {}
    verses_by_root: dict[str, set[tuple[int, int]]] = defaultdict(set)
    # Verses reachable under a root that is only an ALTERNATE reading there. Kept
    # apart from `verses_by_root` so a contested word (ٱلنَّاس: أنس / نوس) is findable
    # under either reading without inflating both families' counts and IDF weights.
    alt_verses_by_root: dict[str, set[tuple[int, int]]] = defaultdict(set)
    forms_by_root: dict[str, set[str]] = defaultdict(set)
    form_to_roots: dict[str, set[str]] = defaultdict(set)
    lem_to_roots: dict[str, set[str]] = defaultdict(set)
    roots_by_verse: dict[str, set[str]] = defaultdict(set)
    # Per (root, normalized-lemma) accumulators for the lemma index.
    lemma_verses: dict[tuple[str, str], set[tuple[int, int]]] = defaultdict(set)
    lemma_forms: dict[tuple[str, str], set[str]] = defaultdict(set)
    lemma_disp: dict[tuple[str, str], Counter] = defaultdict(Counter)
    # Rootless proper-noun accumulators (keyed by search-normalized lemma).
    pn_verses: dict[str, set[tuple[int, int]]] = defaultdict(set)
    pn_forms: dict[str, set[str]] = defaultdict(set)
    pn_disp: dict[str, Counter] = defaultdict(Counter)

    # Surface + verse of EVERY word, rooted or not, so a word the resolver rooted
    # from the treebank (أُو۟لِى → اول) still enters this index. Without it the two
    # chains would disagree by omission: chain B knows the root, chain A never
    # sees the word because its own source carries no ROOT: field for it.
    word_form: dict[str, str] = defaultdict(str)
    word_verse: dict[str, str] = {}
    seen_words: set[str] = set()

    for item in records:
        rec = _as_record(item)
        if rec is None:                       # unreadable fixture line
            continue
        wref = f"{rec.surah}:{rec.ayah}:{rec.word}"
        word_form[wref] += rec.form
        word_verse[wref] = f"{rec.surah}:{rec.ayah}"
        seg = parse_segment(rec)
        if seg is None:
            pn = parse_proper_noun(rec)       # rootless proper noun?
            if pn is not None:
                vid, form, key, raw_lemma = pn
                s, a = (int(x) for x in vid.split(":"))
                pn_verses[key].add((s, a))
                pn_forms[key].add(form)
                pn_disp[key][raw_lemma] += 1
            continue
        sura, aya = (int(x) for x in seg.verse_id.split(":"))
        # The resolver owns the spelling: its primary wins, even when the verdict
        # overrides this segment's own root (107:7 ٱلْمَاعُون: source عون → معن).
        # The ONLY exception is a word whose source carries one root per segment
        # (20:94:2 يبنؤم = بني + أمم), where each segment must keep its own.
        rec = resolved.get(seg.word_ref)
        if rec is None:
            root, alts = normalize_root(seg.root), []
        else:
            cands = [rec["primary"], *rec.get("alternates", [])]
            root = rec["primary"]
            if rec.get("multi_source"):
                match = [c for c in cands if same_root(c, seg.root)]
                root = match[0] if match else root
            alts = [c for c in cands if c != root] if root == rec["primary"] else []

        verses_by_root[root].add((sura, aya))         # dedupe verses per root
        forms_by_root[root].add(seg.form)
        roots_by_verse[seg.verse_id].add(root)
        for alt in alts:
            alt_verses_by_root[alt].add((sura, aya))
            forms_by_root[alt].add(seg.form)
        form_key = normalize_root(seg.form)
        if form_key:
            form_to_roots[form_key].update([root, *alts])
        if seg.lemma:
            lem_to_roots[seg.lemma].update([root, *alts])
        # Lemma bucket. Every rooted QAC segment carries a lemma; fall back to
        # the root key if one is ever missing so no occurrence is dropped.
        lk = (root, seg.lemma or root)
        lemma_verses[lk].add((sura, aya))
        lemma_forms[lk].add(seg.form)
        lemma_disp[lk][seg.lemma_raw or seg.root] += 1
        seen_words.add(seg.word_ref)

    # Words the resolver rooted but this source never marked with a ROOT: field
    # (the 73 treebank-only additions: أُو۟لِى → اول, أَنَّىٰ → اني). Adding them here is
    # what makes both chains publish the same root set for the same word.
    for wref, rec in resolved.items():
        if wref in seen_words or wref not in word_verse:
            continue
        vid = word_verse[wref]
        sura, aya = (int(x) for x in vid.split(":"))
        root, form = rec["primary"], word_form[wref]
        verses_by_root[root].add((sura, aya))
        forms_by_root[root].add(form)
        roots_by_verse[vid].add(root)
        form_key = normalize_root(form)
        if form_key:
            form_to_roots[form_key].add(root)
        lk = (root, root)
        lemma_verses[lk].add((sura, aya))
        lemma_forms[lk].add(form)
        lemma_disp[lk][root] += 1

    index: dict[str, dict] = {}
    for root in sorted(set(verses_by_root) | set(alt_verses_by_root)):
        ordered = sorted(verses_by_root.get(root, set()))   # canonical: sura, aya asc
        entry = {
            "root": root,
            "forms_found": sorted(forms_by_root[root]),
            "verses": [f"{s}:{a}" for s, a in ordered],
            "count": len(ordered),
        }
        # Reachable-but-not-counted: verses where this root is only the alternate
        # reading. `count` and `verses` stay the primary-only tally, so every
        # frequency-weighted consumer (IDF, statistics) is unaffected by alternates.
        alt = sorted(alt_verses_by_root.get(root, set()) - verses_by_root.get(root, set()))
        if alt:
            entry["alt_verses"] = [f"{s}:{a}" for s, a in alt]
        index[root] = entry

    resolution = {
        "form_to_roots": {k: sorted(v) for k, v in sorted(form_to_roots.items())},
        "lem_to_roots": {k: sorted(v) for k, v in sorted(lem_to_roots.items())},
    }
    verse_roots = {vid: sorted(roots) for vid, roots in roots_by_verse.items()}

    # Lemma index: group a root's occurrences per lemma, dominant sense first.
    lemmas_by_root: dict[str, list[dict]] = defaultdict(list)
    for (root, lemma), verses in lemma_verses.items():
        ordered = sorted(verses)
        top_disp = lemma_disp[(root, lemma)].most_common(1)
        lemmas_by_root[root].append({
            "lemma": lemma,
            "lemma_display": top_disp[0][0] if top_disp else lemma,
            "forms_found": sorted(lemma_forms[(root, lemma)]),
            "verses": [f"{s}:{a}" for s, a in ordered],
            "count": len(ordered),
        })
    lemma_index: dict[str, list[dict]] = {}
    for root in sorted(lemmas_by_root):
        lemma_index[root] = sorted(
            lemmas_by_root[root], key=lambda g: (-g["count"], g["lemma"])
        )

    # Proper-noun index: rootless names, keyed by search-normalized lemma.
    proper_nouns: dict[str, dict] = {}
    for key in sorted(pn_verses):
        ordered = sorted(pn_verses[key])
        top_disp = pn_disp[key].most_common(1)
        proper_nouns[key] = {
            "lemma": key,
            "lemma_display": top_disp[0][0] if top_disp else key,
            "forms_found": sorted(pn_forms[key]),
            "verses": [f"{s}:{a}" for s, a in ordered],
            "count": len(ordered),
        }
    return index, resolution, verse_roots, lemma_index, proper_nouns


def run(verses: list[dict]) -> tuple[list[dict], dict]:
    """Build the QAC root index, fill each verse's `roots`, and persist outputs.

    Signature mirrors `ingestion.morphology.run` so `run_pipeline` is unchanged.
    """
    resolved = load_resolved()          # the single root authority (see root_resolver)
    # `qac.records()` streams the corpus and raises with the obtain-it-from advice
    # when the source is absent; the file is never opened here.
    index, resolution, verse_roots, lemma_index, proper_nouns = build(
        tqdm(qac.records(), desc="  qac-morph  ", unit="seg"), resolved
    )

    for v in verses:
        v["roots"] = verse_roots.get(v["id"], [])

    _save(index, resolution, lemma_index, proper_nouns, verses)
    n_rootfree = sum(1 for v in verses if not v["roots"])
    print(
        f"  qac-morph  : {len(index)} roots + {len(proper_nouns)} proper nouns "
        f"indexed from QAC ({n_rootfree} verses have no rooted word)"
    )
    return verses, index


def _save(index: dict, resolution: dict, lemma_index: dict, proper_nouns: dict,
          verses: list[dict]) -> None:
    MORPHOLOGY_JSON.parent.mkdir(parents=True, exist_ok=True)
    with MORPHOLOGY_JSON.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    with RESOLUTION_JSON.open("w", encoding="utf-8") as f:
        json.dump(resolution, f, ensure_ascii=False, indent=2)
    with LEMMA_INDEX_JSON.open("w", encoding="utf-8") as f:
        json.dump(lemma_index, f, ensure_ascii=False, indent=2)
    with PROPER_NOUNS_JSON.open("w", encoding="utf-8") as f:
        json.dump(proper_nouns, f, ensure_ascii=False, indent=2)
    with VERSES_FINAL_JSON.open("w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Standalone (re)build of the QAC index over the existing processed corpus.
    from indexing.corpus import load_verses

    load_verses.cache_clear()  # ensure a fresh mutable list we can write back
    verses, index = run(load_verses())
    # Keys are the EXACT root spelling now (أله, not اله). A folded spelling no
    # longer hits the index directly — that is what LexicalRetriever._canon is for.
    for key in ["كرم", "أله", "سمو", "حصحص", "لؤلؤ"]:
        entry = index.get(key, {})
        print(f"  {key!r}: count={entry.get('count')} "
              f"alt={len(entry.get('alt_verses', []))} "
              f"forms={entry.get('forms_found', [])[:3]}")
