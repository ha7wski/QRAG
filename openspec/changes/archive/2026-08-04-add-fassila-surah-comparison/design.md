## Context

`analysis/fassila.py` already derives the pausal fāṣila of every āya and is frozen against a
6236-āya reference fixture. `GET /fassila/{surah}` exposes it one sūra at a time, and
`/fassila` renders that single sūra. Nothing in the stack can currently read the 114 sūras
together, yet every number the comparison tab needs is a field the per-sūra computation
already returns.

Measured on the working tree, over all 114 sūras:

| figure | value |
|---|---|
| mean distinct fawāṣil per sūra | 3.89 |
| sūras with exactly one fāṣila | 18 |
| maximum distinct fawāṣil | 12 — Hūd (11), 123 āyāt |
| distinct-count buckets | 12, contiguous 1 → 12, none empty |
| distinct fawāṣil corpus-wide | 25 |
| āya-count range | 3 → 286 |
| sūras of ≤ 60 āyāt | 78 / 114 |
| cold cost of computing all 114 | 0.22 s |
| warm cost of computing all 114 | ~9 µs (`@lru_cache`) |

The distribution the pie must show, as slice geometry:

| distinct fawāṣil | sūras | share | slice angle |
|---:|---:|---:|---:|
| 1 | 18 | 15.8 % | 56.8° |
| 2 | 19 | 16.7 % | 60.0° |
| 3 | 30 | 26.3 % | 94.7° |
| 4 | 10 | 8.8 % | 31.6° |
| 5 | 11 | 9.6 % | 34.7° |
| 6 | 3 | 2.6 % | 9.5° |
| 7 | 13 | 11.4 % | 41.1° |
| 8 | 4 | 3.5 % | 12.6° |
| 9 | 1 | 0.9 % | **3.2°** |
| 10 | 3 | 2.6 % | 9.5° |
| 11 | 1 | 0.9 % | **3.2°** |
| 12 | 1 | 0.9 % | **3.2°** |

The constraint that shapes almost every decision below: **the derivation is correct and must
not move.** This change is aggregation and presentation only.

## Goals / Non-Goals

**Goals:**

- Serve every figure the comparison tab shows from one request, computed server-side.
- Keep `analysis/fassila.py`'s derivation functions byte-identical; add aggregation beside them.
- Keep tab 1 a pure relocation — same components, same props, same rendering.
- Make the cross-tab presentation rules (RTL, Western digits, left-to-right ascending X on
  axed charts, continuous lines, no section descriptions) normative rather than conventional.

**Non-Goals:**

- Dark mode (see the proposal's non-goals — the app is light-only by construction).
- Any change to `GET /fassila/{surah}`, its models, or the reference fixture.
- Sorting, searching or paginating the sūra list beyond the category filter.
- Persisting the selected tab or filter in the URL.

## Decisions

### 1. One aggregate endpoint, not 114 client requests

`GET /fassila/overview` fans out over the existing `analyse_surah()` and returns a compact
per-sūra summary plus the corpus aggregates.

*Why:* the summary payload is **21 KB** (**25 KB** with the `fawasil` field of decision 10);
the same information gathered by calling `/fassila/{surah}` 114 times transfers **0.7 MB** —
28× more — because each response carries its full per-āya list (up to 286 entries) of which
the tab keeps a handful of fields. Server-side it is nearly free: `analyse_surah` is
`@lru_cache(maxsize=128)` and 128 ≥ 114, so the whole fan-out costs 0.22 s once and ~9 µs
thereafter, over a single shared pass of the QAC treebank.

> The `maxsize=128` bound is **load-bearing** for this endpoint. Lowering it below 114 turns
> every overview request into a full re-derivation. Note it where it is declared.

*Alternatives considered:* 114 client requests — rejected on the payload and request-count
grounds above. A pre-computed `fassila_overview.json` written by an ingestion script —
rejected because it forks the source of truth: the derivation could change and the file
silently not, exactly the failure mode the reference fixture exists to prevent.

### 2. The aggregation lives in `analysis/fassila.py`, as a new function

A new `overview()` beside `analyse_surah()`, `@lru_cache(maxsize=1)`, pure and offline like
the rest of the module. No new module, no logic duplicated: it *calls* `analyse_surah` and
reshapes, so any future correction to the derivation propagates to both readings at once.

### 3. `/fassila/overview` is declared **before** `/fassila/{surah}`

FastAPI resolves routes in declaration order. `/fassila/{surah}` is typed `int`, so if it is
declared first, a request for `/fassila/overview` matches it, fails `int` coercion and
returns **422 — never reaching the overview handler**. The literal route must come first.

This is invisible in review and trivially broken by an "alphabetize the handlers" tidy-up, so
it gets a comment at the declaration site and a test that asserts `/fassila/overview` returns
200 with a `surahs` array.

*Alternative considered:* `/fassila-overview` as a sibling path, sidestepping the ordering
entirely. Rejected — it breaks the resource grouping for a hazard that one test pins.

### 4. The server computes the tiles and the buckets; the front-end only formats

The response carries the four tile values and the distribution buckets pre-computed, not just
the raw per-sūra rows. This honors "le front ne fait que la mise en forme" literally, keeps
the rounding rule in one place, and makes the figures assertable in a backend test rather
than only through the DOM.

Rounding follows the module's existing `pct()` convention — **one decimal** — so the mean
reads `3.9`, consistent with the percentages already on the page.

Buckets span `min(distinct) … max(distinct)` **contiguously**, emitting a zero-count bucket
for any gap. Today the range is 1 → 12 with no gaps, but a contiguous set is what makes the
distribution a distribution rather than a bag of categories, and the front-end must not have
to reconstruct missing steps.

### 5. Tile semantics — an assumption worth naming

"Total" is read as **the number of sūras covered (114)**, giving the denominator against which
"18 mono-fāṣila sūras" is read. The alternative reading — the 25 distinct fawāṣil corpus-wide —
belongs to the derivation, not to the categorization of sūras this tab is about. The response
carries the sūra total; if the other reading is wanted, it is a label change, not a
recomputation.

### 6. Axed charts are SVG with the X axis ascending left-to-right; the pie has no axis

The page is `dir="rtl"`. A flow-layout bar (the `div` in `FassilaBars`) inherits that
direction and grows right-to-left; **SVG coordinates do not** — `x` is measured from the left
edge whatever the ambient direction. Building the axed charts in SVG therefore satisfies
"tous les graphes se lisent de gauche à droite" by construction, with no `direction`
overrides to maintain, and matches how `FassilaLine` already renders its 0-anchored X axis.

**The reading-direction rule applies to charts that have an axis** — the two diversity lines
and tab 1's sequence line. The pie has no X axis and is out of its scope; its ordering
question is answered instead by decision 8 (slice order) and decision 9 (ramp direction).

`FassilaBars` is **not** converted: tab 1 moves unchanged.

### 7. `طول × تنوّع`: linear X, ordered by `(āya count, sūra number)`

The line connects one vertex per sūra, sorted by āya count ascending with the sūra number as
tie-break. The tie-break is not cosmetic: **24 āya-count values are shared by more than one
sūra** (two of them by five sūras each — 11 āyāt: sūras 62, 63, 93, 100, 101; and 8 āyāt),
so without a deterministic secondary key the polyline would reorder between renders. Shared
X values produce short vertical segments — that is the honest rendering of "several sūras of
this length, differing in diversity".

The X axis is **linear**. It is skewed — 78 of 114 sūras have ≤ 60 āyāt, so roughly two-thirds
of the corpus occupies the left fifth of the axis — but a log or square-root scale would make
"X = number of āyas" no longer readable as a length. Legibility is bought instead the way
`FassilaLine` already buys it: a minimum chart width with horizontal scroll inside the card,
never on the page body.

*Alternative considered:* collapsing sūras that share an āya count to a mean Y. Rejected — it
erases individual sūras from a chart whose subject is individual sūras.

### 8. The distribution is a **pie with a clickable legend**, and the legend is the real control

The distribution renders as a pie of 12 slices, in ascending bucket order (1 → 12) clockwise
from the top, beside a legend whose rows carry the **distinct-fāṣila count, the number of
sūras, and the percentage**. Slice and legend row are two views of one control: clicking
either sets the active category, clicking the active one clears it, and hovering either shows
the same tooltip.

The legend is not decoration, it is the **primary hit target**. The geometry table above says
why: three buckets (9, 11, 12) are single sūras at **0.9 %, a 3.2° wedge** — roughly 9 px of
arc at a 160 px radius. A wedge that thin is a poor click target and an impossible hover
target on touch. The legend row for the same category is a full-width, comfortably tall
control that is always reachable, so nothing about the interaction depends on hitting a
sliver.

*Alternative considered:* a bar histogram (the previous design). It reads small categories
far better and supports an axis. Rejected in favour of the validated prototype: the reader's
question here is *part-to-whole* — "what share of the Qurʾān's sūras is mono-fāṣila?" — which
the pie answers directly, and the legend restores the per-category precision the bars gave.

**The filter reaches the sūra list only.** Both diversity lines keep plotting all 114 sūras
whatever the active category, because they are readings of the corpus **shape**: filtering
them to one bucket would flatten the Y axis to a single value and turn a continuous line into
disconnected segments — the "no scatter" rule broken by the interaction meant to help.

### 9. Ordinal single-hue ramp — and the honest limit on how far a ramp can carry 12 classes

The bucket value is **ordinal**: 1 → 12 distinct fawāṣil is a position in a sequence, and
reordering the categories would destroy the meaning. The correct encoding is therefore one
hue with monotone lightness steps — light = few fawāṣil, dark = many — not a categorical
palette. Slices are shaded from a **brand-green** ramp in that direction.

Two things were measured rather than assumed, and both bound the design:

- **`brand.light` (`#e6f4f0`) cannot be the ramp's light end.** It sits at **1.13:1** against
  a white card, well under the 2:1 floor a ramp's lightest step must clear to be visible at
  all. The usable light end is around `#84c4ab` (**2.01:1**).
- **A green ordinal ramp on white supports at most 6 perceptually distinct steps.** With the
  light end pinned at 2:1 and a dark end near `brand.dark`, the usable OKLCH lightness span
  is ≈ 0.37; at a 0.06 minimum step that is 6 steps, and a 7-step ramp already fails on an
  adjacent pair. Spread over **12** slices, adjacent steps fall to **ΔL ≈ 0.037** — buckets 9
  and 10 are not tellable apart by colour.

The conclusion is not to abandon the ramp but to be exact about what it encodes.
**Colour carries direction; the legend carries identity.** No reading of this chart requires
distinguishing step 9 from step 10 by eye — the reader gets the number in words on the legend
row, in the tooltip, and in the list's status line. This is redundant encoding, which is
precisely what makes 12 ordinal classes acceptable here and would not make them acceptable in
a chart where colour was the only channel.

Concretely: interpolate the 12 slice fills across a **validated 6-step anchor ramp** —
`#84c4ab · #6dad94 · #57967e · #407f69 · #296954 · #0e5440` — which passes monotone lightness,
the 0.06 adjacent-ΔL floor, the 2:1 light-end contrast, and single-hue (spread 8°).

> Verify the ramp with an **ordinal** check — lightness monotonicity, adjacent ΔL, light-end
> contrast on the surface. A *categorical* palette validator FAILS a correct sequential ramp
> by design (it spans the lightness band and the light steps sit below the chroma floor); do
> not "fix" a good ramp to satisfy it.

Slice labels, where drawn, must not be tinted text: any text stays in the project's ink
colours, with the slice fill beside it carrying the identity.

### 10. Each summary carries its distinct fawāṣil (`fawasil`)

`FassilaSurahSummary` gains `fawasil: string[]` — the sūra's distinct fāṣila letters, in the
same descending-frequency order (ties broken by first appearance) that `counts` already uses,
so the field is consistent with the per-sūra endpoint's ordering rather than introducing a
second convention.

*Why the field is required:* the list's status line must show the fawāṣil **present in the
current selection**, which is a union over the selected sūras. Neither `distinct_count` (a
number) nor `dominant` (one letter) can produce it — sūra 11 alone contributes 12 letters of
which `dominant` names one. It costs **4.0 KB** on a 21.2 KB payload (→ 25.3 KB), and it is
derived, not computed: the letters are read straight off the `counts` that `analyse_surah`
already returns.

*The selection reading.* Given the active category's sūras, the front-end counts, for each
letter, **how many sūras in the selection carry it**, and orders descending. The tie-break is
**first appearance scanning the selection in muṣḥaf order** — the same philosophy as
`analyse_surah`'s `first_appearance.index(l)`, so the two orderings cannot disagree in
spirit. For the mono-fāṣila category this yields `ا(8) ر(4) ه(2) ن(1) ل(1) د(1) س(1)`: seven
distinct fawāṣil across the 18 sūras.

*Direction.* Emitting the letters in descending order inside the RTL container puts the most
frequent at the **right** and the least frequent at the left by construction — no reversal,
no `direction` override. The letters render enlarged, in the Arabic face, inside parentheses.

### 11. Section order: tiles → pie → list → the two lines

The sūra list sits **immediately after the pie**, not at the end. The pie's only interaction
is filtering that list, and a control whose effect is three screens below reads as inert:
clicking a slice must visibly change something within the same viewport. The two diversity
lines follow, and they are deliberately last — they are corpus-shape readings that ignore the
filter (decision 8), so nothing about them competes for the reader's attention while the
filter is being used.

### 12. Both tabs stay mounted; the overview is fetched on first activation

Tab switching toggles a `hidden` class with both subtrees mounted, matching the existing
three-tab idiom in `app/verse-study/page.tsx` — so tab 1's selected sūra and tab 2's filter
both survive a switch. The overview request fires on the **first** activation of tab 2, not
on page load: visitors who only want one sūra never pay for it, and it is fetched once.

## Risks / Trade-offs

- **A 12-slice pie exceeds the ≤ 6-segment guidance for part-to-whole charts**, and past ~7
  colour classes adjacent shades blur → accepted as the validated prototype's form;
  mitigated by decision 8 (the legend is the primary control and carries every number) and
  decision 9 (colour encodes direction, never identity).
- **Three categories are 3.2° slivers** (buckets 9, 11, 12 — one sūra each) → the legend row
  is always a full-size target for them; slices additionally get a minimum hit area so a
  near-miss still selects, and hover on either surface opens the same tooltip.
- **A future edit "fixes" the ordinal ramp with a categorical validator** and re-steps it into
  something worse → decision 9 states the correct check and why the categorical one fails by
  design; the check belongs in the task list, not in reviewer memory.
- **Route ordering silently regresses to 422** → a test asserting `GET /fassila/overview`
  returns 200 with a `surahs` array, plus a comment at the declaration site.
- **`maxsize` on `analyse_surah` is lowered below 114 by a future edit**, turning every
  overview request into a 0.22 s re-derivation → the bound is documented as load-bearing at
  the decorator; the cost is a latency regression, not a correctness one.
- **The `طول × تنوّع` line is crowded on the left** (78/114 sūras below 60 āyāt) → accepted
  deliberately (decision 7); mitigated by minimum width plus in-card horizontal scroll, and
  by hover tooltips naming each sūra.
- **The selection reading is a sūra count, not an āya count** — `ا(8)` means "8 of these
  sūras rhyme on `ا`", not "8 āyāt" → this is what `fawasil` can support without shipping
  per-letter counts per sūra; the label must not imply āyāt.
- **The two tabs drift apart visually** as one is edited and not the other → the cross-tab
  presentation rules are written as requirements on `fassila-analysis`, so both tabs are
  checked against the same normative text.
- **Cold first request after a restart pays 0.22 s** → accepted; it is below the threshold
  where a spinner is a problem, and the page already shows a loading state.

## Migration Plan

Purely additive: one new route, one new pure function, one new field on a new model, new
front-end components, and the existing page body relocated into a tab. No data migration, no
schema change, no change to any existing response. Rollback is reverting the commit; nothing
outside `/fassila` observes this change.

## Open Questions

None blocking. The one judgement call — what the "total" tile counts (decision 5) — is
recorded as an assumption and is a label change if read differently.
