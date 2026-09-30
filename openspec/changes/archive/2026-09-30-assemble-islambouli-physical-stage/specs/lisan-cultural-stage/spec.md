## ADDED Requirements

### Requirement: The cultural stage is never generated or inferred
No code path SHALL produce cultural-stage text other than by reading one of two sources:
- a sourced Islambouli citation;
- a signed personal reading.

#### Scenario: A root with neither source
- **WHEN** a root has no cultural citation and no personal reading
- **THEN** `cultural_stage` carries no text
- **AND** the page renders no cultural section: no heading, no placeholder and no «قيد الإعداد»

### Requirement: Islambouli citations are sourced and frozen
`data/references/islambouli_citations.json` SHALL record, per published statement:
- `root`;
- `stage` (`physical` | `cultural`);
- `label_as_printed`, `text_as_printed` and `text`;
- a source naming the programme, a witness image under `data/source/` with its sha256, and its origin.

The file SHALL be frozen by a lock and SHALL be registered in `quran_data/manifest.py`.

#### Scenario: ضرب's cultural stage is cited
- **WHEN** ضرب is analysed
- **THEN** the cultural section shows «إيقاع شيء على شيء يترك فيه أثراً»
- **AND** the citation is attributed to Islambouli with its source

#### Scenario: A witness image that changed
- **WHEN** a witness image's sha256 differs from the recorded one
- **THEN** loading the citations raises

### Requirement: Personal readings are signed and never attributed to Islambouli
A personal reading SHALL be stored in the runtime database with:
- a non-empty author;
- an optional cultural text;
- optional alternative choices.

It SHALL be displayed labelled with its author as a personal reading.
It SHALL never be fed to any measurement.

#### Scenario: Unsigned reading rejected
- **WHEN** `PUT /lisan/reading/{root}` is called with an empty author
- **THEN** the request is rejected with 422

#### Scenario: Both sources present
- **WHEN** a root has both a citation and a personal reading
- **THEN** both are shown, each with its own attribution
