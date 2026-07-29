# verse-study Specification

## Purpose

Define the Verse Study page, which unifies the study tools for exploring the
Quran through itself: finding every verse of a word's root, finding verses
similar to a phrase, and looking up a verse within its surrounding context. The
former standalone "Find Verse context" route is merged in as a tab, so all verse
study happens on one page.

## Requirements

### Requirement: Verse Study tab set

The Verse Study page SHALL present exactly three tabs, in this order:
"Word in Verses", "Similar Verses", then "Find Verse context". Switching tabs
SHALL NOT discard the state (query, results) of the other tabs — each tab keeps
its own results while hidden.

#### Scenario: Tab order and persistence

- **WHEN** a user opens the Verse Study page
- **THEN** three tabs are shown in the order "Word in Verses", "Similar Verses",
  "Find Verse context"
- **AND** results produced in one tab remain intact after switching to another tab
  and back.

### Requirement: Find Verse context tab

The "Find Verse context" tab SHALL let a user pick a surah (by its Arabic name) and
enter an ayah number, then display that verse rendered with the three verses before
and three verses after it (same surah), vocalized, with the chosen verse highlighted.
It SHALL also offer a link to open the full surah page for that verse. This behaviour
SHALL match the former standalone `/verse-context` page.

#### Scenario: Look up a verse in context

- **WHEN** the user selects a surah, enters a valid ayah number, and triggers the lookup
- **THEN** the chosen verse is shown highlighted, surrounded by up to three verses before
  and three after it from the same surah, each fully vocalized
- **AND** a link to open the full surah page for that verse is shown.

#### Scenario: Ayah number kept within the surah

- **WHEN** the user changes the surah to one with fewer ayat than the currently entered
  ayah number
- **THEN** the entered ayah number is clamped down to the last ayah of the newly selected
  surah.

#### Scenario: Verse not found

- **WHEN** the lookup fails (invalid reference or backend error)
- **THEN** an error message is shown and no verse card is rendered.

### Requirement: Opening a verse from another tab

When a user activates a verse in the "Word in Verses" or "Similar Verses" tab, the page
SHALL switch to the "Find Verse context" tab and load that verse in context, without a
full-page navigation to a separate route.

#### Scenario: Click a verse in Word in Verses

- **WHEN** the user clicks a verse listed under "Word in Verses"
- **THEN** the page switches to the "Find Verse context" tab
- **AND** that verse is loaded and shown in context.

#### Scenario: Click a verse in Similar Verses

- **WHEN** the user clicks a result card under "Similar Verses"
- **THEN** the page switches to the "Find Verse context" tab
- **AND** that verse is loaded and shown in context.

### Requirement: Deep-linking to a verse in context

The "Find Verse context" tab SHALL support being opened with a target verse supplied
via URL query parameters (surah and ayah), auto-selecting that tab and auto-loading the
target verse, so bookmarks and back-links continue to work after the standalone route is
removed.

#### Scenario: Open with a target verse in the URL

- **WHEN** the Verse Study page is opened with surah and ayah query parameters identifying
  a verse
- **THEN** the "Find Verse context" tab is active
- **AND** the identified verse is loaded and shown in context automatically.

### Requirement: Removal of the standalone Find Verse context route

The standalone `/verse-context` route SHALL be removed, and it SHALL no longer appear in
the sidebar navigation or as a landing-page feature card. All internal links that pointed
to `/verse-context` SHALL instead reach the "Find Verse context" tab of the Verse Study
page.

#### Scenario: Route no longer navigable in the app

- **WHEN** a user browses the app
- **THEN** no sidebar entry, feature card, or internal link points to a standalone
  `/verse-context` route
- **AND** the "Find Verse context" functionality is reachable only through the Verse Study
  page.

#### Scenario: Back link from a verse page

- **WHEN** the user follows the "back to verse context" link from a `/verse/{surah}/{ayah}`
  page
- **THEN** the Verse Study page opens with the "Find Verse context" tab active.
