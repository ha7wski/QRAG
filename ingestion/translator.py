"""
translator.py — Fill verse translations from data/derived/translations/ (phase 2).

Loads the normalized translation maps produced by scripts/fetch_translations.py
and fills each verse's `translation_fr` / `translation_en` by id. If a
translation file is missing, that language is skipped (no-op) so the pipeline
still runs in an Arabic-only configuration.

Files expected (keyed by "surah:ayah"):
  data/derived/translations/fr_hamidullah.json
  data/derived/translations/en_sahih.json
"""
from __future__ import annotations

import sys
from pathlib import Path

# Runnable as a script from any working directory (`python ingestion/translator.py`).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quran_data import loaders, paths  # noqa: E402

# Each language: where its file lives (for the "missing" message) and the shared
# loader that parses it. Both come from the registry; this module builds no path.
SOURCES = {
    "translation_fr": (paths.TRANSLATION_FR_JSON, loaders.translation_fr),
    "translation_en": (paths.TRANSLATION_EN_JSON, loaders.translation_en),
}


def _load(loader) -> dict[str, str]:
    """The translation map, or `{}` when the file has not been fetched.

    A missing translation is not an error: the pipeline still runs in an
    Arabic-only configuration, so the loader's `DatasetMissing` becomes a
    silent skip here rather than a stopped build.
    """
    try:
        return loader()
    except loaders.DatasetMissing:
        return {}


def run(verses: list[dict]) -> list[dict]:
    """Fill translation fields in place; report coverage per language."""
    maps = {field: _load(loader) for field, (_, loader) in SOURCES.items()}

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
        names = ", ".join(SOURCES[f][0].name for f in missing)
        msg += (f"  ⚠️ missing files ({names}) — run "
                "scripts/fetch_translations.py for cross-lingual retrieval")
    print(msg)
    return verses


if __name__ == "__main__":
    sample = [{"id": "1:1", "translation_fr": "", "translation_en": ""}]
    run(sample)
    print(sample[0])
