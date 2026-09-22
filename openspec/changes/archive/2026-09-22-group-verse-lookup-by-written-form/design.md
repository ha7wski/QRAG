## Context

`retrieval/verse_lookup.py` resolves a typed word to root(s), splits each root's occurrences
into **lemma groups** read from `data/derived/lemma_index.json`, and returns one vocalized
verse row per āya with the token indices to highlight. `api/routers/verse_lookup.py` is a
thin passthrough; `frontend/src/app/verse-study/page.tsx` renders lemma sections → sūra cards
→ verses and derives the header figures.

Highlighting already runs on **positions**, not text: `_positions(key, refs, forms)` walks a
group's `word_refs`, reads each ref's character span from `word_index.json`, rebases it past
the Basmala, and converts it to display-token indices. It then **merges every ref of the
group into one list per verse** — `found[(s, a)] = [3, 11]` — and forgets which ref produced
which index. That last merge is the only reason the written form is not already available: the
information exists one line earlier in the same loop.

Two constraints shape everything below:

- **The three-normalizer footgun.** `arabic_text/__init__.py` carries the comparison table for
  `normalize_text` / `normalize_search` / `normalize_root`, and picking wrong fails *silently*
  — still Arabic, still reviews clean. This change adds a fourth fold-shaped operation, so it
  must compose an existing one rather than write a new mark class. `arabic_text/marks.py`
  already exposes `bare()`, whose set (harakat + tatwīl + waqf marks, dagger alef included) is
  exactly what a written form needs.
- **The memory budget.** `CLAUDE.md` records a hard freeze on a 16 GB Mac, and the codebase
  answers it with lazy loading everywhere (`HybridSearch.embedder`, `VerseLookup._spine`,
  `LazyReranker`). Measured for this change: `word_index.json` costs **+64 MB** resident,
  `qac_words.json` **+248 MB**. The lookup path pays the first and must not start paying the
  second.

## Goals / Non-Goals

**Goals:**

- Make «لفظ» mean the *written form* everywhere in this tab, derived from data already on disk.
- Group the results by لفظ, one block per form, with highlighting scoped to the block.
- Keep the four header figures answering the same shape of question over the same filtered set.
- Add no measurable memory to the lookup path.

**Non-Goals:**

- **Homograph disambiguation.** Which root of `كل` sits in *this* verse remains open
  (`documentation/root-lookup.md` §5.1); this change does not touch root resolution.
- **Re-surfacing the lemma elsewhere.** The lemma is removed from this tab, not relocated to a
  tooltip, a secondary panel, or the QLisan fiche. `/qlisan` already answers per-word morphology.
- **Changing which occurrences are shown.** The grammatical-tool filter, the root resolution
  ladder, the Basmala rebase and the highlight spine all keep their current behaviour. Only the
  grouping, the counting of sūras, and the response shape change.
- **A `/search` or `/qlisan` change.** Those paths do not read lemma groups.

## Decisions

### 1. Derive the لفظ in the engine, at the point positions are resolved

`_positions()` gains a per-ref result: `{word_ref: [token index…]}` alongside the existing
per-verse map, or replaces the per-verse map with a per-ref one the caller collapses. `lookup()`
then reads each ref's marked token, computes its لفظ, and buckets the ref under it.

*Alternative — compute in the frontend from `match_indices` + verse text.* Rejected. The
browser has no QAC segmentation, so it would either ship a prefix map to the client or guess
prefixes from leading letters — the regex the spec forbids. Normalization also belongs to the
backend by repo convention; `frontend/` holds no Arabic fold today and should not acquire one.

*Alternative — precompute the whole grouping at ingestion (root → لفظ → refs).* Rejected as
premature. The grouping depends on the grammatical-tool filter and on the highlighter's
narrowing, both of which live at request time; freezing their output into a dataset would make
a filter change require a pipeline rebuild. Only the *prefix strings* are frozen (decision 3),
because those are a property of the word, not of the query.

### 2. Fold with `arabic_text.bare()`, composed locally — do not add a fourth normalizer

The display token is folded with `arabic_text.bare()` and nothing else. The QAC prefix strings
need one more step (`ٱ` → `ا`, since QAC writes the article both `ٱلْ` and `الْ`), so
the module defines a small local helper for the *prefix side only* — the same shape as the
existing `_norm_match` in this file, whose docstring already records why a local composition
beats widening a shared fold.

`bare()`'s docstring says "a COMPARISON KEY, never a value to store or display". This change
displays its output, which is a genuine deviation and must be recorded there rather than left
for the next reader to trip over: a لفظ is a *grouping key that is shown as its own label*. The
warning's real target — a bare form stored where the exact spelling matters, the trap that bit
the root-keyed curated lists — still holds, and nothing here stores a لفظ as a root.

*Alternative — fold `ٰ` to a plene alef.* Rejected, and measured: it turns `مُوسَىٰ` into
`موسىا`, a spelling that occurs nowhere, splitting a name's 136 occurrences under a bogus label.
The corpus writes a plene alef where it means one (`آيَاتِ`), so the dagger is always a mark here.

*Alternative — also fold `ٱ` on the display side.* Rejected: the vocalized corpus contains
it in 0 of 6 236 rows, so the rule would be unreachable and untestable.

### 3. Extract the prefix strings into their own dataset

The ingestion stage that already reads the QAC segmentation writes a `word ref → prefix string`
map for the 26 001 of 77 429 words that carry a prefix — 0.5 MB of JSON, 108 distinct prefix
strings. `VerseLookup` loads it lazily through the registry, like the spine.

*Alternative — read `qac_words.json` directly.* Rejected on the measurement: +248 MB resident to
read 0.5 MB of content, on the path this repo has already made lazy twice for less. It is also
shared with QLisan, so a backend serving both would pay it either way — but a backend serving
only Verse Lookup would start paying it for nothing.

*Alternative — read `data/source/quran-morphology.txt` through `quran_data/qac.py`.* Rejected:
re-parsing the source per process is the cost `qac_words.json` exists to avoid, and `qac.py`
is deliberately the ONE reader of that file for the *build*, not for the request path.

Missing dataset degrades rather than fails: no prefix removed, rebuild command logged. That is
the path `lemma_index`, `root_graph`, `word_index` and `word_function` all already take.

### 4. Key the groups on `(root, لفظ)`, order them backend-side by first occurrence

A query resolving to several roots (homographs) could in principle produce the same spelling
under two roots; keying on the pair keeps them separate, matching how the root bar already
prints `root1 / root2`.

The backend emits blocks in a canonical order — the recitation position of each لفظ's first
occurrence — and the frontend re-sorts. This mirrors today exactly: the backend sorts verses in
recitation order and `sortSurahs()` reorders client-side, so the ordering control stays a pure
client concern with no round-trip.

### 5. `عدد السور` is derived client-side from the emitted blocks

No new response field. The frontend takes one `Set` over every block's verses. The point is
structural: `CLAUDE.md`'s standing rule is that the header "can only ever describe what the
cards below it contain", and deriving from the rendered blocks makes that true by construction
rather than by two implementations agreeing. `عدد المواضع` and `عدد الآيات` stay backend-computed,
as they are today.

### 6. `lemmas` → `forms`, with the proper noun's name promoted

`VerseLookupLemma` becomes `VerseLookupForm` (`form`, `count`, `occurrences`, `verses`), and
`VerseLookupResponse.lemmas` becomes `forms`. The proper noun's vocalized name, which the header
reads from `lemmas[0].lemma_display` today, becomes a top-level field — otherwise removing the
lemma grouping would remove the name the root bar displays.

Renaming rather than adding a parallel field: the frontend is the only consumer, and a response
carrying both would leave the old grouping alive and unread, which is the state
`test_frontend_reachability.py` and the six unmounted routes exist to prevent.

## Risks / Trade-offs

- **A long header on 58 roots (أتي: 150 ألفاظ)** → Accepted by decision; the header already
  stacks vertically past two entries, so it grows in height rather than breaking. Flagged in the
  proposal as a stated consequence, not hidden.
- **Verses repeat across blocks (373 rows for 353 āyāt on أيي; 643 for 597 on قوم)** → Inherent
  to grouping by form. Mitigated by keeping every header figure a distinct count, so the totals
  never inherit the duplication.
- **Losing the lemma removes a real distinction** — قوم's 18 lemmas separate قَوْم from مَقَام from
  أَقَامَ, and grouping by form scatters them across 69 blocks with no sense boundary → The
  distinction remains reachable per word on `/qlisan`. Recorded here because it is the one thing
  this change trades away, and the decision was made with that in view.
- **`_positions()` is on the highlight path** — its cache key and return shape change, and every
  caller (lemma groups, root fallback, proper nouns) reads it → The three callers are all in this
  file; `tests/test_verse_lookup.py` pins the highlight output, so a regression fails loudly
  rather than showing up as a mis-marked word.
- **The prefix dataset can drift from `qac_words.json`** → It is an extract of the same build
  input, written by the same stage, so they cannot be regenerated separately. The manifest entry
  records the relationship (`tests/test_quran_data.py` requires one).
- **`عدد السور` changes meaning for existing users** → It changes from a sum to a distinct count,
  which for the single-lemma roots that dominate queries is *no visible change at all* (أيي reads
  59 before and after). It is visible only where it was previously misleading.

## Migration Plan

1. Ship the ingestion change and rebuild: `python ingestion/run_pipeline.py`. Backwards
   compatible — the new file is additive and nothing reads it yet.
2. Ship the engine + model change. `POST /verse-lookup` changes shape in the same commit as its
   only consumer; there is no external client and no version negotiation to arrange.
3. Frontend and backend deploy together (they already do — one repo, one launcher).

Rollback is a revert: no data is mutated, `data/derived/` is rebuilt from source, and the new
file is inert if the engine no longer reads it.

## Open Questions

None blocking. Two settled by measurement during design and recorded here so they are not
reopened: the dagger alef is deleted rather than folded (decision 2), and the prefix data is
extracted rather than read from `qac_words.json` (decision 3).
