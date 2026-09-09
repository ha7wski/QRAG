## MODIFIED Requirements

### Requirement: Pages are named in Arabic

Each route SHALL carry an Arabic display name, used identically in the navigation, in
the page heading, and in any cross-page link that names it.

URL paths SHALL NOT change **as part of Arabization**: renaming a page in Arabic SHALL NOT
be the occasion for renaming its route. The table below records the routes as they stand at
this change; a route slug MAY still be realigned by a separate change whose purpose is that
realignment.

| Route | Arabic display name | In navigation |
|---|---|---|
| — (application) | «القرآن بالقرآن» | brand |
| `/chat` | «محاورة القرآن» | yes |
| `/surah` | «سور القرآن» | yes |
| `/verse-study` | «دراسة الآية» | yes |
| `/lexical` | «تحليل اللسان» | yes |
| `/tahlil` | «التحليل النحوي» | yes |
| `/fassila` | «الفواصل» | yes |
| `/qlisan` | «بطاقة الكلمة» | **no** |

`/surah/{number}` is the same page as `/surah`, addressed at a particular sūra; it carries
the same Arabic name and is not a separate entry.

The string "Quran RAG" SHALL NOT appear anywhere in the interface; «القرآن بالقرآن» is
the application's only name.

`/qlisan` SHALL keep its Arabic page name and SHALL be Arabized like every other route,
even though it is absent from the navigation, so that a direct URL does not reach a
half-migrated page.

#### Scenario: One name per page, everywhere

- **WHEN** a route is named in the navigation and in its own page heading
- **THEN** both show the same Arabic name
- **AND** the browser URL for that route is unchanged from before this change.

#### Scenario: A route addressed at a resource keeps its page name

- **WHEN** `/surah/2` is opened
- **THEN** the page is named «سور القرآن» wherever the interface names the page
- **AND** the sūra's own name is shown as the content's heading, not as the page's name.

#### Scenario: The old application name is gone

- **WHEN** any page of the application is rendered
- **THEN** the string "Quran RAG" appears nowhere on screen.

#### Scenario: A route absent from the navigation is still Arabic

- **WHEN** `/qlisan` is opened by direct URL
- **THEN** its heading, caption, buttons and messages are Arabic, exactly as for a
  navigable route.
