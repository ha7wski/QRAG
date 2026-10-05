## MODIFIED Requirements

### Requirement: A model-free route serves one verse's cross-surah neighbours

The backend SHALL serve `GET /verse/{surah}/{ayah}/similar`, reading only `quran_close_verses.json`
(capability `close-verses`). It SHALL load no model and query neither Qdrant nor the reranker. The
response SHALL carry the anchor verse, `unscored`, and EVERY pair of the unified relation holding
that verse — not capped at K — ordered by combined score descending then by reference, each
neighbour with its verse (carrying `surah_name_ar`), the score, the shared roots and, when the pair
has a common part, its matched word count (`words`) and its half-open character span in the
NEIGHBOUR's `text_ar_tashkil` (`span`), both null otherwise. Every verse SHALL go through
`verse_from_record`. An unscored anchor SHALL return an empty list with `unscored: true`; a scored
anchor with no close verse an empty list with `unscored: false`; neither is an error.

#### Scenario: Neighbours of one verse

- **WHEN** the client requests `GET /verse/3/116/similar`
- **THEN** the response SHALL list verses of other surahs only, in score order, each with its surah
  name and shared roots, including 58:17

#### Scenario: A passage-only neighbour is listed

- **WHEN** the client requests `GET /verse/28/20/similar`
- **THEN** the response SHALL list 36:20 with `words` and a `span` whose text starts with «وَجَاءَ»

#### Scenario: The list agrees with the map

- **WHEN** a verse's neighbours are compared with the map's cells
- **THEN** every pair of a cell holding that verse SHALL be in its list, and no other

#### Scenario: Invalid references

- **WHEN** the surah is outside 1–114, or the ayah exceeds the surah's length
- **THEN** the route SHALL answer 422 or 404 respectively, with no partial body

#### Scenario: The intra-surah view survives a missing cross-surah dataset

- **WHEN** `quran_close_verses.json` is absent
- **THEN** `GET /verse/{surah}/{ayah}/similar` SHALL answer 503 naming
  `python scripts/build_quran_close_verses.py`
- **AND** `GET /surah/{number}/similar` SHALL answer exactly as before

#### Scenario: No model is loaded by the route

- **WHEN** the backend starts and only `GET /verse/{s}/{a}/similar` is called
- **THEN** `GET /health` SHALL report no embedder and no search reranker resident

### Requirement: The anchor panel lists the verse's close verses in the rest of the Quran

In the Verse Study «المتشابهات داخل السورة» mode, selecting a verse of a group SHALL show, **below**
the picked verse (its same-surah close verses are not listed), a section headed
«الآيات المتشابهات في سائر القرآن» listing its cross-surah close verses in the order served. Each card
SHALL show the verse vocalized, its surah's Arabic name and its ayah number, and the shared content
roots as Arabic root chips when there are any. When the pair has a common part, it SHALL be
highlighted in the listed verse and the card SHALL state «N كلمات مشتركة»; the picked verse itself
SHALL NOT be highlighted. No numeric score SHALL be shown. Activating a card SHALL open the verse in
«الآية في سياقها».

The verse card (from the intra-surah request) and the cross-surah section SHALL be requested
independently: the card SHALL render without waiting for the cross-surah answer, and a failure of one
SHALL be shown in its own place without hiding the other. A scored verse with no cross-surah close verse SHALL say so in a sentence rather than render an
empty list. The fetched answers SHALL be cached under `verse-study.similar.surah.*`, so returning to a
verse already picked issues no request.

#### Scenario: Pick a verse, see its close verses elsewhere

- **WHEN** the reader picks surah 3 and then 3:116 inside a group
- **THEN** the verse 3:116 is shown, with no list of its close verses in surah 3
- **AND** below it, «الآيات المتشابهات في سائر القرآن» lists 58:17 with its surah name «المجادلة»

#### Scenario: The common part is coloured in the listed verse

- **WHEN** a listed close verse carries a span
- **THEN** that span of its text SHALL be highlighted and «N كلمات مشتركة» SHALL be shown

#### Scenario: The cross-surah request fails

- **WHEN** `GET /verse/{s}/{a}/similar` answers 503
- **THEN** the picked verse SHALL still be shown
- **AND** the cross-surah section SHALL show the failure note in its place

#### Scenario: No cross-surah close verse

- **WHEN** a scored verse has an empty cross-surah neighbour list
- **THEN** the section SHALL state that no verse elsewhere in the Quran is close to it or shares a
  passage with it
