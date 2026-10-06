## Why

The «سور القرآن» page reads a sūra whole, but nothing on it tells the reader that an āya is echoed —
by another āya of the same sūra, or by āyāt elsewhere in the Quran. That knowledge already exists,
computed and measured (`surah_similarity.json`'s groups, `quran_close_verses.json`'s pairs), yet it is
only reachable from «دراسة الآيات», one surah or one map cell at a time. Annotating the reading text
itself puts it where the reader actually is, without leaving the page.

## What Changes

- An **on/off switch** on the reading page shows or hides the annotations. Off, the page is exactly
  today's page.
- **Green — close inside the sūra**: an āya belonging to one of its sūra's groups (the same groups
  «المتقاربات داخل السورة» shows) gets its whole text on a green background (not its marker).
- **Orange — close in other sūras**, split by relation, never by a tuned threshold:
  - a pair from the **whole-verse similarity** relation (`from` contains `similarity`) → the āya's
    `﴿n﴾` marker is coloured orange;
  - a pair that is **only a shared passage** (`from == ["passage"]`) → only the words of the common
    part are coloured orange, through its stored character span.
- An āya that is both (73 today: in a group AND a pair end) shows **both cues** at once — neither colour hides the other.
- **Clicking** an annotated āya (its marker or its coloured words) opens a **bubble on the same page**
  listing its close verses in two sections — inside the sūra / in the other sūras — each with its
  vocalized text and, where it has one, its common part marked. **No navigation**: nothing in the
  bubble is a link.
- A legend explains the two colours while the switch is on.
- New route **`GET /surah/{number}/annotations`**: one model-free static lookup per sūra over the two
  existing datasets, returning per āya its group partners, its whole-verse partners, its
  passage-only partners with spans, and the partner verse records the bubble shows.
- **The «سور القرآن» page stops being annotation-free by definition**: its spec's «no analytical
  annotation» clause becomes «none unless the reader turns the annotations on».

## Capabilities

### New Capabilities
- `surah-reading-annotations`: the closeness annotations of the reading page — the switch, the green /
  orange rules, the double cue, the in-page bubble, and the route that feeds them.

### Modified Capabilities
- `surah-reading`: the requirement «The «سور القرآن» page reads one whole sūra» currently forbids any
  analytical annotation; it becomes conditional on the switch, default off.
- `served-surface`: a new mounted route, `GET /surah/{number}/annotations`, with `SurahReader` as its
  consumer.

## Impact

- Backend: new router `api/routers/surah_annotations.py` + models; reads `surah_similarity.json` and
  `quran_close_verses.json` through the existing loaders/readers (`quran_data`,
  `retrieval/quran_close_verses.py`). No rebuild, no model, no new dataset.
- Frontend: `components/SurahReader.tsx` (switch, colouring, bubble), a new bubble component,
  `lib/api.ts` (client + types), `lib/strings.ts` (Arabic labels).
- Tests (local-only): route tests, `test_served_surface.py` (new route ↔ consumer), Vitest for the
  span/marker computation.
- Depends on the current **uncommitted** working-tree state of the similarity routers (per-verse
  `GET /verse/{s}/{a}/similar` quarantined); that work should be committed before this change is
  applied.
