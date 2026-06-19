"""
query_processor.py — Analyze and expand a user query before retrieval.

Detects the query language, whether it is a lexical (single-word) lookup,
the Arabic root(s) present, simple inline filters (period), and a light
expansion based on the morphology index (root surface forms). The LLM is not
used here, so processing is fast and deterministic.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.normalizer import normalize_text  # noqa: E402

try:
    from langdetect import detect as _ld_detect  # type: ignore

    _HAS_LANGDETECT = True
except Exception:  # pragma: no cover
    _HAS_LANGDETECT = False

_ARABIC_RANGE = range(0x0600, 0x06FF + 1)


@dataclass
class ProcessedQuery:
    original: str
    normalized: str
    language: str                  # "ar" | "fr" | "en" | "unknown"
    expanded_terms: list[str] = field(default_factory=list)
    filters: dict = field(default_factory=dict)


def _is_arabic(text: str) -> bool:
    return any(ord(ch) in _ARABIC_RANGE for ch in text)


def detect_language(text: str) -> str:
    if _is_arabic(text):
        return "ar"
    if _HAS_LANGDETECT:
        try:
            lang = _ld_detect(text)
            if lang in ("fr", "en"):
                return lang
            return lang
        except Exception:
            return "unknown"
    return "unknown"


def detect_filters(text: str) -> dict:
    """Detect simple inline filters mentioned in the query."""
    low = text.lower()
    filters: dict = {}
    if "makki" in low or "mecquoise" in low or "meccan" in low or "مكي" in text:
        filters["period"] = "makkiyya"
    elif "madani" in low or "médinoise" in low or "medinan" in low or "مدني" in text:
        filters["period"] = "madani"
    return filters


class QueryProcessor:
    def __init__(self, lexical_retriever=None):
        # Lazily reuse a LexicalRetriever for root extraction / expansion.
        self._lexical = lexical_retriever

    def _lex(self):
        if self._lexical is None:
            from retrieval.lexical_retriever import LexicalRetriever

            self._lexical = LexicalRetriever()
        return self._lexical

    def process(self, query: str) -> ProcessedQuery:
        original = query.strip()
        normalized = normalize_text(original) if _is_arabic(original) else original
        language = detect_language(original)
        filters = detect_filters(original)

        # arabic_roots is a local intermediate: it only exists to derive the
        # expansion terms below — it is not exposed on ProcessedQuery.
        arabic_roots: list[str] = []
        expanded_terms: list[str] = []

        if _is_arabic(original):
            tokens = [t for t in normalized.split() if t]
            lex = self._lex()
            for tok in tokens:
                root = lex.extract_root(tok)
                if root and root not in arabic_roots:
                    arabic_roots.append(root)
            if arabic_roots:
                # Light expansion: add a few surface forms of the main root.
                entry = lex.index.get(arabic_roots[0])
                if entry:
                    expanded_terms = entry.get("forms_found", [])[:8]

        return ProcessedQuery(
            original=original,
            normalized=normalized,
            language=language,
            expanded_terms=expanded_terms,
            filters=filters,
        )


if __name__ == "__main__":
    qp = QueryProcessor()
    for q in ["الصبر", "Que dit le Coran sur la patience ?", "verses about mercy (makki)"]:
        pq = qp.process(q)
        print(f"\nQ: {q}")
        print(f"  lang={pq.language} filters={pq.filters}")
        print(f"  expanded={pq.expanded_terms}")
