"""
lexical_retriever.py — Root-based lexical lookup (feature F2).

Given an Arabic word, extracts its root, then looks up every occurrence of
that root in the morphology index (`morphology.json`). Returns the surface
forms found, the full occurrence count, and a representative, evenly-spread
sample of the verses (so the LLM analysis covers the whole Quran rather than
just the first occurrences).

The root extractor is the SAME backend used to build the index
(camel-tools → tashaphyne → heuristic), so a queried word maps to the same
root key that was stored.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indexing.corpus import verses_by_id  # noqa: E402
from ingestion.morphology import select_backend  # noqa: E402
from ingestion.normalizer import normalize_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MORPHOLOGY_JSON = ROOT / "data" / "processed" / "morphology.json"

DEFAULT_SAMPLE = 30


def _sample_evenly(items: list, k: int) -> list:
    """Return up to k items evenly spread across the list (order preserved)."""
    n = len(items)
    if n <= k:
        return list(items)
    step = n / k
    return [items[int(i * step)] for i in range(k)]


class LexicalRetriever:
    def __init__(self):
        with MORPHOLOGY_JSON.open(encoding="utf-8") as f:
            self.index: dict[str, dict] = json.load(f)
        self.verses_by_id = verses_by_id()  # shared, cached {id: verse} lookup
        self._get_root, self.backend = select_backend()

    def extract_root(self, word: str) -> str:
        """Map an input word to a root key (hyphen-joined Arabic letters).

        Accepts a plain word ("رحمة"), an already-joined root ("ر-ح-م"), or a
        bare root ("رحم"). Falls back to direct index membership checks.
        """
        word = (word or "").strip()
        if not word:
            return ""
        # Already in the canonical hyphen-joined form?
        if word in self.index:
            return word
        # Bare consonant root like "رحم" → "ر-ح-م"?
        joined = "-".join(word)
        if joined in self.index:
            return joined
        # Otherwise extract via the morphology backend on the normalized word.
        root = self._get_root(normalize_text(word))
        return root

    def retrieve_by_root(self, root: str, sample: int = DEFAULT_SAMPLE) -> dict:
        """Return a structured lexical result for a root key."""
        entry = self.index.get(root)
        if not entry:
            return {
                "root": root,
                "forms": [],
                "occurrences_count": 0,
                "verse_ids": [],
                "verses": [],
            }
        verse_ids = entry["verses"]
        sampled_ids = _sample_evenly(verse_ids, sample)
        verses = [self.verses_by_id[v] for v in sampled_ids if v in self.verses_by_id]
        return {
            "root": root,
            "forms": entry.get("forms_found", []),
            "occurrences_count": entry.get("count", len(verse_ids)),
            "verse_ids": verse_ids,
            "verses": verses,
        }

    def lookup(self, word: str, sample: int = DEFAULT_SAMPLE) -> dict:
        """Convenience: extract the root for `word` and retrieve its occurrences."""
        root = self.extract_root(word)
        result = self.retrieve_by_root(root, sample=sample)
        result["word"] = word
        return result


if __name__ == "__main__":
    lr = LexicalRetriever()
    for w in ["رحمة", "الصبر", "علم"]:
        r = lr.lookup(w, sample=5)
        print(f"{w} → root={r['root']} | occurrences={r['occurrences_count']} "
              f"| forms={r['forms'][:5]}")
        for v in r["verses"]:
            print(f"    [{v['id']}] {v['text_ar']}")
