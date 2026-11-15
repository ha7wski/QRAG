## Context

`/roots` shows a strip of 28 letter buttons; selecting one pushes `?letter=` and fetches
`GET /roots/letter/{letter}` (memoised per group on `app.state.root_index_letters`), then lists the
group's `RootCard`s. The new sheet `data/maani-huruf/maani_huruf.json` (untracked, compiled
2026-11-15, `meta.badge = "تأويلي"`) holds 28 entries keyed by `letter` (`ا` … `ي`), each with
`name`, `series` (`abu_qaisar` 10 / `generalise` 18), `drawing`, `structure`, `core_sense_ar`,
`sources` (keys `AQ IS HA BL NJ SM`, named in `meta.sources`), `positions.{initial,medial,final}`
(`divine_name` — null on the 14 `substitute_word` positions —, `sense_ar`, `examples`, `origin`),
optional `dimensions`, and fields this change does not display.

The sheet is interpretive and mixes two kinds of authorship: Abu Qaisar's own letters, and letters
the compiler built by generalising his procedure; inside a letter, a position is either stated by
the author, inferred from his example, chosen by a rule, or a substitute word. Showing them all in
one voice would attribute to Abu Qaisar what he never said.

## Goals / Non-Goals

**Goals:** one box per selected letter, before the root list; Arabic only; every reading attributed;
the dataset registered like every other one.

**Non-Goals:** text under each strip button (refused by the user); French fields, videos,
`quran_refs`, `convergence`, `notes`, `discarded_poles`; verifying the examples against QAC
(`meta.to_verify` stays open); using the sheet in `/lexical` or in any reading engine.

## Decisions

**D1 — The file moves to `data/references/maani_huruf.json`.** It is curated scholarship carrying
human decisions, which is exactly `references/`; a fifth top-level folder under `data/` would break
the rule that `data/` is organised by what a file is. Constant `MAANI_HURUF_JSON`, manifest entry
(regenerable: no; producer: manual compilation, sources in `meta.sources`; consumer
`api/routers/roots.py`), loader `loaders.maani_huruf()` cached like the others.
*Alternative*: keep `data/maani-huruf/` — rejected, it is the drift `paths.py` exists to prevent.

**D2 — Served inside `GET /roots/letter/{letter}`, not on a new route.** The box appears exactly
when that response arrives, it is already memoised per group, and the served-surface test pins the
route list — a new route would also need a client function and a test update for no gain.
`build_letter` adds `maani: LetterMeaning | None`. The group label `أ` reads the sheet's `ا`; every
other label reads itself. A missing entry, a missing file or a malformed one yields `maani: null`
and a logged warning — the root list is never lost to the box.

**D3 — The server projects; the client only renders.** `LetterMeaning` carries Arabic fields only:
`letter, name, series, core_sense, drawing, structure, positions[] (position, divine_name|null,
sense, examples, origin), sources[] (key, authority, reading), dimensions[] (letter, sense)`.
Positions are a list in fixed order أول/وسط/آخر; sources follow `meta.sources` key order and skip
absent keys. The authority names shown are Arabic labels held in `lib/strings.ts` keyed by source
code (the `meta.sources` strings are French-and-citation mixes); an unknown code renders its code.

**D4 — Attribution is visible.** The box header carries «تأويلي» and the series label («من سلسلة
أبي قيصر» / «مبنيّ على منهجه بالتعميم»). Each position carries its origin as a muted tag («نصّ
المؤلف» / «مستنبط من مثاله» / «بالقاعدة» / «كلمة بديلة»), and a `null` divine name shows the
substitute-word tag instead of an empty slot.

**D5 — Placement and component.** New `components/LetterMeaningBox.tsx`, rendered in the letter
`<section>` right after the group heading and before the readings notice and the root cards, only
when `data.maani` is non-null. Not folded: it is the answer to the click. Arabic runs through
`ArabicText`, `drawing` included (some values are French, e.g. «resh = tête» — shown as stored,
`dir="auto"`).

## Risks / Trade-offs

- [The sheet is untracked and unverified] → badge «تأويلي» on the box; no figure from it enters any
  count or reading engine.
- [A malformed edit of the JSON] → `maani: null` and the page still lists roots; a pytest checks
  the 28 letters load and project.
- [Memoised letters cache keeps an old sheet] → same as the other per-letter data: a backend restart
  refreshes it.

## Migration Plan

`git mv` is not possible (untracked): move the file, then the empty folder goes. Rollback = revert
the change; no schema or runtime data moves.

## Open Questions

None.
