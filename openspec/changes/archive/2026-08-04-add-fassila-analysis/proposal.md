## Why

The fāṣila (فاصلة) — the rhyme-letter that closes each āya in pausal form — is the
audible skeleton of a sūra. Its distribution and its run-structure (long stretches on
a single letter, deliberate breaks, returns) are a primary object of classical
Qurʾānic study, but QURAG currently exposes no way to see them: a reader must read the
whole sūra aloud and tally by ear. A validated HTML prototype
(`~/Downloads/fassila_quran_2.html`) already demonstrates the two readings that make the
structure legible at a glance, over all 114 sūras — this change moves that prototype into
the product, with the derivation moved server-side onto the real corpus instead of a
216 KB blob baked into the page.

## What Changes

- **New backend capability** — a corpus-derived fāṣila computation over the Uthmānī
  vocalized corpus (`data/raw/quran_chakl.csv`, already loaded by
  `indexing.corpus.chakl_by_ref()`), exposed as a read-only endpoint. Per āya it yields
  the last word, its `s:a:w` word reference (aligned with the existing QAC token spine),
  and the fāṣila letter in pausal form: tashkīl removed, tanwīn neutralized, `ة → ه`,
  `ى → ا`, dagger-alif `ٰ → ا`.
- **Muqaṭṭaʿāt exclusion** — āyāt consisting *only* of disconnected letters are flagged
  and excluded from all counts and percentages, while remaining visible as a stated
  exclusion. Verified against the corpus: **20 āyāt across 19 sūras**
  (2:1, 3:1, 7:1, 19:1, 20:1, 26:1, 28:1, 29:1, 30:1, 31:1, 32:1, 36:1, 40:1, 41:1,
  42:1, 42:2, 43:1, 44:1, 45:1, 46:1). Sūras opening with الر / المر / طس / ص / ق / ن are
  **not** excluded — their āya continues with ordinary words, so it carries a real fāṣila.
- **New frontend page** — `/fassila`, a 100 % Arabic RTL page rendered in QURAG's existing
  design language (Tailwind utilities, the `brand` teal family, the established card and
  header idiom, Amiri for Arabic), with a 114-sūra selector (plus prev/next), three summary
  tiles, and the two visualizations validated in the prototype:
  1. a **bar chart** of āya count per distinct fāṣila, sorted by frequency, with the
     percentage computed over *analysed* āyāt (muqaṭṭaʿāt excluded from the denominator);
  2. a **continuous line** whose Y axis lists the fawāṣil **in order of first appearance,
     bottom to top**, and whose X axis is the āya number **starting at 0**.
- A methodology disclosure (collapsed) stating the pausal rules, the exclusion list, and
  the corpus source — the prototype's `<details>` block, kept as product copy.

**Dark mode is deferred.** The original brief asked for one, but the application is
light-only by construction — `globals.css` sets `color-scheme: light`, the sidebar is a
hardcoded `bg-white`, and `frontend/src` contains no `dark:` variant at all. A page-scoped
dark mode would put a dark panel against a permanently light shell; making it coherent means
theming the shell and all six existing pages, which is its own change. `/fassila` therefore
ships in the project's light design language, and dark mode is left to an app-wide change.

No existing behavior changes; this is purely additive.

> **Correction carried into the spec:** the prototype's prose claims the exclusion covers
> "20 āyāt in **16** sūras". Its own embedded data — and an independent recount against
> `quran_chakl.csv` — give **19** sūras. The spec encodes 19.

## Capabilities

### New Capabilities
- `fassila-analysis`: derivation of the pausal-form fāṣila for every āya of a sūra from
  the Uthmānī corpus, muqaṭṭaʿāt exclusion, per-sūra aggregation (counts, percentages
  over analysed āyāt, first-appearance ordering), the read-only API contract that serves
  it, and the two required visualizations plus the sūra selector, Arabic RTL shell and
  dark mode that present it.

### Modified Capabilities

_None._ The change adds a page and an endpoint; no existing requirement's behavior changes.

## Impact

**New code**
- `analysis/fassila.py` — pausal-form derivation + muqaṭṭaʿāt detection + per-sūra
  aggregation (pure, offline, no ML, no LLM).
- `api/models/fassila.py`, `api/routers/fassila.py` — response models and the
  `GET /fassila/{surah}` route; registered in `api/main.py` alongside the existing routers.
- `frontend/src/app/fassila/page.tsx` + chart components; a `getFassila` client in
  `frontend/src/lib/api.ts`; a nav entry in `frontend/src/components/Navbar.tsx`.

**Existing code touched**
- `api/main.py` — one import + one `include_router` line.
- `frontend/src/lib/api.ts`, `frontend/src/components/Navbar.tsx` — additive only.

**Data**
- Reads `data/raw/quran_chakl.csv` through the existing cached
  `indexing.corpus.chakl_by_ref()` loader. No new data files, no pipeline re-run, no
  index rebuild.
- Two corpus properties this derivation must handle (both verified, see `design.md`):
  the Basmala is **prepended to āya 1 of 113 sūras** (all but Sūrat at-Tawba), and āyāt
  may end in non-letter marks (sajda ۩ U+06E9, waqf/small-high marks) that must not be
  mistaken for the fāṣila.

**Dependencies** — none added. Charts are hand-rolled SVG/DOM as in the prototype, so no
charting library enters the bundle.

**Out of scope** — cross-sūra/whole-Qurʾān aggregation, fāṣila-based search or retrieval,
ʿadd al-āy (counting-tradition) variants, and any tie-in to the RAG or LLM paths.
