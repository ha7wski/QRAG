## MODIFIED Requirements

### Requirement: A shared-passage relation between verses of different surahs

Two verses of different surahs SHALL share a passage when the identical-token pairs of their
order-invariant matching — one token per QAC word, the stem segment's lemma, else the bare surface;
content words paired by lemma, non-content words paired by identical token — contain a dense region:
a window of verse A bounded by matched words and the span of their partners in verse B, keeping only
the pairs whose two ends lie inside both windows, that has at least 6 kept pairs, kept pairs at least
0.75 of the longer window, and at least 3 kept pairs joining content words. The region maximising
`2k − unmatched words of both windows` SHALL be kept (ties: earlier window start in A, then the
shorter window). The order of the kept pairs inside the windows SHALL NOT matter. Pairs joined only
by a shared root SHALL count as unmatched words of the region.

#### Scenario: A displaced word does not break a passage

- **WHEN** 28:20 and 36:20 are compared
- **THEN** they SHALL share a passage covering «وَجَاءَ … قَالَ» in both verses

#### Scenario: A word moved across the passage stays in it

- **WHEN** 2:3 and 14:31 are compared
- **THEN** they SHALL share a passage whose window in 2:3 includes «يُنفِقُونَ» and whose window in 14:31
  includes «وَيُنفِقُوا»

#### Scenario: A short formula is not a passage

- **WHEN** two verses share only «إِنَّ ٱللَّهَ غَفُورٌ رَّحِيمٌ»
- **THEN** they SHALL NOT share a passage
