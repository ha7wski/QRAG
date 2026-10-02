## Context

Every per-root figure the tab needs already exists, and each one comes from a single authority:

- **Root set.** `morphology.json` has 1 656 keys. 1 651 come from the QAC morphology file, and five
  come from `root_resolver.py` arbitration: `اول`, `اني` and `معن` carry occurrences, while `طمن` and
  `نوس` are alternate-only, with `count == 0`.
- **Figures.** `VerseLookup.root_forms(root)` returns `words`, `ayat` and `verse_ids` after the
  grammatical-tool filter. «تحليل اللسان» already reads its المواضع block from it, so that the two
  pages never disagree. Measured over all 1 656 keys: **0.9 s** in total, no root empties, and the
  full detail is ~600 KB of JSON (44 736 āya refs).
- **Letter reading.** `assemble(root)` gives the project's mechanical sentence for **1 613** roots and
  refuses 43, all `not-triliteral`. It is pure: no disk access beyond the two frozen, digest-checked
  tables, and no model.
- **Sūra names.** `GET /surahs` metadata already exists.

The request reads «la lecture de lisan produite après décomposition des lettres … hors
interprétation d'Islambouli». The recent feature that decomposes a root into its letters and produces
a sentence is the mechanical assembly (commit `dd22ca6`). What it explicitly is *not* is Islambouli's
own interpretation: his published sentences and the cultural stage. The assembly's label already says
so («لا قولُ إسلامبولي»).

## Goals / Non-Goals

**Goals:**
- Let a reader browse every root by its first letter, with nothing to type.
- For each root, show where it occurs (distinct āyāt, distinct sūras), with the same figures as
  «الكلمة في الآيات» and «تحليل اللسان».
- For each root, show the mechanical letter reading, labelled as the app's.

**Non-Goals:**
- Showing the full verse text in the index. The āya refs link to `/verse/{s}/{a}`; text lives on
  the pages built for it.
- Islambouli's published sentences, the cultural stage, signed personal readings, choosing between
  alternatives, and the core-first reading (5 curated roots; it would be empty on almost every card).
- Search or filtering inside the index. Typing a word already has two pages.
- A precomputed dataset, a build step or a `manifest.py` entry.
- Any change to `assemble.py`, `root_forms` or the root set.

## Decisions

### D1 — List primary roots only (`count > 0`)

`root_forms("نوس")` is not empty: the lemma groups reach ٱلنَّاس through the alternate. Listing
alternate-only keys would therefore show the same occurrences under two roots, and would contradict
the family-count rule (counts tally the primary only). The criterion is the existing `count` field,
not a new curated list.

*Alternative considered:* list all 1 656 keys and mark alternates as «قراءة بديلة». That doubles the
occurrences, and the explanation belongs on `/lexical`, not in an inventory.

### D2 — Group by first radical, with hamza and bare alif in one «أ» group

There are 29 distinct first characters on disk. `ا` begins exactly two roots (`اول`, `اني`), and both
are hamza roots written bare by the treebank. A separate «ا» group of two would be an artefact of
spelling, not of the language. The grouping key is the first radical passed through
`arabic_text.fold_carrier` and then mapped onto `أ`. For in-group ordering, the comparison key folds
carriers (consistent with the lookup fold), and the exact spelling breaks ties, so the order is total.
Pick the fold from the comparison table in `arabic_text/__init__.py`. `normalize_text` is excluded
because it *deletes* hamza.

*Alternative considered:* group by Unicode codepoint. That splits أ / إ / آ / ء into four groups and
orders them by codepoint rather than hijāʾī.

### D3 — Compute on request, per letter, cached in-process

Computing every root costs 0.9 s, and one letter averages ~60 roots, i.e. tens of ms. The router
builds a letter's payload on first request and memoises it (`functools.lru_cache` keyed on the group
label, or a dict on `app.state`). `GET /roots` needs only the root keys and the grouping, not
`root_forms`.

*Alternative considered:* a `data/derived/root_index.json` built by the pipeline. That means a new
manifest entry, a rebuild step and a way to drift from `root_forms`. Cheap computation does not justify
any of it.

### D4 — One router, borrowing only its own dependencies

The new module is `api/routers/roots.py`. It reads `app.state.verse_lookup` (for `root_forms`) and
the root keys through `quran_data.loaders`, never by opening `morphology.json` by hand. It imports
`linguistics.lisan.islambouli.assemble` *inside* the function, as `api/routers/lisan.py` does, and
catches `TableNotFrozen` / `WasfNotFrozen` once per request so that a tampered table degrades to «no
readings» (spec: *A tampered table degrades*). It must not borrow a dependency through another
feature's object (the CLAUDE.md rule about `app.state`). Models go in `api/models/roots.py`.

The shaping logic (grouping, ordering, sūra derivation) is pure: no FastAPI, no disk. It is a few
functions inside the router module, or a small helper next to it, so that it can be tested offline.
It does **not** go under `linguistics/` (that would be a leaf importing `retrieval/` to serve a page)
and it does not go under `retrieval/` (that would add display concerns to a pipeline stage).

### D5 — The reading is called with no `SignedChoices`, always

The roots router never reads `app.db` or `GET /lisan/reading`. That keeps alternatives bracketed for
every root, with no code path that could apply a stored choice. It is the index-level counterpart of
the assembly spec's «no automatic path selects an alternative». The label string is shared with
`/lexical` through `lib/strings.ts` and is not retyped.

### D6 — Page shape

`/roots` is a client page:

- a letter strip of 28 buttons with counts;
- `?letter=` in the URL, written with `router.push` so that Back steps between letters (read through
  `useSearchParams` under a Suspense boundary, as `/lexical` and `/verse-study` do). A first version
  used `router.replace` to keep history short; the reader wants Back to work between letters, and
  the URL — not component state — is what the page renders from, so Back needs nothing else;
- one card per root.

A card shows its root and its counts; the rest is folded behind its header (a button carrying
`aria-expanded`), because a letter renders ~100 cards and the reader scans roots before reading one.
Unfolded, it reads: the reading → «السور» (chips with Arabic names) → «المواضع» (the ألفاظ that
`root_forms` already returns, as `forms`, so the card lists exactly the written forms «الكلمة في
الآيات» groups by) → two green buttons, «الكلمة في الآيات» (`/verse-study?word=`) and «تحليل لساني»
(`/lexical?word=`) to its left. The card carries no āya list: a first version had one (āyāt labelled
«<sūra> <āya>» behind their own control), and the reader preferred to read a root's āyāt where they
are shown in full, on «الكلمة في الآيات».
`verse_ids` stays in the payload — the sūras are derived from it, and it costs nothing.

Nav icon: a lucide icon not used elsewhere, such as `ListOrdered` or `LibraryBig`. It must differ
from `ListTree` (Verse Study) and from the brand icon.

### D7 — Refusal reasons are Arabic at their source

The assembly's refusal reasons (`compose()`'s not-trilateral, `assemble()`'s silent position and
missing formula) are user-facing: `/lexical` and `/roots` both print them. They are written in Arabic
in `linguistics/lisan/islambouli/compose.py` and `assemble.py` themselves, rather than translated by
each page from `refusal_code`, so no consumer can print English by forgetting a mapping. The codes stay
English: they are identifiers, never displayed. `roots.py` no longer falls back to the code when a
reason is empty.

## Risks / Trade-offs

- **[Large letters]** Letters such as س or ن hold ~106 roots, so they render ~106 cards, each with
  sūra chips. → The āyāt are collapsed and the verse text is never fetched; if it proves slow, render
  the cards progressively. No pagination in v1.
- **[A reader may take the assembly for a definition]** → The label is mandatory and identical to
  `/lexical`'s. Refused roots show their reason rather than an empty slot, so silence is never
  mistaken for meaning.
- **[First-request latency]** `root_forms` needs `VerseLookup` warm, and it is built in the lifespan,
  so the first letter costs tens of ms. Acceptable.
- **[Figures drift between pages]** → They cannot: the index calls `root_forms` and does not count
  anything itself. A parity test pins رحم and كيف.
- **[Alternate-only keys may grow]** A future arbitration may add another one. → D1's `count > 0`
  rule covers it without edits.

## Migration Plan

The change is purely additive: two new routes and one new page. Rollback means removing the
`include_router` line and the nav entry. No data or schema migration is needed.

## Open Questions

- Should the «أ» group display its label as «أ» or as «ا / أ»? (Default: «أ».)
- Should root cards also show the ألفاظ list that `root_forms` returns? It is free, but it was not
  requested. (Default: no; it is on `/lexical`.)
