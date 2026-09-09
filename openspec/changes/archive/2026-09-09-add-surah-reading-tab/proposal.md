## Why

The application can already *analyse* the Quran from six angles but it cannot simply
**read** it: reaching a sūra requires clicking a verse reference from some other page,
because `/surah/{n}` has no entry point of its own and is absent from the navigation.

Worse, the page it reaches is wrong. `data/raw/quran_chakl.csv` — the only source of
vocalized text — **prepends the Basmala to āya 1 of 113 sūras**, so `2:1` is stored as
`بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ الم`, not `الم`. Every screen that renders
`text_ar_tashkil` (chat sources, `VerseCard`, `/verse/{s}/{a}`, «دراسة الآية», `/surah/{n}`)
therefore shows the Basmala welded onto the first āya, mis-attributing to the āya text that
is not part of it. This is a correctness defect in the corpus rendering, not a styling
preference, and it is already visible today.

## What Changes

- **New «سور القرآن» tab** at `/surah`: a sūra picker over the 114 sūras, and below it the
  chosen sūra rendered as one continuous vocalized block — the existing `/surah/{n}`
  presentation, unchanged in substance.
- **`/surah/{n}` and `/surah` become one page.** The parametrized route renders the same
  component with the sūra pre-selected, so the deep links already emitted by `VerseCard`,
  `VerseContextCard` and `/verse/{s}/{a}` keep working and keep the tab highlighted.
- **The prepended Basmala is removed from `text_ar_tashkil` at the API's display layer**,
  so every consumer is corrected at once. Al-Fātiḥa is exempt: there the Basmala genuinely
  *is* āya 1 and stays numbered `﴿١﴾`.
- **The Basmala is rendered once, as a heading**, centred above the sūra body — for the 112
  sūras that carry it as a non-āya opening. At-Tawba (9) shows no Basmala at all, and
  al-Fātiḥa shows no heading, since its Basmala is already in the body as āya 1.
- **Navigation is reordered and grows to six entries**: «محاورة القرآن» · «سور القرآن» ·
  «دراسة الآية» · «تحليل اللسان» · «التحليل النحوي» · «الفواصل».
- **The reading position is remembered.** The navigation entry reopens the sūra last read,
  scrolled back to the āya the reader had reached, persisted across reloads and browser
  restarts. The existing previous/next sūra pagination row is kept, alongside the picker.
- **Not changed:** `indexing.corpus.chakl_by_ref()` keeps returning the raw CSV text. Its
  rows are addressed by character offset (`chakl_char_start`/`chakl_char_end`, computed
  against the Basmala-inclusive string) by `analysis/qlisan_data.word_index()`, and through
  it by the QLisan word fiche and `analysis/mizan._vocalized_surface`. Stripping inside the
  shared loader would shift every one of those offsets by the Basmala's length.

## Capabilities

### New Capabilities

- `surah-reading`: the «سور القرآن» tab — sūra selection, whole-sūra vocalized reading,
  Basmala heading placement, and the `/surah` ⇄ `/surah/{n}` deep-link contract.
- `vocalized-verse-text`: the contract for `text_ar_tashkil` across the API — no corpus-
  prepended Basmala on any āya that does not contain it, applied uniformly to every
  endpoint that emits vocalized verse text, and explicitly **not** applied to the
  offset-addressed rows the word-level analyses read.

### Modified Capabilities

- `rtl-app-shell`: the "Navigation item set and order" scenario fixes the navigation at
  five entries in a given order; it becomes six, reordered.
- `arabic-ui-locale`: the route ↔ Arabic-name table gains `/surah` → «سور القرآن», and its
  "In navigation" column changes for that row from absent to `yes`.

## Impact

**Backend**

- `indexing/corpus.py` — new display helper (Basmala detection on diacritic-stripped text
  + the canonical vocalized Basmala read from `(1,1)`, never hand-typed). The cached
  `chakl_by_ref()` itself is untouched.
- `api/models/verse.py` — `verse_from_record` applies the helper when auto-filling
  `text_ar_tashkil`. This is the choke point for `/chat`, `/search`, `/verse/{s}/{a}`,
  `/surah/{n}`.
- `retrieval/verse_lookup.py` — `_verse_row` builds its own shape (`text` +
  `match_indices`) and bypasses `verse_from_record`; it needs the same strip, applied
  *before* `_match_indices` so highlight offsets stay consistent with the text emitted.
- `api/routers/verse.py` — `SurahResponse` gains the Basmala-heading flag so the frontend
  does not re-derive scripture rules in TypeScript.

**Frontend**

- New `/surah/page.tsx` (resume entry point) + a shared surah-view component consumed by
  both routes; `/surah/[number]/page.tsx` becomes a thin wrapper.
- New `lib/readingPosition.ts` — the persisted `{surah, ayah}` pair, on the pattern already
  established and tested by `lib/conversations.ts` (SSR guard, corrupt-value tolerance).
- `components/Navbar.tsx` — sixth entry, new order, new icon.
- `lib/strings.ts` — `S.nav.surahs` and the page's own strings.
- `lib/api.ts` / `lib/types.ts` — the new response field.

**Not affected:** retrieval quality, indexing, the QAC pipeline, `/qlisan`, `/tahlil`,
`/fassila` (which sources its text from the QAC treebank and already sidesteps the Basmala).

## Assumptions

- The picker is a plain `<select>`, matching the sūra pickers already in
  `FassilaAnalysisTab` and `/qlisan`, rather than a new searchable combobox.
- The remembered position is an **āya**, not a pixel offset: the reading block reflows with
  viewport width and font size, so a stored scroll offset would land somewhere arbitrary
  after either changes, while an āya is stable and is the unit a reader actually resumes at.
- Reaching a sūra by **deep link** from elsewhere in the app opens it at the top and updates
  the remembered sūra. Only the navigation entry resumes a position; a shared or cited link
  must land where it points.
