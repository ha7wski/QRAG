## Context

The «الآيات المتشابهات» tab (`SimilarVerses` in `frontend/src/app/verse-study/page.tsx`) calls
`GET /search`: root ∪ BM25 candidates → `bge-reranker-v2-m3` → root-coverage blend → threshold. It is
a *query* path: one typed phrase, one reranker pass over ≤ 32 candidates, ~1 s. The dense E5 branch
was deliberately dropped from it (noise and ~1.7 s of query embedding for short Arabic phrases).

The new question is different in kind. «Which verses of this surah are close to each other?» has no
typed query; its unit is the **pair of verses inside one surah**, and the set of such pairs is
closed: 114 surahs, 327 431 unordered pairs, the largest surah (al-Baqara, 286 verses) holding
40 755 of them. Everything needed to score a pair is already on disk or in Qdrant: the E5 verse
vectors, the per-root verse sets and IDF behind the root channel (`LexicalRetriever.index`), the
cross-encoder `/search` already trusts, the QAC morphology (`quran_data.qac.records()`) and the
grammatical-tool list (`word_function.json`).

**The user fixed what «close» means**: two verses are close when they *share the same meaning or
speak of the same subject, AND have nearly the same syntax*. Consecutive verses close by continuity
are hidden. Grammatical tools are removed from the shared-root signal.

Constraints that shape the design: the 16 GB memory budget (no model resident to serve this; the
248 MB `qac_words.json` never on a request path); embedded Qdrant's exclusive lock; the dependency
order; the `dataset-registry` rule; and the project rule against back-fitting.

## Goals / Non-Goals

**Goals:**
- For any verse, the verses of its own surah that are close in meaning-or-subject AND syntax,
  ranked, with the shared content roots that make the closeness legible.
- For any surah, its groups of mutually close verses, as an overview before any verse is picked.
- Instant render: a static lookup, no model at serve time.
- Parameters frozen against a gold set written before the first measurement.

**Non-Goals:**
- Cross-surah neighbours for a chosen verse (a separate change).
- A textual alignment or diff of two close verses (المتشابه اللفظي as a discipline). Near-identical
  verses will surface — they satisfy both gates — but no letter-level comparison is produced.
- Changing `GET /search`, its pool caps, the reranker, or `SimilarVerses`.
- Renaming the tab (the spec/label drift noted in the proposal is out of scope).

## Decisions

### D1 — Precompute offline, serve a static file

Live scoring would cost one reranker pass per verse of the surah (286 for al-Baqara) or a resident
1.1 GB model for a view that never changes between builds. The pairs are finite and the inputs are
static, so the whole answer is computed once by `scripts/build_surah_similarity.py` and served from
`data/derived/surah_similarity.json`.

*Alternative rejected*: compute on request and cache per surah — still loads the reranker on the
request path, and makes a deployed backend's memory depend on which surahs were visited.

### D2 — Two gates, not one blended score

The definition is a conjunction, so the design keeps it one: a pair must pass a **syntactic gate**
(`syn ≥ σ`) AND a **semantic gate** (`sem ≥ τ_sem`). Blending syntax into a single weighted score
would let a very high semantic score buy back a different construction — exactly what the
definition excludes.

**Semantic score** — three signals, each covering another's blind spot:

| Signal | Source | Sees | Misses |
|---|---|---|---|
| `ce` — cross-encoder | `bge-reranker-v2-m3` on Arabic text | paraphrase, same meaning in other words | trained query→passage, not symmetric |
| `dense` — E5 cosine | vectors read back from Qdrant (Arabic + FR + EN passage) | subject / theme | narrow cosine band; partly the translators' wording |
| `cov` — content-root coverage | `LexicalRetriever.index`, tool-filtered (D4) | lexical-morphological echo | blind to synonymy |

- `ce` is **symmetrised**: mean of `σ(f(A,B))` and `σ(f(B,A))`.
- `dense` is **rank-normalised within the surah** (percentile among the surah's pairs).
- `cov` is the IDF-weighted Jaccard of the two content-root sets.
- `sem = (w_ce·ce + w_dense·dense) × (floor + (1 − floor)·cov)`, in `[0,1]`.

«Same meaning OR same subject» is served by the sum: `ce` carries meaning, `dense` carries subject,
so either can lift `sem` over `τ_sem`.

**Ranking** among pairs that pass both gates: `score = sem × syn`, so of two semantically equal
neighbours the one built more alike ranks first.

**Initial values are fixed a priori, not tuned**: `floor = 0.25` (`SEARCH_COVERAGE_FLOOR`),
`w_ce = 0.7`, `w_dense = 0.3` (the cross-encoder is the comparison `/search` trusts). `σ`, `τ_sem`
and the group threshold τ are fixed from the gold set's *written reasons* before the first build
(D7), and recorded in the header.

### D3 — The syntactic signature and its similarity

Per verse, an ordered sequence with one element per QAC word:

```
element = (segs, stem)                # a 2-tuple of hashables, compared by ==
e.g.  55:13:1 فَبِأَىِّ   → (("P:REM", "P:P", "N:INTG"), ("GEN",))
      55:13:4 تُكَذِّبَانِ → (("V", "N:PRON"), ("IMPF.IND",))
      2:1:1   الٓمٓ      → (("P:INL",), ("",))
```

**Exact construction (task 1.1 — a builder implements this with no further choice).** The input
is `quran_data.qac.records()` (the ONE reader of `quran-morphology.txt`; each `Record` is
`surah, ayah, word, segment, form, tag, features`, `tag ∈ {N, V, P}`, `features` a `|`-separated
string). The treebank (`qac_syntax.json`) is NOT read — see step 4. Split `features` on `|` and
drop empty tokens; call the result `F`.

1. **Keying.** A word is keyed `f"{surah}:{ayah}:{word}"`. Its segments are its records in file
   order (= `segment` ascending). A verse's signature is its words' elements ordered by `word`
   ascending — every word QAC records for `(surah, ayah)`, nothing skipped. QAC carries no Basmala
   word, so no rebase is needed; all 6 236 āyāt have at least one word.
2. **`segs`** — one label per segment, in segment order:
   - `tag == "P"`: `"P:" + F[0]` — QAC's particle tag, which is always the first token (`P`, `CONJ`,
     `DET`, `REM`, `NEG`, `ACC`, `EMPH`, `COND`, `ADDR`, `SUB`, `RES`, `VOC`, `INL`, …; never
     `ROOT:`/`LEM:` in the shipped file — the builder asserts it). `ACC` here is the particle إنّ,
     never a case.
   - `tag == "N"`: `"N:" + t` where `t` is the FIRST token of `F` (in order) that belongs to
     `N_POS = {PN, ADJ, PRON, DEM, REL, T, LOC, NV, INTG, COND, ADDR}`; `"N"` alone when none does
     (a common noun). `ACT_PCPL`, `PASS_PCPL`, `VN`, `INDEF` and `P` (number) are derivation or
     inflection, not part of speech, and are NOT read.
   - `tag == "V"`: `"V"`.
   No other token reaches `segs`: `ROOT:`, `LEM:`, `FAM:`, `SP:`, `VF:`, `PREF`, `SUFF`, person /
   gender / number (`3MP`, `MS`, `F`, …), `PASS` and `INDEF` are all ignored.
3. **`stem`** — a tuple with one string per STEM segment (a segment whose `F` holds neither `PREF`
   nor `SUFF`; 76 866 words have one stem, 563 have two — مِمَّا is `P` + `N:REL` — and both are
   kept, in order):
   - `V` stem: its aspect, the first of `PERF` / `IMPF` / `IMPV` in `F`, followed by `"." + m`
     when a `MOOD:m` token is present → `"PERF"`, `"IMPF.IND"`, `"IMPF.JUS"`, `"IMPV"`;
   - `N` stem: its case, the first of `NOM` / `ACC` / `GEN` in `F`, or `""` when QAC records none
     (pronouns, relatives, demonstratives);
   - `P` stem: `""`. Case is read on `N` stems ONLY and aspect on `V` stems ONLY, so the particle
     `ACC` and the prefix `P:IMPV` (لام الأمر) can never be mistaken for a feature.
   Voice (`PASS`), verb form (`VF:n`) and agreement features are not in `stem`.
4. **No treebank role** (amended 2026-10-02, before the first build — see «Frozen parameters»).
   The first version of this element carried a third member, `role = qac_syntax()[key]["role_ar"]`.
   It was removed: `role_ar` is largely a word-class label (`اسم`, `فعل`, `حرف جر`, …) redundant
   with the segment POS tags already in `segs`, and the treebank labels the SAME token
   inconsistently — «فَبِأَيِّ» in surah 55's refrain is «اسم» in 15 occurrences and «حرف استفهام»
   in the other 16 — so identical texts scored `syn = 0.75`, against the spec scenario «Identical
   constructions score 1». No other treebank field (`relation`, `relation_ar`, `head_ref`) is read
   either: adding one would be a further decision taken after the gold set exists.
5. **Muqaṭṭaʿāt.** Initial letters are `P`-tagged segments with token `INL`, so `الٓمٓ` is the
   element `(("P:INL",), ("",))` like any other word. A verse made ONLY of initials has no
   content root and is therefore `unscored` (D4) and never compared; a verse that opens with
   initials and continues (الٓر تِلْكَ …) keeps the initials as one ordinary element.

- Particles and tool words **stay** in the signature: they are syntax (a شرط construction is defined
  by its أداة), even though D4 removes them from the root signal.
- Lexical content (roots, lemmas, forms) is **not** in the signature — otherwise syntax would
  re-count what `cov` already counts.
- Known granularity, accepted before measurement: the element is finer than a reader's notion of
  «same construction» — a name in the genitive of a construct (قَوْمُ نُوحٍ) and the same slot filled
  by a bare nominative name (عَادٌ) differ in `stem`. The gold set's drafting rule counts
  SHOWN words and treats as free three kinds of change that this element charges for:
  1. **a prefixed conjunction** — `فَ`/`وَ` are segments, so 77:8:1 `فَإِذَا` (`P:REM`, `N:T`) ≠
     77:10:1 `وَإِذَا` (`P:CONJ`, `N:T`), and 23:2:1 `ٱلَّذِينَ` (`N:REL`) ≠ 23:4:1 `وَٱلَّذِينَ`
     (`P:CONJ`, `N:REL`);
  2. **a same-slot substitution that changes `segs`** — a proper name against a common
     noun (54:23:2 `ثَمُودُ` `N:PN` vs 54:33:2 `قَوْمُ` `N`; 37:159:2 `ٱللَّهِ`
     `N:PN` vs 37:180:2 `رَبِّكَ` `N` + `N:PRON`), and the construct case above;
  3. **the vocative glued to its noun** — QAC writes `يَٰقَوْمِ` as ONE word (`P:VOC` + `N` +
     `N:PRON`), so 7:79 and 7:93 are 14 and 15 QAC words where the reader counts 15 and 16.
  The four الذين-series positives (23:2/4, 23:2/9, 23:3/5, 70:23/34), 54:23/33 and 37:159/180 carry
  such uncounted mismatches, and the positives the reasons place at or near the 1/3 limit (55:56/74,
  54:16/18, 7:79/93, 77:8/10, 55:27/78, 54:15/51, 55:50/66) can be flipped by a single one. A positive
  at the drafting limit can therefore fall below `σ`; that loss is reported at the gate, not tuned
  away — `σ` stays derived from the drafting rule (moving it toward the element's granularity would
  fit it to the gold), and a miss of the 1.3 gate-loss target is recorded as the result.

`syn = 1 − lev(A, B) / max(|A|, |B|)`, word as the unit: Levenshtein over the two element
sequences with unit cost for insertion, deletion and substitution, two elements equal only when
the whole tuple is equal. Symmetric, in `[0,1]`, 1 for identical constructions, and it falls with
a length mismatch — «nearly the same syntax» excludes a 3-word verse against a 40-word one. The
gate compares `syn ≥ σ − 1e-9` (see «Frozen parameters»: `σ = 2/3`, and `1 − 3/9` and `2/3` differ
in the last floating-point bit).

*Alternatives rejected*: tree-edit distance over the treebank (QAC's dependency graph covers only
part of the corpus and its partial trees would make coverage, not syntax, decide); POS-n-gram
Jaccard (ignores order, so «فعل ثم فاعل» and its inversion would score alike).

Computed at build time only. `qac_words.json` is never read.

### D4 — Tool words out of the root signal

A verse's content-root set excludes a root when every occurrence of it in the verse is either
listed in `word_function.json` (أداة نداء / استفهام / شرط — the same filter «الكلمة في الآيات»
applies) or a token of the `SimilarVerses` function-word stoplist. The roots shown as shared are
this same set, so the reader never sees أيي shared because both verses open with «يا أيها».

### D5 — Consecutive verses excluded at build time

`|Δayah| = 1` pairs are dropped before scoring: never stored, never a group edge. Doing it in the
dataset rather than the UI means no client can show one, and it saves their cross-encoder calls.
Only `|Δ| = 1` is excluded, as asked; a refrain at `|Δ| = 2` (ar-Raḥmān 13, 16, 18…) stays.

### D6 — Candidate pipeline: cheap gates first

1. All non-consecutive intra-surah pairs between scored verses (≤ 327 431).
2. **Syntactic gate** on every pair — pure Python edit distance over short sequences, seconds to
   minutes. Survivors only go on.
3. `dense` and `cov` on the survivors (vector dot products, set ops).
4. Per verse, keep at most M = 30 survivors by `max(dense rank, cov rank)` for the cross-encoder;
   for a surah of ≤ 2M + 1 verses, keep all.
5. `ce` both directions on the kept pairs → `sem` → semantic gate → `score` → top-K.

Gating on syntax before the cross-encoder is what makes the build affordable: the expensive model
only sees pairs that can still qualify. The evaluation reports how many gold positives each stage
loses. The build checkpoints per surah so an interrupted run resumes.

### D7 — Gold set, drafted by Claude, frozen first

`tests/eval/surah_similarity_gold.json` (local-only) is drafted by Claude before the first build,
every pair carrying its reason:
- **positives** — same meaning or subject AND near syntax: refrains (55, 77, 54, 26, 37),
  parallel formulas inside a surah, narrative statements built the same way;
- **negatives** of three kinds — same subject / different syntax; same syntax / different subject;
  consecutive verses close by continuity (structurally absent after D5, kept as a regression).

Its sha256 goes into the dataset header. `scripts/eval_surah_similarity.py` reports recall@K of the
positives, each positive's rank, the positives lost at each stage (syntax gate, candidate cap,
semantic gate), and negatives of each kind stored as neighbours; it refuses a gold file whose digest
differs from the header's. The target is pre-registered in `tasks.md` before the run; a miss is
recorded as the result.

### D8 — Groups = components of the mutual-neighbour graph above τ

An edge A–B exists iff each is in the other's stored list **and** `score ≥ τ`. Groups are the
connected components of size ≥ 2. Mutuality stops a generic verse from chaining unrelated ones;
components keep refrain series whole, linked across the consecutive gaps D5 creates.

### Frozen parameters (task 1.4) — written before any pair was scored

Frozen against `tests/eval/surah_similarity_gold.json`, **sha256
`34dfcdaa9523d4f5dc5b7c02580f4dff03d2987a0cdf7422a472cccab33cd55c`** — 98 pairs: 60 `positive`,
13 `neg_same_subject_diff_syntax`, 10 `neg_same_syntax_diff_subject`, 15 `neg_consecutive`. When
these values were written, no syntactic similarity, embedding, cross-encoder score or coverage had
been computed on any pair; the gold file was drafted from the verse texts alone, and its
`conventions` state the drafting rule the values below are derived from. The file was revised once,
still before any build and on review of its text alone: two same-syntax/different-subject negatives
exceeded the drafting rule (26:59/200, 37:84/140 → replaced by 26:99/210, 37:108/146), two had
arguably one subject (55:20/50, 77:16/25 → replaced by 85:1/5, 56:12/78), and five reasons were
re-worded (26:8/67, 54:15/51, 2:48/123, 7:79/93, 55:27/78) with no label changed. No value below
moved with that revision (previous digest `71db23e2…0fee5`).

| Parameter | Value | Justification (a priori) |
|---|---|---|
| `σ` (sigma) | **2/3** | The gold drafting rule: a positive differs in construction in at most 1/3 of the longer verse's words (every positive is within it, every same-subject/different-syntax negative beyond it) ⇒ `σ = 1 − 1/3`. Stored as `0.6666666666666666`; compared as `syn ≥ σ − 1e-9` because the rule's boundary cases (1 of 3, 2 of 6, 3 of 9 — positives at the limit, and three same-syntax negatives at 1 of 3) compute to `0.6666666666666667`. |
| `τ_sem` | **0.125** | The weakest positives in the written reasons share **no** content word (81:3/81:5, 23:2/23:4, 94:2/94:4 …: parallel constructions with different lexemes), so `cov = 0` must be able to pass. Such a pair is accepted only when the model evidence sits at its own midpoint — `ce = 0.5` (the cross-encoder's decision boundary) and `dense = 0.5` (the surah median, by construction of the percentile) ⇒ base `0.7·0.5 + 0.3·0.5 = 0.5` ⇒ `sem = floor × 0.5 = 0.125`. Consequence accepted with it: a pair whose content roots coincide (`cov = 1`) passes from base `0.125`. |
| `τ_group` (τ) | **0.4** | A group is a refrain or formula series. The `0.8` below is a CHOSEN value, not one read off the reasons: the gold has no «formula» class, and its formula-like positives are stated anywhere from verbatim (the refrains of 55, 77, 26, 37: syn = 1 on the drafting rule) to 1 of 4 (54:23/33, 37:109/120, 26:66/120: 0.75). The choice is «a group link must be built at least as alike as 1 word in 5» (`syn ≥ 0.8`), which every verbatim refrain clears, with semantic evidence at least the midpoint at full coverage (`sem ≥ 0.5`) ⇒ `0.8 × 0.5 = 0.4`. Consequence accepted with it: a 1-of-4 formula pair forms a group link only if its `sem` reaches `0.4 / 0.75 ≈ 0.53`. Stricter than a neighbour link, so a group never forms on the minimum that admits a neighbour. |
| `K` | **10** | The spec's default and the recall cutoff (task 1.3); a page shows ten close verses. |
| `M` | **30** | D6 as written: caps cross-encoder calls at ≤ 2 × 30 per verse; surahs of ≤ 2M + 1 = 61 verses keep every survivor. |
| `w_ce` / `w_dense` | **0.7 / 0.3** | D2: the cross-encoder is the comparison `/search` already trusts; dense is the minority because the E5 passage also embeds the FR/EN translations. |
| `floor` | **0.25** | `SEARCH_COVERAGE_FLOOR`, the blend `/search` already ships — no new number. |

**Amendment, 2026-10-02 — before any build.** The treebank role (`role_ar`) is removed from the
D3 element, which becomes `(segs, stem)`; the builder no longer reads `qac_syntax.json`, and the
header records `"signature": "segs+stem"` (so a checkpoint computed under the old element is stale).
Decided by the user before the first real build; the justification cites no gold score.
`role_ar` is largely a word-class label redundant with the segment POS tags, and the treebank annotates the same token inconsistently — «فَبِأَيِّ» in
surah 55's refrain is «اسم» in 15 occurrences and «حرف استفهام» in the other 16 — so identical texts
would score `syn = 0.75`, violating the spec scenario «Identical constructions score 1». `σ`,
`τ_sem`, `τ_group`, `K`, `M`, the weights and `floor` are unchanged; the gold file is untouched
(its sha256 above stands).

**Open point for the builder (not decided here):** task 3.6 keeps «top-K with shared content
roots». Eight gold positives share no content word (77:8/10, 77:9/11, 23:2/4, 23:3/5, 81:3/5,
81:11/13, 82:2/4, 94:2/4 — each reason says so); `τ_sem` above lets them pass the semantic gate,
but that storage rule, if kept, makes them unreachable. Either outcome is a result to record, not a
reason to move `τ_sem`. *Resolved 2026-10-02 (user):* the rule is kept — the builder stores a
neighbour only when the two verses share ≥ 1 content root (`require_shared_root: true` in the
header), and a gold positive it drops is reported at stage `no_shared_root`.

### D9 — Placement in the tree

- `scripts/build_surah_similarity.py` — the builder (needs `indexing`, `retrieval` and `quran_data`
  together; `scripts/` sits outside the layered packages).
- `retrieval/surah_similarity.py` — the pure reader; imports `quran_data` only.
- `api/routers/surah_similarity.py` + one `include_router` + response models in `api/models/`.
  Route `GET /surah/{number}/similar[?ayah=]`.
- `quran_data/paths.py::SURAH_SIMILARITY_JSON`, a `manifest.py` entry (inputs: `verses_final.json`,
  the Qdrant collection, `morphology.json`, `quran-morphology.txt`, `word_function.json`),
  `loaders.surah_similarity()`.

### D10 — Dataset shape

```json
{
  "schema": 1,
  "build": {"reranker": "BAAI/bge-reranker-v2-m3", "embedder": "<EMBEDDING_MODEL>",
            "K": 10, "M": 30, "w_ce": 0.7, "w_dense": 0.3, "floor": 0.25,
            "sigma": 0.0, "tau_sem": 0.0, "tau_group": 0.0, "signature": "segs+stem",
            "require_shared_root": true, "gold_sha256": "…"},
  "surahs": {
    "55": {
      "unscored": [],
      "groups": [{"ayahs": [13, 16, 18, 21], "strength": 0.93}],
      "neighbours": {
        "13": [{"a": 16, "s": 0.95, "sem": 0.95, "syn": 1.0, "ce": 0.97, "dense": 0.99,
                "cov": 1.0, "roots": ["أله", "ربب", "كذب"]}]
      }
    }
  }
}
```

Lists are often shorter than K under two gates; estimated ≤ 3 MB.

### D11 — Frontend

A two-segment switch «بعبارة» / «داخل سورة» under the tab heading; «بعبارة» is today's panel,
untouched. «داخل سورة» is a new component in `frontend/src/components/`, reusing the surah select,
the verse card and the root chip of «فهرس الجذور». Groups render first; picking a verse shows its
close verses. Empty states are worded: «unscored» (no content word) vs «no close verse» (scored,
nothing passes both gates). No score, no adjacency marker (there is nothing adjacent to mark). State
under `verse-study.similar.surah.*` via `useCachedState`. The client may fetch a surah once and
switch verses locally; the route serves both shapes.

## Risks / Trade-offs

- **The syntactic gate may be too strict for long verses** — two long verses rarely align word for
  word → normalised edit distance tolerates local differences; the evaluation reports positives lost
  at the gate, and a lost positive is recorded, not tuned away.
- **Signature granularity** — too fine (every feature) and only verbatim repeats pass; too coarse
  (POS only) and every nominal sentence matches → the element is fixed in D3 before measurement.
- **The cross-encoder is a relevance model** → symmetrised, and it shares the semantic gate with
  dense and coverage.
- **Dense vectors embed the FR/EN translations** → minority weight, rank-normalised.
- **Build needs the backend stopped** and ~1.1 GB for the reranker → the build refuses to start if
  the Qdrant lock is held.
- **Stale dataset after a corpus or index rebuild** → inputs listed in the manifest; header records
  models and parameters; loader checks the schema version.

## Migration Plan

Additive: a new dataset, a new route, a new mode. Build the dataset (backend stopped) → start the
backend → ship the frontend. If the dataset is missing, the route answers 503 with the rebuild
command and the «داخل سورة» mode shows it; the phrase mode is unaffected. Rollback: remove the
`include_router` line and the mode switch.

## Resolved Questions

- **Gold-set authorship** — drafted by Claude, under the user's closeness definition (D7).
- **Consecutive verses** — hidden, at build time (D5).
- **Tool words in coverage** — removed (D4).
- **Definition of «close»** — meaning-or-subject AND near syntax, as two gates (D2, D3).

### Amendment, 2026-10-02 — after the first measurement: dense ignored between verbatim verses

Decided by the user. Between two verses whose Arabic is verbatim identical (equal
`quran_data.qac.ayah_words()` tuples — the identity the 1.3 recall rule already uses), `dense` is
not a signal: `sem = ce × (floor + (1 − floor)·cov)`, and the D6 candidate cap ranks such a pair on
its coverage rank alone. The stored entry keeps the measured `dense` and carries `"verbatim": true`
so `sem` stays reproducible; the header records `"dense_on_verbatim": "ignored"`.

*Justification, which cites no gold score:* the E5 passage is `text_ar_clean + translation_fr +
translation_en` (D2 already gives dense the minority weight for that reason). When the Arabic of two
verses is identical, every difference in their vectors comes from the translations, so `dense`
measures how the translators varied, not how the verses differ. No other parameter moved; the
gold file is untouched.

## Measured result (task 4.2, first build, 2026-10-02)

Build: signature `segs+stem`, σ = 2/3, τ_sem = 0.125, τ_group = 0.4, K = 10, M = 30, w_ce = 0.7,
w_dense = 0.3, floor = 0.25, gold sha256 `34dfcdaa…cd55c`. 319 309 non-consecutive scored pairs →
971 pass the syntax gate → 971 cross-encoded → 778 stored, 56 groups, 22 unscored ayat; file 0.13 MB.

| Pre-registered target (1.3) | Measured | |
|---|---|---|
| recall@10 of positives ≥ 0.75 | 48/60 = 0.800 | PASS |
| positives lost at candidate generation ≤ 15 % | 6/60 = 10 % | PASS |
| non-consecutive negatives in a top-3 ≤ 2 | 0 | PASS |
| consecutive negatives stored = 0 | 0 | PASS |

Positives lost by stage: syntax gate 6 (54:23/33, 37:159/180, 23:2/4, 23:3/5, 23:2/9, 70:23/34),
semantic gate 3 (77:8/10, 77:9/11, 81:3/5), no shared root 3 (81:11/13, 82:2/4, 94:2/4 — the
structural loss the kept 3.6 rule implies). No negative of any kind is stored.

**Spec scenario missed — «A refrain forms one group» (55).** The refrain comes out as two groups:
{38, 47, 57, 63, 71, 73, 75} (strength 0.991) and 24 other occurrences (0.984). Cause: the Arabic is
identical and `syn = ce = cov = 1`, but the E5 passage embeds the FR/EN translations, which vary
between occurrences, so `dense` differs; each verse's top-10 fills from its own sub-cluster and the
mutual-edge rule of D8 never links the two. Recorded as the result; not tuned (task 4.3 requires a
justification that does not rest on this outcome).

## Measured result (rebuild after the verbatim amendment, 2026-10-02)

Same parameters, plus `dense_on_verbatim: ignored`. 319 309 pairs → 971 syntax → 971
cross-encoded → 778 stored, **55 groups**, 22 unscored; file 0.14 MB.

| Pre-registered target (1.3) | Measured | |
|---|---|---|
| recall@10 of positives ≥ 0.75 | 48/60 = 0.800 | PASS |
| positives lost at candidate generation ≤ 15 % | 6/60 = 10 % | PASS |
| non-consecutive negatives in a top-3 ≤ 2 | 0 | PASS |
| consecutive negatives stored = 0 | 0 | PASS |

Losses by stage unchanged (syntax gate 6, semantic gate 3, no shared root 3). **Scenario «A refrain
forms one group» now holds**: surah 55's 31 refrain occurrences form ONE group (strength 0.9999);
the two former groups merged, hence 55 groups instead of 56.
