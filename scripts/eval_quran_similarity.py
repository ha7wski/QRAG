#!/usr/bin/env python3
"""
eval_quran_similarity.py — measure the cross-surah similarity build against its gold set.

Reads `data/derived/quran_similarity.json` (through its loader) and the gold set
`tests/eval/quran_similarity_gold.json` (local-only), and reports, against the
target pre-registered in `openspec/changes/add-quran-wide-similar-verses/tasks.md`
§1.2:

  * recall@K of the positives, under the pre-registered rule — `(a, b)` is
    recalled iff `b ∈ N10(a)` or `a ∈ N10(b)`; when `a` and `b` are verbatim
    identical (equal `qac.ayah_words()` tuples), it is also recalled when
    `N10(a)` holds any verse verbatim identical to `b`, or `N10(b)` one
    identical to `a`;
  * the rank of each positive (best of the two directions);
  * the positives lost at each stage — length window, bag bound (both 0 by
    construction: a pair is reported there only if its full `syn ≥ σ`, which
    is a bug), syntax gate, candidate cap, semantic gate, shared-root rule,
    top-K — read from the per-gold-pair diagnostics the builder writes;
  * the negatives of each kind stored as neighbours, and how many appear in
    a top-3 (either direction).

It REFUSES to report when the gold file's sha256 differs from the one the
dataset header was frozen against: a number measured on another gold set is
not the pre-registered measurement.

    python scripts/eval_quran_similarity.py
    python scripts/eval_quran_similarity.py --json      # machine-readable
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quran_data import loaders, qac  # noqa: E402

GOLD_JSON = ROOT / "tests" / "eval" / "quran_similarity_gold.json"
STAGES = ("unscored", "length_window", "bag_bound", "syntax_gate", "short_exact",
          "candidate_cap", "semantic_gate", "no_shared_root", "top_k", "relative_cut", "stored")
PREFILTER_STAGES = ("length_window", "bag_bound")
CANDIDATE_STAGES = ("syntax_gate", "candidate_cap")

# The first build's targets (add-quran-wide-similar-verses tasks.md §1.2), still
# printed; candidate loss is reported against them for continuity.
TARGET_CANDIDATE_LOSS = 0.20
# tighten-cross-surah-similarity design.md D6 (T1–T5), copied as numbers so a miss
# is printed as a miss. They apply to the FIRST sample (the pairs with no `sample`
# key) except T3/T4, which read the second sample against the baseline the
# previous build scored on it (tasks.md §1.4, measured before the rebuild).
TARGET_RECALL = 0.65               # T1
TARGET_NEG_TOP3 = 4                # T2
V2_SAMPLE = "v2-syntax-survivors"
V2_BASELINE_NEG_STORED = 2         # T3: stored ≤ half of this
V2_BASELINE_POS_STORED = 7         # T4: stored ≥ 80 % of this
TARGET_PREFILTER_LOSS = 0          # T5


def parse_ref(raw: str) -> tuple[int, int]:
    s, a = raw.split(":")
    return int(s), int(a)


def neighbour_lists(data: dict) -> dict[str, list[str]]:
    """`{"s:a": ["s:a", …]}` in stored (rank) order."""
    return {ref: [e["r"] for e in lst] for ref, lst in data.get("neighbours", {}).items()}


def rank_in(lists: dict, a: str, b: str) -> int | None:
    """1-based position of `b` in `N(a)`, or None."""
    lst = lists.get(a, [])
    return lst.index(b) + 1 if b in lst else None


def best_rank(lists: dict, a: str, b: str, words: dict) -> int | None:
    """Best rank of the pair in either direction, verbatim class included."""
    ranks = [x for x in (rank_in(lists, a, b), rank_in(lists, b, a)) if x]
    wa, wb = words.get(parse_ref(a)), words.get(parse_ref(b))
    if wa is not None and wa == wb:
        for x, y in ((a, b), (b, a)):
            wy = words.get(parse_ref(y))
            for i, n in enumerate(lists.get(x, []), 1):
                if n != x and words.get(parse_ref(n)) == wy:
                    ranks.append(i)
                    break
    return min(ranks) if ranks else None


def evaluate(data: dict, gold: dict, words: dict) -> dict:
    lists = neighbour_lists(data)
    k = data["build"]["K"]
    diag = {(d["a"], d["b"]): d for d in data.get("diagnostics", {}).get("gold", [])}

    def diag_of(p: dict) -> dict:
        return diag.get((p["a"], p["b"])) or diag.get((p["b"], p["a"])) or {}

    first = [p for p in gold["pairs"] if "sample" not in p]
    second = [p for p in gold["pairs"] if p.get("sample") == V2_SAMPLE]
    positives = [p for p in first if p["label"] == "positive"]
    pos_rows = []
    for p in positives:
        rank = best_rank(lists, p["a"], p["b"], words)
        d = diag_of(p)
        stage = d.get("stage", "unknown")
        # A verbatim-class recall counts even when the pair itself was not stored.
        if rank is not None and stage != "stored":
            stage = "stored (verbatim class)"
        pos_rows.append({"ref": f"{p['a']}/{p['b']}", "rank": rank, "stage": stage,
                         **{key: d.get(key) for key in ("syn", "dense", "cov", "ce", "sem")}})
    recalled = sum(1 for r in pos_rows if r["rank"] is not None and r["rank"] <= k)
    stage_loss = Counter(r["stage"] for r in pos_rows if r["rank"] is None)
    candidate_loss = sum(stage_loss.get(s, 0) for s in CANDIDATE_STAGES)
    prefilter_loss = sum(stage_loss.get(s, 0) for s in PREFILTER_STAGES)

    neg = defaultdict(lambda: {"pairs": 0, "stored": 0, "top3": 0, "refs": []})
    for p in first:
        if p["label"] == "positive":
            continue
        row = neg[p["label"]]
        row["pairs"] += 1
        ranks = [x for x in (rank_in(lists, p["a"], p["b"]), rank_in(lists, p["b"], p["a"])) if x]
        if ranks:
            row["stored"] += 1
            row["refs"].append(f"{p['a']}/{p['b']} rank {min(ranks)}")
            if min(ranks) <= 3:
                row["top3"] += 1

    neg_top3 = sum(v["top3"] for v in neg.values())
    n = len(positives)

    # The second sample: stored or not (either direction, verbatim class included),
    # and the stage where a pair stopped.
    v2 = {"positive": {"pairs": 0, "stored": 0, "refs": []},
          "negative": {"pairs": 0, "stored": 0, "refs": []}}
    v2_stages: dict[str, Counter] = {"positive": Counter(), "negative": Counter()}
    for p in second:
        kind = "positive" if p["label"] == "positive" else "negative"
        row = v2[kind]
        row["pairs"] += 1
        # Positives are credited as T1 credits them (verbatim class included);
        # negatives are counted as T2 counts them (the pair itself listed).
        if kind == "positive":
            rank = best_rank(lists, p["a"], p["b"], words)
        else:
            ranks = [x for x in (rank_in(lists, p["a"], p["b"]), rank_in(lists, p["b"], p["a"])) if x]
            rank = min(ranks) if ranks else None
        v2_stages[kind][diag_of(p).get("stage", "unknown") if rank is None else "stored"] += 1
        if rank is not None:
            row["stored"] += 1
            row["refs"].append(f"{p['a']}/{p['b']} rank {rank}")
    neg_cap = None if V2_BASELINE_NEG_STORED is None else V2_BASELINE_NEG_STORED / 2
    pos_floor = None if V2_BASELINE_POS_STORED is None else 0.8 * V2_BASELINE_POS_STORED
    return {
        "K": k,
        "positives": n,
        "recalled": recalled,
        "recall": recalled / n if n else 0.0,
        "lost_by_stage": dict(stage_loss),
        "candidate_loss": candidate_loss,
        "prefilter_loss": prefilter_loss,
        "negatives": {kind: dict(v) for kind, v in sorted(neg.items())},
        "negatives_in_top3": neg_top3,
        "positive_rows": pos_rows,
        "second_sample": {kind: {**v, "stages": dict(v2_stages[kind])} for kind, v in v2.items()},
        "candidate_loss_ok": (candidate_loss / n if n else 0.0) <= TARGET_CANDIDATE_LOSS,
        "targets": {
            "T1 recall": (recalled / n if n else 0.0) >= TARGET_RECALL,
            "T2 neg_top3": neg_top3 <= TARGET_NEG_TOP3,
            "T3 v2 negatives": None if neg_cap is None else v2["negative"]["stored"] <= neg_cap,
            "T4 v2 positives": None if pos_floor is None else v2["positive"]["stored"] >= pos_floor,
            "T5 prefilter_loss": prefilter_loss == TARGET_PREFILTER_LOSS,
        },
    }


def verbatim_words() -> dict[tuple[int, int], tuple[str, ...]]:
    return qac.ayah_words()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args(argv)

    if not GOLD_JSON.exists():
        sys.exit(f"Gold set not found at {GOLD_JSON} (local-only, under tests/eval/).")
    raw = GOLD_JSON.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        data = loaders.quran_similarity()
    except (loaders.DatasetMissing, loaders.UnknownSchema) as exc:
        sys.exit(str(exc))
    frozen = data["build"].get("gold_sha256")
    if frozen != digest:
        sys.exit(f"Refusing to report: the gold file's sha256 is {digest}, but the dataset "
                 f"was frozen against {frozen}. A measurement on another gold set is not the "
                 f"pre-registered one — restore that file, or rebuild and record why.")
    if not data.get("diagnostics", {}).get("gold"):
        sys.exit("The dataset carries no gold diagnostics; rebuild it with the gold set present.")

    report = evaluate(data, json.loads(raw), verbatim_words())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    t = report["targets"]
    mark = lambda ok: "—" if ok is None else "PASS" if ok else "MISS"  # noqa: E731
    n = report["positives"]
    print(f"Gold sha256 {digest[:12]}… = header ✓   K = {report['K']}   scope = "
          f"{data['build'].get('scope')}")
    print(f"T1 recall@{report['K']} of first-sample positives: {report['recalled']}/{n} = "
          f"{report['recall']:.3f}  (target ≥ {TARGET_RECALL}) {mark(t['T1 recall'])}")
    print(f"   positives lost at candidate generation (syntax gate + cap): "
          f"{report['candidate_loss']}/{n} (first build's target ≤ {TARGET_CANDIDATE_LOSS:.0%}) "
          f"{mark(report['candidate_loss_ok'])}")
    print("   positives lost by stage: " + (", ".join(
        f"{s} {report['lost_by_stage'][s]}" for s in (*STAGES, "unknown")
        if report["lost_by_stage"].get(s)) or "none"))
    print(f"T2 first-sample negatives in a top-3 (either direction): {report['negatives_in_top3']} "
          f"(target ≤ {TARGET_NEG_TOP3}) {mark(t['T2 neg_top3'])}")
    for kind, v in report["negatives"].items():
        print(f"   {kind}: {v['stored']}/{v['pairs']} stored, {v['top3']} in a top-3"
              + (f" — {'; '.join(v['refs'])}" if v["refs"] else ""))
    v2 = report["second_sample"]
    print(f"T3 second-sample negatives stored: {v2['negative']['stored']}/{v2['negative']['pairs']} "
          f"(target ≤ half of the baseline {V2_BASELINE_NEG_STORED}) {mark(t['T3 v2 negatives'])}")
    print(f"T4 second-sample positives stored: {v2['positive']['stored']}/{v2['positive']['pairs']} "
          f"(target ≥ 80 % of the baseline {V2_BASELINE_POS_STORED}) {mark(t['T4 v2 positives'])}")
    for kind in ("positive", "negative"):
        st = v2[kind]["stages"]
        print(f"   {kind}s by stage: " + (", ".join(f"{k_} {st[k_]}" for k_ in sorted(st)) or "none")
              + (f" — stored: {'; '.join(v2[kind]['refs'])}" if v2[kind]["refs"] else ""))
    print(f"T5 positives lost at the pre-filters (length window + bag bound): "
          f"{report['prefilter_loss']} (target = 0) {mark(t['T5 prefilter_loss'])}")
    print("\nPositives (best rank either direction; stage where a miss was lost):")
    for row in report["positive_rows"]:
        sig = " ".join(f"{k}={row[k]}" for k in ("syn", "dense", "cov", "ce", "sem")
                       if row[k] is not None)
        print(f"  {row['ref']:>13}  rank {row['rank'] or '—':>2}  {row['stage']:<23} {sig}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
