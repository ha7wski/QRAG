"""
verse_lookup.py — Exhaustive, vocalized root lookup (Verse Lookup feature).

Given a single Arabic word (no diacritics needed), resolve its root via the
existing morphology index and return *every* verse containing that root or any
of its derivatives, displayed WITH full diacritics (chakl).

This is the exhaustive, no-LLM sibling of the `/lexical` ("Lisan Analysis")
feature:
  - `/lexical`     → samples ~30 verses + adds an LLM linguistic analysis.
  - Verse Lookup   → returns ALL verses, no ML at all, vocalized for display.

Design (isolated but reuses existing infrastructure):
  - root resolution + morphology index + clean corpus come from the shared
    `LexicalRetriever` (same root backend that built the index, so a queried
    word maps to the SAME root key).
  - normalization comes from `ingestion.normalizer.normalize_text`.
  - the ONLY new data dependency is `data/raw/quran_chakl.csv`, the sole source
    of fully diacritized text (the processed corpus `text_ar` has no harakat).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indexing.corpus import chakl_by_ref  # noqa: E402
from ingestion.normalizer import normalize_text  # noqa: E402
from retrieval.lexical_retriever import LexicalRetriever  # noqa: E402

logger = logging.getLogger("quran_rag.verse_lookup")


class VerseLookup:
    """Resolve a word to its root(s) and list every verse, vocalized."""

    def __init__(self, retriever: LexicalRetriever | None = None):
        # Reuse the shared morphology index + root extractor.
        self.lex = retriever or LexicalRetriever()
        self.index = self.lex.index

        # Build a normalized {form -> [root keys]} map so a typed surface form
        # (e.g. "رحيم") resolves even when it is not itself a root key.
        self.form_to_roots: dict[str, list[str]] = {}
        for root_key, entry in self.index.items():
            for form in entry.get("forms_found", []):
                nf = normalize_text(form)
                if nf:
                    self.form_to_roots.setdefault(nf, []).append(root_key)

        # Shared, cached source of diacritized display text (the only one).
        self.chakl = chakl_by_ref()

    # ── root resolution ───────────────────────────────────────────────────
    def resolve_roots(self, word: str) -> list[str]:
        """Return every root key the input word maps to (deduplicated, ordered).

        Matching, in order of trust:
          1. the word IS a root key (hyphen-joined, e.g. "ر-ح-م"),
          2. the bare consonant string joins to a root key ("رحم" → "ر-ح-م"),
          3. the word is a known surface form of one or more roots,
          4. fallback: the morphology backend extracts a root for the word.
        """
        w = normalize_text(word)
        if not w:
            return []
        roots: list[str] = []

        def add(rk: str) -> None:
            if rk and rk in self.index and rk not in roots:
                roots.append(rk)

        if word.strip() in self.index:  # already hyphen-joined
            add(word.strip())
        add("-".join(w))                # bare root "رحم" → "ر-ح-م"
        for rk in self.form_to_roots.get(w, []):  # known surface form
            add(rk)
        if not roots:                    # backend extraction fallback
            add(self.lex.extract_root(w))
        return roots

    # ── per-verse word highlighting ───────────────────────────────────────
    @staticmethod
    def _match_indices(vocalized_text: str, forms: list[tuple[str, str]]) -> list[int]:
        """Indices of the whitespace tokens (in the vocalized text) that contain
        a matched surface form, so the frontend can highlight the word in place.

        morphology.json records forms and verses at the root level only, never
        which form sits in which verse, so we reconstruct it. Each vocalized
        token is normalized (harakat stripped) before comparison; a token is
        flagged if any form's normalized surface is a substring of it — this
        catches attached clitics (و/ب/ال... e.g. "يوسف" inside "وَيُوسُفَ").
        Best-effort and deterministic; imperfect for very short forms.
        """
        norm_forms = [nf for _, nf in forms if nf]
        out: list[int] = []
        for i, tok in enumerate(vocalized_text.split()):
            ntok = normalize_text(tok)
            if ntok and any(nf in ntok for nf in norm_forms):
                out.append(i)
        return out

    # ── main entry ────────────────────────────────────────────────────────
    def lookup(self, word: str) -> dict:
        """Return the full Verse Lookup result for `word`."""
        roots = self.resolve_roots(word)
        if not roots:
            return {"word": word, "root": "", "root_found": False,
                    "total": 0, "verses": []}

        # Merge verse refs + surface forms across all matched roots.
        verse_ids: list[str] = []
        seen: set[str] = set()
        forms: list[tuple[str, str]] = []  # (display form, normalized form)
        seen_forms: set[str] = set()
        for rk in roots:
            entry = self.index[rk]
            for vid in entry.get("verses", []):
                if vid not in seen:
                    seen.add(vid)
                    verse_ids.append(vid)
            for form in entry.get("forms_found", []):
                nf = normalize_text(form)
                if form not in seen_forms:
                    seen_forms.add(form)
                    forms.append((form, nf))

        verses = []
        for vid in verse_ids:
            try:
                s, a = (int(x) for x in vid.split(":"))
            except ValueError:
                logger.warning("VerseLookup: malformed verse ref %r, skipping.", vid)
                continue
            chakl = self.chakl.get((s, a))
            if chakl is None:
                logger.warning("VerseLookup: no vocalized row for %s, skipping.", vid)
                continue
            verses.append({
                "surah_number": s,
                "surah_name": chakl["surah_name"],
                "aya_number": a,
                "text": chakl["text"],
                "match_indices": self._match_indices(chakl["text"], forms),
            })

        verses.sort(key=lambda v: (v["surah_number"], v["aya_number"]))
        return {
            "word": word,
            "root": " / ".join(roots),
            "root_found": True,
            "total": len(verses),
            "verses": verses,
        }


if __name__ == "__main__":
    vl = VerseLookup()
    for w in ["رحم", "صبر", "زقزقة"]:
        r = vl.lookup(w)
        print(f"{w} → root={r['root']!r} found={r['root_found']} total={r['total']}")
        for v in r["verses"][:2]:
            print(f"    [{v['surah_number']}:{v['aya_number']}] {v['text']} "
                  f"| match_indices={v['match_indices']}")
