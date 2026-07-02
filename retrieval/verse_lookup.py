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
    `LexicalRetriever`, whose QAC maps resolve a queried word to the SAME root
    key that was stored (root-safe normalization on both sides).
  - display normalization for word highlighting comes from
    `ingestion.normalizer.normalize_text`.
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
        # Reuse the shared morphology index + QAC resolver.
        self.lex = retriever or LexicalRetriever()
        self.index = self.lex.index

        # Shared, cached source of diacritized display text (the only one).
        self.chakl = chakl_by_ref()

    # ── root resolution ───────────────────────────────────────────────────
    def resolve_roots(self, word: str) -> list[str]:
        """Return every root key the input word maps to (deduplicated, ordered).

        Delegates to the shared LexicalRetriever's QAC ladder (raw-root keys):
          1. the root-safe-normalized input IS a root key,
          2. known QAC surface FORM → root(s),
          3. known QAC lemma → root(s),
          4. external stemmer fallback — only if QAC_STEMMER_FALLBACK=1.
        Homographs return multiple roots.

        Note on QAC segmentation: QAC splits clitics into separate segments, so
        the FORM map keys are clitic-stripped surface segments (e.g. "بسم" is
        stored as "بِ" + "سْمِ", never as a whole-word form). A word that only
        ever occurs with attached clitics may therefore miss the FORM step and
        rely on the lemma or bare-root steps; if none match and the stemmer
        fallback is disabled, it returns no roots — an accepted trade-off of the
        QAC-only default.
        """
        return self.lex.resolve_roots(word)

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
