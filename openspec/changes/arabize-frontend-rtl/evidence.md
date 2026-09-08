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
npx vitest run                       11 files, 94 tests, 0 failures  (1.94 s)
npx tsc --noEmit                     clean
npx tsc --noEmit -p tsconfig.test.json   clean
```

Baseline at task 2.3 was 8 files / 77 tests. The three new files are all contract tests:

| file | asserts |
|---|---|
| `src/app/layout.test.tsx` | the shell emits `lang="ar" dir="rtl"`, carries **exactly one** `dir`, offsets by `md:ms-64` with no `m[lr]-`, and takes its metadata from the dictionary |
| `src/app/inputRowOrder.test.tsx` | DOM order of the chat composer and the `/tahlil` and `/qlisan` pickers |
| `src/components/chartAxis.test.tsx` | both charts' `cx` values monotonic, both scroll wrappers `dir="ltr"`, the zoom label islanded |

Each of the three was **proved able to fail** by injecting the regression it exists to catch:
`dir="rtl"` + `md:ml-64` on `<main>`; the `/qlisan` picker reversed in source; `FassilaLine`'s
island removed. A contract test that has never failed is a guess.

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
