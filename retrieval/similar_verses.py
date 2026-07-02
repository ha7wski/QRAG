"""
similar_verses.py — Root-based candidate generation for the "Similar Verses" tab.

The dense branch is noise for short Classical-Arabic phrase queries, and plain
BM25 pulls false positives on ambiguous function words (e.g. لمّا). This path
instead:

  1. CLEAN the query — drop function words (an explicit particle stoplist) and
     reduce each content word to its QAC root, stripping attached clitics /
     pronoun suffixes so inflected forms resolve (e.g. "اشده" → strip ـه → "اشد"
     → root ش-د-د, which the bare surface form alone does NOT resolve).
  2. GENERATE candidates — verses containing those roots, scored by IDF-weighted
     coverage: a verse matching more (and rarer) query roots ranks higher. This
     naturally prefers AND-style overlap (all roots present) while still keeping
     partial matches, and never returns the function-word noise.

The caller compares the full query against these candidates (cross-encoder
rerank) and applies the relevance threshold. If the query yields no content
roots, `candidates_for` returns None so the caller can fall back to hybrid.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indexing.text_normalize import normalize_search  # noqa: E402

# Arabic function words to drop before root extraction. Stored raw; normalized
# with normalize_search at load so comparison matches the tokenized query
# (hamza folded, ى→ي, ة→ه). Explicit list because some particles spuriously
# resolve to a root via a homograph (e.g. لمّا → لمم from "أكلاً لمّاً").
_STOPWORDS_RAW = [
    "و", "ف", "ب", "ك", "ل", "ال", "لل",
    "لما", "ما", "من", "في", "على", "إلى", "عن", "إن", "أن", "أنه", "إنه",
    "لا", "لم", "لن", "قد", "ثم", "أو", "أم", "بل", "لكن", "حتى", "إذا", "إذ",
    "كي", "لكي", "لو", "لولا", "هل", "يا", "إلا", "مع", "كما",
    "هو", "هي", "هم", "هن", "هما", "أنت", "أنا", "نحن", "أنتم",
    "هذا", "هذه", "ذلك", "تلك", "الذي", "التي", "الذين",
    "كل", "بعض", "غير", "عند", "بين", "لدى", "نحو", "قبل", "بعد", "دون",
]
STOPWORDS = frozenset(normalize_search(w) for w in _STOPWORDS_RAW)

# Enclitic pronoun suffixes / proclitics to peel (longest first) when a token
# does not resolve, retrying resolution on the bare stem. Conservative: a strip
# is accepted only if it actually yields a known root.
_SUFFIXES = ["هما", "كما", "هم", "هن", "كم", "كن", "نا", "ني", "ها", "ه", "ك", "ي"]
_PREFIXES = ["وال", "فال", "بال", "كال", "ال", "لل", "و", "ف", "ب", "ك", "ل", "س"]

POOL_CAP = 60  # max candidates handed to the comparison/rerank stage


class SimilarVerses:
    def __init__(self, lexical_retriever):
        # Reuse the shared LexicalRetriever: QAC index + resolver + verse records.
        self.lex = lexical_retriever
        self.N = len(self.lex.verses_by_id) or 6236

    # ── query cleaning → content roots ────────────────────────────────────
    def _resolve_token(self, token: str) -> list[str]:
        """Resolve a token to root(s), retrying with clitics/pronouns stripped."""
        roots = self.lex.resolve_roots(token)
        if roots:
            return roots
        for suf in _SUFFIXES:
            if token.endswith(suf) and len(token) - len(suf) >= 2:
                roots = self.lex.resolve_roots(token[: -len(suf)])
                if roots:
                    return roots
        for pre in _PREFIXES:
            if token.startswith(pre) and len(token) - len(pre) >= 2:
                roots = self.lex.resolve_roots(token[len(pre):])
                if roots:
                    return roots
        return []

    def content_terms(self, query: str) -> list[str]:
        """Query tokens with function words removed — used to clean the BM25 query
        so it doesn't match verses via a shared particle (e.g. لمّا)."""
        return [
            tok
            for tok in normalize_search(query).split()
            if tok and tok not in STOPWORDS
        ]

    def content_roots(self, query: str) -> list[str]:
        """Return the deduped roots of the query's content words (stopwords out)."""
        roots: list[str] = []
        for tok in normalize_search(query).split():
            if not tok or tok in STOPWORDS:
                continue
            for r in self._resolve_token(tok):
                if r not in roots:
                    roots.append(r)
        return roots

    # ── context comparison (query-root coverage) ─────────────────────────
    def query_root_idf(self, query: str) -> dict[str, tuple[float, set]]:
        """`{root: (idf, verse_set)}` for the query's content roots — used to
        score how much of the query's context (its meaningful words) a candidate
        actually covers."""
        out: dict[str, tuple[float, set]] = {}
        for r in self.content_roots(query):
            entry = self.lex.index.get(r)
            if entry:
                df = entry.get("count") or len(entry.get("verses", []))
                out[r] = (math.log(self.N / max(df, 1)), set(entry.get("verses", [])))
        return out

    @staticmethod
    def coverage_fraction(verse_id: str, root_idf: dict[str, tuple[float, set]]) -> float:
        """Fraction (IDF-weighted) of the query's content roots present in the
        verse. 1.0 = the verse shares the query's whole content context; 0.0 =
        it matched only via a function word / a single shared surface token.
        Returns 1.0 when the query has no content roots (coverage is inapplicable)."""
        if not root_idf:
            return 1.0
        total = sum(idf for idf, _ in root_idf.values())
        got = sum(idf for idf, vs in root_idf.values() if verse_id in vs)
        return (got / total) if total else 1.0

    # ── root-based candidate generation ───────────────────────────────────
    def candidates_for(self, query: str, filters: dict | None = None) -> list[dict] | None:
        """Return candidate verse records ranked by IDF-weighted root coverage,
        or None if the query has no resolvable content root (→ caller falls back).
        """
        roots = self.content_roots(query)
        if not roots:
            return None

        scores: dict[str, float] = {}
        for r in roots:
            entry = self.lex.index.get(r)
            if not entry:
                continue
            df = entry.get("count") or len(entry.get("verses", []))
            idf = math.log(self.N / max(df, 1))
            for vid in entry.get("verses", []):
                scores[vid] = scores.get(vid, 0.0) + idf
        if not scores:
            return None

        ranked_ids = sorted(scores, key=lambda v: scores[v], reverse=True)[:POOL_CAP]
        records: list[dict] = []
        for vid in ranked_ids:
            v = self.lex.verses_by_id.get(vid)
            if v is None:
                continue
            if filters and not _passes(v, filters):
                continue
            records.append({**v, "score": round(scores[vid], 4)})
        return records or None


def _passes(verse: dict, filters: dict) -> bool:
    for key in ("surah_number", "period", "juz"):
        if filters.get(key) is not None and verse.get(key) != filters[key]:
            return False
    return True


if __name__ == "__main__":
    from retrieval.lexical_retriever import LexicalRetriever

    sv = SimilarVerses(LexicalRetriever())
    for q in ["و لما بلغ اشده", "الحمد لله رب العالمين", "قل هو الله احد"]:
        roots = sv.content_roots(q)
        cands = sv.candidates_for(q) or []
        print(f"{q!r}\n  roots={roots}  candidates={len(cands)}  top={[c['id'] for c in cands[:8]]}")
