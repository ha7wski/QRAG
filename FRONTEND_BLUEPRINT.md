# Frontend blueprint — the reusable shell

What this file is: a **generic** description of the frontend shipped in `frontend/`, written so
the same *shape* (typography, shell, page skeleton, data layer, copy layer) can be lifted into an
unrelated product. It documents the reusable half only. Anything Qurʾān-specific — the root
lookup, the fāṣila charts, the QAC vocabulary — is named here solely so you know what to delete.

Read it top to bottom once, then use §12 as the copy checklist.

---

## 1. Stack

| | |
|---|---|
| Framework | **Next.js 14**, App Router, `src/` layout, `output: "standalone"` |
| Language | TypeScript, `strict: true`, path alias `@/* → ./src/*` |
| Styling | **Tailwind CSS 3** only — no CSS modules, no styled-components, no UI kit |
| Icons | **lucide-react** — the single icon source |
| Fonts | self-hosted `.woff2`, hand-written `@font-face` (no `next/font`) |
| Tests | **Vitest** + Testing Library + jsdom, with their own `tsconfig.test.json` |
| Runtime deps | `next`, `react`, `react-dom`, `lucide-react`. **That is the whole list.** |

The short dependency list is a property worth keeping: every visual decision below is expressible
in Tailwind utilities plus ~150 lines of `globals.css`, so there is no component library to fight,
theme, or upgrade.

Config files, all at `frontend/`: `next.config.js`, `tailwind.config.ts`, `postcss.config.js`,
`tsconfig.json` (+ `tsconfig.test.json`), `vitest.config.ts`, `.eslintrc.json`, `Dockerfile`,
`.env.local.example`.

---

## 2. Directory layout

```
frontend/src/
  app/
    layout.tsx          the shell: <html>, <body>, Navbar, <main> container
    globals.css         @font-face rules + the 3 global classes
    page.tsx            landing (hero + feature cards)
    fonts/              vendored .woff2 + OFL licences + README.md
    <feature>/page.tsx  one directory per route
    <a>/[b]/page.tsx    dynamic routes (deep links)
  components/           presentational + one-concern client components
  lib/
    api.ts              the ONLY place that calls the backend
    strings.ts          the ONLY place user-facing copy lives
    types.ts            response types mirroring the backend contract
    pageCache.ts        useState that survives navigation
    <feature>Types.ts   per-feature response types
```

Three rules make this layout hold:

1. **A page owns fetching and state; a component owns rendering.** Pages are `"use client"` and
   hold `useState`/`useCachedState`; components take props and decide nothing about transport.
2. **No component imports another page.** Shared UI moves to `components/`.
3. **No orphan components.** A test (`test_frontend_reachability.py` in this repo) fails when a
   file under `src/components/` is reachable from nothing. Cheap, and it keeps deletions honest.

---

## 3. The shell (`app/layout.tsx`)

```tsx
export const metadata: Metadata = { title: S.app.title, description: S.app.description };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>
        <Navbar />
        <main className="px-4 py-6 md:ms-64 md:px-8">
          <div className="mx-auto max-w-4xl">{children}</div>
        </main>
      </body>
    </html>
  );
}
```

Four decisions live in those ten lines:

- **Direction and language are declared exactly once.** Every element-level `dir` in the tree is
  therefore either an explicit LTR island or an override *inside* one — never a restatement. For
  an LTR product: `<html lang="en">`, drop `dir`, and §10 mostly evaporates.
- **The sidebar offset lives on `<main>`**, expressed with the logical `ms-` so it follows the
  document direction (`ml-` for an LTR-only app).
- **One measure for the whole app**: `mx-auto max-w-4xl`. Every page inherits it, so no page
  re-decides its own width. Pages that need to be wider (charts, tables) scroll inside their own
  `overflow-x-auto`, they do not break out of the container.
- **Metadata reads from the copy dictionary**, not from literals — see §8.

---

## 4. Navigation (`components/Navbar.tsx`)

One component, two presentations, no media-query JS:

- **`md` and up** — a persistent 64-unit sidebar pinned to the inline-start edge:
  `fixed inset-y-0 start-0 z-50 flex w-64 flex-col overflow-y-auto border-e border-gray-200 bg-white`.
- **Below `md`** — a sticky top bar carrying a hamburger and the brand
  (`sticky top-0 z-30 … md:hidden`), plus the same `<aside>` slid off-canvas by a transform,
  with a `fixed inset-0 z-40 bg-black/40` backdrop. Both the backdrop and any item click close it.

The link list is data, not markup:

```tsx
const links = [
  { href: "/chat", label: S.nav.chat, icon: MessageSquare },
  …
];
const isActive = (href: string) => href === "/" ? pathname === "/" : pathname.startsWith(href);
```

`startsWith` is what keeps `/surah/12` highlighting the `/surah` entry. Active item:

```
bg-gradient-to-l from-brand to-brand-dark text-white shadow-sm
```

inactive: `text-gray-600 hover:bg-brand-light hover:text-brand-dark`, both on
`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition`.

Two conventions worth carrying over: **no two entries share an icon** (the icon is a second
identifier, not decoration), and the brand block at the top of the sidebar is itself a link to `/`.

---

## 5. Typography — the part most worth copying

The rule is **one typeface per script, selected by `unicode-range`, never by a class on an
element**. In this app: Amiri draws Arabic (interface included), IBM Plex Sans Arabic draws Latin
and digits. A Latin run inside an Arabic sentence changes face mid-word, with no markup, because
the Arabic face simply declares no coverage for those codepoints.

```css
@font-face {
  font-family: "Amiri";
  font-style: normal; font-weight: 400; font-display: swap;
  src: url("./fonts/amiri-400-arabic.woff2") format("woff2");
  unicode-range: U+0020, U+00A0, U+0600-06FF, …;   /* Arabic block + the word space */
}
```

```ts
// tailwind.config.ts
fontFamily: {
  sans:   ["Amiri", "IBM Plex Sans Arabic", "Segoe UI", "system-ui", "serif"], // document default
  arabic: ["Amiri", "IBM Plex Sans Arabic", "Segoe UI", "system-ui", "serif"], // explicit handle
  ui:     ["IBM Plex Sans Arabic", "Segoe UI", "system-ui", "sans-serif"],     // named opt-out
}
```

Transferable lessons, each of which cost a bug here:

- **The second entry in the stack is load-bearing, not a fallback.** Since the first face covers
  only one script, everything else *resolves* to the second. Removing it would hand digits to a
  system font.
- **Check which subset carries `U+0020`.** Google ships the word space in the `latin` subset, so
  dropping a face's Latin file silently hands every space *inside* a sentence to the other face —
  measured here as a 19 % tightening of word spacing. The glyph was already in the Arabic file;
  only the declared range omitted it.
- **`next/font/local` cannot express `unicode-range`** (one file per weight/style), and
  `next/font/google` moves the network dependency to build time, where it becomes a *fatal* build
  error offline instead of a silent fallback. Hand-written `@font-face` is the only form that gets
  self-hosting *and* per-subset loading.
- **Keep the files under `src/app/fonts/`, referenced relatively.** Webpack emits them to
  `.next/static/media/`, which the standalone Docker copy already includes. Files in `public/`
  need their own COPY line and 404 without it.
- **Ship the licence next to the font** (`OFL-*.txt`) and do not rename the family — that is the
  whole OFL obligation.

Three global classes, and only three (`globals.css`):

```css
body        { @apply bg-gray-50 text-gray-900; }
.arabic-text{ direction: rtl; @apply font-arabic; line-height: 2.2; }  /* the "content" voice */
.western-digits { font-feature-settings: "locl" 0; }  /* stop locale digit substitution */
```

The generic idea behind `.arabic-text`: **the boundary between the content and the software
around it is carried by size, weight and leading — not by a different typeface.** An earlier split
(chrome in the sans, content in the serif) read as two applications sharing a window.

---

## 6. Design tokens and the recurring class strings

The entire palette extension is four values:

```ts
colors: { brand: { DEFAULT: "#0e7c66", dark: "#0a5c4c", light: "#e6f4f0" } }
```

Everything else is stock Tailwind gray/amber/emerald/sky/red. `brand` for actions and active
states, `brand-dark` for text on light, `brand-light` for tinted surfaces. Swapping the product's
colour is **one line**.

Copy these strings verbatim; they are the visual system:

| Element | Classes |
|---|---|
| Card / panel | `rounded-lg border border-gray-200 bg-white p-4 shadow-sm` |
| Card, interactive | `… rounded-xl p-6 transition hover:border-brand hover:shadow-md` (add `group`) |
| Section with header | `overflow-hidden rounded-xl border bg-white` + `border-b border-gray-100 px-4 py-2.5` header + `px-4 py-3` body |
| Primary button | `flex items-center gap-1 rounded-lg bg-brand px-4 py-2 text-white disabled:opacity-50` |
| Text input | `min-w-[200px] flex-1 rounded-lg border border-gray-300 px-3 py-2 focus:border-brand focus:outline-none` |
| Tab strip | wrapper `flex gap-6 border-b border-gray-200`; tab `-mb-px border-b-2 px-1 py-2 text-base font-medium transition`; active `border-brand text-brand-dark`; idle `border-transparent text-gray-500 hover:text-gray-800` |
| Badge / pill | `rounded-full px-2 py-0.5 text-xs` + a tone pair (`bg-brand-light text-brand-dark`, `bg-emerald-50 text-emerald-700`, `bg-amber-50 text-amber-700`, `bg-sky-50 text-sky-700`, `bg-gray-100 text-gray-500`) |
| Error strip | `rounded bg-red-50 px-3 py-2 text-sm text-red-700` |
| Warning banner | `flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800` |
| Icon tile | `flex h-12 w-12 items-center justify-center rounded-xl bg-brand-light` + `h-6 w-6 text-brand-dark` |
| Page heading | `text-2xl font-semibold text-gray-800` + caption `mt-1 text-sm text-gray-500` |
| Vertical rhythm | `space-y-6` inside a page, `space-y-12` on the landing page |

Icon sizes are `h-4 w-4` inline, `h-5 w-5` in navigation, `h-6/7 w-6/7` in tiles — always with
`shrink-0` in a flex row.

**One rule that is not cosmetic: a tone never carries meaning alone.** Where a badge encodes
provenance or trust (`LevelCard`'s five tones), the *label text* is the contract and the colour is
decoration, so the distinction survives greyscale, colour-blindness and a screenshot.

---

## 7. Page skeleton

Every feature page is the same five blocks in the same order:

```tsx
"use client";
export default function FeaturePage() {
  const [q, setQ] = useCachedState("feature.q", "");        // durable input
  const [data, setData] = useCachedState<T | null>("feature.data", null);
  const [loading, setLoading] = useState(false);            // NEVER cached
  const [error, setError] = useCachedState<Failure | null>("feature.error", null);
  const runSeq = useRef(0);                                 // monotonic run id

  async function run(explicit?: string) { /* see §9 */ }

  return (
    <div className="space-y-6">
      <div>                                                  {/* 1. heading + caption */}
        <h1 className="text-2xl font-semibold text-gray-800">{S.feature.heading}</h1>
        <p className="mt-1 text-sm text-gray-500">{S.feature.caption}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">    {/* 2. control row */}
        <input … onKeyDown={(e) => e.key === "Enter" && run()} />
        <button onClick={() => run()} disabled={loading || !q.trim()}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
          {S.feature.submit}
        </button>
      </div>

      {error && <FailureNote failure={error} className="rounded bg-red-50 px-3 py-2 text-sm text-red-700" />}
      {loading && <p className="text-sm text-gray-500">{S.feature.loading}</p>}
      {data && !loading && <FeatureResult data={data} />}     {/* 5. all rendering delegated */}
    </div>
  );
}
```

Details that matter:

- `onClick={() => run()}`, never `onClick={run}` — the bare form hands React's `MouseEvent` to the
  first parameter.
- **A monotonic `runSeq` ref guards every async write.** Two fast submissions must not leave one
  query's result beside another's. Only `seq === runSeq.current` may call a setter.
- **Tabs stay mounted.** `const [tab, setTab] = useState<Tab>(…)` and then
  `<div className={tab === "x" ? "" : "hidden"}>` — hidden, not unmounted, so each tab's results
  and scroll survive a switch. A heavy tab gets a one-way `opened` latch so it is not mounted (and
  does not fetch) until first activated.
- **`useSearchParams` requires a `<Suspense>` boundary** in the App Router. The page component
  becomes a two-line wrapper around the real one.
- Deep-link arrival stores the *consumed value* in a ref, not a boolean, so `?w=A → ?w=B` without
  an unmount still triggers the second run.
- Independent secondary data is fired alongside and awaited last, with its rejection swallowed:
  a supplementary panel's failure must cost the panel, never the main result.

---

## 8. Copy: one typed dictionary (`lib/strings.ts`)

**No user-facing string is written in a component.** Everything lives in one `as const` object
grouped by page, so the whole interface voice can be reviewed as a single artefact — and so tests
assert on `S.*` keys (checking *wiring*) instead of retyped literals that break on a typo fix.

```ts
export const S = {
  app:  { name: "…", title: "…", description: "…" },
  nav:  { chat: "…", openMenu: "…", closeMenu: "…" },
  home: { heading: "…", lede: "…", cards: { chat: { title, desc, cta }, … }, note: "…" },
  <feature>: { heading, caption, placeholder, submit, loading, … },
  errors: { … }, common: { … },
} as const;
```

Two documented exemptions, worth keeping: text interpolated from backend data, and domain
vocabulary a component derives from a typed map it already owns. Those are content, not interface
copy, and stay with their type.

The dictionary also hosts the *language rules* the interface needs, which is what keeps them out
of JSX:

- `iso(token)` wraps a Latin/numeric token in `FSI…PDI` (`U+2068`/`U+2069`) so `(Qdrant)` inside an
  RTL sentence does not render as `)Qdrant(`. A dictionary entry returns a `string` and so cannot
  emit an element — and this also works inside `title` and `aria-label`, where an element cannot go.
- `count(n, forms)` / `countParts(n, forms)` implement plural agreement (Arabic has four forms:
  1, 2, 3–10, 11+). Any language with non-trivial plurals gets the same treatment: the rule lives
  in one function, the component only decides where the emphasis goes (`components/Counted.tsx`).
- `forStatus(status, kind)` picks the user-facing sentence from **HTTP status + failure kind**,
  so a 422 on a malformed word says what to fix instead of announcing an outage.

---

## 9. Data layer

**`lib/api.ts` is the only module that calls the backend.** One exported `API_URL`, one function
per endpoint, one error type:

```ts
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) { super(message); this.name = "ApiError"; this.status = status; }
}
export function statusOf(e: unknown)  { return e instanceof ApiError ? e.status : undefined; }
export function detailOf(e: unknown)  { return e instanceof Error && e.message ? e.message : undefined; }
```

`NEXT_PUBLIC_*` is **inlined at build time** — it is a build input, not a runtime setting. The
Dockerfile takes it as an `ARG`; a container that must point elsewhere has to be rebuilt.

Error presentation is centralised in `components/FailureNote.tsx`:

```tsx
<div role="status">
  <span>{failure.text}</span>          {/* the sentence: always from the dictionary */}
  {failure.detail && <p dir="ltr" lang="en" className="mt-1 font-mono text-xs opacity-60">{failure.detail}</p>}
</div>
```

The principle generalises past RTL: **raw exception text is never the sentence the user reads.**
Under a network failure that text is the browser's own English string, which is exactly when the
user most needs a sentence they understand. The diagnostic is kept — demoted to a subordinate
technical line, with its own `dir` and `lang` so a screen reader does not read English aloud in the
document's voice.

Three state mechanisms, deliberately distinct:

| Need | Mechanism | Lifetime |
|---|---|---|
| Transient (`loading`, in-flight id) | `useState` | the mount |
| "My search is still there when I come back" | `useCachedState` (`lib/pageCache.ts`) | the tab's JS session |
| "Resume where I stopped" | `localStorage`, debounced + `pagehide` (`lib/readingPosition.ts`) | across sessions |

`useCachedState` is a drop-in `useState` backed by a module-level `Map`. Two constraints are
structural, not stylistic: **the write must happen in an effect** (a module-level Map is shared by
every SSR request, so writing during render leaks one visitor's state into another's HTML — and
`useEffect` never runs on the server, which makes the isolation a guarantee), and **only durable
state may be cached** (a restored `loading: true` is a spinner that never stops). Keys are
namespaced by page and field: `"verse-study.word.query"`.

For resume-style position: persist a **semantic anchor** (an item id), never a scroll offset —
offsets are invalidated by width and font-size. An `IntersectionObserver` over the anchors tracks
it, and is attached **only after the restore scroll**, or it overwrites what it is restoring.

A streaming endpoint (SSE) is consumed with `fetch` + a `ReadableStream` reader in `api.ts`, and
the page appends tokens to the last message; the transport stays out of the component either way.

---

## 10. RTL / bidi rules (skip most of this for an LTR product)

Keep §10.1 in any language; the rest applies when the document direction is RTL.

**10.1 — Content of unknown direction gets `dir="auto"`.** User input echoed back, a translation
field, an answer whose language follows the question: the bidi algorithm derives the run from the
first strong character instead of inheriting the document's. Add `lang` wherever it is known.

**10.2 — Logical utilities everywhere**: `ms-/me-`, `ps-/pe-`, `start-/end-`, `text-start/
text-end`, `border-s/border-e`, `rounded-s*/rounded-e*`. Write the direction's values directly;
do not maintain `ltr:`/`rtl:` variant pairs unless you genuinely ship both directions.

**10.3 — Three categories of trap**, and only the first is greppable:

| Kind | Example | Found by grep? | After a root flip |
|---|---|---|---|
| Physical utility | `ml-4`, `text-right`, `left-0` | yes | unchanged → wrong |
| **Already-logical utility** | `justify-end`, `items-end`, `self-end` | **no** | **silently inverted** |
| Physical with no logical form | `translate-x-*`, `bg-gradient-to-r`, inline `style={{ left }}` | only if enumerated | unchanged → wrong |

The middle row is why a clean grep is not a green light: those classes are *already* correct-looking
and the root direction moves them under you. Each must be re-derived from intent.

**10.4 — Named cases you will hit:**
- **Transforms are physical.** An off-canvas drawer anchored to the inline-start edge hides with
  `translate-x-full` under RTL and `-translate-x-full` under LTR. No logical utility exists; flip
  the sign by hand.
- **Gradients are physical.** `bg-gradient-to-l` is what puts the dark end at a pill's trailing
  edge under RTL.
- **Auto margins are not positions.** `ms-auto`/`me-auto` name *which side of the main axis absorbs
  the free space*; mirroring one turns it inert (measured: `me-auto` moved an element 0 px).
  Convert by preserving the main-axis side, not the physical one.
- **Icons are SVGs and do not mirror.** Decide per site: forward/send/"go there" points along the
  reading direction, back/previous against it; decorative and vertical glyphs (`ChevronDown`,
  spinners, `ArrowUp`) are unchanged. Where no mirrored glyph exists, flip with a transform rather
  than substituting a different icon. The same applies to literal arrow characters, whose
  `Bidi_Mirrored` rendering is engine-dependent.
- **`justify-end` means the *left* edge under RTL.** Rows hand-reversed in source to "look right"
  get flipped twice. Fix the DOM order to be logical and let the container do the work.

**10.5 — LTR islands are bounded and declared.** A chart SVG and *its own scroll wrapper* carry
`dir="ltr"` (an `x` is a coordinate, not text flow), and physical utilities are permitted inside.
Chrome around a chart — legends, buttons, tables, tooltips containing prose — is **not** part of
the island. A tooltip rendered as a sibling is outside it by construction.

---

## 11. Testing

- `npx vitest run` (`vitest.config.ts`, jsdom, `vitest.setup.ts` for jest-dom).
- **Test files are excluded from the main `tsconfig.json`** so `next build` never type-checks or
  fails on test code — which means they are invisible to `tsc` and can rot against an API that no
  longer exists. `tsconfig.test.json` exists solely to type-check them:
  `npx tsc --noEmit -p tsconfig.test.json`. Carry both files or you carry the rot.
- Assert on `S.*` dictionary values, never on retyped user-facing strings.

---

## 12. Duplication checklist

Copy `frontend/` wholesale, then work down this list:

1. `package.json` — rename; the dependency list needs no change.
2. `src/lib/strings.ts` — **rewrite entirely.** This is the product's voice and the largest single
   edit. Keep `iso`, `count`/`countParts`, `forStatus` and the `FailureKind` union; replace the
   `NOUNS` table with your language's plural forms (or delete it for English-style plurals).
3. `src/app/layout.tsx` — set `lang` / `dir`. If LTR: drop `dir`, change `md:ms-64` to `md:ml-64`.
4. `src/components/Navbar.tsx` — new `links` array (label + href + a unique icon). If LTR: flip the
   drawer transform sign, `start-0 → left-0`, `border-e → border-r`, `bg-gradient-to-l → -to-r`.
5. `tailwind.config.ts` — the `brand` triple; and the font stacks (§5) if your scripts differ.
6. `src/app/globals.css` + `src/app/fonts/` — replace the faces, or delete the `@font-face` block
   and the two helper classes entirely for a system-font product. Keep the `body` line.
7. `src/lib/api.ts` — keep `API_URL`, `ApiError`, `statusOf`, `detailOf`; replace the endpoint
   functions. `src/lib/types.ts` mirrors the new backend contract.
8. `src/app/page.tsx` — the landing hero + three feature cards; structure unchanged, copy from `S`.
9. Delete every domain page and component (`verse-study`, `lexical`, `tahlil`, `fassila`,
   `qlisan`, `surah`, `verse`, `Verse*`, `Fassila*`, `Lisan*`, `Tahlil*`, `Sarfi*`, `Fiche*`,
   `ArabicText`, `numerals.ts`, the `*Types.ts`).
10. **Keep as-is**, they are domain-free: `components/FailureNote.tsx`, `components/LevelCard.tsx`,
    `components/HealthBanner.tsx` (repoint the endpoint), `components/ScrollToTop.tsx`,
    `components/Counted.tsx`, `lib/pageCache.ts`, `lib/readingPosition.ts`, `lib/chartTooltip.ts`.
11. `.env.local.example`, `Dockerfile` (`ARG NEXT_PUBLIC_API_URL`), `next.config.js` — port and URL.
12. `vitest.config.ts` + `tsconfig.test.json` — unchanged.

**What makes the result feel like the same product**, in order of impact: the font strategy (§5),
the `brand` triple plus the class table (§6), the sidebar-and-drawer shell (§3–4), and the
five-block page skeleton (§7). The RTL machinery (§10) is the part that does *not* travel — for an
LTR product it collapses into "use `ml-`, and still set `dir="auto"` on user content".
