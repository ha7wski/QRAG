## Context

The reading page (`components/SurahReader.tsx`) renders a sūra as one `ArabicText` block: each āya is
a `<span>` holding `text_ar_tashkil || text_ar`, followed by a `﴿n﴾` marker carrying `id="ayah-{n}"`
and `data-ayah` (the reading-position observer depends on both). Sūras over 50 āyāt are shown one
range at a time (`CHUNK_SIZE`).

Both closeness relations are already built and measured, so this change reads, it never computes:

- **Intra-sūra** — `data/derived/surah_similarity.json`, `surahs[n].groups[] = {ayahs, strength}`;
  189 āyāt sit in a group (287 have neighbours; the user chose the groups).
- **Cross-sūra** — `data/derived/quran_close_verses.json`, `pairs[] = {a, b, score, sim, pas, from,
  roots, k, wa, wb, ca, cb}`; `from ∈ {["similarity"] 300, ["passage"] 2040, both 151}`; `ca`/`cb`
  are half-open character spans in each verse's displayed `text_ar_tashkil` (Basmala stripped),
  computed at build time. 1 891 āyāt appear in a pair; 73 āyāt are in both relations (in a group AND a pair end — 111 would count neighbours, which the cue does not use). Busiest sūras:
  2 (328 pair-ends), 3 (308).

`retrieval/quran_close_verses.py` is already the pure reader of the second file (memoised, model-free);
`api/routers/surah_similarity.py` already reads the first and turns a missing file into a 503 with the
rebuild command.

The working tree carries uncommitted edits to the similarity routers and frontend (per-verse
`GET /verse/{s}/{a}/similar` quarantined, picked-verse panel removed). This design assumes that state.

## Goals / Non-Goals

**Goals:**
- Green āya text for group members, orange marker for whole-verse cross pairs, orange words for
  passage-only cross pairs, both cues visible at once.
- An in-page bubble on click, no navigation.
- Off by default; switching off restores today's page byte-for-byte in rendering.
- Zero new computation: no rebuild, no model, no new dataset.

**Non-Goals:**
- Marking the common part of *intra*-sūra groups (the intra dataset has no spans; whole-verse only).
- Marking words for whole-verse (`similarity`) pairs even when they carry a common part — the user's
  rule is «entire → marker».
- Any threshold on coverage, score or strength; any change to either dataset or its gold.
- Annotating `/qlisan`, Verse Study or any other page.

## Decisions

**1. One per-sūra route, `GET /surah/{number}/annotations`, rather than per-āya fetches or reusing
existing routes.** The colours need every āya's status at once; the bubble needs partner texts. One
payload per sūra (fetched once, cached client-side per sūra, only while the switch is on) serves both.
Alternatives: re-mounting the quarantined `GET /verse/{s}/{a}/similar` for the bubble (one request per
click, and it covers only the cross half), or composing `GET /surah/{n}/similar` + the matrix routes
client-side (three shapes to reconcile, and the matrix is cell-oriented, not āya-oriented). Size bound:
sūra 2 has 328 pair-ends → ≤ 328 partner records, roughly ≤ 150 KB uncompressed; acceptable for an
opt-in view.

Response shape (sketch):
```
{ surah, ayahs: [ { ayah, group: [10, 116] | [],
                    whole:   [ {ref, score, span_self?, span_other?} ],
                    passage: [ {ref, score, span_self,  span_other } ] } ],
  verses: { "36:20": VerseRecord, ... } }   // partners, deduplicated
```
`span_self` is the pair's `ca` or `cb` as seen from this āya (the reader normalises pair order).
Group partners are same-sūra āyāt; their records also go in `verses` so the bubble never fetches.

**2. The relation decides marker vs words — not coverage.** Chosen by the user. `"similarity" in
from` → marker (including the 151 pairs that are also a passage); `from == ["passage"]` → words.
Consequence, accepted: an āya may get an orange marker from one pair and orange words from another.

**3. Rendering the words: split the āya text by the merged spans.** In the frontend, the passage
spans of one āya are sorted and merged into disjoint runs, and the text is cut into plain / `<mark>`
segments. Offsets are JS string indices (UTF-16); the build computed them in Python (code points).
Arabic text with harakat is BMP-only, so the two coincide — the implementation asserts the span ends
within the string, and a Vitest pins one real āya (28:20). When the āya is rendered from the `text_ar`
fallback (no `text_ar_tashkil`), spans are not applied and the marker turns orange instead.

**4. Two cues that never overlap.** Green = a light green background (`bg-emerald-100`, cloned
across line breaks) over the āya's WHOLE text — chosen after the first visual check, because a green
fill on the marker was indistinguishable from the always-green `﴿n﴾` digits. Orange = an orange ring
around the marker (whole-verse pair) and a light orange `<mark>` on the passage words. Both = green
text + orange-ringed marker; orange words stay orange on top of the green text. The marker keeps `id`
and `data-ayah` so the reading-position observer and `#ayah-n` deep links are untouched.

**5. Bubble: a lightweight popover, not a modal and not a route.** A component (e.g.
`components/CloseVersesBubble.tsx`) positioned under the clicked marker/word, with
`role="dialog"`, focus moved in on open and back on close, Escape / outside click / another āya closes
it. Entries reuse `SimilarVerseParts.tsx`'s verse-text rendering (common part in `<mark>`) but
**without** its «الآية في سياقها» link. Intra partners in another range of a long sūra are listed by
text, not scrolled to.

**6. Switch state in `localStorage`** (`surah.annotations.on`), via the same try/catch pattern the
reader already uses for its position; per browser, not per sūra.

**7. Backend structure.** A new router `api/routers/surah_annotations.py` composing the two existing
readers; models in `api/models/surah_annotations.py`; verses through `verse_from_record`. Mounted in
`api/main.py`. Errors mirror the sibling routers (422 path validation, 503 + rebuild command).

## Risks / Trade-offs

- [Orange covers ~30 % of āyāt; heavy sūras (2, 3) will look busy] → off by default; marker-only for
  whole pairs keeps most of the text uncoloured; the legend explains it.
- [Span offsets computed in Python code points vs JS UTF-16] → BMP-only text; bounds-checked;
  pinned by a test on 28:20.
- [Stale dataset vs displayed text (a rebuilt `quran_chakl.csv` shifting spans)] → the build already
  refuses stale inputs; the route can verify each span lies inside its verse's text and 503 otherwise
  (same rule as the existing pair routes).
- [Payload size on long sūras] → one fetch per sūra, cached; measured on sūra 2 during apply.
- [Click targets on coloured words interfere with text selection] → activation on click only, not on
  mousedown; selection drags do not open the bubble.

## Migration Plan

Additive. No data rebuild. Rollback = unmount the route and remove the switch; the reading page's
default (off) is already today's page.

## Open Questions

- Exact orange / green shades — to be validated visually on sūra 3
  during apply.
