## ADDED Requirements

### Requirement: The personal-reading routes are served and called by /lexical
`GET /lisan/reading/{root}` and `PUT /lisan/reading/{root}` SHALL be mounted.
The «تحليل اللسان» page SHALL call both, and `test_served_surface.py` SHALL list them among the served routes.

#### Scenario: Both routes have a live caller
- **WHEN** `test_served_surface.py` resolves the callers of the two personal-reading routes
- **THEN** each has a caller in `frontend/src/lib/api.ts` used by the `/lexical` page
