## Context

Decision D6 of `2026-09-09-arabize-frontend-rtl` gave the application two faces with two
roles: Amiri for Qurʾānic renderings, IBM Plex Sans Arabic for chrome. Both are vendored as
woff2 under `frontend/src/app/fonts/` and declared by hand in `frontend/src/app/globals.css`
— **two `@font-face` rules per weight**, split by `unicode-range` into an `-arabic` file
(U+0600–06FF and the presentation-form blocks) and a `-latin` file (U+0000–00FF plus the
general-punctuation block). That split was adopted because Google publishes these faces per
subset and `next/font/local` cannot express `unicode-range`; it is now the mechanism this
change turns to its own ends.

The current wiring, measured on the running application:

| surface | declared stack | face actually rendered |
|---|---|---|
| `h1` of `/fassila` (`font-arabic`, weight 600) | `Amiri, "Scheherazade New", serif` | Amiri 700 — 193.92 px |
| the same string in the chrome face | — | Plex would be 227.04 px |
| `93` in a comparison row (weight 700) | body default | IBM Plex Sans Arabic — 19.20 px |
| the same digits in Amiri | — | would be 17.02 px |

The owner's reference is the first row for all Arabic, and the third row for all digits.

Two constraints frame the work. `font-ui` is referenced **nowhere** in the source: the chrome
gets Plex only because `fontFamily.sans` was overridden and Tailwind's preflight puts `sans`
on `html`. And Amiri ships **two weights only** (400, 700), against Plex's 400/500/600.

## Goals / Non-Goals

**Goals:**

- One Arabic voice: Amiri on every Arabic string, obtained by default rather than by class.
- Digits and Latin runs render exactly as they do today, with no per-element opt-in — inside
  an Amiri sentence as much as outside one.
- No component file is touched. A change of typographic policy should not be a 25-file diff,
  and it should not need re-applying to every component written afterwards.

**Non-Goals:**

- Changing the numeral policy (`arabic-ui-locale`): which numbers are Western and which are
  Arabic-Indic is decided elsewhere and stays decided there.
- Adding a typeface, a weight, or a build step. Both faces are already vendored.
- Re-tuning the chrome's type scale or weights. If Amiri's colour turns out to be wrong at a
  given size, that is a follow-up with its own evidence, not a guess made inside this change.

## Decisions

### D1 — Select the face by script, not by element

The faces are declared over **different** Unicode ranges and stacked `Amiri, Plex, …`. Amiri
claims the Arabic ranges and the word space; a Latin character or an ASCII digit finds no
Amiri face that claims it and falls through to Plex — mid-word, mid-sentence, with no markup.

The ranges are not disjoint and never were: Google's `arabic` subset already claims
U+200C–200E, U+2010–2011 and U+204F, all of which sit inside the `latin` subset's
U+2000–206F. Where two faces claim a character, **stack order decides** — which is why Amiri
must come first in every stack this change touches, and why `font-ui` (Plex first) is the
only place the outcome inverts.

*Why not the obvious alternative* — put `font-arabic` on every chrome element: it is a diff
across every component, it decays the moment someone writes a new one, and it **cannot solve
the digit half of the request at all**. `<span class="font-arabic">آية 93</span>` sets the
whole run in Amiri, digits included. Getting Plex digits by hand would mean wrapping every
number in the application in a second element. The range mechanism does it for free.

*Why not `font-family` with a `:lang()` selector*: it selects on the *declared* language of
an element, not on the script of the characters, so it has the same mid-run blindness.

### D2 — Delete the Amiri Latin subsets rather than narrow their range

To make Latin fall through, the Amiri `-latin` faces must stop claiming U+0000–00FF. Two ways:
narrow their `unicode-range` to the letters only (keeping Amiri's Latin letterforms while
digits escape), or drop the two files.

Dropping them wins. Amiri's Latin is used on exactly three kinds of run — verse references,
QAC tags, the French/English translation paragraphs — and all three read better in the sans
that already sets them today; a half-escaped range would also be a rule no reader could
predict from the stylesheet. It removes two files from the repository and one line from the
provenance table, and it makes the invariant statable in one sentence: *Amiri draws Arabic,
Plex draws everything else.*

Note this is also what keeps the translation paragraphs (`VerseCard`, no font class, body
default) rendering as they do today even though the body default becomes Amiri.

**Amended during implementation — the word space is carved back out of `latin`.** Google puts
`U+0020` in the `latin` subset, so dropping the Amiri Latin files handed every space *inside
an Arabic sentence* to Plex. Measured on the running page: Amiri's space is 7.007 px at 24 px
against Plex's 5.664 px, so Arabic word spacing tightened by 19 % — on the Qurʾānic verse
bodies as much as on the chrome, a change to the revealed text that nobody asked for and that
the `unicode-range` mechanism caused silently.

The fix costs nothing: `amiri-*-arabic.woff2` **already carries the space glyph**, it was only
absent from the declared range (verified by re-declaring that same file over `U+0020` and
measuring 7.008 px). So `U+0020, U+00A0` are prepended to the Amiri Arabic ranges. No file is
re-vendored, and no other neutral is carved out — punctuation such as `:` and `·` appears only
in chrome sentences, where Plex already drew it before this change.

This is the general shape of the risk, worth stating once: a subset boundary drawn for Latin
web pages does not coincide with the boundary between "Arabic run" and "not Arabic run". The
word space was the one character on the wrong side of it.

### D3 — Keep both faces stacked; keep `font-ui` as the named opt-out

`arabic` and `sans` become the same stack, `Amiri` first and `IBM Plex Sans Arabic` second.
`ui` keeps its present Plex-first stack: it is used nowhere, but it is now the handle the
spec's "secondary face" names, and the escape hatch for a surface that must be sans in Arabic
too. `"Scheherazade New"` leaves the stacks: its job was to catch an Amiri that failed to
load, and Plex — vendored, self-hosted, already in the stack — does that job with a face that
is actually guaranteed to be there.

The Plex `-arabic` subsets stay vendored even though Amiri now precedes them everywhere.

**Corrected by measurement:** the first draft of this decision claimed they would cost nothing
at runtime, on the reasoning that a browser fetches a font file only when a glyph needs it.
They *are* fetched on a cold load — `document.fonts` reports the Plex Arabic 400 and 600 faces
`loaded` on `/fassila`. The cause is `font-display: swap`: while Amiri is still downloading,
the next family in the stack is what paints the Arabic, so the browser fetches it. Roughly
69 KB, once, and the end state is Amiri on every Arabic run — verified by substituting the
stack in place on a live chart label and a sidebar entry, both of which measure to Amiri
exactly. Keeping the subsets is what makes that swap window readable rather than blank, and
they remain what `font-ui` and the Amiri-failed-to-load path resolve to.

`.arabic-text` keeps an explicit font declaration (`@apply font-arabic`) rather than relying
on inheritance: a Qurʾānic rendering should be guaranteed its face even inside a `font-ui`
island.

### D4 — Accept the weight collapse; do not re-tune the chrome

Amiri has 400 and 700. Under CSS font matching, chrome asking for `font-medium` (500)
resolves **down** to 400 — weights below the target are checked before weights above it in
the 400–500 band — and `font-semibold` (600) resolves **up** to 700. So medium chrome becomes
regular and semibold chrome becomes bold.

This is accepted rather than corrected, because the reference the owner chose *is* that
resolution: the `/fassila` heading asks for 600 and is drawn by Amiri 700. Introducing a
weight map to preserve the old visual weights would be optimising against the sample.

## Risks / Trade-offs

- **Legibility of a naskh book face at 12–14 px** — the argument D6 was built on. → Verify on
  the running application at the smallest chrome sizes before closing: the `text-xs` badges in
  `VerseCard`, the 11 px chart annotations on `/fassila`, and the sidebar entries.
- **Amiri's vertical metrics are taller than Plex's**, so line boxes grow at equal
  `font-size`. Fixed-height or tightly-padded chrome (sidebar rows, pill badges, tab strip)
  may crowd or clip. → Same visual pass; the fix, if needed, is padding, not a face.
- **The revealed/software boundary is no longer carried by the face.** → Accepted, explicitly,
  by the owner. It is now carried by size, weight and the `line-height: 2.2` of
  `.arabic-text`, which no chrome surface reproduces.
- **A future Latin-letter surface silently gets Plex.** → That is the rule now, stated in the
  spec and in `fonts/README.md`; it is also what happens today on every such surface.
- **`.western-digits` becomes belt-and-braces**, since the face drawing digits is no longer
  the one with the Arabic `locl` substitution. → Keep it. It is required by `arabic-ui-locale`
  and it is the guard that survives someone re-adding an Amiri Latin subset.

## Migration Plan

CSS and asset-only; there is no data, no API and no build-configuration change. Rollback is
`git revert` of the single commit, which restores the two woff2 files with it. No cache
invalidation concern: webpack content-hashes the emitted font filenames.

## Open Questions

None blocking. The one thing that cannot be settled on paper is the visual pass in
*Risks* — it is a task, not a question.
