#!/usr/bin/env python3
"""
eval_quran_close_verses.py — measure the unified cross-surah relation against both gold sets.

Reads `data/derived/quran_close_verses.json` (through its loader), the two gold sets
`tests/eval/quran_similarity_gold.json` and `tests/eval/quran_passages_gold.json`
(local-only; relabelled under `order-invariant-closeness` D10, which read them first —
so every figure here is IN-SAMPLE for version 2, and the figure that counts is
`scripts/eval_closeness_blind.py`'s), and reports, against the targets pre-registered
in `openspec/changes/unify-close-verses/design.md` D10:

  * the gold positives present, per gold sample (similarity first sample, similarity
    second sample `v2-syntax-survivors`, passages), the negatives present per kind, and
    `neg_same_subject_diff_syntax` APART — it enters no target;
  * the AUC of `score`, of `sim` and of `pas` over the positives present against the
    negatives present (ties count ½), each with its counts;
  * U1 — AUC(score) ≥ 0.80;
  * U2 — 28:20/36:20 present with `pas > 0`, its common part ONE run per verse reading
    «وَجَاءَ … قَالَ» (the character spans sliced out of each verse's DISPLAYED text);
  * U3 — 26:203/37:54 with `pas = 0`, in the lower half of cell (26, 37)'s list;
  * U4 — `len(pairs) = |S ∪ W|`, recomputed from the two input datasets.

Unified labels (D10): a positive of either gold file is a positive; a negative is a
`neg_same_syntax_diff_subject` / `neg_diff_subject_diff_syntax` pair of the similarity
gold or a `neg_scattered` / `neg_short_formula` pair of the passage gold. A pair held by
both files counts once; `neg_same_subject_diff_syntax` yields to the other file's label.
A pair one file calls positive and the other negative is BOTH — D10 adds no exception,
and its pre-registered counts (51 / 60 positives of the first similarity sample, 7
negatives including the 2 `neg_short_formula` pairs reached through S) include the two
such pairs on both sides. It is listed as a conflict for the reader, and in the AUC its
comparison with itself is a tie (½).

It REFUSES to report when either gold file's sha256, or either input dataset's sha256,
differs from the one the header recorded: a number measured on other files is not the
pre-registered measurement.

    python scripts/eval_quran_close_verses.py
    python scripts/eval_quran_close_verses.py --json      # machine-readable
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

from arabic_text import bare  # noqa: E402
from quran_data import loaders, paths  # noqa: E402
from quran_data.corpus import chakl_by_ref, strip_leading_basmala  # noqa: E402

SIMILARITY_GOLD = ROOT / "tests" / "eval" / "quran_similarity_gold.json"
PASSAGES_GOLD = ROOT / "tests" / "eval" / "quran_passages_gold.json"

V2_SAMPLE = "v2-syntax-survivors"
MOTIVATING = ("28:20", "36:20")
FRAME_ONLY = ("26:203", "37:54")
FRAME_CELL = (26, 37)

POSITIVE = "positive"
NEGATIVE_KINDS = {
    "similarity": ("neg_same_syntax_diff_subject", "neg_diff_subject_diff_syntax"),
    "passages": ("neg_scattered", "neg_short_formula"),
}
APART_KIND = "neg_same_subject_diff_syntax"

# design.md D10, copied as numbers so a miss is printed as a miss.
TARGET_AUC = 0.80                  # U1
U2_START = "وَجَاءَ"               # U2: the common part starts with this in both verses…
U2_END = "قَالَ"                   # …and ends with this, compared under `bare()`


# ── refs and keys ─────────────────────────────────────────────────────────

def parse_ref(raw: str) -> tuple[int, int]:
    s, a = raw.split(":")
    return int(s), int(a)


def pair_key(a: str, b: str) -> tuple[str, str]:
    """The unordered pair as an ordered tuple, lower verse first (numerically)."""
    return (a, b) if parse_ref(a) <= parse_ref(b) else (b, a)


def _ordered(keys) -> list[tuple[str, str]]:
    return sorted(keys, key=lambda k: (parse_ref(k[0]), parse_ref(k[1])))


# ── digests ───────────────────────────────────────────────────────────────

def sha256_of(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def digest_problems(build: dict, actual: dict[str, dict[str, str | None]]) -> list[str]:
    """Every mismatch between the header's digests and the files on disk.

    `actual` mirrors the header layout: `{"inputs": {name: sha}, "gold": {name: sha}}`.
    A missing header entry or a missing file is a mismatch too — nothing here is
    allowed to default to «fine».
    """
    problems = []
    for section, names in (("inputs", ("quran_similarity", "quran_passages")),
                           ("gold", ("quran_similarity_gold", "quran_passages_gold"))):
        recorded = (build.get(section) or {})
        for name in names:
            want, got = recorded.get(name), actual.get(section, {}).get(name)
            if got is None:
                problems.append(f"{section}.{name}: the file is missing on disk")
            elif want != got:
                problems.append(f"{section}.{name}: sha256 on disk is {got}, the header "
                                f"recorded {want}")
    return problems


# ── labels ────────────────────────────────────────────────────────────────

def label_class(source: str, label: str) -> str | None:
    """`"positive"`, `"negative"`, `"apart"`, or None for a label D10 does not name."""
    if label == POSITIVE:
        return "positive"
    if label in NEGATIVE_KINDS[source]:
        return "negative"
    if source == "similarity" and label == APART_KIND:
        return "apart"
    return None


def sample_of(source: str, pair: dict) -> str:
    if source == "passages":
        return "passages"
    return "similarity v2" if pair.get("sample") == V2_SAMPLE else "similarity v1"


def unify_labels(sim_gold: dict, pas_gold: dict) -> dict:
    """The unified labels of D10.

    Returns `{"labels": {key: {"classes", "kinds", "samples"}}, "conflicts": [...]}`,
    one entry per unordered pair whichever files label it (kinds and samples merged).
    `apart` yields to any positive or negative label of the same pair. A pair labelled
    positive by one file and negative by the other keeps BOTH classes — it is a
    positive AND a negative, exactly as D10's definitions read and as its pre-registered
    counts were computed — and is also listed under `conflicts` so the report shows it.
    """
    seen: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    for source, gold in (("similarity", sim_gold), ("passages", pas_gold)):
        for p in gold["pairs"]:
            cls = label_class(source, p["label"])
            if cls is None:
                continue
            seen[pair_key(p["a"], p["b"])].append((cls, p["label"], sample_of(source, p)))
    labels, conflicts = {}, []
    for key in _ordered(seen):
        rows = seen[key]
        # `apart` is no target label: a positive or negative of the other file wins
        # over it («a same-subject pair that shares a passage is not a miss», D10).
        targeted = [r for r in rows if r[0] != "apart"]
        rows = targeted or rows
        classes = sorted({r[0] for r in rows})
        if len(classes) > 1:
            conflicts.append({"pair": f"{key[0]}/{key[1]}",
                              "labels": [f"{r[2]}: {r[1]}" for r in rows]})
        labels[key] = {"classes": classes,
                       "kinds": sorted({r[1] for r in rows}),
                       "samples": sorted({r[2] for r in rows})}
    return {"labels": labels, "conflicts": conflicts}


# ── measures ──────────────────────────────────────────────────────────────

def auc(pos: list[float], neg: list[float]) -> float | None:
    """P(a positive outscores a negative), ties ½; None when either side is empty."""
    if not pos or not neg:
        return None
    total = 0.0
    for x in pos:
        for y in neg:
            total += 1.0 if x > y else 0.5 if x == y else 0.0
    return total / (len(pos) * len(neg))


def cell_rank(pairs: list[dict], cell: tuple[int, int], key: tuple[str, str]
              ) -> tuple[int | None, int]:
    """1-based rank of `key` in the cell's list (score desc, then `(a, b)`), and its size."""
    lo, hi = sorted(cell)
    members = [p for p in pairs if parse_ref(p["a"])[0] == lo and parse_ref(p["b"])[0] == hi]
    members.sort(key=lambda p: (-p["score"], parse_ref(p["a"]), parse_ref(p["b"])))
    for i, p in enumerate(members, 1):
        if pair_key(p["a"], p["b"]) == key:
            return i, len(members)
    return None, len(members)


def in_lower_half(rank: int | None, n: int) -> bool:
    """U3's rule: the pair ranks strictly past the middle of its cell (rank > n / 2)."""
    return rank is not None and rank > n / 2


def input_union(similarity: dict, passages: dict) -> set[tuple[str, str]]:
    """|S ∪ W| as D1 defines it: every stored neighbour pair, plus every passage pair."""
    keys = set()
    for ref, lst in similarity.get("neighbours", {}).items():
        for e in lst:
            keys.add(pair_key(ref, e["r"]))
    for p in passages.get("passages", []):
        keys.add(pair_key(p["a"], p["b"]))
    return keys


def common_part_reads(text_a: str, text_b: str, pair: dict) -> dict:
    """U2's check: ONE run per verse, starting with «وَجَاءَ» and ending with «قَالَ» under `bare()`.

    Schema 2 stores `ca` / `cb` as lists of half-open spans, one per run of coloured
    words (order-invariant-common-words D5); the slice shown is the first run's start
    to the last run's end, and the passage must be a single run in each verse.
    """
    if not all(pair.get(f) for f in ("ca", "cb")):
        return {"slice_a": None, "slice_b": None, "runs": None, "ok": False}
    ca, cb = pair["ca"], pair["cb"]
    sa = text_a[ca[0][0]:ca[-1][1]]
    sb = text_b[cb[0][0]:cb[-1][1]]
    start, end = bare(U2_START), bare(U2_END)
    ok = len(ca) == 1 and len(cb) == 1 and all(
        bare(s).strip().startswith(start) and bare(s).strip().endswith(end) for s in (sa, sb))
    return {"slice_a": sa, "slice_b": sb, "runs": [len(ca), len(cb)], "ok": ok}


def displayed_text(ref: str) -> str:
    """The verse's `text_ar_tashkil` as the API serves it (Basmala stripped)."""
    s, a = parse_ref(ref)
    row = chakl_by_ref().get((s, a))
    return "" if row is None else strip_leading_basmala(s, a, row["text"])


def dense_check_record(build: dict) -> dict | None:
    """Whatever the header records about D2's dense integrity check, if anything."""
    found = {k: v for k, v in build.items() if "dense_check" in k}
    return found or None


# ── report ────────────────────────────────────────────────────────────────

def evaluate(data: dict, sim_gold: dict, pas_gold: dict, union: set, texts=displayed_text
             ) -> dict:
    pairs = data.get("pairs", [])
    stored = {pair_key(p["a"], p["b"]): p for p in pairs}

    # Per gold file, before unification: the figures D10 states in advance.
    per_sample = defaultdict(lambda: {"pairs": 0, "present": 0})
    per_kind = defaultdict(lambda: {"pairs": 0, "present": 0, "refs": []})
    for source, gold in (("similarity", sim_gold), ("passages", pas_gold)):
        for p in gold["pairs"]:
            cls = label_class(source, p["label"])
            hit = stored.get(pair_key(p["a"], p["b"]))
            if cls == "positive":
                row = per_sample[sample_of(source, p)]
            elif cls in ("negative", "apart"):
                row = per_kind[p["label"]]
                if hit is not None:
                    row["refs"].append(f"{p['a']}/{p['b']} score={hit['score']}")
            else:
                continue
            row["pairs"] += 1
            row["present"] += hit is not None

    unified = unify_labels(sim_gold, pas_gold)
    pos = [stored[k] for k, v in unified["labels"].items()
           if "positive" in v["classes"] and k in stored]
    neg = [stored[k] for k, v in unified["labels"].items()
           if "negative" in v["classes"] and k in stored]
    aucs = {m: auc([p[m] for p in pos], [p[m] for p in neg]) for m in ("score", "sim", "pas")}

    mkey = pair_key(*MOTIVATING)
    m = stored.get(mkey)
    reads = None if m is None else common_part_reads(texts(mkey[0]), texts(mkey[1]), m)
    u2 = m is not None and m["pas"] > 0 and reads["ok"]

    fkey = pair_key(*FRAME_ONLY)
    f = stored.get(fkey)
    rank, n_cell = cell_rank(pairs, FRAME_CELL, fkey)
    u3 = f is not None and f["pas"] == 0 and in_lower_half(rank, n_cell)

    stored_keys = set(stored)
    dense = dense_check_record(data.get("build", {}))
    # Equal sets AND equal lengths: together they also rule out a pair stored twice.
    u4 = len(pairs) == len(union) and stored_keys == union
    if dense is not None:
        # Recorded in whatever form the build chose: only an explicit failure fails U4.
        u4 = u4 and not any(v is False or v in ("fail", "failed") for v in dense.values())

    return {
        "pairs": len(pairs),
        "positives_present": {s: dict(v) for s, v in sorted(per_sample.items())},
        "negatives_present": {k: dict(v) for k, v in sorted(per_kind.items())
                              if k != APART_KIND},
        "apart": dict(per_kind.get(APART_KIND, {"pairs": 0, "present": 0, "refs": []})),
        "conflicts": unified["conflicts"],
        "auc": {mname: {"auc": a, "positives": len(pos), "negatives": len(neg)}
                for mname, a in aucs.items()},
        "motivating": None if m is None else {
            "pair": f"{mkey[0]}/{mkey[1]}", "score": m["score"], "sim": m["sim"],
            "pas": m["pas"], "k": m.get("k"), **reads},
        "frame_only": {"pair": f"{fkey[0]}/{fkey[1]}", "present": f is not None,
                       "pas": None if f is None else f["pas"],
                       "score": None if f is None else f["score"],
                       "rank": rank, "cell_size": n_cell},
        "union": {"inputs": len(union), "stored": len(pairs),
                  "missing": [f"{a}/{b}" for a, b in _ordered(union - stored_keys)][:20],
                  "extra": [f"{a}/{b}" for a, b in _ordered(stored_keys - union)][:20],
                  "dense_check": dense},
        "targets": {
            "U1 AUC(score)": None if aucs["score"] is None else aucs["score"] >= TARGET_AUC,
            "U2 28:20/36:20": u2,
            "U3 26:203/37:54": u3,
            "U4 integrity": u4,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args(argv)

    for gold in (SIMILARITY_GOLD, PASSAGES_GOLD):
        if not gold.exists():
            sys.exit(f"Gold set not found at {gold} (local-only, under tests/eval/).")
    try:
        data = loaders.quran_close_verses()
    except (loaders.DatasetMissing, loaders.UnknownSchema) as exc:
        sys.exit(str(exc))
    actual = {
        "inputs": {"quran_similarity": sha256_of(paths.QURAN_SIMILARITY_JSON),
                   "quran_passages": sha256_of(paths.QURAN_PASSAGES_JSON)},
        "gold": {"quran_similarity_gold": sha256_of(SIMILARITY_GOLD),
                 "quran_passages_gold": sha256_of(PASSAGES_GOLD)},
    }
    problems = digest_problems(data.get("build", {}), actual)
    if problems:
        sys.exit("Refusing to report: the files on disk are not the ones the dataset was built "
                 "and frozen against —\n  " + "\n  ".join(problems) + "\nA measurement on other "
                 "files is not the pre-registered one: restore them, or rebuild in order "
                 "(build_quran_similarity.py → build_quran_passages.py → "
                 "build_quran_close_verses.py) and record why.")
    try:
        similarity, passages = loaders.quran_similarity(), loaders.quran_passages()
    except (loaders.DatasetMissing, loaders.UnknownSchema) as exc:
        sys.exit(str(exc))

    report = evaluate(data, json.loads(SIMILARITY_GOLD.read_bytes()),
                      json.loads(PASSAGES_GOLD.read_bytes()), input_union(similarity, passages))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    t = report["targets"]
    mark = lambda ok: "—" if ok is None else "PASS" if ok else "MISS"  # noqa: E731
    print(f"Digests = header ✓ (2 inputs, 2 gold)   pairs stored: {report['pairs']}")
    print("Positives present (reported, not a target):")
    for s, v in report["positives_present"].items():
        print(f"  {s}: {v['present']}/{v['pairs']}")
    print("Negatives present (reported, not a target):")
    for kind, v in report["negatives_present"].items():
        print(f"  {kind}: {v['present']}/{v['pairs']}"
              + (f" — {'; '.join(v['refs'])}" if v["refs"] else ""))
    a = report["apart"]
    print(f"Apart, in no target — {APART_KIND}: {a['present']}/{a['pairs']} present"
          + (f" — {'; '.join(a['refs'])}" if a["refs"] else ""))
    if report["conflicts"]:
        print("Label conflicts between the gold files (counted as a positive AND a negative, D10):")
        for c in report["conflicts"]:
            print(f"  {c['pair']}: {'; '.join(c['labels'])}")
    for mname in ("score", "sim", "pas"):
        r = report["auc"][mname]
        val = "—" if r["auc"] is None else f"{r['auc']:.3f}"
        print(f"AUC({mname}) = {val}  on {r['positives']} positives × {r['negatives']} negatives")
    print(f"U1 AUC(score) ≥ {TARGET_AUC}: {mark(t['U1 AUC(score)'])}")
    m = report["motivating"]
    if m is None:
        print(f"U2 {'/'.join(MOTIVATING)}: NOT present {mark(t['U2 28:20/36:20'])}")
    else:
        print(f"U2 {m['pair']}: score {m['score']}, sim {m['sim']}, pas {m['pas']}, k {m['k']} "
              f"{mark(t['U2 28:20/36:20'])}")
        print(f"   common part in {MOTIVATING[0]}: {m['slice_a'] or '—'}")
        print(f"   common part in {MOTIVATING[1]}: {m['slice_b'] or '—'}")
    f = report["frame_only"]
    print(f"U3 {f['pair']}: " + (f"pas {f['pas']}, score {f['score']}, rank {f['rank']} of "
                                 f"{f['cell_size']} in cell {FRAME_CELL}" if f["present"]
                                 else "NOT present") + f" {mark(t['U3 26:203/37:54'])}")
    u = report["union"]
    dense = ("not recorded in the header — U4 is the union count only (the build refuses to "
             "write when the D2 check fails)" if u["dense_check"] is None
             else f"header records {u['dense_check']}")
    print(f"U4 pairs stored {u['stored']} vs |S ∪ W| = {u['inputs']}; dense check: {dense} "
          f"{mark(t['U4 integrity'])}")
    if u["missing"] or u["extra"]:
        print(f"   missing (first 20): {', '.join(u['missing']) or 'none'}")
        print(f"   extra (first 20): {', '.join(u['extra']) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
