#!/usr/bin/env python3
"""
eval_surah_similarity.py — measure the intra-surah similarity build against its gold set.

Reads `data/derived/surah_similarity.json` (through its loader) and the gold set
`tests/eval/surah_similarity_gold.json` (local-only), and reports, against the
target pre-registered in `openspec/changes/add-surah-similar-verses/tasks.md`
§1.3:

  * recall@K of the positives, under the pre-registered rule — `(a, b)` is
    recalled iff `b ∈ N(a)` or `a ∈ N(b)`; when `a` and `b` are verbatim
    identical, a neighbour verbatim identical to the other also counts;
  * the rank of each positive (best of the two directions);
  * the positives lost at each stage — unscored, syntax gate, candidate cap,
    semantic gate, shared-root rule, top-K — read from the per-gold-pair
    diagnostics the builder writes;
  * the negatives of each kind stored as neighbours, and how many appear in
    a top-3 (either direction).

It REFUSES to report when the gold file's sha256 differs from the one the
dataset header was frozen against: a number measured on another gold set is
not the pre-registered measurement.

    python scripts/eval_surah_similarity.py
    python scripts/eval_surah_similarity.py --json      # machine-readable
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

GOLD_JSON = ROOT / "tests" / "eval" / "surah_similarity_gold.json"
STAGES = ("unscored", "consecutive", "syntax_gate", "candidate_cap", "semantic_gate",
          "no_shared_root", "top_k", "stored")

# tasks.md §1.3, copied as numbers so a miss is printed as a miss.
TARGET_RECALL = 0.75
TARGET_CANDIDATE_LOSS = 0.15
TARGET_NEG_TOP3 = 2
TARGET_CONSECUTIVE_STORED = 0


def neighbour_lists(data: dict) -> dict[tuple[int, int], list[int]]:
    """`{(surah, ayah): [neighbour ayah, …]}` in stored (rank) order."""
    out: dict[tuple[int, int], list[int]] = {}
    for s, entry in data["surahs"].items():
        for a, lst in entry.get("neighbours", {}).items():
            out[(int(s), int(a))] = [int(e["a"]) for e in lst]
    return out


def rank_in(lists: dict, surah: int, a: int, b: int) -> int | None:
    """1-based position of `b` in `N(a)`, or None."""
    lst = lists.get((surah, a), [])
    return lst.index(b) + 1 if b in lst else None


def best_rank(lists: dict, surah: int, a: int, b: int, words: dict) -> int | None:
    """Best rank of the pair in either direction, verbatim class included."""
    ranks = [x for x in (rank_in(lists, surah, a, b), rank_in(lists, surah, b, a)) if x]
    if words.get((surah, a)) == words.get((surah, b)):
        for x, y in ((a, b), (b, a)):
            for i, n in enumerate(lists.get((surah, x), []), 1):
                if n != x and words.get((surah, n)) == words.get((surah, y)):
                    ranks.append(i)
                    break
    return min(ranks) if ranks else None


def evaluate(data: dict, gold: dict, words: dict) -> dict:
    lists = neighbour_lists(data)
    k = data["build"]["K"]
    diag = {(d["surah"], d["a"], d["b"]): d for d in data.get("diagnostics", {}).get("gold", [])}

    positives = [p for p in gold["pairs"] if p["label"] == "positive"]
    pos_rows = []
    for p in positives:
        rank = best_rank(lists, p["surah"], p["a"], p["b"], words)
        stage = diag.get((p["surah"], p["a"], p["b"]), {}).get("stage", "unknown")
        # A verbatim-class recall counts even when the pair itself was not stored.
        if rank is not None and stage != "stored":
            stage = "stored (verbatim class)"
        pos_rows.append({"ref": f"{p['surah']}:{p['a']}/{p['b']}", "rank": rank, "stage": stage,
                         **{key: diag.get((p["surah"], p["a"], p["b"]), {}).get(key)
                            for key in ("syn", "dense", "cov", "ce", "sem")}})
    recalled = sum(1 for r in pos_rows if r["rank"] is not None and r["rank"] <= k)
    stage_loss = Counter(r["stage"] for r in pos_rows if r["rank"] is None)
    candidate_loss = stage_loss.get("syntax_gate", 0) + stage_loss.get("candidate_cap", 0)

    neg = defaultdict(lambda: {"pairs": 0, "stored": 0, "top3": 0, "refs": []})
    for p in gold["pairs"]:
        if p["label"] == "positive":
            continue
        row = neg[p["label"]]
        row["pairs"] += 1
        ranks = [x for x in (rank_in(lists, p["surah"], p["a"], p["b"]),
                             rank_in(lists, p["surah"], p["b"], p["a"])) if x]
        if ranks:
            row["stored"] += 1
            row["refs"].append(f"{p['surah']}:{p['a']}/{p['b']} rank {min(ranks)}")
            if min(ranks) <= 3:
                row["top3"] += 1

    non_consec_top3 = sum(v["top3"] for kind, v in neg.items() if kind != "neg_consecutive")
    consec_stored = neg["neg_consecutive"]["stored"]
    n = len(positives)
    return {
        "K": k,
        "positives": n,
        "recalled": recalled,
        "recall": recalled / n if n else 0.0,
        "lost_by_stage": dict(stage_loss),
        "candidate_loss": candidate_loss,
        "negatives": {kind: dict(v) for kind, v in sorted(neg.items())},
        "non_consecutive_negatives_in_top3": non_consec_top3,
        "consecutive_negatives_stored": consec_stored,
        "positive_rows": pos_rows,
        "targets": {
            "recall": (recalled / n if n else 0.0) >= TARGET_RECALL,
            "candidate_loss": (candidate_loss / n if n else 0.0) <= TARGET_CANDIDATE_LOSS,
            "neg_top3": non_consec_top3 <= TARGET_NEG_TOP3,
            "consecutive_stored": consec_stored == TARGET_CONSECUTIVE_STORED,
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
        data = loaders.surah_similarity()
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
    mark = lambda ok: "PASS" if ok else "MISS"  # noqa: E731
    n = report["positives"]
    print(f"Gold sha256 {digest[:12]}… = header ✓   K = {report['K']}")
    print(f"recall@{report['K']} of positives: {report['recalled']}/{n} = {report['recall']:.3f}  "
          f"(target ≥ {TARGET_RECALL}) {mark(t['recall'])}")
    print(f"positives lost at candidate generation (syntax gate + cap): "
          f"{report['candidate_loss']}/{n} (target ≤ {TARGET_CANDIDATE_LOSS:.0%}) "
          f"{mark(t['candidate_loss'])}")
    print("positives lost by stage: " + (", ".join(
        f"{s} {report['lost_by_stage'][s]}" for s in (*STAGES, "unknown")
        if report["lost_by_stage"].get(s)) or "none"))
    print(f"non-consecutive negatives in a top-3: {report['non_consecutive_negatives_in_top3']} "
          f"(target ≤ {TARGET_NEG_TOP3}) {mark(t['neg_top3'])}")
    print(f"consecutive negatives stored: {report['consecutive_negatives_stored']} "
          f"(target = 0) {mark(t['consecutive_stored'])}")
    for kind, v in report["negatives"].items():
        print(f"  {kind}: {v['stored']}/{v['pairs']} stored, {v['top3']} in a top-3"
              + (f" — {'; '.join(v['refs'])}" if v["refs"] else ""))
    print("\nPositives (best rank either direction; stage where a miss was lost):")
    for row in report["positive_rows"]:
        sig = " ".join(f"{k}={row[k]}" for k in ("syn", "dense", "cov", "ce", "sem")
                       if row[k] is not None)
        print(f"  {row['ref']:>12}  rank {row['rank'] or '—':>2}  {row['stage']:<22} {sig}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
