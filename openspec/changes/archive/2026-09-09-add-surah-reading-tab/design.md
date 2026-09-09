## Context

`/surah/{n}` already renders a whole sūra as one continuous vocalized block. It is
reachable only by clicking a verse reference from another page — no navigation entry, no
picker — and it renders the Basmala welded onto āya 1 for 112 sūras.

The defect is in the data, not the component. `data/raw/quran_chakl.csv` is the only
source of vocalized text, and it prepends the Basmala to āya 1 of **113 sūras** (all but
at-Tawba; in al-Fātiḥa the Basmala genuinely *is* āya 1). Because `verse_from_record`
auto-fills `text_ar_tashkil` from that CSV and every frontend surface renders
`text_ar_tashkil || text_ar`, the artefact is already on screen in chat sources,
`VerseCard`, `/verse/{s}/{a}` and «دراسة الآية».

Three facts, verified against the data in this repository, constrain any fix:

1. **`chakl_by_ref()` is addressed by character offset.** `analysis/qlisan_data.word_index()`
   stores `chakl_char_start`/`chakl_char_end` computed against the Basmala-**inclusive**
   string — `2:1:1` (`الٓمٓ`) is recorded at `[39, 42)` in a 42-character row. The QLisan word
   fiche and `analysis/mizan._vocalized_surface` slice by those offsets. Stripping inside the
   shared cached loader shifts every one of them.
2. **An exact-string match cannot find the Basmala.** A hand-typed
   `text.startswith("بِسْمِ اللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ")` matched **0 of 114** rows in this
   corpus: combining-mark order is not stable, so visually identical strings differ by
   codepoint sequence.
3. **A literal Arabic character class is not reviewable.** While prototyping, a diacritic
   class written with literal Arabic characters silently matched letters and reduced whole
   āyāt to whitespace — and the broken class was visually indistinguishable from the
   correct one, because bidi reordering rearranges what a range looks like on screen.

## Goals / Non-Goals

**Goals:**

- A «سور القرآن» navigation entry that opens a sūra picker and reads the chosen sūra.
- One rendering path shared by `/surah` and `/surah/{n}`, so deep links keep working and
  the two can never drift apart.
- `text_ar_tashkil` carries only the āya's own text, on every endpoint, in one place.
- The Basmala shown exactly once per sūra, in its correct role (heading for 112 sūras,
  āya `﴿١﴾` for al-Fātiḥa, absent for at-Tawba).
- A reading position that survives leaving the app: the navigation entry resumes the sūra
  last read, at the āya the reader had reached.
- Word-level analyses (QLisan fiche, mīzān surface) keep byte-identical behaviour.

**Non-Goals:**

- Translations, tafsīr, audio recitation, or per-āya cards on the reading page.
- Syncing the reading position across devices or browsers — it is per-browser, like the
  saved conversations.
- Re-deriving `chakl_char_start`/`chakl_char_end` against a stripped corpus.
- Uthmānī rasm rendering. The reading page keeps the imlāʾī orthography of
  `quran_chakl.csv`; the screenshot's muṣḥaf calligraphy is not the target.
- Changing `/qlisan`, which still displays its verse with the Basmala prefix because its
  highlighting is offset-addressed (documented, not fixed here).

## Decisions

### D1 — The strip is a display helper, not a change to `chakl_by_ref()`

A new pure function in `indexing/corpus.py`:

```
basmala_text() -> str                       # the vocalized Basmala, read from row (1,1)
strip_leading_basmala(surah, ayah, text) -> str
```

`chakl_by_ref()` keeps returning raw CSV rows. Offset-addressed consumers
(`qlisan_data.word_index`, `mizan._vocalized_surface`) read the loader and are unaffected;
display consumers call the helper.

*Alternative considered:* strip inside `chakl_by_ref()` and shift the stored offsets by the
prefix length during the QLisan index build. Rejected — it makes a display concern a
pipeline concern, requires rebuilding `word_index`, and any offset produced by an older
build would silently point into the wrong word.

### D2 — Detection compares diacritic-stripped forms, against a corpus-sourced Basmala

The reference string is `bare(chakl_by_ref()[(1, 1)]["text"])`, never a literal typed into
source. The candidate is `bare(text)`; a match is `startswith`. Verified: 113 of 114 first
āyāt match, the exception being at-Tawba — exactly the expected set.

To map the bare prefix length back into the raw string, walk the raw text counting
non-diacritic characters until the bare length is consumed, then absorb the trailing
combining marks on the last consumed letter and the following whitespace.

Verified end to end: `2:1` → `الم`, `1:1` unchanged, `9:1` unchanged, and no first āya
retains a Basmala prefix after the strip. Residual word-count differences against
`verses_final.json` are waqf marks (`ۖ ۚ ۗ`), which the bare form drops and the undiacritized
corpus keeps as separate tokens — not strip failures.

### D3 — The diacritic class is written with `\u` escapes only

Per fact 3 above, and per the existing project note that a two-range class silently misses
U+064C–U+0659. The class is specified once, with escapes and an inline comment naming each
range, and reused rather than re-typed.

*Alternative considered:* `unicodedata.combining(c) != 0`. Viable and self-documenting, but
it does not cover the waqf marks (U+06D6–U+06DC) and the tatweel, and it is markedly slower
over 6236 rows. The escaped class is kept, with the property test as the guard.

### D4 — The guard is `ayah == 1 and surah != 1`, checked before matching

The Basmala occurs *inside* `27:30` (`إِنَّهُ مِنْ سُلَيْمَانَ وَإِنَّهُ بِسْمِ اللَّهِ…`) — not as a
prefix, so the prefix test alone already spares it, but the position guard makes that
independent of the matcher. Verified: `27:30` is returned unchanged.

### D5 — The backend decides whether a sūra gets a Basmala heading

`SurahResponse` gains one field: `basmala: str` — the vocalized Basmala for the 112 sūras
that open with it, and `""` for al-Fātiḥa (where it is āya 1) and at-Tawba (which has
none). The frontend renders the field if non-empty and holds no rule of its own.

*Alternative considered:* let the frontend special-case `number !== 1 && number !== 9`.
Rejected — it puts a scripture rule in TypeScript, duplicated in any future consumer, and
hard-codes the exceptional sūra numbers in a layer that has no access to the corpus.

### D6 — `/surah` is a resume entry point; one component, one URL per sūra

The navigation entry points at `/surah`, which holds no rendering of its own: it reads the
stored reading position and `router.replace`s to `/surah/{n}#ayah-{a}`, falling back to
`/surah/1` when nothing is stored. `/surah/[number]` is the single rendering path — picker
at the top, sūra below. Choosing in the picker navigates to `/surah/{n}`, so every sūra on
screen has a shareable URL, and the existing deep links from `VerseCard`,
`VerseContextCard` and `/verse/{s}/{a}` land on the same page with the picker already
synchronized. `isActive` already uses `pathname.startsWith(href)`, so the entry highlights
on both.

`/surah` is therefore a **client** component. A server-side `redirect()` cannot read the
stored position, and `replace` (not `push`) keeps the resume hop out of the back history,
so Back from a sūra returns to the page the reader came from rather than bouncing through
`/surah`.

Falling back to a concrete sūra rather than an empty prompt follows the pickers already in
the app (`FassilaAnalysisTab` opens on sūra 12, `/qlisan` on 1:1).

*Alternative considered:* a `?s=` query parameter on a single `/surah` page. Rejected — it
would either break the deep links already emitted across the app or require keeping the
parametrized route as a second renderer, which is the divergence this decision exists to
prevent.

### D7 — The stepper stays, and it is the picker's complement

The previous/next sūra links at the foot of the page are kept. They serve sequential
reading — finishing al-Baqara and continuing into Āl ʿImrān without returning to the top of
the page — which the picker does not: the picker serves *jumping*, the stepper *continuing*.
They already satisfy the RTL icon rules, so they are kept as they stand.

### D8 — The reading position is an āya, persisted in `localStorage`

A dedicated `lib/readingPosition.ts` stores `{surah, ayah}` under one key, on the pattern
`lib/conversations.ts` already establishes and that its Vitest suite already covers: reads
guarded for SSR (`window` absent) and wrapped against a corrupt or unparsable value, writes
wrapped against a quota or private-mode failure. A value outside `1…114`, or an āya beyond
the sūra's length, is discarded in favour of the fallback rather than trusted.

**The unit is the āya, not a scroll offset.** The reading block reflows with viewport width
and font size, so a stored pixel offset lands somewhere arbitrary after either changes,
while an āya survives both and is what a reader actually resumes at. The position is
therefore also expressible in the URL — `#ayah-200` — which makes the resume hop legible
and the resulting address shareable.

The current āya is the first āya marker visible in the viewport, tracked with an
`IntersectionObserver` over the markers. It is persisted on a debounce and on `pagehide`,
not on every scroll event: `localStorage` writes are synchronous and would otherwise land
in the scroll path.

*Alternative considered:* `lib/pageCache.ts` (`useCachedState`). Rejected — its cache is a
module-level `Map` scoped to the tab's JS session and dropped by a hard reload, so the
position would not survive F5. Its docstring's argument against `localStorage` is aimed at
large transient state ("serialising a 180-verse lookup on every keystroke"); a
`{surah, ayah}` pair is the opposite case — tiny, and durable by purpose.

*Alternative considered:* restoring the raw `scrollTop`. Rejected for the reflow reason
above, and because it cannot be expressed in a URL.

### D9 — Navigation grows to six entries and is reordered

Order, reading right-to-left: «محاورة القرآن» · «سور القرآن» · «دراسة الآية» ·
«تحليل اللسان» · «التحليل النحوي» · «الفواصل». The new entry needs an icon distinct from
`BookOpen`, which is already the brand mark *and* the «التحليل النحوي» icon.

## Risks / Trade-offs

- **A future contributor strips inside `chakl_by_ref()`** and silently breaks QLisan
  highlighting → the loader's docstring states the offset contract, and a test asserts
  `chakl_by_ref()[(2,1)]["text"]` still begins with the Basmala.
- **The escaped diacritic class is re-typed as a literal** in a later edit and silently
  eats letters → a property test asserts `bare()` preserves every Arabic letter of a
  fixture āya, so the failure is loud.
- **The strip runs per call** on hot paths (`/chat` returns ~5 verses, `/surah` up to 286)
  → it is O(prefix) and only ever executes its loop for āya 1; the ~285 other āyāt of a
  sūra fail the `ayah == 1` guard before any regex runs.
- **`/qlisan` keeps showing the prefixed verse**, so the app is briefly inconsistent
  between the reading surfaces and that one analytical page → accepted and documented;
  `/qlisan` is absent from the navigation and reachable by direct URL only.
- **The resume hop is visible as a flash** of al-Fātiḥa, or of the top of the sūra, before
  the position is applied → `/surah` renders no sūra at all, only a neutral loading state,
  and the scroll is applied in a layout effect once the verses are in the DOM, so the
  reader sees one paint at the right place rather than two.
- **`localStorage` is unavailable or full** (private mode, blocked site data, quota) →
  every read and write is wrapped; a failed read falls back to al-Fātiḥa and a failed write
  is dropped silently. The page never depends on the position existing.
- **A stored position outgrows its sūra** (a corrupt value, or hand-edited storage) → the
  sūra is validated against `1…114` and the āya against the loaded sūra's length before
  either is used; an out-of-range value falls back rather than scrolling nowhere.
- **`IntersectionObserver` firing during the restore** overwrites the stored position with
  the top of the sūra before the scroll lands → the observer is attached only after the
  restore scroll has been applied.

## Migration Plan

No data migration: `quran_chakl.csv`, `verses_final.json` and the QLisan word index are all
untouched. No index rebuild, no re-ingestion. The change is deployable by restarting the
backend and rebuilding the frontend, and revertible by reverting the commit.

The reading position is new state with no prior version, so there is nothing to migrate and
no format to read back; an absent key is the normal first-run case and already falls back
to al-Fātiḥa.

## Open Questions

- Should the āya number `﴿٢﴾` link to `/verse/{s}/{a}`? Deferred — the user kept only the
  existing header when asked what to preserve around the reading area. The āya markers now
  carry a DOM id for the resume scroll, so making them links later is a small step.
