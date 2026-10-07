## Context

`scripts/build_quran_close_verses.py` (change `unify-close-verses`, D5) gives every close pair a common
part: the shared passage, else the best Smith–Waterman alignment of the two verses' QAC lemma
sequences. It stores `k` (matched words), `wa`/`wb` (1-based inclusive word span per verse) and
`ca`/`cb` (one half-open character span per verse in the displayed `text_ar_tashkil`). Three surfaces
colour `ca`/`cb` as one block: the reading page's orange words (`lib/annotations.ts`), its bubble
(`CloseVersesBubble.tsx`) and the map's cell list (`QuranSimilarityMap.tsx`, whose hub shows the union
of its pairs' spans).

An alignment cannot cross: two words shared in a different order cannot both be matched, so the span
both includes unmatched words (gaps) and excludes displaced shared words. Measured on today's file:
1 103 of 2 462 pairs colour 2 215 unmatched words; 916 leave 1 564 shared content words uncoloured.
2:3 / 14:31 is the user's case: `matches = (1,3)(2,4)(4,5)(5,6)(6,8)(7,9)`, `wa = [1,7]`,
`wb = [3,9]` — أَنفَقَ (2:3 word 8, 14:31 word 7) crosses رزق and is matched on neither side.

Constraint: this change is DISPLAY ONLY. The pair set, `sim`, `pas`, `score` and the passage dataset
are untouched, so every figure measured under `unify-close-verses` stays valid.

## Goals / Non-Goals

**Goals:**
- Colour exactly the words the two verses share, whatever their order, on both sides.
- Keep each coloured word's partner in the data (the later relation change scores from it).
- One definition, computed once at build time; no request computes a matching.

**Non-Goals:**
- Changing which pairs exist, their scores, `pas`, or the passage relation (step 2 of the plan, a
  separate measured change: order-invariant lexical core × syntax × semantics).
- IDF weighting: it only matters for a score; for choosing partners it is constant within a lemma
  and is left to step 2.
- UI linking a hovered word to its partner. The data carries it; no surface uses it yet.

## Decisions

**D1 — Content words.** A word is matchable when it carries a root (the passage build's `content`
flag, `Corpus.content`) AND its reference is not in `word_function.json` (a grammatical-tool
occurrence: vocative أَيّ, interrogatives, conditionals). Same exclusion Word in Verses applies, so a
«يا أيها» never counts as shared meaning. Alternative rejected: the passage build's flag alone — it
lets أَيُّهَا be «shared» between any two vocative verses.

**D2 — The matching.** A maximum-weight one-to-one bipartite matching between the content words of
A and of B (`scipy.optimize.linear_sum_assignment`, `maximize=True`; scipy is already a dependency
of the passage build). Edge weight: 1 when the two words have the same token (the passage build's
lemma token — identical tokens, identical rule), else 0.5 when their resolved primary roots are
equal (`Corpus.roots`), else no edge. Every weight carries a tie-break `− 10⁻³ · |p/n_A − q/n_B|`
(relative position), so among equal partners a word takes the one at the nearest relative place —
deterministic, and the matching stays order-INVARIANT (order only breaks exact ties). Kept edges:
weight > 0. Each kept edge records `(p, q, kind)`, `kind ∈ {"lemma", "root"}`.
Alternatives rejected: greedy left-to-right (order-dependent again); bag intersection without
partners (loses which word answers which, needed by step 2); Smith–Waterman plus a second pass for
the leftovers (two definitions for one notion).
Prototype on today's pairs: 2:3 / 14:31 → `(2,4) (4,5) (5,6) (7,9) (8,7)`, all `lemma` — ينفقون is
matched, بالغيب is not; 2 403 pairs reach ≥ 2 matched words, 88 have 1, 401 edges are `root`.

**D3 — Bridging function words.** For two matched pairs `(p, q)` and `(p', q')` with `p < p'` and
`q < q'` (same order on both sides) and no matched pair `(r, s)` with `p < r < p'` AND `q < s < q'`,
the UNMATCHED words strictly between them are coloured on both sides when the two sequences of
unmatched in-between tokens are identical (and not empty). This keeps «مِنْ» inside 28:20 / 36:20's
«وَجَاءَ … قَالَ» coloured, so a shared passage still reads as one run; a function word that only one
verse holds, that differs between the verses, or that sits between crossing partners stays plain.
Bridged words carry no partner and do not count in «N كلمات مشتركة».
*Amended during implementation:* the first wording («consecutive among A's matched words, partners
consecutive among B's») could not satisfy its own 28:20 / 36:20 scenario — the displaced «رَجُل» is
matched between «مِنْ»'s neighbours in 36:20, so those neighbours' partners are never consecutive and
«مِنْ» would stay plain, splitting each verse into two runs. Matched words are therefore skipped by the
comparison instead of blocking it. Consequence, accepted: the rule colours everything the first wording
did plus bridged words in 65 of today's 2 403 common parts (one to three function words each, identical
on both sides), e.g. «وَمِمَّا» of 2:3 with «مِمَّا» of 14:31 beside the displaced «يُنفِقُونَ» — a word
both verses hold right before their shared «رَزَقْنَاهُمْ». Pinned in
`tests/test_quran_close_verses_build.py` (`test_the_bridge_skips_a_matched_word_…`).

**D4 — When a pair has a common part.** At least 2 matched content words (the current `MARK_MIN`).
Otherwise the pair carries none and is shown plain, as today. A passage pair always qualifies (its
alignment holds ≥ 3 content matches, all of which the matching can also take).

**D5 — Stored shape (schema 2).** `k`, `wa`, `wb` stay — they are the passage's figures and `pas`
reads `k`. The common part becomes:
- `m`: `[[p, q, "lemma"|"root"], …]`, sorted by `p`, word numbers 1-based;
- `ca`, `cb`: lists of half-open character spans `[[s, e], …]`, ascending, one per RUN of
  consecutive coloured words of that verse (matched or bridged), the run running from its first
  word's start to its last word's end in the displayed text — so the space between two coloured
  neighbours is coloured too.
`m`, `ca`, `cb` are present together or absent together; `k`/`wa`/`wb` keep their own presence rule
(passage or alignment), since `pas` and the evaluation read them. The header names the matching
rule, the weights, the tie-break, D3 and the threshold; the schema constant
`QURAN_CLOSE_VERSES_SCHEMA` moves to 2 so a stale file is refused with its rebuild command.
Alternative rejected: one span per word — the reader would have to re-merge adjacent words, and
`mergeSpans` only merges touching spans, not ones separated by a space.

**D6 — Serving.** `retrieval/quran_close_verses.py` validates the new shape; served pairs carry
`words` = `len(m)`, `spans_u`, `spans_v` (lists, oriented: `u` the lower surah), null together;
`ayah_view` / the annotations route serve each side's list oriented to the āya. Routes keep their
paths; only the field names/types change.

**D7 — Frontend.** `types.ts` follows the API. `annotations.ts` already unions lists of spans
(`mergeSpans`, `splitMarked`); it takes the lists instead of wrapping one span. The map's `groupPairs`
pushes every span of a pair (hub: union across its pairs). The bubble marks the partner's list.
Visual: unchanged colours; a common part may now show several orange runs in one verse.

## Risks / Trade-offs

- [A root-level edge colours a word whose meaning differs (same root, different lemma, e.g. آمنوا /
  الأمانة)] → `kind` is stored; 401 such edges today. Accepted for display; step 2 weights them at 0.5
  in the score and may show them in a lighter tone if the reader wants.
- [Fragmented colouring when shared words are scattered] → that is the truth of the pair; D3 keeps
  genuine shared passages in one run.
- [Changing the schema breaks a stale dataset] → the loader refuses schema 1 with the rebuild command;
  routes answer 503 with it, the reading page shows the sūra unannotated (existing behaviour).
- [The rebuild needs the backend stopped and the cross-encoder] → no new cost: the matching is
  model-free and adds seconds to the existing ≈ 2.5 min build. The integrity checks (stale `dense`)
  stay.
- [The `unify-close-verses` spec scenario «the span starts with وَجَاءَ and ends with قَالَ»] → kept as
  «the runs, together, start … and end …»; with D3 28:20 / 36:20 is one run.

## Migration Plan

1. Implement build + reader + routes + frontend in one change (the API change is breaking and has one
   client).
2. Stop the backend, run `python scripts/build_quran_close_verses.py`, restart.
3. Check: `python scripts/eval_quran_close_verses.py` prints the same figures as before (inputs and
   scores unchanged — only the header's common-part fields differ); 2:3 / 14:31 colours ينفقون.
Rollback: `git revert` the change and rebuild the dataset (schema 1).

## Build result (task 5.2)

Rebuilt 2026-10-06 under this change: 2 491 pairs, pair set, order, `sim`, `pas`, `score`, `from` and
`roots` identical to the schema-1 file on every pair; `eval_quran_close_verses.py` unchanged
(AUC(score) 0.726 on 89 × 7, U2/U3/U4 PASS, U1 MISS as before). Common part on 2 403 pairs (212 without
a passage; every passage pair has one), 12 584 matched words, 399 `root` edges, 1 666 pairs coloured in
several runs. 2:3 / 14:31: `words` = 5, 2:3 coloured «يُؤْمِنُونَ» + «وَيُقِيمُونَ … يُنْفِقُونَ»,
«بِالْغَيْبِ» plain.

## Open Questions

None blocking. Showing `root` edges in a lighter tone is deferred to step 2.
