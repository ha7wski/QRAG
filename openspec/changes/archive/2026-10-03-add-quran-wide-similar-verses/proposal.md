## Why

«المتشابهات داخل السورة» answers *which verses of THIS surah echo the one I picked?* — and stops at
the surah's edge. The reader's next question is the same one asked of the whole Book: *where else in
the Quran is this said, built the same way?* — 3:116 «لَن تُغْنِيَ عَنْهُمْ أَمْوَالُهُمْ وَلَا أَوْلَادُهُم مِّنَ
ٱللَّهِ شَيْـًٔا ۖ وَأُو۟لَٰٓئِكَ أَصْحَٰبُ ٱلنَّارِ» returns almost verbatim in 58:17; 2:5 «أُو۟لَٰٓئِكَ عَلَىٰ هُدًى
مِّن رَّبِّهِمْ ۖ وَأُو۟لَٰٓئِكَ هُمُ ٱلْمُفْلِحُونَ» in 31:5; Ṣāliḥ's call to Thamūd in 7:73 in 11:61 and 26:142.
That is تفسير القرآن بالقرآن across surahs, and no page offers it from a chosen verse: the phrase
search («المتشابهات من عبارة») needs a typed query and uses a different notion of closeness (no
syntactic gate).

The set is still closed and finite — **19 113 299 cross-surah verse pairs** (all 19 440 730 pairs
minus the 327 431 intra-surah ones) — so it can be answered offline with the same two-gate
comparison the intra-surah dataset uses, and served as a static lookup.

## What Changes

- **In «المتشابهات داخل السورة», selecting a group verse now shows a second list, below the
  surah's close verses**: «الآيات المتشابهات في سائر القرآن» — its close verses **in the other
  surahs**, ranked, each with its surah name and ayah number and the content roots it shares with
  the picked verse. A card opens «الآية في سياقها» like every verse of the tab.
- **Same definition of «close», unchanged** (decided by the user): same meaning or subject AND
  nearly the same syntax, two gates, the frozen `σ = 2/3`, `τ_sem = 0.125`, weights and floor of the
  intra-surah build; grammatical tools out of the root signal; dense ignored between verbatim
  verses. **Verses of the anchor's own surah are excluded** (decided by the user): they are already
  listed just above, so this list shows only what it adds.
- **New derived dataset `data/derived/quran_similarity.json`**, built offline by a new script
  `scripts/build_quran_similarity.py`, reusing the intra-surah builder's signature, coverage, gates
  and cross-encoder code: for every scored verse, its top-K cross-surah neighbours passing both
  gates, with their signals and shared roots. No groups (a cross-surah group is a separate
  question). Registered in `quran_data/paths.py` + `manifest.py`, one cached loader.
- **A new gold set frozen before the build**: `tests/eval/quran_similarity_gold.json`, cross-surah
  pairs drafted by Claude under the same definition (positives; same-subject/different-syntax and
  same-syntax/different-subject negatives), with a pre-registered target. A miss is recorded as the
  result.
- **New route `GET /verse/{surah}/{ayah}/similar`**, model-free, served from the new dataset,
  independent of `GET /surah/{number}/similar` so a missing cross-surah dataset never breaks the
  intra-surah view. The served-surface table gains one row.
- `GET /search`, `GET /surah/{number}/similar` and `surah_similarity.json` are **not modified**.

## Capabilities

### New Capabilities
- `quran-wide-similarity`: the offline cross-surah similarity dataset (its candidate pipeline,
  record shape, invariants and evaluation gate), the model-free route that serves it, and the
  «في سائر القرآن» list rendered under a picked verse in «المتشابهات داخل السورة».

### Modified Capabilities
- `served-surface`: the consumed-surface table gains `GET /verse/{surah}/{ayah}/similar`, called by
  the Verse Study «المتشابهات داخل السورة» mode.

## Impact

- **Build**: new `scripts/build_quran_similarity.py`; the pure helpers it shares with
  `scripts/build_surah_similarity.py` are imported from it, not copied. Needs the backend
  **stopped** (embedded Qdrant lock) and ~1.1 GB for the reranker; the syntactic gate now runs over
  ~19 M pairs, so it needs a cheap exact pre-filter (design D3) and a per-surah checkpoint. Expected
  runtime: tens of minutes to a few hours, reported by a `--dry-run`.
- **Backend**: new pure reader `retrieval/quran_similarity.py` (imports `quran_data` only), new
  router `api/routers/quran_similarity.py`, one `include_router`, one response model.
- **Data**: `data/derived/quran_similarity.json` (+ `paths.py` constant, `manifest.py` entry,
  `loaders.quran_similarity()`), estimated ≤ 3 MB, git-ignored like every derived file.
- **Frontend**: `components/SurahSimilarity.tsx` (second list in the anchor panel, its own loading /
  error / empty states, cached under `verse-study.similar.surah.*`), `lib/api.ts`, `lib/strings.ts`.
- **Tests (local-only)**: dataset invariants, route contract, `test_served_surface.py` and
  `test_quran_data.py` by construction, a Vitest for the new list.
