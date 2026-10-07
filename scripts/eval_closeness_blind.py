#!/usr/bin/env python3
"""
eval_closeness_blind.py — measure the closeness relation on the BLIND sample.

The figure that counts for version 2 of `order-invariant-closeness` (design.md D9,
D10.3): the three gold sets were READ when version 2 was designed, so they are reported
as in-sample by their own eval scripts, and the comparable number is this one — a sample
drawn model-free and through no gate (`scripts/draw_closeness_blind_sample.py`, 60
cross-surah pairs sharing ≥ 3 content lemmas, 20 per `lex` bin), labelled in a fresh
context from the written definition and the two texts only, BEFORE the first version-2
build, and committed to `tests/eval/closeness_blind_v2.json` (local-only).

Reads that sample, `data/derived/quran_similarity.json` and
`data/derived/quran_close_verses.json` (through their loaders), and reports:

  * positives STORED — a positive counts as stored when the relation holds it in
    EITHER direction: listed as a neighbour in `quran_similarity.json` under either
    verse, or present as a pair in `quran_close_verses.json` (the union of the
    similarity pairs and the passages) — over the total positives;
  * negatives stored, over the total negatives, the same way;
  * the pre-registered targets, printed PASS / MISS: positives stored ≥ 0.65,
    negatives stored ≤ 0.25;
  * the same two figures per `lex` bin of the sample;
  * the per-pair table: ref, label, lex, where it is stored (`similarity` and/or
    `passage`, from the close-verses `from`), and its stored score (the close-verses
    `score`, else the similarity `s`).

A pair still unlabelled (`label: null`) is reported apart and enters no ratio; any
label other than `positive` / `negative` refuses the report (the file is a measurement,
a typo in it is not to be read around).

It REFUSES to report when the sample's sha256 differs from the `blind_sample_sha256`
BOTH dataset headers recorded at build time (the builds hash the file's bytes without
reading it), or when the close-verses file was not composed from the similarity file on
disk: a number measured on other files is not the pre-registered measurement.

Nothing is written, and nothing is tuned from what this prints (design.md D10.4).

`openspec/changes/short-verse-material` (task 1.3) adds a second sample, read with
`--sample tests/eval/closeness_blind_short.json` (drawn by
`scripts/draw_short_pair_blind_sample.py`): 40 short cross-surah pairs in two
STRATA, 1 shared content lemma / 2+. When the pairs carry a `stratum`, the figures
are reported per stratum instead of per `bin`, and the positives of the 1-lemma
stratum — dropped by the short-verse material rule by construction — are reported
apart as the rule's RECALL COST and enter no positives ratio (design.md D2); its
negatives count like every other. The short sample's sha256 is checked against
the headers' `blind_short_sha256` (the sample is recognised by its declared
`scope`, or by being the protocol's file), every other sample's against
`blind_sample_sha256`.

    python scripts/eval_closeness_blind.py
    python scripts/eval_closeness_blind.py --json      # machine-readable
    python scripts/eval_closeness_blind.py --sample tests/eval/closeness_blind_short.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quran_data import loaders, paths  # noqa: E402

BLIND_SAMPLE_JSON = ROOT / "tests" / "eval" / "closeness_blind_v2.json"
# The header key both builds write (build_quran_similarity.py, build_quran_close_verses.py).
HEADER_KEY = "blind_sample_sha256"
# short-verse-material D2: the short-pair sample, its declared scope, the header key both
# builds write for it, and the stratum whose positives are the rule's recall cost.
BLIND_SHORT_JSON = ROOT / "tests" / "eval" / "closeness_blind_short.json"
SHORT_SCOPE = "cross-surah-closeness-blind-short"
SHORT_HEADER_KEY = "blind_short_sha256"
RECALL_COST_STRATUM = "1"
POSITIVE, NEGATIVE = "positive", "negative"
LABELS = (POSITIVE, NEGATIVE)

# design.md D9 («On the BLIND sample … the figure that counts»), copied as numbers so a
# miss is printed as a miss.
TARGET_POSITIVES_STORED = 0.65
TARGET_NEGATIVES_STORED = 0.25


# ── refs and keys ─────────────────────────────────────────────────────────

def parse_ref(raw: str) -> tuple[int, int]:
    s, a = raw.split(":")
    return int(s), int(a)


def pair_key(a: str, b: str) -> tuple[str, str]:
    """The unordered pair as an ordered tuple, lower verse first (numerically)."""
    return (a, b) if parse_ref(a) <= parse_ref(b) else (b, a)


# ── the two relations, as sets of unordered pairs ─────────────────────────

def similarity_pairs(data: dict) -> dict[tuple[str, str], float]:
    """Every neighbour pair of `quran_similarity.json`, from either verse's list, with
    the higher of the two stored `s` should the sides ever disagree."""
    out: dict[tuple[str, str], float] = {}
    for ref, lst in data.get("neighbours", {}).items():
        for e in lst:
            key = pair_key(ref, e["r"])
            if key not in out or e["s"] > out[key]:
                out[key] = e["s"]
    return out


def close_verses_pairs(data: dict) -> dict[tuple[str, str], dict]:
    return {pair_key(p["a"], p["b"]): p for p in data.get("pairs", [])}


# ── digests ───────────────────────────────────────────────────────────────

def sha256_of(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def header_key_for(path: Path, sample: dict) -> str:
    """The header key a sample's digest is checked against: `SHORT_HEADER_KEY` for the
    short-pair sample (its declared `scope`, or the protocol's file itself),
    `HEADER_KEY` for every other."""
    if sample.get("scope") == SHORT_SCOPE or Path(path).resolve() == BLIND_SHORT_JSON.resolve():
        return SHORT_HEADER_KEY
    return HEADER_KEY


def digest_problems(digest: str, headers: dict[str, dict], key: str = HEADER_KEY) -> list[str]:
    """Every dataset whose header does not carry exactly `digest` under `key`.

    A header without the key (a build that never hashed the sample) is a problem, not a
    pass — nothing here is allowed to default to «fine».
    """
    problems = []
    for name, build in headers.items():
        recorded = (build or {}).get(key)
        if recorded is None:
            problems.append(f"{name}: its header carries no {key} — it was built "
                            f"without the blind sample on disk, or before it existed")
        elif recorded != digest:
            problems.append(f"{name}: its header recorded {key} = {recorded}, the "
                            f"sample on disk is {digest}")
    return problems


def consistency_problems(cv_build: dict, similarity_sha: str | None) -> list[str]:
    """The close-verses file must have been composed from the similarity file on disk."""
    recorded = ((cv_build or {}).get("inputs") or {}).get("quran_similarity")
    if recorded is None or recorded != similarity_sha:
        return [f"quran_close_verses: its header's inputs.quran_similarity is {recorded}, "
                f"the similarity file on disk is {similarity_sha} — the two datasets were "
                f"not built as a pair"]
    return []


# ── the report ────────────────────────────────────────────────────────────

def _ratio(stored: int, total: int) -> float | None:
    return None if total == 0 else stored / total


def evaluate(sample: dict, sim_data: dict, cv_data: dict) -> dict:
    """The report, as data: per-pair rows in the sample's order, the two ratios, the
    targets (None when a class has no pair), the per-bin figures — per-stratum when the
    pairs carry a `stratum` —, the unlabelled, and the recall cost (the positives of
    `RECALL_COST_STRATUM`, outside the positives ratio; None for a sample without
    strata)."""
    sim = similarity_pairs(sim_data)
    cv = close_verses_pairs(cv_data)
    rows = []
    for p in sample["pairs"]:
        key = pair_key(p["a"], p["b"])
        ref = f"{p['a']}/{p['b']}"
        label = p.get("label")
        if label is not None and label not in LABELS:
            raise ValueError(f"{ref}: label {label!r} is neither {POSITIVE!r} nor "
                             f"{NEGATIVE!r} (nor null)")
        stored: list[str] = []
        if key in sim:
            stored.append("similarity")
        if key in cv:
            stored.extend(f for f in cv[key].get("from", []) if f not in stored)
        score = cv[key]["score"] if key in cv else sim.get(key)
        row = {"ref": ref, "label": label, "lex": p.get("lex"), "bin": p.get("bin"),
               "stored": stored, "score": score}
        if "stratum" in p:
            row["stratum"] = p["stratum"]
        rows.append(row)

    stratified = any("stratum" in r for r in rows)
    # design.md D2 (short-verse-material): the 1-lemma positives are the rule's recall
    # cost, reported apart; they enter no positives ratio.
    cost = [r for r in rows if stratified and r["label"] == POSITIVE
            and r.get("stratum") == RECALL_COST_STRATUM]

    def figure(label):
        mine = [r for r in rows if r["label"] == label and not any(r is c for c in cost)]
        n_stored = sum(1 for r in mine if r["stored"])
        return {"total": len(mine), "stored": n_stored, "ratio": _ratio(n_stored, len(mine))}

    pos, neg = figure(POSITIVE), figure(NEGATIVE)
    unlabelled = [r for r in rows if r["label"] is None]
    group_key = "stratum" if stratified else "bin"
    groups: dict[str, dict] = {}
    for r in rows:
        if r["label"] is None:
            continue
        b = groups.setdefault(r.get(group_key), {"positives": 0, "positives_stored": 0,
                                                 "negatives": 0, "negatives_stored": 0})
        side = "positives" if r["label"] == POSITIVE else "negatives"
        b[side] += 1
        b[f"{side}_stored"] += bool(r["stored"])
    report = {
        "pairs": len(rows),
        "positives": pos,
        "negatives": neg,
        "unlabelled": {"total": len(unlabelled),
                       "stored": sum(1 for r in unlabelled if r["stored"]),
                       "refs": [r["ref"] for r in unlabelled]},
        "strata" if stratified else "bins": {k: groups[k] for k in sorted(groups, key=str)},
        "recall_cost": None if not stratified else {
            "stratum": RECALL_COST_STRATUM, "positives": len(cost),
            "stored": sum(1 for r in cost if r["stored"]), "refs": [r["ref"] for r in cost]},
        "rows": rows,
        "targets": {
            "positives_stored": None if pos["ratio"] is None
            else pos["ratio"] >= TARGET_POSITIVES_STORED,
            "negatives_stored": None if neg["ratio"] is None
            else neg["ratio"] <= TARGET_NEGATIVES_STORED,
        },
    }
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--sample", type=Path, default=None,
                    help=f"the blind sample to measure on (default: {BLIND_SAMPLE_JSON}; "
                         f"the short-pair sample is {BLIND_SHORT_JSON})")
    args = ap.parse_args(argv)
    sample_path = BLIND_SAMPLE_JSON if args.sample is None else args.sample

    if not sample_path.exists():
        sys.exit(f"Blind sample not found at {sample_path} (local-only, under "
                 f"tests/eval/; drawn by scripts/draw_closeness_blind_sample.py or "
                 f"scripts/draw_short_pair_blind_sample.py).")
    raw = sample_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        sample = json.loads(raw)
    except ValueError as exc:
        sys.exit(f"Refusing to report: {sample_path} is not JSON ({exc})")
    key = header_key_for(sample_path, sample)
    try:
        sim_data = loaders.quran_similarity()
        cv_data = loaders.quran_close_verses()
    except (loaders.DatasetMissing, loaders.UnknownSchema) as exc:
        sys.exit(str(exc))
    problems = digest_problems(digest, {"quran_similarity": sim_data.get("build", {}),
                                        "quran_close_verses": cv_data.get("build", {})}, key)
    problems += consistency_problems(cv_data.get("build", {}),
                                     sha256_of(paths.QURAN_SIMILARITY_JSON))
    if problems:
        sys.exit("Refusing to report: the files on disk are not the ones the datasets were "
                 "built and frozen against —\n  " + "\n  ".join(problems) + "\nA measurement "
                 "on other files is not the pre-registered one: restore them, or rebuild in "
                 "order (build_quran_similarity.py → build_quran_passages.py → "
                 "build_quran_close_verses.py) and record why.")
    try:
        report = evaluate(sample, sim_data, cv_data)
    except ValueError as exc:
        sys.exit(f"Refusing to report: {exc}")
    report = {"sample": str(sample_path), "sha256": digest, "header_key": key, **report}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    t = report["targets"]
    mark = lambda ok: "—" if ok is None else "PASS" if ok else "MISS"  # noqa: E731
    fmt = lambda r: "—" if r is None else f"{r:.3f}"  # noqa: E731
    pos, neg, un = report["positives"], report["negatives"], report["unlabelled"]
    print(f"Blind sample {sample_path.name} sha256 {digest[:12]}… = both headers' {key} ✓   "
          f"pairs: {report['pairs']} (positives {pos['total']}, negatives {neg['total']}, "
          f"unlabelled {un['total']})")
    print(f"positives stored (either direction): {pos['stored']}/{pos['total']} = "
          f"{fmt(pos['ratio'])}  (target ≥ {TARGET_POSITIVES_STORED}) "
          f"{mark(t['positives_stored'])}")
    print(f"negatives stored: {neg['stored']}/{neg['total']} = {fmt(neg['ratio'])}  "
          f"(target ≤ {TARGET_NEGATIVES_STORED}) {mark(t['negatives_stored'])}")
    if un["total"]:
        print(f"unlabelled, in no ratio: {un['total']} ({un['stored']} stored) — "
              f"{', '.join(un['refs'])}")
    cost = report["recall_cost"]
    if cost is not None:
        print(f"recall cost of the rule (stratum {cost['stratum']} positives, in no ratio): "
              f"{cost['positives']} ({cost['stored']} stored)"
              + (f" — {', '.join(cost['refs'])}" if cost["refs"] else ""))
    groups, name = ((report["strata"], "stratum") if "strata" in report
                    else (report["bins"], "lex"))
    for b, v in groups.items():
        print(f"  {name} {b}: positives stored {v['positives_stored']}/{v['positives']}, "
              f"negatives stored {v['negatives_stored']}/{v['negatives']}")
    print(f"{'ref':<14}{'label':<10}{'lex':>7}  {'stored':<22}score")
    for r in report["rows"]:
        print(f"{r['ref']:<14}{(r['label'] or 'unlabelled'):<10}"
              f"{('—' if r['lex'] is None else f'{r['lex']:.3f}'):>7}  "
              f"{(', '.join(r['stored']) or '—'):<22}"
              f"{'—' if r['score'] is None else r['score']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
