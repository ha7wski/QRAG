"""
lexical_retriever.py — Root-based lexical lookup (feature F2 / Verse Study).

Given an Arabic word, resolves its root(s) via the Quranic Arabic Corpus (QAC)
maps built by `ingestion/qac_morphology.py`, then looks up every occurrence of
that root in the morphology index (`morphology.json`). Returns the surface forms
found, the full occurrence count, and a representative, evenly-spread sample of
the verses (so the LLM analysis covers the whole Quran rather than just the
first occurrences).

Resolution is QAC-only by default (D3): the roots are manually verified, so a
typed word maps to the exact root key that was stored, keyed by the root-safe
normalization in `ingestion.root_normalize` (never `normalizer.normalize_text`,
which deletes hamza). An external stemmer fallback exists but is gated behind
`QAC_STEMMER_FALLBACK=1` (OFF by default, mirroring the reranker toggle); when
off, out-of-corpus words simply return no match.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indexing.corpus import verses_by_id  # noqa: E402
from ingestion.root_normalize import normalize_root  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MORPHOLOGY_JSON = ROOT / "data" / "processed" / "morphology.json"
RESOLUTION_JSON = ROOT / "data" / "processed" / "qac_resolution.json"

DEFAULT_SAMPLE = 30


def _stemmer_fallback_enabled() -> bool:
    """External-stemmer fallback is OFF unless QAC_STEMMER_FALLBACK=1."""
    return os.getenv("QAC_STEMMER_FALLBACK", "0") == "1"


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
        # QAC resolution maps: normalized FORM/LEM → [root keys].
        self.form_to_roots: dict[str, list[str]] = {}
        self.lem_to_roots: dict[str, list[str]] = {}
        if RESOLUTION_JSON.exists():
            with RESOLUTION_JSON.open(encoding="utf-8") as f:
                res = json.load(f)
            self.form_to_roots = res.get("form_to_roots", {})
            self.lem_to_roots = res.get("lem_to_roots", {})
        self.verses_by_id = verses_by_id()  # shared, cached {id: verse} lookup
        self._stemmer = None  # lazily loaded only if the fallback is enabled

    # ── root resolution (QAC ladder, D3) ──────────────────────────────────
    def resolve_roots(self, word: str) -> list[str]:
        """Return every root key `word` maps to (deduplicated, ordered).

        Ladder, in order of trust (all keyed by root-safe normalization):
          1. the normalized input IS a root key,
          2. known QAC surface FORM → root(s),
          3. known QAC lemma → root(s),
          4. external stemmer fallback — only if QAC_STEMMER_FALLBACK=1.

        Homographs return multiple roots (e.g. "كل" → ["اكل", "كلل", "كيل"]).
        Returns [] when nothing matches and the stemmer fallback is disabled.
        """
        w = normalize_root(word)
        if not w:
            return []
        roots: list[str] = []

        def add(rk: str) -> None:
            if rk and rk in self.index and rk not in roots:
                roots.append(rk)

        if w in self.index:                       # 1. already a root key
            add(w)
        for rk in self.form_to_roots.get(w, []):  # 2. surface FORM → root(s)
            add(rk)
        for rk in self.lem_to_roots.get(w, []):   # 3. lemma → root(s)
            add(rk)
        if not roots and _stemmer_fallback_enabled():  # 4. gated fallback
            add(self._stem_root(w))
        return roots

    def extract_root(self, word: str) -> str:
        """Map an input word to a single root key (the best/first match).

        Convenience for callers that want one root (query expansion, LLM
        analysis). Returns "" when the word resolves to no known root.
        """
        roots = self.resolve_roots(word)
        return roots[0] if roots else ""

    def _stem_root(self, normalized_word: str) -> str:
        """Fallback: extract a root via the legacy stemmer, mapped into the QAC
        key space. Only reached when QAC_STEMMER_FALLBACK=1."""
        if self._stemmer is None:
            from ingestion.morphology import select_backend  # lazy, heavy

            self._stemmer, _ = select_backend()
        raw = self._stemmer(normalized_word)          # hyphen-joined, old format
        return normalize_root(raw.replace("-", ""))   # → QAC raw-root key space

    # ── occurrence retrieval ──────────────────────────────────────────────
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
        """Convenience: resolve the root for `word` and retrieve its occurrences."""
        root = self.extract_root(word)
        result = self.retrieve_by_root(root, sample=sample)
        result["word"] = word
        return result


if __name__ == "__main__":
    lr = LexicalRetriever()
    for w in ["رحمة", "الصبر", "علم", "كريم"]:
        r = lr.lookup(w, sample=5)
        print(f"{w} → root={r['root']} | occurrences={r['occurrences_count']} "
              f"| forms={r['forms'][:5]}")
        for v in r["verses"]:
            print(f"    [{v['id']}] {v['text_ar']}")
