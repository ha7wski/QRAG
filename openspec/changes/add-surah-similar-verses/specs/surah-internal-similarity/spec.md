## ADDED Requirements

### Requirement: Closeness is meaning-or-subject AND near syntax

Two verses of the same surah SHALL be considered close only when BOTH conditions hold:

1. **Semantic** — they share the same meaning, or speak of the same subject: the semantic score
   (cross-encoder, dense cosine, shared-root coverage) reaches the frozen threshold `τ_sem`.
   Between two verses whose Arabic is verbatim identical, the dense cosine SHALL NOT enter the
   semantic score (it embeds the translations, which vary while the Arabic does not);
2. **Syntactic** — they have nearly the same syntax: the syntactic similarity of their QAC word
   signatures reaches the frozen threshold `σ`.

Neither condition alone SHALL make a pair close: same subject in a different construction is not
close, and the same construction on an unrelated subject is not close. A pair failing either gate
SHALL appear in no neighbour list and contribute no group edge.

#### Scenario: Same subject, different syntax

- **WHEN** two verses of a surah speak of the same subject but one is a nominal sentence and the
  other a long conditional construction, so their syntactic similarity is below `σ`
- **THEN** neither SHALL list the other as a neighbour

#### Scenario: Same syntax, different subject

- **WHEN** two verses share a construction (syntactic similarity ≥ `σ`) but their semantic score is
  below `τ_sem`
- **THEN** neither SHALL list the other as a neighbour

#### Scenario: A refrain passes both gates

- **WHEN** two occurrences of «فَبِأَيِّ آلَاءِ رَبِّكُمَا تُكَذِّبَانِ» in surah 55 are compared
- **THEN** both gates SHALL pass and each SHALL list the other as a neighbour unless they are
  consecutive

### Requirement: The syntactic signature comes from QAC

Each verse's syntactic signature SHALL be the ordered sequence of its words' QAC descriptions:
for every word, the part-of-speech tags of its segments in order (prefixes, stem, suffixes) with the
stem's verb aspect/mood or nominal case where QAC records one. The treebank role
(`qac_syntax.json` `role_ar`) SHALL NOT be part of the signature. Particles and tool words SHALL be
kept in the signature — they are syntax, even though they are excluded from the root signal.

Syntactic similarity SHALL be `1 − normalized edit distance` between the two signatures (word as the
unit, distance divided by the longer length), so that it is symmetric, lies in `[0, 1]`, and falls
when the two verses differ markedly in length.

The signature SHALL be computed at build time only, through `quran_data.qac.records()`.
`qac_words.json` SHALL NOT be read on any request path.

#### Scenario: Syntactic similarity is symmetric and bounded

- **WHEN** the syntactic similarity of any pair (A, B) is computed
- **THEN** it SHALL equal that of (B, A) and lie in `[0, 1]`

#### Scenario: Identical constructions score 1

- **WHEN** two verses have identical QAC signatures (e.g. two occurrences of a refrain)
- **THEN** their syntactic similarity SHALL be 1

#### Scenario: Identical text, identical signature

- **WHEN** two occurrences of «فَبِأَيِّ آلَاءِ رَبِّكُمَا تُكَذِّبَانِ» in surah 55 are compared — including
  55:13 and 55:25, which the treebank labels differently («اسم» vs «حرف استفهام» on «فَبِأَيِّ»)
- **THEN** their signatures SHALL be equal and their syntactic similarity SHALL be 1

### Requirement: Grammatical-tool occurrences are excluded from the root signal

The shared-root coverage SHALL be computed over each verse's **content** roots only: a root SHALL NOT
count for a verse when every occurrence of it in that verse is a grammatical tool — listed in
`word_function.json` (أداة نداء / استفهام / شرط) — or a word of the existing function-word stoplist
(`retrieval/similar_verses.py`). The roots displayed as shared SHALL be those same content roots.
Coverage SHALL be the IDF-weighted Jaccard of the two content-root sets; a root nobody holds as
primary carries no weight.

#### Scenario: A vocative does not make two verses share a root

- **WHEN** two verses of a surah each open with «يَا أَيُّهَا» and share no other root
- **THEN** their shared-root list SHALL be empty and their coverage 0

### Requirement: Consecutive verses are never shown as close

A pair of verses whose ayah numbers differ by exactly 1 SHALL NOT be stored as neighbours and SHALL
NOT form a group edge, whatever its scores, because their closeness is mostly continuity of
context. The exclusion SHALL be applied at build time, so no client can display such a pair.

#### Scenario: Adjacent refrain occurrences

- **WHEN** a refrain recurs in two consecutive ayat
- **THEN** neither SHALL list the other as a neighbour
- **AND** both MAY still belong to the same group through non-consecutive members

### Requirement: An offline intra-surah similarity dataset

The system SHALL ship a derived dataset, `data/derived/surah_similarity.json`, built by
`scripts/build_surah_similarity.py`, holding for every verse its close verses **within its own
surah**. The dataset SHALL be registered in `quran_data/paths.py` and `quran_data/manifest.py`
(producer, inputs, consumers, rebuild command) and read only through one cached loader in
`quran_data/loaders.py`.

For each verse the dataset SHALL record at most K neighbours (K frozen in the build, default 10),
only pairs passing both gates, each carrying: the neighbour's ayah number, a composite score in
`[0, 1]`, and the signals that composed it (cross-encoder, dense cosine, shared-root coverage,
syntactic similarity), plus the list of shared content roots (canonical, hamza-bearing spellings).
A verse MAY have fewer than K neighbours, or none.

The dataset SHALL carry a build header naming the models used (reranker and embedder ids), K, M,
the weights, `τ_sem`, `σ`, the group threshold, and the sha256 of the gold set the parameters were
frozen against. The loader SHALL refuse a file whose schema version it does not know, with the
rebuild command from the manifest.

#### Scenario: Neighbours never leave the surah

- **WHEN** the dataset is loaded
- **THEN** every neighbour of every verse SHALL belong to the same surah as that verse
- **AND** no verse SHALL list itself, nor a verse at `|Δayah| = 1`

#### Scenario: Every stored pair passes both gates

- **WHEN** any stored neighbour entry is read
- **THEN** its syntactic similarity SHALL be ≥ `σ` and its semantic score ≥ `τ_sem` as recorded in
  the header

#### Scenario: The score is symmetric

- **WHEN** verse A lists verse B as a neighbour with score s, and B lists A
- **THEN** B's entry for A SHALL carry the same score s
- **AND** the cross-encoder signal SHALL be the mean of both directions `(A, B)` and `(B, A)`

#### Scenario: Neighbours are deterministically ordered

- **WHEN** a verse's neighbours are read
- **THEN** they SHALL be sorted by composite score descending, ties broken by ayah number ascending
- **AND** two builds over the same inputs and parameters SHALL produce byte-identical files

#### Scenario: A missing dataset names its rebuild command

- **WHEN** the loader is called and `surah_similarity.json` is absent
- **THEN** it SHALL raise `DatasetMissing` naming `python scripts/build_surah_similarity.py`

### Requirement: Verses with no content are not compared

A verse with no content root after the tool and function-word filter (the muqaṭṭaʿāt such as «الم»,
and any verse made only of particles) SHALL have no neighbours and SHALL belong to no group. The
dataset SHALL list such verses explicitly as `unscored` per surah, so that their absence is a
recorded decision and not a silent gap.

#### Scenario: A disjointed-letters verse is listed as unscored

- **WHEN** the dataset entry for surah 2 is read
- **THEN** ayah 1 («الم») SHALL appear in that surah's `unscored` list
- **AND** it SHALL appear in no verse's neighbour list and in no group

### Requirement: Groups of mutually close verses per surah

For every surah the dataset SHALL carry **groups**: the connected components (size ≥ 2) of the graph
whose edges are *mutual* neighbour pairs (each in the other's stored list) with a composite score at
least the frozen group threshold τ. A verse SHALL belong to at most one group. Groups SHALL be
ordered by mean internal edge score descending, ties broken by their first ayah ascending.

#### Scenario: Dense is ignored between verbatim-identical verses

- **WHEN** two verses of a surah have identical Arabic words but different dense cosines
- **THEN** their semantic score SHALL be computed from the cross-encoder and coverage alone, and
  the stored pair SHALL be marked `verbatim`

#### Scenario: A refrain forms one group

- **WHEN** the groups of surah 55 (ar-Raḥmān) are read
- **THEN** the verses carrying the refrain «فَبِأَيِّ آلَاءِ رَبِّكُمَا تُكَذِّبَانِ» SHALL fall in one group,
  linked through non-consecutive occurrences

#### Scenario: A surah may have no group

- **WHEN** no mutual pair in a surah passes both gates and reaches τ
- **THEN** that surah's `groups` SHALL be an empty list, not an error

### Requirement: Parameters are frozen against a gold set written beforehand

Before the weights and thresholds (`τ_sem`, `σ`, τ) are chosen, a gold set SHALL be committed to the
local evaluation harness (`tests/eval/surah_similarity_gold.json`), drafted by Claude under the
closeness definition above, each pair carrying its reason:

- **positives** — same meaning or subject AND near syntax (refrains, parallel formulas, parallel
  narrative statements built the same way);
- **negatives, three kinds** — same subject / different syntax; same syntax / different subject;
  consecutive verses that are close by continuity.

The build SHALL record that file's sha256 in its header. An evaluation script SHALL report, on that
gold set: recall of the positives within the top-K, the rank of each positive, the positives lost at
each gate and at candidate generation, and how many negatives of each kind are stored as neighbours.
A parameter change after the first measurement SHALL be justified without citing the gold score; a
result short of the pre-registered target SHALL be recorded as the result.

#### Scenario: The header proves which gold set froze the parameters

- **WHEN** the dataset header is read
- **THEN** its gold-set digest SHALL equal the sha256 of the committed gold file
- **AND** the evaluation script SHALL refuse to report against a gold file with a different digest

#### Scenario: Consecutive negatives are structurally absent

- **WHEN** the evaluation runs
- **THEN** zero consecutive-verse negatives SHALL be stored as neighbours

### Requirement: A model-free route serves the dataset

The backend SHALL serve `GET /surah/{number}/similar`, reading only the dataset. It SHALL load no
model and query neither Qdrant nor the reranker; after any number of calls `GET /health` SHALL still
report `models.embedder = false` and `models.search_reranker = false` if nothing else loaded them.

- Without `ayah`: the response SHALL carry the surah's number and Arabic name, its groups (each with
  its verses, vocalized, and its mean score) and its `unscored` ayahs.
- With `?ayah=a`: the response SHALL carry the anchor verse and its neighbours in dataset order, each
  with its verse, score and shared roots. An `unscored` anchor SHALL return an empty neighbour list
  with `unscored: true`; a scored anchor with no close verse SHALL return an empty list with
  `unscored: false`. Neither is an error.

Every verse in the response SHALL go through `verse_from_record`, so it carries `text_ar_tashkil`
with the Basmala stripped, like every other verse the API returns.

#### Scenario: Neighbours of one verse

- **WHEN** the client requests `GET /surah/12/similar?ayah=4`
- **THEN** the response SHALL list up to K verses of surah 12, none of them 12:3, 12:4 or 12:5, in
  score order, each with its shared roots

#### Scenario: Invalid references

- **WHEN** the surah number is outside 1–114, or `ayah` exceeds the surah's length
- **THEN** the route SHALL answer 422 or 404 respectively, and no partial body

#### Scenario: No model is loaded by the route

- **WHEN** the backend starts and only `GET /surah/{n}/similar` is called
- **THEN** `GET /health` SHALL report no embedder and no search reranker resident

### Requirement: The «داخل سورة» mode renders the dataset

The Verse Study `similar` tab's «داخل سورة» mode SHALL let the reader pick a surah by its Arabic name
(the shared surah picker), then render that surah's groups, strongest first, each verse vocalized and
numbered, each group framed in green and numbered (1, 2, 3 …) in a green disc on its right. Selecting a verse of a
group SHALL show its close verses in the same surah, ranked, each with its shared content roots
displayed as Arabic root chips. There is no ayah selector: a verse in no group is not offered.

No numeric score SHALL be shown; the ranking order carries it. No consecutive verse SHALL be shown as
close. The surah's `unscored` verses SHALL be named in a one-line note, and a scored verse with no
close verse SHALL say so, rather than render an empty list.

#### Scenario: Pick a surah, then a verse of a group

- **WHEN** the reader selects surah 55 and then a refrain verse inside its group
- **THEN** the groups of surah 55 are shown, each numbered in a green disc
- **AND** the ranked close verses of that verse within surah 55 are shown with their shared roots

#### Scenario: Unscored verses are named, not offered

- **WHEN** the reader selects surah 2
- **THEN** a one-line note SHALL name ayah 1 as not compared (it carries no content word), and no
  control SHALL offer it for selection

#### Scenario: A verse with no close verse is explained

- **WHEN** the anchor view of a scored verse with an empty neighbour list is rendered
- **THEN** the panel SHALL say that no verse of the surah is close to it in both meaning and syntax
