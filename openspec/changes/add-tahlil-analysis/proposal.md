## Why

QLisan answers **ما هذه الكلمة؟** — root, wazn, باب, البنية, الموقع الإعرابي, العلامة, المتعلَّق,
النظائر, all verbatim from QAC and all badged «معطى محقّق». It never answers **لماذا هذه الكلمة
بالذات؟** A reader sees «وزن يُفاعِلون، باب المفاعلة» and learns a label; the reference analysis of
يُسَارِعُونَ says «صيغة المفاعلة هنا ليست على بابها في المشاركة، بل تفيد المبالغة والتكلّف في طلب
السبق» — and that sentence is the whole point of studying the word.

Measured on the reference exemplar, the split is **وصف ≈ 20 % / تعليل + تركيب ≈ 80 %**. QLisan
ships the 20 %. Tahlil is the page that composes those levels and generates the other 80 % —
under the founding constraint **تفسير القرآن بالقرآن**: no tafsīr, no external commentary, meaning
anchored on (1) the letters of the root, (2) the Quran's own usage (النظائر as empirical proof),
(3) purely linguistic core-sense lexicons (Maqāyīs). Nothing else is admissible evidence.

**Measured first** (`baseline.py` + `baseline.md`, whole corpus, before any code). Over the
49 967 rooted words: الحروف evidence 100 % *after one key fix*, صرفي 94.1 %, نحوي 100 %,
دلالي 99.1 %, **all four blocks grounded for 93.2 %** (46 557 words). Five findings that the
aggregate hides and that shape this spec:

1. **A silent 9.4 % letter loss.** The Hasan Abbas dataset keys hāʾ as «هـ» (letter + tatweel);
   root keys use bare «ه». Unfolded, 4 698 words lose a root letter with **no error at all** —
   the synthesis is simply built from two letters instead of three. The exact failure shape the
   mīzān work hit with lafẓ al-jalāla: complete-looking, invisible in a coverage rate.
2. **Position claims cannot be universal.** د, ذ, ط carry no `position_notes` in the source;
   16.7 % of rooted words contain one. The أول/وسط/آخر line is omitted per letter, never
   generalized.
3. **The reference example's own contrast is unattested.** «أبلغ من يُسرِعون» compares against a
   form that **does not occur in the Quran** — the only lemmas under `سرع` are يُسَٰرِعُ (III),
   سَرِيع, أَسْرَع, سِرَاع. A naive "cite an attested naẓīr or omit" rule would delete the best
   sentence of the target output. So the contrast is licensed in two checkable flavours (attested
   / deliberately-absent), and forbidden only when attestation was never checked.
4. **The reference analysis asserts a fact we do not yet compute.** «مضارع مرفوع وعلامته ثبوت
   النون» — `case_marker` covers nominal case only and returns `None` for this word. It is fully
   derivable from QAC (IMPF untagged = مرفوع, 5 582 words; `MOOD:JUS` 1 418; `MOOD:SUBJ` 1 330;
   2 594 مرفوع أفعال خمسة), so it belongs to the **deterministic** layer, not to the model.
   *(Corrected during implementation from 2 593: the original count omitted the `2FD` pgn.)*
5. **The pinned exemplar is 23:61:2 (المؤمنون), not آل عمران.** «أُولَٰئِكَ يُسَارِعُونَ فِي
   الْخَيْرَاتِ» is 23:61; آل عمران 3:114 reads وَيُسَارِعُونَ and becomes its closest naẓīr.

## What Changes

Everything is **additive**. QLisan's route, fiche, four-level order and «معطى محقّق» badge are
untouched; Tahlil is a new page reading the same assembler.

- **New page `/tahlil`** — verse picker + click-a-word (the QLisan selector, reused), rendering
  **five blocks**: الحروف/الصوتي · صرفي · نحوي · دلالي · تركيب/القيمة الزائدة. Output is
  **Arabic only**; labels stay bilingual as in QLisan.
- **Block 1 الحروف is a rebuild, not a port.** The existing `/lexical` letter path reads the old
  28-row CSV. Tahlil reads the new **`arabic_letter_semantics_hasan_abbas.json` v0.2.0** (29
  entries, page-cited, per-position notes, صفات) through a key-normalizing loader, decomposes the
  root, gives each letter صفات (**fact**) + دلالة + position (**تأويلي**), synthesizes a core
  sense, and **validates it against the naẓāʾir** — a synthesis that fails validation is marked
  weak and logged, never silently shown.
- **Two new versioned KBs**: **دلالة الصيغة** (وزن/باب/زمن/صيغة → sense, one row per entry with a
  named صرف/نحو/بلاغة provenance) and the **contrast table** (which باب a given باب is opposed to,
  e.g. فاعَلَ ↔ أفعَلَ ↔ فعَّلَ). Both are data files with a version string that participates in the
  cache key.
- **New deterministic نحوي facts** — the verb-mood marker (مرفوع بثبوت النون / مجزوم بحذفها /
  منصوب بحذفها) computed from QAC, badged محقّق. The **Zero relation + السبب** are consumed from
  `add-nahwi-zero-relations` when present, and omitted when not.
- **A generative layer on Qwen** producing the تعليل of each block and the تركيب thesis, in the
  exact prose shape of the reference exemplar, from a prompt that receives **only** the assembled
  evidence — never the model's own knowledge of the verse.
- **Three badges everywhere**: **محقّق** (QAC fact or a deterministic derivation of one) ·
  **مُولَّد** (generated, anchored on naẓāʾir / form-KB / Maqāyīs) · **تأويلي** (letter
  phono-semantics, «أبلغ من X»). **Nothing generated is ever badged محقّق.**
- **Cite-or-omit is enforced in code, not asked of the model.** Every generated sentence carries
  machine-readable citations (letter entry + page · naẓīr ref · form-KB row id · Maqāyīs aṣl); a
  sentence whose citations do not resolve is **dropped before rendering** and logged. Citations
  are displayed under the claim, with the naẓāʾir refs linking to the verses.
- **Verse granularity** — `/tahlil` also produces a verse-level synthesis composing the analyses
  of the verse's own words. It is generated from the word analyses only. **The Zero pyramid view
  of the verse stays out of scope.**
- **On-the-fly with a SQLite cache** keyed on `(ref, prompt_version, kb_version, model)` in the
  existing `data/runtime/app.db` Store — no 49k-word batch, invalidated by a version bump.
- **Review a posteriori** — a persisted `reviewed` flag per generated analysis plus an expert
  validation action; the ~30 gold exemplars are reviewed before acceptance, the rest at leisure.
- **No new Qdrant collection.** The checklist's `quran_usage` is deliberately *not* built:
  `root_graph.json` already gives the **exact and complete** occurrence set per root
  (deterministic, no approximation), which is what cite-or-omit requires. The existing
  `quran_verses` collection + `retrieval/similar_verses.py` (root ∪ BM25 → reranker → coverage
  blend) is reused only to **rank which naẓāʾir to show** when a root has many — 41 204 words sit
  in the "10 + siblings" bucket. Recorded as a decision in `design.md` so it can be overridden.
- **No tafsīr source of any kind**, and **Rāghib is deferred** — it exists nowhere on disk;
  Maqāyīs already covers 1 142/1 642 roots (75.7 % of rooted words) and is already ingested.
- **الحقل الدلالي is re-sourced.** The checklist's "QAC ontology" **does not exist in this repo**
  (verified: no ontology file, no loader, nothing). The field is derived instead from the Quran's
  own co-occurrence around the root's occurrences — self-referential, consistent with the founding
  principle — and badged مُولَّد. Importing an external ontology is a separate change.

## Capabilities

### New Capabilities

- `tahlil-word-analysis`: the page and its contract — the five-block composition, the three-badge
  taxonomy, the cite-or-omit enforcement point, the citation payload, the cache, the `reviewed`
  flag, the coverage log, and the gold-set acceptance discipline (including the pinned 23:61:2
  scenario).
- `tahlil-huruf-phonosemantics`: block 1 — the Hasan Abbas dataset contract (key normalization,
  per-letter صفات vs دلالة separation, page citation, per-letter position honesty), the root
  decomposition, the core-sense synthesis, and its validation against Quranic usage.
- `tahlil-form-semantics`: the versioned دلالة الصيغة KB and the contrast table serving blocks 2
  and 3 — wazn/باب/زمن/derived-noun → sense with provenance, the two licensed contrast flavours,
  and the new deterministic verb-mood marker.
- `tahlil-dalali`: block 4 — core sense from letters + Maqāyīs, contextual sense inferred from the
  Quran alone (verse context + naẓāʾir), the co-occurrence-derived حقل دلالي, and the explicit
  exclusion of tafsīr and أسباب النزول.
- `tahlil-tarkib`: block 5 — the single thesis composing the four levels, its obligation to name
  the levels it composes, the contrastive clause, and the rule that it is omitted rather than
  weakened when fewer than two levels are grounded.
- `tahlil-verse-synthesis`: the verse-granularity synthesis built from the verse's word analyses,
  its own citation and badge rules, and its explicit non-goal (no Zero pyramid view).

### Modified Capabilities

- `qlisan-word-analysis`: the badge requirement grows from two states («معطى محقّق» / pending) to
  the **three-badge taxonomy** shared with Tahlil, with the invariant that no generated content
  ever carries محقّق; and the fiche fields Tahlil composes (`mizan`, `bab`, `iraab_ar`,
  `head_ref`, `nazair`, `segments`) become a **stability contract** — they may be extended, not
  renamed or re-shaped, without a delta.

## Impact

- **New backend package `tahlil/`** — `evidence.py` (assemble the grounded evidence bundle from
  the existing on-disk artifacts), `huruf.py` (block 1), `form_kb.py` (KB loaders), `citations.py`
  (the cite-or-omit validator), `prompts.py`, `tahlil_service.py` (orchestration + cache). Pure
  stdlib where possible, mirroring `analysis/` and `madar/` conventions.
- **`analysis/qac_labels.py`** — additive: the verb-mood marker derivation (nominal `case_marker`
  untouched).
- **`analysis/word_analysis.py`** — read-only consumer; **not modified** (Tahlil calls
  `analyze_word` and composes on top).
- **New data**: `data/references/sigha_dalala.json` + `data/references/bab_contrast.json`
  (versioned, provenance per row). The letters dataset stays where it is; the duplicate copy in
  `data/processed/` is removed in favour of the single `data/references/` source.
- **New data prerequisite**: `tahlil/huruf.py` now reads `data/raw/quran-morphology.txt` — the only
  source that preserves the hamza seat the processed corpus folds away. It raises a
  `FileNotFoundError` naming the 19.6 % consequence if the file is absent, so it degrades loudly
  rather than quietly wrong; the runbook must list it among the files a cloner needs.
- **API**: `POST /tahlil/word`, `POST /tahlil/verse`, `POST /tahlil/review` — new router
  `api/routers/tahlil.py` + models `api/models/tahlil.py`. No existing route changes.
- **Store**: two tables in `data/runtime/app.db` (`tahlil_cache`, `tahlil_review`).
- **Frontend**: new `frontend/src/app/tahlil/page.tsx` (+ nav entry), reusing the QLisan verse
  selector and `LevelCard`, extended with a third badge tone and a citation strip.
- **LLM**: `generation/llm_client.py` reused as-is (Qwen local default, Anthropic fallback);
  `LLM_PROVIDER` and a new `TAHLIL_GENERATION_ENABLED` toggle. With generation off, the page still
  renders every deterministic block — the same honest-degradation contract as Madār.
- **Depends on** `add-nahwi-zero-relations` for the Zero relation + السبب of block 3; ships
  without it (fields omitted, logged), so the two changes are orderable independently.
- **Not touched**: retrieval/indexing pipelines, the Qdrant schema, `ingestion/`, chat, search,
  verse-study, lexical, madar.
- **Tests (local-only)**: a ~30-word gold set of expert exemplars with 23:61:2 pinned, per-source
  sample inspection (letters / naẓāʾir / form-KB / Maqāyīs separately), a citation-resolution
  sweep, and a corpus-wide grounding sweep asserting the `baseline.md` rates do not regress.
