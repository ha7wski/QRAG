## Context

The similarity relation is a whole-verse relation by construction (D1 of the cross-surah build). A
shared passage is a different question — «does this wording come back elsewhere?» — and needs a
LOCAL comparison. It is also a lexical question: a passage is shared wording, so it needs no
embedding and no cross-encoder.

## Decisions

Every value below is frozen BEFORE the gold set exists and before the build is run on the corpus.

### D1 — tokens

One token per QAC word (`quran_data.qac.records()`, positions `s:a:w`): the `LEM:` of the word's
STEM segment (a segment carrying neither `PREF` nor `SUFF`); a word with no stem lemma takes its
surface folded by `arabic_text.bare()`. *Settled at implementation, before any measurement:* a word
with several stem segments (563 words, «مِمَّا» = مِن + ما) is one token, its stem lemmas joined by `+`
in segment order; a matched position counts as content when the words on BOTH sides carry a root.
So the proclitics و/ف/ب/ل/ال and the suffixed pronouns never
decide a match, and inflection is absorbed by the lemma (يَسْعَىٰ ≡ سَعَى). A token is a **content**
token when the word carries a `ROOT:` feature.

### D2 — local alignment

Smith–Waterman over the two token sequences: match +2, mismatch −1, gap −1, score floored at 0.

*Amended 2026-10-05, before the gold set was measured or the corpus built.* The version frozen first
used unit scores (+1/−1/−1). Implementing it showed the decision contradicted its own example:
«جَاءَ» (+1) followed by the gap of the displaced «رَجُل» (−1) sums to exactly 0, the standard
traceback stops there, and 28:20/36:20 aligns on 5 words, below `L_MIN`. The implementer proposed
walking the traceback through such zeros, a non-standard rule written for that one pair. Instead the
scores move to the textbook +2/−1/−1, with the standard traceback (stop at a zero cell). Effect: one
match pays for one gap or one mismatch, so a passage carries on past a single displaced or substituted
word; the D3 density bound (≥ 0.75) still limits how loose a passage can be. The change is known to
reach the motivating pair; that pair is a requirement, not evidence, and the gold set stays unmeasured
until the build runs once. The best cell (highest score; ties → smallest end in A, then in B) is traced back
(diagonal first, then up, then left) to the aligned spans `A[i1..i2]`, `B[j1..j2]` (1-based QAC word
numbers, inclusive) and the number of MATCHED positions `k`. A displaced word costs two gaps
(28:20/36:20: «رَجُل» before or after «مِن أَقْصا مَدِينَة»).

### D3 — acceptance

A pair of verses of DIFFERENT surahs shares a passage iff the best alignment has
`k ≥ L_MIN = 6`, `k ≥ DENSITY = 0.75 × max(i2 − i1 + 1, j2 − j1 + 1)`, and at least
`CONTENT_MIN = 3` of the matched positions are content tokens. Six words is the shortest span the
user's example and the earlier diagnostic treat as a passage rather than a formula («إِنَّ ٱللَّهَ
غَفُورٌ رَّحِيمٌ», «وَمَا أَدْرَاكَ مَا», «فَبِأَيِّ آلَاءِ رَبِّكُمَا تُكَذِّبَانِ» stay out); 0.75 lets a quarter
of the span differ — one substitution in five, or one displaced word in eight. One passage per pair:
the best alignment only.

### D4 — candidates, exactly

Only pairs whose token MULTISETS share ≥ L_MIN tokens are aligned: `k` matched positions are `k`
equal tokens, so a pair below that bound cannot pass D3. The bound is computed exactly as
`Σ_c min(count_A(c), count_B(c))` via sparse products of count-threshold indicator matrices.

### D5 — the dataset

`data/derived/quran_passages.json`, schema 1: `build` (token rule, `l_min`, `density`,
`content_min`, scores, gold sha256), and `passages`: a list of
`{"a": "s:a", "b": "s:a", "wa": [i1, i2], "wb": [j1, j2], "k": int, "roots": [...]}` with `a` in the
lower surah, sorted by `(a, b)`; `roots` are the content roots of the matched words (canonical,
hamza-bearing). Byte-identical across two builds. No model, no Qdrant: it may run with the backend up.

### D6 — the routes

`GET /quran-passages/matrix` returns the similarity map's shape (`surahs` (all 114), `cells`
`{a, b, pairs, verses_a, verses_b}` with `a < b`, `total_pairs`, `max_pairs`).
`GET /quran-passages/pairs/{a}/{b}` returns `{a, b, surah_name_a, surah_name_b, verses_a, verses_b,
pairs: [{u: Verse, v: Verse, words: k, span_u: [start, end], span_v: [start, end]}]}`, `u` in the
lower surah, ordered `k` desc then `(u, v)`; spans are half-open CHARACTER offsets into each verse's
`text_ar_tashkil`, from the first aligned word's start to the last one's end, read from
`word_index.json`'s `chakl_char_start/end` and rebased past the Basmala the displayed āya-1 text is
stripped of. Same error rules as the similarity map: `a == b` → 422 before any read, out of range →
422, empty cell → 200 with `pairs: []`, `(b, a)` ≡ `(a, b)`, missing / unknown-schema / malformed →
503 naming `python scripts/build_quran_passages.py`. Every verse through `verse_from_record`.

### D7 — the map

Inside «الآيات المتشابهات في سائر القرآن», a two-way switch above the chart: «الآيات المتشابهات» (default,
today's map) / «المقاطع المشتركة». The chart component is reused with the relation's matrix; axes,
bins, tooltip, keyboard rules unchanged. A picked passage cell lists its pairs: the count heading, then
per pair both verses with the passage marked (`<mark>`, green tint) and «N كلمات مشتركة»; a verse opens
«الآية في سياقها». State per relation under `verse-study.similar.quran.*`.

### D8 — gold and target

`tests/eval/quran_passages_gold.json` is drafted from the verse texts alone, blind to this build
(no alignment run on any pair): positives (two verses of different surahs sharing a contiguous phrase
of ≥ 6 words, identical up to proclitics, case endings, pronoun suffixes and at most one substituted
or displaced word per five), negatives of two kinds (≥ 6 common words scattered, not a phrase; a
shared phrase of only 3–5 words). 28:20/36:20 is excluded (it motivated the change). Target,
pre-registered: recall of positives ≥ 0.80; negatives found ≤ 10 % of negatives; and 28:20/36:20
found (a requirement, reported apart).

## Risks / Trade-offs

- Lemmas merge homographs and split suppletive forms → accepted; one passage word in four may differ.
- Common long formulas (e.g. «خَالِدِينَ فِيهَا أَبَدًا ۖ ذَٰلِكَ الْفَوْزُ الْعَظِيمُ») will fill some
  cells → they ARE shared passages under the definition; the cell lists show them.
