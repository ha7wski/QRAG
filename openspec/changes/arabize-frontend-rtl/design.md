## Context

The frontend is Next.js 14 (App Router) + Tailwind 3.4.19, ~50 source files under
`frontend/src`, ~6 500 lines. It is **half-Arabized already**, and that is the real
starting condition:

- Domain output is Arabic — QLisan's fiche labels, Fassila's tabs, the نحوي rows, the
  Arabic placeholders in Verse Study and Lisan Analysis.
- Application chrome is English — navigation, page headings and captions, buttons,
  status and error messages, the whole landing page. ~93 distinct English strings by a
  conservative count, plus the landing page's long-form copy. Two `src/lib/` modules
  contribute too and were missing from the first inventory: `api.ts` throws 23 English
  `Error` messages that today ARE the on-screen sentence, and `conversations.ts` writes
  the English default title `"New conversation"` into `localStorage`.
- Direction is faked, three different ways:
  1. **58 element-level `dir` attributes** — 48 `dir="rtl"` mostly restating what a root
     `dir` would give for free, plus 10 load-bearing `dir="ltr"` islands. (Measured; the
     figure was recorded as 59.)
  2. **Hand-reversed DOM order.** `qlisan` and `tahlil` render their verse picker as
     `button → āya input → sūra select` inside `justify-end`, so an LTR document paints
     them right-aligned and reading right-to-left. The code says so in a comment:
     *"RTL layout; the button ends up on the left."*
  3. **Physical utilities** — `ml-auto`, `text-right`, `border-l`, `-translate-x-full`,
     `left-0`: **36 real occurrences across 16 files**, on 32 lines. The figure recorded
     here was "~93 across 25 files", inflated ~2.6x by a contaminated grep: `rounded-l`
     matches **`rounded-lg`** (61 hits) and `right-`/`left-` match the English comments
     "right-to-left" / "right-aligned" (5 hits). Task 2.1 pins the corrected command.
     **Crucially, ~2/3 of these sit INSIDE a `dir="rtl"` subtree** and therefore mean the
     opposite of what their name suggests — see D12.
  4. **Element-level direction on content that is not Arabic.** Translations, LLM answers
     and the user's own query are rendered with no isolation, so they inherit whatever
     direction surrounds them — see D19.

Constraint from archived specs: `fassila-surah-comparison` requires chart X axes to
ascend **left-to-right** ("sūra 1 is the leftmost vertex and sūra 114 the rightmost").
`FassilaDiversityLine` already documents this and pins its scroll wrapper to `dir="ltr"`.
Document-level RTL must not disturb it.

Tailwind 3.4 provides the full logical-property set (`ms/me`, `ps/pe`, `start/end`,
`border-s/e`, `rounded-s/e`, `text-start/end`) — no upgrade needed.

## Goals / Non-Goals

**Goals:**
- One declaration of direction, at the document root, that every component inherits.
- One dictionary that holds every Arabic interface string, so the wording can be
  reviewed as a single artefact by a reader of Arabic.
- Navigation on the right; action buttons on the left of their input — as a *derived*
  consequence of RTL, not as a per-component trick.
- Qurʾānic text stays typographically distinct from the application around it.
- Zero backend, API, data, or retrieval change.

**Non-Goals:**
- No i18n library, no message catalogues per locale, no language switcher. The app
  becomes deliberately monolingual Arabic; a second locale is not a requirement being
  designed for.
- No route renaming — `/qlisan`, `/tahlil`, `/fassila` keep their URLs.
- No change to the answer language of the LLM (already driven by the question).
- No change to numeral policy.
- No component restructuring (that is `restructure-app-architecture`'s job).

## Decisions

### D1 — Direction at `<html>`, not per page

`<html lang="ar" dir="rtl">` in `app/layout.tsx`; every element-level `dir="rtl"` that
merely restates it is deleted.

*Why:* it makes direction a property of the application rather than a fact each new
component must remember. The 59 scattered attributes are the current cost of not having
done this; every one of them was a decision someone had to make.

*Alternative considered — per-page `dir="rtl"` (what `/fassila` does today).* Rejected:
it leaves the root LTR, so anything rendered outside a page container (portals, the
future toast/dialog layer, `<body>` background scroll behaviour) stays LTR, and the next
component still has to decide.

### D2 — Write RTL values directly; do not use Tailwind's `rtl:` variants

Because there is exactly one direction, `md:ms-64` is written directly rather than
`md:ltr:ml-64 md:rtl:mr-64`.

*Why:* dual-direction classes double the surface to maintain for a benefit — an LTR
mode — that Non-Goals explicitly excludes.

### D3 — Sidebar on the right via logical insets; the drawer transform is physical

| Concern | Now | After |
|---|---|---|
| Sidebar anchor | `left-0` | `start-0` (inline-start = right under RTL) |
| Sidebar border | `border-r` | `border-e` (faces the content) |
| Content offset | `md:ml-64` | `md:ms-64` |
| Drawer hidden state | `-translate-x-full` | `translate-x-full` |

*The transform is the trap.* Tailwind's `translate-x-*` maps to a CSS transform, and
**transforms are physical — they do not follow writing direction**. A drawer that hides
with `-translate-x-full` under RTL slides off to the *left*, i.e. across the content it
should be leaving. The sign must be flipped by hand; no logical utility does it.

### D4 — Restore logical DOM order in the hand-reversed rows

`qlisan` and `tahlil` verse pickers become `sūra select → āya input → load button` in
source order, and `justify-end` becomes `justify-start`.

*Why:* `justify-content` **is** direction-aware — under RTL, `justify-end` means the
*left* edge. Left as-is, those two rows would be flipped twice (once by the reversed
DOM, once by the document) and land as `select → input → button` reading left-to-right,
pinned to the left edge: the exact opposite of the requirement. The rendered pixels
after the fix are identical to today's; only the source becomes honest.

*Alternative considered — `flex-row-reverse`.* Rejected: it re-introduces a second
mechanism for direction and desynchronizes visual order from tab order for keyboard users.

### D5 — One typed dictionary, `src/lib/strings.ts`

```ts
export const S = {
  app:  { name: "القرآن بالقرآن", tagline: "…" },
  nav:  { chat: "محاورة القرآن", verseStudy: "دراسة الآية", … },
  chat: { placeholder: "اكتب سؤالك…", send: "إرسال", newConversation: "محادثة جديدة", … },
  errors: { unreachable: "…", degraded: (parts: string) => `…${parts}…` },
} as const;
```

Keys are grouped by page/component; interpolation is expressed as a function so no
component concatenates Arabic fragments in JSX (where an inserted Latin token would
break the bidi run).

**Two documented exemptions.** (a) Text interpolated from backend data. (b) Arabic domain
terminology a component derives from a typed map it already owns — QLisan's
feature-key → Arabic-label map, the نحوي role labels — which stays with its domain type
rather than migrating into UI strings. These are corpus vocabulary, not interface copy;
`qac-morphosyntax-index` and `qlisan-word-analysis` already specify them.

*Alternative considered — `next-intl`.* Rejected under Non-Goals: a provider, a message
loader and a `useTranslations` call per component, to serve one locale.

*Alternative considered — Arabic literals inline.* Rejected: the Arabic wording is the
part most likely to need review by a human reader, and 25 files is not a reviewable unit.

### D6 — Two typefaces, two roles

`Amiri` stays bound to `.arabic-text` / `font-arabic` and is used only for Qurʾānic
renderings. A screen face — **IBM Plex Sans Arabic** (preferred; it has a true Arabic
design with matching Latin for the numerals we keep Western) — is registered as
`font-ui` and set as the `body` default.

*Why:* Amiri is a naskh book face with fine strokes; at 12–14 px in a tab strip or a
button it loses legibility, and using it for chrome erases the visual boundary between
the revealed text and the software commenting on it — a boundary this product exists to
respect.

The face is **IBM Plex Sans Arabic**, and the "or Noto Kufi Arabic" alternative is
withdrawn: the two are not interchangeable. Noto splits Latin into a separate family, so
under Noto Kufi every Western digit, every `2:255`, every QAC tag and every `dir="ltr"`
detail line would fall through to an unspecified system fallback — on exactly the surfaces
the numeral policy exists to stabilise. `font-ui` therefore also needs a full fallback
stack, matching the existing `arabic: ["Amiri", "Scheherazade New", "serif"]` convention.

**Loading: vendor the files and use `next/font/local`, NOT `next/font/google`.** The
original reasoning here was wrong on two counts. (a) The current `<link>` tags are fetched
by the *browser*, on the reader's machine; `HF_HUB_OFFLINE=1` in `local-dev/start.sh:331`
is a HuggingFace-Hub variable for the *Python* process and has no bearing on them, so it
was never evidence about fonts. (b) `next/font/google` does not remove the network
dependency — it **moves it to build time**, and there the failure is fatal rather than
silent: the fetch error is swallowed into a fallback only when `isDev`
(`next/dist/compiled/@next/font/dist/google/loader.js:139`) and re-thrown under
`next build` (`fetch-css-from-google-fonts.js:58`). `local-dev/start.sh:408` runs
`rm -rf .next` before every rebuild — and it rebuilds whenever any frontend source file is
newer than `BUILD_ID`, i.e. after every edit of this change — so webpack's font cache never
survives. Offline, `next/font/google` turns today's silent serif fallback into
`die "Frontend build failed"` (`start.sh:414`): the app does not launch at all.

So: vendor Amiri (400, 700) and IBM Plex Sans Arabic (400, 500, 600) as woff2 under
`frontend/src/app/fonts/`. Both faces are OFL-1.1, so their licence files ship beside them.

**Amended during implementation (2026-09-08): the declaration is hand-written `@font-face`,
not `next/font/local`.** The original wording named `next/font/local`; it structurally
cannot serve this project. Google publishes these faces **per subset** — a separate woff2
for `arabic` and for `latin` — while `next/font/local` takes **one file per (weight, style)**
and offers no `unicode-range`. That leaves only bad options: declare the `arabic` file alone
and every Western digit, every `2:255` and every Latin technical tag falls through to a
system font — the exact failure this decision rejects Noto Kufi for; or declare both files
under one weight, where Next emits two identical `@font-face` rules with no `unicode-range`,
the browser keeps the first, and the second is dead weight.

Hand-written `@font-face` with `unicode-range` in `globals.css` reaches this decision's
actual goal — self-hosted, no network at build time — *and* keeps the subset economy, so a
page with no Latin never downloads the Latin file. Measured: **388 KB over 10 files**
(Amiri 105+19 / 97+19 KB, IBM Plex 32+13 / 35+14 / 35+14 KB), within the size this decision
budgeted.

The files stay under `src/app/` rather than `public/`, and that is not a preference:
`frontend/Dockerfile` copies `.next/standalone` and `.next/static` and **not** `public/`
(which does not exist in this project), so fonts placed there would 404 in the container
image. Referenced relatively from `globals.css`, webpack emits them into
`.next/static/media/` — verified: the 10 files are there after a clean build.

*What is given up:* `next/font`'s automatic preload hints and its `size-adjust` fallback
metrics. Neither is load-bearing here — `font-display: swap` covers the swap behaviour, and
the layout-shift argument that motivated the migration was about the *runtime* `<link>`,
which is gone either way.

*Note for the tests:* both `next/font/google` and `next/font/local` are **0-byte runtime
stubs** resolved by a webpack loader Vitest never runs. This amendment removes that hazard
entirely — no test needs to mock a font module, because no module is imported. Task 8.3 is
simplified accordingly: it still needs `vi.mock("next/navigation", …)` for `Navbar`, but no
font mock.

### D7 — LTR islands stay, and become explicit

Kept as `dir="ltr"`: the Fassila chart SVGs, their axis labels, tooltips and scroll
wrappers; verse references `2:255`; Latin QAC segment tags. Physical utilities are
permitted **inside** these islands, where the physical side is the intended one.

*Why:* an SVG's `x` is a coordinate, not text flow, and the archived comparison spec
pins the semantics of the axis. Making the islands explicit turns "this happens to work"
into "this is declared".

**Three corrections, all measured against the tree.**

1. *The islands mostly do not exist yet.* Only `FassilaDiversityLine` has any
   (`:142`, `:177`). `FassilaLine.tsx:89` is an `overflow-x-auto` around a `min-w-[560px]`
   SVG with **no** `dir` at all, and `FassilaDistributionPie` has none. So the change must
   **add** an island to `FassilaLine`, not preserve one — and doing so fixes a defect that
   already violates the in-force requirement `openspec/specs/fassila-surah-comparison/spec.md:589`
   ("Chart scrolling is direction-independent"): under `fassila/page.tsx:41`'s `dir="rtl"`
   the sequence chart already opens at the highest āya on a narrow viewport. Task 6.6's
   original "do not touch the `dir="ltr"` wrappers" made that defect unfixable by
   instruction, and task 9.3's screenshot comparison is blind to it — the bug reproduces
   identically before and after.
2. *Tooltips are NOT part of the island.* Listing "tooltips" among the LTR islands was an
   error: both chart tooltips are **siblings** of the scroll wrapper, not children
   (`FassilaLine.tsx:186-193`, `FassilaDiversityLine.tsx:282-291`), and their content is
   **Arabic prose** (`آية {n} · {fasila} · {word}`). Forcing `dir="ltr"` on them would
   invert the field order of an Arabic sentence. They stay right-to-left.
3. *An island must be **bounded** so it contains every physical utility attributed to it.*
   A physical utility on an outer wrapper, a sibling, or a portalled tooltip is a violation
   even when a nearby inner element declares `dir="ltr"`. And flow-layout chrome around a
   chart — a legend, a bar row, a zoom control, a table — is **not** part of the chart's
   island: only the coordinate-bearing SVG and its own scroll container are exempt. D7's own
   rationale ("an SVG's `x` is a coordinate, not text flow") does not reach a legend button.
   `FassilaComparisonTab.tsx:139` is the deliberate counter-case: its scrollable table
   **stays RTL**, because its first column is «السورة» and an RTL container opens on it,
   whereas an LTR island would open the table on its last columns.

### D8 — Tests follow the dictionary, not string literals

The Vitest suites assert on rendered English (`getByText("Load verse")`). They are
updated to assert on `S.*` values imported from the dictionary rather than on retyped
Arabic literals.

*Why:* an assertion that retypes the Arabic passes only until someone fixes a hamza in
the dictionary. Importing the key makes the test check *wiring* — that the component
renders the string it is supposed to — which is the thing that can actually regress.

### D10 — Exception text is not interface language

Twelve call sites render `e?.message || "English fallback"` straight into the UI. Under
a network failure `e.message` is the browser's own English string ("Failed to fetch"),
so translating only the fallback would leave English on screen precisely when the user
most needs to understand what happened.

The pattern becomes: **the user-facing sentence is always the Arabic string from the
dictionary**; the exception text, when it is worth keeping at all, is rendered as a
secondary technical line inside `dir="ltr"` in a muted style.

```ts
// before
setError(e?.message || "Verse not found");
// after
setError({ text: S.errors.verseNotFound, detail: e?.message });
```

*Why:* it makes the Arabic-only requirement hold under failure, not just on the happy
path, and it keeps the diagnostic (which a developer wants verbatim, in English) instead
of discarding it.

*Alternative considered — drop the detail entirely.* Rejected: it would make backend
error text, which several endpoints return deliberately, unreachable from the UI.

### D9 — Ordering against `restructure-app-architecture`

Land **this change first**, then the restructure.

*Why:* the restructure collapses duplicated renderers (`ArabicText` vs `.arabic-text` vs
`font-arabic`), unifies verse rendering, and deletes `LexicalResult`. Those merges are
easier to judge once every component already inherits direction from the root and reads
its text from one dictionary — the merge candidates become textually near-identical.
Run in the other order, this change would have to Arabize components the restructure is
about to delete.

*If the restructure lands first instead:* the only rework is re-applying the string and
direction edits to the surviving merged components — mechanical, but it re-does part of
the sweep. Note that the restructure plans to **delete** `components/LexicalResult.tsx`;
task ordering below marks it so it is not translated for nothing.

**The overlap is 12 files, and two of them are conflicts rather than rework.** Both changes
rewrite: `ArabicText.tsx`, `globals.css`, `verse-study/page.tsx`, `surah/[number]/page.tsx`,
`verse/[surah]/[ayah]/page.tsx`, `lexical/page.tsx`, `VerseCard.tsx`, `VerseContextCard.tsx`,
`LexicalResult.tsx`, `Navbar.tsx`, `page.tsx`, `lib/api.ts`.

1. **Who owns `dir` on `ArabicText`.** `ArabicText.tsx:12` is `<span dir="rtl" lang="ar">`.
   This change's `rtl-app-shell` spec requires deleting a `dir="rtl"` that only restates the
   root; the restructure makes that component the *owner* of direction and forbids bespoke
   `dir="rtl" lang="ar"` markup elsewhere. Archived together, the two requirements
   contradict. Resolution: keep `lang="ar"` (a content declaration, not a direction one) and
   **exempt the canonical Arabic renderer from the redundant-`dir` rule**, recorded in the
   `rtl-app-shell` delta so the archived specs agree.
2. **The `/lexical` slug.** The restructure renames it (`restructure-app-architecture/tasks.md:46`:
   *"realign the `/lexical` route slug to the Lisan feature name"*); this change's
   `arabic-ui-locale` spec said "URL paths SHALL NOT change" and pins `/lexical` in its route
   table. Whichever lands second would invalidate the other's archived main spec.

**Settled 2026-09-08 — this change lands first, and all three consequences are resolved.**
The restructure is at 0/39 tasks, so nothing was committed on either side and the arbitration
cost nothing.

- *(a) `LexicalResult.tsx`* — task 6.7 **translates** it: 3 strings and one `ml-auto`. The
  restructure deletes the component afterwards, so that work is discarded. Accepted: it is
  the cheapest of the three consequences, and the alternative — landing the restructure first
  — would force the string and direction edits to be re-applied across every merged component,
  re-doing part of a 36-site sweep to save four lines.
- *(b) `ArabicText`* — keep `lang="ar"`; the canonical Arabic renderer is **exempted** from
  the redundant-`dir` rule, recorded in the `rtl-app-shell` delta. The exemption is written as
  a property of the component's contract, so the restructure's later requirement that it *own*
  direction reads as a continuation rather than a reversal.
- *(c) The URL requirement is scoped*, not defended: "URL paths SHALL NOT change **as part of
  Arabization**". This is faithful to the requirement's actual intent — Arabization is not an
  occasion to renumber routes — and leaves the restructure's realignment legitimate, which it
  is: `/lexical` genuinely is misaligned with the `lisan/` feature it serves.

### D11 — Settled naming, and the two collisions it leaves behind

The owner has settled the names:

| Surface | Name |
|---|---|
| Application | «القرآن بالقرآن» (replaces "Quran RAG" everywhere) |
| `/chat` | «محاورة القرآن» |
| `/verse-study` | «دراسة الآية» |
| `/fassila` | «الفواصل» |
| `/lexical` | «تحليل اللسان» |
| `/tahlil` | «التحليل النحوي» |
| `/qlisan` | **removed from the navigation** |

Navigation therefore carries five items, in this order: محاورة القرآن، دراسة الآية،
الفواصل، تحليل اللسان، التحليل النحوي.

The `/tahlil` name is **definite**, settled 2026-09-08. The indefinite «تحليل نحوي» read as a
fragment beside four definite or annexed entries — and the definite form is also what stops
the collision below from being character-identical.

**`/qlisan` is removed from the navigation, not from the application.** The route, its
page and its backend endpoints stay. Two consequences are recorded rather than acted on:

1. *The page becomes orphaned.* The navigation is the only inbound link to `/qlisan` in
   the entire frontend — every other occurrence of the string is a backend endpoint
   (`/qlisan/verse`, `/qlisan/word`, `/qlisan/form`), and those stay in use by
   «تحليل اللسان» through `SarfiRows`. After this change the page is reachable only by
   typing its URL. This change still Arabizes and re-directions it (tasks 5.4, 6.x), so
   that a deep link does not land on a half-migrated page.
2. *The `/qlisan` API surface is untouched.* Removing a navigation entry has no bearing
   on the endpoints; nothing backend-side changes.

**The «تحليل نحوي» collision is resolved, not recorded.** `components/LisanResult.tsx:236`
renders a collapsible section headed exactly «تحليل نحوي» — inside `/lexical`, the page now
named «تحليل اللسان». A menu entry and a section of a different page carrying the same name
would let a reader open that section expecting to arrive at `/tahlil`.

Both sides move, so the fix is a rename rather than a note:

- the page is «التحليل النحوي» (definite), and
- the section becomes **«الصرف والإعراب»**.

*Why the section too, rather than relying on the definite/indefinite distinction alone:* that
section renders `SarfiRows`, i.e. **morphology** (صرف) plus a case-marker hint derived from
the نحوي level. Its label was loose independently of this change, and the new one names what
it actually shows. Resolving both halves means the menu confusion disappears for a reason a
reader can see, not because two strings differ by an article.

Task 7.11 carries the rename, including `LisanResult.test.tsx:15`, which hard-codes the old
string as a test constant, and routes the new label through `strings.ts` so gate 4.6 reviews
its wording like every other Arabic string.

### D12 — The physical→logical mapping is TWO tables, and the `dir` attributes are the sweep's input data

A physical utility is not a fact about a side. It is a fact about the side someone wanted
**given the direction their element resolved to when they wrote it**. The tree holds both
kinds, and roughly two thirds of the 36 occurrences are the second:

| The utility sits in… | What `mr-` means there today | Correct logical form |
|---|---|---|
| an LTR-resolving element (no `dir` ancestor) | inline-**end** | `me-` |
| a `dir="rtl"` subtree (48 of them) | inline-**start** | **`ms-`** |

The RTL-subtree mapping is the exact mirror of the LTR one: `mr-`→`ms-`, `ml-`→`me-`,
`pr-`→`ps-`, `pl-`→`pe-`, `right-`→`start-`, `left-`→`end-`, `text-right`→`text-start`,
`text-left`→`text-end`, `border-r`→`border-s`, `border-l`→`border-e`.

Confirmed RTL-context members: the whole `fassila/page.tsx:41` subtree
(`FassilaAnalysisTab.tsx:170,173,176`; `FassilaComparisonTab.tsx:146`;
`FassilaDistributionPie.tsx:188`; `FassilaBars.tsx:49`; `FassilaTile.tsx:29`),
`LisanResult.tsx:72,102,241,275,282`, `MadarAslCard.tsx:102`,
`verse-study/page.tsx:194,714,772`. The repo already states the rule at
`SarfiRows.tsx:134`: *"`items-start` = right edge in RTL"*.

*Consequence for sequencing:* **deleting the redundant `dir="rtl"` attributes must run
LAST, not first.** The original task order deleted them before converting, which destroys
the only evidence of which mapping applies. And the residue grep cannot recover it: a
zero-hit grep passes just as happily on an inverted conversion as on a correct one, so it
is a **coverage** check, never a correctness check.

*Why this was missed:* D4 found the same pathology in DOM **order** and fixed it in two
files, but never generalised it to **utilities**. Three independent reviews landed on this
finding, which is why it is a decision rather than a task note.

### D13 — The direction-aware utilities are the ones the grep cannot find

Two disjoint hazards exist and the inventory only covered one:

| Kind | Example | Grep finds it? | Side after the flip |
|---|---|---|---|
| Physical | `ml-4`, `text-right`, `left-0` | yes | unchanged (wrong) |
| **Logical** | `justify-end`, `items-end`, `self-end`, `*-auto` margins | **no** | **inverted** |
| Physical with no logical form | `translate-x`, `bg-gradient-to-r`, inline `style={{left}}` | only if listed | unchanged (wrong) |

The middle row is why a clean grep is not a green light: those utilities are already
logical, so the sweep leaves them alone while the root flip silently moves them. Each must
be re-derived from intent. Note `flex-col-reverse` is **not** in this class — it reverses
the block axis and is direction-independent — so a class string carrying both
(`flex-col-reverse items-end`, `verse-study/page.tsx:403`) needs each half judged apart.

### D14 — Directional icons follow the reading direction, decided per site

An icon is an SVG: it does not mirror with `dir`. Glyph direction is therefore a decision,
and the tree is already **split** — Fassila's sūra stepper was authored for RTL
(`ChevronRight` labelled «السورة السابقة»), while `/surah` and `/verse` pagination was
authored for LTR. A blanket swap would fix one and break the other.

- *Semantically directional* (forward, back, next, previous, submit, "go there"): forward
  and send point **left**; back and previous point **right**.
- *Decorative or vertical* (`ChevronDown`, spinners, `ArrowUp`, a 180° rotation of a
  vertically symmetric glyph): unchanged.
- Where no mirrored counterpart exists (`Send`), flip with an explicit horizontal transform
  rather than substituting a different glyph.

Also in this class: three literal `←` (U+2190) characters, whose codepoint is
`Bidi_Mirrored`, so their rendered direction inside an RTL run is engine-dependent
(`LisanResult.tsx:150`, `verse/[surah]/[ayah]/page.tsx:49`).

### D15 — Interpolated Latin and numeric tokens are isolated with FSI/PDI, not with spans

The Risks register promised that "Latin/numeric tokens are wrapped in `dir="ltr"` spans",
while D5 required interpolation to happen inside dictionary **functions**. Those two cannot
both hold: a function returns a `string` and cannot emit an element. The token then travels
as one flat run and the bidi algorithm reorders it — `«…فهرس البحث (Qdrant)»` renders as
`)Qdrant(`, because the mirrored parentheses resolve to the surrounding RTL level.

`strings.ts` therefore exports `iso()` wrapping a token in FSI…PDI (`\u2068`…`\u2069`).
It is the only isolation available to a plain string, and it also works inside `title` and
`aria-label`, where an element cannot go. A raw `${token}` in an Arabic template is a review
defect. Where the token is already an element, the dictionary exports the sentence in pieces
and the component renders a `dir="ltr"` span instead.

### D16 — Backend *prose* is interface language; backend *data* is not

D5's exemption (a) and the locale spec's exempt class 3 were meant to cover backend **data**
— a root, a lemma, a percentage, a QAC tag. Read literally they also license backend
**prose**, and that licenses the single most common non-happy path on «تحليل اللسان»:
`lisan/lisan_service.py:178-181` returns a full English paragraph, rendered as the only
content of the panel at `LisanResult.tsx:47`. It arrives as HTTP 200 with `root: null`, so
the "failure message" scenarios never fire either.

The sibling service already holds the correct Arabic sentence, verbatim
(`madar/madar_service.py:179-181`). This change therefore makes **one narrow, prose-only
backend edit** — that `message` plus the `SOURCES` attributions at `:41-45` — and the goal
"zero backend change" is restated as **zero backend *behaviour* change**: no schema, no
endpoint, no retrieval, no contract.

Related, on the frontend side: where a payload offers the same value in both scripts, the
Arabic field is the one to render. `VerseCard.tsx:19` does the opposite today
(`surah_name_en || surah_name_ar`) although `types.ts:6-7` makes the Arabic field required
and the Latin one optional.

### D17 — The Arabic error sentence is selected by failure KIND, not one per call site

D10 demotes the exception text. It must not demote the *information*. Several backend
details are actionable and are precisely why a call site surfaces them —
`lexical/page.tsx:87-89` says so in a comment ("422 carries a FastAPI `detail`; surface it
verbatim"). Collapsing every failure at a call site into one generic Arabic sentence would
satisfy the Arabic-only requirement and make the app less usable: a user who types Latin
script into «تحليل اللسان» would lose the sentence that tells them what to fix.

`strings.ts` therefore exposes `errors.forStatus(status, kind)` returning a distinct Arabic
sentence for the kinds the API actually distinguishes — non-Arabic input, empty input, a
missing verse/word/sūra, a service outage, a network rejection, and a generic fallback.
`api.ts:127` ("not found") and `:128` ("lookup failed") both feed one call site today and
must not merge.

### D18 — Counted nouns take number-aware Arabic forms

D5 required interpolation to be a function; it never required the function to be
**number-aware**. Arabic counted nouns take four forms — singular (1), dual (2), plural
(3-10), singular accusative (11+) — so `${n} آية` is wrong for most values of n. Seven
call sites need it, and one of them, `MadarAslCard.tsx:17-22`, already hand-codes the rule
for 1/2/3-10 and gets 11+ wrong («١١ أصول» must be «١١ أصلًا»): the requirement is
established in the repo and generalised nowhere.

Two of the seven sites are an `aria-label` and a `title` — text a visual review pass cannot
see, and which exemption (a) would otherwise wave through.

### D19 — Content of unknown direction is isolated with `dir="auto"`

The LTR-islands requirement listed charts, verse references and QAC tags. It omitted the
content whose script the interface cannot know in advance, and which after the root flip
inherits RTL: `VerseCard`'s `translation_fr` / `translation_en` paragraphs, the chat answer
bubble (`generation/prompts.py:29-30` answers in the question's language), the composer
textarea, and the user's own query echoed back into an Arabic sentence
(`verse-study/page.tsx:334-336`, `:649-651`).

`dir="auto"` lets the bidi algorithm derive the run from its first strong character instead
of inheriting the document's. Where the language is known, the element also carries `lang`,
so a screen reader does not read English with an Arabic voice — including the `dir="ltr"`
technical-detail line D10 introduces.

Note the interaction with task 5.1: dropping the "Arabic, French, or English" claim from
the landing copy is a change of emphasis, not of behaviour. The capability remains, which is
exactly why this decision is needed.

### D20 — The spec deltas, not the Vitest suites, are this change's durable contract

Every frontend test file is excluded from the published repo (`.gitignore:53-56`;
`git ls-files frontend` lists none) and the CI workflow is local-only. On a clone,
`npx vitest run` exits 0 with "No test files found" — so task 8.5 is **green by absence**,
and every claim the tests were meant to lock would be unenforced.

Consequently: for each behaviour this change guards, the **scenario in `specs/`** is the
artefact of record and the Vitest case is a local convenience. An assertion added in group 8
with no matching scenario is, from the repo's point of view, unverified. Two further limits
are worth stating rather than discovering: jsdom applies no CSS layout, so no Vitest
assertion in this suite can detect a mirroring failure; and `tsconfig.json` excludes the test
files while Vitest transpiles with esbuild, so a mistyped `S.*` key in a test is caught by
neither the build nor the runner.

### D21 — «النظائر» is not available as the `similar` tab label

The `similar` tab runs a semantic phrase search (`GET /search`), and the page's own Arabic
sentence already says so: «ما هي الآيات القريبة في المعنى من …» (`verse-study/page.tsx:648`).
«النظائر» is the term of «الوجوه والنظائر», a discipline about a *word's* senses across
verses — and this codebase already uses it that way, two pages over: `analysis/word_analysis.py:51`
`_nazair()`, and the citation kind `nazir` → «نظيرة» at `TahlilClaim.tsx:9`, both surfaced on
`/tahlil` and `/lexical`. Adopting it here would introduce a second D11-class collision, this
one created by the change rather than inherited.

Recommended: «الآيات القريبة في المعنى» — descriptive, and it matches the sentence the tab
already prints. Tight-strip alternative: «التقارب في المعنى». «الآيات المتشابهة» is also
unavailable: it names المتشابه اللفظي, verbal similarity, which is what this tab does not do.
The label is the owner's call (task 1.6).

### D22 — `lang="ar"` arms the Arabic-Indic digit substitution document-wide

"Numerals — unchanged" is a Non-Goal that this change actively threatens. `globals.css:20-26`
records the mechanism in the repo's own words: Quranic faces carry a `locl` feature that
substitutes Arabic-Indic digits *when the surrounding text reads as Arabic* — a condition the
browser derives from `lang`. Today `<html lang="en">` and only ~30 elements opt into Arabic
locally; `.western-digits` neutralises the feature on 23 nodes. Task 3.3 moves `lang="ar"` to
the root, arming the substitution on **every Amiri run in the application**, including
numeric surfaces that have never needed protection.

The counter-measure is to invert the opt-out into an opt-in: `font-feature-settings: "locl" 0`
on `body`, re-enabled only where Arabic-Indic digits are wanted, with every reading number made
explicit through `toArabicDigits`. This also removes a live inconsistency — `surah/[number]/page.tsx:79`
converts through a *local duplicate* of the helper while `verse-study/page.tsx:228` relies on the
font feature for the same visual idiom.

`.western-digits` itself stays correct but becomes inert on the new UI face, so its coverage
— not its definition — is the risk. The rendered result is font-specific and cannot be
inferred from the source: it must be checked (tasks 2.4, 9.2d).

## Risks / Trade-offs

- **A *converted* physical utility is the real hazard, not a missed one.** Under `dir="rtl"`,
  `text-right` already means `text-start`; ~2/3 of the 36 occurrences sit inside a
  `dir="rtl"` subtree and were written against RTL. A single mapping table inverts them, and
  the residue grep rewards the inversion. → Classify by resolved direction first (D12), keep
  the annotation as an artefact, and treat the grep as coverage only.
- **A missed physical utility is invisible in review but wrong on screen.** → The corrected
  inventory command is pinned in task 2.1 with its output; the previous grep over-reported
  ~2.6× and would have buried the signal.
- **A direction-*aware* utility flips while staying grep-clean.** `justify-end`, `items-end`,
  `*-auto` margins. → D13, audited by hand at named sites.
- **A property with no logical form never flips at all.** Transforms, gradients, inline
  `style={{ left }}`, and SVG icon glyphs. → D3, D14, task 7.6, with the empty results
  recorded too so the check is repeatable.
- **The Fassila charts silently mirror — and one is already wrong today.** `FassilaLine` has
  no LTR island, so a screenshot comparison passes on a defect that pre-exists the change.
  → D7, plus a machine-checkable axis assertion (task 2.2b) instead of an eyeball.
- **Bidi mangling in mixed strings.** → D15: FSI/PDI inside the dictionary, `dir="ltr"` spans
  in JSX, `dir="auto"` for content of unknown script (D19). Three `/ {maxAyah}` fragments and
  five verse references are the concrete sites.
- **The numeral policy is threatened by a change that lists it as a Non-Goal.** → D22.
- **Arabic wording quality is not a build concern.** A typo, a wrong ḥarf, a wrong count form
  or an unidiomatic term compiles fine. → D5 plus D18, and a review gate (4.6) that names a
  reviewer, records its outcome, and blocks group 5 — and that covers the eight Arabic
  templates which stay in components, three of them in `aria-label`/`title` text no visual
  pass can see.
- **English leaks from places the inventory never listed.** `lib/api.ts`, `lib/conversations.ts`
  (persisted), `relativeTime()`, `LevelCard`'s `titleEn` gloss, and a backend paragraph.
  → D16, D20, and a Latin-text audit split into four scoped passes (task 7.10c) because a
  single grep returns ~2000 lines of `className` noise.
- **The safety net is invisible to the repo.** All five test suites are git-excluded. → D20:
  every new assertion also exists as a spec scenario.
- **Test churn is broad and shallow — except where it is deceptive.** One existing test mocks
  `new Error("Verse not found")` and asserts that same string, so under D10 it stays green
  whether or not the Arabic sentence was ever wired. → D8 plus task 8.1(c).
- **Scope pressure toward a redesign.** → Non-Goals hold the line: same routes, same pages,
  same components, same numeral policy. The one deliberate widening is D16's prose-only
  backend edit, and it is bounded to two literals in one module.

## Migration Plan

Incremental, one revertable commit per numbered step. Gates after **every** step:
`npx tsc --noEmit` (seconds) and `npx vitest run` (offline, jsdom, no models). `next build`
is the expensive one and stays at 9.1. Do not batch — the original "single-shot" plan put
both mechanical gates behind 54 tasks over 16 files, which makes a break unattributable.

0. Branch, then pin the inventory (0.1, 2.1, 2.1b, 2.2, 2.4) — no code.
1. Fonts only (3.1, 3.1b, 3.2, 3.4). Gate: an **offline** `next build`.
2. **`dir="rtl"` + `lang="ar"` + metadata (3.3) as a commit of its own.** This is the single
   highest-risk edit in the change: it inverts the resolved direction of every element not
   already inside one of the 48 `dir="rtl"` islands — exactly the elements the physical
   utilities were written for. Gate: walk all **nine** routes at both widths before
   continuing (3.8b). Do not bundle it with fonts or the Navbar; a revert must isolate it.
3. Navbar and content offset (3.5, 3.6-3.6d, 3.7, 3.8).
4. `strings.ts` **drafted in full and not wired** (group 4) — inert, zero risk, and therefore
   **not required to be serialised after the shell**: the draft is authored alongside steps 1-3
   so the owner's review of the blocking core (4.6) overlaps the shell commits instead of
   queuing behind them. Only the *review* gates group 5, not the drafting. The gate itself is
   split — a blocking core of ~25 cross-page strings, then a rolling per-page review at each
   group-5 commit — and three of the five defect classes it used to carry are mechanised
   (task 4.5e), leaving the human pass to register and idiom, which is the only part no
   assertion can judge.
5. One commit per page (5.1-5.8), then the error shape (5.9) and the stored title (5.10).
6. One commit per component group (6.1-6.6e); 6.7 per the task-1.5 decision.
7. The sweep in D12 order: classify (7.1) → convert LTR-context (7.2) → convert RTL-context
   (7.3) as a **separate** commit → cross-boundary alignment (7.4) → direction-aware audit
   (7.5) → no-logical-form properties (7.6) → icons (7.7, 7.8, 7.8b) → **only then** delete
   the redundant `dir` attributes (7.9) → residue and Latin audits (7.10-7.10c).
8. Tests (group 8), then verification (group 9).

**Rollback:** revert the branch — with one caveat, rather than "nothing to undo". Conversation
*titles* are persisted (`lib/conversations.ts:12`, key `quran-rag.chat.v1`, written at `:89`
and `:123`), so a reader who used the app before the change keeps English "New conversation"
entries in the switcher, and after a rollback keeps the Arabic ones. Titles are cosmetic and
self-heal on the first message, so they are mapped on read rather than migrated by a version
bump. **`STORAGE_KEY` MUST NOT change**: `loadStore()` silently returns an empty store on an
unknown key or version and `saveStore` swallows failures, so renaming it to match the new brand
would delete every saved conversation with no error on screen. `lib/pageCache.ts` is genuinely
safe — a module-level in-memory `Map`, never written to disk.

## Settled since the review (2026-09-08)

- **Ordering against `restructure-app-architecture`** — this change first; the three
  consequences are resolved in D9. Task 1.5.
- **The `similar` tab label** — «الآيات القريبة في المعنى» (D21). «التقارب في المعنى» is the
  pre-approved shorter form should the three-tab strip prove too tight in the 9.2 walk.
  Task 1.6.
- **`/tahlil` is «التحليل النحوي»**, and the colliding section of «تحليل اللسان» becomes
  «الصرف والإعراب» (D11). Tasks 1.3, 1.7, 7.11.

## Open Questions

- **`/qlisan` orphaning** (D11) is accepted as-is and belongs to `restructure-app-architecture`.
- **Whether `FassilaDiversityLine`'s zoom controls keep their physical-right placement**
  (task 6.6d) — the only LTR island in the change that wraps chrome rather than geometry.
  Cosmetic; the recommendation is to record the current placement as intentional.
- **The Arabic wording itself**, which no decision above settles: gate 4.6 is the one open
  item that blocks group 5, and it needs a named reviewer and a date.
