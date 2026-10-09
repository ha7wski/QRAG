## MODIFIED Requirements

### Requirement: Cross-surah closeness uses the intra-surah definition unchanged

Two verses of **different** surahs SHALL be considered close only when they pass BOTH gates of the
`surah-internal-similarity` capability, with the same frozen values: the semantic gate
(`sem = (w_ce·ce + w_dense·dense) × (floor + (1 − floor)·lex) ≥ τ_sem`, dense ignored between verbatim
verses, `lex` the order-invariant matching's IDF Jaccard) and the syntactic gate (`syn ≥ σ`, the
Levenshtein similarity over the same coarse QAC signature, blocks re-orderable along the matching).
Grammatical tools
SHALL be excluded from the lexical signal exactly as there, and a pair SHALL be stored only when its
matched content mass is positive.

The build SHALL reuse the intra-surah builder's functions and constants for the signature, the
syntactic similarity, the lexical signal, the semantic score, the candidate cap and the neighbour
selection, not a copy of them. Five rules SHALL apply to the cross-surah population only:

- `dense` SHALL be the cosine's average-rank percentile among the cross-surah pairs that pass the
  syntactic gate (`syn ≥ σ`) and the short-pair rule below (that rule included, the `σ_x` and
  material rules NOT), so that it is symmetric and spread over the candidates the semantic gate
  decides between;
- a pair whose longer signature has at most `short_exact_max_len = 3` elements SHALL pass the
  syntactic gate only when `syn = 1`;
- a pair SHALL be stored only when `syn ≥ σ_x`, a cross-surah threshold with `σ_x ≥ σ`; this rule is
  a FILTER applied after the semantic gate, the short-verse material rule and the matched-mass rule,
  so it moves neither the population `dense` is ranked in nor the candidate cap;
- a pair SHALL be stored only when its shared material covers a verse: with `L` the number of
  `lemma` edges of the pair's order-invariant content-word matching (root-only edges do not count),
  `L ≥ 2`, and the IDF-WEIGHTED coverage `wcov ≥ κ`, whatever the verses' lengths — for each verse,
  the summed IDF of its root over the words joined by a `lemma` edge divided by the summed IDF over its
  content words (the `lex` weights), `wcov` being the larger of the two ratios; this rule is a FILTER
  applied after the `σ_x` rule;
- in each verse's list, a neighbour SHALL be kept only when its score is at least `ρ = 0.5` times the
  best score of that list, the material and `σ_x` rules having been applied before the cut.

A pair failing either the `σ_x` rule or the material rule SHALL NOT be stored, and the build SHALL
count it under its own stage (`syntax_cross`, `material`).

`σ_x` and `κ` SHALL be the values chosen by the calibration requirement below; the intra-surah build
SHALL NOT read them.

#### Scenario: The parameters are the intra-surah ones

- **WHEN** the headers of `quran_similarity.json` and `surah_similarity.json` are compared
- **THEN** `σ`, `τ_sem`, `w_ce`, `w_dense`, `floor`, `K`, `M`, `signature`, the syntactic measure, the
  lexical signal and `dense_on_verbatim` SHALL be equal
- **AND** the cross-surah header SHALL name `dense_population: "syntax-survivors"`,
  `short_exact_max_len`, `rho`, `sigma_cross` and `material_min_coverage`

#### Scenario: A near-verbatim return in another surah passes both gates

- **WHEN** 3:116 and 58:17 («لَن تُغْنِيَ عَنْهُمْ أَمْوَالُهُمْ وَلَا أَوْلَادُهُم مِّنَ ٱللَّهِ شَيْـًٔا ۚ أُو۟لَٰٓئِكَ أَصْحَٰبُ
  ٱلنَّارِ ۖ هُمْ فِيهَا خَٰلِدُونَ») are compared
- **THEN** their syntactic similarity SHALL be at least `σ_x`, their shared lemmas SHALL cover at least
  `κ` of the shorter verse, and each SHALL list the other

#### Scenario: Same subject, different construction, across surahs

- **WHEN** two verses of different surahs speak of the same subject but their syntactic similarity
  is below `σ_x`
- **THEN** neither SHALL list the other

#### Scenario: A short pair needs identical syntax

- **WHEN** two cross-surah verses whose longer signature has 3 elements differ in one element
- **THEN** neither SHALL list the other

#### Scenario: A few scattered shared words are not enough

- **WHEN** two long verses share content lemmas covering less than `κ` of the shorter verse's content
  words, however high their cross-encoder score
- **THEN** neither SHALL list the other

#### Scenario: Frequent lemmas weigh little

- **WHEN** 2:10 and 39:26 are compared (three shared lemmas — الله، عذاب، كان — over nine content words)
- **THEN** their weighted coverage SHALL be below `κ` and neither SHALL list the other

#### Scenario: Root-only matches are not material

- **WHEN** a pair's matching joins words by root only, with fewer than 2 `lemma` edges
- **THEN** neither SHALL list the other

#### Scenario: A weak echo is cut from a list

- **WHEN** a verse's best neighbour scores `s_best` and another of its neighbours scores below
  `0.5 · s_best`
- **THEN** that verse's list SHALL NOT hold the weaker neighbour

## ADDED Requirements

### Requirement: The cross-surah thresholds are calibrated and measured on disjoint blind samples

`σ_x` and `κ` SHALL be chosen, before the build, by a selection rule committed in the change's design
before any label is read, applied to a CALIBRATION sample, and SHALL then be measured on a disjoint
HOLDOUT sample. Both samples SHALL be drawn with a fixed seed from the cross-surah pairs stored by the
previous build of `quran_similarity.json` (the population the new rules can only shrink), stratified by
lemma coverage and by `syn`, low coverage (`lex < 0.3`) included, and SHALL exclude every pair of the
existing gold and blind files. Each pair SHALL be labelled from its two texts and the written
definition alone, by three independent labellers shown no score, a label requiring two votes of three;
pairs without a majority SHALL be left out and counted.

The written definition SHALL state that two verses are close when they say the same thing in the same
construction with enough shared lemmas, whatever their length, and that a few shared words scattered
through two otherwise different verses is not closeness.

The selection rule SHALL be computed over a grid fixed in the design, with `P` and `N` the fractions
of the calibration positives and negatives that would stay stored at a grid point. Among the points
with `N` at or under the registered ceiling (`0.15`), it SHALL pick the highest `P`, ties going to the
higher `κ` and then to the higher `σ_x`. When no point reaches the ceiling, it SHALL pick the lowest
`N`, ties going to the highest `P`, and the miss of the ceiling SHALL be recorded. The build SHALL
refuse to store pairs while `σ_x` and `κ` are not a point of that grid. The header of
`quran_similarity.json` SHALL carry `σ_x`, `κ` and the sha256 of both sample files. The evaluation SHALL
report, on the holdout, the positives and negatives stored against targets registered in the design,
and the pairs lost at the new `material` and `syntax_cross` stages; a result short of a target SHALL be
recorded as the result, and no parameter SHALL be changed after the holdout is read.

#### Scenario: The holdout is not the calibration

- **WHEN** both sample files are read
- **THEN** no pair SHALL appear in both, nor in any earlier gold or blind file

#### Scenario: The header proves which samples chose the thresholds

- **WHEN** the dataset header is read
- **THEN** its calibration and holdout digests SHALL equal the sha256 of the committed sample files

#### Scenario: The motivating pair is measured, not used

- **WHEN** the pair 2:10 / 39:26 is looked up in the two samples
- **THEN** it SHALL be in neither, and its fate after the build SHALL be reported apart in the design's
  measured result
