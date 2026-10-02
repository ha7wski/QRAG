## Why

Every root page in the app starts from a word the reader already has in mind: «الكلمة في الآيات»,
«تحليل اللسان» and the QLisan fiche all need one typed first. Nothing lets a reader browse the
Quran's root inventory itself. The project holds that inventory (1 656 root keys in
`morphology.json`, 1 654 of them carrying occurrences) and computes every figure such a browser
needs. It also produces a mechanical letter reading for 1 613 of them. A reader still cannot see
that inventory as a whole: which roots exist, how widely each one is spread across the āyāt and
sūras, and what the letter decomposition yields for each.

## What Changes

- A new **«فهرس الجذور»** tab (`/roots`) lists every root that has at least one occurrence, grouped
  by its first radical in hijāʾī order.
- For each root, the tab shows:
  - the **distinct āyāt** where it occurs, each one a link to `/verse/{s}/{a}`;
  - the **distinct sūras**, each one a link to `/surah/{n}`;
  - the counts behind them (مواضع, آيات, سور).

  Every figure comes from `VerseLookup.root_forms`, the method «الكلمة في الآيات» and «تحليل
  اللسان» already share. That keeps the grammatical-tool filter and the canonical root keys, so all
  three pages give the same answer for a root.
- Each root also shows its **letter reading**: the project's mechanical assembly of the root's three
  letters (`linguistics/lisan/islambouli/assemble.py`). It is shown under the exact label `/lexical`
  already uses, «تركيبٌ آليٌّ للأسطر الثلاثة، من صنع هذا التطبيق — لا تعريفٌ، ولا قولُ إسلامبولي»,
  and every «أو» alternative is shown, bracketed.
- **Excluded from the tab, per the request («hors interprétation d'Islambouli»):**
  - Islambouli's own published sentences (`islambouli_citations.json`);
  - the cultural stage;
  - signed personal readings.

  The assembly's words still come from Islambouli's frozen letter table. What is left out is his
  interpretation, not his table.
- A root the assembly refuses gets the refusal reason and no sentence. These are the 43 roots that
  are not trilateral (برزخ, زلزل, طمأن …) and any root with a letter that has no row.
- Each root links to `/lexical?word=<root>` and `/verse-study?word=<root>` for the full analysis.
- Two new read-only routes: `GET /roots` (the letters, with how many roots each holds) and
  `GET /roots/letter/{letter}` (one letter's roots, in full). There is no LLM and no new dataset.
- «فهرس الجذور» joins the navigation right before the lexical page. In the same change, after review
  of the running app: three tabs are renamed («دراسة الآيات»، «تحليل لساني عربي»، «فواصل الآيات
  والسور») and «التحليل النحوي» is removed — its page deleted, its routes quarantined. The navigation
  ends at **six** entries.

## Capabilities

### New Capabilities
- `root-index`: the browsable inventory of Quranic roots. It covers:
  - which roots are listed and how they are grouped by letter;
  - the per-root distinct āyāt and sūras and where those figures come from;
  - the per-root mechanical letter reading, with its label and what is excluded;
  - the two routes;
  - the `/roots` page.

### Modified Capabilities
- `rtl-app-shell`: the navigation item set and order change (add «فهرس الجذور», drop «التحليل
  النحوي», three renames).
- `arabic-ui-locale`: the page-name table (three renames, `/roots` added, `/tahlil` gone).
- `islambouli-physical-assembly`: refusal reasons are Arabic.
- `served-surface`: two new routes join the served surface, each with its consumer, `/roots`; the two
  `/tahlil` routes are quarantined.

## Impact

- **Backend:**
  - new `api/routers/roots.py`, mounted in `api/main.py`;
  - new response models in `api/models/`.

  The router reads `app.state.verse_lookup` and `app.state.lexical_retriever`, and imports
  `linguistics.lisan.islambouli.assemble` lazily, as `api/routers/lisan.py` does. Nothing outside
  `api/` imports `linguistics/`, so the import direction is unchanged.
- **Frontend:**
  - new `frontend/src/app/roots/page.tsx` and its components;
  - `lib/api.ts` client functions and `lib/strings.ts` labels;
  - a new `Navbar.tsx` entry.
- **Tests (local-only):**
  - `test_served_surface.py` (two new mounted routes, each with a consumer);
  - `test_frontend_reachability.py`;
  - new backend tests for the listing, grouping and figure parity with `root_forms`;
  - Vitest for the page.
- **Cost:** `root_forms` over all 1 656 keys measured **0.9 s** in total, and the full detail is
  ~600 KB of JSON. That is cheap enough to compute per letter on request and cache in the process,
  with no build step and no `manifest.py` entry.
