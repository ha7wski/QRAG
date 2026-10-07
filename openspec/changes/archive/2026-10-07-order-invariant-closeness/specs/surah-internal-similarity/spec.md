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
