## MODIFIED Requirements

### Requirement: Verse Study tab set

The Verse Study page SHALL present exactly three tabs. Each tab has a stable
**identity** and an **Arabic label**:

| Identity | Arabic label |
|---|---|
| `word` (formerly "Word in Verses") | «الكلمة في الآيات» |
| `similar` (formerly "Similar Verses") | «الآيات القريبة في المعنى» |
| `context` (formerly "Find Verse context") | «الآية في سياقها» |

The tabs SHALL be presented in the order `word`, `similar`, `context`. Because the page
is right-to-left, that order reads from the **right**: `word` is the rightmost tab and
`context` the leftmost. The tab strip SHALL open on `word` by default.

Switching tabs SHALL NOT discard the state (query, results) of the other tabs — each tab
keeps its own results while hidden.

The `similar` label SHALL NOT be «النظائر». That term names the discipline
«الوجوه والنظائر» — a *word's* senses across verses — and this application already uses
«نظيرة» in exactly that sense on other pages, so the label would collide with a live term
while misdescribing a tab that performs a semantic phrase search. «الآيات المتشابهة» is
likewise unavailable: it names المتشابه اللفظي, verbal similarity, which this tab does not
do.

Elsewhere in this specification, the English names "Word in Verses", "Similar Verses" and
"Find Verse context" denote these tab **identities**, not text rendered on screen; no
English tab label is displayed. The identities as implemented are the short forms `word`,
`similar` and `context`; the English phrases are the names the other requirements of this
capability use to refer to them.

#### Scenario: Tab order and persistence

- **WHEN** a user opens the Verse Study page
- **THEN** three tabs are shown, labelled «الكلمة في الآيات», «الآيات القريبة في المعنى»,
  «الآية في سياقها», reading right-to-left in that order
- **AND** the `word` tab is active
- **AND** results produced in one tab remain intact after switching to another tab
  and back.

#### Scenario: No English tab label is rendered

- **WHEN** the Verse Study tab strip is rendered
- **THEN** none of the strings "Word in Verses", "Similar Verses", "Find Verse context"
  appears on screen.
