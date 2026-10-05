# quran-wide-similarity Specification

## Purpose

Answer, for a verse picked in «المتشابهات داخل السورة», «where else in the Quran is this said, built
the same way?» — its close verses in the OTHER surahs, under the intra-surah definition unchanged
(meaning-or-subject AND near syntax). Computed once, offline, into a derived dataset measured against
a cross-surah gold set frozen beforehand, and served model-free under the picked verse.
## Requirements
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

### Requirement: Neighbours come only from other surahs

For every verse, the cross-surah dataset SHALL list only verses of a **different** surah. A verse of
the anchor's own surah SHALL never appear, whatever its score — the intra-surah list already shows
those.

#### Scenario: No same-surah neighbour

- **WHEN** the dataset is loaded
- **THEN** no stored neighbour of any verse SHALL belong to that verse's surah
- **AND** no verse SHALL list itself

### Requirement: The syntactic gate's pre-filters are exact

To make the gate affordable over the 19 113 299 cross-surah pairs, the build MAY skip a pair by a
lower bound on its edit distance (length difference, multiset difference of signature elements), but
only by a bound that is exact: a skipped pair SHALL have `syn < σ`. Every pair that is not skipped
SHALL be scored by the same syntactic-similarity function as the intra-surah build.

#### Scenario: No passing pair is pruned

- **WHEN** a random sample of cross-surah pairs dropped by the pre-filters is scored with the full
  syntactic similarity
- **THEN** every one of them SHALL score below `σ`

### Requirement: An offline cross-surah similarity dataset

The system SHALL ship `data/derived/quran_similarity.json`, built by
`scripts/build_quran_similarity.py`, registered in `quran_data/paths.py` and `quran_data/manifest.py`
(producer, inputs, consumers, rebuild command, backend-must-be-stopped note) and read only through one
cached loader in `quran_data/loaders.py`.

For each scored verse it SHALL record at most K neighbours, each carrying the neighbour's reference
(`"surah:ayah"`), the composite score `sem × syn` in `[0, 1]`, the signals (`sem`, `syn`, `ce`,
`dense`, `cov`), `verbatim: true` when dense did not enter `sem`, and the shared content roots in
their canonical, hamza-bearing spellings. Verses with no content root SHALL be listed in a top-level
`unscored` list and have no neighbours. The header SHALL name the models, every parameter, the scope
`cross-surah`, the dense population, and the sha256 of the cross-surah gold set. The loader SHALL
refuse an unknown schema version with the rebuild command.

#### Scenario: Every stored pair passes both gates

- **WHEN** any stored entry is read
- **THEN** its `syn` SHALL be ≥ `σ` and its `sem` ≥ `τ_sem` as recorded in the header
- **AND** its `roots` SHALL be non-empty

#### Scenario: The score is symmetric

- **WHEN** verse u lists v and v lists u
- **THEN** both entries SHALL carry the same score and the same signals

#### Scenario: Neighbours are deterministically ordered

- **WHEN** a verse's neighbours are read
- **THEN** they SHALL be sorted by score descending, ties broken by (surah, ayah) ascending
- **AND** two builds over the same inputs and parameters SHALL produce byte-identical files

#### Scenario: A disjointed-letters verse is unscored

- **WHEN** the dataset is read
- **THEN** `2:1` SHALL be in `unscored` and in no verse's neighbour list

#### Scenario: A missing dataset names its rebuild command

- **WHEN** the loader is called and `quran_similarity.json` is absent
- **THEN** it SHALL raise `DatasetMissing` naming `python scripts/build_quran_similarity.py`

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

### Requirement: A model-free route serves one verse's cross-surah neighbours

The backend SHALL serve `GET /verse/{surah}/{ayah}/similar`, reading only `quran_close_verses.json`
(capability `close-verses`). It SHALL load no model and query neither Qdrant nor the reranker. The
response SHALL carry the anchor verse, `unscored`, and EVERY pair of the unified relation holding
that verse — not capped at K — ordered by combined score descending then by reference, each
neighbour with its verse (carrying `surah_name_ar`), the score, the shared roots and, when the pair
has a common part, its matched word count (`words`) and its half-open character span in the
NEIGHBOUR's `text_ar_tashkil` (`span`), both null otherwise. Every verse SHALL go through
`verse_from_record`. An unscored anchor SHALL return an empty list with `unscored: true`; a scored
anchor with no close verse an empty list with `unscored: false`; neither is an error.

#### Scenario: Neighbours of one verse

- **WHEN** the client requests `GET /verse/3/116/similar`
- **THEN** the response SHALL list verses of other surahs only, in score order, each with its surah
  name and shared roots, including 58:17

#### Scenario: A passage-only neighbour is listed

- **WHEN** the client requests `GET /verse/28/20/similar`
- **THEN** the response SHALL list 36:20 with `words` and a `span` whose text starts with «وَجَاءَ»

#### Scenario: The list agrees with the map

- **WHEN** a verse's neighbours are compared with the map's cells
- **THEN** every pair of a cell holding that verse SHALL be in its list, and no other

#### Scenario: Invalid references

- **WHEN** the surah is outside 1–114, or the ayah exceeds the surah's length
- **THEN** the route SHALL answer 422 or 404 respectively, with no partial body

#### Scenario: The intra-surah view survives a missing cross-surah dataset

- **WHEN** `quran_close_verses.json` is absent
- **THEN** `GET /verse/{surah}/{ayah}/similar` SHALL answer 503 naming
  `python scripts/build_quran_close_verses.py`
- **AND** `GET /surah/{number}/similar` SHALL answer exactly as before

#### Scenario: No model is loaded by the route

- **WHEN** the backend starts and only `GET /verse/{s}/{a}/similar` is called
- **THEN** `GET /health` SHALL report no embedder and no search reranker resident

### Requirement: The anchor panel lists the verse's close verses in the rest of the Quran

In the Verse Study «المتشابهات داخل السورة» mode, selecting a verse of a group SHALL show, **below**
the picked verse (its same-surah close verses are not listed), a section headed
«الآيات المتشابهات في سائر القرآن» listing its cross-surah close verses in the order served. Each card
SHALL show the verse vocalized, its surah's Arabic name and its ayah number, and the shared content
roots as Arabic root chips when there are any. When the pair has a common part, it SHALL be
highlighted in the listed verse and the card SHALL state «N كلمات مشتركة»; the picked verse itself
SHALL NOT be highlighted. No numeric score SHALL be shown. Activating a card SHALL open the verse in
«الآية في سياقها».

The verse card (from the intra-surah request) and the cross-surah section SHALL be requested
independently: the card SHALL render without waiting for the cross-surah answer, and a failure of one
SHALL be shown in its own place without hiding the other. A scored verse with no cross-surah close verse SHALL say so in a sentence rather than render an
empty list. The fetched answers SHALL be cached under `verse-study.similar.surah.*`, so returning to a
verse already picked issues no request.

#### Scenario: Pick a verse, see its close verses elsewhere

- **WHEN** the reader picks surah 3 and then 3:116 inside a group
- **THEN** the verse 3:116 is shown, with no list of its close verses in surah 3
- **AND** below it, «الآيات المتشابهات في سائر القرآن» lists 58:17 with its surah name «المجادلة»

#### Scenario: The common part is coloured in the listed verse

- **WHEN** a listed close verse carries a span
- **THEN** that span of its text SHALL be highlighted and «N كلمات مشتركة» SHALL be shown

#### Scenario: The cross-surah request fails

- **WHEN** `GET /verse/{s}/{a}/similar` answers 503
- **THEN** the picked verse SHALL still be shown
- **AND** the cross-surah section SHALL show the failure note in its place

#### Scenario: No cross-surah close verse

- **WHEN** a scored verse has an empty cross-surah neighbour list
- **THEN** the section SHALL state that no verse elsewhere in the Quran is close to it or shares a
  passage with it

