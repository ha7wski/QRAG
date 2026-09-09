## MODIFIED Requirements

### Requirement: Navigation sits on the right

The persistent navigation SHALL be anchored to the **right** edge of the viewport on
`md` and wider screens, and the main content SHALL be offset on its right accordingly.
On narrow screens the navigation SHALL be a drawer that slides in **from the right**,
opened from a top bar whose menu control sits at the right.

#### Scenario: Sidebar on wide screens

- **WHEN** the viewport is `md` or wider
- **THEN** the navigation sidebar is pinned to the right edge
- **AND** the main content area is offset so that it does not sit under the sidebar.

#### Scenario: Drawer on narrow screens

- **WHEN** the viewport is narrower than `md` and the user opens the menu
- **THEN** the drawer slides in from the right edge
- **AND** it closes on backdrop click, on close-button click, and on selecting an item.

#### Scenario: Navigation item set and order

- **WHEN** the navigation renders its items
- **THEN** it shows exactly six entries, top to bottom: «محاورة القرآن»، «سور القرآن»،
  «دراسة الآية»، «تحليل اللسان»، «التحليل النحوي»، «الفواصل»
- **AND** no entry points to `/qlisan`
- **AND** each item's icon and Arabic label read right-to-left within the row.

#### Scenario: Each entry is told apart by its icon

- **WHEN** the navigation renders its items
- **THEN** no two entries carry the same icon
- **AND** no entry carries the icon used for the brand.

#### Scenario: Brand in the navigation header

- **WHEN** the navigation header renders the application name
- **THEN** it reads «القرآن بالقرآن».
