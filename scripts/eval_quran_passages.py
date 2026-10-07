#!/usr/bin/env python3
"""
eval_quran_passages.py — measure the shared-passage build against its gold set.

Reads `data/derived/quran_passages.json` (through its loader) and the gold set
`tests/eval/quran_passages_gold.json` (local-only; relabelled under
`order-invariant-closeness` D10, which read it first — so this figure is IN-SAMPLE for
version 2, and the figure that counts is `scripts/eval_closeness_blind.py`'s), and
reports, against the targets pre-registered in
`openspec/changes/add-shared-passages/design.md` D8 and
`openspec/changes/order-invariant-closeness/design.md` D9:

  * recall of the positives — a positive `(a, b)` is found iff the dataset holds a
    passage for that unordered pair;
  * the negatives of each kind found;
  * 28:20/36:20, the pair that motivated add-shared-passages, reported apart;
  * 2:3/14:31, the pair that motivated order-invariant-closeness (a word moved
    across the passage), reported apart.

It REFUSES to report when the gold file's sha256 differs from the one the dataset
header was frozen against: a number measured on another gold set is not the
pre-registered measurement.

    python scripts/eval_quran_passages.py
    python scripts/eval_quran_passages.py --json      # machine-readable
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quran_data import loaders  # noqa: E402

GOLD_JSON = ROOT / "tests" / "eval" / "quran_passages_gold.json"
MOTIVATING = ("28:20", "36:20")
MOVED = ("2:3", "14:31")           # order-invariant-closeness D9

# design.md D8, copied as numbers so a miss is printed as a miss.
TARGET_RECALL = 0.80
TARGET_NEG_SHARE = 0.10


def _key(a: str, b: str) -> frozenset:
    return frozenset((a, b))


def evaluate(data: dict, gold: dict) -> dict:
    found = {_key(p["a"], p["b"]): p for p in data.get("passages", [])}
    positives = [p for p in gold["pairs"] if p["label"] == "positive"]
    pos_rows = []
    for p in positives:
        hit = found.get(_key(p["a"], p["b"]))
        pos_rows.append({"ref": f"{p['a']}/{p['b']}", "found": hit is not None,
                         "k": None if hit is None else hit["k"]})
    recalled = sum(r["found"] for r in pos_rows)
    neg = defaultdict(lambda: {"pairs": 0, "found": 0, "refs": []})
    for p in gold["pairs"]:
        if p["label"] == "positive":
            continue
        row = neg[p["label"]]
        row["pairs"] += 1
        hit = found.get(_key(p["a"], p["b"]))
        if hit is not None:
            row["found"] += 1
            row["refs"].append(f"{p['a']}/{p['b']} k={hit['k']}")
    n_neg = sum(v["pairs"] for v in neg.values())
    neg_found = sum(v["found"] for v in neg.values())
    n = len(positives)
    motivating = found.get(_key(*MOTIVATING))
    moved = found.get(_key(*MOVED))
    return {
        "positives": n,
        "recalled": recalled,
        "recall": recalled / n if n else 0.0,
        "negatives": {kind: dict(v) for kind, v in sorted(neg.items())},
        "negatives_found": neg_found,
        "negatives_total": n_neg,
        "motivating": None if motivating is None else
        {"wa": motivating["wa"], "wb": motivating["wb"], "k": motivating["k"]},
        "moved": None if moved is None else
        {"wa": moved["wa"], "wb": moved["wb"], "k": moved["k"]},
        "positive_rows": pos_rows,
        "targets": {
            "recall": (recalled / n if n else 0.0) >= TARGET_RECALL,
            "negatives": neg_found <= TARGET_NEG_SHARE * n_neg,
            "motivating": motivating is not None,
            "moved": moved is not None,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args(argv)

    if not GOLD_JSON.exists():
        sys.exit(f"Gold set not found at {GOLD_JSON} (local-only, under tests/eval/).")
    raw = GOLD_JSON.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        data = loaders.quran_passages()
    except (loaders.DatasetMissing, loaders.UnknownSchema) as exc:
        sys.exit(str(exc))
    frozen = data["build"].get("gold_sha256")
    if frozen != digest:
        sys.exit(f"Refusing to report: the gold file's sha256 is {digest}, but the dataset "
                 f"was frozen against {frozen}. A measurement on another gold set is not the "
                 f"pre-registered one — restore that file, or rebuild and record why.")

    report = evaluate(data, json.loads(raw))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    t = report["targets"]
    mark = lambda ok: "PASS" if ok else "MISS"  # noqa: E731
    print(f"Gold sha256 {digest[:12]}… = header ✓   passages stored: {len(data['passages'])}")
    print(f"recall of positives: {report['recalled']}/{report['positives']} = "
          f"{report['recall']:.3f}  (target ≥ {TARGET_RECALL}) {mark(t['recall'])}")
    print(f"negatives found: {report['negatives_found']}/{report['negatives_total']} "
          f"(target ≤ {TARGET_NEG_SHARE:.0%}) {mark(t['negatives'])}")
    for kind, v in report["negatives"].items():
        print(f"  {kind}: {v['found']}/{v['pairs']} found"
              + (f" — {'; '.join(v['refs'])}" if v["refs"] else ""))
    m = report["motivating"]
    print(f"28:20/36:20: " + ("found, " + f"words {m['wa']} / {m['wb']}, k = {m['k']}" if m
                               else "NOT found") + f" {mark(t['motivating'])}")
    m = report["moved"]
    print(f"2:3/14:31: " + ("found, " + f"words {m['wa']} / {m['wb']}, k = {m['k']}" if m
                             else "NOT found") + f" {mark(t['moved'])}")
    missed = [r["ref"] for r in report["positive_rows"] if not r["found"]]
    print("positives missed: " + (", ".join(missed) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
