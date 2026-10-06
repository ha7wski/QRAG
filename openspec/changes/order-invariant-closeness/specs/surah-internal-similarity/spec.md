## MODIFIED Requirements

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

Each verse's syntactic signature SHALL be the ordered sequence of its words' QAC descriptions:
for every word, the part-of-speech tags of its segments in order (prefixes, stem, suffixes) with the
stem's verb aspect/mood or nominal case where QAC records one. The treebank role
(`qac_syntax.json` `role_ar`) SHALL NOT be part of the signature. Particles and tool words SHALL be
kept in the signature — they are syntax, even though they are excluded from the root signal.

Syntactic similarity SHALL be `½·uni + ½·bi`, where `uni` is the size of the multiset intersection of
the two verses' signature elements divided by the longer verse's word count, and `bi` the size of the
multiset intersection of their consecutive element pairs divided by the longer verse's word count
minus one (`bi = uni` when both verses have one word). It SHALL be symmetric, lie in `[0, 1]`, equal
1 for identical signatures, fall when the two verses differ markedly in length, and cost a displaced
block only the element pairs at its junctions.

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

#### Scenario: A moved block costs only its junctions

- **WHEN** a signature of 9 elements is compared with the same elements where a block of 3 has been
  moved elsewhere
- **THEN** `uni` SHALL be 1 and at most 3 of the 8 element pairs SHALL be lost

### Requirement: Grammatical-tool occurrences are excluded from the root signal

The lexical signal SHALL be computed over each verse's **content words** only: a word SHALL be a
content word when its resolved primary root belongs to its verse's content roots — a root SHALL NOT
count for a verse when every occurrence of it in that verse is a grammatical tool listed in
`word_function.json` (أداة نداء / استفهام / شرط) or a word of the existing function-word stoplist
(`retrieval/similar_verses.py`) — and its own occurrence is not a grammatical tool. The two verses'
content words SHALL be joined by a maximum-weight one-to-one matching (same lemma token: 1; different
token, same primary root: 0.5; among equal partners the nearest relative position), and `lex` SHALL be
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
