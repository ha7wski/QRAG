# Evidence a clone cannot reproduce

Every test file in this project is git-excluded, the CI workflow is local-only, and
`baseline/` holds screenshots of a build that no longer exists. So the numbers below are
recorded here, in a committed file, rather than left in a terminal (design D20, task 8.7).

Run 2026-09-08 from the worktree `.claude/worktrees/arabize-frontend-rtl`.

---

## 1. The sweep inventory (task 2.1)

A command, not a number. `git grep <rev>` applies one expression to the pre-change tree and
to HEAD without checking either out — which also makes the "after" number reproducible by
anyone holding both commits.

```bash
RE='(^|[^a-zA-Z0-9-])-?((sm|md|lg|xl|2xl|hover|focus|focus-visible|group-hover|disabled|first|last|even|odd):)*(m[lr]-[0-9a-z.[]+|p[lr]-[0-9a-z.[]+|(left|right)-[0-9a-z.[/]+|text-(left|right)|border-[lr]([^a-z-]|$)|border-[lr]-[0-9a-z]+|rounded-([lr]|[tb][lr])([^a-z-]|$)|rounded-([lr]|[tb][lr])-[0-9a-z]+|translate-x-[0-9a-z./[]+)'

git grep -nE "$RE" main -- 'frontend/src/*.tsx' 'frontend/src/*.ts' 'frontend/src/*.css' \
  | grep -viE 'right-to-left|left-to-right|right-aligned|left-aligned'
```

The `-viE` filter is not cosmetic and the order matters: `grep -o` strips the line, so a
prose filter applied after it has nothing left to match. Without the filter the count is
inflated ≈2.6×, because `rounded-l` matches **`rounded-lg`** (61 hits) and `right-`/`left-`
match the English comments "right-to-left" and "right-aligned".

| revision | lines | files |
|---|---|---|
| `main` (before) | **32** | **16** |
| `HEAD` (after) | **3** | **2** |

The three survivors are all deliberate, and all of one kind — **transforms, which have no
logical form at all** (design D13), so their sign was flipped by hand and the grep cannot
tell that from an oversight:

```
frontend/src/app/page.tsx:77            -translate-x-0.5   (an ArrowLeft nudging toward the reading direction)
frontend/src/components/Navbar.tsx:78   translate-x-0      (drawer, open)
frontend/src/components/Navbar.tsx:79   translate-x-full   (drawer, closed — sign flipped, since the drawer now leaves to the right)
```

### Element-level `dir` attributes

| revision | `rtl` | `ltr` | `auto` |
|---|---|---|---|
| `main` | 48 | 10 | 0 |
| `HEAD` | **2** | 23 | 8 |

The two surviving `dir="rtl"` are exactly the two the design exempts: the root declaration in
`layout.tsx` and `ArabicText.tsx`, the canonical Arabic renderer whose direction is part of
its contract (design D9, task 7.9). `dir="auto"` did not exist before this change: it is the
D19 treatment for translations, whose script is not ours to know.

---

## 2. The suite (tasks 8.5, 8.6)

```
npx vitest run                       12 files, 111 tests, 0 failures
npx tsc --noEmit                     clean
npx tsc --noEmit -p tsconfig.test.json   clean
```

Baseline at task 2.3 was 8 files / 77 tests. The four new files are all contract tests:

| file | asserts |
|---|---|
| `src/app/layout.test.tsx` | the shell emits `lang="ar" dir="rtl"`, carries **exactly one** `dir`, offsets by `md:ms-64` with no `m[lr]-`, and takes its metadata from the dictionary |
| `src/app/inputRowOrder.test.tsx` | DOM order of the chat composer and the `/tahlil` and `/qlisan` pickers |
| `src/components/chartAxis.test.tsx` | both charts' `cx` values monotonic, both scroll wrappers `dir="ltr"`, the zoom label islanded |
| `src/lib/strings.test.ts` | `count()` at every boundary for all eleven noun series; no un-isolated `${…}` in an Arabic template; no Latin in any runtime value of `S` outside an FSI/PDI pair |

Each was **proved able to fail** by injecting the regression it exists to catch:
`dir="rtl"` + `md:ml-64` on `<main>`; the `/qlisan` picker reversed in source; `FassilaLine`'s
island removed; a Latin `chat.send`, a dual collapsed onto the singular, and a bare
`${unchecked}`. A contract test that has never failed is a guess.

`tsconfig.test.json` typechecks the test files, which nothing else did — `tsconfig` excludes
them so `next build` ignores them, and Vitest transpiles with esbuild without typechecking. It
found two things on its first run: six `titleEn` props passed to a component that no longer
accepts them (React ignores an unknown prop, so the suite stayed green), and a **pre-existing**
type error in `MadarAslCard.test.tsx`'s fixture.

---

## 3. The build (task 9.1)

```
npx next build     ✓ Generating static pages (10/10)
```

Ten routes, matching task 2.3's baseline: `/`, `/_not-found`, `/chat`, `/fassila`, `/lexical`,
`/qlisan`, `/tahlil`, `/verse-study`, `/surah/[number]`, `/verse/[surah]/[ayah]`.

No TypeScript error from the typed dictionary. Three ESLint warnings, all in
`FassilaComparisonTab.tsx:49` (`react-hooks/exhaustive-deps`) — **pre-existing**, verified by
reading the same line in `main`.

All ten vendored `woff2` are emitted with content hashes to `.next/static/media/`, which is
what design D6 claims and what neither a unit test nor a screenshot can show:

```
amiri-{400,700}-{arabic,latin}.<hash>.woff2
plexarabic-{400,500,600}-{arabic,latin}.<hash>.woff2
```

---

## 4. The Latin-text audit (task 7.10c)

Four scoped passes over `frontend/src`, excluding `*.test.*`. A single naive grep is unusable:
`[A-Za-z]{2,} [A-Za-z]{2,}` returns ~2000 lines, dominated by `className`, module specifiers
and cache keys.

| pass | command | before | after |
|---|---|---|---|
| (a) JSX text nodes | `grep -rnoE '>[A-Za-z][A-Za-z ,.?!-]{2,}<'` | 10 | **0** |
| (b) visible attributes | `grep -rnoE '(placeholder\|aria-label\|title\|alt)="[^"]*[A-Za-z]{2,}'` | 7 | **1** |
| (c) Latin held in a variable | every `setError(` / `setMessage(` / `let …: string` initialiser | 1 | **0** |
| (d) `strings.ts` residue | Latin inside string *values* | — | **0** |

The single (b) survivor is «QAC» inside an Arabic `title` — an exempt identifier, the corpus's
own name. Pass (c) exists for `HealthBanner.tsx:38`, which builds its message into a local
variable and is reachable no other way; all three of its branches now assign from `S.health.*`.
One deliberate Latin constant remains in the source and is not a violation:
`conversations.ts:17`'s `LEGACY_DEFAULT_TITLE`, which is never rendered — it is the value
**compared against** what a previous version wrote to a reader's disk.

---

## 5. Screenshots (`baseline/`)

`before-*` are the pre-change build, photographed while the owner's own stack was running —
a better reference than anything rebuilt afterwards. `after-*` are keyed to the task that
produced them. `after-6-fassila-counted-nouns.jpg` is the one that shows a defect being
removed rather than a layout being flipped: «93 آية · 83.8%», «9 آيات», «آية».

---

## 6. The route walk (task 9.2 and the rest of group 9)

Measured in the running page rather than photographed, so the record is numbers and
not an impression. Viewport 1470 px.

| route | nav gap from the right edge | horizontal overflow | Latin in visible text |
|---|---|---|---|
| `/` | 0 px | 0 | none |
| `/chat` | 0 | 0 | none |
| `/verse-study` | 0 | 0 | none |
| `/fassila` | 15 (scrollbar) | -15 | none |
| `/lexical` | 0 | 0 | none |
| `/tahlil` | 0 | 0 | none |
| `/qlisan` (direct URL) | 0 | 0 | none |
| `/surah/2` | 15 | -15 | none *(after the fix below)* |
| `/verse/2/255` | 15 | -15 | translations only |

The sidebar measures 256 px flush against the right edge, and `<main>` spans 0→1214,
exactly the viewport less the sidebar. `/qlisan` carries no navigation entry: the
sidebar lists exactly five, and none of them is «بطاقة الكلمة» (task 9.2b).

**The walk found two violations no grep could.** Both sit between JSX interpolations,
so the text node the audit's pattern needs never exists:

- `/surah/2` led with «The Cow · La Vache · 286 verses · madani» — two translated
  names, an English noun, and the raw corpus token for the period. Now «مدنية · ٢٨٦ آية»,
  through the same period map `VerseCard` already used.
- `/verse/2/255` preferred `surah_name_en` over `surah_name_ar` and rendered
  «(Surah 2)» and «Verse 255» — the same reversal `VerseCard` had needed, plus one
  Latin label.

Translations keep their Latin, and that is the design: every one carries `dir="auto"`
with its `lang`, verified live on `/verse/2/255` — four French and four English runs,
each isolated (design D19).

### Numerals (task 9.2d)

The two sites task 3.4c set out to reconcile **still disagreed**: `/surah/2` rendered
«﴿١﴾» and `/verse-study` «﴿1﴾». Only half of 3.4c had been done — the duplicated helper
was deleted, but Verse Study still left the conversion to the font's `locl` feature,
which design D22 measured does not fire in Amiri v30. Both badge sites now convert
explicitly. Verified after the fix, on one page: badges «﴿١﴾ ﴿٣﴾ ﴿٣٧﴾ ﴿٥٤﴾»
(Arabic-Indic) beside analytical counts «336, 116, 2» (Western).

### Directional controls (task 9.4b)

| control | icon | position |
|---|---|---|
| previous āya («2:254») | `arrow-right` | x 1019 — toward the start |
| next āya («2:256») | `arrow-left` | x 180 — toward the end |
| «السورة السابقة» | `chevron-right` | x 980, right of the select |
| «السورة التالية» | `chevron-left` | x 690, left of the select |

### Input rows (task 9.4)

Every action button sits left of the control it acts on, and the picker reads
right-to-left: sūra 945 → āya 771 → action 624. The chat composer: box at 635, send at
183. The sūra `<select>`'s UA disclosure arrow draws on the left, clear of the Arabic
text; the Verse Study āya box was the only one aligning to the start and now matches
its two siblings with `text-center`.

### Charts (task 9.3)

The sequence chart cannot overflow above 560 px, so the scroll origin was measured on
the diversity chart instead, whose zoom makes it overflow at any width. At ×2:
`scrollWidth 1708 > clientWidth 854`, `scrollLeft 0` — it opens at sūra 1, under real
overflow, which is the whole point of the `dir="ltr"` island. The comparison **table**
beside it carries no `dir` and opens on «السورة», its first column (task 6.6e).

### Failure paths (task 9.5)

- Backend unreachable: «تعذّر الاتصال بالخادم؛ تأكّد من تشغيله ثم أعد المحاولة.»
- A 422 from «تحليل اللسان»: «تُكتب الكلمة بالحرف العربي.» over
  `word must be written in Arabic script` in a `dir="ltr" lang="en"` line.

The second was a **defect found by this walk**: it used to read «تعذّر الاتصال
بالخادم» — an outage that had not happened. `/lexical` is the one page that does not
go through `lib/api.ts`; it hand-rolled its `fetch` and threw a plain `Error`, so the
status never reached `statusOf()` and `forStatus(undefined, …)` chose the outage
sentence. It now throws the same `ApiError` the client throws.

### Stored conversations (task 9.2e)

A seeded `version: 1` store whose conversation is titled `New conversation` opens with
«محادثة جديدة» in the switcher, the conversation intact, and the English title still on
disk — mapped on read, never migrated, because bumping the version would discard every
saved conversation.

### What could not be verified

**Mobile width.** `resize_window` reports success and the viewport does not change —
`innerWidth` stays 1470 and `outerWidth` reads 0. Measured twice, at 420×860 and at
1000×800. Recorded as a gap rather than claimed.

What that leaves unexercised is the drawer, and its one risky part **was** measured,
because the transform is physical and its sign had to be flipped by hand (design D13).
Applying the closed-state classes without the `md:` override gives
`matrix(1, 0, 0, 1, 256, 0)` — the drawer leaves to the **right**, off the viewport
edge at 1470. Before this change it was `-translate-x-full`, for a drawer pinned left.
The rest of the mobile question is `flex-wrap` rows, where the placement rule does not
bind and DOM order does — and DOM order is asserted by test 8.4 at every width.

---

## 7. Every mirrored site, before and after (task 9.7)

Generated from the 2.1 inventory rather than eyeballed, because a screenshot diff
cannot answer the question this table exists for: whether a side was *already* wrong
before the change. Twice in this change it was — the percent sign and the counted
nouns — and both are invisible to a before/after comparison that assumes the "before"
was correct.

```
30 sites

app/layout.tsx:  33  ml                           (site removed or rewritten)
app/verse-study/page.tsx: 194  text-right                   right  -> text-start                 right
app/verse-study/page.tsx: 219  text-right                   right  -> text-start                 right
app/verse-study/page.tsx: 516  text-right                   right  -> text-start                 right
app/verse-study/page.tsx: 714  text-right                   right  -> text-start                 right
app/verse-study/page.tsx: 772  text-right                   right  -> text-start                 right
components/ChatInterface.tsx: 309  text-left                    left   -> text-start                 right
components/ChatInterface.tsx: 353  text-right                   (site removed or rewritten)
components/ChatInterface.tsx: 363  ml                           left   -> ms                         right
components/ChatInterface.tsx: 388  ml                           left   -> ms                         right
components/FassilaAnalysisTab.tsx: 170  text-right                   right  -> text-start                 right
components/FassilaAnalysisTab.tsx: 173  text-right                   right  -> text-start                 right
components/FassilaAnalysisTab.tsx: 176  text-right                   right  -> text-start                 right
components/FassilaBars.tsx:  49  text-left                    left   -> text-end                   left
components/FassilaComparisonTab.tsx: 146  text-right                   right  -> text-start                 right
components/FassilaDistributionPie.tsx: 188  text-right                   right  -> start                      right
components/FassilaTile.tsx:  29  mr                           right  -> ms                         right
components/LexicalResult.tsx:  23  ml                           left   -> ms                         right
components/LisanResult.tsx:  72  mr                           right  -> ms                         right
components/LisanResult.tsx: 102  mr                           right  -> ms                         right
components/LisanResult.tsx: 241  mr                           right  -> ms                         right
components/LisanResult.tsx: 275  mr                           right  -> ms                         right
components/LisanResult.tsx: 282  right, text-right            right  -> start, text-start          right
components/MadarAslCard.tsx: 102  pr                           right  -> ps                         right
components/Navbar.tsx:  30  ml                           (site removed or rewritten)
components/Navbar.tsx:  67  left, border-r               left/right -> start, border-e            left/right
components/ScrollToTop.tsx:  29  right                        right  -> end                        left
components/VerseCard.tsx:  57  ml                           left   -> ms                         right
components/VerseCard.tsx:  63  text-right                   right  -> text-start                 right
components/VerseContextCard.tsx:  59  text-right                   right  -> text-start                 right
```

Reading it: **24 of 30 sites keep the side they rendered on**, which is the mirror
table doing what D12 says it does. The exceptions are all deliberate and all recorded:
`ScrollToTop` (right → left, clear of the navigation that took the right), `Navbar`
(the drawer edge), and the chat's own rows. Three rows are misreported by the
generator and worth the footnote: `ChatInterface:388`, `LexicalResult:23` and
`VerseCard:57` are **auto margins**, where the "side" of the utility is not a position
but the side of the main axis that absorbs the free space — the case task 7.12
corrected after measuring it.
