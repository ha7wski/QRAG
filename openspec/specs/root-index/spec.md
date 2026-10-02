# root-index Specification

## Purpose
«فهرس الجذور»: every Quranic root that carries an occurrence, browsed by first radical in hijāʾī order. Each root shows the figures «الكلمة في الآيات» and «تحليل لساني عربي» already share (distinct āyāt and sūras, its written forms) and the project's mechanical letter assembly, labelled as the app's and never as Islambouli's. No model, no new dataset: everything is read from `root_forms` and `assemble()`.
## Requirements
### Requirement: The index lists every root that carries an occurrence, once

The index SHALL list a root if, and only if, it is the **primary** root of at least one Quranic word.
That is the set of `morphology.json` keys whose `count` is greater than zero: 1 654 roots on today's
data.

A key that exists only as an **alternate** reading SHALL NOT be listed. Today these are `نوس` (the
alternate of `أنس` for ٱلنَّاس) and `طمن` (the alternate of `طمأن`). The words they reach are
already counted under their primary root, so listing them would show the same occurrences twice.

Each root SHALL appear under its canonical QAC key, in its exact hamza-bearing spelling, and never
under a folded form.

#### Scenario: An alternate-only key is absent

- **WHEN** the full index is read across all letters
- **THEN** neither `نوس` nor `طمن` appears
- **AND** `أنس` and `طمأن` each appear exactly once

#### Scenario: The total matches the primary roots

- **WHEN** the number of roots is summed over every letter
- **THEN** it equals the number of `morphology.json` keys with `count > 0`

#### Scenario: A hamzated root keeps its spelling

- **WHEN** the root لؤلؤ is listed
- **THEN** it is shown as `لؤلؤ`, never as `لولو` or `لالا`

### Requirement: Roots are grouped by first radical in hijāʾī order

Roots SHALL be grouped by their first radical, and the groups SHALL follow hijāʾī order:
ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن ه و ي.

All of these SHALL fall into the one first group, labelled «أ»:
- a first radical written as a hamza or on any hamza carrier (أ إ آ ء ؤ ئ);
- a bare alif (ا), as in the arbitrated roots `اول` and `اني`.

Inside a group, roots SHALL be ordered by hijāʾī order letter by letter, comparing with hamza carriers
folded. When two roots are equal under that fold, they SHALL be ordered by their exact spelling. The
ordering SHALL be total and deterministic.

A letter that begins no root SHALL still appear in the letter list, with a count of zero.

#### Scenario: Bare-alif roots join the hamza group

- **WHEN** the «أ» group is read
- **THEN** it contains `أبب`, `اول` and `اني`
- **AND** no separate «ا» group exists

#### Scenario: Group order is hijāʾī

- **WHEN** the letter list is read
- **THEN** «أ» comes first, «ب» second and «ي» last
- **AND** there are 28 groups

#### Scenario: Ordering is reproducible

- **WHEN** the same letter is requested twice, in two separate processes
- **THEN** the roots come back in the same order

### Requirement: Per-root āyāt and sūras come from the shared root-forms computation

For each root, the index SHALL report:
- the distinct āyāt in which the root occurs, as `surah:ayah` refs in canonical order;
- the distinct sūras those āyāt belong to, each with its Arabic name;
- the counts مواضع (words), آيات and سور, each one a DISTINCT count.

The words, the āyāt and their refs SHALL be read from `VerseLookup.root_forms(root)` and SHALL NOT be
recomputed from `morphology.json`. The sūras SHALL be derived from those refs. This means the index
inherits two things:
- the grammatical-tool filter (`word_function.json`);
- the لفظ grouping that «الكلمة في الآيات» and «تحليل اللسان» already share.

As a result, a root gives the same figures on all three pages.

#### Scenario: Parity with «تحليل اللسان»

- **WHEN** the index entry of root رحم is compared with `VerseLookup.root_forms("رحم")`
- **THEN** its مواضع, آيات and āya refs are identical

#### Scenario: A tool-only use is not counted

- **WHEN** the root كيف is listed
- **THEN** its مواضع equals `root_forms("كيف")["words"]`, which today is 3, and not the 83 raw
  occurrences

#### Scenario: The sūra count is distinct

- **WHEN** a root occurs in several āyāt of one sūra
- **THEN** that sūra is counted once
- **AND** the سور count never exceeds 114

### Requirement: Each root shows the project's mechanical letter reading, labelled as such

For each root, the index SHALL show the sentence `linguistics/lisan/islambouli/assemble.py` produces
with no signed choice. Every «أو» alternative SHALL appear, bracketed.

The sentence SHALL carry the exact label «تركيبٌ آليٌّ للأسطر الثلاثة، من صنع هذا التطبيق — لا
تعريفٌ، ولا قولُ إسلامبولي».

The index SHALL NOT show any of the following:
- Islambouli's published sentences (`islambouli_citations.json`);
- the cultural stage;
- a signed personal reading or its choices;
- the core-first engine's reading.

No model SHALL produce or re-word the sentence.

When the assembly refuses a root (not trilateral, a silent position, no formula), the index SHALL
show no sentence and SHALL show the refusal reason instead. That reason SHALL be Arabic text: the
index SHALL NOT send or show an English message, nor fall back to the English `refusal_code`.

If the letter table or the وصف table fails its lock, the readings SHALL be omitted for every root,
with one notice on the page. The listing and the figures SHALL still be served.

#### Scenario: ضرب shows the assembly, not Islambouli's sentence

- **WHEN** the «ض» group is read
- **THEN** ضرب carries «دفع شديد جداً، متوقف مكرر منتهٍ بجمع مستقر» under the label above
- **AND** «دفع شديد مكرر منتهٍ بجمع مستقر» (his published sentence) appears nowhere on the page

#### Scenario: Alternatives are never resolved

- **WHEN** كتب is listed, and a signed personal reading for كتب exists in `app.db`
- **THEN** its sentence is still «(وقف، أو ضغط خفيف) دفع خفيف متوقف منتهٍ بجمع مستقر»

#### Scenario: A quadriliteral root is refused, visibly

- **WHEN** زلزل is listed
- **THEN** it carries no sentence
- **AND** it carries the assembly's refusal reason, written in Arabic with no Latin letter

#### Scenario: A tampered table degrades, not fails

- **WHEN** `islambouli_wasf.csv` no longer matches its lock and a letter is requested
- **THEN** the response still lists the letter's roots with their figures
- **AND** no root carries a sentence
- **AND** the page shows a single notice explaining why

### Requirement: Two read-only routes serve the index

The system SHALL serve two routes:
- `GET /roots`, which returns the 28 letter groups in order, each with its label and its number of
  roots;
- `GET /roots/letter/{letter}`, which returns that group's roots in order, each one carrying:
  - `root`;
  - `words`, `ayat` and `surahs` (counts);
  - `verse_ids`;
  - `surah_list` (number and Arabic name);
  - `forms` (the distinct written forms, from `root_forms`);
  - `reading` (sentence and label), or `reading_refusal`.

`{letter}` SHALL accept the group label and any letter that folds into it, so `ا`, `أ` and `ء` all
return the «أ» group. An unknown letter SHALL return 404.

Neither route SHALL call an LLM, load the embedder or load a reranker.

#### Scenario: Letter list

- **WHEN** `GET /roots` is called
- **THEN** it returns 28 groups whose counts sum to the number of listed roots

#### Scenario: A hamza-carrier path resolves to the group

- **WHEN** `GET /roots/letter/ء` is called
- **THEN** the response equals that of `GET /roots/letter/أ`

#### Scenario: No model memory is paid

- **WHEN** both routes have been called on a fresh backend
- **THEN** `GET /health` still reports the embedder and the reranker as not loaded

### Requirement: The «فهرس الجذور» page

The `/roots` page SHALL show a strip of the 28 letters, each with its root count. Selecting a letter
SHALL list that group's roots, one card per root.

Each card SHALL always show its root and its three counts. Everything else on the card SHALL be
**folded by default** and unfolded by activating the card's header:
- the letter reading and its label, or its refusal reason;
- «السور»: the distinct sūras, each a link to `/surah/{n}`;
- «المواضع»: the root's distinct written forms (ألفاظ) as `VerseLookup.root_forms(root)["forms"]`
  returns them, in that order — the Quran's words that come from this root;
- two links styled as primary (green) buttons: `/verse-study?word=<root>` («الكلمة في الآيات») and,
  to its left, `/lexical?word=<root>` («تحليل لساني»).

The card SHALL NOT list the āyāt nor carry an āya control: «الكلمة في الآيات» is where a root's āyāt
are read. The API still serves `verse_ids`.

The selected letter SHALL be reflected in the URL (`/roots?letter=<letter>`) by a history PUSH, so
that a letter can be deep-linked and the browser's Back returns to the previously selected letter.
All Arabic text SHALL render RTL through `ArabicText`.

#### Scenario: Opening a letter

- **WHEN** the reader opens `/roots?letter=ك`
- **THEN** the «ك» group's roots are listed, each card showing its root and counts only

#### Scenario: A card unfolds

- **WHEN** the reader activates the header of the card of ضرب
- **THEN** its reading, «السور», «المواضع» and the «الكلمة في الآيات» button appear
- **AND** «المواضع» comes right after «السور» and lists the forms of `root_forms("ضرب")`
- **AND** activating the header again folds the card, the root staying visible

#### Scenario: No āya list, two green links

- **WHEN** a card is unfolded
- **THEN** it shows no āya link and no āya control
- **AND** besides the sūra chips it links to `/verse-study?word=<root>` and, to its left,
  `/lexical?word=<root>`, both on green buttons

#### Scenario: Back returns to the previous letter

- **WHEN** the reader selects «ب», then «ك», then presses the browser's Back
- **THEN** the URL is `/roots?letter=ب` and the «ب» group is listed

#### Scenario: Jump to the root's āyāt

- **WHEN** the reader follows a root's «الكلمة في الآيات» button
- **THEN** `/verse-study` opens on that root's «الكلمة في الآيات» results

