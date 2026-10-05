## ADDED Requirements

### Requirement: The shared-passage routes are removed

`GET /quran-passages/matrix` and `GET /quran-passages/pairs/{a}/{b}` SHALL be unmounted and their
router, models, reader and client functions deleted: the page that called them now reads the
unified relation through `GET /quran-similarity/matrix` and `GET /quran-similarity/pairs/{a}/{b}`.
The test that guards the served surface SHALL name both, so that mounting them again is a decision.

#### Scenario: The passage routes answer 404

- **WHEN** `GET /quran-passages/matrix` or `GET /quran-passages/pairs/28/36` is requested
- **THEN** the backend SHALL answer 404

#### Scenario: No client function is left behind

- **WHEN** the frontend client is searched for `quran-passages`
- **THEN** nothing SHALL be found
