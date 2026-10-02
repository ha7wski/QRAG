## ADDED Requirements

### Requirement: Refusal reasons are written in Arabic

Every `refusal_reason` produced by `compose()` or `assemble()` SHALL be Arabic text containing no
Latin letter, because the pages print it as is. `refusal_code` SHALL stay an English identifier and
SHALL NOT be displayed.

#### Scenario: A quadriliteral root is refused in Arabic

- **WHEN** زلزل is assembled
- **THEN** `refusal_code` is `not-triliteral`
- **AND** `refusal_reason` names the root and contains no character in `[A-Za-z]`

#### Scenario: Every refusal over the corpus is Arabic

- **WHEN** every root of `morphology.json` is assembled
- **THEN** no refusal reason contains a character in `[A-Za-z]`
