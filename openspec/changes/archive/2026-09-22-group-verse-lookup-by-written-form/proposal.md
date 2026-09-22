## Why

On `/verse-study` → «الكلمة في الآيات», the header reports `عدد الألفاظ` as the number of
**lemmas** — dictionary entries — because that is what the backend groups by. For the query
«الآيات» it therefore prints **1 (آيَة)**, and the whole result list is one undifferentiated
block of 353 āyāt.

That answers a lexicographic question the page never asked. A reader studying a root through
the Quran wants to see how the word is actually **written** across its occurrences —
آيات، آياتنا، آية، آياته، آياتي — and to read each spelling's verses together. «لفظ» in this
page's sense is the *written word*, not the *lexeme*; the header has been using the term for
the other thing, and a count of «1» on the most common query reads as a bug.

The written forms need **no new information**. Highlighting already runs on positions
(`root_graph` × `word_index`), so for every displayed occurrence the engine knows exactly which
token of the vocalized row is marked — it computes that token's index and then discards which
word ref produced it. Clitic segmentation is likewise already on disk:
`data/derived/qac_words.json` carries `segments_detail`, so `بِـَٔايَٰتِنَآ` is known to be
PREFIX `بِ` + STEM + SUFFIX `نَآ`. Crossing the two yields `آياتنا` exactly.

That index is 248 MB resident, though, against `word_index.json`'s 64 MB, and the lookup path
holds neither today. So the build extracts the 0.5 MB the derivation actually needs — the
prefix string of the 26 001 words that have one — into its own dataset, and the request path
reads that.

## What Changes

### «لفظ» is redefined as the written form, and it becomes the grouping key

- A **لفظ** is the marked display token of an occurrence, with every mark removed
  (`arabic_text.bare()` — the dagger alef included, so `مُوسَىٰ` gives `موسى` and not `موسىا`),
  minus *exactly* the PREFIX segments QAC declares for that word. Pronoun suffixes are part of
  the لفظ (آياتنا ≠ آيات); the proclitics و/ف/ب/ل/ك/س/ٱل are not.
- Derivation is from the QAC segmentation, never from a regex over leading letters. A regex
  would strip the first radical of every root that begins with one of those letters —
  `وَلَد` → `لد`, `كِتَاب` → `تاب`.
- `عدد الألفاظ` reports the number of distinct ألفاظ, and the header lists them all, each
  chip scrolling to its block (as the lemma chips do today).

### The result list is grouped by لفظ instead of by lemma — **BREAKING**

- One collapsible block per لفظ, holding the surah cards, holding the verses. The lemma level
  is **removed from the screen entirely**: no lemma sections, no lemma count, no lemma chips.
  `lemma_index` remains an internal input (it carries the `word_refs` and `forms_found` the
  highlighter needs) but nothing about lemmas reaches the UI.
- Inside a لفظ block, only that لفظ's occurrences are highlighted. A verse holding two ألفاظ
  of the root appears in both blocks, each time with only the relevant word marked.
- The existing three-way ordering control («حسب المصحف» / «الأكثر آياتٍ» / «الأقلّ آياتٍ»)
  drives **both** levels: it orders the لفظ blocks and the surah cards inside them.

### `عدد السور` becomes a distinct count — **BREAKING**

- Today it is the SUM of the cards, an explicit past decision recorded in `CLAUDE.md`
  («the header adds up against what the reader sees»), whose accepted cost was قوم announcing
  225 of the 114 sūras that exist. With ألفاظ blocks that sum reaches 154 for «الآيات» (from
  59 today) and 330 for قوم.
- `عدد السور` SHALL therefore count **distinct sūras over the root**, joining `عدد الآيات` and
  `عدد المواضع`, which are already distinct. All four header figures then answer the same
  shape of question over the same filtered set.

### Proper nouns gain ألفاظ

- A rootless name (لوط، إبراهيم) is grouped by لفظ under the same rule; the header, which
  omits the لفظ list for proper nouns today, shows it. لوط yields لوط and لوطا.

### API response — **BREAKING**

- `VerseLookupResponse.lemmas: list[VerseLookupLemma]` is replaced by
  `forms: list[VerseLookupForm]`. The proper noun's display name, read from `lemmas[0]` today,
  moves to a top-level field. `POST /verse-lookup` stays mounted; only its body changes. The
  frontend is the only consumer.

### Stated consequences, accepted

- **Long roots produce long headers.** Across the corpus the median root has 3 ألفاظ and the
  mean is 6.6, but 58 roots exceed 30 and أتي reaches **150**. The chosen design lists them
  all rather than truncating.
- **Verses repeat across blocks.** 19 of the 353 āyāt of أيي hold two ألفاظ, so the page lists
  373 rows for 353 distinct āyāt (قوم: 643 rows for 597 āyāt). The header keeps reporting
  distinct āyāt.

## Capabilities

### New Capabilities
- `word-in-verses`: the «الكلمة في الآيات» tab as a whole — what a لفظ is and how it is
  derived, how occurrences are grouped and counted, what each header figure means, how the
  ordering control applies, and what the `/verse-lookup` response carries. No existing spec
  states these requirements; the behaviour shipped without one.

### Modified Capabilities
<!-- None. `verse-study` specifies the tab set, tab persistence, cross-tab navigation and
     deep-linking — none of which changes. `served-surface` lists `POST /verse-lookup` as a
     mounted route, which it remains; that spec does not constrain response bodies. -->

## Impact

**Backend**
- `retrieval/verse_lookup.py` — the لفظ derivation and grouping. `_positions()` must retain
  which word ref produced which token index instead of merging them per verse; `lookup()`
  regroups by لفظ.
- `api/models/verse_lookup.py` — `VerseLookupForm` replaces `VerseLookupLemma`.
- `ingestion/qac_treebank.py` (Stage 5) — already the writer of `qac_words.json`; emits the new prefix dataset alongside it, from the same parsed segmentation.
- `quran_data/paths.py`, `loaders.py`, `manifest.py` — one path constant, one lazy loader, one
  manifest entry for it (`tests/test_quran_data.py` fails without all three).

**Frontend**
- `frontend/src/app/verse-study/page.tsx` — the header counters, the chip list, the block
  structure, the ordering control's second axis, and the collapsed-state cache keys
  (`${root}:${lemma}:${surah}` → `${root}:${form}:${surah}`).
- `frontend/src/lib/types.ts` — the response types. **Not** `api.ts`: every backend response
  type lives in `types.ts`, which `api.ts` only imports from.
- `frontend/src/lib/strings.ts` — the ordering control's label, which named only the sūras.

**Tests (local-only)**
- `tests/test_verse_lookup.py` — new cases for the لفظ rule, the prefix guard, the single
  multi-token occurrence (39:56 «يَا حَسْرَتَا» → `حسرتا`), and the distinct `عدد السور`.
- `frontend/src/app/verse-study/page.test.tsx` — block structure and header assertions.

**Docs**
- `documentation/root-lookup.md` (French) — the pipeline description and its improvement list.
- `CLAUDE.md` — the `retrieval/` paragraph on `verse_lookup.py`, and the header-counting
  paragraph whose «سور is the SUM of the lemma cards» rule this change reverses.

**Data**
- One new derived file: the per-word-ref prefix map (~0.5 MB), written by the ingestion stage
  that already reads the QAC segmentation. It is `data/derived/`, therefore git-ignored and
  rebuilt by `python ingestion/run_pipeline.py`. No new *information* — it is an extract of
  `qac_words.json`, split out so the request path need not hold 248 MB to read 0.5 MB of it.
