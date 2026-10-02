## Why

The «الآيات المتشابهات» tab answers one question today: *which verses, anywhere in the Quran, are
closest to the phrase I typed?* It cannot answer the question a reader asks while studying one
surah: *which verses of THIS surah echo each other?* — the refrains of ar-Raḥmān and al-Mursalāt,
the narrative beats of Yūsuf that answer one another, the opening and closing of al-Baqara. That is
تفسير القرآن بالقرآن at the scale of a surah, and the existing route cannot serve it: `GET /search`
needs a typed query, and running it once per verse of a 286-verse surah means 286 reranker passes
(~1 s each) for a single page.

The question is closed and finite — 114 surahs, **327 431 intra-surah verse pairs** in total
(al-Baqara alone 40 755) — so it can be answered once, offline, with the full-cost comparison, and
served as a static lookup: no model resident, instant render, and the reader can move from verse to
verse inside the surah without a round trip to a model.

## What Changes

- **New mode in the «الآيات المتشابهات» tab**: a two-way switch at the top of the tab —
  «بعبارة» (the existing phrase search, unchanged) and «داخل سورة» (new). The new mode lets the
  reader pick a surah, then shows:
  - the surah's **groups of mutually close verses** (strongest first), each group listing its
    verses vocalized with their numbers;
  - on selecting any verse of the surah, its **nearest verses within the same surah**, ranked,
    each with the roots it shares with the selected verse.
- **What «close» means, fixed by the user**: two verses are close when they **share the same meaning
  or speak of the same subject, AND have nearly the same syntax**. Semantic closeness alone is not
  enough. A pair of **consecutive verses** (`|Δayah| = 1`) is never shown — their closeness is mostly
  continuity of context. **Grammatical-tool occurrences** (أداة نداء / استفهام / شرط, and the
  function-word stoplist) are removed from the shared-root signal.
- **New derived dataset `data/derived/surah_similarity.json`**, built offline by a new script:
  for every verse, its top-K neighbours *within its own surah* that pass both a syntactic gate and
  a semantic threshold, with the signals behind the score (cross-encoder, dense cosine, shared
  roots, syntactic similarity from the QAC morphology), plus per-surah groups. Registered
  in `quran_data/paths.py` + `manifest.py`, read through one cached loader. Rebuildable; never
  hand-edited.
- **A frozen gold set and a measurement before any weight is chosen**: a list of intra-surah verse
  pairs, drafted by Claude under the user's definition — positives (same meaning or subject AND
  near syntax) and three kinds of negatives (same subject / different syntax; same syntax /
  different subject; consecutive) — written BEFORE the weights and thresholds are set, so the
  parameters are not fitted to the output they produce.
- **New route `GET /surah/{number}/similar`** (optional `?ayah=` for one verse's neighbours),
  model-free, served from the dataset. Mounted because the new mode calls it; the
  served-surface table gains one row.
- The existing phrase search (`GET /search`) is **not modified**.

## Capabilities

### New Capabilities
- `surah-internal-similarity`: the offline intra-surah similarity dataset (how it is built, what
  each record holds, its invariants and its evaluation gate), the model-free route that serves it,
  and the «داخل سورة» mode that renders it.

### Modified Capabilities
- `verse-study`: the `similar` tab gains a second mode («داخل سورة») beside the phrase search;
  switching modes keeps each mode's state; opening a verse from the new mode reaches «الآية في
  سياقها» like every other verse in the tab.
- `served-surface`: the consumed-surface table gains `GET /surah/{number}/similar`, called by the
  Verse Study «داخل سورة» mode.

## Impact

- **Backend**: new `retrieval/surah_similarity.py` (pure reader + group/neighbour shaping), new
  router `api/routers/surah_similarity.py`, one `include_router` in `api/main.py`, one new response
  model. No change to `/search`, `HybridSearch`, the reranker or `SimilarVerses`.
- **Build**: new `scripts/build_surah_similarity.py`. Reads verse vectors out of Qdrant, reads the
  QAC morphology (`quran_data.qac.records()`) for the syntactic signature (build time only —
  never on a request path; the treebank role is not part of it, design D3), reads `word_function.json` for the tool filter, and
  runs
  `bge-reranker-v2-m3` over the candidate pairs — so it needs the backend **stopped** (embedded
  Qdrant takes an exclusive lock) and ~1.1 GB of model memory for the run; nothing is resident at
  serve time.
- **Data**: `data/derived/surah_similarity.json` (a new `paths.py` constant + `manifest.py` entry
  under the existing `dataset-registry` rules — no requirement there changes), estimated 3–5 MB (6 236 verses × K=10
  neighbours), git-ignored like every derived file.
- **Frontend**: `frontend/src/app/verse-study/page.tsx` (mode switch + new panel, likely split into
  a component), `lib/api.ts` (one client function + types), `lib/strings.ts` (Arabic labels).
- **Tests (local-only)**: dataset invariants, route contract, `test_served_surface.py` and
  `test_quran_data.py` updated by construction, a Vitest for the mode switch.
- **Noted, out of scope**: the `verse-study` spec still names the tab «الآيات القريبة في المعنى»
  and forbids «الآيات المتشابهة», while the shipped label is «الآيات المتشابهات». This change does
  not rename the tab; the drift should be settled separately.
