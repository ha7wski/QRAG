## Context

Today the "Find Verse context" feature is a standalone route,
`frontend/src/app/verse-context/page.tsx`. It:
- loads the surah list via `getSurahs()` and one verse-in-context via
  `getVerse(surah, ayah, CONTEXT_WINDOW=3)`,
- reads `?surah=&ayah=` query params (under a `<Suspense>` boundary, App Router
  requirement) to deep-link and auto-load,
- renders the target verse highlighted with ±3 neighbours and an "Open full Sourate page"
  link.

`frontend/src/app/verse-study/page.tsx` is a client component with a local `tab` state
(`"word" | "similar"`) and two sub-components (`WordInVerses`, `SimilarVerses`) kept
mounted (hidden via `className`) so results survive tab switches. Both sub-components link
individual verses out with `<Link href={/verse-context?surah=..&ayah=..}>`.

Other references to `/verse-context`: the sidebar (`components/Navbar.tsx`), the landing
feature cards (`app/page.tsx`), and the error-state back link in
`app/verse/[surah]/[ayah]/page.tsx`.

## Goals / Non-Goals

**Goals:**
- Make "Find Verse context" the third tab of Verse Study, after "Similar Verses", with
  identical behaviour to the standalone page.
- Let a verse clicked in the other two tabs open in the context tab in-page (no route
  change), while keeping URL deep-linking working for external/back links.
- Remove the standalone route and every stale reference to it.

**Non-Goals:**
- No backend changes; reuse `getVerse` / `getSurahs`.
- No redesign of the context UI, the picker, or the other two tabs' internals.
- No redirect shim for `/verse-context` (the route is simply removed; internal links are
  all updated). Rewriting local-only docs (CLAUDE.md) is out of scope.

## Decisions

**1. Lift the active tab and a "context target" into the page component.**
Extend the `Tab` union to `"word" | "similar" | "context"` and add tabs entry
`["context", "Find Verse context"]` last. Add page-level state
`contextTarget: { surah: number; ayah: number; nonce: number } | null` and a setter
`openInContext(surah, ayah)` that sets the target and switches `tab` to `"context"`. Pass
`openInContext` down to `WordInVerses` and `SimilarVerses`; pass `contextTarget` to the
new `FindVerseContext` sub-component.

The `nonce` (a monotonically increasing counter, incremented on each `openInContext`
call) is the trigger the context tab watches — so clicking the *same* verse twice, or a
verse already displayed, still re-triggers a load. This avoids relying on value-equality
of `{surah, ayah}`.

**2. In-tab verse activation replaces the `<Link>` navigations.**
In `SurahCard` (Word in Verses) and the Similar Verses result cards, replace
`<Link href="/verse-context?...">` with a `<button>`/clickable element calling
`openInContext(surah, ayah)`. Keeps all three tools on one page and preserves each tab's
state (the page stays mounted). The clickable elements keep their current Arabic
`title`/hover styling.

**3. `FindVerseContext` sub-component = the moved logic, kept mounted like the others.**
Port the standalone page's body (surah picker, ayah input, `lookup`, result rendering)
into a `FindVerseContext` component inside `verse-study/page.tsx`. It reacts to two inputs:
- `contextTarget` (from in-page clicks) — a `useEffect` on `contextTarget?.nonce` calls
  `lookup(target.surah, target.ayah)` and syncs the picker's `surah`/`ayah` state.
- URL query params for deep-linking (see Decision 4).

**4. Deep-linking via `useSearchParams`, page wrapped in `<Suspense>`.**
Move the Suspense boundary up to the Verse Study page (App Router requires
`useSearchParams()` to sit under Suspense). On mount, if `?surah=&ayah=` are present, set
the active tab to `"context"` and auto-load that verse (mirrors the old page's mount
effect). Accepting the bare `?surah=&ayah=` params (no extra `tab=` flag needed) keeps the
existing deep-link URL shape working; a `tab` param is unnecessary because presence of
`surah`+`ayah` implies the context tab. The back link in `verse/[surah]/[ayah]` becomes
`/verse-study` (context tab is the natural landing since it is where a verse lookup lives;
no target params means it opens empty on the context tab — acceptable for an error
fallback). Alternatively it can carry the failed ref; opening empty is the simpler choice.

**5. Delete `app/verse-context/` and prune nav/landing references.**
Remove the directory. Drop the `{ href: "/verse-context", ... }` entry from `Navbar.tsx`
`links` and the matching feature object from `app/page.tsx` `features` (nav shrinks to
three: Talk to Quran · Verse Study · Lisan Analysis). Point the verse-page back link at
`/verse-study`.

## Risks / Trade-offs

- **Suspense scope:** wrapping the whole Verse Study page in `<Suspense>` for
  `useSearchParams` is required; ensure the two existing tabs still render (they will —
  they don't use search params, and the fallback is only shown pre-hydration). Low risk.
- **Broken external bookmarks:** any external link to `/verse-context` 404s after removal.
  Accepted per proposal (product is early; no redirect shim). Internal links are all
  migrated, so in-app navigation is unaffected.
- **State growth in one component:** Verse Study now owns three tabs' worth of state.
  Mitigated by keeping each tab's logic in its own sub-component; only `tab` +
  `contextTarget` live at the page level.
- **Re-trigger correctness:** using a `nonce` (not value equality) guarantees repeated
  clicks on the same verse reload it; forgetting it would make the second click a no-op.
