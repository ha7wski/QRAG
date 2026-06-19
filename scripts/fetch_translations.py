"""
fetch_translations.py — Download French and English Quran translations.

Source: alquran.cloud API (open Quran data).
  - French : Hamidullah          (edition: fr.hamidullah)
  - English: Sahih International  (edition: en.sahih)

Each edition is normalized to a flat JSON map keyed by "surah:ayah":
    { "1:1": "In the name of Allah...", ... }
and saved under data/translations/.

Usage:
    python scripts/fetch_translations.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "translations"

EDITIONS = {
    "fr_hamidullah": "fr.hamidullah",
    "en_sahih": "en.sahih",
}
API = "https://api.alquran.cloud/v1/quran/{edition}"
EXPECTED_VERSES = 6236


def fetch_edition(edition: str) -> dict[str, str]:
    """Fetch one edition and return a {"surah:ayah": text} map."""
    url = API.format(edition=edition)
    print(f"  downloading {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "quran-rag/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if payload.get("code") != 200:
        raise RuntimeError(f"API returned {payload.get('code')} for {edition}")

    mapping: dict[str, str] = {}
    for surah in payload["data"]["surahs"]:
        sn = surah["number"]
        for ayah in surah["ayahs"]:
            an = ayah["numberInSurah"]
            mapping[f"{sn}:{an}"] = ayah["text"].strip()
    return mapping


def run() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, edition in EDITIONS.items():
        mapping = fetch_edition(edition)
        n = len(mapping)
        out = OUT_DIR / f"{name}.json"
        with out.open("w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        flag = "ok" if n == EXPECTED_VERSES else f"⚠️ expected {EXPECTED_VERSES}"
        print(f"  {name}: {n} verses [{flag}] → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"❌ Failed to fetch translations: {exc}")
        sys.exit(1)
