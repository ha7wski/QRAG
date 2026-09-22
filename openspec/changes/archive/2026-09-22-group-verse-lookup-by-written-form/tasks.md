## 1. The prefix dataset (build side)

- [x] 1.1 In `ingestion/qac_treebank.py`, alongside the `qac_words` assembly, collect
      `word ref → joined PREFIX segment string` for every word whose `segments_detail` opens
      with one or more PREFIX segments; stop at the first non-PREFIX segment. Expect 26 001
      entries of 77 429.
- [x] 1.2 Write it to a new derived JSON file and add its path constant to
      `quran_data/paths.py` (never build the path by hand anywhere else).
- [x] 1.3 Add the `quran_data/manifest.py` entry: what it is, that `ingestion/qac_treebank.py`
      Stage 5 produces it, that `retrieval/verse_lookup.py` consumes it, that it is regenerable,
      and the exact rebuild command. `tests/test_quran_data.py` fails until the constant, the
      entry and the consumer list all agree.
- [x] 1.4 Add the lazy loader in `quran_data/loaders.py`, following the existing pattern
      (process-cached, `DatasetMissing` carrying the manifest's rebuild command).
- [x] 1.5 Rebuild with `python -m ingestion.qac_treebank` (Stage 5 runs standalone — the full
      `run_pipeline.py` was unnecessary). Observed: 26 001 entries, 108 distinct prefix
      strings, 469 718 bytes.

## 2. The لفظ derivation (engine)

- [x] 2.1 Add the fold helper to `retrieval/verse_lookup.py`: the display side is
      `arabic_text.bare()` unchanged; the prefix-comparison side is `bare()` plus `ٱ` →
      `ا`. Document at the definition why the dagger alef is deleted and not folded
      (`مُوسَىٰ` → `موسى`, not `موسىا`) and why no fourth normalizer is added to `arabic_text/`.
- [x] 2.2 Add the per-occurrence derivation: last marked display token → fold → strip the
      declared prefixes, each only when the folded token actually starts with it. Leave the
      token intact otherwise.
- [x] 2.3 Load the prefix map lazily, next to `_spine()`, degrading to "no prefix removed" with
      a logged rebuild command when the dataset is absent.
- [x] 2.4 Change `_positions()` to retain which word ref produced which token index instead of
      merging them per verse, and update its cache key. Keep the `(found, seen)` distinction —
      a verse in `seen` but not in `found` still means "fall back", not "no occurrence".
- [x] 2.5 Update the three callers of `_positions()` (lemma groups, `_tokens_for_root`, proper
      nouns) to the new shape.

## 3. Grouping and counting (engine)

- [x] 3.1 Rewrite `lookup()` to bucket refs by `(root, لفظ)` instead of by lemma group, keeping
      `lemma_index` as the internal source of `word_refs` and `forms_found`.
- [x] 3.2 Scope each block's `match_indices` to that لفظ's refs only, so a verse holding two
      ألفاظ marks a different word in each block.
- [x] 3.3 Order the blocks by the recitation position of each لفظ's first occurrence.
      Defect found by the orchestrator's comparator and fixed: `_form_blocks` sorted within
      ONE root, and `lookup()` concatenated roots, so a homograph query (كل → أكل / كلل / كيل)
      emitted مأكول (105:5) ahead of كلما (2:20). `lookup()` now re-sorts across roots; the
      client breaks its count ties on the received order, so this had to be right on the wire.
- [x] 3.4 Keep `occurrences` and `total` as distinct counts over the emitted set — the existing
      `_word_count` / `seen_verses` logic, unchanged in meaning.
- [x] 3.5 Apply the same grouping to the proper-noun branch, and carry the vocalized name out
      of the group so the root bar can still show it.

## 4. API contract

- [x] 4.1 In `api/models/verse_lookup.py`, replace `VerseLookupLemma` with `VerseLookupForm`
      (`form`, `count`, `occurrences`, `verses`).
- [x] 4.2 Replace `VerseLookupResponse.lemmas` with `forms`, and add the top-level proper-noun
      display name. Remove every lemma field.
- [x] 4.3 Confirm `POST /verse-lookup` stays mounted and `tests/test_served_surface.py` still
      passes (the route set is unchanged; only the body is).

## 5. Frontend

- [x] 5.1 Update the response types in `frontend/src/lib/types.ts` — **not** `api.ts`, which
      only imports `VerseLookupResponse` and needed no edit. The plan named the wrong file.
- [x] 5.2 Replace the lemma sections with لفظ blocks in
      `frontend/src/app/verse-study/page.tsx`, keeping the sūra-card and verse levels inside.
      Remove every lemma label, count and chip.
- [x] 5.3 Header: `عدد الألفاظ` = number of blocks, with every لفظ listed and each entry
      scrolling to its block; `عدد السور` = one `Set` over all blocks' verses (distinct), not a
      sum. Keep `عدد المواضع` omitted when zero.
- [x] 5.4 Extend the ordering control to both levels under one selection: blocks by distinct-āya
      count (ties by earlier first occurrence, in both directions, as an explicit second key —
      not sort stability), sūra cards as today. Keep it hidden when there is nothing to order.
      Collateral, done: the control's label «ترتيب السور» became «الترتيب» — one selection now
      orders both levels, so a label naming only the sūras would be false on screen. Not pinned
      by any spec or test; a one-line revert in `strings.ts` if the owner prefers the old wording.
- [x] 5.5 Update the collapsed-state cache keys from `${root}:${lemma}:${surah}` to
      `${root}:${form}:${surah}`, and the block anchor ids the header entries scroll to.
- [x] 5.6 Show the proper noun's name from the new top-level field, and show its ألفاظ list
      (previously omitted for proper nouns).

## 6. Tests (local-only)

- [x] 6.1 `tests/test_verse_lookup.py` — the derivation: `2:39:4` (`بِآيَاتِنَا`) → `آياتنا`;
      a root starting with a proclitic letter keeps its first radical (`ولد` → `ولد`);
      `مُوسَىٰ` → `موسى`; `39:56:4` (`يَا حَسْرَتَا`, two marked tokens) → `حسرتا`; a merged
      interrogative hamza leaves the token intact (`آللَّهُ`).
- [x] 6.2 `tests/test_verse_lookup.py` — the grouping: «الآيات» yields the nine blocks
      `آيات، آياتنا، آية، آياته، آياتي، آياتك، آيتك، آيتين، آياتها`; a verse holding two ألفاظ
      appears in both blocks with different `match_indices`; no block for a grammatical tool.
- [x] 6.3 `tests/test_verse_lookup.py` — the counts: «الآيات» reports 382 / 353 / 9, and the
      blocks list 373 verse rows against 353 distinct āyāt.
- [x] 6.4 `tests/test_verse_lookup.py` — proper nouns: «لوط» yields two blocks (`لوط`, `لوطا`)
      and carries the vocalized name; «موسى» yields one.
- [x] 6.5 A test asserting the lookup path does not make `qac_words.json` resident.
- [x] 6.6 `frontend/src/app/verse-study/page.test.tsx` — block structure, header figures, and
      that no lemma label renders. Type-check with `npx tsc --noEmit -p tsconfig.test.json`.
- [x] 6.7 Run `python -m pytest -q` (1319 passed, 2 skipped), `npx vitest run` (156 passed,
      10 files) and `npx tsc --noEmit -p tsconfig.test.json` (clean).
      Extra, not in the plan: `tests/test_basmala_api.py` also read the removed `lemmas`
      key in two places and needed the same rename.
      Extra, not in the plan: the suites were MUTATION-TESTED — five deliberate breaks of
      the engine and five of the page. All ten are caught. The tenth only after adding a
      test: desyncing the header chips from the block order left every assertion green,
      though `goToForm` addresses blocks by index and a drift lands the reader on the
      wrong block with no visible symptom.

## 7. Documentation

- [x] 7.1 `documentation/root-lookup.md` (French) — new §2 bis on the لفظ derivation, the
      grouping and highlight scoping in §1, `word_prefixes.json` + `word_function.json` added
      to §3's file table with the 248 MB / 0.5 MB reason, and both Stage-4 and Stage-5
      standalone rebuild commands. NOTE: the improvement list closes NOTHING — §5.1's two
      items were already resolved and the homograph half of §5.2 is untouched. Added instead
      a third bullet recording that the same per-occurrence data made this grouping possible.
- [x] 7.2 `CLAUDE.md` — the `retrieval/` paragraph on `verse_lookup.py` (grouping by لفظ, the
      new dataset and its 248 MB / 0.5 MB rationale) and the header-counting paragraph, whose
      «سور is the SUM of the lemma cards» rule this change reverses. State the new rule and why.
- [x] 7.3 `arabic_text/marks.py` — record at `bare()` that a لفظ is a grouping key which is
      also displayed, so its "never display" warning is not read as forbidding this use.

## 8. Verify against the running app

- [x] 8.1 Verified in Chrome against a freshly started backend (:8001) and a rebuilt frontend
      (:3000). Header reads exactly `عدد المواضع : 382 · عدد الآيات : 353 · عدد السور : 59 ·
      عدد الألفاظ : 9` with all nine ألفاظ listed, bare, in first-occurrence order.
      NOTE: the app found running was STALE — backend started before this change (it still
      served `lemmas`) and a frontend production build from before the page was rewritten.
      Verifying without restarting both would have verified nothing.
- [x] 8.2 Verified on the live backend: 6:157 is listed in two blocks and marks a different
      word in each — token 32 `آيَاتِنَا` under `آياتنا`, token 23 `بِآيَاتِ` under `آيات`.
      Visually, the `قوم` block gathers `لِقَوْمٍ` and `ٱلْقَوْمَ`: two displayed spellings, one لفظ
      once the proclitics come off, each highlighted whole in its own verse.
- [x] 8.3 One click on «الأكثر آياتٍ» reordered BOTH levels: block `آيات` (145 āyāt) to the
      top, and inside it `آل عمران` (15 āyāt) to the top. The header chips followed the
      blocks, which is the invariant `goToForm`'s index addressing depends on. The choice
      persisted across the next search, as a preference.
- [x] 8.4 `قوم` renders `660 · 597 · 79 · 69` with its 69 ألفاظ wrapping over five lines,
      dense but intact. `عدد السور : 79` is under the 114 that exist — the reversed rule
      doing its job, where the old sum would have announced 330.
