#!/usr/bin/env python3
"""
draw_short_pair_blind_sample.py — the blind sample of `short-verse-material` (D2).

Draws, MODEL-FREE and through NO gate of the relation, 40 cross-surah pairs of SHORT
verses to be labelled in a fresh context before the build that adds the short-verse
material rule. Population: every pair of verses of different surahs whose shorter
verse has at most `SHORT_MAX` QAC words, whose longer verse has at most `LONG_MAX`,
whose order-invariant matching (closeness_core D2) holds at least one `lemma` content
edge, and which passes the SYNTAX gate (coarse signature, σ, the cross short-exact rule)
— model-free, the class the rule targets: the same mould. Neither the semantic gate nor
the rule under test is applied. Strata: `PER_STRATUM` pairs with exactly one shared content lemma, `PER_STRATUM`
with two or more. Pairs of every existing gold and blind file are excluded.

Writes `tests/eval/closeness_blind_short.json` with `label: null` on every pair; the
definition is the one of `closeness_blind_v2.json`, word for word.

    python scripts/draw_short_pair_blind_sample.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_quran_passages as bp  # noqa: E402
import build_quran_similarity as bq  # noqa: E402
import build_surah_similarity as bs  # noqa: E402
import closeness_core as cc  # noqa: E402
from draw_closeness_blind_sample import (DEFINITION_AR, DEFINITION_EN,  # noqa: E402
                                         gold_pairs, shown)

SEED = 20261007
SHORT_MAX = 5
LONG_MAX = 10
PER_STRATUM = 20
OUT = ROOT / "tests" / "eval" / "closeness_blind_short.json"
BLIND_V2 = ROOT / "tests" / "eval" / "closeness_blind_v2.json"


def main() -> int:
    corpus = bp.Corpus()
    known = gold_pairs()
    if BLIND_V2.exists():
        known |= {tuple(sorted((p["a"], p["b"]))) for p in json.loads(BLIND_V2.read_text())["pairs"]}
    n = [len(ws) for ws in corpus.words]
    short = [i for i, k in enumerate(n) if k <= LONG_MAX]
    by_lemma: dict[int, list[int]] = {}
    for i in short:
        for t, c in zip(corpus.seqs[i], corpus.content[i]):
            if c:
                by_lemma.setdefault(t, []).append(i)
    candidates: set[tuple[int, int]] = set()
    for verses in by_lemma.values():
        vs = sorted(set(verses))
        for x in range(len(vs)):
            for y in range(x + 1, len(vs)):
                i, j = vs[x], vs[y]
                if corpus.surah_of[i] != corpus.surah_of[j] and min(n[i], n[j]) <= SHORT_MAX:
                    candidates.add((i, j))
    sigs = bs.load_signatures()
    content_sets, _ = bs.load_content_roots()
    vwords = bs.load_verse_words(content_sets)
    strata: dict[str, list[tuple[tuple[str, str], int]]] = {"1": [], "2+": []}
    for i, j in sorted(candidates):
        key = (bp.ref_str(corpus.refs[i]), bp.ref_str(corpus.refs[j]))
        if tuple(sorted(key)) in known:
            continue
        edges = cc.match_all([w.token for w in corpus.words[i]], [w.token for w in corpus.words[j]],
                             corpus.roots[i], corpus.roots[j], corpus.content[i], corpus.content[j])
        lemmas = sum(1 for e in edges if e.kind == cc.LEMMA)
        if not lemmas:
            continue
        ra, rb = corpus.refs[i], corpus.refs[j]
        sy = bs.syntax_similarity(sigs[ra], sigs[rb], vwords[ra], vwords[rb]).syn
        if not (cc.passes_syntax(sy) and bq.passes_short_rule(len(sigs[ra]), len(sigs[rb]), sy)):
            continue
        if lemmas:
            strata["1" if lemmas == 1 else "2+"].append((key, lemmas))
    rng = random.Random(SEED)
    pairs = []
    for name, pool in strata.items():
        take = rng.sample(pool, min(PER_STRATUM, len(pool)))
        print(f"stratum {name} shared lemma(s): {len(pool)} in population, {len(take)} drawn")
        for (a, b), lemmas in sorted(take):
            sa, aa = map(int, a.split(":"))
            sb, ab = map(int, b.split(":"))
            pairs.append({"a": a, "b": b, "shared_lemmas": lemmas, "stratum": name,
                          "text_a": shown(sa, aa), "text_b": shown(sb, ab),
                          "label": None, "reason": None})
    data = {
        "version": 1,
        "scope": "cross-surah-closeness-blind-short",
        "definition": DEFINITION_EN,
        "definition_ar": DEFINITION_AR,
        "conventions": [
            "Drawn by scripts/draw_short_pair_blind_sample.py (seed %d): population = every cross-surah "
            "pair whose shorter verse has <= %d QAC words and longer <= %d, sharing >= 1 content lemma "
            "(closeness_core D2 lemma edges), passing the syntax gate (coarse signature, sigma, short-exact) "
            "and no other gate; %d pairs per stratum (1 shared lemma / 2+); pairs "
            "of the existing gold and blind files excluded." % (SEED, SHORT_MAX, LONG_MAX, PER_STRATUM),
            "Pair shape: {a, b, shared_lemmas, stratum, text_a, text_b, label, reason}; a < b by "
            "(surah, ayah); texts are the shown vocalized verses (Basmala stripped).",
            "Labels: positive / negative under the definition, from the definition and the two texts "
            "ONLY, in a fresh context, before the short-verse-material build; every label carries its "
            "reason.",
            "Targets registered before the draw: negatives stored <= 0.25; positives stored >= 0.65; "
            "the 1-lemma stratum's positives are reported apart as the rule's recall cost.",
        ],
        "population": {k: len(v) for k, v in strata.items()},
        "pairs": pairs,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {OUT} — {len(pairs)} pairs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
