## 1. Token-alignment spine (the hard core — do FIRST)

- [x] 1.1 Parse `data/raw/eqtb/quranic-treebank.csv`; treat QAC `word_id` as canonical. Count words as `max(word_id) WHERE location != '_'` (exclude `(*)` elided heads and parenthesized pro-drop pronouns at `word_id=0`).
- [x] 1.2 Concatenate treebank segments per `word_id` into whole-word Uthmani/imlā'ī forms before any matching (segment ≠ word).
- [x] 1.3 Build the merge-only alignment `chakl-token → word_id | DROP` against `quran_chakl.csv`: rule cascade = strip mark-only tokens (waqf U+06D6–U+06DC, sajda U+06E9, hizb U+06DE) → strip prepended basmala on the 112 verse-1s → merge bare vocative يَا → residual clitic classes.
- [x] 1.4 Create `data/processed/overrides.json` for the ~15–30 residual verses that do not reconcile automatically; the build must consume it, not hardcode exceptions.
- [x] 1.5 Build the char-span map: a normalized copy (fold ٱ U+0671 / superscript alif U+0670 → ا U+0627, strip tashkīl) WITH an index map back to raw `quran_chakl` offsets, so highlights land on raw glyphs.
- [x] 1.6 Emit `data/processed/word_index.json` (`"s:a:w" → {uthmani, imlaai, chakl_char_span, tok_ids[], drop_reason?}`) and an audit report; the gate is "every chakl content-token maps + every QAC word covered", NOT equal counts.
- [x] 1.7 Verifier over all 6236 verses: 0 unexplained mismatches; spot-check highlighting offsets on 2:2 (with ۛ), a basmala-prefixed verse-1, and 2:255.

## 2. QAC per-word morpho-syntax index (صرفي + نحوي data)

- [x] 2.1 From the same treebank CSV, write `data/processed/qac_words.json` keyed off the spine → `{form, segments[], root, lemma, pos, features{}}` (root/lemma via `normalize_root`, never `normalize_text`); rootless words (proper nouns) marked, not dropped.
- [x] 2.2 Write `data/processed/qac_syntax.json` (`{role, head_position, relation, dependents[]}`) resolved against `RelLabels.csv`; unannotated words absent (⇒ نحوي unavailable), not fabricated.
- [x] 2.3 Build `data/processed/root_graph.json` (root → derived lemmas/forms → occurrence positions) for naẓāʾir.
- [x] 2.4 Wire all artifacts into `ingestion/run_pipeline.py` without altering existing root-level outputs; add `@lru_cache` loaders in the `indexing/corpus.py` style.
- [x] 2.5 Cross-validate a sample against the legacy `morphology.json` (mustafa0x) + CAMeL; flag divergences (treebank is source of truth).
- [x] 2.6 Unit-test: known positions (1:1:2 اسم → root سمو; 2:255) resolve correctly; determinism; token count per verse matches the spine.

## 3. Deterministic analysis assembler (صرفي + نحوي)

- [x] 3.1 `analysis/word_analysis.py`: given `(surah, ayah, word)`, assemble صرفي from `qac_words.json` and نحوي from `qac_syntax.json`, both LLM-free; include root-graph siblings (naẓāʾir) with positions.
- [x] 3.2 Per-level `available` flags; نحوي `available:false` when the word has no treebank annotation; no LLM fallback anywhere.
- [x] 3.3 Unit-test determinism and availability flags.

## 4. Backend API — QLisan fiche endpoint

- [x] 4.1 `api/models/qlisan.py`: `QlisanRequest{surah, ayah, word}` and `QlisanResponse{sawti, sarfi, nahwi, dalali}`, each level a labelled sub-model with `available: bool` (mirror the Madār field-per-layer shape).
- [x] 4.2 `api/routers/qlisan.py` (`APIRouter(tags=["qlisan"])`, `POST /qlisan/word`); validate input (400 empty, 404 when the `surah:ayah:word` position does not exist); build deterministic levels via `analysis/word_analysis.py`; register with one `include_router` line in `api/main.py`; lazy `_service(request)`.
- [x] 4.3 Provide the selectable verse with QAC-aligned token boundaries from `word_index.json` (reuse `GET /verse/...` or add a QLisan verse+tokens path) so UI token index == QAC word index.
- [x] 4.4 `dalali` returns `{available:false, message}` until section 7.
- [x] 4.5 Endpoint tests: four ordered levels; 404 on bad position; a test asserting the deterministic levels contain no LLM-produced field.

## 5. Frontend — QLisan page and word selection

- [x] 5.1 Create `src/app/qlisan/page.tsx` (`"use client"`, `Suspense` if it reads search params); add `{ href: "/qlisan", label: "QLisan", icon }` to the `links` array in `components/Navbar.tsx` (optional card in `app/page.tsx`).
- [x] 5.2 Add typed client functions in `src/lib/api.ts` (`qlisanWord(...)` + the verse+tokens fetch).
- [x] 5.3 Verse loader UI: reuse the inline surah `<select>` from `getSurahs()` + ayah input (clamped to surah length); render the vocalized verse.
- [x] 5.4 Adapt `HighlightedVerse` so each token is a clickable `<button>` whose boundaries come from the spine char-spans (NOT a naïve whitespace split); clicking selects/highlights the word and requests its fiche.
- [x] 5.5 Render the four-level fiche in fixed order صوتي → صرفي → نحوي → دلالي using `ArabicText`; visibly distinguish deterministic levels from the sourced دلالي level; show pending/unavailable levels, don't omit them.
- [x] 5.6 Link root siblings (naẓāʾir) in the صرفي level to their verses via existing deep-links.

## 6. Phonetic level (صوتي) — increment 2

- [ ] 6.1 `analysis/phonetics.py`: G2P + syllabation from the vocalized rasm (`chakl_by_ref()`), no LLM; do NOT use the treebank `phonetic` column (incomplete + context-baked). Optionally adopt the Halabi Arabic-Phonetiser.
- [ ] 6.2 Build a static makhraj/ṣifāt table ATTRIBUTED to a named recitation school; annotate each letter; response names the authority.
- [ ] 6.3 `analysis/tajwid.py`: reimplement the tajwīd rule logic using `quran-tajweed`'s CC-BY DATA (its code is unlicensed); map char-offset rule spans → word positions via the spine; empty list when none apply; unavailable when no vocalized form.
- [ ] 6.4 Handle cross-word rules (idghām/iqlāb/sun-letter lām) at verse level, anchored to the selected word and its neighbour.
- [ ] 6.5 Wire صوتي into the assembler + response; flip its `available` flag on.
- [ ] 6.6 Unit-test transcription/syllabation/tajwīd on known words (a مدّ, an إدغام, a cross-word case); verify determinism.

## 7. Dalālī extractive layer (دلالي) — increment 3

- [ ] 7.1 Extend `scripts/build_maqayis_dataset.py` from aṣl-only to full-entry chunks; keep the `madar/maqayis_store.py` root-key lookup pattern (`normalize_root` key + geminate fallback, offline).
- [ ] 7.2 Acquire a public-domain-provenance edition of *Mufradāt* al-Rāghib (avoid NC/share-alike digital editions); parse root→entry into a store parallel to `MaqayisStore` (`analysis/lexicon_store.py`).
- [ ] 7.3 دلالي service = deterministic root→entry lookup returning VERBATIM lexicon text with citation (source = citation); no LLM, no Qdrant collection; no-entry ⇒ `available:false`.
- [ ] 7.4 Render دلالي as cited verbatim entries + naẓāʾir, visibly distinct from and never merged into the deterministic levels.
- [ ] 7.5 Tests: attested root returns verbatim entry + citation; unknown root ⇒ unavailable (never fabricated); دلالي never blended into deterministic levels; `quran_verses` chat/search unchanged.
- [ ] 7.6 (DEFERRED, off by default) If generative synthesis is later built: dedicated `qlisan_lexicon` Qdrant collection (reuse embedder/BM25/reranker), per-claim ENTAILMENT + verbatim-span grounding (NOT id-membership), drop failing claims, fall back to the extractive view.

## 8. Licensing hygiene, validation, and docs (private/local posture)

- [ ] 8.1 Create `data/SOURCES.md` recording each source + license (QAC/eqtb GPL; Tanzil CC-BY-3.0; quran-tajweed data CC-BY-4.0 / code unlicensed; lexicon editions); confirm `quran.csv`/`quran_chakl.csv` provenance; do NOT ingest any NC source.
- [ ] 8.2 Run `openspec validate add-qlisan-word-analysis` and fix any issues.
- [ ] 8.3 Update `CLAUDE.md`/`architecture.md` for the new ingestion artifacts, endpoint, route, and env toggles; note that no new Qdrant collection is added in the MVP.
- [ ] 8.4 Manually verify the incremental flow: increment 1 shows صرفي/نحوي with صوتي/دلالي pending; later increments flip them on without regressing earlier levels.
