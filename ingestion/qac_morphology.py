"""
qac_morphology.py — Stage 4 (QAC) of the ingestion pipeline.

Builds the Arabic root index that powers the Verse Study / lexical features
from the Quranic Arabic Corpus (QAC), `data/raw/quran-morphology.txt`
(mustafa0x/quran-morphology fork), whose roots are manually verified. This
replaces the tashaphyne light-stemmer builder in `ingestion/morphology.py`,
which mis-roots words (e.g. كريم → ريم instead of كرم). The old builder is kept
in place, unmodified, so the two can be validated side by side.

Source format — one line per morphological SEGMENT (not per word):
    LOCATION <TAB> FORM <TAB> TAG <TAB> FEATURES
  - LOCATION = sura:aya:word:segment  (e.g. 1:2:1:2)
  - FEATURES = pipe-separated tokens; the root, WHEN PRESENT, is a token
    "ROOT:<arabic>" that may appear at ANY position. The lemma is "LEM:<arabic>".
  - Many lines have NO ROOT token (prefixes, DET, pronouns, particles,
    disconnected-letter openers). Those are skipped silently.

Design decisions (fixed):
  D1 — root keys are the RAW QAC root, root-safe normalized (D2), NOT hyphen-
       joined. Quadriliteral (4-letter) roots are handled natively.
  D2 — normalization comes from `ingestion.root_normalize.normalize_root`
       (never `normalizer.normalize_text`).
  D3 — resolution maps (form→roots, lemma→roots) are emitted for the resolver.
  D4 — this is a NEW, separate builder; `ingestion/morphology.py` is untouched.

Outputs:
  - data/processed/morphology.json     : root → {root, forms_found, verses, count}
  - data/processed/qac_resolution.json : {form_to_roots, lem_to_roots}
  - data/processed/verses_final.json   : verses with the `roots` field filled
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.root_normalize import normalize_root  # noqa: E402

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(it, **kwargs):  # type: ignore
        return it

ROOT = Path(__file__).resolve().parents[1]
QAC_MORPHOLOGY_TXT = ROOT / "data" / "raw" / "quran-morphology.txt"
MORPHOLOGY_JSON = ROOT / "data" / "processed" / "morphology.json"
RESOLUTION_JSON = ROOT / "data" / "processed" / "qac_resolution.json"
VERSES_FINAL_JSON = ROOT / "data" / "processed" / "verses_final.json"


class Segment:
    """A parsed, root-bearing QAC segment (pure data)."""

    __slots__ = ("verse_id", "form", "root", "lemma")

    def __init__(self, verse_id: str, form: str, root: str, lemma: str):
        self.verse_id = verse_id  # "sura:aya"
        self.form = form          # raw, diacritized FORM (kept for display)
        self.root = root          # root-safe normalized root key
        self.lemma = lemma        # root-safe normalized lemma ("" if absent)


def parse_line(line: str) -> Segment | None:
    """Parse one QAC line into a Segment, or None to skip it.

    Returns None for blank lines, malformed lines (< 4 tab fields), lines whose
    LOCATION is not numeric, and — the common case — lines with no ROOT token.
    The ROOT token is found by PREFIX SCAN over the pipe-split FEATURES, never
    by column index (its position varies from line to line).
    """
    line = line.rstrip("\n")
    if not line.strip():
        return None
    parts = line.split("\t")
    if len(parts) < 4:
        return None
    location, form, _tag, features = parts[0], parts[1], parts[2], parts[3]

    raw_root = ""
    raw_lemma = ""
    for token in features.split("|"):
        if token.startswith("ROOT:"):
            raw_root = token[len("ROOT:"):]
        elif token.startswith("LEM:"):
            raw_lemma = token[len("LEM:"):]
    if not raw_root:
        return None

    loc_parts = location.split(":")
    if len(loc_parts) < 2:
        return None
    try:
        sura, aya = int(loc_parts[0]), int(loc_parts[1])
    except ValueError:
        return None

    return Segment(
        verse_id=f"{sura}:{aya}",
        form=form,
        root=normalize_root(raw_root),
        lemma=normalize_root(raw_lemma) if raw_lemma else "",
    )


def build(lines) -> tuple[dict, dict, dict]:
    """Build the index + resolution maps + verse→roots map from raw QAC lines.

    Returns (index, resolution, verse_roots):
      - index         : root → {root, forms_found, verses, count}
      - resolution    : {"form_to_roots": {...}, "lem_to_roots": {...}}
      - verse_roots   : verse_id → sorted[roots]   (to fill each verse's `roots`)
    """
    verses_by_root: dict[str, set[tuple[int, int]]] = defaultdict(set)
    forms_by_root: dict[str, set[str]] = defaultdict(set)
    form_to_roots: dict[str, set[str]] = defaultdict(set)
    lem_to_roots: dict[str, set[str]] = defaultdict(set)
    roots_by_verse: dict[str, set[str]] = defaultdict(set)

    for line in lines:
        seg = parse_line(line)
        if seg is None:
            continue
        sura, aya = (int(x) for x in seg.verse_id.split(":"))
        verses_by_root[seg.root].add((sura, aya))     # dedupe verses per root
        forms_by_root[seg.root].add(seg.form)
        roots_by_verse[seg.verse_id].add(seg.root)
        form_key = normalize_root(seg.form)
        if form_key:
            form_to_roots[form_key].add(seg.root)
        if seg.lemma:
            lem_to_roots[seg.lemma].add(seg.root)

    index: dict[str, dict] = {}
    for root in sorted(verses_by_root):
        ordered = sorted(verses_by_root[root])         # canonical: sura, aya asc
        index[root] = {
            "root": root,
            "forms_found": sorted(forms_by_root[root]),
            "verses": [f"{s}:{a}" for s, a in ordered],
            "count": len(ordered),
        }

    resolution = {
        "form_to_roots": {k: sorted(v) for k, v in sorted(form_to_roots.items())},
        "lem_to_roots": {k: sorted(v) for k, v in sorted(lem_to_roots.items())},
    }
    verse_roots = {vid: sorted(roots) for vid, roots in roots_by_verse.items()}
    return index, resolution, verse_roots


def run(verses: list[dict]) -> tuple[list[dict], dict]:
    """Build the QAC root index, fill each verse's `roots`, and persist outputs.

    Signature mirrors `ingestion.morphology.run` so `run_pipeline` is unchanged.
    """
    if not QAC_MORPHOLOGY_TXT.exists():
        raise FileNotFoundError(
            f"{QAC_MORPHOLOGY_TXT} not found. The QAC morphology source is "
            f"required to build the root index."
        )
    with QAC_MORPHOLOGY_TXT.open(encoding="utf-8") as f:
        index, resolution, verse_roots = build(tqdm(f, desc="  qac-morph  ", unit="seg"))

    for v in verses:
        v["roots"] = verse_roots.get(v["id"], [])

    _save(index, resolution, verses)
    n_rootfree = sum(1 for v in verses if not v["roots"])
    print(
        f"  qac-morph  : {len(index)} roots indexed from QAC "
        f"({n_rootfree} verses have no rooted word)"
    )
    return verses, index


def _save(index: dict, resolution: dict, verses: list[dict]) -> None:
    MORPHOLOGY_JSON.parent.mkdir(parents=True, exist_ok=True)
    with MORPHOLOGY_JSON.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    with RESOLUTION_JSON.open("w", encoding="utf-8") as f:
        json.dump(resolution, f, ensure_ascii=False, indent=2)
    with VERSES_FINAL_JSON.open("w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Standalone (re)build of the QAC index over the existing processed corpus.
    from indexing.corpus import load_verses

    load_verses.cache_clear()  # ensure a fresh mutable list we can write back
    verses, index = run(load_verses())
    for key in ["كرم", "اله", "سمو", "حصحص"]:
        entry = index.get(key, {})
        print(f"  {key!r}: count={entry.get('count')} "
              f"forms={entry.get('forms_found', [])[:4]}")
