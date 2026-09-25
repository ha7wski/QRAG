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
| `GET /verse/{surah}/{ayah}` | Verse Study, `/verse/[surah]/[ayah]` |
| `GET /surah/{number}`, `GET /surahs` | `SurahReader`, Fassila, QLisan, Tahlīl, Verse Study |
| `GET /fassila/{surah}`, `GET /fassila/overview` | Fassila tabs |
| `POST /lisan/analyze` | «تحليل اللسان» page — core-first reading |
| `POST /lisan/concept` | «تحليل اللسان» page — physics-first مفهوم |
| `POST /qlisan/word`, `POST /qlisan/form`, `GET /qlisan/verse/{s}/{a}` | QLisan page, Tahlīl page, «تحليل اللسان» page |
| `POST /tahlil/word`, `POST /tahlil/review` | Tahlīl page |

`GET /health` is mounted on operational grounds — the frontend banner reads it, and it is the
documented readiness probe.

`POST /lisan/analyze` and `POST /lisan/concept` are two engines answering the same question by
opposite routes, and both are called by the same page for the duration of the comparison. Two routes
on one page is deliberate here and is **not** a precedent for mounting a route whose consumer is a
future intention: the comparison panel ships in the same change as the route.

#### Scenario: The mounted surface matches the consumed surface

- **WHEN** the mounted routes are compared against the endpoints the frontend calls
- **THEN** the two sets SHALL be equal, apart from `GET /health`
- **AND** a test SHALL assert this so a route cannot be mounted without a consumer

#### Scenario: A page's behaviour is unchanged

- **WHEN** each of the nine pages is exercised after the change
- **THEN** every request it makes SHALL succeed
- **AND** its rendered output SHALL be identical to before, apart from `/lexical`'s added concept
  and comparison panels

#### Scenario: Both lisan routes have a live caller

- **WHEN** `test_served_surface.py` resolves the callers of `POST /lisan/analyze` and
  `POST /lisan/concept`
- **THEN** each SHALL be called by the «تحليل اللسان» page
- **AND** removing either panel from the frontend SHALL fail the test until its route is unmounted
