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
  - word highlighting reads the POSITIONS QAC already knows: `root_graph`
    (root → the word refs `s:a:w` carrying it, primary and alternate readings)
    crossed with `word_index` (that word's character span in the chakl row, 77 429
    of 77 429 aligned). Substring matching survives only as the fallback for a
    root or a verse the spine cannot answer for — see `_match_indices`.
  - the ONLY new data dependency is the vocalized corpus
    (`quran_data.paths.QURAN_CHAKL_CSV`), the sole source of fully diacritized
    text (the processed corpus `text_ar` has no harakat). It is reached through
    `quran_data.corpus.chakl_by_ref()`, never opened here.
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quran_data.corpus import chakl_by_ref, strip_leading_basmala  # noqa: E402
from arabic_text import normalize_search  # noqa: E402
from quran_data import loaders, paths  # noqa: E402
from retrieval.lexical_retriever import (  # noqa: E402
    LexicalRetriever,
    clitic_alif_candidates,
)

logger = logging.getLogger("quran_rag.verse_lookup")

# Superscript (dagger) alef. QAC surface forms write some words with it
# (بَقَرَٰت) where the vocalized mushaf uses a plene alef (بَقَرَات). normalize_search
# strips U+0670 as a diacritic — dropping the alef — so the form (→ بقرت) failed to
# match the plene token (→ بقرات) and the word was left un-highlighted. Folding it to
# a full alef on BOTH sides before normalize_search reconciles the two orthographies.
_SUPERSCRIPT_ALEF = "ٰ"

# Display tokens are whitespace-separated runs, exactly what `str.split()` yields
# and what the frontend renders — the waqf marks the chakl CSV writes standalone
# (ۖ ۗ …) included, so a span index and a `split()` index cannot drift apart.
_TOKEN_RE = re.compile(r"\S+")


def _narrow(hits: list[int], text: str, spans: list[tuple[int, int]],
            norm_forms: list[str]) -> list[int]:
    """Keep, among the tokens one QAC word covers, those carrying its lexical part.

    Only ever applied INSIDE a span the alignment already proved correct, so it
    can narrow but never wander: at worst it keeps everything. That is why a
    substring test is safe here and is not in `_match_indices`, where it had the
    whole verse to go wrong in.

    What it removes is the vocative particle. QAC glues `يٰ` to the noun it calls,
    so `يٰأيها` is one word covering the two tokens `يَا أَيُّهَا`; the particle bears
    no root and must not be marked. Single-token words skip it entirely.
    """
    if len(hits) < 2 or not norm_forms:
        return hits
    kept = [i for i in hits
            if any(nf in _norm_match(text[spans[i][0]:spans[i][1]]) for nf in norm_forms)]
    return kept or hits          # never leave a word unmarked


def _norm_match(text: str) -> str:
    """Hamza-safe search normalization with the dagger alef folded to a plene
    alef, for word-highlight matching only (local to Verse Lookup — the shared
    normalize_search is left untouched, so BM25/search are unaffected)."""
    return normalize_search(text.replace(_SUPERSCRIPT_ALEF, "ا"))


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
        # Shared and cached by the registry; READ-ONLY, like every loader result.
        try:
            self.lemma_index: dict[str, list[dict]] = loaders.lemma_index()
        except loaders.DatasetMissing:
            self.lemma_index = {}
            logger.warning(
                "VerseLookup: %s not found — falling back to root-level grouping. "
                "Run `python -m ingestion.qac_morphology` to build it.",
                paths.LEMMA_INDEX_JSON,
            )

        # Proper-noun index: search-normalized lemma → {lemma_display, forms_found,
        # verses, count} for rootless names (لوط, إبراهيم …). Optional: absent →
        # proper nouns simply stay unresolvable (pre-rebuild behavior).
        try:
            self.proper_nouns: dict[str, dict] = loaders.proper_nouns()
        except loaders.DatasetMissing:
            self.proper_nouns = {}

        # Highlight spine: LAZY, like `HybridSearch.embedder`. `word_index` costs
        # ~52 MB resident and only the highlighter reads it, so a backend serving
        # chat and never a word lookup must not pay for it at startup. Loaded on the
        # first highlight; see `_spine`.
        self._spine_cache: tuple[dict[str, list[str]], dict[str, dict]] | None = None
        # Which words serve as a grammatical tool rather than carry their meaning.
        # Optional and lazy like the spine; absent → nothing is set apart, which is
        # the behaviour a corpus built before Stage 5 emitted it already had.
        self._word_function_cache: dict[str, str] | None = None

        # Per-root token maps and per-verse display spans, both built on demand:
        # a lookup touches a handful of roots, never all 1656.
        self._root_tokens: dict[str, tuple[dict, set]] = {}
        self._spans: dict[tuple[int, int], tuple[str, int, list[tuple[int, int]]]] = {}

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

    # ── per-verse word highlighting: positions first ──────────────────────
    def _spine(self) -> tuple[dict[str, list[str]], dict[str, dict]]:
        """`(root_graph, word_index)`, both built by `ingestion/qac_treebank.py`.

        Which WORD of a verse carries the root, and where that word sits in the
        chakl row. Optional the same way the lemma and proper-noun indexes are: a
        corpus built before Stage 5 existed has neither, and highlighting degrades
        to the substring fallback rather than failing. Read through `getattr` so an
        object assembled by `__new__` (tests) still works.

        Both are registry loaders, so a backend already serving QLisan — which
        reads `word_index` for its per-word fiche — holds ONE copy of each.
        """
        sp = getattr(self, "_spine_cache", None)
        if sp is None:
            try:
                sp = (loaders.root_graph(), loaders.word_index())
            except loaders.DatasetMissing:
                sp = ({}, {})
                logger.warning(
                    "VerseLookup: %s / %s not found — highlighting falls back to "
                    "substring matching. Run `python -m ingestion.qac_treebank`.",
                    paths.ROOT_GRAPH_JSON, paths.WORD_INDEX_JSON,
                )
            self._spine_cache = sp
        return sp

    def _display(self, s: int, a: int) -> tuple[str, int, list[tuple[int, int]]] | None:
        """`(displayed text, chakl→display char shift, token spans)`, or None.

        The shift is what `strip_leading_basmala` removed. `word_index` stores every
        offset against the RAW chakl row, Basmala included (that is deliberate — the
        QLisan fiche slices by those offsets), so a position has to be rebased before
        it means anything in the text this feature emits. Skipping the rebase moves
        every highlight in a Basmala-prefixed verse by the four words of the Basmala.
        """
        cached = self._spans.get((s, a))
        if cached is None:
            chakl = self.chakl.get((s, a))
            if chakl is None:
                return None
            raw = chakl["text"]
            text = strip_leading_basmala(s, a, raw)
            cached = (text, len(raw) - len(text),
                      [m.span() for m in _TOKEN_RE.finditer(text)])
            self._spans[(s, a)] = cached
        return cached

    def _tokens_for_root(self, root: str) -> tuple[dict[tuple[int, int], list[int]],
                                                   set[tuple[int, int]]] | None:
        """Positions of every word of `root` — the ROOT-level fallback.

        Used when a lemma group carries no `word_refs`, i.e. a corpus built before
        Chain A recorded them. It cannot separate two lemmas of one root inside a
        verse (40:81 = آيَاتِهِ + فَأَيَّ), which is exactly why `word_refs` exists.
        """
        root_graph, _word_index = self._spine()
        refs = root_graph.get(root) if root else None
        if refs is None:
            return None
        return self._positions(f"root:{root}", refs)

    def _positions(self, key: str, refs: list[str],
                   forms: list[str] | None = None) -> tuple[
            dict[tuple[int, int], list[int]], set[tuple[int, int]]] | None:
        """`({(surah, ayah): [token index…]}, {verses these words appear in})`.

        `refs` are `s:a:w` word refs; `key` names the cache entry (a root, or a
        root+lemma pair). None when the spine cannot answer at all — the signal to
        fall back to substring matching rather than to conclude "no occurrence".

        The two halves answer different questions, and both are needed: a verse in
        `seen` but absent from the map is one whose words failed to align (fall
        back); a verse in neither is one the word simply is not in (highlight
        nothing). Collapsing them would silently turn one into the other.
        """
        cached = self._root_tokens.get(key)
        if cached is not None:
            return cached
        _root_graph, word_index = self._spine()
        norm_forms = [nf for nf in (_norm_match(f) for f in forms or ()) if nf]
        found: dict[tuple[int, int], list[int]] = {}
        seen: set[tuple[int, int]] = set()
        for ref in refs:
            try:
                s, a, _w = (int(x) for x in ref.split(":"))
            except ValueError:
                logger.warning("VerseLookup: malformed word ref %r, skipping.", ref)
                continue
            disp = self._display(s, a)
            if disp is None:
                continue
            seen.add((s, a))
            entry = word_index.get(ref)
            if not entry or not entry.get("aligned"):
                continue
            text, shift, spans = disp
            # EVERY display token the word's character span overlaps, not just the
            # one its first character falls in. QAC counts a vocative and its noun
            # as ONE word (`يٰأبت`, `يٰأيها`) where the chakl row writes two tokens
            # (`يَا أَبَتِ`, `يَا أَيُّهَا`); anchoring on the start alone highlighted the
            # particle and left the noun bare. A word that is one token overlaps
            # one token, so the ordinary case is untouched — 282 occurrences of
            # 50 342 span more than one.
            lo = entry["chakl_char_start"] - shift
            hi = entry["chakl_char_end"] - shift
            hits = [i for i, (b, e) in enumerate(spans) if b < hi and lo < e]
            hits = _narrow(hits, text, spans, norm_forms)
            if hits:
                bucket = found.setdefault((s, a), [])
                bucket.extend(i for i in hits if i not in bucket)
        for idx in found.values():
            idx.sort()
        cached = (found, seen)
        self._root_tokens[key] = cached
        return cached

    def _indices(self, s: int, a: int, text: str, forms: list[tuple[str, str]],
                 spine: tuple[dict, set] | None) -> list[int]:
        """The tokens to highlight in one verse: aligned positions, else substring."""
        if spine is not None:
            found, seen = spine
            if (s, a) in found:
                return found[(s, a)]
            if (s, a) not in seen:
                return []          # the root is genuinely absent from this verse
        return self._match_indices(text, forms)

    @staticmethod
    def _match_indices(vocalized_text: str, forms: list[tuple[str, str]]) -> list[int]:
        """FALLBACK highlighter: tokens that merely *contain* a matched surface form.

        Used only where `_indices` cannot read a position — a root outside the root
        graph, a word the treebank failed to align, a proper noun (rootless, so the
        graph does not list it). It is a heuristic and a known-lossy one: an
        unanchored substring test lit up every token containing a two-letter form,
        so `أَتَ` → `ات` highlighted `الصَّالِحَاتِ` and `جَنَّاتٍ`. That was 9.0 % of all
        highlighted tokens before positions replaced it on the main path.

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
            ntok = _norm_match(tok)
            if ntok and any(nf in ntok for nf in norm_forms):
                out.append(i)
        return out

    def _word_function(self) -> dict[str, str]:
        """`s:a:w` → the grammatical tool it serves as; absent = carries meaning."""
        wf = getattr(self, "_word_function_cache", None)
        if wf is None:
            try:
                wf = loaders.word_function()
            except loaders.DatasetMissing:
                wf = {}
                logger.warning(
                    "VerseLookup: %s not found — grammatical tools are not set "
                    "apart. Run `python -m ingestion.qac_treebank`.",
                    paths.WORD_FUNCTION_JSON,
                )
            self._word_function_cache = wf
        return wf

    def _lexical_refs(self, lg: dict) -> list[str] | None:
        """A lemma group's word refs, MINUS the ones that serve as a tool.

        Carrying a root is not the same as being an occurrence of its meaning: in
        «يَٰٓأَيُّهَا ٱلنَّاسُ» the segment `أَيُّ` bears ROOT:أيي, yet the word is a calling
        formula and has nothing to do with آية «sign». Those occurrences are
        dropped outright — not listed, not highlighted, not counted — so every
        figure the page reports describes the same filtered set.

        The cost is deliberate and worth stating: كيف keeps 3 of its 83
        occurrences, because 80 of them are interrogative particles. No root is
        emptied entirely.

        None means "no word refs recorded" (a corpus built before Chain A stored
        them); the caller then falls back to the group's own verse list, unfiltered
        — degraded, but never wrong about what it does show.
        """
        refs = lg.get("word_refs")
        if not refs:
            return None
        wf = self._word_function()
        return [r for r in refs if r not in wf]

    @staticmethod
    def _verses_of(refs: list[str]) -> list[str]:
        """The distinct verses of a set of word refs, in recitation order."""
        return sorted({r.rsplit(":", 1)[0] for r in refs},
                      key=lambda v: tuple(int(x) for x in v.split(":")))

    # ── occurrence counting ───────────────────────────────────────────────
    @staticmethod
    def _word_count(ref_groups: list[list[str]]) -> int:
        """Distinct WORDS across the lemma groups actually returned.

        A different question from `total`, which counts ĀYĀT: 40:81 holds two
        words of أيي (`آيَاتِهِ` and `فَأَيَّ`), so it counts once there and twice here
        — أيي is 597 words in 562 āyāt. Neither figure is the sum of the lemma
        cards (353 + 214 = 567), which double-counts the 5 āyāt hosting both
        lemmas; that sum answers no question and is not reported.

        Counted from the groups that are emitted, not from the root graph, so the
        header can only ever describe what the cards below it contain. The two
        sources agree on 1653 of 1654 roots — عون is the exception, at one word —
        and one source cannot drift from the display.

        Deduplicated because ONE word can sit in two roots' groups: QAC writes
        20:94:2 `يبنؤم` as a single word carrying two roots (بني + أمم), so a
        query reaching both must not count it twice.
        """
        return len({ref for refs in ref_groups for ref in refs})

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

    def _verse_row(self, vid: str, forms: list[tuple[str, str]],
                   spine: tuple[dict, set] | None = None) -> dict | None:
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
        # This row bypasses `verse_from_record`, so it applies the strip itself —
        # and applies it BEFORE highlighting, whose output is a list of token
        # positions in the emitted text. Highlighting the raw row and shipping the
        # stripped one would shift every index by the Basmala's four tokens.
        text, _shift, _spans = self._display(s, a)
        return {
            "surah_number": s,
            "surah_name": chakl["surah_name"],
            "aya_number": a,
            "text": text,
            "match_indices": self._indices(s, a, text, forms, spine),
        }

    def _rows_for(self, verse_ids: list[str], forms_found: list[str],
                  spine: tuple[dict, set] | None = None) -> list[dict]:
        """Vocalized rows for a list of verse refs, highlighting `spine`'s words.

        `forms_found` feeds the substring fallback only; pass a `spine` whenever
        one is available, so aligned positions are used instead.
        """
        forms = [(f, _norm_match(f)) for f in forms_found]
        rows = []
        for vid in verse_ids:
            row = self._verse_row(vid, forms, spine)
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
        for stem in clitic_alif_candidates(key):
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
                # A rootless name is absent from the root graph, but Chain A
                # records its word refs all the same — so it highlights by
                # position like everything else, and can be counted.
                refs = pn.get("word_refs") or []
                spine = (self._positions(f"pn:{pn['lemma']}", refs,
                                         pn.get("forms_found")) if refs else None)
                verses = self._rows_for(pn.get("verses", []),
                                        pn.get("forms_found", []), spine)
                return {
                    "word": word,
                    "root": "",
                    "roots": [],
                    "root_found": True,
                    "is_proper_noun": True,
                    "occurrences": self._word_count([refs]),
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
                    "is_proper_noun": False, "occurrences": 0, "total": 0,
                    "lemmas": []}

        lemma_groups: list[dict] = []
        seen_verses: set[str] = set()
        emitted_refs: list[list[str]] = []
        for rk in roots:
            for lg in self._lemma_groups_for_root(rk):
                refs = self._lexical_refs(lg)
                # Lemma-exact positions when Chain A recorded them; the
                # root-level spine otherwise (older corpus), substring last.
                spine = (self._positions(f"{rk}|{lg['lemma']}", refs,
                                         lg.get("forms_found"))
                         if refs else self._tokens_for_root(rk))
                verses = self._rows_for(
                    self._verses_of(refs) if refs is not None else lg.get("verses", []),
                    lg.get("forms_found", []), spine)
                if not verses:
                    continue
                seen_verses.update(
                    f"{r['surah_number']}:{r['aya_number']}" for r in verses
                )
                emitted_refs.append(refs or [])
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
            "occurrences": self._word_count(emitted_refs),
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
