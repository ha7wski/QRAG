#!/usr/bin/env python3
"""
draw_closeness_blind_sample.py — the blind sample of `order-invariant-closeness` (D10.3).

Draws, MODEL-FREE and through NO gate of the relation, 60 cross-surah verse pairs to
be labelled in a fresh context before the first version-2 build. The population is
every pair of verses of different surahs sharing at least `L_MIN_CONTENT` content
lemmas (the passage candidate generator over content tokens only); EVERY pair of it
gets its `lex` (closeness_core D3, the raw matching — no syntax, no semantics), and
`PER_BIN` pairs are drawn per `lex` bin with a seeded generator. Pairs already
in any of the three gold files are excluded, so the sample is fresh.

Writes `tests/eval/closeness_blind_v2.json` with `label: null` on every pair. The
labeller fills `label` (`positive` / `negative`) and `reason` from the written
definition and the two texts only. Deterministic: same seed, same file.

    python scripts/draw_closeness_blind_sample.py
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
import build_surah_similarity as bs  # noqa: E402
import closeness_core as cc  # noqa: E402
from quran_data.corpus import chakl_by_ref, strip_leading_basmala  # noqa: E402

SEED = 20261006
L_MIN_CONTENT = 3
BINS = ((0.3, 0.5), (0.5, 0.7), (0.7, 1.0001))
PER_BIN = 20
OUT = ROOT / "tests" / "eval" / "closeness_blind_v2.json"
GOLD = [ROOT / "tests" / "eval" / n for n in
        ("quran_similarity_gold.json", "quran_passages_gold.json")]

DEFINITION_EN = (
    "Two verses of different surahs are CLOSE when they share the same material — the same "
    "lemmas or roots; pronoun suffixes, clitic particles (و ف ب ل ال) and function words do not "
    "count — built the same way (verb aspect and voice, noun type, the particles), with their "
    "blocks in ANY order: a permutation of blocks is close, a few shared words scattered through "
    "two otherwise different verses is not. They also count as close when they share a PASSAGE: "
    "at least 6 identical words, at least 3 of them content words, forming one dense region "
    "(at least three quarters of each window) in both verses, blocks in any order, whatever the "
    "rest of the two verses says. Meaning alone (same subject in another construction) does not "
    "make two verses close.")
DEFINITION_AR = (
    "آيتان من سورتين مختلفتين «متقاربتان» إذا اشتركتا في المادة نفسها — الألفاظ أو الجذور؛ لا تُحسب "
    "ضمائر الإضافة ولا حروف الجر والعطف المتصلة ولا أدوات المعاني — وبُنيتا على الوجه نفسه (زمن الفعل "
    "ومبنيّه للمعلوم أو المجهول، نوع الاسم، الأدوات)، بأي ترتيب للمقاطع: تبديلُ مواضع المقاطع تقاربٌ، "
    "وكلماتٌ قليلة مشتركة متفرقة في آيتين مختلفتين ليس تقاربًا. وتُعدّان متقاربتين أيضًا إذا اشتركتا "
    "في مقطع: ست كلمات متطابقة على الأقل، ثلاث منها على الأقل كلمات محتوى، تؤلّف منطقة واحدة متكاثفة "
    "(ثلاثة أرباع كل نافذة على الأقل) في الآيتين، بأي ترتيب للمقاطع، مهما قال باقي الآيتين. "
    "اتفاق المعنى وحده (الموضوع نفسه ببناء آخر) لا يجعل الآيتين متقاربتين.")


def shown(s: int, a: int) -> str:
    return strip_leading_basmala(s, a, chakl_by_ref()[(s, a)]["text"])


def gold_pairs() -> set[tuple[str, str]]:
    out = set()
    for path in GOLD:
        for p in json.loads(path.read_text())["pairs"]:
            out.add(tuple(sorted((p["a"], p["b"]))))
    return out


def main() -> int:
    corpus = bp.Corpus()
    _, idf = bs.load_content_roots()
    content_seqs = [tuple(t for t, c in zip(seq, flags) if c)
                    for seq, flags in zip(corpus.seqs, corpus.content)]
    population = bp.candidate_pairs(content_seqs, corpus.surah_of, l_min=L_MIN_CONTENT)
    print(f"population: {len(population)} cross-surah pairs sharing ≥ {L_MIN_CONTENT} content lemmas")
    rng = random.Random(SEED)
    pre = population
    known = gold_pairs()
    scored = []
    for i, j in pre:
        ra, rb = corpus.refs[i], corpus.refs[j]
        key = tuple(sorted((bp.ref_str(ra), bp.ref_str(rb))))
        if key in known:
            continue
        va = [w.token for w in corpus.words[i]]
        vb = [w.token for w in corpus.words[j]]
        edges = cc.match_all(va, vb, corpus.roots[i], corpus.roots[j],
                             corpus.content[i], corpus.content[j])
        value = cc.lex(edges, corpus.roots[i], corpus.roots[j],
                       corpus.content[i], corpus.content[j], idf)
        scored.append((key, value))
    pairs = []
    for lo, hi in BINS:
        pool = [(k, v) for k, v in scored if lo <= v < hi]
        pool.sort()
        take = rng.sample(pool, min(PER_BIN, len(pool)))
        print(f"bin [{lo}, {hi if hi < 1.0001 else 1.0}): {len(pool)} in population, {len(take)} drawn")
        for (a, b), v in sorted(take):
            sa, aa = map(int, a.split(":"))
            sb, ab = map(int, b.split(":"))
            pairs.append({"a": a, "b": b, "lex": round(v, 4), "bin": f"[{lo}, {hi if hi < 1.0001 else 1.0})",
                          "text_a": shown(sa, aa), "text_b": shown(sb, ab),
                          "label": None, "reason": None})
    data = {
        "version": 1,
        "scope": "cross-surah-closeness-blind",
        "definition": DEFINITION_EN,
        "definition_ar": DEFINITION_AR,
        "conventions": [
            "Drawn by scripts/draw_closeness_blind_sample.py (seed %d): population = every cross-surah "
            "pair sharing >= %d content lemmas, every one scored by lex (closeness_core D3, the raw "
            "matching, no gate); %d pairs drawn per lex bin; pairs of the existing gold files excluded."
            % (SEED, L_MIN_CONTENT, PER_BIN),
            "Pair shape: {a, b, lex, bin, text_a, text_b, label, reason}; a < b by (surah, ayah); "
            "texts are the shown vocalized verses (Basmala stripped).",
            "Labels: positive (close under the definition: same material built the same way in any "
            "block order, or a shared passage) / negative. Labelled in a fresh context from the "
            "definition and the two texts ONLY, before the first version-2 build; every label carries "
            "its reason.",
            "The target registered before the draw: positives stored by the relation (either direction) "
            ">= 0.65; negatives stored <= 0.25.",
        ],
        "population": len(population),
        "pairs": pairs,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {OUT} — {len(pairs)} pairs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
