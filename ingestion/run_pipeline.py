"""
run_pipeline.py — Main ingestion pipeline driver.

Chains the four ingestion stages in order:
    parser → normalizer → enricher → qac-morphology

The pipeline is idempotent: re-running it simply regenerates the processed
JSON files from the raw CSV. Final artifacts are written under
`data/processed/`.

Usage:
    python ingestion/run_pipeline.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Allow running as a script (`python ingestion/run_pipeline.py`) by adding the
# project root to sys.path so the `ingestion` package imports resolve.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion import (  # noqa: E402
    parser,
    normalizer,
    enricher,
    translator,
    morphology,       # legacy tashaphyne builder — kept for validation, unused
    qac_morphology,   # QAC root builder (manually-verified roots)
)


def main() -> int:
    print("=" * 60)
    print("Quran RAG — ingestion pipeline")
    print("=" * 60)
    start = time.perf_counter()
    errors = 0

    stage_times: list[tuple[str, float]] = []

    def timed(name, fn, *args):
        """Run a pipeline stage, record and print its wall-clock latency."""
        t0 = time.perf_counter()
        result = fn(*args)
        dt = time.perf_counter() - t0
        stage_times.append((name, dt))
        print(f"    ⏱  {name}: {dt:.2f}s")
        return result

    try:
        verses = timed("parser", parser.run)
        timed("normalizer", normalizer.run, verses)
        timed("enricher", enricher.run, verses)
        timed("translator", translator.run, verses)
        # Stage 4 — root index. Switched from the tashaphyne stemmer (mis-roots,
        # e.g. كريم → ريم) to the QAC manually-verified roots. Old call kept,
        # commented, so we can validate the two builders before removing it:
        # verses, index = timed("morphology", morphology.run, verses)
        verses, index = timed("qac-morphology", qac_morphology.run, verses)
    except Exception as exc:  # surface a clear failure, keep a clean exit code
        print(f"\n❌ Pipeline failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1

    # Final sanity checks.
    n = len(verses)
    n_roots = len(index)
    n_no_clean = sum(1 for v in verses if not v["text_ar_clean"])
    n_no_period = sum(1 for v in verses if not v["period"])
    errors = n_no_clean + n_no_period

    elapsed = time.perf_counter() - start
    print("-" * 60)
    print(f"{n} verses processed, {errors} errors, "
          f"morphology.json created with {n_roots} roots")
    print(f"  empty text_ar_clean : {n_no_clean}")
    print(f"  missing period      : {n_no_period}")
    print("  stage latencies:")
    for name, dt in stage_times:
        print(f"    {name:<12}: {dt:6.2f}s")
    print(f"  total elapsed       : {elapsed:.1f}s")
    print("  outputs:")
    print("    data/processed/verses_raw.json")
    print("    data/processed/verses_enriched.json")
    print("    data/processed/morphology.json")
    print("    data/processed/verses_final.json")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
