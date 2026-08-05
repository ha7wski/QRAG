# root-attribution Specification

## Purpose
TBD - created by archiving change add-root-arbitration. Update Purpose after archive.
## Requirements
### Requirement: Every word resolves to one ranked root set

Each of the 77 429 Quran words SHALL resolve to exactly one **primary** root plus zero or more
**alternate** roots, ordered, or to no root at all. The resolution SHALL be a pure function of the
two source resources and the arbitration file — never of the calling module, so the same word
yields the same root set everywhere in the product.

A word with no root in either resource SHALL keep no root. A root SHALL NEVER be invented,
inferred by a stemmer, or back-filled from a similar-looking word.

#### Scenario: Consensual word carries a single root

- **WHEN** the root set is resolved for 1:1:1 بِسْمِ (source A `سمو`, treebank `سمو`)
- **THEN** the primary root is `سمو`
- **AND** the alternate list is empty

#### Scenario: Scholarly disagreement is preserved as primary plus alternate

- **WHEN** the root set is resolved for 2:8:2 ٱلنَّاسِ (source A `أنس`, treebank `نوس`)
- **THEN** the primary root is `أنس`
- **AND** `نوس` is present as an alternate
- **AND** the same pair is returned for all 241 words of that family, with no per-call variation

#### Scenario: Rootless word stays rootless

- **WHEN** the root set is resolved for a particle that neither resource assigns a root to
  (one of the 27 088 such words)
- **THEN** no root is returned
- **AND** no stemmer or heuristic fallback is consulted

### Requirement: The stored root keeps its exact spelling; folding is confined to keys

The root stored and displayed SHALL be the exact QAC spelling, hamza carriers included. Folding
(`normalize_root` and the hamza-blind cross-source fold) SHALL be used **only** to build lookup
keys, index entries, and comparisons — never as the persisted or rendered value.

This is a one-way constraint: a folded form cannot be restored to its spelling, while an exact
spelling can always be folded on demand. All 139 hamzated roots of the reference source SHALL
survive into `data/processed/`, against 1 today.

#### Scenario: A hamzated root survives storage

- **WHEN** the root of 22:23:19 وَلُؤْلُؤًا is stored
- **THEN** the stored value is `لؤلؤ`
- **AND** it is never `لالا` (the treebank's already-stripped form) nor `لولو` (the carrier-folded form)

#### Scenario: Folded lookups still reach the family

- **WHEN** a caller looks a root up by `لولو`, by `لالا`, or by `لؤلؤ`
- **THEN** all three reach the same root family and return its 6 words
- **AND** the returned root is rendered as `لؤلؤ`

#### Scenario: Hamzated roots are not lost corpus-wide

- **WHEN** the processed root inventory is rebuilt
- **THEN** it contains 139 hamzated roots
- **AND** no stored root has had a hamza carrier replaced by a bare alif

### Requirement: Arbitration follows a fixed, ordered cascade

When the two resources disagree on a word, the root SHALL be decided by the following rules,
evaluated in order, the first rule that yields an answer winning:

0. a verdict recorded in the arbitration file for that word or root family;
1. the two roots are equal under either fold — no disagreement; keep the reference source's spelling;
2. exactly one resource proposes a root — take it;
3. the classical lexicon arbitrates: the entry a lexicographer filed the word under decides;
4. attestation elsewhere in the Quran breaks a tie the lexicon leaves open;
5. two lexica disagree — keep both roots, primary then alternate.

Rule 3 SHALL outrank rule 4. Corpus frequency is evidence, never authority.

Rule 3 SHALL consult the lexica present on disk. Only Maqāyīs al-Lugha is available today, so
rule 5 cannot fire from a lexical conflict yet, and no multi-lexicon aggregation machinery SHALL
be built for a case that does not exist. The ranking rule is nevertheless fixed now: when a second
lexicon is added and the two disagree, both roots are kept, Maqāyīs primary and the other
alternate. Neither lexicon SHALL be declared permanently authoritative over the other.

#### Scenario: Spelling difference is not a disagreement

- **WHEN** source A gives `لؤلؤ` and the treebank gives `لالا` for 55:22:3
- **THEN** rule 1 matches (the forms are equal under the hamza-blind fold)
- **AND** the root is `لؤلؤ`, the reference spelling
- **AND** the word is not reported as an arbitration case

#### Scenario: The lexicon outranks corpus frequency

- **WHEN** the root is arbitrated for 107:7:2 ٱلْمَاعُونَ (source A `عون`, attested 11 times
  elsewhere; treebank `معن`, attested nowhere else)
- **THEN** rule 3 decides from the lexical entry, before rule 4 is consulted
- **AND** the more frequent root does not win by frequency alone

#### Scenario: A single lexicon on disk does not trigger rule 5

- **WHEN** the cascade reaches rule 3 and only Maqāyīs al-Lugha is available
- **THEN** its entry decides
- **AND** rule 5 does not fire, and no second-lexicon lookup is attempted
- **AND** a family the single lexicon cannot settle is left to rule 4, then recorded as an
  open arbitration case rather than guessed

#### Scenario: Cascade is order-stable

- **WHEN** the same disagreement is arbitrated twice
- **THEN** the same rule number fires and the same root set is produced
- **AND** the deciding rule number is recorded alongside the result

### Requirement: A silence is never chosen over a root claim

Where one resource assigns a root and the other assigns none, the root SHALL be kept. An
abstention carries no information and SHALL NOT override a claim. This settles the 447 words that
form the largest disagreement class.

Proper nouns SHALL keep their root **and** carry `is_proper_noun`, rather than having the root
nulled: a flagged root can be filtered at display time, an erased one cannot be recovered.

#### Scenario: Fused word keeps the root of its bearing segment

- **WHEN** the root is resolved for 2:21:1 يَٰٓأَيُّهَا (source A `أيي`, treebank silent — one of
  215 such words) or for 3:167:20 يَوْمَئِذٍ (source A `يوم`, treebank silent — 70 words)
- **THEN** the root from source A is kept
- **AND** the word is not left rootless

#### Scenario: Proper noun keeps a flagged root

- **WHEN** the root is resolved for 2:31:2 ءَادَمَ (source A `أدم`, treebank silent)
- **THEN** the root `أدم` is stored
- **AND** `is_proper_noun` is true
- **AND** a consumer that excludes proper nouns can filter on that flag rather than on a missing root

#### Scenario: A root added by only the treebank is accepted by default

- **WHEN** the treebank assigns `اول` to 2:179:5 يَٰٓأُو۟لِى where source A assigns none
  (one of 73 such words)
- **THEN** rule 2 keeps the root without requiring a citation
- **AND** no blanket citation requirement is imposed on the other 72

#### Scenario: A weak addition is flagged rather than silently kept

- **WHEN** the treebank assigns a root to a word whose part of speech makes the derivation
  doubtful — `اني` on the interrogative أَنَّىٰ (28 words, INTG)
- **THEN** the root is still kept under rule 2
- **AND** the family is flagged as needing a lexical citation, so the reviewer sees the few
  doubtful cases instead of auditing the whole block

### Requirement: Misleading fused compounds are marked from a fixed list

A word SHALL carry the fused-compound marker when displaying its bare root would mislead a reader
about where the word comes from. The marker SHALL be driven by an **enumerated list of lemmas**
recorded in the arbitration file, and SHALL NOT be derived from a structural predicate over
segments. The marker is data, not presentation, so any consumer can filter on it.

The inclusion test is applied by a human, once per lemma: *if the bare root is shown, will the
reader be wrong about the origin of the word?*

- يَٰٓأَيُّهَا displays `أيي`, which is آية's root — the reader concludes the vocative comes from آية.
  Marked.
- بِسْمِ displays `سمو` — the root genuinely describes the word; only a clitic preposition is
  attached. Not marked.

A structural rule cannot make this call. يَٰقَوْمِ (15 words, root `قوم`), يَٰٓأَهْلَ (12, `اهل`),
يَٰبَنِيَّ (10, `بني`) and يَٰٓأُو۟لِى (5, `اول`) have exactly the shape of يَٰٓأَيُّهَا — a vocative
particle welded to a rooted stem — yet none of them misleads about the word's origin, so none is
marked. Identical structure, opposite verdict. Conversely a "≥2 stem segments" test would mark 563
words (إنما 113, مما 111, عما 47, ألا 45…) that carry no root at all, and would still miss يَٰٓأَيُّهَا.

The list as measured today — 3 lemmas, 225 words:

| lemma | form | root | words | why it misleads |
|---|---|---|---:|---|
| `ايها` | يَٰٓأَيُّهَا | `أيي` | 153 | that root is آية's; the vocative does not come from آية |
| `ايتها` | يَٰٓأَيَّتُهَا | `أيي` | 2 | same |
| `يوميذ` | يَوْمَئِذٍ | `يوم` | 70 | the root covers يوم only; إذ is a separate unit |

Adding a lemma SHALL go through the arbitration file with its misleading-origin reason recorded.
A word whose lemma is absent from the list SHALL NOT be marked, whatever its segment structure.

#### Scenario: Listed lemma is marked

- **WHEN** the root set is resolved for 2:21:1 يَٰٓأَيُّهَا (lemma `ايها`, on the list)
- **THEN** the root `أيي` is kept
- **AND** the word carries the fused-compound marker

#### Scenario: Same structure, not misleading, not marked

- **WHEN** the root set is resolved for a يَٰقَوْمِ occurrence (lemma `قوم`, a vocative particle
  welded to a rooted stem, exactly like يَٰٓأَيُّهَا)
- **THEN** the root `قوم` is kept
- **AND** no marker is set, because `قوم` does describe the word's origin

#### Scenario: Single-unit word is not marked

- **WHEN** the root set is resolved for a bare أَيّ (lemma `اى`, one of 60 words) or for a
  آية / ءايات occurrence (382 words)
- **THEN** the root `أيي` is kept
- **AND** no marker is set, even though the treebank assigns أَيّ no root

#### Scenario: The list is closed against structural false positives

- **WHEN** the root set is resolved for a word with two stem segments but no root — إنما, مما,
  عما, ألا (among 563 such words)
- **THEN** no marker is set, because no lemma of theirs is on the list
- **AND** the marker never appears on a word that carries no root

#### Scenario: A root search can separate compounds from real occurrences

- **WHEN** the root `أيي` is queried (597 words in the reference source)
- **THEN** the 382 آية / ءايات words are distinguishable from the 155 marked vocatives
- **AND** a caller searching آية can exclude يا أيها by the marker alone

### Requirement: Every deviation from the reference source is recorded with an authority

A single versioned arbitration file SHALL be the only place where a stored root may differ from
the reference source. Each entry SHALL carry: the target (word ref or root family), the chosen
primary root, any alternates, the deciding rule, and a cited authority (lexicon and entry, or
corpus evidence). Undocumented deviation SHALL NOT be possible: no module may transform a root
in passing.

#### Scenario: Arbitration file is the sole deviation channel

- **WHEN** the resolved root for a word differs from the reference source's root
- **AND** no arbitration entry covers that word or its root family
- **THEN** the build fails and names the word

#### Scenario: An entry without an authority is rejected

- **WHEN** an arbitration entry sets a primary root but cites no lexicon entry and no corpus evidence
- **THEN** the arbitration file is rejected as invalid

### Requirement: Both processing chains serve the same arbitrated root

The morphology chain (`morphology.json`, `qac_resolution.json`) and the treebank chain
(`qac_words.json`, `root_graph.json`) SHALL publish the same root set for the same word. The
product SHALL NOT expose two rival answers for one word, as it does today for the 757 divergent
words.

#### Scenario: The two halves of the product agree

- **WHEN** the root of 2:8:2 ٱلنَّاسِ is read from the retrieval side and from the analysis side
- **THEN** both return primary `أنس` with alternate `نوس`
- **AND** neither returns a root the other does not know

#### Scenario: Divergence between chains is impossible by construction

- **WHEN** the processed data is rebuilt
- **THEN** a check over all 77 429 words reports 0 words whose root set differs between the two chains

### Requirement: Root retrieval reaches a word under any of its roots

A search or lookup by root SHALL return a word when the query root matches its primary **or** any
alternate. A word SHALL appear once per result set regardless of how many of its roots matched.
Ranking of a hit SHALL NOT depend on which of its roots matched.

The asymmetry is deliberate: an extra root costs some noise, a missing root makes verses
unreachable.

#### Scenario: Either reading finds the same verses

- **WHEN** a user searches the root `نوس`
- **THEN** the 241 ٱلنَّاس words are returned
- **AND** searching `أنس` returns those same 241 words plus the 97 words of that root's other
  attestations

#### Scenario: A multi-root word is not duplicated

- **WHEN** a query matches both the primary and an alternate root of the same word
- **THEN** the word appears exactly once in the results

### Requirement: Unarbitrated disagreements fail the check

A repeatable check SHALL compare the two resources over every word and fail when a disagreement is
neither resolved by a cascade rule that needs no human input (rules 1, 2, 4) nor covered by an
arbitration entry. The check SHALL report the count by disagreement type so a regression is visible
as a number, not as a silently different root.

#### Scenario: A new disagreement blocks the build

- **WHEN** a resource is updated and introduces a disagreement absent from the arbitration file
- **THEN** the check fails
- **AND** it names the word, both candidate roots, and the size of the affected family

#### Scenario: Baseline is measurable at any time

- **WHEN** the check is run on the current data
- **THEN** it reports the number of agreeing words, of disagreeing words, and the breakdown by type
- **AND** the target state is 0 unarbitrated disagreements out of the 757 present today

