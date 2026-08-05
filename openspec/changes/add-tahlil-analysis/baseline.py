"""
baseline.py — Grounding-availability sweep for the Tahlil page, run BEFORE the proposal.

Tahlil is *cite-or-omit*: an assertion ships only when it points at a letter entry, a
naẓīr, a form-KB row, or a Maqāyīs aṣl. So the question that decides the shape of the
feature is not "can the model write it" but **"for how many words does the evidence
exist at all"** — measured per block, on the real on-disk corpus, before any code.

Blocks measured (the five of the page):
  1. الحروف  — every root letter present in the Hasan Abbas dataset (+ the هـ/ه key gap)
  2. صرفي    — mīzān `verified`, باب, and an attested same-root contrast lemma («أبلغ من X»)
  3. نحوي    — iʿrāب composed, head_ref present (the Zero relation is a *dependency*, not
               yet on disk — reported as 0 with the target from add-nahwi-zero-relations)
  4. دلالي   — Maqāyīs aṣl for the root, and same-lemma naẓāʾir as empirical evidence
  5. تركيب   — words where ALL FOUR blocks carry at least one grounded fact

Pure stdlib + the on-disk artifacts (no ML, no network, no Qdrant). The full corpus runs
in ~1 min, so every one of the 77 429 words is measured — no sampling.

Usage:
    python openspec/changes/add-tahlil-analysis/baseline.py            # summary
    python openspec/changes/add-tahlil-analysis/baseline.py --dump     # + coverage TSV
"""
from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis import mizan  # noqa: E402
from analysis.qlisan_data import qac_syntax, qac_words, root_graph  # noqa: E402

HERE = Path(__file__).resolve().parent
LETTERS_JSON = ROOT / "data" / "references" / "arabic_letter_semantics_hasan_abbas.json"
MAQAYIS_CSV = ROOT / "data" / "references" / "maqayis_asl.csv"


def load_letters() -> tuple[dict[str, dict], dict[str, dict]]:
    """(as-keyed, normalized) letter tables. The dataset keys ه as «هـ» (two chars);
    root keys use the bare «ه» — the normalized table folds it so the gap is measurable."""
    data = json.loads(LETTERS_JSON.read_text(encoding="utf-8"))["letters"]
    raw = {row["letter"]: row for row in data}
    norm = {row["letter"].replace("هـ", "ه"): row for row in data}
    return raw, norm


def load_maqayis() -> dict[str, str]:
    """normalized root -> asl_status (`has_asl` / `no_asl` / …)."""
    with MAQAYIS_CSV.open(encoding="utf-8") as f:
        return {r["root_normalized"]: r["asl_status"] for r in csv.DictReader(f)}


def main(dump: bool = False) -> None:
    raw_letters, norm_letters = load_letters()
    maqayis = load_maqayis()
    words = qac_words()
    syntax = qac_syntax()
    graph = root_graph()

    # Lemmas attested under each root — the source of the «أبلغ من X» contrast.
    lemmas_by_root: dict[str, set[str]] = collections.defaultdict(set)
    lemma_count: collections.Counter = collections.Counter()
    for ref, rec in words.items():
        r, l = rec.get("root"), rec.get("lemma")
        if r and l:
            lemmas_by_root[r].add(l)
            lemma_count[(r, l)] += 1

    total = len(words)
    rooted = [ref for ref, rec in words.items() if rec.get("root")]
    n_rooted = len(rooted)

    c: collections.Counter = collections.Counter()
    omit_reasons: collections.Counter = collections.Counter()
    rows: list[tuple] = []

    for ref in rooted:
        rec = words[ref]
        root = rec["root"]

        # ── block 1: الحروف ────────────────────────────────────────────────
        miss_raw = [ch for ch in root if ch not in raw_letters]
        miss_norm = [ch for ch in root if ch not in norm_letters]
        b1_raw = not miss_raw
        b1 = not miss_norm
        c["b1_letters_raw_keys"] += b1_raw
        c["b1_letters_normalized"] += b1
        if b1 and not b1_raw:
            c["b1_recovered_by_ha_fold"] += 1
        if not b1:
            omit_reasons["letter-absent-from-dataset:" + "".join(miss_norm)] += 1
        # position claims need position_notes on every letter
        c["b1_with_position_notes"] += b1 and all(
            (norm_letters[ch]["dalala_hasan_abbas"] or {}).get("position_notes")
            for ch in root
        )

        # ── block 2: صرفي ──────────────────────────────────────────────────
        m = mizan.compute_mizan(rec, ref)
        b2_wazn = bool(m.get("available") and m.get("verified"))
        c["b2_mizan_verified"] += b2_wazn
        c["b2_bab"] += bool(m.get("bab"))
        # a contrast lemma = another lemma of the same root attested in the Quran
        others = lemmas_by_root[root] - {rec.get("lemma")}
        b2_contrast = bool(others)
        c["b2_contrast_lemma"] += b2_contrast
        if not b2_contrast:
            omit_reasons["no-contrast-lemma-under-root"] += 1
        b2 = b2_wazn or bool(m.get("bab"))
        c["b2_any"] += b2

        # ── block 3: نحوي ──────────────────────────────────────────────────
        srec = syntax.get(ref)
        b3 = srec is not None and bool(srec.get("relation_ar"))
        c["b3_iraab"] += b3
        c["b3_head_ref"] += bool(srec and srec.get("head_ref"))
        if not b3:
            omit_reasons["absent-from-treebank"] += 1

        # ── block 4: دلالي ─────────────────────────────────────────────────
        b4_asl = maqayis.get(root) == "has_asl"
        c["b4_maqayis_asl"] += b4_asl
        same_lemma = lemma_count[(root, rec.get("lemma"))] - 1
        c["b4_nazair_same_lemma_ge1"] += same_lemma >= 1
        c["b4_nazair_same_lemma_ge3"] += same_lemma >= 3
        n_root_occ = len(graph.get(root, []))
        b4 = b4_asl or same_lemma >= 1
        c["b4_any"] += b4
        if not b4:
            omit_reasons["no-asl-and-no-nazir"] += 1

        # ── block 5: تركيب — all four blocks grounded ──────────────────────
        b5 = b1 and b2 and b3 and b4
        c["b5_all_four"] += b5

        if dump:
            rows.append(
                (ref, rec.get("uthmani", ""), root, rec.get("lemma", ""),
                 int(b1), int(b2), int(b3), int(b4), int(b5),
                 m.get("wazn") or "", m.get("bab") or "",
                 same_lemma, n_root_occ, int(b4_asl))
            )

    def pct(n: int) -> str:
        return f"{n:>6} / {n_rooted}  ({n / n_rooted:6.1%})"

    print(f"corpus            : {total} words, {n_rooted} rooted ({n_rooted/total:.1%}), "
          f"{len(graph)} roots, {len(syntax)} in treebank")
    print()
    print("block 1 الحروف")
    print("  all root letters in dataset (dataset keys as-is) :", pct(c["b1_letters_raw_keys"]))
    print("  all root letters in dataset (هـ→ه folded)        :", pct(c["b1_letters_normalized"]))
    print("  recovered by that one fold                       :", pct(c["b1_recovered_by_ha_fold"]))
    print("  every letter also carries position_notes         :", pct(c["b1_with_position_notes"]))
    print()
    print("block 2 صرفي")
    print("  mīzān verified                                   :", pct(c["b2_mizan_verified"]))
    print("  باب present                                       :", pct(c["b2_bab"]))
    print("  contrast lemma attested under the same root      :", pct(c["b2_contrast_lemma"]))
    print("  block grounded (wazn or bab)                     :", pct(c["b2_any"]))
    print()
    print("block 3 نحوي")
    print("  iʿrāb composable (in treebank, has relation)     :", pct(c["b3_iraab"]))
    print("  head_ref (المتعلَّق) present                        :", pct(c["b3_head_ref"]))
    print("  Zero relation (إسناد/تخصيص/إضافة/توضيح)          :      0  — dependency, not on disk")
    print()
    print("block 4 دلالي")
    print("  Maqāyīs aṣl for the root                         :", pct(c["b4_maqayis_asl"]))
    print("  ≥1 same-lemma naẓīr                              :", pct(c["b4_nazair_same_lemma_ge1"]))
    print("  ≥3 same-lemma naẓāʾir                            :", pct(c["b4_nazair_same_lemma_ge3"]))
    print("  block grounded (aṣl or naẓīr)                    :", pct(c["b4_any"]))
    print()
    print("block 5 تركيب")
    print("  all four blocks carry evidence                   :", pct(c["b5_all_four"]))
    print()
    print("omission reasons (top 12):")
    for reason, n in omit_reasons.most_common(12):
        print(f"  {n:>6}  {reason}")

    if dump:
        out = HERE / "baseline-coverage.tsv"
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["ref", "word", "root", "lemma", "b1_huruf", "b2_sarfi",
                        "b3_nahwi", "b4_dalali", "b5_all", "wazn", "bab",
                        "same_lemma_nazair", "root_occurrences", "has_asl"])
            w.writerows(rows)
        print(f"\nwrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main(dump="--dump" in sys.argv)
