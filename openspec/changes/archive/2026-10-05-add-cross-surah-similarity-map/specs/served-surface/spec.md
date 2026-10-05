## MODIFIED Requirements

### Requirement: Every mounted route has a real consumer

A route SHALL be mounted only if something in the shipped product calls it: a frontend page, another
backend component, or a documented operational need. A route reachable only from a test, or only from
a client function no page imports, SHALL NOT be mounted.

The surface after this change is exactly what the nine frontend pages call:

| Route | Called by |
|---|---|
| `POST /chat/stream` | `ChatInterface` |
| `POST /feedback` | `ChatInterface` |
| `GET /health` | `HealthBanner` |
| `GET /search` | Verse Study → «آيات مشابهة» |
| `POST /verse-lookup` | Verse Study → «الكلمة في الآيات» |
| `GET /surah/{number}/similar` | Verse Study → «الآيات المتشابهات», mode «داخل سورة» |
| `GET /verse/{surah}/{ayah}/similar` | Verse Study → «الآيات المتشابهات», mode «داخل سورة», section «في سائر القرآن» |
| `GET /quran-similarity/matrix`, `GET /quran-similarity/pairs/{a}/{b}` | Verse Study → «الآيات المتشابهات», mode «الآيات المتشابهات في سائر القرآن» |
| `GET /verse/{surah}/{ayah}` | Verse Study, `/verse/[surah]/[ayah]` |
| `GET /surah/{number}`, `GET /surahs` | `SurahReader`, Fassila, QLisan, Verse Study |
| `GET /fassila/{surah}`, `GET /fassila/overview` | Fassila tabs |
| `POST /lisan/analyze` | «تحليل لساني عربي» page — core-first reading |
| `GET /lisan/reading/{root}`, `PUT /lisan/reading/{root}` | «تحليل لساني عربي» page — signed personal reading |
| `POST /qlisan/word`, `POST /qlisan/form`, `GET /qlisan/verse/{s}/{a}` | QLisan page, «تحليل لساني عربي» page |
| `GET /roots`, `GET /roots/letter/{letter}` | «فهرس الجذور» page |

`GET /health` is mounted on operational grounds: the frontend banner reads it, and it is the
documented readiness probe.

`POST /lisan/concept` (the physics-first engine, a closed experiment at `k / 40 = 0`) is
**quarantined**. Its handler lives in `api/routers/lisan_concept.py`, which `api/main.py` imports but
does not mount, and `/lexical` no longer renders its panel.

`POST /tahlil/word` and `POST /tahlil/review` are **quarantined** on the same terms: «التحليل النحوي»
left the navigation and its `/tahlil` page was deleted, so `api/main.py` imports `tahlil_router` but
does not mount it. The engine under `linguistics/tahlil/` and its tests stay; `linguistics/madar/
maqayis_store.py` is no longer on a served request path through it.

#### Scenario: The mounted surface matches the consumed surface

- **WHEN** the mounted routes are compared against the endpoints the frontend calls
- **THEN** the two sets SHALL be equal, apart from `GET /health`
- **AND** a test SHALL assert this, so that a route cannot be mounted without a consumer

#### Scenario: A page's behaviour is unchanged

- **WHEN** each of the eight pages that existed before the change and remain is exercised after it
- **THEN** every request it makes SHALL succeed
- **AND** its rendered output SHALL be identical to before, apart from the navigation and the
  renamed page headings

#### Scenario: The concept route stays quarantined

- **WHEN** the mounted routes are listed
- **THEN** `POST /lisan/concept`, `POST /tahlil/word` and `POST /tahlil/review` SHALL NOT be among them
- **AND** `api/routers/lisan_concept.py` SHALL still import and expose the route, so that rebranching
  is one `include_router` line

#### Scenario: The intra-surah similarity route has its consumer

- **WHEN** the mounted routes are compared against the endpoints the frontend calls
- **THEN** `GET /surah/{number}/similar` SHALL be in both sets
- **AND** removing the «داخل سورة» mode without unmounting the route SHALL fail that comparison

#### Scenario: The cross-surah similarity route has its consumer

- **WHEN** the mounted routes are compared against the endpoints the frontend calls
- **THEN** `GET /verse/{surah}/{ayah}/similar` SHALL be in both sets
- **AND** removing the «في سائر القرآن» section without unmounting the route SHALL fail that comparison

#### Scenario: The matrix routes have their consumer

- **WHEN** the mounted routes are compared against the endpoints the frontend calls
- **THEN** `GET /quran-similarity/matrix` and `GET /quran-similarity/pairs/{a}/{b}` SHALL be in both sets
