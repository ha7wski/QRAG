"""
verify_gold.py — Sanity-check the gold sets in qa_dataset.json against the
indexed corpus. For every relevant_verse_id it confirms the verse exists and
prints its Arabic + English text so relevance can be judged by reading.

Usage:
    python tests/eval/verify_gold.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSES = ROOT / "data" / "processed" / "verses_final.json"
DATASET = Path(__file__).resolve().parent / "qa_dataset.json"


def main() -> int:
    verses = {v["id"]: v for v in json.load(open(VERSES, encoding="utf-8"))}
    data = json.load(open(DATASET, encoding="utf-8"))
    questions = data["questions"]

    missing_total = 0
    all_surahs: set[int] = set()
    per_lang: dict[str, int] = {}

    for q in questions:
        per_lang[q["language"]] = per_lang.get(q["language"], 0) + 1
        print(f"\n[{q['id']}] ({q['language']}) {q['question']}")
        for vid in q["relevant_verse_ids"]:
            v = verses.get(vid)
            if v is None:
                print(f"  ❌ MISSING {vid}")
                missing_total += 1
                continue
            all_surahs.add(v["surah_number"])
            en = (v.get("translation_en") or "")[:70]
            ar = (v.get("text_ar") or "")[:32]
            print(f"  {vid:<7} EN: {en}")
            print(f"          AR: {ar}")

    print("\n" + "=" * 60)
    print(f"questions: {len(questions)}  | per language: {per_lang}")
    print(f"distinct surahs covered: {len(all_surahs)} -> {sorted(all_surahs)}")
    print(f"missing verse ids: {missing_total}")
    return 1 if missing_total else 0


if __name__ == "__main__":
    sys.exit(main())
