## ADDED Requirements

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
