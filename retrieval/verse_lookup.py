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
  - word-highlight matching uses the hamza-safe `indexing.text_normalize.
    normalize_search` (keeps the alif; `normalize_text` deletes hamza and would
    over-match, e.g. أَرْض → رض matching every عرض/مرض token).
  - the ONLY new data dependency is `data/raw/quran_chakl.csv`, the sole source
    of fully diacritized text (the processed corpus `text_ar` has no harakat).
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indexing.corpus import chakl_by_ref  # noqa: E402
from indexing.text_normalize import normalize_search  # noqa: E402
from retrieval.lexical_retriever import (  # noqa: E402
    LexicalRetriever,
    _clitic_alif_candidates,
)

logger = logging.getLogger("quran_rag.verse_lookup")

ROOT = Path(__file__).resolve().parents[1]
LEMMA_INDEX_JSON = ROOT / "data" / "processed" / "lemma_index.json"
PROPER_NOUNS_JSON = ROOT / "data" / "processed" / "proper_nouns.json"


class VerseLookup:
    """Resolve a word to its root(s) and list every verse, vocalized, grouped by
    lemma (the root's occurrences split per lemma / sense)."""

    def __init__(self, retriever: LexicalRetriever | None = None):
        # Reuse the shared morphology index + QAC resolver.
        self.lex = retriever or LexicalRetriever()
        self.index = self.lex.index

        # Shared, cached source of diacritized display text (the only one).
        self.chakl = chakl_by_ref()

        # Lemma index: root → [{lemma, lemma_display, forms_found, verses, count}].
        # Optional — if absent (built by an older pipeline), the lookup falls back
        # to a single synthetic group per root (see _lemma_groups_for_root).
        self.lemma_index: dict[str, list[dict]] = {}
        if LEMMA_INDEX_JSON.exists():
            with LEMMA_INDEX_JSON.open(encoding="utf-8") as f:
                self.lemma_index = json.load(f)
        else:
            logger.warning(
                "VerseLookup: %s not found — falling back to root-level grouping. "
                "Run `python -m ingestion.qac_morphology` to build it.",
                LEMMA_INDEX_JSON,
            )

        # Proper-noun index: search-normalized lemma → {lemma_display, forms_found,
        # verses, count} for rootless names (لوط, إبراهيم …). Optional: absent →
        # proper nouns simply stay unresolvable (pre-rebuild behavior).
        self.proper_nouns: dict[str, dict] = {}
        if PROPER_NOUNS_JSON.exists():
            with PROPER_NOUNS_JSON.open(encoding="utf-8") as f:
                self.proper_nouns = json.load(f)

    # ── root resolution ───────────────────────────────────────────────────
    def resolve_roots(self, word: str) -> list[str]:
        """Return every root key the input word maps to (deduplicated, ordered).

        Delegates to the shared LexicalRetriever's *lenient* resolver: the QAC
        ladder (root-key → surface FORM → lemma → gated stemmer) plus a fallback
        that retries on clitic-stripped and plene→defective-alif variants when
        the exact word misses. Homographs return multiple roots.

        Note on QAC segmentation: QAC splits clitics into separate segments, so
        the FORM map keys are clitic-stripped surface segments (e.g. "بسم" is
        stored as "بِ" + "سْمِ", never as a whole-word form). This is exactly why
        the lenient path is used here: a word typed with a leading `ال`
        (السماوات) or a plene alif the mushaf writes as a dagger alif (سماوات vs
        stored سموات) would otherwise miss every step and return no roots.
        """
        return self.lex.resolve_roots_lenient(word)

    # ── per-verse word highlighting ───────────────────────────────────────
    @staticmethod
    def _match_indices(vocalized_text: str, forms: list[tuple[str, str]]) -> list[int]:
        """Indices of the whitespace tokens (in the vocalized text) that contain
        a matched surface form, so the frontend can highlight the word in place.

        morphology.json records forms and verses at the root level only, never
        which form sits in which verse, so we reconstruct it. Both the form and
        the vocalized token are normalized with the HAMZA-SAFE `normalize_search`
        (keeps the alif — `أَرْض` → `ارض`, not `رض`) before comparison; a token is
        flagged if any form's normalized surface is a substring of it — this
        catches attached clitics (و/ب/ال... e.g. "يوسف" inside "وَيُوسُفَ").

        Using `normalize_search` (not `normalize_text`, which DELETES hamza) is
        essential: hamza deletion collapsed `أَرْض` to `رض`, which then matched
        every عرض/مرض/فرض token as a substring and highlighted the wrong words.
        Best-effort and deterministic; still imperfect for very short forms.
        """
        norm_forms = [nf for _, nf in forms if nf]
        out: list[int] = []
        for i, tok in enumerate(vocalized_text.split()):
            ntok = normalize_search(tok)
            if ntok and any(nf in ntok for nf in norm_forms):
                out.append(i)
        return out

    # ── lemma grouping ────────────────────────────────────────────────────
    def _lemma_groups_for_root(self, rk: str) -> list[dict]:
        """The lemma groups of a root (dominant lemma first). Falls back to one
        synthetic group covering the whole root when no lemma index is loaded."""
        groups = self.lemma_index.get(rk)
        if groups:
            return groups
        entry = self.index.get(rk, {})
        return [{
            "lemma": rk,
            "lemma_display": rk,
            "forms_found": entry.get("forms_found", []),
            "verses": entry.get("verses", []),
        }]

    def _verse_row(self, vid: str, forms: list[tuple[str, str]]) -> dict | None:
        """Build one vocalized verse row (with match highlighting), or None if the
        ref is malformed / has no vocalized source row."""
        try:
            s, a = (int(x) for x in vid.split(":"))
        except ValueError:
            logger.warning("VerseLookup: malformed verse ref %r, skipping.", vid)
            return None
        chakl = self.chakl.get((s, a))
        if chakl is None:
            logger.warning("VerseLookup: no vocalized row for %s, skipping.", vid)
            return None
        return {
            "surah_number": s,
            "surah_name": chakl["surah_name"],
            "aya_number": a,
            "text": chakl["text"],
            "match_indices": self._match_indices(chakl["text"], forms),
        }

    def _rows_for(self, verse_ids: list[str], forms_found: list[str]) -> list[dict]:
        """Vocalized rows for a list of verse refs, highlighting `forms_found`."""
        forms = [(f, normalize_search(f)) for f in forms_found]
        rows = []
        for vid in verse_ids:
            row = self._verse_row(vid, forms)
            if row is not None:
                rows.append(row)
        return rows

    # ── proper-noun fallback (rootless names) ─────────────────────────────
    def _resolve_proper_noun(self, word: str) -> dict | None:
        """Resolve a rootless proper noun (لوط, إبراهيم …). Tries the search-
        normalized word, then clitic-stripped / alif-collapsed variants (so
        لوط, لوطًا, ولوط all reach the same name)."""
        if not self.proper_nouns:
            return None
        key = normalize_search(word)
        if not key:
            return None
        pn = self.proper_nouns.get(key)
        if pn:
            return pn
        for stem in _clitic_alif_candidates(key):
            pn = self.proper_nouns.get(stem)
            if pn:
                return pn
        return None

    # ── main entry ────────────────────────────────────────────────────────
    def lookup(self, word: str) -> dict:
        """Return the full Verse Lookup result for `word`, grouped by lemma.

        The word resolves to root(s); each root's occurrences are split into its
        lemmas (e.g. سمو → سماء "heaven" / اسم "name"), so the UI can show the
        root and the distinct lemmas found under it. Highlighting is per lemma
        (only that lemma's surface forms are marked in each verse).

        When the word has no QAC root it may still be a proper noun (لوط, موسى …),
        which QAC leaves rootless; those resolve via the proper-noun index and
        come back as a single group with an empty root and `is_proper_noun`."""
        # Resolution order: strict root → proper noun → lenient root. Proper nouns
        # come BEFORE the lenient (clitic-stripping) pass so a name like "لوطًا"
        # resolves to the prophet لوط, not to a spurious root found by peeling its
        # leading ل (which would otherwise give وطأ).
        roots = self.lex.resolve_roots(word)          # strict, exact QAC ladder
        if not roots:
            pn = self._resolve_proper_noun(word)       # rootless proper noun?
            if pn is not None:
                verses = self._rows_for(pn.get("verses", []), pn.get("forms_found", []))
                return {
                    "word": word,
                    "root": "",
                    "roots": [],
                    "root_found": True,
                    "is_proper_noun": True,
                    "total": len(verses),
                    "lemmas": [{
                        "root": "",
                        "lemma": pn["lemma"],
                        "lemma_display": pn.get("lemma_display") or pn["lemma"],
                        "count": len(verses),
                        "verses": verses,
                    }],
                }
            roots = self.lex.resolve_roots_lenient(word)  # clitic/alif retries

        if not roots:
            return {"word": word, "root": "", "roots": [], "root_found": False,
                    "is_proper_noun": False, "total": 0, "lemmas": []}

        lemma_groups: list[dict] = []
        seen_verses: set[str] = set()
        for rk in roots:
            for lg in self._lemma_groups_for_root(rk):
                verses = self._rows_for(lg.get("verses", []), lg.get("forms_found", []))
                if not verses:
                    continue
                seen_verses.update(
                    f"{r['surah_number']}:{r['aya_number']}" for r in verses
                )
                lemma_groups.append({
                    "root": rk,
                    "lemma": lg["lemma"],
                    "lemma_display": lg.get("lemma_display") or lg["lemma"],
                    "count": len(verses),
                    "verses": verses,
                })

        return {
            "word": word,
            "root": " / ".join(roots),
            "roots": roots,
            "root_found": True,
            "is_proper_noun": False,
            "total": len(seen_verses),
            "lemmas": lemma_groups,
        }


if __name__ == "__main__":
    vl = VerseLookup()
    for w in ["السماوات", "صبر", "زقزقة"]:
        r = vl.lookup(w)
        print(f"{w} → root={r['root']!r} found={r['root_found']} total={r['total']} "
              f"lemmas={len(r['lemmas'])}")
        for g in r["lemmas"][:3]:
            print(f"    lemma {g['lemma_display']!r} ({g['root']}): {g['count']} verses"
                  f" — e.g. {g['verses'][0]['surah_number']}:{g['verses'][0]['aya_number']}"
                  if g["verses"] else "")
