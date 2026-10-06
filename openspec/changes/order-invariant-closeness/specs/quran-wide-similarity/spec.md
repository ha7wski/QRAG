## MODIFIED Requirements

### Requirement: Cross-surah closeness uses the intra-surah definition unchanged

Two verses of **different** surahs SHALL be considered close only when they pass BOTH gates of the
`surah-internal-similarity` capability, with the same frozen values: the semantic gate
(`sem = (w_ce·ce + w_dense·dense) × (floor + (1 − floor)·lex) ≥ τ_sem`, dense ignored between verbatim
verses, `lex` the order-invariant matching's IDF Jaccard) and the syntactic gate (`syn ≥ σ`, the
order-robust unigram + bigram measure over the same QAC `(segs, stem)` signature). Grammatical tools
SHALL be excluded from the lexical signal exactly as there, and a pair SHALL be stored only when its
matched content mass is positive.

The build SHALL reuse the intra-surah builder's functions and constants for the signature, the
syntactic similarity, the lexical signal, the semantic score, the candidate cap and the neighbour
selection, not a copy of them. Three rules SHALL apply to the cross-surah population only:

- `dense` SHALL be the cosine's average-rank percentile among the cross-surah pairs that pass the
  syntactic gate (this rule included), so that it is symmetric and spread over the candidates the
  semantic gate decides between;
- a pair whose longer signature has at most `short_exact_max_len = 3` elements SHALL pass the
  syntactic gate only when `syn = 1`;
- in each verse's list, a neighbour SHALL be kept only when its score is at least `ρ = 0.5` times the
  best score of that list.

#### Scenario: The parameters are the intra-surah ones

- **WHEN** the headers of `quran_similarity.json` and `surah_similarity.json` are compared
- **THEN** `σ`, `τ_sem`, `w_ce`, `w_dense`, `floor`, `K`, `M`, `signature`, the syntactic measure, the
  lexical signal and `dense_on_verbatim` SHALL be equal
- **AND** the cross-surah header SHALL name `dense_population: "syntax-survivors"`,
  `short_exact_max_len` and `rho`

#### Scenario: A near-verbatim return in another surah passes both gates

- **WHEN** 3:116 and 58:17 («لَن تُغْنِيَ عَنْهُمْ أَمْوَالُهُمْ وَلَا أَوْلَادُهُم مِّنَ ٱللَّهِ شَيْـًٔا ۚ أُو۟لَٰٓئِكَ أَصْحَٰبُ
  ٱلنَّارِ ۖ هُمْ فِيهَا خَٰلِدُونَ») are compared
- **THEN** their syntactic similarity SHALL be at least `σ` and they SHALL share content roots

#### Scenario: Same subject, different construction, across surahs

- **WHEN** two verses of different surahs speak of the same subject but their syntactic similarity
  is below `σ`
- **THEN** neither SHALL list the other

#### Scenario: A short pair needs identical syntax

- **WHEN** two cross-surah verses whose longer signature has 3 elements differ in one element
- **THEN** neither SHALL list the other

#### Scenario: A weak echo is cut from a list

- **WHEN** a verse's best neighbour scores `s_best` and another of its neighbours scores below
  `0.5 · s_best`
- **THEN** that verse's list SHALL NOT hold the weaker neighbour

### Requirement: The syntactic gate's pre-filters are exact

To make the gate affordable over the 19 113 299 cross-surah pairs, the build MAY skip a pair by an
upper bound on its syntactic similarity (the length bound `m / M` with `m`, `M` the shorter and
longer word counts, or the multiset bound `|bag_A ∩ bag_B| / M` on coarse elements — both exact
under any re-ordering of blocks),
but only by a bound that is exact: a skipped pair SHALL have `syn < σ`. Every pair that is not skipped
SHALL be scored by the same syntactic-similarity function as the intra-surah build.

#### Scenario: No passing pair is pruned

- **WHEN** a random sample of cross-surah pairs dropped by the pre-filters is scored with the full
  syntactic similarity
- **THEN** every one of them SHALL score below `σ`
