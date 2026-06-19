"""
morphology.py — Stage 4 of the ingestion pipeline.

Builds the Arabic root index that powers the lexical-search feature (F2).
For each verse it extracts the root of every token, then aggregates a global
index mapping each root to the forms found and the verses it appears in.

Backend selection (best available wins, with graceful fallback):
  1. camel-tools  — full morphological analyzer (heavy, ~2 GB models)
  2. tashaphyne   — Arabic light stemmer with root extraction (lightweight)
  3. heuristic    — internal affix-stripping fallback (no extra dependency)

Outputs:
  - data/processed/morphology.json    : root → {root, forms, verses, count}
  - data/processed/verses_final.json  : verses with the `roots` field filled
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(it, **kwargs):  # type: ignore
        return it

ROOT = Path(__file__).resolve().parents[1]
MORPHOLOGY_JSON = ROOT / "data" / "processed" / "morphology.json"
VERSES_FINAL_JSON = ROOT / "data" / "processed" / "verses_final.json"

# Arabic letters considered valid root consonants.
_ARABIC_LETTERS = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")

# Common Arabic clitics for the heuristic fallback.
_PREFIXES = ("وال", "فال", "بال", "كال", "ال", "و", "ف", "ب", "ك", "ل", "س")
_SUFFIXES = ("ون", "ين", "ان", "ات", "ة", "ها", "هم", "هن", "كم", "كن",
             "نا", "ني", "ه", "ي", "ك", "وا", "ت", "ن")


def _format_root(root_chars: str) -> str:
    """Return a root as hyphen-joined Arabic letters, e.g. 'رحم' → 'ر-ح-م'."""
    letters = [c for c in root_chars if c in _ARABIC_LETTERS]
    return "-".join(letters)


# ── Backend: camel-tools ────────────────────────────────────────────────
def _load_camel():
    try:
        from camel_tools.morphology.database import MorphologyDB
        from camel_tools.morphology.analyzer import Analyzer

        db = MorphologyDB.builtin_db()
        analyzer = Analyzer(db)

        def get_root(word: str) -> str:
            analyses = analyzer.analyze(word)
            if not analyses:
                return ""
            root = analyses[0].get("root", "")
            return _format_root(root.replace(".", ""))

        return get_root, "camel-tools"
    except Exception:
        return None


# ── Backend: tashaphyne ─────────────────────────────────────────────────
def _load_tashaphyne():
    try:
        from tashaphyne.stemming import ArabicLightStemmer

        stemmer = ArabicLightStemmer()

        def get_root(word: str) -> str:
            stemmer.light_stem(word)
            root = stemmer.get_root()
            return _format_root(root)

        return get_root, "tashaphyne"
    except Exception:
        return None


# ── Backend: heuristic fallback ─────────────────────────────────────────
def _load_heuristic():
    def get_root(word: str) -> str:
        w = "".join(c for c in word if c in _ARABIC_LETTERS)
        if not w:
            return ""
        # Strip a single leading clitic.
        for p in _PREFIXES:
            if w.startswith(p) and len(w) - len(p) >= 3:
                w = w[len(p):]
                break
        # Strip a single trailing clitic.
        for s in _SUFFIXES:
            if w.endswith(s) and len(w) - len(s) >= 3:
                w = w[: -len(s)]
                break
        return _format_root(w)

    return get_root, "heuristic"


def select_backend():
    """Return (get_root_fn, backend_name) using the best available backend."""
    for loader in (_load_camel, _load_tashaphyne, _load_heuristic):
        result = loader()
        if result is not None:
            return result
    return _load_heuristic()  # unreachable, but keeps the type stable


def run(verses: list[dict]) -> tuple[list[dict], dict]:
    """Build the root index, fill each verse's `roots`, and persist outputs."""
    get_root, backend = select_backend()
    if backend == "heuristic":
        print("  morphology : ⚠️  camel-tools and tashaphyne unavailable, "
              "using the heuristic fallback (approximate roots)")

    index: dict[str, dict] = {}

    for v in tqdm(verses, desc="  morphology ", unit="verse"):
        verse_roots: set[str] = set()
        for token in v["text_ar_clean"].split():
            root = get_root(token)
            if not root or len(root.replace("-", "")) < 2:
                continue
            verse_roots.add(root)
            entry = index.setdefault(
                root, {"root": root, "forms": set(), "verses": set(), "count": 0}
            )
            entry["forms"].add(token)
            entry["verses"].add(v["id"])
        v["roots"] = sorted(verse_roots)

    # Convert sets to sorted lists and compute counts (occurrences = verses).
    serializable: dict[str, dict] = {}
    for root, entry in index.items():
        verses_list = sorted(
            entry["verses"], key=lambda vid: tuple(map(int, vid.split(":")))
        )
        serializable[root] = {
            "root": root,
            "forms_found": sorted(entry["forms"]),
            "verses": verses_list,
            "count": len(verses_list),
        }

    _save(serializable, verses)
    print(f"  morphology : {len(serializable)} roots indexed ({backend} backend)")
    return verses, serializable


def _save(index: dict, verses: list[dict]) -> None:
    MORPHOLOGY_JSON.parent.mkdir(parents=True, exist_ok=True)
    with MORPHOLOGY_JSON.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    with VERSES_FINAL_JSON.open("w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    get_root, backend = select_backend()
    print(f"Backend: {backend}")
    for w in ["الرحمن", "الرحيم", "العالمين", "يعلمون"]:
        print(f"  {w} → {get_root(w)}")
