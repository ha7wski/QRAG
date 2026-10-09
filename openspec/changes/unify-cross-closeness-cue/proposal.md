## Why

The cross-surah «close verse» relation stores pairs its own written definition rejects. The blind
definition says «a few shared words scattered through two otherwise different verses is not close»,
yet 2:10 / 39:26 is stored: `syn` 0.75, `lex` 0.097, three shared lemmas (الله، عذاب، كان), and it
passes because the cross-encoder (`ce` 0.77) carries the semantic gate through the `floor` 0.25. This
is not isolated: 314 of the 1 088 stored cross-surah similarity pairs have `lex < 0.2` and `syn < 0.9`.
Nothing enforces shared material on a long verse (the ≥ 2-lemma rule of `short-verse-material` stops at
5 words), and the blind sample that measured the relation was drawn with `lex ≥ 0.3`, so this class was
never measured.

The reading page compounds the confusion with two orange cues for one relation: an orange ring for a
whole-verse pair, orange words for a passage-only pair. A whole-verse pair's common part is never shown
in the text, so 2:2 carries a ring while «الْكِتَابُ لَا رَيْبَ» and «هُدًى لِّلْمُتَّقِينَ», the words that
make it close to 32:2 and 3:138, stay plain.

## What Changes

- **Cross-surah similarity — a shared-material gate for every length.** A cross-surah similarity pair
  SHALL be stored only when its shared content LEMMAS cover a minimum share `κ` of the shorter verse's
  content words (root-only matches do not count), on top of the existing gates; and its syntax SHALL pass
  a cross-surah threshold `σ_x ≥ σ` («the same syntax»). The intra-surah relation (green) is unchanged.
- **The thresholds are chosen by a rule written before any label is seen**, on a calibration sample
  drawn from the currently stored pairs (stratified by coverage and `syn`, `lex < 0.3` included), and
  MEASURED on a disjoint holdout sample, both labelled blind under the written definition. A miss is
  recorded, never tuned.
- **Shared passages are unchanged and still suffice**: a pair holding a passage stays a close pair
  whatever the new gate says (the union of `close-verses` is kept). A pair that loses its similarity
  but holds a passage becomes passage-only.
- **Reading page — ONE orange cue.** An āya with at least one close verse in another sūra (any pair,
  whole-verse or passage) gets an orange `﴿n﴾` marker AND every one of its common parts (all pairs)
  coloured orange in its text. The legend has two entries: green «آية قريبة داخل السورة», orange «آية
  قريبة في سائر القرآن». The «جزء مشترك في سائر القرآن» entry goes.
- **BREAKING (API, frontend moves in the same change):** `GET /surah/{number}/annotations` replaces
  `whole` + `passage` with one `cross` list, score descending.
- Rebuild `quran_similarity.json` → `quran_close_verses.json`; the surah × surah map follows
  automatically (fewer pairs).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quran-wide-similarity`: adds the cross-only shared-material gate (`κ`) and the cross-only syntax
  threshold (`σ_x`), their calibration and holdout measurement, and their header fields.
- `surah-reading-annotations`: one orange cue (marker + all common parts) instead of a relation split;
  two-entry legend; route returns one `cross` list.

## Impact

- `scripts/closeness_core.py` (pure `material_ok`), `scripts/build_quran_similarity.py` (new stage,
  header), `scripts/build_quran_close_verses.py` (rebuild only), a new draw script and two labelled
  files under `tests/eval/` (local-only), `scripts/eval_quran_similarity.py` (new stage reported).
- `api/routers/surah_annotations.py`, `api/models/surah_annotations.py`.
- `frontend/src/lib/annotations.ts`, `components/SurahReader.tsx`, `components/CloseVersesBubble.tsx`,
  `lib/api.ts`, `lib/strings.ts`, and their tests.
- Data: `quran_similarity.json` and `quran_close_verses.json` rebuilt (backend stopped). The intra
  dataset `surah_similarity.json` is untouched.
- Docs: `CLAUDE.md` figures (pair counts, the two-cue description).
