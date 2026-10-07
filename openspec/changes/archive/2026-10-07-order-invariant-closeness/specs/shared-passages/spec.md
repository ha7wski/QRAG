## MODIFIED Requirements

### Requirement: A shared-passage relation between verses of different surahs

Two verses of different surahs SHALL share a passage when the identical-token pairs of their
order-invariant matching — one token per QAC word, the stem segment's lemma, else the bare surface;
content words paired by lemma, non-content words paired by identical token — contain a dense region:
a window of verse A bounded by matched words and a window of verse B bounded by matched words, keeping
only the pairs whose two ends lie inside both windows, that has at least 6 kept pairs, kept pairs at
least 0.75 of the longer window, and at least 3 kept pairs joining content words. Among the window
pairs meeting those three conditions, the one with the MOST kept pairs SHALL be stored (ties: the
larger `2k − unmatched words of both windows`, then the earlier and then the shorter window in A,
then the earlier in B; A the lower-surah verse). The order of the kept pairs inside the windows SHALL
NOT matter. Pairs joined only by a shared root SHALL count as unmatched words of the region. A token
repeated in a verse SHALL pair with the occurrence at the offset of the shared material (the median
shift of the uniquely matched words), not at the same relative position of its verse.

#### Scenario: A displaced word does not break a passage

- **WHEN** 28:20 and 36:20 are compared
- **THEN** they SHALL share a passage covering «وَجَاءَ … قَالَ» in both verses

#### Scenario: A word moved across the passage stays in it

- **WHEN** 2:3 and 14:31 are compared
- **THEN** they SHALL share a passage whose window in 2:3 includes «يُنفِقُونَ» and whose window in 14:31
  includes «وَيُنفِقُوا»

#### Scenario: A repeated opening of a long verse is a passage

- **WHEN** 2:255 and 3:2 are compared — both open with «اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ», and
  2:255 holds «لا» several more times
- **THEN** they SHALL share a passage of those 7 words

#### Scenario: The largest accepted region is stored, not the best-scoring one

- **WHEN** the best-scoring window pair of a verse pair fails density while a smaller window pair
  within it meets all three conditions
- **THEN** that smaller window pair SHALL be stored

#### Scenario: A short formula is not a passage

- **WHEN** two verses share only «إِنَّ ٱللَّهَ غَفُورٌ رَّحِيمٌ»
- **THEN** they SHALL NOT share a passage
