"""
translator.py — Fill verse translations from data/translations/ (phase 2).

Loads the normalized translation maps produced by scripts/fetch_translations.py
and fills each verse's `translation_fr` / `translation_en` by id. If a
translation file is missing, that language is skipped (no-op) so the pipeline
still runs in an Arabic-only configuration.

Files expected (keyed by "surah:ayah"):
  data/translations/fr_hamidullah.json
  data/translations/en_sahih.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS_DIR = ROOT / "data" / "translations"

SOURCES = {
    "translation_fr": TRANSLATIONS_DIR / "fr_hamidullah.json",
    "translation_en": TRANSLATIONS_DIR / "en_sahih.json",
}


def _load(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run(verses: list[dict]) -> list[dict]:
    """Fill translation fields in place; report coverage per language."""
    maps = {field: _load(path) for field, path in SOURCES.items()}

    missing = [field for field, m in maps.items() if not m]
    counts = {field: 0 for field in SOURCES}
    for v in verses:
        for field, m in maps.items():
            text = m.get(v["id"])
            if text:
                v[field] = text
                counts[field] += 1

    parts = ", ".join(f"{f.split('_')[1]}={counts[f]}" for f in SOURCES)
    msg = f"  translator : {parts}"
    if missing:
        names = ", ".join(SOURCES[f].name for f in missing)
        msg += (f"  ⚠️ missing files ({names}) — run "
                "scripts/fetch_translations.py for cross-lingual retrieval")
    print(msg)
    return verses


if __name__ == "__main__":
    sample = [{"id": "1:1", "translation_fr": "", "translation_en": ""}]
    run(sample)
    print(sample[0])
