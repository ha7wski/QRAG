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
  - results are grouped by **لفظ** — the WRITTEN form of each occurrence, read
    off the very token the highlighter marks (`_written_form`). Not by lemma:
    آيات، آياتنا، آياته are three ألفاظ of the one lemma آيَة, and «how is this
    word written across the Quran» is the question this page asks. The lemma
    index stays an internal input, for its `word_refs` and `forms_found`.
  - the ONLY new data dependency is the vocalized corpus
    (`quran_data.paths.QURAN_CHAKL_CSV`), the sole source of fully diacritized
    text (the processed corpus `text_ar` has no harakat). It is reached through
    `quran_data.corpus.chakl_by_ref()`, never opened here. `word_prefixes.json`
    is read too, lazily: it says which proclitics come off a لفظ, and exists so
    this path never loads `qac_words.json` (248 MB) to learn them — see
    `_prefixes`.
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quran_data.corpus import chakl_by_ref, strip_leading_basmala  # noqa: E402
from arabic_text import bare, normalize_search  # noqa: E402
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


def _ref_key(ref: str) -> tuple[int, int, int]:
    """A `s:a:w` word ref as a recitation-order sort key."""
    s, a, w = ref.split(":")
    return int(s), int(a), int(w)


def _ref_key_verse(ref: str) -> tuple[int, int]:
    """Recitation order for a `surah:ayah` ref (`_ref_key` wants a word ref)."""
    s, a = ref.split(":")
    return int(s), int(a)


def _block_key(block: dict, refs: list[str]) -> tuple[int, int, int]:
    """A لفظ block's first occurrence, as a recitation-order sort key.

    Falls back to the block's first verse when it carries no refs — the
    substring-highlighted block a corpus without positions still produces, whose
    `refs` list is empty and would make `min()` raise.
    """
    if refs:
        return min(_ref_key(r) for r in refs)
    first = block["verses"][0]
    return first["surah_number"], first["aya_number"], 0


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


# Wasla alef (U+0671). QAC writes the article both `ٱلْ` (1718 words) and `الْ`
# (2633), so a declared prefix is compared with it folded to a plene alef. Only
# the PREFIX side: the vocalized corpus contains `ٱ` in 0 of its 6236 rows, so
# folding the display token too would be a rule nobody could ever check.
_ALEF_WASLA = "ٱ"
_PLENE_ALEF = "ا"


def _written_form(token: str, prefix: str) -> str:
    """The لفظ of one occurrence: the display token as the mushaf writes it,
    minus the proclitics QAC declares for that word.

    `arabic_text.bare()` and nothing else on the display side. It DELETES the
    dagger alef, which is what a written form wants — `مُوسَىٰ` → `موسى`. Folding
    it to a plene alef instead (what `_norm_match` above must do, for a different
    question) yields `موسىا`, a spelling that occurs nowhere, splitting the name's
    136 occurrences under a bogus label. The corpus writes a plene alef wherever
    it means one (`آيَاتِ`), so here the dagger is always a mark.

    No fourth normalizer is added to `arabic_text/`: this composes an existing
    fold locally, the same move `_norm_match` makes one function up and for the
    same reason — a shared fold must not widen to serve one caller. And yes, this
    DISPLAYS what `bare()`'s docstring calls a comparison key: a لفظ is a grouping
    key that is also its own label. Nothing stores it, least of all as a root,
    which is the trap that warning is about.

    `prefix` is the joined PREFIX segment string; stripping the join and stripping
    the segments one at a time agree on all 50 045 displayed occurrences. It is
    removed ONLY when the folded token actually starts with it, and the token is
    left alone otherwise — which happens on 156 of those occurrences (171 counting
    each declared segment separately), correctly every time: 126 are the vocative
    `يٰ` QAC glues onto the noun it calls, a separate display token the caller's
    last-token rule has already left behind, and the rest an interrogative hamza
    or an article that has merged orthographically with the stem and cannot come
    off without re-spelling the word (`أَأَتَّخِذُ`, `آللَّهُ`, `آلْـَٰٔنَ`).
    """
    word = bare(token)
    key = bare(prefix).replace(_ALEF_WASLA, _PLENE_ALEF)
    if key and word.startswith(key):
        return word[len(key):]
    return word


class VerseLookup:
    """Resolve a word to its root(s) and list every verse, vocalized, grouped by
    لفظ — the WRITTEN form of each occurrence (آيات، آياتنا، آياته …), not the
    lemma. The lemma index stays an internal input: it carries the `word_refs`
    and `forms_found` the position highlighter needs, and reaches no response."""

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
        # The proclitics QAC declares per word — what makes a لفظ the word minus
        # its و/ف/ب/ل/ك/س/ٱل. Optional and lazy like the two above; see `_prefixes`.
        self._prefix_cache: dict[str, str] | None = None

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

    def _prefixes(self) -> dict[str, str]:
        """`s:a:w` → the proclitics QAC declares for that word, joined, in order.

        Lazy and optional exactly like the spine, the lemma index and the tool
        map: absent, no prefix is removed, so `بِـَٔايَٰتِنَا` reads as its own لفظ
        instead of joining `آياتنا`. The page still answers.

        This is deliberately NOT `qac_words.json`, which carries the same
        segmentation inside `segments_detail`: that index costs **248 MB**
        resident against `word_index.json`'s 64 MB, and this path holds neither.
        `word_prefixes.json` is the 0.5 MB extract of it that exists for this
        reader — written by the same build run, so it cannot drift from it.
        """
        px = getattr(self, "_prefix_cache", None)
        if px is None:
            try:
                px = loaders.word_prefixes()
            except loaders.DatasetMissing:
                px = {}
                logger.warning(
                    "VerseLookup: %s not found — ألفاظ keep their proclitics. "
                    "Run `python -m ingestion.qac_treebank`.",
                    paths.WORD_PREFIXES_JSON,
                )
            self._prefix_cache = px
        return px

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

    def _root_positions(self, root: str) -> tuple[dict[str, list[int]],
                                                  set[tuple[int, int]]] | None:
        """Per-ref positions of every word of `root` — the ROOT-level fallback.

        Used when a lemma group carries no `word_refs`, i.e. a corpus built before
        Chain A recorded them. It cannot separate two lemmas of one root inside a
        verse (40:81 = آيَاتِهِ + فَأَيَّ), which is exactly why `word_refs` exists.
        """
        root_graph, _word_index = self._spine()
        refs = root_graph.get(root) if root else None
        if refs is None:
            return None
        return self._positions(f"root:{root}", refs)

    def _tokens_for_root(self, root: str) -> tuple[dict[tuple[int, int], list[int]],
                                                   set[tuple[int, int]]] | None:
        """The same thing collapsed per verse — a spine `_indices` can consume."""
        pos = self._root_positions(root)
        return None if pos is None else (self._per_verse(pos[0]), pos[1])

    def _positions(self, key: str, refs: list[str],
                   forms: list[str] | None = None) -> tuple[
            dict[str, list[int]], set[tuple[int, int]]] | None:
        """`({word ref: [token index…]}, {verses these words appear in})`.

        `refs` are `s:a:w` word refs; `key` names the cache entry (a root, or a
        root+lemma pair). None when the spine cannot answer at all — the signal to
        fall back to substring matching rather than to conclude "no occurrence".

        Indices are kept PER REF, not merged per verse. The لفظ of an occurrence
        is read off the very token this loop resolves, so collapsing here would
        throw away the only record of which word produced which index — and one
        verse can hold two ألفاظ of one root, each belonging to a different block.
        `_per_verse()` does the collapse where a caller still wants it, over the
        subset of refs it is highlighting.

        The two halves answer different questions, and both are needed: a verse in
        `seen` but absent from the map is one whose words failed to align (fall
        back); a verse in neither is one the word simply is not in (highlight
        nothing). Collapsing them would silently turn one into the other.
        """
        # Namespaced so an entry can never be read back under the per-VERSE shape
        # this method used to return; the callers' own keys stay theirs to choose.
        key = f"byref:{key}"
        cached = self._root_tokens.get(key)
        if cached is not None:
            return cached
        _root_graph, word_index = self._spine()
        norm_forms = [nf for nf in (_norm_match(f) for f in forms or ()) if nf]
        found: dict[str, list[int]] = {}
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
                # One ref appears once in `refs`, but a defensive merge costs
                # nothing and keeps the map a function of the ref, not of order.
                bucket = found.setdefault(ref, [])
                bucket.extend(i for i in hits if i not in bucket)
        for idx in found.values():
            idx.sort()
        cached = (found, seen)
        self._root_tokens[key] = cached
        return cached

    @staticmethod
    def _per_verse(by_ref: dict[str, list[int]],
                   refs: list[str] | None = None) -> dict[tuple[int, int], list[int]]:
        """Collapse per-ref token indices into the per-verse lists a row marks.

        `refs` restricts the collapse to ONE لفظ's occurrences, which is what makes
        a verse holding two ألفاظ mark a different word in each block. Passing
        None collapses everything, the whole-root behaviour `_tokens_for_root`
        needs for its fallback spine.
        """
        out: dict[tuple[int, int], list[int]] = {}
        for ref in (by_ref if refs is None else refs):
            hits = by_ref.get(ref)
            if not hits:
                continue
            s, a, _w = (int(x) for x in ref.split(":"))
            bucket = out.setdefault((s, a), [])
            bucket.extend(i for i in hits if i not in bucket)
        for idx in out.values():
            idx.sort()
        return out

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
        """Distinct WORDS across the ألفاظ blocks actually returned.

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

    # ── lemma groups: an internal input, never a response shape ───────────
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

    # ── لفظ grouping: one block per written form ──────────────────────────
    def _form_blocks(self, rk: str, groups: list[dict],
                     ns: str = "lemma") -> tuple[list[dict], list[list[str]]]:
        """The ألفاظ of one root: `([block…], [that block's word refs…])`.

        The lemma groups are pooled first and re-split by written form, because a
        لفظ is a property of the WORD, not of the lemma it was filed under: `آيَاتِهِ`
        is `آياته` whichever sense QAC assigned it. They are still read one at a
        time, since `forms_found` is what narrows a multi-token span to the token
        that actually carries the root (`يَا أَبَتِ` → `أَبَتِ`), and that list is
        lemma-exact.

        `ns` namespaces the position cache so a proper noun (root `""`) cannot
        collide with a root's entry.
        """
        prefixes = self._prefixes()
        hits_by_ref: dict[str, list[int]] = {}
        buckets: dict[str, list[str]] = {}      # لفظ → its word refs
        seen: set[tuple[int, int]] = set()
        surfaces: list[str] = []                # every surface form of the root
        # (group, its refs the spine could not answer for) — None = the whole group.
        unreadable: list[tuple[dict, list[str] | None]] = []

        for lg in groups:
            surfaces.extend(lg.get("forms_found") or [])
            refs = self._lexical_refs(lg)
            if refs is None:
                # No `word_refs` — a corpus built before Chain A recorded them.
                # The root's own occurrences stand in, which cannot tell two
                # lemmas of one root apart (40:81 = آيَاتِهِ + فَأَيَّ): the degradation
                # the highlighter already took, now visible in the grouping too.
                pos = self._root_positions(rk)
                wf = self._word_function()
                refs = [r for r in (pos[0] if pos else ()) if r not in wf]
            elif not refs:
                # EMPTY is not the same as None: every occurrence of this lemma
                # serves as a grammatical tool (أَيّ is 215 of أيي's 597 words, all
                # of them), so the lemma contributes nothing. Reading it as "no
                # refs recorded" would re-admit the whole root through the
                # fallback above, tools included.
                continue
            else:
                pos = self._positions(f"{ns}:{rk}|{lg['lemma']}", refs,
                                      lg.get("forms_found"))
            if pos is None or not refs:
                # Nothing positional to read at all: keep the group as ONE block
                # labelled with its bare lemma and highlighted by substring, which
                # is what this feature did before positions existed. A لفظ cannot
                # be derived without knowing which token was marked, and dropping
                # the occurrences instead would hide verses that do contain the root.
                unreadable.append((lg, None))
                continue
            by_ref, group_seen = pos
            seen |= group_seen
            missed: list[str] = []
            for ref in refs:
                marks = by_ref.get(ref)
                lafz = self._lafz(ref, marks, prefixes) if marks else None
                if lafz is None:
                    missed.append(ref)       # unaligned word, or no display row
                    continue
                hits_by_ref[ref] = marks
                buckets.setdefault(lafz, []).append(ref)
            if missed:
                unreadable.append((lg, missed))

        blocks: list[tuple[tuple[int, int, int], dict, list[str]]] = []
        for form, block_refs in buckets.items():
            # `_per_verse` is restricted to THIS لفظ's refs, so a verse holding two
            # ألفاظ marks a different word in each block it appears in.
            found = self._per_verse(hits_by_ref, block_refs)
            verses = self._rows_for(self._verses_of(block_refs), surfaces,
                                    (found, seen))
            if not verses:
                continue
            blocks.append((
                min(_ref_key(r) for r in block_refs),
                {"root": rk, "form": form, "count": len(verses),
                 "occurrences": len(set(block_refs)), "verses": verses},
                block_refs,
            ))
        for lg, missed in unreadable:
            listed = self._verses_of(missed) if missed else lg.get("verses", [])
            verses = self._rows_for(listed, lg.get("forms_found", []), None)
            if not verses:
                continue
            blocks.append((
                (verses[0]["surah_number"], verses[0]["aya_number"], 0),
                {"root": rk, "form": bare(lg.get("lemma_display") or lg["lemma"]),
                 "count": len(verses), "occurrences": len(missed or ()),
                 "verses": verses},
                list(missed or ()),
            ))

        # Recitation position of each لفظ's FIRST occurrence. A canonical order,
        # not the displayed one: the ordering control is a client concern, exactly
        # as it already is for the sūra cards.
        blocks.sort(key=lambda b: b[0])
        return [b[1] for b in blocks], [b[2] for b in blocks]

    def _lafz(self, ref: str, marks: list[int],
              prefixes: dict[str, str]) -> str | None:
        """The written form of the occurrence `ref` marks, or None if unreadable.

        The LAST marked token is the one that carries it: QAC merges a proclitic
        particle into the word it governs (`يحسرتى` for the two display tokens
        `يَا حَسْرَتَا`), and Arabic writes the particle first, so the lexical head
        comes last. Only one occurrence of 50 045 still marks two tokens after
        `_narrow`, and it is exactly that shape.
        """
        try:
            s, a, _w = (int(x) for x in ref.split(":"))
        except ValueError:                      # already logged by `_positions`
            return None
        disp = self._display(s, a)
        if disp is None:
            return None
        text, _shift, spans = disp
        start, end = spans[marks[-1]]
        return _written_form(text[start:end], prefixes.get(ref, "")) or None

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
        """Return the full Verse Lookup result for `word`, grouped by لفظ.

        The word resolves to root(s); each root's occurrences are split by the
        WRITTEN form they take (أيي → آيات، آياتنا، آيته …), one block per form,
        and each block marks only its own occurrences — a verse holding two
        ألفاظ of the root appears in both, marking a different word each time.

        When the word has no QAC root it may still be a proper noun (لوط, موسى …),
        which QAC leaves rootless; those resolve via the proper-noun index, are
        grouped by لفظ the same way, and carry the vocalized name out separately
        in `proper_noun_display` — the root bar's only source for it."""
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
                # position like everything else, and can be counted. It is passed
                # as a single group with an empty root: its ألفاظ (لوط / لوطا) are
                # derived exactly as a root's are.
                forms, refs = self._form_blocks("", [pn], ns="pn")
                return {
                    "word": word,
                    "root": "",
                    "roots": [],
                    "root_found": True,
                    "is_proper_noun": True,
                    "proper_noun_display": pn.get("lemma_display") or pn["lemma"],
                    "occurrences": self._word_count(refs),
                    "total": self._distinct_verses(forms),
                    "forms": forms,
                }
            roots = self.lex.resolve_roots_lenient(word)  # clitic/alif retries

        if not roots:
            return {"word": word, "root": "", "roots": [], "root_found": False,
                    "is_proper_noun": False, "proper_noun_display": "",
                    "occurrences": 0, "total": 0, "forms": []}

        forms: list[dict] = []
        emitted_refs: list[list[str]] = []
        for rk in roots:
            blocks, refs = self._form_blocks(rk, self._lemma_groups_for_root(rk))
            forms.extend(blocks)
            emitted_refs.extend(refs)

        # `_form_blocks` orders by first occurrence WITHIN one root; a homograph
        # query concatenates several, and the concatenation is not recitation
        # order — كل reaches أكل / كلل / كيل and put مأكول (105:5) ahead of كلما
        # (2:20). The order has to be right ON THE WIRE, not merely intended:
        # the client breaks its count ties by the order it receives, so a wrong
        # one here does not surface as a wrong order, it surfaces as an arbitrary
        # one. Only ever reorders a multi-root result; within one root the list
        # is already sorted and this would be a no-op.
        if len(roots) > 1:
            order = sorted(range(len(forms)),
                           key=lambda i: _block_key(forms[i], emitted_refs[i]))
            forms = [forms[i] for i in order]
            emitted_refs = [emitted_refs[i] for i in order]

        return {
            "word": word,
            "root": " / ".join(roots),
            "roots": roots,
            "root_found": True,
            "is_proper_noun": False,
            "proper_noun_display": "",
            # Both are DISTINCT counts over the blocks actually emitted, unchanged
            # in meaning: مواضع counts words, آيات counts āyāt. They are not the
            # sums of the blocks — 19 of أيي's 353 āyāt hold two ألفاظ, so the
            # blocks list 373 rows for 353 āyāt, and a sum would count those twice.
            "occurrences": self._word_count(emitted_refs),
            "total": self._distinct_verses(forms),
            "forms": forms,
        }

    # ── the same ألفاظ, without the verses ────────────────────────────────
    def root_forms(self, root: str) -> dict:
        """The distinct ألفاظ of ONE root, with the figures «الكلمة في الآيات» shows.

        «تحليل اللسان» prints the same المواضع block, and it must not compute it a
        second way. `morphology.json`'s `forms_found` — what it used — is a list of
        VOCALIZED surfaces, so `رَحْمَةً` / `رَحْمَةٍ` / `رَحْمَةُ` are three entries of one
        written form: the page announced 43 ألفاظ for رحم where this one counts 31,
        and printed the same word four times in a row. The deeper divergence is not
        the duplicates: `forms_found` is unfiltered, so an occurrence serving as a
        grammatical tool (`word_function.json`) stays in its count and is out of the
        لفظ grouping — two pages disagreeing on the same root, each internally
        consistent.

        `root` is a CANONICAL QAC root key, the spelling `resolve_roots` / `_ladder`
        return; this is the per-root half of `lookup` verbatim, verse rows built and
        then dropped. Built, not skipped: `_form_blocks` drops a block whose verses
        would not render, so a cheaper path would list ألفاظ «دراسة الآية» does not
        show — the one thing this method exists to prevent. ~10 ms on رحم.
        """
        if not root:
            return {"root": "", "forms": [], "words": 0, "ayat": 0, "verse_ids": []}
        blocks, refs = self._form_blocks(root, self._lemma_groups_for_root(root))
        # Read off the emitted rows, not off `refs`: `ayat` then equals
        # `len(verse_ids)` by construction, and both describe exactly the blocks
        # «دراسة الآية» would display for this root.
        verse_ids = sorted(
            {f"{r['surah_number']}:{r['aya_number']}"
             for b in blocks for r in b["verses"]},
            key=_ref_key_verse,
        )
        return {
            "root": root,
            "forms": [b["form"] for b in blocks],
            "words": self._word_count(refs),
            "ayat": len(verse_ids),
            "verse_ids": verse_ids,
        }

    @staticmethod
    def _distinct_verses(blocks: list[dict]) -> int:
        """Distinct āyāt across the emitted blocks (a verse may sit in several)."""
        return len({(r["surah_number"], r["aya_number"])
                    for b in blocks for r in b["verses"]})


if __name__ == "__main__":
    vl = VerseLookup()
    for w in ["السماوات", "صبر", "زقزقة"]:
        r = vl.lookup(w)
        print(f"{w} → root={r['root']!r} found={r['root_found']} total={r['total']} "
              f"forms={len(r['forms'])}")
        for g in r["forms"][:3]:
            print(f"    لفظ {g['form']!r} ({g['root']}): {g['count']} verses, "
                  f"{g['occurrences']} occurrences — e.g. "
                  f"{g['verses'][0]['surah_number']}:{g['verses'][0]['aya_number']}")
