## MODIFIED Requirements

### Requirement: The similar tab has two modes

The `similar` tab SHALL offer three modes behind a switch at the top of the tab, in this order:
«المتشابهات داخل السورة» (labelled «داخل سورة» elsewhere in this change) — the intra-surah similarity
view defined by the `surah-internal-similarity` capability — first; then «الآيات المتشابهات في سائر
القرآن» — the surah × surah matrix defined by the `cross-surah-similarity-map` capability; then
«المتشابهات من عبارة» (labelled «بعبارة» elsewhere in this change) — the existing phrase search over
all 6 236 verses (`GET /search`), unchanged. The tab SHALL open on «بعبارة».

Each mode SHALL keep its own state (query and results for «بعبارة»; selected surah, selected ayah
and results for «داخل سورة»; the matrix, the selected cell and its pairs for the matrix mode) while
another is shown, and across a switch to another tab and back,
using the same cached-state mechanism the tab already uses.

The switch labels SHALL be Arabic; no English mode name SHALL be rendered.

#### Scenario: Switching modes keeps both states

- **WHEN** the reader runs a phrase search, switches to «داخل سورة», picks surah 55, and switches back
- **THEN** the phrase results are still shown
- **AND** switching to «داخل سورة» again shows surah 55's groups without a new request

#### Scenario: The phrase search is unchanged

- **WHEN** the reader uses «بعبارة»
- **THEN** it SHALL issue the same `GET /search` request and render the same results as before this
  change

#### Scenario: Opening a verse from the intra-surah mode

- **WHEN** the reader activates a verse card in the «داخل سورة» mode
- **THEN** the page SHALL switch to the «الآية في سياقها» tab and load that verse in context, as the
  phrase-search results already do

#### Scenario: The matrix mode keeps its cell

- **WHEN** the reader selects a cell in the matrix mode, switches to «بعبارة», and back
- **THEN** the same cell SHALL be outlined with its pairs listed, without a new request
