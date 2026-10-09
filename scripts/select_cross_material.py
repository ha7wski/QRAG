#!/usr/bin/env python3
"""
select_cross_material.py — pick the cross-only syntax threshold `σ_x` and the material
coverage `κ` by the selection rule registered BEFORE any label was read.

`openspec/changes/unify-cross-closeness-cue` D6. Reads ONE file: the labelled
CALIBRATION sample `tests/eval/cross_material_calibration.json` (local-only). It never
opens the holdout — the holdout measures the choice (D7, `scripts/eval_cross_material.py`)
and must not take part in it.

Every pair of the calibration was stored by the previous build, so D3 (both new rules are
filters after the semantic gate) makes the simulation exact: a pair stays stored iff

    syn ≥ σ_x            (`closeness_core.passes_syntax`, tolerant of the last bit)
    AND L ≥ 2            (`closeness_core.MATERIAL_MIN_LEMMAS`)
    AND wcov ≥ κ         (IDF-weighted coverage, tolerant by `closeness_core.COVERAGE_EPS`)

— the predicate `closeness_core.material_ok`. `syn` and `L` are read from the sample;
`wcov` (`closeness_core.weighted_coverage`) is recomputed model-free from the cross
build's `Corpus`, since the sample's `coverage` field is the count-only `L / c`.

D6, verbatim: grid `σ_x ∈ SIGMA_CROSS_GRID`, `κ ∈ MATERIAL_COVERAGE_GRID` (imported from
the cross build, the only legal values). For each point, `P` = labelled positives kept /
labelled positives, `N` = labelled negatives kept / labelled negatives. Keep the points
with `N ≤ 0.15`; among them the highest `P`; ties → the higher `κ`, then the higher `σ_x`.
If no point has `N ≤ 0.15`: the lowest `N`, ties → the highest `P` (then the same κ / σ_x
order, so the choice is always unique), and the ceiling is recorded as NOT reached.

A pair with no majority (`label: null`) is left out and counted. Nothing is written.

    python scripts/select_cross_material.py
    python scripts/select_cross_material.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import closeness_core as cc  # noqa: E402
from build_quran_similarity import (  # noqa: E402 — the grid, defined once
    MATERIAL_COVERAGE_GRID, SIGMA_CROSS_GRID,
)

CALIBRATION_JSON = ROOT / "tests" / "eval" / "cross_material_calibration.json"
N_CEILING = 0.15          # D6: negatives kept ≤ 0.15
SYN_ROUNDING = 5e-5       # the sample's `syn` is rounded to 4 decimals


def load_calibration(path: Path = CALIBRATION_JSON) -> tuple[list[dict], int]:
    """The labelled pairs (majority `positive` / `negative`) and the no-majority count.
    Refuses an unlabelled file or an unknown label."""
    data = json.loads(path.read_text())
    labelled, no_majority = [], 0
    for p in data["pairs"]:
        label = p.get("label")
        if label is None:
            if not p.get("votes"):
                sys.exit(f"{path.name}: {p['a']}/{p['b']} carries no votes — label the sample "
                         "first (unify-cross-closeness-cue task 1.3)")
            no_majority += 1
            continue
        if label not in ("positive", "negative"):
            sys.exit(f"{path.name}: {p['a']}/{p['b']} has label {label!r}")
        labelled.append(p)
    recorded = data.get("no_majority")
    if recorded is not None and recorded != no_majority:
        sys.exit(f"{path.name}: header no_majority={recorded} but {no_majority} pairs are null")
    return labelled, no_majority


def check_rounding(pairs: list[dict]) -> None:
    """A rounded `syn` within the rounding step of a grid threshold, without being that
    threshold's own rounding, could sit on either side of it: refuse rather than guess."""
    for p in pairs:
        for s in SIGMA_CROSS_GRID:
            if abs(p["syn"] - s) < SYN_ROUNDING and p["syn"] != round(s, 4):
                sys.exit(f"{p['a']}/{p['b']}: syn {p['syn']} is ambiguous against σ_x = {s}")


def add_weighted_coverage(pairs: list[dict]) -> None:
    """Each pair's IDF-weighted coverage `wcov`, from the cross build's own `Corpus`."""
    import build_quran_similarity as q
    corpus = q.Corpus()
    for p in pairs:
        i, j = corpus.index[q.parse_ref(p["a"])], corpus.index[q.parse_ref(p["b"])]
        lemmas, _, p["wcov"] = corpus.material_coverage(min(i, j), max(i, j))
        if lemmas != p["L"]:
            sys.exit(f"{p['a']}/{p['b']}: L {lemmas} differs from the sample's {p['L']}")


def kept(p: dict, sigma_x: float, kappa: float) -> bool:
    """D1 + D2 on one stored pair (see the module docstring)."""
    if not cc.passes_syntax(p["syn"], sigma_x):
        return False
    if p["L"] < cc.MATERIAL_MIN_LEMMAS:
        return False
    return p["wcov"] >= kappa - cc.COVERAGE_EPS


def grid(pairs: list[dict]) -> list[dict]:
    pos = [p for p in pairs if p["label"] == "positive"]
    neg = [p for p in pairs if p["label"] == "negative"]
    if not pos or not neg:
        sys.exit("the calibration needs labelled positives AND negatives")
    rows = []
    for s in SIGMA_CROSS_GRID:
        for k in MATERIAL_COVERAGE_GRID:
            kp = sum(kept(p, s, k) for p in pos)
            kn = sum(kept(p, s, k) for p in neg)
            rows.append({"sigma_x": s, "kappa": k, "pos_kept": kp, "pos": len(pos),
                         "neg_kept": kn, "neg": len(neg),
                         "P": kp / len(pos), "N": kn / len(neg)})
    return rows


def choose(rows: list[dict]) -> tuple[dict, bool]:
    """D6. Returns (the chosen row, whether the N ceiling was reached)."""
    ok = [r for r in rows if r["N"] <= N_CEILING + 1e-12]
    if ok:
        return max(ok, key=lambda r: (r["P"], r["kappa"], r["sigma_x"])), True
    return min(rows, key=lambda r: (r["N"], -r["P"], -r["kappa"], -r["sigma_x"])), False


def fmt_sigma(s: float) -> str:
    return "2/3" if abs(s - 2 / 3) < 1e-12 else f"{s:.2f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    pairs, no_majority = load_calibration()
    check_rounding(pairs)
    add_weighted_coverage(pairs)
    rows = grid(pairs)
    best, reached = choose(rows)

    if args.json:
        print(json.dumps({"calibration": str(CALIBRATION_JSON.relative_to(ROOT)),
                          "labelled": len(pairs), "no_majority": no_majority,
                          "grid": rows, "chosen": best, "ceiling_reached": reached},
                         ensure_ascii=False, indent=1))
        return 0

    npos, nneg = rows[0]["pos"], rows[0]["neg"]
    print(f"calibration: {CALIBRATION_JSON.relative_to(ROOT)} — {len(pairs)} labelled "
          f"({npos} positive, {nneg} negative), {no_majority} no majority (left out)")
    print(f"rule (D6): N ≤ {N_CEILING}; max P; ties → higher κ, then higher σ_x\n")
    print(f"{'σ_x':>5} {'κ':>5}   {'P':>13}   {'N':>13}   eligible")
    for r in rows:
        mark = "  <= chosen" if r is best else ""
        print(f"{fmt_sigma(r['sigma_x']):>5} {r['kappa']:>5.2f}   "
              f"{r['P']:.3f} ({r['pos_kept']:>2}/{r['pos']})   "
              f"{r['N']:.3f} ({r['neg_kept']:>2}/{r['neg']})   "
              f"{'yes' if r['N'] <= N_CEILING + 1e-12 else 'no':>8}{mark}")
    print(f"\nchosen: σ_x = {fmt_sigma(best['sigma_x'])}, κ = {best['kappa']:.2f} — "
          f"P = {best['P']:.3f} ({best['pos_kept']}/{best['pos']}), "
          f"N = {best['N']:.3f} ({best['neg_kept']}/{best['neg']}); "
          f"ceiling N ≤ {N_CEILING} {'reached' if reached else 'NOT reached'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
