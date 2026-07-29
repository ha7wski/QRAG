#!/usr/bin/env python3
"""
build_maqayis_dataset.py — OFFLINE, one-shot builder for the Maqāyīs aṣl dataset.

Parses Ibn Fāris' *Muʿjam Maqāyīs al-Lugha* (m. 395 AH) into a small CSV mapping
each triliteral/quadriliteral root to the canonical **aṣl** (أصل, the semantic
pivot Ibn Fāris assigns it) — the SOURCED, verified half of the `madar/` feature.

Source (public-domain text, open-access edition; whitelisted repo):
  OpenITI/0400AH → data/0395IbnFarisQazwini/0395IbnFarisQazwini.MucjamMaqayis/
                   0395IbnFarisQazwini.MucjamMaqayis.Shamela0021710-ara1
  Edition: Hārūn (عبد السلام محمد هارون), دار الفكر — kept as metadata.

Discipline (project rule): no fabrication. When the aṣl line does not match the
regular template cleanly, the row is flagged `parse_uncertain` (never guessed),
and roots explicitly declared root-less ("شيء لا أصل له") are stored as `no_asl`
with an EMPTY aṣl text. Nothing carries Ibn Fāris' name unless it is his text.

This script is NOT on the runtime path — it is run once to produce
`data/references/maqayis_asl.csv`, which the `madar/` package then reads offline.

Usage:
    python scripts/build_maqayis_dataset.py            # parse local source → CSV
    python scripts/build_maqayis_dataset.py --fetch     # (re)download source first
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.root_normalize import normalize_root  # noqa: E402

SOURCE_URL = (
    "https://raw.githubusercontent.com/OpenITI/0400AH/master/data/"
    "0395IbnFarisQazwini/0395IbnFarisQazwini.MucjamMaqayis/"
    "0395IbnFarisQazwini.MucjamMaqayis.Shamela0021710-ara1"
)
SOURCE_PATH = ROOT / "data" / "raw" / "maqayis" / "maqayis_shamela.txt"
OUT_CSV = ROOT / "data" / "references" / "maqayis_asl.csv"

SOURCE_TAG = "maqayis_openiti"
EDITION_TAG = "Harun_DarAlFikr"

# Witness roots checked in the build report (and in tests).
WITNESS_ROOTS = ["لحد", "جعم", "جعن", "كتب", "رحم"]

# ── line classification ──────────────────────────────────────────────────────
_ENTRY_RE = re.compile(r"^### \|\s*(.*)$")
# Page markers (`# PageV01P003`) and stray ids (`ms0997`) are noise between the
# entry header and its aṣl line — skipped when locating the first body line.
_PAGE_RE = re.compile(r"^#\s*PageV\d+P\d+")
_MS_NOISE_RE = re.compile(r"^#?\s*ms\d+\s*$")
_ARABIC_TOKEN_RE = re.compile(r"^[ء-ي]{2,5}$")

# aṣl-count number words (searched inside the first sentence of the aṣl line).
_COUNT_WORDS = {
    "أصلان": 2, "أصلين": 2,
    "ثلاثة": 3, "أربعة": 4, "خمسة": 5, "ستة": 6,
}
# "root has no aṣl" declarations (Ibn Fāris' own wording): an explicit "no aṣl"
# statement, or a root he marks مهمل ("neglected", carries no principle).
_NO_ASL_RE = re.compile(
    r"لا\s+أصل\s+له|ليس\b[^.]*\bأصل\b[^.]*\bله|مهمل"
)
# aṣl markers. Besides the literal أصل/أصول, Ibn Fāris very often states the
# principle with the bare formula "<letters> يدل/تدل [بناؤها] على <meaning>"
# (no word "أصل" at all) — that IS an aṣl clause and must be captured.
_HAS_ASL_RE = re.compile(r"أصل|أصول|اصل|يدل|تدل")


def _extract_root(header: str) -> str | None:
    """Return the cleaned root key printed in an entry header, or None if the
    header is a section/chapter marker or unparseable noise.

    Accepts the two regular forms: parenthesized `(كتب)` and a bare compact
    Arabic token `اح` / `آخ`. Rejects bracketed section titles (`[المقدمة]`),
    `باب ...` chapter heads, and anything with internal spaces/punctuation
    (`ا ك`, `اس، ل`, `" الس`) — those are formatting noise, not roots."""
    s = header.strip()
    if not s or s.startswith("["):
        return None
    if s.startswith("باب") or s.startswith(": باب"):
        return None
    m = re.search(r"\(([^)]+)\)", s)
    cand = (m.group(1) if m else s).strip()
    # Strip edge punctuation the source sometimes leaves on a bare token.
    cand = cand.strip(" \t:.\"«»،ـ")
    if _ARABIC_TOKEN_RE.fullmatch(cand):
        return cand
    return None


def _entry_body(lines: list[str], start: int) -> str | None:
    """Full stitched body of the entry whose header is at `lines[start]`, up to
    the next entry header. Unlike the old first-physical-line reader, this
    RE-JOINS `~~` continuation lines onto the line they continue (the source
    wraps a single sentence across several physical lines), so an aṣl is never
    cut mid-word. Page markers and stray `ms####` ids are dropped; the remaining
    `#` lines (prose AND poetry shawāhid) are concatenated into one blob — the
    aṣl extractor below keeps only the first sentence of each aṣl, so the
    shawāhid between/after them fall away naturally."""
    parts: list[str] = []
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        if _ENTRY_RE.match(ln):          # hit the next entry — done
            break
        if _PAGE_RE.match(ln) or _MS_NOISE_RE.match(ln):
            continue
        if ln.startswith("~~"):          # continuation of the previous physical line
            cont = ln[2:].strip()
            if parts:
                parts[-1] = (parts[-1] + " " + cont).strip()
            elif cont:
                parts.append(cont)
        elif ln.startswith("# "):
            parts.append(ln[2:].strip())
        elif ln.strip() and not ln.startswith("#"):
            parts.append(ln.strip())
    body = _clean_inline(" ".join(p for p in parts if p))
    return body or None


# Multiple aṣl of one root are stored in the single `asl_text` CSV cell joined
# by this sentinel (never appears in Arabic prose); the store splits it back to
# a list. A single-aṣl root stores plain text with no sentinel.
ASL_DELIM = " ||| "

# Ordinal markers that open each aṣl in Ibn Fāris' "أصول ثلاثة: فالأول ... والأصل
# الثاني ... والأصل الثالث ..." template, one alternation per aṣl position.
# Deliberately CONNECTOR-PREFIXED (فـ/وـ) — the bare "الأول"/"الثاني" occur too
# often mid-sentence and would mis-cut a segment. Segmentation only promotes when
# it finds EXACTLY the declared number of aṣl (see `_segment_asls`); otherwise we
# fall back to the un-truncated opening sentence — never a half-list posing as full.
_ORDINALS = [
    r"فالأول|فالأصل الأول|والأول|أحدهما|إحداهما|وأولها",
    r"والأصل الثاني|فالأصل الثاني|والثاني|والآخر|والأصل الآخر|وثانيها",
    r"والأصل الثالث|فالأصل الثالث|والثالث|وثالثها",
    r"والأصل الرابع|فالأصل الرابع|والرابع|ورابعها",
    r"والأصل الخامس|فالأصل الخامس|والخامس",
    r"والأصل السادس|فالأصل السادس|والسادس",
]


def _clean_inline(text: str) -> str:
    """Drop inline page markers / stray `ms####` ids the OpenITI text leaves
    mid-line, and collapse whitespace."""
    text = re.sub(r"PageV\d+P\d+", " ", text)
    text = re.sub(r"\bms\d+\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _declared_count(first_sentence: str) -> int:
    """The number of aṣl Ibn Fāris declares in the opening sentence (default 1;
    a bare plural "أصول" with no number word means at least 2)."""
    count = 1
    for word, n in _COUNT_WORDS.items():
        if word in first_sentence:
            count = max(count, n)
    if count == 1 and "أصول" in first_sentence:
        count = 2
    return count


def _segment_asls(body: str, count: int) -> tuple[str, list[str]] | None:
    """Split the entry body into (preamble, [aṣl glosses]) by the ordinal
    markers, each gloss cut at its first full stop (so the shawāhid drop out).
    The PREAMBLE is Ibn Fāris' own opening declaration before the first aṣl
    (e.g. "الباء والعين واللام أصول ثلاثة") — a synthetic lead shown above the
    list. Returns None unless exactly `count` clean segments are found — the
    caller then keeps the honest single-sentence fallback."""
    positions: list[tuple[int, int]] = []
    cursor = 0
    for i in range(count):
        if i >= len(_ORDINALS):
            break
        m = re.search(_ORDINALS[i], body[cursor:])
        if not m:
            break
        positions.append((cursor + m.start(), cursor + m.end()))
        cursor += m.end()
    if len(positions) != count:
        return None
    asls: list[str] = []
    for idx, (_, marker_end) in enumerate(positions):
        seg_end = positions[idx + 1][0] if idx + 1 < len(positions) else len(body)
        gloss = _clean_inline(body[marker_end:seg_end].split(".", 1)[0])
        gloss = gloss.strip(" :،-–—")
        if not (3 <= len(gloss) <= 400):
            return None
        asls.append(gloss)
    preamble = _clean_inline(body[:positions[0][0]]).strip(" .:،-–—")
    return preamble, asls


def _parse_asl(body: str) -> dict:
    """Extract {asl_text, asl_count, asl_status, confidence} from an entry body.

    The aṣl text stored is Ibn Fāris' OWN wording, never a paraphrase. When he
    declares several aṣl and the ordinal template segments cleanly, ALL of them
    are captured (joined by `ASL_DELIM`); otherwise the un-truncated opening
    sentence is kept, with `asl_count` still reflecting his declared number so
    the UI notes there are more. `no_asl` → empty text; a body with no aṣl marker
    at all is flagged `parse_uncertain` (kept verbatim, not promoted)."""
    first_sentence = _clean_inline(body.split(".", 1)[0])
    # "no aṣl" / "مهمل" declarations sit at the very head of an entry; scope the
    # check there so a "لا أصل" buried in a later shāhid can't void a real aṣl.
    head = body[:200]
    if _NO_ASL_RE.search(head):
        return {"asl_text": "", "asl_preamble": "", "asl_count": 0,
                "asl_status": "no_asl", "confidence": "high"}
    if _HAS_ASL_RE.search(first_sentence):
        count = _declared_count(first_sentence)
        if count >= 2:
            segmented = _segment_asls(body, count)
            if segmented:
                preamble, asls = segmented
                return {"asl_text": ASL_DELIM.join(asls), "asl_preamble": preamble,
                        "asl_count": count, "asl_status": "has_asl",
                        "confidence": "high"}
        return {"asl_text": first_sentence, "asl_preamble": "", "asl_count": count,
                "asl_status": "has_asl", "confidence": "high"}
    # No aṣl marker at all: don't guess — flag for review, keep the real text.
    return {"asl_text": first_sentence, "asl_preamble": "", "asl_count": 1,
            "asl_status": "parse_uncertain", "confidence": "low"}


def parse_source(text: str) -> list[dict]:
    """Parse the full OpenITI text into per-root records (last entry wins on
    duplicate normalized keys — the source has occasional repeated headers)."""
    lines = text.splitlines()
    rows: dict[str, dict] = {}
    for i, ln in enumerate(lines):
        if not _ENTRY_RE.match(ln):
            continue
        header = _ENTRY_RE.match(ln).group(1)
        root_raw = _extract_root(header)
        if root_raw is None:
            continue
        body = _entry_body(lines, i)
        if body is None:
            continue
        parsed = _parse_asl(body)
        root_norm = normalize_root(root_raw)
        if not root_norm:
            continue
        rows[root_norm] = {
            "root_normalized": root_norm,
            "root_raw": root_raw,
            "asl_text": parsed["asl_text"],
            "asl_preamble": parsed["asl_preamble"],
            "asl_count": parsed["asl_count"],
            "asl_status": parsed["asl_status"],
            "source": SOURCE_TAG,
            "edition": EDITION_TAG,
            "confidence": parsed["confidence"],
        }
    return list(rows.values())


def _load_qac_roots() -> set[str]:
    """Normalized set of QAC root keys (for the overlap report). Empty if the
    morphology index is not built yet."""
    import json

    path = ROOT / "data" / "processed" / "morphology.json"
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {normalize_root(k) for k in json.load(f)}


def _fetch_source() -> None:
    SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Fetching source from {SOURCE_URL} ...")
    urllib.request.urlretrieve(SOURCE_URL, SOURCE_PATH)  # noqa: S310 (whitelisted)
    print(f"  saved → {SOURCE_PATH} ({SOURCE_PATH.stat().st_size} bytes)")


def build(fetch: bool = False) -> list[dict]:
    if fetch or not SOURCE_PATH.exists():
        if not SOURCE_PATH.exists() and not fetch:
            print(f"Source not found at {SOURCE_PATH}; downloading (--fetch implied).")
        _fetch_source()
    text = SOURCE_PATH.read_text(encoding="utf-8")
    rows = parse_source(text)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["root_normalized", "root_raw", "asl_text", "asl_preamble",
              "asl_count", "asl_status", "source", "edition", "confidence"]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["root_normalized"]))
    return rows


def report(rows: list[dict]) -> None:
    total = len(rows)
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r["asl_status"]] = by_status.get(r["asl_status"], 0) + 1
    print("\n" + "=" * 64)
    print("BUILD REPORT — Maqāyīs aṣl dataset")
    print("=" * 64)
    print(f"  output        : {OUT_CSV}")
    print(f"  total entries : {total}   (Ibn Fāris reference ~3500 roots)")
    for st in ("has_asl", "no_asl", "parse_uncertain"):
        print(f"    {st:<16}: {by_status.get(st, 0)}")

    by_key = {r["root_normalized"]: r for r in rows}
    print("\n  witness roots (raw → extracted aṣl):")
    for w in WITNESS_ROOTS:
        r = by_key.get(normalize_root(w))
        if r is None:
            print(f"    {w}: NOT FOUND")
            continue
        note = f"[{r['asl_status']}, count={r['asl_count']}]"
        print(f"    {w} {note}: {r['asl_text'] or '(no aṣl)'}")
    # Control assertion surfaced (not enforced here — tests enforce it).
    lahad = by_key.get(normalize_root("لحد"))
    ok = bool(lahad) and "ميل" in lahad["asl_text"]
    print(f"\n  control: لحد aṣl contains « ميل » → {'PASS' if ok else 'FAIL'}")

    qac = _load_qac_roots()
    if qac:
        keys = set(by_key)
        covered = len(qac & keys)
        pct = 100.0 * covered / len(qac) if qac else 0.0
        print(f"\n  QAC overlap   : {covered}/{len(qac)} QAC roots have an aṣl "
              f"entry ({pct:.1f}%)")
    else:
        print("\n  QAC overlap   : morphology.json not built — skipped.")
    print("=" * 64)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the Maqāyīs aṣl dataset (offline).")
    ap.add_argument("--fetch", action="store_true",
                    help="(re)download the OpenITI source before parsing")
    args = ap.parse_args()
    rows = build(fetch=args.fetch)
    report(rows)


if __name__ == "__main__":
    main()
