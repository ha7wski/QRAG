## Context

A validated HTML prototype (`~/Downloads/fassila_quran_2.html`, 299 KB) already produces the
intended output for all 114 sūras. It is a single self-contained page carrying a 216 KB
`SURAS` blob — pre-computed `{n, name, nv, v:[{a, l, w, m?}]}` — plus ~120 lines of vanilla
DOM/SVG rendering. Its **behavior and design are the reference**; what must change is where
the derivation happens. Baking a 216 KB corpus-derived blob into the frontend bundle
duplicates data the backend already has in memory and would drift the moment the corpus is
touched.

Everything needed is already on disk and already loaded by the running backend:

- `data/raw/quran_chakl.csv` — the Uthmānī vocalized corpus, served by the cached
  `indexing.corpus.chakl_by_ref()` (`{(surah, ayah): {"text", "surah_name"}}`).
- `data/raw/quran-morphology.txt` — the QAC treebank, whose location keys are `s:a:w:seg`
  and whose muqaṭṭaʿāt are tagged `INL`.

Three corpus properties were verified against the data before writing this design, and each
one drives a decision below:

1. **The Basmala is prepended to āya 1 of 113 sūras** in `quran_chakl.csv` — every sūra but
   at-Tawba. Sūra 1's āya 1 *is* the Basmala. QAC does **not** count it: `2:1:1` is `الٓمٓ`.
2. **Combining-mark order is not stable.** A literal `"بِسْمِ ٱللَّهِ…"` comparison against
   2:1 fails even though the text is visually identical, because shadda/ḥaraka ordering
   differs. Any Basmala match must run on diacritic-stripped text.
3. **Āyāt can end in non-letters:** the sajda mark `۩` (U+06E9) closes 15 āyāt, U+06DC closes
   2, and waqf marks appear inline. 224 āyāt end in a dagger alif (U+0670), and the large
   majority end in a bare combining ḥaraka.

## Goals / Non-Goals

**Goals:**

- Reproduce the prototype's output exactly — same fāṣila per āya, same 20 exclusions, same
  two visualizations, same Arabic RTL shell and dark mode.
- Move the derivation server-side, computed from the corpus at request time, so the
  frontend ships rendering code only.
- Emit `s:a:w` word references aligned with the existing QAC token spine, so a fāṣila can
  later be linked into QLisan / Verse Study without a second alignment pass.
- Keep the derivation pure and dependency-free: no ML, no LLM, no new packages.

**Non-Goals:**

- Cross-sūra or whole-Qurʾān aggregation (the prototype is per-sūra; so is this).
- Fāṣila-driven search, retrieval, or any RAG integration.
- ʿadd al-āy (āya-counting tradition) variants — the corpus's Kufi numbering is taken as
  given.
- Deep-linking a fāṣila into QLisan. The `s:a:w` reference is emitted so this stays cheap
  later, but wiring it is not in scope.

## Decisions

### D1 — Detect muqaṭṭaʿāt via the QAC `INL` tag, not a hardcoded string list

The request specified exact-match against the known combinations. Testing showed a strictly
better method with an identical result: an āya is muqaṭṭaʿāt-only **iff every one of its QAC
words carries `INL`**. Run over the treebank this yields exactly the 20 āyāt in 19 sūras that
the prototype flags — `MATCHES GROUND TRUTH: True`, no misses, no extras.

Why prefer it:

- **No list to maintain and no Basmala problem.** String matching against 2:1 would first
  have to strip the prepended Basmala and normalize mark order (findings 1 and 2); the tag
  lookup sidesteps both.
- **الر / المر / طس / ص / ق / ن fall out correctly for free.** Those āyāt continue with
  ordinary words, so not every word is `INL` and they are retained — no special-casing.
- **Same provenance as the rest of QURAG.** Roots, lemmas and the token spine all come from
  this treebank; adding a parallel hand-maintained truth source would be the odd one out.

The known-combinations list does not disappear — it is **frozen into a test** asserting the
exact 20 references, so any future corpus swap that changes the set fails loudly.

*Alternative rejected:* exact string matching as originally specified. Same output, but it
needs the Basmala-strip and mark-order normalization to work at all, and it hardcodes
knowledge the corpus already carries.

### D2 — Source words from the QAC treebank (Uthmānī rasm), not from `quran_chakl.csv`

**Reversed during implementation.** This decision originally read "split `quran_chakl.csv`
and strip the prepended Basmala"; validating against the reference fixture showed that to be
wrong at the root, for a reason neither the prototype's prose nor the repo's docs record.

`quran_chakl.csv` is **imlāʾī** (modern plene) orthography; the fāṣila is a property of the
**Uthmānī rasm**. The two disagree exactly where the rhyme lives — word-finally:

| | `quran_chakl.csv` (imlāʾī) | QAC (Uthmānī rasm) | fāṣila |
|---|---|---|---|
| 20:14 | `فَاعْبُدْنِي` | `فَٱعْبُدْنِى` | `ي` ✗ vs `ا` ✓ |
| 1:2 | `الْعَالَمِينَ` | `ٱلْعَٰلَمِينَ` | `ن` (agrees) |
| 2:23 | `صَادِقِينَ` | `صَٰدِقِينَ` | `ن` (agrees) |

Reading the plene text produced **43 wrong fāṣila** against the reference — most of Sūrat
Ṭā-Hā, whose rhyme is precisely the final `ى`. The QAC treebank, whose surface forms
concatenate back to the rasm, produced **0 wrong out of 6236**.

Sourcing from QAC also dissolves two problems the original decision existed to solve:

- **`s:a:w` alignment becomes definitional** rather than something to verify — the word
  index *is* the QAC word index. The planned "word counts match QAC" post-condition test is
  now vacuous and was dropped.
- **The Basmala problem disappears.** QAC does not carry the prefix that `quran_chakl.csv`
  prepends to āya 1 of 113 sūras, so there is nothing to strip and no unstable mark-order
  comparison to get right. `strip_basmala` was written, then deleted.

`quran_chakl.csv` is still read, but only for sūra names — QAC carries none.

*Residual difference, accepted:* the fixture's display words drop the dagger alif and madda
that QAC keeps (`الْعَلَمِينَ` vs `ٱلْعَٰلَمِينَ`). Letter skeletons are identical on 6215 of
6216 āyāt; the one exception is 37:130, where QAC writes the proper noun `إِلْ يَاسِينَ` with
an internal space and the fixture shows only `يَاسِينَ` (fāṣila `ن` either way). Keeping the
fuller QAC vocalization is more faithful to the rasm and consistent with how QURAG displays
vocalized text elsewhere, so it stands.

### D3 — Compute per request, cache per process

The whole-corpus derivation is a linear scan over 6236 rows with no model in the loop. Cache
the parsed muqaṭṭaʿāt reference set and the per-sūra results with `functools.lru_cache`,
following the established `indexing/corpus.py` pattern. First call warms; subsequent calls
are dictionary lookups. No precomputed artifact, no new file in `data/processed/`, no
pipeline stage — so a corpus change is picked up on restart rather than needing a rebuild.

*Alternative rejected:* a build-time `data/processed/fassila.json`. It would shave a
negligible amount off a warm request while adding a pipeline stage and a staleness mode.

### D4 — Backend owns derivation; frontend owns rendering only

`analysis/fassila.py` holds the pausal reduction, exclusion and aggregation as pure
functions. `api/routers/fassila.py` exposes `GET /fassila/{surah}` and does nothing but call
them. The page fetches one sūra at a time — a per-sūra payload is a few KB against the
prototype's 216 KB all-sūras blob, so the selector stays instant while the bundle stays
small.

This mirrors the existing split (`analysis/` computes, `api/routers/` serves,
`frontend/` renders) and keeps the derivation unit-testable with no HTTP in the loop.

### D5 — Hand-rolled SVG, ported from the prototype

The prototype's charts are ~80 lines of `createElementNS` against a `viewBox`, with two
mapping functions doing the real work:

```
rowY(letter) = mT + (nR - order.indexOf(letter) - 0.5) / nR * plotH   // bottom-up, first-appearance
ayaX(aya)    = mL + (aya / N) * plotW                                  // domain starts at 0
```

`rowY` is exactly the spec's "first appearance, bottom to top" and `ayaX` is exactly "starts
at 0" — the two requirements most easily lost in translation. Port these verbatim into React
rather than re-deriving them, and keep the prototype's adaptive vertex radius
(`N>160 ? 1.6 : N>90 ? 2.1 : 2.6`) and its `niceStep` tick chooser.

*Alternative rejected:* a charting library (Recharts, visx). Both required behaviors — a
categorical Y axis ordered by first appearance, and an X domain anchored at 0 rather than at
the first data point — are fights with a library's defaults, for a bundle cost, to reproduce
a design that already works in 80 lines.

### D6 — Adopt the project's design language; defer dark mode

The prototype is a standalone page with its own neutral palette and a blue series colour
(`--series-1: #2a78d6`). QURAG has an established visual language that the page must join
instead: Tailwind utilities (no bespoke CSS custom properties), the `brand` teal family
(`#0e7c66` / `brand-dark #0a5c4c` / `brand-light #e6f4f0`), cards as
`rounded-xl border border-gray-200 bg-white shadow-sm` with `border-b border-gray-100`
sub-headers, page headers as `text-2xl font-semibold text-gray-800` over
`text-sm text-gray-500`, controls as `rounded-lg border border-gray-300 …
focus:border-brand`, Amiri via `.arabic-text` / `font-arabic`, and lucide icons. The
prototype governs **behavior and layout**; the project governs **colour and chrome**.

The charts follow: bars, polyline and vertices take `brand` teal, gridlines take
`gray-200`, axis labels `gray-500`. Since Tailwind classes work on SVG elements, no
chart-specific palette layer is needed.

**Dark mode is deferred to an app-wide change.** The original brief asked for it, but the
application is light-only by construction: `globals.css` sets `color-scheme: light` and
`body { @apply bg-gray-50 }`, `Navbar` is a hardcoded `bg-white`, and there is not one
`dark:` variant in `frontend/src`. Three options were weighed:

1. *page-scoped dark* — honours the brief literally, but renders a dark panel beside a white
   sidebar and a `gray-50` gutter: a visible seam, not a design;
2. *app-wide dark* — coherent, but means `darkMode: "class"`, a theme provider, and `dark:`
   variants across six existing pages and ten components — far outside this change;
3. *defer* — `/fassila` ships in the project's light language, dark mode becomes its own
   change.

Option 3 was chosen. This is a deliberate reduction of the original brief, recorded here so
it is not mistaken for an oversight.

## Risks / Trade-offs

- **Pausal reduction misfires on an unforeseen orthographic case** → The prototype's
  embedded `SURAS` blob is a validated, complete reference: extract it once and assert the
  backend reproduces all 6236 `(āya → fāṣila)` pairs. Any divergence surfaces as a named
  failing reference, not a vague suspicion. This is the single highest-value test in the
  change.
- **The `s:a:w` alignment drifts on āyāt with unusual tokenization** → D2's post-condition
  test compares word counts against QAC for every āya, so drift fails at test time rather
  than showing a wrong word in a tooltip.
- **The prototype's methodology prose is wrong** — it says "20 āyāt in 16 sūras"; the data
  says 19 (2, 3, 7, 19, 20, 26, 28–32, 36, 40–46; sūra 42 contributes two āyāt). Porting the
  copy verbatim would ship the error. The spec fixes it at 19; the frozen exclusion test
  keeps it honest.
- **Long sūras crowd the line chart** — al-Baqara plots 285 vertices across 26 rows. Mitigated
  by the prototype's adaptive radius and by letting the SVG scroll horizontally inside its
  own container, never the page body.
- **First-call latency on a cold cache** — one full-corpus scan on the first request.
  Acceptable (no model load, unlike `/search`); if it proves noticeable, warm it in the
  FastAPI lifespan next to the existing warmups.

## Migration Plan

Purely additive: a new module, a new router registered in `api/main.py`, a new page and a
nav entry. Nothing existing changes behavior, so there is no migration and no data
backfill. Rollback is removing the `include_router` line and the nav entry; no state is
written, so nothing needs undoing.

## Open Questions

- **Nav placement and label.** The Arabic-only page sits in an otherwise English-labelled
  nav (`Talk to Quran · Find Verse context · Verse Study · QLisan · Lisan Analysis`).
  Proposed: `Fassila`, placed after `Verse Study`. Worth a look at apply time.
- **Whether to link a fāṣila into QLisan.** The `s:a:w` reference makes it a small follow-up;
  deliberately deferred rather than designed in now.
