## Context

Two cross-surah relations exist, each built and measured on its own:

- **Similarity** (`quran_similarity.json`): whole-verse closeness, `s = sem × syn` behind a syntax
  gate, a semantic gate, a short-pair rule, a relative cut and a top-K. Its distinct unordered pairs
  are the set **S** (451 today).
- **Shared passage** (`quran_passages.json`): a Smith–Waterman local alignment of QAC stem lemmas
  with ≥ 6 matched words, density ≥ 0.75, ≥ 3 content words. Its pairs are the set **W** (2 191).

|S ∩ W| = 151, |S \ W| = 300, |W \ S| = 2 040. The map shows them behind a switch. The user wants
one relation, one score, and the common part coloured.

What was looked at before these decisions, so that it is on record: the sizes above; the length of
the best local alignment of the 300 pairs of S \ W (1 word: 12, 2: 39, 3: 126, 4: 67, 5: 46, ≥ 6: 10);
the quartiles of `k / min length` over W (pairs in S: 0.86 / 1.0 / 1.0; pairs not in S:
0.35 / 0.47 / 0.62); which gold pairs S and W hold (D10); the alignment of 26:203/37:54 («قال هل»,
2 words). None of these is a measurement of the combined score: `sim` does not exist yet for the
2 040 pairs of W \ S.

## Goals / Non-Goals

**Goals:** one pair set, one score, one map; the common part visible on every pair that has one; the
existing builds, parameters and gold measurements untouched; every new value frozen here before the
build runs.

**Non-Goals:** changing what either input relation accepts (no gate, threshold or weight of
`build_quran_similarity.py` or `build_quran_passages.py` moves); the intra-surah view; fixing the
passage relation's two recorded misses (best-scoring vs best-accepted alignment, أَنَّ ≠ إِنَّ); a new
gold set.

## Decisions

Every value below is frozen BEFORE `build_quran_close_verses.py` is run on the corpus.

### D1 — the pair set is the union

`P = S ∪ W`: a pair of verses of different surahs is in the unified relation iff the similarity
dataset stores it in either verse's list, or the passage dataset holds it. Each pair records which
input holds it (`from`: `"similarity"`, `"passage"`, or both). Neither input is rebuilt or filtered.

*Alternative considered — passage first, then closeness (the first wording of the request):* it
keeps 151 of the 451 close pairs. The user confirmed the union on 2026-10-05.

### D2 — `sim`: the similarity score, ungated where it was never computed

`sim = sem × syn`, the cross-surah build's own score, in [0, 1].

- For a pair of S: the stored `s`, READ from `quran_similarity.json` (the higher one should the two
  sides ever disagree, as the reader does today). It is not recomputed.
- For a pair of W \ S: computed with the functions IMPORTED from `build_quran_similarity.py` (which
  imports them from the intra build) — `syn_similarity` over the same signatures, `cov_similarity`,
  the symmetrised cross-encoder, `sem_score` (dense ignored between verbatim verses) — and with NO
  gate: σ, the short-pair rule, the cap M, τ_sem, the relative cut and K decide membership in S, and
  membership here is D1. `dense` is the cosine's average-rank percentile among the syntax survivors,
  the population the similarity build ranks in; the build re-derives that population by running the
  imported syntax stage (0.5 s) and ranks the W \ S pairs against it, as the similarity build
  already does for a gold pair its gate dropped.
- These pairs are cross-encoded in a call of their own (~4 080 predictions).

Integrity check: for every pair of S the build recomputes `dense` and compares it with the stored
value (4 decimals). A difference means the vectors or the similarity dataset moved since it was
built; the build refuses and names the rebuild order.

*Alternative considered — `sim = sem` (meaning only) for W \ S:* S pairs would then be scored on
`sem × syn` and the others on `sem`, two scales in one list.

### D3 — `pas`: the share of the shorter verse a shared PASSAGE covers

For a pair of W: `pas = k / min(n_a, n_b)`, `k` the passage's matched words and `n` each verse's QAC
word count (the alignment's own sequences), in (0, 1]. For a pair not in W: `pas = 0`.

A common part shorter than a passage does not score. The line between a formula and a passage is
the passage relation's frozen `L_MIN = 6`, and its gold set labels «a shared phrase of only 3–5
words» a NEGATIVE (`neg_short_formula`); scoring such a part would reward what that gold calls a
miss. Worked from the definition: 26:203/37:54 share «قال هل», 2 of 4 words — `pas` would be 0.5 for
a pair whose stored closeness is already contested.

### D4 — the score

`score = 1 − (1 − sim)(1 − pas)`, rounded to 4 decimals. Either measure alone can carry a pair; both
together rank it higher than either; `pas = 0` leaves `score = sim`, so the 300 pairs of S \ W keep
their order. Pairs are ordered by score descending, then `(u, v)` ascending.

*Alternatives considered:* a weighted sum halves a pair that is strong on one axis only (28:20/36:20
would rank below every close pair); `max` ignores that both agree.

### D5 — the common part, shown on every pair that has one

- Pair of W: the stored passage (`wa`, `wb`, `k`).
- Pair of S \ W: the best Smith–Waterman alignment, by the functions imported from
  `build_quran_passages.py` (same tokens, +2 / −1 / −1, same traceback and tie rule), kept as a
  common part iff `k ≥ MARK_MIN = 2`, `k ≥ 0.75 ×` the longer aligned span (the passage relation's
  density) and at least `MARK_CONTENT_MIN = 1` matched position joins two content words. Otherwise
  the pair has no common part.

The common part is DISPLAY for S \ W (D3): it never changes `pas`.

Each common part is stored as word spans AND as half-open character spans into each verse's
displayed `text_ar_tashkil` (first aligned word's start to the last one's end, from
`word_index.json`'s `chakl_char_start/end`, rebased past the Basmala `strip_leading_basmala`
removes). The spans are computed at BUILD time: `word_index.json` costs 64 MB resident, and
`GET /verse/{s}/{a}/similar` is called for every picked verse; the reader stays a reader of one
small file. A span that falls outside the displayed text fails the build.

### D6 — the dataset

`data/derived/quran_close_verses.json`, schema 1, registered in `paths.py` / `manifest.py` /
`loaders.py` (`QURAN_CLOSE_VERSES_JSON`, `loaders.quran_close_verses()`):

    build:    scope "cross-surah"; the score, sim and pas rules as text; mark_min, mark_content_min,
              mark_density; reranker, embedder;
              inputs: {quran_similarity: sha256, quran_passages: sha256}   # the files composed
              gold:   {quran_similarity_gold: sha256, quran_passages_gold: sha256}
    unscored: ["s:a", …]     # the similarity dataset's list, minus any verse holding a pair
    pairs:    [{"a": "s:a", "b": "s:a",            # a in the lower surah; sorted by (a, b)
                "score", "sim", "pas",
                "from": ["similarity"] | ["passage"] | ["similarity", "passage"],
                "roots": [...],                    # shared content roots, similarity's definition
                "k", "wa": [i1, i2], "wb": [j1, j2],      # the common part: all five present,
                "ca": [start, end], "cb": [start, end]}]  # or all five absent

`roots` is one definition for every pair: the content roots the two verses share, as the similarity
build computes them (stored for S; computed the same way for W \ S — non-empty on today's inputs,
and an empty list is legal). Two builds over the same inputs are byte-identical.

Build order, recorded in the manifest: `build_quran_similarity.py` → `build_quran_passages.py` →
`build_quran_close_verses.py`. The backend must be STOPPED (verse vectors come out of the embedded
Qdrant) and the cross-encoder is loaded (~1.1 GB). No checkpoint: one cross-encoder call.

### D7 — one reader, three routes, two routes removed

`retrieval/quran_close_verses.py` — pure (imports `quran_data` only, no model, no Qdrant) —
replaces `retrieval/quran_similarity.py` and `retrieval/quran_passages.py`, both deleted. Same
functions as today (`ayah_view`, `pair_set`, `matrix`, `cell_pairs`), same `MalformedEntry` → 503
discipline, same memoisation on the loaded dict.

Route paths are unchanged, so the client keeps its URLs:

- `GET /quran-similarity/matrix` — same shape; cells count the pairs of P.
- `GET /quran-similarity/pairs/{a}/{b}` — each pair
  `{u, v, score, roots, words: k | null, span_u: [s, e] | null, span_v: [s, e] | null}`, ordered by
  score desc then `(u, v)`. Error rules unchanged.
- `GET /verse/{surah}/{ayah}/similar` — the verse's pairs of P, score desc then `(surah, ayah)`,
  each neighbour `{verse, score, roots, words | null, span | null}`, `span` in the NEIGHBOUR's text.
  **No cap at K**: P is a pair set, and capping one verse's list would make the panel disagree with
  the map (53 verses hold more than 10 pairs; the longest list is 31).
- 503 names `python scripts/build_quran_close_verses.py`.
- `GET /quran-passages/matrix` and `/pairs/{a}/{b}` are deleted with their router and models, and
  named in `test_served_surface.py`'s removed list. Deleted, not quarantined: nothing they answered
  is lost, the unified routes answer it.

### D8 — the frontend

- `QuranSimilarityMap.tsx`: the relation switch, the passage panel and the state under
  `verse-study.similar.quran.passages.*` / `.relation` go. One chart over the unified matrix; axes,
  log bins (1, 2, 3–4, 5–8, 9–16, 17+), tooltip, keyboard and caching rules unchanged. A picked cell
  lists its pairs: both verses, the common part in `<mark>` when the pair has one, «N كلمات مشتركة»
  under it, the root chips when `roots` is non-empty, no numeric score.
- `SurahSimilarity.tsx`, section «الآيات المتشابهات في سائر القرآن»: each close verse marks its span
  and shows «N كلمات مشتركة» when it has one. The picked verse itself is not marked (its span differs
  per neighbour). The empty-list sentence becomes «لا توجد في سائر القرآن آية تشابهها أو تشاركها
  مقطعًا».
- The marked verse text moves to `SimilarVerseParts.tsx`, shared by both.
- `lib/api.ts`: `getQuranPassagesMatrix` / `getQuranPassagesPairs` and their types deleted; the
  similarity types gain the nullable fields.

### D9 — the two input datasets stay

`quran_similarity.json` and `quran_passages.json` keep their builds, loaders, gold sets and eval
scripts. Their manifest consumers become the unified build and their own eval script; no route
reads them any more.

### D10 — gold and targets

No new gold set: the two existing files, unchanged, their digests in the header.
`scripts/eval_quran_close_verses.py` refuses to report when either gold digest or either input
digest differs from the header's.

Unified labels: a **positive** is a positive of either gold file; a **negative** is a
`neg_same_syntax_diff_subject` or `neg_diff_subject_diff_syntax` pair of the similarity gold, or a
`neg_scattered` or `neg_short_formula` pair of the passage gold. `neg_same_subject_diff_syntax` is
reported apart and enters no target: the unified relation has no syntax requirement, so a
same-subject pair that shares a passage is not a miss. A pair in both files counts once.

Known before the build, because membership is D1 (reported, NOT targets): positives present —
similarity gold first sample 51 / 60 (41 through S, 10 more through W), second sample 6 / 17, passage
gold 38 / 40; negatives present 7 (4 `neg_same_syntax_diff_subject` and 2 `neg_short_formula`
through S, 1 `neg_scattered` through W); 5 `neg_same_subject_diff_syntax` pairs present through W.

Pre-registered, unmeasurable before the build (they depend on `sim` for W \ S and on the score):

- **U1 — ordering.** AUC ≥ 0.80, the probability that a gold positive present outscores a gold
  negative present (ties ½). Reported beside the AUC of `sim` alone and of `pas` alone, on which
  there is no target.
- **U2 — the motivating pair.** 28:20/36:20 is present with `pas > 0`, and its common part reads
  «وَجَاءَ … قَالَ» in both verses.
- **U3 — the frame-only pair.** 26:203/37:54 has `pas = 0` and sits in the lower half of the list of
  cell (26, 37).
- **U4 — integrity.** `len(pairs) = |S ∪ W|`, and the D2 dense check passes.

A miss is recorded as the result. No value of D2–D5 moves after the build.

### Amendments at implementation, before the build ran (2026-10-05)

No value of D1–D10 moved. Recorded because they settle wording the build exposed:

- **D4 / spec scenario «Both measures raise the score».** The scenario said «greater than both»;
  under D4 a measure equal to 1 gives `score = 1`, and on the inputs 81 of the 151 pairs of S ∩ W
  have `sim = 1` or `pas = 1`. The scenario now reads «at least the larger, and greater than both
  before rounding when both are below 1» — what D4 always meant.
- **D10 — a pair labelled in both gold files with opposite labels** (37:80/77:44 and 77:15/83:10:
  positive in the similarity gold, `neg_short_formula` in the passage gold). D10 defines a positive
  as «a positive of either file» and a negative as «a `neg_short_formula` pair of the passage gold»,
  and its pre-counted figures (7 negatives, 51 / 60) include both pairs on both sides. The evaluation
  therefore counts each as a positive AND a negative (its comparison with itself is a tie, ½) and
  lists the conflict. «Counts once» applies to two files giving the SAME label.
- **D2 / D6 — two refusals the build adds**, which only stop it and change no value: a stored
  similarity pair that no longer passes today's syntax gate (its dense could not be ranked among the
  survivors), and a similarity header naming another reranker or embedder than the one loaded
  (stored and computed `sim` would sit on two scales).

## Risks / Trade-offs

- The map gets about 5 × denser (2 491 pairs, 935 cells, 104 surahs) → the log bins absorb it; 11
  cells reach the top bin. Cells full of long formulas are darker than today: those are pairs of P.
- U1 rests on 7 negatives → the AUC is reported with its counts; the order among unlabelled pairs is
  not measured by this change.
- `sim` is low for most of W \ S (whole-verse `syn` is below σ there) → expected: `pas` carries
  those pairs, and half of them cover under 50 % of the shorter verse, so they rank low.
- Three builds in a chain → the header's input digests and the eval's refusal catch a stale file;
  the 503 and the manifest name the order.
- Character spans frozen at build time → `quran_chakl.csv` is a source the project never rewrites;
  a test slices every span against `word_index.json`.

## Migration Plan

Build the dataset with the backend stopped, deploy backend and frontend together (the routes keep
their paths but the pair shape gains fields and the passage routes vanish). Rollback: revert the
commit; both input datasets are untouched.
