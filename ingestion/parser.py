"""
parser.py — Stage 1 of the ingestion pipeline.

Reads the raw Quran CSV (`data/raw/quran.csv`) and produces a list of
structured verses following the project's canonical schema, saved to
`data/processed/verses_raw.json`.

Expected CSV columns: num_soura, num_aya, aya, name_soura
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

# Project root (two levels above this file)
ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "quran.csv"
OUTPUT_JSON = ROOT / "data" / "processed" / "verses_raw.json"

# Expected number of verses (sanity check)
EXPECTED_VERSES = 6236


def build_verse(num_soura: int, num_aya: int, aya: str, name_soura: str) -> dict:
    """Build a verse dict in the canonical schema, with the empty fields
    that later pipeline stages will fill in."""
    return {
        "id": f"{num_soura}:{num_aya}",
        "surah_number": num_soura,
        "surah_name_ar": name_soura,
        "surah_name_fr": "",          # → enricher.py
        "surah_name_en": "",          # → enricher.py
        "ayah_number": num_aya,
        "text_ar": aya,               # raw text from the CSV
        "text_ar_clean": "",          # → normalizer.py
        "translation_fr": "",         # → phase 2
        "translation_en": "",         # → phase 2
        "transliteration": "",        # optional in phase 1
        "period": "",                 # → enricher.py (makkiyya | madani)
        "juz": 0,                     # → enricher.py (1–30)
        "themes": [],
        "roots": [],                  # → morphology.py
    }


def parse(raw_csv: Path = RAW_CSV) -> list[dict]:
    """Parse the CSV and return the list of structured verses."""
    if not raw_csv.exists():
        raise FileNotFoundError(
            f"Source file not found: {raw_csv}\n"
            "Place the corpus at data/raw/quran.csv before running the pipeline."
        )

    verses: list[dict] = []
    # utf-8-sig automatically strips the BOM at the start of the file.
    with raw_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        expected_cols = {"num_soura", "num_aya", "aya", "name_soura"}
        missing = expected_cols - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"Missing columns in CSV: {missing}. "
                f"Found: {reader.fieldnames}"
            )

        for lineno, row in enumerate(reader, start=2):
            try:
                num_soura = int(row["num_soura"])
                num_aya = int(row["num_aya"])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid numbers on line {lineno}: {row}"
                ) from exc

            aya = (row["aya"] or "").strip()
            name_soura = (row["name_soura"] or "").strip()
            verses.append(build_verse(num_soura, num_aya, aya, name_soura))

    return verses


def save(verses: list[dict], output: Path = OUTPUT_JSON) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)


def run() -> list[dict]:
    """Entry point called by run_pipeline.py."""
    verses = parse()
    n = len(verses)
    if n != EXPECTED_VERSES:
        print(
            f"  ⚠️  {n} verses parsed (expected: {EXPECTED_VERSES}). "
            "Check the source file."
        )
    surahs = {v["surah_number"] for v in verses}
    print(f"  parser     : {n} verses, {len(surahs)} surahs")
    save(verses)
    return verses


if __name__ == "__main__":
    run()
