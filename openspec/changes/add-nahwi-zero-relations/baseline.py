"""Proposal-time baseline for the Zero-theory relation layer.

Prototype of the mapper specified in `design.md`, run over the whole corpus to
produce the measured numbers in `proposal.md` and the triage log
`baseline-coverage.tsv`. This is a MEASUREMENT script, not the shipped module —
the real one lands at `analysis/zero_relations.py`.

Run: python openspec/changes/add-nahwi-zero-relations/baseline.py [out.tsv]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from analysis import qac_labels  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
syn: dict = json.loads((PROCESSED / "qac_syntax.json").read_text(encoding="utf-8"))
words: dict = json.loads((PROCESSED / "qac_words.json").read_text(encoding="utf-8"))

ISNAD, TAKHSIS, IDAFA, TAWDIH = "إسناد", "تخصيص", "إضافة", "توضيح"
FAMILY = {"NOM": ISNAD, "ACC": TAKHSIS, "GEN": IDAFA}

# تبعية relations — the تابع inherits its متبوع's case, so the case family cannot decide.
TABAIYA = {"Adj", "App", "conj", "emph"}
# POS that can bear a case, and so can be a relatum. A حرف never can.
NOMINAL_POS = {"N", "PN", "ADJ", "PRON", "REL", "DEM", "T", "LOC"}
# Relations naming a nominal slot: a preposition carrying one heads a شبه جملة
# standing in that slot, so the bare «أداة الإضافة» label would lie.
NOMINAL_SLOT = {"Subj", "Pass", "Pred", "Obj", "Poss", "Spec", "circ",
                "pred<<in>>", "subj<<in>>", "pred<<an>>", "subj<<an>>"}


def canonical_case(relation: str | None, relation_ar: str | None) -> str | None:
    """Case family for a QAC role — extends `relation_canonical_case` with `gen`.

    `relation_canonical_case` deliberately withholds «مجرور» because its display
    override already expresses the case; the Zero layer needs the family anyway.
    """
    if relation == "gen":
        return "GEN"
    return qac_labels.relation_canonical_case(relation_ar)


def classify(ref: str) -> tuple[str, str | None, str | None, str]:
    """-> (bucket, relation, role, reason_key); bucket ∈ relatum|marker|minted|omitted."""
    w = words.get(ref) or {}
    s = syn.get(ref)
    pos = w.get("pos", "")

    if s is None:  # absent from the treebank
        if pos == "CONJ":
            return "minted", TAWDIH, "أداة العطف", "minted-conj"
        return "omitted", None, None, f"absent-from-treebank:{pos}"

    relation = s.get("relation")
    relation_ar = s.get("relation_ar")
    case = (w.get("features") or {}).get("nominal_case")
    nominal = pos in NOMINAL_POS or bool(case)

    # 1. A verb is the pole of الإسناد — مسند, never cased, never a relatum.
    if pos == "V":
        return "marker", ISNAD, "مسند", "verb"

    # 2. تبعية → توضيح, decided by the relation itself (not by case).
    if relation in TABAIYA:
        if nominal:
            return "relatum", TAWDIH, "تابع", "tabaiya"
        if pos in ("CONJ", "REM", "SUP"):
            return "marker", TAWDIH, "أداة العطف", "harf-atf"
        return "omitted", None, None, f"tabi-non-nominal:{pos}:{relation_ar}"

    # 3. حرف جر = أداة الإضافة — unless it heads a nominal slot (guard 3).
    if pos == "P":
        if relation in NOMINAL_SLOT:
            return "omitted", None, None, f"prep-in-nominal-slot:{relation_ar}"
        return "marker", IDAFA, "أداة الإضافة", "harf-jarr"

    # 4. حرف نصب = أداة التخصيص.
    if pos == "ACC":
        return "marker", TAKHSIS, "أداة التخصيص", "harf-nasb"

    # 5. Relata only — a particle bears no case, so it can never be one (guard 1).
    if not nominal:
        return "omitted", None, None, f"non-nominal-pos:{pos}:{relation_ar}"

    cc = canonical_case(relation, relation_ar)
    if cc:
        if case and case != cc:  # QAC contradicts its own case tag
            return "omitted", None, None, f"case-conflict:{relation_ar}"
        if cc == "GEN":  # guard 2: direct إضافة vs إضافة بأداة
            role = "مضاف إليه" if relation == "Poss" else "مجرور بأداة الإضافة"
        elif cc == "ACC":
            role = "مخصِّص"
        else:
            role = "مسند" if (relation_ar or "").startswith("خبر") else "مسند إليه"
        return "relatum", FAMILY[cc], role, f"canonical:{relation_ar}"

    if case:  # relation bears no fixed case; the word's own case decides
        role = {"NOM": "مسند إليه", "ACC": "مخصِّص", "GEN": "مجرور بأداة الإضافة"}[case]
        return "relatum", FAMILY[case], role, f"case-only:{relation_ar}"

    return "omitted", None, None, f"no-case:{relation_ar}:{pos}"


def main() -> None:
    buckets = collections.Counter()
    rels = collections.Counter()
    roles = collections.Counter()
    reasons = collections.Counter()
    omitted_rows: list[tuple] = []
    samples: dict = collections.defaultdict(list)
    cased = collections.Counter()

    for ref in words:
        bucket, relation, role, why = classify(ref)
        buckets[bucket] += 1
        if relation:
            rels[relation] += 1
            roles[role] += 1
            if len(samples[(relation, role)]) < 10:
                samples[(relation, role)].append(
                    (ref, words[ref].get("uthmani", ""), (syn.get(ref) or {}).get("relation_ar"))
                )
            if bucket == "relatum":
                has = bool((words[ref].get("features") or {}).get("nominal_case"))
                cased[(relation, "معرب" if has else "مبني")] += 1
        else:
            reasons[why.split(":")[0]] += 1
            s = syn.get(ref) or {}
            omitted_rows.append((ref, words[ref].get("uthmani", ""),
                                 s.get("relation", "-"), s.get("relation_ar", "-"), why))

    total = len(words)
    shown = buckets["relatum"] + buckets["marker"] + buckets["minted"]
    verified = buckets["relatum"] + buckets["marker"]

    print(f"TOTAL WORDS {total}\n")
    for k in ("relatum", "marker", "minted", "omitted"):
        print(f"  {k:10} {buckets[k]:7}  {100 * buckets[k] / total:5.1f}%")
    print(f"\n  verified (معطى محقّق) {verified:7}  {100 * verified / total:5.1f}%")
    print(f"  shown total          {shown:7}  {100 * shown / total:5.1f}%")
    print(f"  omitted + logged     {buckets['omitted']:7}  {100 * buckets['omitted'] / total:5.1f}%")

    print("\nBY RELATION (of shown):")
    for k, v in rels.most_common():
        print(f"  {k:8} {v:7}  {100 * v / shown:5.1f}% of shown  {100 * v / total:5.1f}% of corpus")
    print("\nBY ROLE:")
    for k, v in roles.most_common():
        print(f"  {k:22} {v:7}  {100 * v / total:5.1f}%")
    print("\nRELATA — معرب (full السبب) vs مبني (في محلّ variant):")
    for k, v in sorted(cased.items()):
        print(f"  {k[0]:8} {k[1]:6} {v:7}")
    m = sum(v for k, v in cased.items() if k[1] == "معرب")
    print(f"  => معرب {m}/{buckets['relatum']} = {100 * m / buckets['relatum']:.1f}%")
    print("\nOMITTED reasons:")
    for k, v in reasons.most_common():
        print(f"  {k:26} {v:6}  {100 * v / total:5.2f}%")

    print("\n===== PER-RELATION × ROLE SAMPLES (inspect; a rate hides a wrong-but-complete relation) =====")
    for key in sorted(samples, key=lambda k: (k[0], k[1])):
        print(f"\n--- {key[0]} / {key[1]} ---")
        for ref, word, rar in samples[key]:
            print(f"   {ref:12} {word:20} rel_ar={rar}")

    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
        with out.open("w", encoding="utf-8") as f:
            f.write("ref\tword\trelation\trelation_ar\treason\n")
            for row in omitted_rows:
                f.write("\t".join(str(x) for x in row) + "\n")
        print(f"\nwrote {len(omitted_rows)} omitted rows -> {out}")


if __name__ == "__main__":
    main()
