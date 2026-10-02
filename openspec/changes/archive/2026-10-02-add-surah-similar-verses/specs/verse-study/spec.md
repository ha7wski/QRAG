## ADDED Requirements

### Requirement: The similar tab has two modes

The `similar` tab SHALL offer two modes behind a two-way switch at the top of the tab, in this
order: «المتشابهات داخل السورة» (labelled «داخل سورة» elsewhere in this change) — the intra-surah
similarity view defined by the `surah-internal-similarity` capability — first, then «المتشابهات من
عبارة» (labelled «بعبارة» elsewhere in this change) — the
existing phrase search over all 6 236 verses (`GET /search`), unchanged. The tab SHALL open on
«بعبارة».

Each mode SHALL keep its own state (query and results for «بعبارة»; selected surah, selected ayah
and results for «داخل سورة») while the other is shown, and across a switch to another tab and back,
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
