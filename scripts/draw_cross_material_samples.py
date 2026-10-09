#!/usr/bin/env python3
"""
draw_cross_material_samples.py — the two samples of `unify-cross-closeness-cue` (D4).

Draws, MODEL-FREE and BEFORE any threshold is chosen, a CALIBRATION sample (which
chooses `σ_x` and `κ`, D6) and a disjoint HOLDOUT sample (which measures them, D7).
The population is every distinct pair stored in the CURRENT
`data/derived/quran_similarity.json` (its `neighbours`): the new cross-only rules are
filters, they can only remove a stored pair, so a pair outside it can never be gained.

Per pair:
  syn       the stored `syn` (coarse signature, block re-ordering);
  L         the number of `lemma` edges of the pair's order-invariant matching
            (`closeness_core.match_all`, through the cross build's own `Corpus`, so the
            per-verse tokens / roots / content flags are exactly the build's);
  c         `min(cA, cB)`, the content-word count (`closeness_core.content_words`) of the
            verse with fewer content words;
  coverage  `L / c` (0 when `c` is 0).

Strata (D4): coverage [0, 0.25) · [0.25, 0.5) · [0.5, 1] × syn [σ, 0.85) · [0.85, 1].
`PER_STRATUM` pairs per stratum per file, seeded; a stratum with fewer than
`2 × PER_STRATUM` pairs is split alternately between the two files in its seeded order,
and its size is reported. Excluded: every pair of the four gold / blind files and the
pair that motivated the change (2:10 / 39:26, reported apart, never drawn).

Each file stores the D5 definition (both languages) and `label: null`; the labellers
fill `label`, `reason` and `votes` from the definition and the two texts only.
Deterministic: same seed, same population, same bytes.

    python scripts/draw_cross_material_samples.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_quran_similarity as bq  # noqa: E402
import closeness_core as cc  # noqa: E402
from quran_data import paths  # noqa: E402

SEED = 20261009
PER_STRATUM = 10
SIGMA = cc.SIGMA
COVERAGE_BINS = ((0.0, 0.25, "[0, 0.25)"), (0.25, 0.5, "[0.25, 0.5)"), (0.5, None, "[0.5, 1]"))
SYN_BINS = ((SIGMA - cc.SIGMA_EPS, 0.85, "[σ, 0.85)"), (0.85, None, "[0.85, 1]"))
MOTIVATING = ("2:10", "39:26")
EVAL = ROOT / "tests" / "eval"
EXCLUDED_FILES = [EVAL / n for n in ("quran_similarity_gold.json", "quran_passages_gold.json",
                                     "closeness_blind_v2.json", "closeness_blind_short.json")]
OUT_CALIBRATION = EVAL / "cross_material_calibration.json"
OUT_HOLDOUT = EVAL / "cross_material_holdout.json"

# D5 — the definition the labellers read, verbatim from the design.
DEFINITION_EN = (
    "Two verses of different surahs are CLOSE when they say the same thing, built the same way, "
    "with enough of the same lemmas — whatever their length. Pronoun suffixes, clitic particles "
    "(و ف ب ل ال) and function words do not count, and blocks may come in any order. A few shared "
    "words scattered through two otherwise different verses is NOT closeness, even when both verses "
    "speak of the same subject; and the same subject in another construction is NOT closeness. A "
    "short verse wholly contained in a longer one IS close.")
DEFINITION_AR = (
    "آيتان من سورتين مختلفتين «متقاربتان» إذا قالتا الشيء نفسه، بالبناء نفسه، بقدرٍ كافٍ من الألفاظ "
    "نفسها — طالتا أو قصرتا. لا تُحسب ضمائر الإضافة ولا الحروف المتصلة (و ف ب ل ال) ولا أدوات المعاني، "
    "ويجوز أي ترتيب للمقاطع. كلماتٌ قليلة مشتركة متفرقة في آيتين مختلفتين ليست تقاربًا، ولو كان موضوعهما "
    "واحدًا؛ والموضوع نفسه ببناء آخر ليس تقاربًا. والآية القصيرة الواردة بتمامها في آية أطول متقاربةٌ معها.")


def ref_key(raw: str) -> tuple[int, int]:
    return bq.parse_ref(raw)


def pair_key(a: str, b: str) -> tuple[str, str]:
    """The pair, lower verse first by (surah, ayah)."""
    return tuple(sorted((a, b), key=ref_key))


def excluded_pairs() -> set[tuple[str, str]]:
    out = {pair_key(*MOTIVATING)}
    for path in EXCLUDED_FILES:
        for p in json.loads(path.read_text())["pairs"]:
            out.add(pair_key(p["a"], p["b"]))
    return out


def stored_pairs() -> dict[tuple[str, str], float]:
    """Every distinct stored pair and its `syn` (identical from either side)."""
    data = json.loads(paths.QURAN_SIMILARITY_JSON.read_text())
    out: dict[tuple[str, str], float] = {}
    for a, lst in data["neighbours"].items():
        for e in lst:
            key = pair_key(a, e["r"])
            if key in out and out[key] != e["syn"]:
                sys.exit(f"pair {key} stored with two syn values: {out[key]} / {e['syn']}")
            out[key] = e["syn"]
    return out


def material(corpus: bq.Corpus, a: str, b: str) -> tuple[int, int]:
    """`(L, c)`: lemma edges of the pair's matching, and the shorter content count."""
    i, j = corpus.index[ref_key(a)], corpus.index[ref_key(b)]
    va, vb = corpus.vwords[i], corpus.vwords[j]
    edges = corpus.edges(i, j)
    lemmas = sum(1 for e in cc.content_edges(edges) if e.kind == cc.LEMMA)
    return lemmas, min(sum(va.content), sum(vb.content))


def bin_of(value: float, bins) -> str:
    for lo, hi, label in bins:
        if value >= lo and (hi is None or value < hi):
            return label
    raise ValueError(f"{value} outside every bin")


def stratum_of(coverage: float, syn: float) -> str:
    return f"coverage {bin_of(coverage, COVERAGE_BINS)} × syn {bin_of(syn, SYN_BINS)}"


def main() -> int:
    population = stored_pairs()
    excluded = excluded_pairs()
    print(f"population: {len(population)} stored cross-surah similarity pairs")
    corpus = bq.Corpus()

    rows = {}
    for (a, b), s in sorted(population.items(), key=lambda kv: (ref_key(kv[0][0]), ref_key(kv[0][1]))):
        L, c = material(corpus, a, b)
        cov = L / c if c else 0.0
        rows[(a, b)] = {"a": a, "b": b, "stratum": stratum_of(cov, s), "syn": s,
                        "L": L, "c": c, "coverage": round(cov, 4)}

    motivating = rows.get(pair_key(*MOTIVATING))
    print(f"motivating pair {'/'.join(MOTIVATING)}: "
          + (json.dumps(motivating, ensure_ascii=False) if motivating else "NOT STORED"))

    strata = [f"coverage {cl} × syn {sl}" for _, _, cl in COVERAGE_BINS for _, _, sl in SYN_BINS]
    rng = random.Random(SEED)
    calibration, holdout = [], []
    sizes = {}
    for name in strata:
        pool = [k for k, r in rows.items() if r["stratum"] == name and k not in excluded]
        total = sum(1 for r in rows.values() if r["stratum"] == name)
        rng.shuffle(pool)       # pool is in (surah, ayah) order before the shuffle
        if len(pool) >= 2 * PER_STRATUM:
            cal, hol, mode = pool[:PER_STRATUM], pool[PER_STRATUM:2 * PER_STRATUM], "drawn"
        else:
            cal, hol, mode = pool[0::2], pool[1::2], "split alternately"
        sizes[name] = {"population": total, "eligible": len(pool),
                       "calibration": len(cal), "holdout": len(hol)}
        print(f"{name}: {total} stored, {len(pool)} eligible, {len(cal)} + {len(hol)} {mode}")
        calibration += cal
        holdout += hol

    cal_set, hol_set = set(calibration), set(holdout)
    assert len(cal_set) == len(calibration) and len(hol_set) == len(holdout)
    assert not cal_set & hol_set, "calibration and holdout overlap"
    assert not (cal_set | hol_set) & excluded, "an excluded pair was drawn"
    assert pair_key(*MOTIVATING) not in cal_set | hol_set

    def write(path: Path, keys, role: str) -> None:
        keys = sorted(keys, key=lambda k: (strata.index(rows[k]["stratum"]),
                                           ref_key(k[0]), ref_key(k[1])))
        data = {
            "version": 1,
            "scope": f"cross-material-{role}",
            "definition_en": DEFINITION_EN,
            "definition_ar": DEFINITION_AR,
            "conventions": [
                "Drawn by scripts/draw_cross_material_samples.py (unify-cross-closeness-cue D4): "
                "population = every distinct pair stored in data/derived/quran_similarity.json "
                "before the change; strata = coverage (L/c: lemma edges over the shorter content "
                "count) × syn; %d per stratum per file, seeded, disjoint from the other file; a "
                "stratum under %d eligible pairs split alternately. Excluded: the four gold / "
                "blind files and %s." % (PER_STRATUM, 2 * PER_STRATUM, "/".join(MOTIVATING)),
                "Labels (D5): positive / negative under the definition, from the two vocalized "
                "texts ONLY (no score, stratum, syn or coverage); three independent fresh-context "
                "labellers, majority of three in `label`, the three votes in `votes`; no majority "
                "-> left out and counted.",
                "The calibration chooses sigma_x and kappa by the D6 rule; the holdout measures "
                "them (D7: positives stored >= 0.70, negatives stored <= 0.20).",
            ],
            "seed": SEED,
            "population_size": len(population),
            "stratum_sizes": {n: {"population": sizes[n]["population"],
                                  "eligible": sizes[n]["eligible"],
                                  "drawn": sizes[n][role]} for n in strata},
            "pairs": [{**rows[k], "label": None, "reason": None, "votes": None} for k in keys],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
        print(f"wrote {path} — {len(keys)} pairs")

    write(OUT_CALIBRATION, calibration, "calibration")
    write(OUT_HOLDOUT, holdout, "holdout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
