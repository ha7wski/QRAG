# vocalized-verse-text Specification

## Purpose

Define what the API means by fully vocalized verse text, and hold one line through every
endpoint that emits it: the text of an āya carries that āya's own words and nothing else.

The line needs defending because the sole source of vocalized text,
`data/source/quran_chakl.csv`, prepends the Basmala to āya 1 of 113 sūras — an artefact of
the file, not of the revelation. This capability places the removal at the API's display
layer, names the two āyāt that are exempt and the one place a Basmala legitimately sits
inside an āya, and specifies how the Basmala is recognised at all: by comparing
diacritic-stripped forms against a reference read from the corpus, never against a
literal typed into source.

It also protects the exception. The shared loader keeps returning raw rows, because the
word-level analyses address those rows by character offset; removing the prefix there
would shift every offset and silently return the wrong word. The removal is a display
concern and stays one.

## Requirements
### Requirement: Vocalized verse text carries only the āya's own words

Every field the API emits as fully vocalized verse text — `Verse.text_ar_tashkil` and the
`text` of a Verse Study word-lookup row — SHALL contain the words of that āya and nothing
else.

`data/source/quran_chakl.csv`, the sole source of vocalized text, prepends the Basmala to
āya 1 of 113 sūras. That prefix is an artefact of the source file, not part of the āya, and
SHALL be removed before the text leaves the API.

Two āyāt are exempt, and their text SHALL be emitted unchanged:

| Āya | Why |
|---|---|
| `1:1` | In al-Fātiḥa the Basmala *is* āya 1. |
| `9:1` | At-Tawba carries no Basmala; the row has no prefix to remove. |

A Basmala occurring anywhere other than at the start of an āya 1 SHALL NOT be removed —
`27:30` ends with it as part of Sulaymān's letter.

#### Scenario: An āya 1 that the corpus prefixed

- **WHEN** the API emits vocalized text for `2:1`
- **THEN** the text is «الم»
- **AND** it does not begin with the Basmala.

#### Scenario: Al-Fātiḥa keeps its first āya

- **WHEN** the API emits vocalized text for `1:1`
- **THEN** the text is the Basmala, unchanged from the corpus row.

#### Scenario: At-Tawba is untouched

- **WHEN** the API emits vocalized text for `9:1`
- **THEN** the text is the corpus row, unchanged, beginning «بَرَاءَةٌ».

#### Scenario: A Basmala inside an āya is not a prefix

- **WHEN** the API emits vocalized text for `27:30`
- **THEN** the text is the corpus row, unchanged, and still contains the Basmala.

#### Scenario: The correction reaches every surface

- **WHEN** `2:1` is returned as a chat source, as a `/search` result, as the subject or a
  neighbour of `/verse/2/1`, inside `/surah/2`, or as a Verse Study word-lookup row
- **THEN** each of them shows the āya without the prepended Basmala.

### Requirement: Basmala detection is diacritic-insensitive and corpus-sourced

The Basmala SHALL be recognised by comparing **diacritic-stripped** forms. The reference
string SHALL be derived from the corpus row for `1:1`, never from a Basmala literal typed
into source code: combining-mark order is not stable across this corpus, so a hand-typed
literal that is visually identical fails an exact comparison on every row.

The character class used to strip diacritics SHALL be written with explicit `\u` escapes,
not literal Arabic characters. Under bidirectional reordering a malformed range is visually
indistinguishable from a correct one, and an over-broad class deletes Arabic letters
instead of marks.

#### Scenario: A hand-typed literal is not used

- **WHEN** the Basmala reference string is obtained
- **THEN** it comes from the corpus row for `1:1`, stripped of diacritics.

#### Scenario: Detection is not defeated by mark order

- **WHEN** each of the 114 first āyāt is tested against the reference
- **THEN** exactly 113 match — every sūra except at-Tawba.

#### Scenario: Diacritic stripping preserves letters

- **WHEN** a vocalized āya is diacritic-stripped
- **THEN** every Arabic letter of the āya survives
- **AND** only marks, waqf signs and tatweel are removed.

### Requirement: The shared vocalized loader keeps its raw rows

`indexing.corpus.chakl_by_ref()` SHALL keep returning the corpus rows exactly as stored,
Basmala prefixes included. The removal SHALL live in a separate display helper that callers
apply.

Rows from this loader are addressed by character offset: `analysis.qlisan_data.word_index()`
records `chakl_char_start` / `chakl_char_end` computed against the Basmala-inclusive string
(`2:1:1` is recorded at `[39, 42)`), and both the QLisan word fiche and
`analysis.mizan._vocalized_surface` slice rows by those offsets. Removing the prefix inside
the loader would shift every one of them and silently return the wrong word.

#### Scenario: The loader is unchanged

- **WHEN** `chakl_by_ref()` is asked for `2:1`
- **THEN** the returned text still begins with the Basmala.

#### Scenario: Offset-addressed slicing still lands on the right word

- **WHEN** the stored offsets for `2:1:1` are applied to the row returned by the loader
- **THEN** the slice is «الٓمٓ».

### Requirement: A sūra's opening Basmala is exposed as its own field

`GET /surah/{number}` SHALL return the sūra's opening Basmala as a dedicated field,
separate from any āya text, so that no consumer has to decide which sūras open with one.

The field SHALL carry the vocalized Basmala for the 112 sūras that open with it as a
non-āya opening, and SHALL be empty for al-Fātiḥa — where it is āya 1 and already present
in the verse list — and for at-Tawba, which has none.

#### Scenario: A sūra that opens with the Basmala

- **WHEN** `GET /surah/2` is called
- **THEN** the response carries the vocalized Basmala in its own field
- **AND** the first verse in the list is «الم».

#### Scenario: Al-Fātiḥa

- **WHEN** `GET /surah/1` is called
- **THEN** the dedicated field is empty
- **AND** the Basmala appears in the verse list as āya 1.

#### Scenario: At-Tawba

- **WHEN** `GET /surah/9` is called
- **THEN** the dedicated field is empty
- **AND** no verse in the list has been altered.
