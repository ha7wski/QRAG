#!/usr/bin/env python3
"""
eval_cross_material.py — measure the cross-only syntax and material rules on their
two blind samples.

`openspec/changes/unify-cross-closeness-cue` chose `σ_x` (`syn ≥ σ_x`) and `κ` (the
shared lemmas cover `κ` of the shorter verse's content words, `L ≥ 2`) on a
CALIBRATION sample (D6) and measures them on a disjoint HOLDOUT (D7). Both were drawn
by `scripts/draw_cross_material_samples.py` from the pairs the PREVIOUS build stored
and labelled blind (D5): `tests/eval/cross_material_calibration.json` and
`tests/eval/cross_material_holdout.json` (local-only).

Reads both samples and `data/derived/quran_similarity.json` (through its loader), and
reports:

  * on the HOLDOUT — the figure that counts — positives stored and negatives stored,
    over the labelled positives / negatives, against the targets registered in D7
    (positives ≥ 0.70, negatives ≤ 0.20), printed PASS / MISS;
  * the same two figures on the CALIBRATION, apart and with no target (it chose the
    thresholds, so it is in-sample);
  * for every labelled pair of both samples, the PREDICTED outcome — `syn ≥ σ_x` and
    the core's `material_ok` at the header's `κ`, recomputed model-free from the
    corpus through the cross build's own `Corpus` — against the actual one, listing
    each mismatch: D3 makes the prediction exact for a pair the previous build
    stored, so a mismatch is a defect of the build or of this script, never noise;
  * the fate of 2:10 / 39:26 (the pair that motivated the change, in neither sample),
    2:2 / 32:2 and 2:2 / 3:138;
  * with `--previous FILE`, the pairs stored now that FILE (the previous
    `quran_similarity.json`) did not store — the relative cut running after the new
    rules is the only way the build can gain one (D3) — and the pairs it lost.

«Stored» is «listed under EITHER verse» in `quran_similarity.json`. A pair with no
majority (`label: null`) is skipped and counted; any other label but `positive` /
`negative` refuses the report.

It REFUSES to report when a sample's sha256 differs from the one the dataset header
recorded (`calibration_sha256`, `holdout_sha256`), or when the header recorded none:
a number measured on another sample is not the registered measurement.

Nothing is written, and nothing is tuned from what this prints (D7: a miss is
recorded, never tuned).

    python scripts/eval_cross_material.py
    python scripts/eval_cross_material.py --json
    python scripts/eval_cross_material.py --previous /path/to/previous/quran_similarity.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import closeness_core as cc  # noqa: E402
from quran_data import loaders  # noqa: E402

CALIBRATION_JSON = ROOT / "tests" / "eval" / "cross_material_calibration.json"
HOLDOUT_JSON = ROOT / "tests" / "eval" / "cross_material_holdout.json"
CALIBRATION_KEY, HOLDOUT_KEY = "calibration_sha256", "holdout_sha256"
POSITIVE, NEGATIVE = "positive", "negative"
LABELS = (POSITIVE, NEGATIVE)
# design.md D7, copied as numbers so a miss is printed as a miss.
TARGET_POS_STORED = 0.70
TARGET_NEG_STORED = 0.20
# design.md D7: reported apart, no target.
WATCHED = (("2:10", "39:26"), ("2:2", "32:2"), ("2:2", "3:138"))

Signals = dict          # {"syn", "L", "c", "coverage"}
Predictor = Callable[[str, str], "Signals | None"]


# ── refs, keys and the stored relation ───────────────────────────────────

def parse_ref(raw: str) -> tuple[int, int]:
    s, a = raw.split(":")
    return int(s), int(a)


def pair_key(a: str, b: str) -> tuple[str, str]:
    """The unordered pair as an ordered tuple, lower verse first (numerically)."""
    return (a, b) if parse_ref(a) <= parse_ref(b) else (b, a)


def ref_of(key: tuple[str, str]) -> str:
    return f"{key[0]}/{key[1]}"


def stored_pairs(data: dict) -> set[tuple[str, str]]:
    """Every pair listed under EITHER verse in `quran_similarity.json`."""
    return {pair_key(ref, e["r"]) for ref, lst in data.get("neighbours", {}).items() for e in lst}


def compare_previous(now: dict, before: dict) -> tuple[list, list]:
    """`(gained, lost)`: pairs stored now and not before, and the reverse, sorted."""
    a, b = stored_pairs(now), stored_pairs(before)
    order = lambda k: (parse_ref(k[0]), parse_ref(k[1]))  # noqa: E731
    return sorted(a - b, key=order), sorted(b - a, key=order)


# ── the prediction ────────────────────────────────────────────────────────

def predict(sig: Signals, sigma_x: float, kappa: float) -> bool:
    """D1–D2 as the build applies them: `syn ≥ σ_x − ε` (`passes_syntax`) AND
    `L ≥ MATERIAL_MIN_LEMMAS` AND `L / c ≥ κ − ε` — the core's own comparisons."""
    return (cc.passes_syntax(sig["syn"], sigma_x)
            and sig["L"] >= cc.MATERIAL_MIN_LEMMAS
            and sig["coverage"] >= kappa - cc.COVERAGE_EPS)


def corpus_predictor(corpus) -> Predictor:
    """The signals of a pair, model-free, from the cross build's `Corpus`: the exact
    `syn` (not the 4-decimal stored value, which can sit on the wrong side of σ_x) and
    the material `(L, c, coverage)` of the pair's matching."""
    def signals(a: str, b: str) -> Signals | None:
        try:
            i, j = corpus.index[parse_ref(a)], corpus.index[parse_ref(b)]
        except KeyError:
            return None
        i, j = min(i, j), max(i, j)
        L, c, coverage = corpus.material_coverage(i, j)
        return {"syn": corpus.syntax(i, j).syn, "L": L, "c": c, "coverage": coverage}
    return signals


def make_predictor() -> Predictor:
    import build_quran_similarity as q
    return corpus_predictor(q.Corpus())


# ── scoring ───────────────────────────────────────────────────────────────

def score(sample: dict, stored: set, predictor: Predictor, sigma_x: float, kappa: float) -> dict:
    """Positives / negatives stored, unlabelled pairs, and predicted-vs-actual mismatches."""
    out = {POSITIVE: {"pairs": 0, "stored": 0, "refs": []},
           NEGATIVE: {"pairs": 0, "stored": 0, "refs": []},
           "unlabelled": [], "mismatches": [], "unpredicted": []}
    for p in sample.get("pairs", []):
        key = pair_key(p["a"], p["b"])
        label = p.get("label")
        if label is None:
            out["unlabelled"].append(ref_of(key))
            continue
        if label not in LABELS:
            sys.exit(f"Refusing to report: {ref_of(key)} carries the label {label!r}; a sample "
                     f"is a measurement — only {LABELS} or null are read.")
        is_stored = key in stored
        row = out[label]
        row["pairs"] += 1
        if is_stored:
            row["stored"] += 1
            row["refs"].append(ref_of(key))
        sig = predictor(*key)
        if sig is None:
            out["unpredicted"].append(ref_of(key))
            continue
        predicted = predict(sig, sigma_x, kappa)
        if predicted != is_stored:
            out["mismatches"].append({"ref": ref_of(key), "label": label, "predicted": predicted,
                                      "stored": is_stored, **_rounded(sig)})
    return out


def targets(rep: dict) -> dict:
    pos, neg = rep[POSITIVE], rep[NEGATIVE]
    return {"positives": bool(pos["pairs"]) and pos["stored"] / pos["pairs"] >= TARGET_POS_STORED,
            "negatives": bool(neg["pairs"]) and neg["stored"] / neg["pairs"] <= TARGET_NEG_STORED}


def _rounded(sig: Signals) -> dict:
    return {"syn": round(sig["syn"], 4), "L": sig["L"], "c": sig["c"],
            "coverage": round(sig["coverage"], 4)}


def watched(stored: set, scores: dict, predictor: Predictor, sigma_x: float, kappa: float
            ) -> list[dict]:
    rows = []
    for a, b in WATCHED:
        key = pair_key(a, b)
        sig = predictor(*key)
        rows.append({"ref": f"{a}/{b}", "stored": key in stored, "s": scores.get(key),
                     "predicted": None if sig is None else predict(sig, sigma_x, kappa),
                     **({} if sig is None else _rounded(sig))})
    return rows


# ── digests ───────────────────────────────────────────────────────────────

def sha256_of(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def check_digest(path: Path, build: dict, key: str) -> str:
    """The sample's sha256, or exit naming the mismatch (a header without it included)."""
    digest = sha256_of(path)
    if digest is None:
        sys.exit(f"Sample not found at {path} (local-only, under tests/eval/).")
    recorded = build.get(key)
    if recorded != digest:
        sys.exit(f"Refusing to report: {path.name}'s sha256 is {digest}, but the dataset header "
                 f"recorded {key} = {recorded}. A measurement on another sample is not the "
                 f"registered one — restore that file, or rebuild and record why.")
    return digest


# ── main ──────────────────────────────────────────────────────────────────

def _fraction(row: dict) -> str:
    n = row["pairs"]
    return f"{row['stored']}/{n} = {row['stored'] / n:.3f}" if n else "0/0"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--previous", type=Path,
                    help="the previous build's quran_similarity.json, to count gained / lost pairs")
    args = ap.parse_args(argv)

    try:
        data = loaders.quran_similarity()
    except (loaders.DatasetMissing, loaders.UnknownSchema) as exc:
        sys.exit(str(exc))
    build = data["build"]
    cal_sha = check_digest(CALIBRATION_JSON, build, CALIBRATION_KEY)
    hold_sha = check_digest(HOLDOUT_JSON, build, HOLDOUT_KEY)
    if "sigma_cross" not in build or "material_min_coverage" not in build:
        sys.exit("Refusing to report: the dataset header names no sigma_cross / "
                 "material_min_coverage — it predates the cross-only rules; rebuild it.")
    sigma_x, kappa = build["sigma_cross"], build["material_min_coverage"]

    stored = stored_pairs(data)
    scores: dict = {}
    for ref, lst in data.get("neighbours", {}).items():
        for e in lst:
            k_ = pair_key(ref, e["r"])
            scores[k_] = max(scores.get(k_, e["s"]), e["s"])
    predictor = make_predictor()
    holdout = score(json.loads(HOLDOUT_JSON.read_text(encoding="utf-8")), stored, predictor,
                    sigma_x, kappa)
    calibration = score(json.loads(CALIBRATION_JSON.read_text(encoding="utf-8")), stored,
                        predictor, sigma_x, kappa)
    report = {"sigma_cross": sigma_x, "material_min_coverage": kappa,
              "holdout": holdout, "holdout_targets": targets(holdout),
              "calibration": calibration,
              "watched": watched(stored, scores, predictor, sigma_x, kappa),
              "stored_pairs": len(stored)}
    if args.previous is not None:
        before = json.loads(args.previous.read_text(encoding="utf-8"))
        gained, lost = compare_previous(data, before)
        report.update(gained_over_previous=len(gained), lost_since_previous=len(lost),
                      gained=[ref_of(k_) for k_ in gained])
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    mark = lambda ok: "PASS" if ok else "MISS"  # noqa: E731
    t = report["holdout_targets"]
    print(f"σ_x = {sigma_x}   κ = {kappa}   calibration sha256 {cal_sha[:12]}… = header ✓   "
          f"holdout sha256 {hold_sha[:12]}… = header ✓   {len(stored)} pairs stored")
    print(f"HOLDOUT positives stored: {_fraction(holdout[POSITIVE])}  "
          f"(target ≥ {TARGET_POS_STORED}) {mark(t['positives'])}")
    print(f"HOLDOUT negatives stored: {_fraction(holdout[NEGATIVE])}  "
          f"(target ≤ {TARGET_NEG_STORED}) {mark(t['negatives'])}")
    print(f"calibration (in-sample, no target): positives stored "
          f"{_fraction(calibration[POSITIVE])}, negatives stored {_fraction(calibration[NEGATIVE])}")
    for name, rep in (("holdout", holdout), ("calibration", calibration)):
        if rep["unlabelled"]:
            print(f"   {name}: {len(rep['unlabelled'])} pair(s) without a majority, left out: "
                  + ", ".join(rep["unlabelled"]))
        if rep["unpredicted"]:
            print(f"   {name}: {len(rep['unpredicted'])} pair(s) the corpus cannot score: "
                  + ", ".join(rep["unpredicted"]))
        print(f"   {name}: predicted vs actual — {len(rep['mismatches'])} mismatch(es)"
              + "".join(f"\n      {m['ref']} ({m['label']}): predicted "
                        f"{'kept' if m['predicted'] else 'dropped'}, actually "
                        f"{'stored' if m['stored'] else 'not stored'} — syn {m['syn']}, "
                        f"L {m['L']}, c {m['c']}, coverage {m['coverage']}"
                        for m in rep["mismatches"]))
    print("Watched pairs (D7, reported apart):")
    for w in report["watched"]:
        sig = " ".join(f"{k_}={w[k_]}" for k_ in ("syn", "L", "c", "coverage") if k_ in w)
        at = "" if w["s"] is None else f" s={w['s']}"
        verdict = "—" if w["predicted"] is None else "kept" if w["predicted"] else "dropped"
        print(f"   {w['ref']:>11}  {'stored' if w['stored'] else 'not stored':<10}{at}  "
              f"predicted {verdict}  {sig}")
    if args.previous is not None:
        print(f"Against {args.previous}: {report['gained_over_previous']} pair(s) stored now and "
              f"not before, {report['lost_since_previous']} stored before and not now"
              + (f" — gained: {', '.join(report['gained'])}" if report["gained"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
