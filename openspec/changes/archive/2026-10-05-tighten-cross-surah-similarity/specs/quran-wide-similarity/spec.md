## MODIFIED Requirements

### Requirement: Cross-surah closeness uses the intra-surah definition unchanged

Two verses of **different** surahs SHALL be considered close only when they pass BOTH gates of the
`surah-internal-similarity` capability, with the same frozen values: the semantic gate
(`sem = (w_ce·ce + w_dense·dense) × (floor + (1 − floor)·cov) ≥ τ_sem`, dense ignored between verbatim
verses) and the syntactic gate (`syn ≥ σ` over the same QAC `(segs, stem)` signature). Grammatical
tools SHALL be excluded from the root signal exactly as there, and a pair SHALL be stored only when
the two verses share at least one content root.

The build SHALL reuse the intra-surah builder's functions and constants for the signature, the
syntactic similarity, the coverage, the semantic score, the candidate cap and the neighbour selection,
not a copy of them. Three rules SHALL apply to the cross-surah population only:

- `dense` SHALL be the cosine's average-rank percentile among the cross-surah pairs that pass the
  syntactic gate (this rule included), so that it is symmetric and spread over the candidates the
  semantic gate decides between;
- a pair whose longer signature has at most `short_exact_max_len = 3` elements SHALL pass the
  syntactic gate only when `syn = 1`;
- in each verse's list, a neighbour SHALL be kept only when its score is at least `ρ = 0.5` times the
  best score of that list.

#### Scenario: The parameters are the intra-surah ones

- **WHEN** the headers of `quran_similarity.json` and `surah_similarity.json` are compared
- **THEN** `σ`, `τ_sem`, `w_ce`, `w_dense`, `floor`, `K`, `M`, `signature` and `dense_on_verbatim`
  SHALL be equal
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

### Requirement: Measured against a cross-surah gold set frozen beforehand

Before the first build, a gold set of cross-surah pairs SHALL be committed to the local evaluation
harness (`tests/eval/quran_similarity_gold.json`), drafted by Claude from the verse texts alone under
the intra-surah gold's drafting rule, each pair with its reason: positives (same meaning or subject
AND near syntax) and two kinds of negatives (same subject / different syntax; same syntax / different
subject). A target SHALL be pre-registered before the build. The gold set SHALL measure the reused
parameters; it SHALL NOT be used to derive or tune them.

Version 2 of the gold set SHALL add a second sample drawn at random (fixed seed) from the cross-surah
pairs passing `σ`, labelled from the verse texts alone by three independent labellers shown no score,
a label requiring two votes of three; each added pair SHALL carry `sample: "v2-syntax-survivors"`, and
pairs without a majority SHALL be left out and counted.

An evaluation script SHALL report recall@K of the positives, each positive's rank, the positives lost
at each stage (pre-filters, syntax gate, short-pair rule, candidate cap, semantic gate, shared-root
rule, top-K, relative cut) and the negatives stored, the second sample reported apart, and SHALL
refuse a gold file whose digest differs from the header's. A result short of the target SHALL be
recorded as the result.

#### Scenario: The header proves which gold set was measured

- **WHEN** the dataset header is read
- **THEN** its gold digest SHALL equal the sha256 of the committed gold file

#### Scenario: The pre-filters lose no positive

- **WHEN** the evaluation runs
- **THEN** zero positives SHALL be reported lost at the length or bag pre-filter stage

#### Scenario: The second sample is reported apart

- **WHEN** the evaluation runs on gold version 2
- **THEN** it SHALL report the second sample's positives and negatives stored separately from the
  first sample's figures
