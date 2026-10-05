#!/usr/bin/env python3
"""
build_quran_passages.py — the offline shared-passage build.

Answers, once and for every pair of verses of DIFFERENT surahs, «does a passage
of this verse's wording come back in that one?» and writes the answer to
`data/derived/quran_passages.json`, which `GET /quran-passages/*` serves. The
design is `openspec/changes/add-shared-passages/design.md`; every value below
was frozen there (D1–D6) before the gold set existed and before this build ran
on the corpus — decisions to record there, never tuning knobs:

  * D1 — one token per QAC word: the `LEM:` of the word's STEM segment (a
    segment carrying neither `PREF` nor `SUFF`), else the word's surface folded
    by `arabic_text.bare()`. A token is CONTENT when the word carries `ROOT:`.
  * D2 — Smith–Waterman over the two token sequences, match +2 (amended), mismatch −1,
    gap −1, floored at 0; best cell = highest score, ties → smallest end in A,
    then in B; traced back diagonal first, then up, then left.
  * D3 — accepted iff `k ≥ L_MIN`, `k ≥ DENSITY × the longer aligned span` and
    ≥ `CONTENT_MIN` matched content tokens. One passage per pair.
  * D4 — only pairs whose token MULTISETS share ≥ `L_MIN` tokens are aligned
    (`k` matched positions are `k` equal tokens, so nothing else can pass),
    computed exactly with sparse count-threshold indicator products.
  * D5 — the file layout, schema 1, byte-identical across builds.

Model-free and Qdrant-free: it may run with the backend up.

    python scripts/build_quran_passages.py              # full build
    python scripts/build_quran_passages.py --no-gold    # without the local-only gold set
    python scripts/build_quran_passages.py --jobs 4     # alignment worker processes
    python scripts/build_quran_passages.py --surahs 28,36   # report only, write nothing

Three points D1/D2 leave open, settled here and recorded in the header:

  * A word with SEVERAL stem segments (563 words: «مِمَّا» = مِن + ما, «إِنَّمَا»)
    keeps one token per word: its stem lemmas joined by `+`, in segment order.
  * The scores are match +2, mismatch −1, gap −1 (design D2, amended before any
    gold measurement): with unit scores «جَاءَ» (+1) then the gap of the displaced
    «رَجُل» (−1) sum to 0 and the standard traceback cuts 28:20/36:20 to 5 words —
    the case D2 names. The traceback is the standard one: it stops at a zero.
  * A matched position counts as content when the words on BOTH sides carry a
    root; `roots` is the sorted union of both sides' canonical roots there.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator, NamedTuple, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arabic_text import bare  # noqa: E402
from quran_data import loaders, paths, qac  # noqa: E402

SCHEMA = loaders.QURAN_PASSAGES_SCHEMA
SCOPE = "cross-surah"
# Frozen in openspec/changes/add-shared-passages/design.md (D2, D3).
MATCH, MISMATCH, GAP = 2, -1, -1
L_MIN = 6
DENSITY = 0.75
CONTENT_MIN = 3
TOKEN_RULE = ("one token per QAC word: the LEM of its stem segment(s) (neither PREF nor "
              "SUFF), '+'-joined in segment order; a word with none takes bare(surface)")
CONTENT_RULE = "the word carries a ROOT feature; a matched position counts when both words do"
TRACEBACK = "diagonal, then up, then left; stops at a zero cell (standard Smith-Waterman)"
CANDIDATES = "token multisets share >= l_min tokens (exact, sparse threshold products)"
GOLD_JSON = ROOT / "tests" / "eval" / "quran_passages_gold.json"
REBUILD = "python scripts/build_quran_passages.py"


# ═══════════════════════════════════════════════════════════════════════════
#  Pure functions — importable by tests, no disk
# ═══════════════════════════════════════════════════════════════════════════

class Word(NamedTuple):
    """One QAC word as this build sees it (D1)."""

    token: str
    content: bool
    root: str | None          # the QAC `ROOT:` as written, None for a rootless word


def _features(rec) -> list[str]:
    return rec.features.split("|")


def word_of(segments: Sequence) -> Word:
    """D1: the word's token, its content flag and its raw root, from its segments.

    `segments` are `quran_data.qac.Record`s of ONE word, in segment order.
    """
    lemmas: list[str] = []
    root = None
    for seg in segments:
        feats = _features(seg)
        for f in feats:
            if f.startswith("ROOT:") and root is None:
                root = f[5:].strip() or None
        if "PREF" in feats or "SUFF" in feats:
            continue
        lemmas.extend(f[4:] for f in feats if f.startswith("LEM:") and f[4:])
    token = "+".join(lemmas) if lemmas else bare("".join(s.form for s in segments))
    return Word(token, root is not None, root)


class Alignment(NamedTuple):
    """The best local alignment of A against B (D2), 1-based inclusive spans."""

    score: int
    i1: int
    i2: int
    j1: int
    j2: int
    matches: tuple[tuple[int, int], ...]   # (i, j) of every matched position, ascending

    @property
    def k(self) -> int:
        return len(self.matches)


def smith_waterman(a: Sequence, b: Sequence) -> Alignment | None:
    """D2: Smith–Waterman of `a` against `b`, or None when no cell scores above 0.

    Scores match +2, mismatch −1, gap −1, floored at 0. The best cell is the
    first highest score in row-major order — smallest end in A, then in B. The
    traceback prefers the diagonal, then up (a word of A against a gap), then
    left, and stops at a zero cell, as standard. A cell above 0 whose diagonal
    predecessor is 0 can only be a match, so the alignment starts on a match.
    """
    n, m = len(a), len(b)
    H = [[0] * (m + 1) for _ in range(n + 1)]
    best, bi, bj = 0, 0, 0
    for i in range(1, n + 1):
        ai, prev, row = a[i - 1], H[i - 1], H[i]
        for j in range(1, m + 1):
            v = prev[j - 1] + (MATCH if ai == b[j - 1] else MISMATCH)
            u = prev[j] + GAP
            if u > v:
                v = u
            le = row[j - 1] + GAP
            if le > v:
                v = le
            if v < 0:
                v = 0
            row[j] = v
            if v > best:
                best, bi, bj = v, i, j
    if best == 0:
        return None
    i, j = bi, bj
    i1, j1 = bi, bj
    matches: list[tuple[int, int]] = []
    while i > 0 and j > 0 and H[i][j] > 0:
        h = H[i][j]
        same = a[i - 1] == b[j - 1]
        if H[i - 1][j - 1] + (MATCH if same else MISMATCH) == h:
            if same:
                matches.append((i, j))
            i1, j1 = i, j
            i, j = i - 1, j - 1
        elif H[i - 1][j] + GAP == h:
            i1 = i
            i -= 1
        elif H[i][j - 1] + GAP == h:
            j1 = j
            j -= 1
        else:
            break                       # only the floor explains this cell
    matches.reverse()
    return Alignment(best, i1, bi, j1, bj, tuple(matches))


def rejection(k: int, span_a: int, span_b: int, content: int) -> str | None:
    """D3: the first rule a candidate fails — `l_min`, `density`, `content_min` — or None."""
    if k < L_MIN:
        return "l_min"
    if k < DENSITY * max(span_a, span_b):
        return "density"
    if content < CONTENT_MIN:
        return "content_min"
    return None


def common_tokens(a: Iterable, b: Iterable) -> int:
    """`Σ_c min(count_A(c), count_B(c))` — the scalar reference of the D4 bound."""
    ca, cb = Counter(a), Counter(b)
    return sum(min(n, cb[t]) for t, n in ca.items() if t in cb)


def candidate_pairs(seqs: Sequence[Sequence[int]], surah_of: Sequence[int],
                    l_min: int = L_MIN) -> list[tuple[int, int]]:
    """D4: every `(i, j)`, `i < j`, of different surahs sharing ≥ `l_min` tokens.

    `seqs` are interned token sequences (ints ≥ 0). The overlap of two multisets
    is `Σ_t Σ_c [count_A(c) ≥ t][count_B(c) ≥ t]`, so it is the sum, over the
    count thresholds t, of the products `I_t · I_tᵀ` of the 0/1 matrices «verse
    holds token c at least t times». Exact integer arithmetic; returned sorted.
    """
    import numpy as np
    import scipy.sparse as sp

    n = len(seqs)
    if n < 2:
        return []
    counts = [Counter(s) for s in seqs]
    vocab = 1 + max((t for s in seqs for t in s), default=0)
    top = max((max(c.values()) for c in counts if c), default=0)
    total = sp.csr_matrix((n, n), dtype=np.int64)
    for t in range(1, top + 1):
        rows, cols = [], []
        for i, c in enumerate(counts):
            for tok, cnt in c.items():
                if cnt >= t:
                    rows.append(i)
                    cols.append(tok)
        ind = sp.csr_matrix((np.ones(len(rows), dtype=np.int64), (rows, cols)),
                            shape=(n, vocab))
        total = total + ind @ ind.T
    upper = sp.triu(total, k=1).tocoo()
    surah = np.asarray(surah_of)
    keep = (upper.data >= l_min) & (surah[upper.row] != surah[upper.col])
    return sorted(zip(upper.row[keep].tolist(), upper.col[keep].tolist()))


# ═══════════════════════════════════════════════════════════════════════════
#  The corpus
# ═══════════════════════════════════════════════════════════════════════════

def qac_records() -> Iterator:
    """The QAC segments — one seam, so a test can cut the population down."""
    return qac.records()


def ref_str(ref: tuple[int, int]) -> str:
    return f"{ref[0]}:{ref[1]}"


class Corpus:
    """Every verse in (surah, ayah) order: its words (D1), interned tokens, roots."""

    def __init__(self, records: Iterable | None = None, resolved: dict | None = None):
        by_word: dict[tuple[int, int, int], list] = defaultdict(list)
        for rec in (qac_records() if records is None else records):
            by_word[(rec.surah, rec.ayah, rec.word)].append(rec)
        verses: dict[tuple[int, int], dict[int, Word]] = defaultdict(dict)
        for (s, a, w), segs in by_word.items():
            verses[(s, a)][w] = word_of(sorted(segs, key=lambda r: r.segment))
        self.refs = sorted(verses)
        self.index = {r: i for i, r in enumerate(self.refs)}
        self.surah_of = [r[0] for r in self.refs]
        self.words: list[list[Word]] = []
        for r in self.refs:
            ws = verses[r]
            if sorted(ws) != list(range(1, len(ws) + 1)):
                raise ValueError(f"{ref_str(r)}: QAC word numbers are not 1..{len(ws)}")
            self.words.append([ws[w] for w in sorted(ws)])
        vocab: dict[str, int] = {}
        self.seqs = [tuple(vocab.setdefault(w.token, len(vocab)) for w in ws)
                     for ws in self.words]
        self.content = [tuple(w.content for w in ws) for ws in self.words]
        resolved = loaders.roots_resolved() if resolved is None else resolved
        self.roots: list[tuple[str | None, ...]] = []
        for r, ws in zip(self.refs, self.words):
            self.roots.append(tuple(
                ((resolved.get(f"{r[0]}:{r[1]}:{n}") or {}).get("primary") or w.root)
                if w.content else None
                for n, w in enumerate(ws, start=1)))

    def judge(self, i: int, j: int, al: Alignment | None) -> tuple[str | None, dict | None]:
        """`(rejection, passage)` for the aligned pair `(i, j)`, `i` in the lower surah."""
        if al is None:
            return "l_min", None
        content = [(p, q) for p, q in al.matches
                   if self.content[i][p - 1] and self.content[j][q - 1]]
        why = rejection(al.k, al.i2 - al.i1 + 1, al.j2 - al.j1 + 1, len(content))
        if why:
            return why, None
        roots = sorted({r for p, q in content
                        for r in (self.roots[i][p - 1], self.roots[j][q - 1]) if r})
        return None, {"a": ref_str(self.refs[i]), "b": ref_str(self.refs[j]),
                      "wa": [al.i1, al.i2], "wb": [al.j1, al.j2], "k": al.k, "roots": roots}


# ═══════════════════════════════════════════════════════════════════════════
#  The alignment stage — multiprocessing, independent of the split
# ═══════════════════════════════════════════════════════════════════════════

_SEQS: Sequence[Sequence[int]] | None = None


def _init_worker(seqs) -> None:
    global _SEQS
    _SEQS = seqs


def _align_chunk(chunk: list[tuple[int, int]]) -> list[tuple[int, int, Alignment | None]]:
    return [(i, j, smith_waterman(_SEQS[i], _SEQS[j])) for i, j in chunk]


def align_stage(seqs, pairs: list[tuple[int, int]], jobs: int, chunk: int = 2000
                ) -> dict[tuple[int, int], Alignment | None]:
    """`{(i, j): best alignment}` for every candidate; the result does not depend on `jobs`."""
    chunks = [pairs[n:n + chunk] for n in range(0, len(pairs), chunk)]
    out: dict[tuple[int, int], Alignment | None] = {}
    if jobs <= 1 or len(chunks) <= 1:
        _init_worker(seqs)
        for c in chunks:
            out.update(((i, j), al) for i, j, al in _align_chunk(c))
        return out
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(jobs, initializer=_init_worker, initargs=(seqs,)) as pool:
        for res in pool.imap_unordered(_align_chunk, chunks, chunksize=1):
            out.update(((i, j), al) for i, j, al in res)
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  The build
# ═══════════════════════════════════════════════════════════════════════════

def gold_digest(no_gold: bool) -> str | None:
    if not GOLD_JSON.exists():
        if no_gold:
            return None
        sys.exit(f"Gold set not found at {GOLD_JSON}. The header must name the gold set "
                 f"this build is measured against; pass --no-gold to build without one.")
    return hashlib.sha256(GOLD_JSON.read_bytes()).hexdigest()


def header(gold_sha: str | None) -> dict:
    return {
        "scope": SCOPE,
        "token": TOKEN_RULE,
        "content": CONTENT_RULE,
        "alignment": "smith-waterman",
        "scores": {"match": MATCH, "mismatch": MISMATCH, "gap": GAP},
        "traceback": TRACEBACK,
        "l_min": L_MIN,
        "density": DENSITY,
        "content_min": CONTENT_MIN,
        "candidates": CANDIDATES,
        "gold_sha256": gold_sha,
    }


def build(corpus: Corpus, jobs: int) -> tuple[list[dict], dict]:
    """The sorted passages and the per-stage counts."""
    t0 = time.time()
    pairs = candidate_pairs(corpus.seqs, corpus.surah_of)
    stats: dict = {"candidates": len(pairs), "candidates_s": round(time.time() - t0, 1)}
    t1 = time.time()
    aligned = align_stage(corpus.seqs, pairs, jobs)
    stats["align_s"] = round(time.time() - t1, 1)
    passages, why = [], Counter()
    for i, j in pairs:
        reason, passage = corpus.judge(i, j, aligned[(i, j)])
        if passage is None:
            why[reason] += 1
        else:
            passages.append(passage)
    # Global indexes are (surah, ayah) order, so sorting by them is sorting by (a, b)
    # numerically — the order the reader serves ties in.
    passages.sort(key=lambda p: (corpus.index[_ref(p["a"])], corpus.index[_ref(p["b"])]))
    stats.update({f"rejected_{k_}": why[k_] for k_ in ("l_min", "density", "content_min")})
    stats["passages"] = len(passages)
    return passages, stats


def _ref(raw: str) -> tuple[int, int]:
    s, a = raw.split(":")
    return int(s), int(a)


def dataset(passages: list[dict], head: dict) -> dict:
    return {"schema": SCHEMA, "build": head, "passages": passages}


def dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=False, separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-gold", action="store_true",
                    help="build without the gold set (header gold_sha256 = null)")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                    help="alignment worker processes (default: CPUs − 1)")
    ap.add_argument("--surahs", help="comma-separated surahs: align among these only, "
                                     "print the counts, write nothing")
    args = ap.parse_args(argv)
    only = sorted({int(s) for s in args.surahs.split(",")}) if args.surahs else None

    head = None if only else header(gold_digest(args.no_gold))
    t0 = time.time()
    records = qac_records()
    if only:
        records = (r for r in records if r.surah in set(only))
    corpus = Corpus(records)
    print(f"Corpus: {len(corpus.refs)} verses, "
          f"{sum(len(s) for s in corpus.seqs)} words [{time.time() - t0:.1f}s]")
    passages, stats = build(corpus, args.jobs)
    print(f"CANDIDATES (D4): {stats['candidates']} cross-surah pairs share ≥ {L_MIN} tokens "
          f"[{stats['candidates_s']}s]")
    print(f"ALIGNED (D2/D3): {stats['passages']} passages; rejected — l_min "
          f"{stats['rejected_l_min']}, density {stats['rejected_density']}, content_min "
          f"{stats['rejected_content_min']} [{stats['align_s']}s, {args.jobs} job(s)]")
    if only:
        print(f"(surahs {only} only — nothing written)")
        return 0
    out = paths.QURAN_PASSAGES_JSON
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(dumps(dataset(passages, head)), encoding="utf-8")
    tmp.replace(out)
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.2f} MB) — {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
