# word-in-verses Specification

## Purpose
TBD - created by archiving change group-verse-lookup-by-written-form. Update Purpose after archive.
## Requirements
### Requirement: «لفظ» denotes the written form of an occurrence

Throughout the «الكلمة في الآيات» tab and the `POST /verse-lookup` response, **لفظ** SHALL
denote the *written form* of an occurrence — the word as the mushaf spells it — and SHALL NOT
denote the lemma, the lexeme, or the QAC morphological form.

A لفظ SHALL be derived from a single occurrence as follows:

1. Take the display token the highlighter marks for that occurrence. When more than one
   display token is marked, take the **last** of them: QAC merges a proclitic particle with
   the word it governs (`يحسرتى` for the two tokens `يَا حَسْرَتَا`), and in Arabic the particle
   is written first, so the lexical head is last.
2. Remove every mark — harakat, waqf marks, tatwīl, and the superscript (dagger) alef
   `ٰ` — leaving the letters as the mushaf writes them. This is exactly
   `arabic_text.bare()`; no other fold SHALL be applied to the display token.
3. Remove the leading PREFIX segments that the corpus records for that word ref, in order,
   stopping at the first segment that is not a PREFIX. Each segment SHALL be folded with
   `arabic_text.bare()` **and** have its wasla alef `ٱ` folded to a plene alef before
   comparison, because QAC writes the article both ways (`ٱلْ` 1 718 times, `الْ` 2 633).

Step 2 SHALL delete `ٰ` rather than fold it to a plene alef. Folding it corrupts every
word the mushaf ends in `ىٰ`: `مُوسَىٰ` becomes `موسىا` instead of `موسى`, silently splitting
one لفظ into a spelling that occurs nowhere. The words that need a plene alef already carry
one in this corpus (`آيَاتِ`, not `ءَايَٰتِ`), and the words that carry the dagger want it gone
(`ٱلرَّحْمَٰن` → `الرحمن`). `arabic_text.bare()` already deletes it.

Step 2 SHALL NOT fold the wasla alef on the display side. The vocalized corpus contains
`ٱ` in **0 of its 6 236 rows**, so the fold is unreachable there and would only be a
rule nobody can check.

Pronoun suffixes SHALL remain part of the لفظ: `آياتنا`, `آياته` and `آيات` are three distinct
ألفاظ. Proclitics SHALL NOT: `بِآيَاتِنَا` and `آيَاتِنَا` are one لفظ, `آياتنا`.

The derivation SHALL read the prefixes from the QAC segmentation and SHALL NOT infer them from
the word's leading letters. A rule that strips a leading و/ف/ب/ل/ك/س would remove the first
radical of every root beginning with one, turning `وَلَد` into `لد` and `كِتَاب` into `تاب`.

Step 3 SHALL strip a declared PREFIX only when the folded token actually begins with it, and
SHALL leave the token unchanged otherwise. This guard fires on **156 of the corpus's 50 045**
displayed occurrences, in every case correctly: the bulk are the vocative `يٰ` QAC glues to its
noun, which is a separate display token step 1 has already left behind, and the rest are an
interrogative hamza, an article, or a wāw that has merged orthographically with the stem and
cannot be removed without re-spelling the word (`أَأَتَّخِذُ`, `آللَّهُ`, `آلْـَٰٔنَ`).

The prefixes MAY be compared as one joined string rather than segment by segment. Measured over
all 50 045 occurrences, the two shapes yield an identical لفظ in every case; the segment-by-segment
count is 171 rather than 156 only because a word carrying two prefixes (`وي`, `ءال`) fails the
guard twice. 171 counts SEGMENTS, 156 counts OCCURRENCES — the figure that describes the rule is
156.

#### Scenario: Proclitic removed, pronoun suffix kept

- **WHEN** the لفظ is derived for word ref `2:39:4`, whose display token is `بِآيَاتِنَا` and
  whose QAC segments are PREFIX `بِ` + STEM + SUFFIX `نَآ`
- **THEN** the لفظ is `آياتنا`.

#### Scenario: A root beginning with a proclitic letter keeps its first radical

- **WHEN** the لفظ is derived for an occurrence of the root `ولد` whose display token is
  `وَلَدٌ` and whose QAC segments declare no PREFIX
- **THEN** the لفظ is `ولد`, not `لد`.

#### Scenario: A word the mushaf ends in a dagger alef

- **WHEN** the لفظ is derived for an occurrence whose display token is `مُوسَىٰ`
- **THEN** the لفظ is `موسى`, and every occurrence of the name yields that one لفظ.

#### Scenario: Merged orthography leaves the token intact

- **WHEN** the لفظ is derived for an occurrence whose QAC segments declare an interrogative
  hamza PREFIX but whose display token begins with `آ` (`آللَّهُ`, `آلْـَٰٔنَ`)
- **THEN** the declared prefix is not removed and the لفظ is the folded token as written.

#### Scenario: A QAC word covering several display tokens

- **WHEN** the لفظ is derived for word ref `39:56:4`, which QAC records as the single word
  `يحسرتى` and the vocalized row writes as the two tokens `يَا حَسْرَتَا`, both marked
- **THEN** the لفظ is `حسرتا`.

### Requirement: The lookup path does not load the full QAC word index

Deriving ألفاظ SHALL NOT make `data/derived/qac_words.json` resident on the `/verse-lookup`
path. That index costs **248 MB** resident against `word_index.json`'s 64 MB, and this
application's memory budget is documented as having already caused a hard freeze on a 16 GB
machine.

The prefix segments SHALL instead be read from a dedicated dataset carrying only what the
derivation needs — the PREFIX string per word ref, for the 26 001 of 77 429 words that have
one, which is 0.5 MB of JSON across 108 distinct prefix strings.

#### Scenario: Memory cost of a word lookup

- **WHEN** a backend that has served only `/verse-lookup` requests is inspected
- **THEN** `qac_words.json` is not resident.

#### Scenario: Prefix data stays a build product

- **WHEN** the prefix dataset is missing (a corpus built before this change)
- **THEN** the lookup still returns its blocks, deriving each لفظ from the display token with
  no prefix removed, and the dataset's rebuild command is logged — the same degradation path
  the lemma index and the highlight spine already take.

### Requirement: Occurrences are grouped by لفظ

The results of a word lookup SHALL be grouped into one block per distinct لفظ. The lemma
SHALL NOT appear on screen in any form — not as a section, a count, a chip, or a label.

Each لفظ block SHALL contain the sūra cards holding that لفظ's occurrences, and each sūra card
SHALL contain its verses, preserving the existing two-level structure below the block.

A result with a single لفظ SHALL still be wrapped in a block. The lemma grouping it replaces
rendered the sūra list bare at n=1, because a lemma name added nothing there; a لفظ does — it
is the derived spelling, and it is the answer to what the reader typed («الخيرات» → «خيرات»).
It is also what the header entry has to land on. The accepted cost is that a one-لفظ result
prints its سور/آيات figures twice, a line apart.

Within a لفظ block, a verse SHALL highlight only the occurrences of **that** لفظ. A verse
holding two ألفاظ of the same root SHALL appear in both blocks, each time with only the
relevant word marked.

The lemma index SHALL remain an internal input — it supplies the `word_refs` and `forms_found`
the position-based highlighter needs — and its removal from the display SHALL NOT change which
occurrences are shown.

#### Scenario: One block per written form

- **WHEN** a user looks up «الآيات» (root أيي)
- **THEN** nine blocks are shown, titled `آيات`, `آياتنا`, `آية`, `آياته`, `آياتي`, `آياتك`,
  `آيتك`, `آيتين`, `آياتها`
- **AND** no lemma name (`آيَة`) is rendered anywhere on the page.

#### Scenario: A verse holding two written forms

- **WHEN** a verse contains both `آيَاتِنَا` and `آيَاتِهِ`
- **THEN** it appears in the `آياتنا` block with only `آيَاتِنَا` marked
- **AND** it appears in the `آياته` block with only `آيَاتِهِ` marked.

#### Scenario: Grammatical tools stay excluded

- **WHEN** the ألفاظ of a root are assembled
- **THEN** occurrences that `word_function.json` records as serving a grammatical role
  (أداة نداء / استفهام / شرط) contribute no لفظ, are not listed, and are not counted
- **AND** for «الآيات» no block titled `أي` or `أيها` exists.

### Requirement: Header figures are distinct counts over the root

The header SHALL report four figures, each a **distinct** count over the same filtered set of
occurrences — the set the blocks below it display:

| Figure | Counts |
|---|---|
| `عدد المواضع` | distinct words carrying the root |
| `عدد الآيات` | distinct āyāt |
| `عدد السور` | distinct sūras |
| `عدد الألفاظ` | distinct ألفاظ |

`عدد السور` SHALL NOT be the sum of the blocks' sūra counts. Summing it made the header add up
against the cards when there were few of them; with one card per لفظ the sum reaches 154 for
أيي (against 59 distinct sūras) and 330 for قوم, exceeding the 114 sūras that exist.

`عدد المواضع` SHALL be omitted rather than printed as zero when it is zero.

#### Scenario: Distinct sūra count

- **WHEN** a user looks up «الآيات»
- **THEN** the header reads `عدد المواضع : 382`, `عدد الآيات : 353`, `عدد السور : 59`,
  `عدد الألفاظ : 9`.

#### Scenario: The blocks may list more verse rows than the header's āya count

- **WHEN** a root has āyāt holding two ألفاظ (19 of أيي's 353)
- **THEN** the blocks together list more verse rows (373) than `عدد الآيات` reports (353)
- **AND** `عدد الآيات` still reports distinct āyāt.

### Requirement: Every لفظ is listed in the header and navigates to its block

The header SHALL list every لفظ, in the same order as the blocks, with no truncation and no
"show more" affordance. Each entry SHALL be activatable and SHALL scroll its block into view.

The list SHALL be complete even for the roots that produce many ألفاظ: the median root has 3,
the mean is 6.6, 58 roots exceed 30, and أتي reaches 150.

#### Scenario: Navigating to a block

- **WHEN** the user activates the `آياتي` entry in the header
- **THEN** the page scrolls the `آياتي` block into view.

#### Scenario: A root with many written forms

- **WHEN** a user looks up a word resolving to the root أتي
- **THEN** all 150 ألفاظ are listed in the header, none elided.

### Requirement: The ordering control applies to both levels

The existing three-way ordering control («حسب المصحف» / «الأكثر آياتٍ» / «الأقلّ آياتٍ») SHALL
order the لفظ blocks **and** the sūra cards inside each block, under one selection. There SHALL
be a single control, not one per level.

Under «حسب المصحف», ألفاظ SHALL be ordered by the position of their first occurrence in
recitation order. Under the two frequency orders, ألفاظ SHALL be ordered by the number of
distinct āyāt in the block — the figure the block prints — with ties broken deterministically
by the earlier first occurrence in both directions, mirroring how the sūra cards already break
ties by an explicit second key rather than by sort stability.

That tie-break reads the order the blocks ARRIVE in, so first-occurrence order is a property of
the response and not merely of the view: see the ordering clause in the response requirement
below. A wrong order there does not surface as a visibly wrong order — it surfaces as an
arbitrary one.

The control's label SHALL NOT name only the sūras. It read «ترتيب السور» while it ordered one
level; ordering two makes that false on screen, and it reads «الترتيب».

The control SHALL remain hidden only when BOTH axes are trivial — one لفظ block holding one
sūra card. Either axis having more than one member SHALL bring it back, even when the other
does not: two blocks inside a single sūra are still two blocks to order.

#### Scenario: One control reorders both levels

- **WHEN** the user selects «الأكثر آياتٍ»
- **THEN** the لفظ blocks are ordered by descending distinct-āya count
- **AND** within each block the sūra cards are ordered by descending āya count.

#### Scenario: Mushaf order

- **WHEN** the user selects «حسب المصحف»
- **THEN** the لفظ blocks are ordered by the recitation position of each لفظ's first
  occurrence
- **AND** the sūra cards inside each block are in recitation order.

#### Scenario: Several ألفاظ inside one sūra still offer the control

- **WHEN** a lookup returns two لفظ blocks whose verses all sit in the same sūra
- **THEN** the ordering control is shown.

#### Scenario: The header list tracks the blocks through a reorder

- **WHEN** the user changes the order
- **THEN** the ألفاظ listed in the header are reordered to match the blocks, in the same
  sequence, so that activating one still reaches its own block.

### Requirement: Proper nouns are grouped by لفظ

A rootless proper noun (لوط، إبراهيم) SHALL be grouped by لفظ under the same derivation rule,
and its ألفاظ SHALL be listed in the header. The header SHALL NOT omit the لفظ list for a
proper noun.

The vocalized name SHALL remain available for the header's identity line, which previously
read it from the first lemma group.

#### Scenario: A name's written forms

- **WHEN** a user looks up «لوط»
- **THEN** the header shows the vocalized name and `عدد الألفاظ : 2`
- **AND** two blocks are shown, titled `لوط` and `لوطا`.

### Requirement: The `/verse-lookup` response carries written forms

`POST /verse-lookup` SHALL remain mounted at the same path and SHALL return, in place of the
lemma groups, a list of لفظ groups. Each group SHALL carry the لفظ itself, its distinct-āya
count, its occurrence count, and its verses, each verse carrying the token indices to
highlight for that لفظ alone.

The response SHALL carry the proper noun's vocalized display name as a top-level field rather
than inside a group, so that removing the lemma grouping does not remove the name.

The response SHALL NOT carry a lemma field of any kind.

The groups SHALL be emitted in first-occurrence order **globally, across every root the word
resolved to** — not per root and then concatenated. A homograph query reaches several roots
(كل → أكل / كلل / كيل), and ordering within each before joining them put مأكول (105:5) ahead of
كلما (2:20). The client breaks its own count ties on the order it receives, so this ordering is
part of the contract rather than a convenience.

The groups SHALL be keyed on the pair (root, لفظ), so one spelling reachable under two roots
stays two groups.

#### Scenario: Blocks of a homograph query interleave by first occurrence

- **WHEN** a word resolves to several roots
- **THEN** the groups of all of them are in one recitation-order sequence, not grouped by root.

#### Scenario: Response shape

- **WHEN** a client posts a word to `/verse-lookup`
- **THEN** the response carries the لفظ groups, the four header totals, and no lemma field.

#### Scenario: Highlighting is scoped to the group

- **WHEN** a verse appears under two different لفظ groups in one response
- **THEN** each group's copy of that verse carries only the token indices of its own لفظ.

