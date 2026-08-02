## ADDED Requirements

### Requirement: Deterministic phonetic transcription and syllabation

The phonetic (صوتي) level SHALL be computed deterministically from the fully
vocalized (tashkīl) form of the selected word, with no LLM involvement. It SHALL
produce a grapheme-to-phoneme (G2P) transcription and a syllabation of the word,
computed from the vocalized rasm by an explicit rule set. The transcription SHALL
NOT be taken from the treebank's precomputed phonetic column, which is incomplete
and context-baked (it encodes verse-position sandhi rather than a word-intrinsic
form).

#### Scenario: Phonetic level from vocalized word

- **WHEN** the صوتي level is requested for a word whose vocalized form is available
- **THEN** a G2P transcription and a syllable breakdown are returned, derived from the vocalized rasm
- **AND** the same vocalized word always yields the same transcription and syllabation.

#### Scenario: Vocalized form unavailable

- **WHEN** no vocalized form is available for the word
- **THEN** the صوتي level is reported as unavailable rather than guessed.

### Requirement: School-attributed articulation description per letter

For each letter of the selected word, the صوتي level SHALL provide its
articulation point (makhraj) and its phonetic attributes (ṣifāt), drawn from a
fixed reference table. Because these classifications differ between recitation
schools (e.g. 17 vs 16 vs 14 makhārij), the level SHALL name the school/authority
the table follows, and SHALL present it as an attributed reading rather than as an
un-attributed universal fact.

#### Scenario: Makhraj and sifat per letter, attributed

- **WHEN** the صوتي level is produced for a word
- **THEN** each of its letters is annotated with its makhraj and its ṣifāt from the reference table
- **AND** the response names the school/authority the makhārij count and mapping follow.

### Requirement: Applicable tajwīd rules, including cross-word rules

The صوتي level SHALL identify the tajwīd rules that apply for the selected word,
computed deterministically from the vocalized text. Rules internal to the word
SHALL be reported against the positions in the word where they apply. Rules that
operate across a word boundary (e.g. idghām, iqlāb, sun-letter lām between two
words) SHALL be computed at verse level and reported as anchored to the selected
word and its neighbour, not misrepresented as word-intrinsic. Tajwīd rule
detection SHALL be sourced from the open tajwīd rule data (its logic
reimplemented), never from unlicensed code.

#### Scenario: Word-internal tajwid rules identified

- **WHEN** the vocalized word triggers one or more word-internal tajwīd rules (e.g. elongation, internal nasalization)
- **THEN** those rules are listed with the positions in the word where they apply
- **AND** when no rule applies, an empty rule list is returned rather than fabricated rules.

#### Scenario: Cross-word rule anchored at verse level

- **WHEN** a tajwīd rule applies between the selected word and an adjacent word
- **THEN** the rule is reported as applying at the boundary with the named neighbour
- **AND** it is not presented as a property internal to the selected word alone.
