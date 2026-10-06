## ADDED Requirements

### Requirement: The surah annotation route has its consumer

`GET /surah/{number}/annotations` SHALL be mounted, and its consumer SHALL be the reading page
(`SurahReader`, «سور القرآن»), which calls it only while the closeness annotations are on.

#### Scenario: The annotation route is in both sets

- **WHEN** the mounted routes are compared against the endpoints the frontend calls
- **THEN** `GET /surah/{number}/annotations` SHALL be in both sets
- **AND** removing the annotations from the reading page without unmounting the route SHALL fail that
  comparison

#### Scenario: The quarantined per-verse route stays quarantined

- **WHEN** the mounted routes are listed after this change
- **THEN** `GET /verse/{surah}/{ayah}/similar` SHALL still NOT be among them — the bubble reads the
  per-sūra annotation payload, not the per-verse route
