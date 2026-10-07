# surah-internal-similarity Specification

## Purpose

Answer, for every surah, «which verses of THIS surah echo each other?» — two verses being close
only when they share a meaning or subject AND are built with nearly the same syntax. The answer is
computed once, offline, into a derived dataset measured against a gold set frozen beforehand, and
served model-free to the «المتشابهات داخل السورة» mode of Verse Study.
## Requirements
### Requirement: Closeness is meaning-or-subject AND near syntax

Two verses of the same surah SHALL be considered close only when BOTH conditions hold:

1. **Semantic** — they share the same meaning, or speak of the same subject: the semantic score
   (cross-encoder, dense cosine, and the lexical signal `lex` of their order-invariant content-word
   matching) reaches the frozen threshold `τ_sem`. Between two verses whose Arabic is verbatim
   identical, the dense cosine SHALL NOT enter the semantic score (it embeds the translations, which
   vary while the Arabic does not);
2. **Syntactic** — they have nearly the same syntax: the syntactic similarity of their QAC word
   signatures reaches the frozen threshold `σ`.

Neither condition alone SHALL make a pair close: same subject in a different construction is not
close, and the same construction on an unrelated subject is not close. A pair failing either gate
SHALL appear in no neighbour list and contribute no group edge. Neither condition SHALL depend on the
order in which the shared lemmas or roots occur in the two verses.

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

#### Scenario: A displaced block does not change the verdict

- **WHEN** a verse is compared with the same verse in which one block of at least 3 words has been
  moved
- **THEN** their syntactic similarity SHALL be at least `σ` and their `lex` SHALL be 1

### Requirement: The syntactic signature comes from QAC

Each verse's syntactic signature SHALL be the ordered sequence of its words' COARSE QAC descriptions:
for every word, its stem segments only — a verb as its aspect (PERF / IMPF / IMPV) and whether it is
passive, a noun as its QAC subcategory (PN, ADJ, PRON, DEM, REL, T, LOC, NV, INTG, COND, ADDR) or a bare
noun, a particle as its tag — with no prefix or suffix segment, no case and no mood, so that a pronoun
suffix, a clitic particle, a case ending or a mood never changes the element. The treebank role
(`qac_syntax.json` `role_ar`) SHALL NOT be part of the signature. Particles and tool words SHALL be
kept in the signature — they are syntax, even though they are excluded from the root signal.

Syntactic similarity SHALL be `1 − normalized edit distance` (word as the unit, distance divided by the
longer length) taken as the best of three alignments: the two signatures as written, and each one
against the other with its blocks re-ordered along the lexical matching — a block being a maximal run
of positions whose matched partners keep their order, unmatched positions staying with the block they
follow, the blocks concatenated in the order of their first partner. It SHALL be symmetric, lie in
`[0, 1]`, equal 1 for identical signatures and for a pure permutation of blocks, cost a substituted
word one edit, and fall when the two verses differ markedly in length.

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

#### Scenario: A permutation of blocks scores 1

- **WHEN** a verse is compared with the same words in which two blocks have been exchanged
- **THEN** their syntactic similarity SHALL be 1

#### Scenario: A pronoun suffix, a clitic or a mood is not a difference

- **WHEN** 43:83 and 70:42 (the same text, two verbs tagged subjunctive in one and jussive in the
  other) are compared, or two words differ only by a pronoun suffix (رَبِّكُمْ / رَبِّهِمْ) or a clitic
  (وَالزُّبُرِ / وَبِالزُّبُرِ)
- **THEN** their elements SHALL be equal and the pair SHALL cost no edit

### Requirement: Grammatical-tool occurrences are excluded from the root signal

The lexical signal SHALL be computed over each verse's **content words** only: a word SHALL be a
content word when its resolved primary root belongs to its verse's content roots — a root SHALL NOT
count for a verse when every occurrence of it in that verse is a grammatical tool listed in
`word_function.json` (أداة نداء / استفهام / شرط) or a word of the existing function-word stoplist
(`retrieval/similar_verses.py`) — and its own occurrence is not a grammatical tool. The two verses'
content words SHALL be joined by a maximum-weight one-to-one matching (same lemma token: 1; different
token, same primary root: 0.5; among equal partners the one at the offset of the shared material — the
median shift of the uniquely matched words), and `lex` SHALL be
the IDF-weighted Jaccard of that matching: matched weight × root IDF, divided by the IDF mass of both
verses' content words minus that matched mass. A root nobody holds as primary carries no weight. The
roots displayed as shared SHALL be the roots of the matched content words. A pair SHALL be stored
only when its matched mass is positive.

#### Scenario: A vocative does not make two verses share a root

- **WHEN** two verses of a surah each open with «يَا أَيُّهَا» and share no other root
- **THEN** their shared-root list SHALL be empty and their `lex` 0

#### Scenario: Order does not change lex

- **WHEN** the content words of a verse are compared with the same words in another order
- **THEN** `lex` SHALL be 1

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
group SHALL show that verse; its close verses within the same surah SHALL NOT be listed (the group
already shows the verses that echo it — decided by the user, 2026-10-03), and what follows it is its
close verses in the rest of the Quran (`quran-wide-similarity`). There is no ayah selector: a verse in
no group is not offered.

No numeric score SHALL be shown; the ranking order carries it. No consecutive verse SHALL be shown as
close. The surah's `unscored` verses SHALL be named in a one-line note.

#### Scenario: Pick a surah, then a verse of a group

- **WHEN** the reader selects surah 55 and then a refrain verse inside its group
- **THEN** the groups of surah 55 are shown, each numbered in a green disc
- **AND** the picked verse is shown, with no list of its close verses within surah 55

#### Scenario: Unscored verses are named, not offered

- **WHEN** the reader selects surah 2
- **THEN** a one-line note SHALL name ayah 1 as not compared (it carries no content word), and no
  control SHALL offer it for selection

### Requirement: A short verse needs two shared lemmas

When the shorter of two verses has at most 5 QAC words, the pair SHALL be stored as close (neighbour or
group edge) only when the two verses' order-invariant content-word matching holds at least 2 pairs
joined by the same lemma; pairs joined only by a shared root SHALL NOT count. Pairs whose shorter verse
has more than 5 words SHALL be governed by the matched-mass rule alone. The cross-surah relation SHALL
apply the same rule, through the intra definition it reuses.

#### Scenario: One shared lemma in a short mould is not close

- **WHEN** 69:3 and 83:19 («وَمَا أَدْرَاكَ مَا الْحَاقَّةُ» / «وَمَا أَدْرَاكَ مَا عِلِّيُّونَ») are compared
- **THEN** neither SHALL list the other

#### Scenario: A verbatim short refrain stays close

- **WHEN** two non-consecutive occurrences of «فَبِأَيِّ آلَاءِ رَبِّكُمَا تُكَذِّبَانِ» are compared
- **THEN** the rule SHALL NOT drop the pair

#### Scenario: A long pair is not subject to the rule

- **WHEN** both verses have more than 5 words and share one content lemma
- **THEN** the short-verse rule SHALL NOT drop the pair

