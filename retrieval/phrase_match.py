"""
phrase_match.py — model-free lexical scoring of verses against a SHORT query, for
the «المتقاربات من عبارة» tab (`GET /search`).

Why it exists. For a short query the root pipeline loses what the query is about:
«و من الناس» kept one content root (أنس), which 317 verses share at an identical
IDF score, so the 20 handed to the reranker were simply the first 20 in mushaf
order — and the function words that carry the construction («ومن الناس من…») had
been thrown away. 10 of the 12 verses that write «ومن الناس» never reached the
pool. This module scores EVERY verse that could match, before any model:

  * coverage — per content word of the query, the best level at which the verse
    holds it, IDF-weighted, ORDER-INVARIANT (a bigram matches in either order):
        same written word 1.0 · same word once proclitics are peeled 0.9
        · same lemma 0.7 · same root only 0.4
    so الناس / للناس outrank الإنسان (lemma إنسان, root أنس) which outranks آنست.
  * sequence — the longest run of query words (function words INCLUDED) found
    CONTIGUOUS and in order in the verse, each word weighted 1.0 exact / 0.9 once
    peeled, divided by the query length. A function word therefore only counts
    next to the words around it, never on its own («من» is in 2 000 verses).

  lexical = 0.6·coverage + 0.4·sequence   (sequence alone when the query has no
  content word, e.g. «إن الذين»).

Lemmas come from QAC: each written word of an āya is paired by position with its
QAC word (`ingestion.qac_morphology.aligned_tokens`, the same pairing that builds
`word_to_roots`) and given that word's lemma from `lemma_index.json`. Built once,
lazily, on the first short query (~1 s, a few tens of MB).
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arabic_text import normalize_search  # noqa: E402
from ingestion.qac_morphology import aligned_tokens  # noqa: E402
from quran_data import loaders, qac  # noqa: E402

# Match levels (see module docstring).
EXACT, PEELED, LEMMA, ROOT = 1.0, 0.9, 0.7, 0.4
W_COVERAGE, W_SEQUENCE = 0.6, 0.4

# Conjunctions, then one preposition/article layer. The article is peeled only
# when ≥ 3 letters remain, so الله never becomes the preposition له.
_CONJ = ("و", "ف")
_PROCLITICS = ("وال", "فال", "بال", "كال", "لل", "ال", "ب", "ك", "ل")


def stems(tok: str) -> frozenset[str]:
    """The token and its proclitic-peeled forms: وللناس → {وللناس, للناس, ناس}."""
    out = {tok}
    heads = [tok]
    for c in _CONJ:
        if tok.startswith(c) and len(tok) - len(c) >= 2:
            heads.append(tok[len(c):])
    for h in heads:
        out.add(h)
        for p in _PROCLITICS:
            rest = h[len(p):]
            if h.startswith(p) and len(rest) >= (3 if "ال" in p or p == "لل" else 2):
                out.add(rest)
    return frozenset(out)


def query_units(query: str) -> list[str]:
    """Search-normalized query words; a lone و / ف is joined to the next word,
    so «و من» and «ومن» are the same query."""
    toks = normalize_search(query).split()
    units: list[str] = []
    i = 0
    while i < len(toks):
        if toks[i] in _CONJ and i + 1 < len(toks):
            units.append(toks[i] + toks[i + 1])
            i += 2
        else:
            units.append(toks[i])
            i += 1
    return units


class _Word:
    __slots__ = ("norm", "stems", "tool", "lemmas", "roots", "idf")

    def __init__(self, norm, stems_, tool, lemmas, roots, idf):
        self.norm, self.stems, self.tool = norm, stems_, tool
        self.lemmas, self.roots, self.idf = lemmas, roots, idf


class PhraseMatcher:
    def __init__(self, similar):
        # `similar` is the shared SimilarVerses: its stoplist and root resolver
        # decide what a function word is, so both paths agree on it.
        self.similar = similar
        self.lex = similar.lex
        self.N = similar.N
        self._built = False

    # ── index ───────────────────────────────────────────────────────────────
    def _build(self) -> None:
        ref_lemma: dict[str, tuple[str, str]] = {}
        for root, groups in loaders.lemma_index().items():
            for g in groups:
                for ref in g["word_refs"]:
                    ref_lemma[ref] = (root, g["lemma"])

        ayah_words = qac.ayah_words()
        self.tokens: dict[str, list[tuple[str, frozenset[str]]]] = {}
        self.lemmas: dict[str, frozenset[tuple[str, str]]] = {}
        self.roots: dict[str, frozenset[str]] = {}
        self.by_stem: dict[str, set[str]] = defaultdict(set)
        self.by_lemma: dict[tuple[str, str], set[str]] = defaultdict(set)
        self.stem_lemmas: dict[str, set[tuple[str, str]]] = defaultdict(set)

        for vid, v in self.lex.verses_by_id.items():
            s, a = v["surah_number"], v["ayah_number"]
            plain = [t for t in v["text_ar"].split() if normalize_search(t)]
            toks = [(normalize_search(t), stems(normalize_search(t))) for t in plain]
            self.tokens[vid] = toks
            for _, st in toks:
                for x in st:
                    self.by_stem[x].add(vid)
            lems: set[tuple[str, str]] = set()
            paired = aligned_tokens(v["text_ar"], len(ayah_words.get((s, a), ())))
            for w, tok in enumerate(paired or (), start=1):
                rl = ref_lemma.get(f"{s}:{a}:{w}")
                if rl is None:
                    continue
                lems.add(rl)
                self.by_lemma[rl].add(vid)
                for x in stems(normalize_search(tok)):
                    self.stem_lemmas[x].add(rl)
            if paired is None:     # 7 āyāt QAC cannot pair: lemmas from refs alone
                prefix = f"{s}:{a}:"
                lems |= {rl for ref, rl in ref_lemma.items() if ref.startswith(prefix)}
            self.lemmas[vid] = frozenset(lems)
            self.roots[vid] = frozenset(v.get("roots") or ())
        self._built = True

    # ── query ───────────────────────────────────────────────────────────────
    def _is_tool(self, unit: str) -> bool:
        if self.similar._is_stopword(unit):
            return True
        return any(unit.startswith(c) and self.similar._is_stopword(unit[len(c):])
                   for c in _CONJ)

    def analyse(self, query: str) -> list[_Word]:
        if not self._built:
            self._build()
        words: list[_Word] = []
        for u in query_units(query):
            st = stems(u)
            tool = self._is_tool(u)
            lemmas: set[tuple[str, str]] = set()
            roots: set[str] = set()
            if not tool:
                for x in st:
                    lemmas |= self.stem_lemmas.get(x, set())
                roots = {r for r, _ in lemmas} | set(self.similar._resolve_token(u))
            df = len(set().union(*(self.by_stem.get(x, set()) for x in st)))
            if not df and roots:
                df = min(len((self.lex.index.get(r) or {}).get("verses") or ()) or self.N
                         for r in roots)
            words.append(_Word(u, st, tool, frozenset(lemmas), frozenset(roots),
                               math.log(self.N / max(df, 1))))
        return words

    def candidates(self, words: list[_Word]) -> set[str]:
        """Every verse that holds a query word at some level; for a query made of
        function words only, the verses holding its first word."""
        out: set[str] = set()
        content = [w for w in words if not w.tool]
        for w in content:
            for x in w.stems:
                out |= self.by_stem.get(x, set())
            for rl in w.lemmas:
                out |= self.by_lemma.get(rl, set())
            for r in w.roots:
                out |= set((self.lex.index.get(r) or {}).get("verses") or ())
        if not content and words:
            for x in words[0].stems:
                out |= self.by_stem.get(x, set())
        return out

    # ── scoring ─────────────────────────────────────────────────────────────
    @staticmethod
    def _surface(w: _Word, norm: str, st: frozenset[str]) -> float:
        if norm == w.norm:
            return EXACT
        return PEELED if st & w.stems else 0.0

    def score(self, vid: str, words: list[_Word]) -> dict:
        toks = self.tokens.get(vid, [])
        content = [w for w in words if not w.tool]

        cov = 0.0
        if content:
            total = got = 0.0
            for w in content:
                level = max((self._surface(w, n, st) for n, st in toks), default=0.0)
                if level < LEMMA and w.lemmas & self.lemmas.get(vid, frozenset()):
                    level = LEMMA
                if level < ROOT and w.roots & self.roots.get(vid, frozenset()):
                    level = ROOT
                total += w.idf
                got += w.idf * level
            cov = got / total if total else 0.0

        # Longest contiguous in-order run, weighted (longest common substring DP).
        best = 0.0
        prev = [0.0] * (len(toks) + 1)
        for w in words:
            cur = [0.0] * (len(toks) + 1)
            for j, (n, st) in enumerate(toks, start=1):
                m = self._surface(w, n, st)
                if m:
                    cur[j] = prev[j - 1] + m
                    if cur[j] > best:
                        best = cur[j]
            prev = cur
        seq = best / len(words) if words else 0.0

        lex = W_COVERAGE * cov + W_SEQUENCE * seq if content else seq
        return {"lex": round(lex, 4), "cov": round(cov, 4), "seq": round(seq, 4)}


if __name__ == "__main__":
    import time

    from retrieval.lexical_retriever import LexicalRetriever
    from retrieval.similar_verses import SimilarVerses

    pm = PhraseMatcher(SimilarVerses(LexicalRetriever()))
    for q in ["و من الناس", "الصيحة فأخذتهم", "إن الذين كفروا"]:
        t = time.perf_counter()
        ws = pm.analyse(q)
        cands = pm.candidates(ws)
        ranked = sorted(cands, key=lambda v: -pm.score(v, ws)["lex"])
        print(f"{q!r}: {len(cands)} candidates, {1000 * (time.perf_counter() - t):.0f} ms")
        for v in ranked[:14]:
            print("   ", v, pm.score(v, ws))
