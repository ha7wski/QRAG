## REMOVED Requirements

### Requirement: Model-free routes serve the passage map and a cell's passages

**Reason**: The shared passage is no longer a view of its own. Every passage pair is a pair of the
unified relation (`close-verses`), served with its span by the similarity map's routes.

**Migration**: `GET /quran-passages/matrix` → `GET /quran-similarity/matrix`;
`GET /quran-passages/pairs/{a}/{b}` → `GET /quran-similarity/pairs/{a}/{b}`, whose pairs carry
`words`, `span_u` and `span_v`. Both removed routes answer 404.

### Requirement: The map switches between the two relations

**Reason**: The map draws one relation, the union of the two, so there is nothing to switch.

**Migration**: None for the reader: every pair either view listed is listed by the single map, the
shared passage highlighted in both verses.
