## Context

`/lexical` has now had two engines and is about to have a third. The history matters, because
each engine fixed the previous one's defect and inherited a new one.

1. **Concatenation** (original). One frozen gloss per letter, chained. `خ-ي-ر` read
   «القذارة والخشونة والخواء… فساد» — the antonym of the attested sense. Defect: a letter carries
   a *bundle* of senses and nothing selected among them.
2. **Core-first** (`constrain-lisan-by-root-core`, shipped). Ibn Fāris' aṣl is fetched first and
   selects one sense per letter by shared axis. `خ-ي-ر` now reads correctly, and the minimal pair
   `خ-ي-ر`/`خ-ب-ث` proves the same letter can read two ways. Defect, structural and unavoidable:
   **the selector is the answer**. A sense survives by agreeing with the core, so the output cannot
   carry information the core did not already carry. `رحمة` shows it at the surface — `ر` matches
   nothing and is reported `unmatched` — but the deeper cost is invisible: on the roots where it
   *does* produce a paragraph, that paragraph is a restatement of the aṣl.
3. **Physics-first** (this change). Nothing about the root's meaning enters before the concept
   exists. The input is the tajwīd description of its letters; the aṣl is read afterwards, to
   check the result.

The engine in (2) is **not** modified, deprecated, or hidden by this change. Both answer, side by
side, until the comparison in §8 has a number attached to it.

What is already on disk and what this design does with it:

| Asset | Status | Use here |
|---|---|---|
| `arabic_letters_dataset.csv` — `makhraj_ar`, `sifat` for 28 letters | shipped | **the only input** |
| the same file's `ibn_jinni_note*` columns | shipped | **banned from this path** (§2) |
| `letter_senses.csv` + its lock (58 sourced senses) | shipped, frozen | not read |
| `root_cores.json`, `semantic_axes.json` | shipped | read **after** generation only (§7) |
| `morphology.json` (1656 roots, 1613 triliteral) | derived | occurrence lists for the confrontation |
| `maqayis_asl.csv` (3326 roots with a cited aṣl) | shipped | 1149 of the 1613 triliteral QAC roots |

## Goals / Non-Goals

**Goals:**

- Generate a **مفهوم** — one fixed Arabic sentence — for a root, from the measurable phonetics of
  its letters and nothing else.
- Make blindness **architectural**, not procedural: the composing modules must be incapable of
  reading the aṣl, enforced by a static import test, not by discipline.
- Make the mapping table **frozen, sourced and root-independent**, on the proven
  `letter_senses.lock.json` model.
- Report **one** number on a **pre-drawn, never-inspected** witness set: how many generated
  concepts cover all attested uses.
- Say out loud, on screen, that a مفهوم is fixed and a معنى is contextual — and say when a
  concept is partial.

**Non-Goals:**

- Beating the core-first engine. The comparison is the deliverable; a verdict is not.
- Covering every root. Quadriliterals and alef-bearing keys are explicitly out (§6).
- Any per-root tuning, exception list, or override. There is no mechanism for one, by construction.
- Touching `linguistics/lisan/`'s existing modules, `letter_senses.csv`, or `POST /lisan/analyze`.

## Decisions

### D1 — The input is `sifat` and `makhraj_ar`; `ibn_jinni_note*` is banned

`arabic_letters_dataset.csv` mixes two layers. `makhraj_ar` / `sifat` are tajwīd description —
`ب` is `shadida; majhura; mustafila; munfatiha; qalqala`, which is a fact about the mouth.
`ibn_jinni_note` is already a reading — «the lips seal and hold air, then burst — gesture of
enclosing and then releasing what is contained». That column is **one frozen interpretive gloss per
letter**: it is engine (1), verbatim, sitting in a CSV. Reading it would reintroduce the original
bug wearing this change's name.

The ban is enforced, not merely stated: the feature extractor selects its columns by name and a
test asserts that no module under `linguistics/lisan/concept/` mentions `ibn_jinni_note`.

*Alternative rejected*: use `ibn_jinni_note` as a "sanity hint" for the curator. Rejected because
a hint consulted while writing the table is back-fitting with extra steps.

### D2 — Only the marked member of an opposition yields a primitive

24 of 28 letters are `munfatiha`; 21 of 28 are `mustafila`. A feature carried by six sevenths of
the alphabet discriminates nothing, and a table that maps it is padding its own output.

The criterion is not a coverage threshold (which would be an arbitrary line drawn where it happens
to be convenient) but the classical structure of the صفات themselves:

- **Privative oppositions** — one member is defined as the *absence* of the other. `انفتاح` is the
  absence of `إطباق`; `استفال` is the absence of `استعلاء`. The absent member yields **nothing**.
- **Equipollent oppositions** — both members are positive articulatory states: `شدة` / `توسط` /
  `رخاوة` (three degrees of air obstruction), `جهر` / `همس` (air checked vs. air running). Every
  member yields a primitive.
- **صفات لا ضد لها** — `قلقلة`, `صفير`, `تكرير`, `تفشي`, `استطالة`, `انحراف`, `لين`, `غنة`. Each
  yields a primitive.
- **Unresolved values** yield nothing. `ء` carries `mahmusa/majhura (debated)`; a disputed fact is
  not a fact. `ء` is left with `شدة` alone.

This rule is posed before the table, applies to the vocabulary rather than to any letter, and is
what excludes `munfatiha`/`mustafila` without anyone deciding that they are inconvenient.

### D3 — مخرج IS mapped in v1.0.0 — §D13's probe decided it

> **AMENDED 2026-09-25, after the probe.** This section chose option (b), and it said so
> provisionally: «§D13's collision probe runs before any curation and decides it.» It ran, it
> returned `identical` on 5 of 5, and **option (a) is now v1.0.0**. The original reasoning is kept
> below because it is the record of what was believed before the measurement; the verdict closes the
> section.

The sheet holds **18 distinct `makhraj_ar` strings for 28 letters** (this note first said 23; the count was wrong, and the correction leaves the argument standing — 18 strings over 28 letters is still close to one per letter). A table keyed on them would
be a per-letter glossary in disguise — the same artefact D1 bans, arrived at by arithmetic instead
of by prose. Two ways out:

- **(a) Reduce to the five classical zones** (حلق / لهاة-حنك أقصى / وسط اللسان / طرف اللسان-لثة-أسنان /
  شفتان) and map those.
- **(b) Record the مخرج on screen as part of the physical profile, map nothing from it in v1.**

**(b) was chosen, provisionally.** The primitive vocabulary is capped at 15 (§D4) and the صفات alone fill it
exactly; adding five zone primitives means either breaking the cap or evicting real صفات to make
room for a coarser signal. More decisively: the acceptance case `ضرب` is fully reproducible from
the صفات alone (§D5), so the zones are not needed to clear the bar this change set itself. **That was provisional.** §D13's collision probe ran before any curation and decided it.

*Consequence, stated up front*: `ب`'s «qui se ferme» in the brief's own gloss comes from the
**makhraj** (the two lips sealing), not from a صفة. The generated concept for `ب` will carry the
sharp stop and the rebound and will **not** carry the closure. That was a real loss, recorded
rather than patched — **and it is now partly recovered**: with the zones mapped, `ب` leads with
`بُرُوز`, the lips being the outermost locus. That was not arranged. `بُرُوز` glosses position on the
inner→outer axis, not closure, and nothing was tuned toward `ضرب`.

#### Verdict — 2026-09-25

The probe returned **`identical` on 5 of 5** qualifying comparisons: `حرب` = `حرج` = `حرد`,
`تبر` = `كبر`, `كود` = `كيد`. No `order-distinct`, no `distinct`. Option **(a) is v1.0.0**: the five
classical zones are mapped as one graded series on the inner→outer articulation axis —
`غَوْر`(حلق, 6) · `أَصْل`(أقصى اللسان, 2) · `وَسَط`(وسط اللسان, 3) · `طَرَف`(طرف اللسان, 13) ·
`بُرُوز`(شفتان, 4). Each row asserts position on that axis and nothing more; its `physical_basis` is
the uncontested locus.

Two costs are recorded rather than smoothed over.

**`حافة اللسان` has no home in a five-zone cut.** `ض` and `ل` are grouped with `طرف اللسان`, the
front-of-tongue region taken whole. A sixth zone would separate them, and adding one *because they
are awkward* would be choosing granularity by its result. It merges no profile: both letters already
carry a صفة no other letter has.

**`ح` and `ه` remain indistinguishable** — same `حلق` zone, same `رخاوة`/`همس`. Five zones cannot
separate them, and splitting `الحلق` into its three classical sub-positions to force it would be the
same refused move.

#### The residual is ACCEPTED — decided 2026-09-25, with its reason

The widening measured the cost rather than leaving it as a phrase: of **130** minimal pairs swept
across the three remaining classes, **117** are `distinct`, none is `order-distinct`, and all **13**
`identical` outcomes fall on `ح`/`ه` — **12** of them on divergent aṣl and therefore confirmed
collisions.

**The granularity is not reopened.** §D3 forbade it in advance, and *the prohibition is worth most
exactly here* — at the moment there is a good technical reason to override it. A sixth zone, or a
three-way split of `الحلق`, would take the number to zero in an afternoon, and the zero would mean
nothing: it would be the table adjusted until the measurement agreed with it, which is the failure
mode the entire change is built to make impossible. **Twelve collisions, published and counted, are
worth more than a zero obtained by tuning.** A rule that only binds when it is cheap is not a rule.

#### The one condition under which it IS reopened

Refusing forever would be its own kind of dogma, so the legitimate moment is named here rather than
left to judgement later. It is **the mandated measurement, never another probe**:

> **Reopening condition.** If, once `k / 40` is measured, the *profile collisions* are shown to
> **dominate** the failures — that is, if the witness roots that miss their frozen uses do so
> predominantly because another root shares their concept — then that evidence justifies a
> granularity change, and only then.

**The proof required, fixed here before the measurement so it cannot be assembled to fit:**

1. The per-root failure reasons are already committed for all 40 (§D9 step 3), so the classification
   is done on records that exist before this question is asked.
2. A failing root counts as a **collision failure** only when a *different* QAC root key composes to
   its exact realised primitives, at the same positions in the same order, and the two roots' aṣl
   diverge under §D13's set rule. That is the same `identical` criterion the probe uses — not a
   looser resemblance invented for the occasion.
3. «Dominate» means **strictly more than half** of the roots that fail. A plurality is not a
   mandate, and a threshold chosen after seeing the split would be the defect this clause exists to
   prevent.
4. The change that follows is a **lock version bump justified by a feature-level authority** — the
   granularity of the classical مخارج — carrying this clause as its reason and the measurement as
   its evidence. It is never a row edited to rescue a root.

If the failures are spread across other causes, the residual stays accepted and the number stands as
measured. **The probe cannot trigger this**: it already ran, its remedy is already v1.0.0, and
re-running it on a table it has no new information about would be looking for a second licence to do
what the first one did not license.

### D4 — The table: 21 features → 20 primitives, closed and capped

One row per (feature, primitive) in `physical_primitives.csv`. The vocabulary is closed at **20**,
because a rich table explains everything and therefore nothing.

> **AMENDED 2026-09-25.** The cap was **15** — the brief's «une quinzaine maximum» — and the صفات
> alone filled it exactly. §D13's probe proved a ṣifāt-only table cannot tell `ب` from `ج` from `د`,
> and §D3's pre-declared fallback brought the five مخرج zones in. The ceiling was raised by **exactly
> five**, and by five rather than to «enough»: the zones are a **closed classical partition**, not
> five free parameters, which is the whole reason raising the ceiling is not the same as removing it.
> The alternative — holding 15 by evicting five صفات primitives — was weighed and refused: the five
> most-covered are `ظُهور`(17) `جَرَيان`(15) `خَفاء`(10) `قَطْع`(8) `ضَخامة`(7), and the last two
> carry real signal.

**Every row declares a `status`, and the two statuses have different evidentiary duties.**

| `status` | What it claims | What it must carry |
|---|---|---|
| `attested` | a named authority states this quality-to-notion mapping | `authority` + real `pages`, checked against the authority index |
| `hypothesis` | **the project asserts it**; the *physical* fact is uncontested tajwīd | `physical_basis` (the tajwīd definition) + optional `support` citations, explicitly **not** offered as authority |

The validator accepts a row with real pages **or** an explicit `hypothesis`. It accepts neither an
empty field nor an approximate page.

**The table borrows no authority it does not have.** Ibn Jinnī, in «باب في إمساس الألفاظ أشباه
المعاني», states the principle and illustrates it on a handful of cases (`خَضِم`/`قَضِم`,
`قَدَّ`/`قَطَّ`); he never tabulates the صفات. Ḥasan ʿAbbās gives senses **per letter**, not per
صفة, and draws them partly from the words themselves. No page anywhere carries «شدة → قَطْع» as a
general rule, and no page carries «شفتان → بُرُوز» either. All 21 rows are therefore **a construction of this project**, and saying so
is not a weakness of the method — it is the condition under which `k / 40` means anything. A row
dressed in a borrowed citation would make the measurement unfalsifiable, because the failure could
always be blamed on the source.

| # | Physical feature (from `sifat`) | Primitive | Gloss | Letters | Expected `status` |
|---|---|---|---|---|---|
| 1 | `shadida` | قَطْع | clean break, abrupt stop | 8 | hypothesis |
| 2 | `mutawassita (bayniyya)` | تَمَهُّل | held flow, neither cut nor free | 5 | hypothesis |
| 3 | `rikhwa` | جَرَيان | continuous running | 15 | hypothesis |
| 4 | `majhura` | ظُهور | audible presence, manifestation | 17 | hypothesis |
| 5 | `mahmusa` | خَفاء | muted, light, effaced | 10 | hypothesis |
| 6 | `musta'liya` ∪ `mutbaqa` | ضَخامة | bulk, weight, volume | 7 | hypothesis |
| 7 | `qalqala` | ارتِداد | rebound | 5 | hypothesis |
| 8 | `safir` | حِدّة | thin, piercing sharpness | 3 | hypothesis |
| 9 | `takrir` | تَكرار | repetition | 1 | candidate `attested` |
| 10 | `tafashshi` | انتِشار | spreading, diffusion | 1 | hypothesis |
| 11 | `istitala` | امتِداد | extension in space | 1 | hypothesis |
| 12 | `inhiraf` | مَيْل | swerve, deviation | 1 | hypothesis |
| 13 | `lin` | لِين | softness, shocklessness | 2 | hypothesis |
| 14 | `madd` | مَدّ | prolongation | 2 | hypothesis |
| 15 | `ghunna` | رَنين | resonance, containment | 2 | hypothesis |
| 16 | `makhraj:halq` | غَوْر | inwardness, sounded before the mouth | 6 | hypothesis |
| 17 | `makhraj:aqsa_al_lisan` | أَصْل | rootedness, at the tongue's base | 2 | hypothesis |
| 18 | `makhraj:wasat_al_lisan` | وَسَط | centrality, between two ends | 3 | hypothesis |
| 19 | `makhraj:taraf_al_lisan` | طَرَف | edge, the point of contact | 13 | hypothesis |
| 20 | `makhraj:shafatan` | بُرُوز | protrusion, at the mouth's threshold | 4 | hypothesis |

Rows 16–20 are §D3's verdict, added when the probe closed. They are **one graded series on the
inner→outer articulation axis**, not five independent notions: each asserts position on that axis
and its `physical_basis` is the uncontested locus. Reading a *meaning* off a place — «the throat is
where deep things come from» — would be engine (1) again, with anatomy for a glossary.

Row 6 merges `استعلاء` and `إطباق` into one primitive, as the brief proposes («إطباق/استعلاء →
volume et lourdeur»). It is still the only merge, and with the five zone rows the table holds 21 rows over 21 features, mapping onto exactly 20 primitives.

The `status` column above is an **expectation, not a verdict**: a row becomes `attested` only when a
real page is found for it, and the curator is not to force any. Row 9 is flagged as a candidate
because `تكرير` is the one صفة whose tajwīd *definition* — a repeated tap of the tongue tip — is
itself the notion, so the gap between physical fact and primitive is narrowest there. Even it ships
as `hypothesis` unless a page actually says so.

Page ranges are not invented here. A draft of the previous change carried nine fabricated page
ranges, and that is the reason the lock checks its own citations — the `hypothesis` status exists
precisely so that no row is ever tempted into a citation it cannot produce.

**What the table produces, measured, before any root is read:**

| | ṣifāt only (superseded draft) | **v1.0.0, with the zones** |
|---|---|---|
| letters with at least one primitive | 28 / 28 | **28 / 28** — none is silent |
| primitives per letter | 1 (ء) · 2 (8) · 3 (13) · 4 (6) | 2 (ء) · 3 (8) · 4 (13) · 5 (6) |
| distinct letter profiles | 18 / 28 | **27 / 28** — only `ح`/`ه` |
| **distinct realised outputs** | **18 / 28** | **27 / 28** — only `ح`/`ه` |

**The last line is the one that matters, and the draft taught us that the hard way.** The two
quantities are not the same, and the design originally tracked only the first. A letter's *profile*
is everything the table gives it; its *realised* output is the handful the composition rule puts in
the sentence — and the probe compares realised primitives, not profiles. Under the zone table with a
realised window of **two**, profiles rise to 27 while realised pairs reach only **25**: the zone that
separates `و` from `ي` (`بُرُوز` 4 against `وَسَط` 3) ranks third and never reaches the sentence, and
`خ`/`غ` collapse the same way. Widening the window to three is what closes the gap (§D5).

*In its favour*: the table still **cannot** encode a per-letter gloss. It assigns each letter a
position on two independent axes — a ṣifāt profile and one of five articulation zones — and both are
declared over the vocabulary, never over a letter. `ح` and `ه` remain strictly indistinguishable to
it.

*Against it*: two roots differing only in `ح`/`ه` **get the same concept**. `ح-ر-ب` and a
hypothetical `ه-ر-ب`-shaped pair differing only there are one concept. This is a falsifiable
prediction of the design, narrowed from seven collision classes to one, and §8 records it as such
rather than leaving it to be discovered as a bug.

### D5 — Composition: positions are fixed, and rarity ranks within a position

**The positional rule, posed once and never adapted**: the first radical **opens** the action, the
second is its **body**, the third **concludes** it.

A letter contributes up to four primitives and a مفهوم is one sentence, so something must order
them. Selecting by *meaning* is forbidden — that is the core-first engine. The rule is therefore
computed from the table alone and is root-independent:

> Within a position, primitives are ordered by **ascending letter-coverage** — the rarer primitive
> first — ties broken by declaration order in the table. The sentence realises the **top three** per
> position; the rest are returned as `carried` and shown under the sentence, never dropped.

Rarity is the right ordering because a primitive carried by 17 of 28 letters (`ظُهور`) is nearly
free of information, while one carried by a single letter (`تَكرار`) is almost the letter's
signature. It also disposes of the `ظُهور`/`جَرَيان` dilution problem without a special case.

> **AMENDED 2026-09-25 — the window was two, and it was widened AFTER a probe came back negative.
> That is stated here rather than implied, because §D5's whole claim used to be «this rule was fixed
> before it was checked», and for the window that is no longer true.**
>
> What forced it: §D3's pre-declared fallback brought the five مخرج zones in, and nobody had
> anticipated how the zones would interact with the window. At two, the zone that separates `و` from
> `ي` ranks third and never reaches the sentence — so the concepts stayed identical although the
> profiles had become distinct (§D4). Three is the smallest window under which every zone reaches the
> output it was added to produce.
>
> Why this is not back-fitting, and where it is exposed. It **is** decided against the LETTER SHEET,
> not against any root: no witness root was read, no aṣl consulted, and the holdout is untouched — so
> the change cannot have been shaped by the thing it will be measured on. It **is** declared before
> the second probe runs, so the probe remains a real test. But it **is** a composition rule changed
> in response to a measurement, and «the rule was fixed before it was checked» now holds for the
> positions, the rarity order and the tie-break — and not for the window. A reader is owed that
> distinction rather than asked to trust the section's opening sentence.
>
> The cost is real and permanent: the مفهوم now realises **nine** primitives rather than six, so the
> sentence is longer and flatter. §D6's template is rewritten for nine.

**The positional rule, the rarity order and the tie-break were fixed before they were checked**, and
none of the three has moved. Applied to the one declared development case, under v1.0.0:

| position | letter | all primitives (rarity order) | realised |
|---|---|---|---|
| opens | ض | امتِداد(1) · ضَخامة(7) · **طَرَف(13)** · جَرَيان(15) · ظُهور(17) | **امتداد · ضخامة · طرف** |
| body | ر | تَكرار(1) · تَمَهُّل(5) · **طَرَف(13)** · ظُهور(17) | **تكرار · تمهل · طرف** |
| concludes | ب | **بُرُوز(4)** · ارتِداد(5) · قَطْع(8) · ظُهور(17) | **بروز · ارتداد · قطع** |

Under the superseded ṣifāt-only draft the realised pairs were `امتداد · ضخامة` / `تكرار · تمهل` /
`ارتداد · قطع`. Two changes, both consequences of the zones and neither arranged: every position
gains its articulation locus, and `ب` now **leads** with `بُرُوز` because the lips are rare (4
letters) where the tongue-tip is not (13). That is §D3's booked loss coming back — `ب`'s closure came
from the مخرج and the draft could not carry it — and it came back through the rarity rule, untouched,
rather than through anything aimed at `ضرب`.

The brief's hand gloss reads «ض force pleine, lourde, étendue + ر mouvement répété + ب contact net
qui se ferme et rebondit». The mechanism returns *extension and bulk*, *repetition, held*, *rebound
after a clean stop* — the same three readings, on all three letters, first try, from a rule written
before the check. That is the strongest evidence available that the objective layer carries the
signal this change is betting on.

**The rule has a structural bias, and it is predictable from the table alone.** Seven letters own a
صفة no other letter carries — `ر` (تكرير), `ش` (تفشي), `ض` (استطالة), `ل` (انحراف), and `ص`/`ز`/`س`
(صفير, 3 letters) — so rarity ordering makes them **always** lead with their own signature. The ten
profile-identical letters (§D4) necessarily lead with something generic. The method will therefore
read sharply on roots containing a signature letter and flatly on roots built from ordinary stops.

The zones **do not remove this bias and were not meant to**: they add a second rare-ish primitive to
the letters at the uncommon loci (`أَصْل` 2 · `وَسَط` 3 · `بُرُوز` 4), so `ق ك ج ش ي ب ف م و` now also
lead with something of their own, while the thirteen letters at `طَرَف` still do not. The split in
§D11 is unchanged and still declared on the seven **ṣifa**-signature letters, because that is the
line that was declared before the measurement and moving it now would be choosing the split after
seeing the table.

This is a bias to **measure**, not to correct: correcting it would mean weighting the order by
something other than the table, which is the first step back toward selecting by meaning. §D11
splits the metric along exactly this line.

### D6 — The مفهوم: one sentence, and nothing the primitives did not license

The output is a **مفهوم**, not a معنى: fixed, context-independent, single-sentence, Arabic,
nominal (مصدر-headed), no example, no Quranic citation, no hedging. The deterministic template is
the ground truth:

```
«{P1} {P2} {P3}، {P4} {P5} {P6}، حتَّى {P7} {P8} {P9}»
```

> **AMENDED 2026-09-25.** The template had six slots, two per position. §D5 widened the realised
> window to three, so it has **nine**. The six-slot exemplar this section used to carry —
> ضرب → «امتِدادٌ ضَخْمٌ، يَتَكَرَّرُ مُتَمَهِّلًا، حتَّى يَنقَطِعَ فَيَرتَدَّ» — no longer describes
> the output and is kept only as the record of the superseded draft. The nine-slot Arabic is **task
> 5.1's work and is deliberately not drafted here**: writing the sentence in the design, before the
> template module exists, is how a phrasing gets chosen for how well it reads on `ضرب`.
>
> The cost is stated where §D5 states it: the sentence is longer and flatter. A مفهوم carrying nine
> primitives is closer to a list than a sentence, and `طَرَف` — 13 of 28 letters — will appear in
> most of them. The containment rule below is unchanged and is what stops the extra length being
> filled with anything the primitives did not license.

> **AMENDED AGAIN 2026-09-25 — name the cost properly: the window bought COVERAGE with
> READABILITY, and the مفهوم of `ضرب` is now a list of nine nouns rather than a sentence.**
>
> This is the same notch §D5's reservation records, seen from the other end. §D5 is written from
> the METHOD's side — a composition rule that is no longer entirely pre-registered — and states the
> length as a consequence in one clause. Read from the OUTPUT's side it is the headline result:
>
>     «امتِدادٌ وضَخامةٌ وطَرَفٌ، ثُمَّ تَكرارٌ وتَمَهُّلٌ وطَرَفٌ، حتَّى بُرُوزٌ وارتِدادٌ وقَطْعٌ»
>
> Nine مصادر joined by و and two adverbs of sequence. It is grammatical Arabic and it is not a
> sentence anybody would call a مفهوم: it enumerates. §D5's exchange is therefore literal — every
> zone that reaches the reader was bought by a notion the reader has to hold, and the pair `و`/`ي`
> was separated at the cost of the output reading as an inventory.
>
> **The و is not the problem and is not up for removal.** Bare juxtaposition —
> «امتِدادٌ ضَخامةٌ» — is not an Arabic list; it reads as نعت, which would ASSERT that the ضخامة is
> the امتداد. The composition licenses no such claim: the two are co-ordinate primitives of one
> letter. The و costs a syllable and forbids an assertion, which is the right trade.
>
> **The window does NOT go back to two.** It moved once, after a measurement, and that exposure is
> recorded on the metric (§D11). Moving it back because the output reads poorly would be a second
> adjustment — this time made against the *appearance* of the result — and two adjustments, each
> individually defensible, is how a pre-registered rule becomes a tuned one. The number stays at
> three and the reservation stays attached to it.
>
> **What changes instead is the PRESENTATION, and only on screen.** §D6's deterministic chain
> remains the ground truth: it is what `compose()` returns, what `confront()` judges, what the
> record stores and what `k / 40` is measured on. The `/lexical` page (task 9.2) renders the same
> nine primitives as **three positional groups** — يفتَح / جسَد / يختِم — legible as three readings
> of three letters rather than as one long sentence. Nothing is dropped, reordered or re-worded;
> the screen stops presenting an enumeration as though it were a scholar's sentence. The single
> chain is still shown, verbatim, as what was recorded.

Compare the brief's target sentence, «إيقاعُ شيءٍ على شيءٍ إيقاعًا يُحدِثُ أثرًا». It is better
Arabic and it is **richer than the composition licenses**: neither *شيء على شيء* (two participants)
nor *أثر* (a trace left behind) is derivable from `امتداد · ضخامة · طرف · تكرار · تمهل · طرف · بروز · ارتداد · قطع`.
Those notions come from knowing what ضرب means. **The containment rule is exactly what forbids
closing that gap**, by template or by LLM. The engine's sentence will read more bluntly than a
scholar's, permanently, and that is the price of it being generated rather than recalled.

An **optional** LLM phrasing pass (`CONCEPT_LLM_PHRASING=0`, off) may only re-word the realised
primitives. It is containment-checked: every content word of its output must map to a primitive's
declared lemma set; a sentence introducing anything else is **rejected and not shown**, falling
back to the template. The repo has been burned twice by fluent-but-false generation (`/madar` is
quarantined for precisely this), so the LLM is a renderer with a veto over it, never an author.

**No silent fallback.** If a letter yields no primitive, the response carries
`partial: true` and `silent_letters: [...]`, the sentence omits that position rather than
improvising a filler, and the screen says which letter is silent and why. On today's table this
fires only for the alef case in D7 — the table leaves no letter of the 28 empty, and with the zones
every letter now carries at least two primitives (`ء` has `قَطْع` and `غَوْر`, where the draft left
it with one).

### D7 — Roots the rule does not cover, declared in advance

| Case | Count | Rule |
|---|---|---|
| Hamza carriers `أ ؤ ئ آ` in a root key | 139 letter positions, 138 roots | Folded to `ء` with `arabic_text.fold_carrier` and read from `ء`'s row. The stored root keeps its exact spelling; the fold is a lookup key only. |
| **Bare `ا`** in a root key (`اني`, `اول`, `هاء`, `هات`) | 4 roots | `ا` is not in the 28-letter sheet and has no مخرج of its own. It yields **no primitive**: the letter is reported silent and the concept is **partial**. |
| **Quadriliteral** roots | 43 of 1656 | The positional rule has three slots. It is **not** stretched to four — adapting the rule to the case is what the brief forbids. These roots return **no concept**, with a stated reason. A four-position rule is a future change, posed in advance like this one. |
| Weak radicals `و`/`ي` | — | **No exception.** They are consonants in the sheet (`جريان · مد · ظهور · لين`) and the table applies mechanically. 16 of the 40 witness roots carry one, so the choice is measured rather than assumed. |

### D8 — Blindness is enforced by the import graph

A protocol that says «generate first, then look» is kept by whoever runs it. An import boundary is
kept by the build.

`linguistics/lisan/concept/compose.py` and its feature/table modules **must not import**
`root_core_store`, `sense_selection`, `qlisan_data`, or anything reading `root_cores.json` /
`maqayis_asl.csv`. The confrontation lives in a separate module, `confront.py`, which imports the
concept *result* and the core store — never the reverse. `tests/test_import_direction.py` already
enforces one-way dependencies for the repo; this adds one edge to it.

The practical consequence: it is not possible to write a version of the composer that peeks at the
aṣl without deleting a test that says so.

### D9 — The confrontation protocol: the expectation is frozen before the concept exists

The order is load-bearing. If the attested uses are written down *after* reading the concept, "does
it cover them" is elastic — the list quietly shapes itself around what the sentence happens to say.

For each witness root, in this order:

1. **Enumerate the attested uses first.** From `morphology.json`'s occurrence list and the aṣl's
   `verbatim`, the curator writes the root's distinct Quranic senses into
   `data/references/concept_attestation.json` — `uses[]`, each with a gloss and one verse reference
   — and **commits that entry before the concept is generated**. This is the frozen expectation.
2. **Generate the concept**, blind, by D8.
3. **Judge coverage per use**: `covered` / `not_covered`, with one line of reason. Then the root's
   verdict is `covers_all` only if every `uses[]` entry is `covered`.

> **THE COVERAGE CRITERION, ADDED 2026-09-25 — written before any witness root's concept was read,
> and that ordering is the only thing that makes it a criterion rather than a description.**
>
> §D9 said «judge coverage» and did not say what coverage is. A judge with no written criterion
> applies one anyway, discovers it while judging, and drifts toward the answer that makes the number
> look like whatever they expected — in either direction. The criterion below was committed as its
> own step, before the first witness concept was generated, for the same reason the `uses[]` were.
>
> **A use is `covered` when a reader given ONLY the nine realised primitives, in their positional
> order, and told nothing whatever about the root, would recognise that use's notion as something
> the reading says.** Three tests, all necessary:
>
> 1. **Nothing imported.** Every content notion of the gloss traces to at least one realised
>    primitive. If the step from the primitives to the gloss needs a notion the nine do not carry,
>    the use is not covered. This is the containment discipline the phrasing veto already applies to
>    prose, applied to the judgement.
> 2. **Not merely inert.** The primitives must do more than fail to contradict the gloss. A reading
>    compatible with a use but silent about it is a MISS, not a pass — «does not contradict» is the
>    failure mode a nine-primitive reading is most prone to, because nine notions are compatible with
>    almost anything. At least one realised primitive must carry the gloss's CENTRAL notion.
> 3. **The direction holds.** The positional rule is part of the claim: opens → body → concludes. A
>    gloss whose notion requires the root to end in an opening-out is not covered by a reading whose
>    third position is `قَطْع`, however well the first two fit.
>
> **The prohibition that makes it work: the judge may not use what they know the root means to build
> the bridge.** Knowing that `قوم` is standing makes `أَصْل · ظُهور` look like a foundation. It only
> looks like one to someone who already has the answer, and that is precisely the back-fitting the
> whole design exists to exclude. Where the bridge needs the root's meaning, the verdict is
> `not_covered`.
>
> **A miss names its class, in the first word of its `reason`.** Four, and they are exhaustive by
> construction — a miss fails test 1, test 2 or test 3, or the reading is not about this root at all:
>
> | class | what failed |
> |---|---|
> | `imported` | test 1 — the gloss needs a notion absent from the nine |
> | `inert` | test 2 — the nine are compatible with the gloss and say nothing about it |
> | `direction` | test 3 — the positional order contradicts the gloss |
> | `collision` | another root with a divergent aṣl composes to these exact nine, so nothing in this reading is about this root |
>
> The classes exist to make §D3's reopening condition measurable. That condition requires collision
> failures to be **strictly more than half** of all failing roots, «classified on the per-root
> reasons already committed» — which is only checkable if the reasons were classified when they were
> written, against a vocabulary fixed beforehand. This is that vocabulary.
>
> **`collision` is computed, and it is computed AFTER the verdicts are written.** Whether another
> QAC root composes to the same nine realised primitives is a mechanical fact about the table, not a
> judgement, and it is recorded per root as `collision_with`. It is derived after the judging pass so
> that knowing a root collides cannot soften or harden the reading of its uses — the criterion above
> never mentions collision, and a use that fails does so on tests 1–3 before anyone asks why.
4. **Record disagreement as a result.** A root whose concept misses its aṣl stays recorded as a
   miss. It is **never** a reason to add a row to the table, change a primitive's gloss, or
   re-order anything. The table changes only through a lock version justified by a feature-level
   authority — never by a root.

The confrontation view shows, side by side: the generated مفهوم · Ibn Fāris' aṣl `verbatim` ·
the root's occurrences · the recorded verdict · and, for comparison, the core-first engine's
reading of the same root.

**`ضرب` is confronted too, and its coverage is published — but it is not a gate.** It was used to
verify the composition rule (§D5), so measuring coverage on it proves nothing: the rule and the case
were checked against each other. Its five brief-named uses (الضرب باليد · الضرب في الأرض · ضرب
الأمثال · ضرب الخيمة · «وضُرِبت عليهم الذلة») are recorded and judged like any other root's, and the
result is expected to be **partial** — `امتداد · ضخامة · تكرار · تمهل · ارتداد · قطع` does not reach
*ضرب الأمثال*. A published partial on the flagship case is worth more than its absence, which would
read as a quiet pass.

### D10 — The witness set, drawn now

Drawn once, with the seed below, before the table was written. It is in the repo as
`data/references/concept_witness_set.json`, and a test re-runs the draw and fails if the file has
moved.

- **Frame**: triliteral QAC roots (1613) ∩ a Maqāyīs `has_asl` row joined through
  `arabic_text.normalize_root` (1149) ∩ ≥ 20 Quranic occurrences, minus the 5 roots already curated
  in `root_cores.json` (`خبث خير رحم ظلم كفر`) and minus the declared development case `ضرب`.
  **280 roots**, in two strata: 205 with 20–99 occurrences, 75 with 100+.
- **Draw**: `random.Random(20260925).sample(...)`, proportional — **29** from the lower stratum,
  **11** from the upper. Seed = today's date, chosen before drawing; drawn once, not re-rolled.

> أبو · أثم · بعث · بني · توب · ثني · خشي · خلص · خوف · دخل · ذوق · رجع · رود · زيد · سرف · سوع ·
> صدر · طير · عبد · عرب · عقل · غرق · غفل · فقه · فلح · قرب · قسط · قعد · قمر · قول · قوم · لسن ·
> مسك · نجو · نذر · نصر · نكر · هجر · وثق · وجه

Structure of the draw, for the record: 16 of the 40 carry a weak radical (`و`/`ي`), 2 carry a hamza
carrier (`أبو`, `أثم`), none is quadriliteral, none carries a bare alef. The weak-radical share is
high and was not adjusted — D7's "no exception" rule is therefore measured on 40 % of the set.

**The holdout discipline**: the *identity* of these roots is public (it has to be — you must know
what to exclude). What is never done before the table is locked: reading their aṣl, generating
their concepts, or checking anything against them. The table is written against the feature
vocabulary, not against roots.

### D11 — One metric

> **k / 40** — the number of witness roots whose generated concept covers **all** the uses frozen
> for it in step 1.

Not a per-letter match rate, not an average coverage, not partial credit, not a figure computed
over roots that happened to work. The per-root verdicts are published alongside so the number can
be audited, and `scripts/validate_concept_datasets.py` refuses to print the metric if any witness
root's `uses[]` was committed *after* its concept was recorded.

**One split is reported with it**, because §D5's bias predicts it: `k / 40` is broken down by
whether the root contains a **signature letter** (`ر ش ض ل ص ز س`) or not. If the method works only
on roots carrying one, the headline number hides that, and the split is what exposes it. The split
is declared here, before the measurement, so it cannot be chosen afterwards for being flattering.

**Audit is possible, not performed.** There is no second judge and this note does not pretend to
one: the curator writes the verdicts. What is committed — the frozen `uses[]`, the generated
concept, the verdict and its reason, for all 40 — is everything a reader who clones the repo needs
to redo the judgement themselves and disagree.

**The reading carries a reservation, and the reservation travels with the NUMBER.**

> `k / 40` was produced by a composition rule that is **not entirely pre-registered**. The realised
> window — how many primitives per position reach the sentence — was set to **two** in advance and
> widened to **three** *after* a measurement came back negative, on `ضرب`, the declared development
> case. The positions, the rarity ordering and the tie-break were fixed before they were checked and
> have not moved; **the window was not**.

This is stated **here, on the metric**, and not only in §D5 where the change happened, because a
reader meeting `k / 40` is entitled to know how it was produced without going to look. §D5 explains
*why* the window moved; this clause says *what that costs the number*, at the moment the number is
read.

What contains the exposure, and what does not:

- **The holdout is intact.** No witness root was read, composed or consulted when the window
  changed. Whatever `k / 40` turns out to be, it was not obtained by tuning against the set it
  measures.
- **`ضرب` is a declared development case**, excluded from `k` for exactly this reason (§D9) — it was
  used to verify the composition rule, so a coverage figure on it proves nothing. That exclusion was
  declared before the window moved and is what keeps the adjustment out of the measured set.
- **It is still an adjustment made on a case.** One free parameter of the composition rule was set
  by looking at an outcome. The set it was set on is outside the measurement, which bounds the
  damage; it does not erase it. A reader who discounts `k / 40` on that ground is reading correctly,
  and the number is published with the discount visible rather than without it.

**Every surface that prints `k / 40` SHALL print this reservation with it** — the validator's metric
output, the documentation, and any summary of the result. A caveat a reader has to go and find is a
caveat the publisher has kept.

### D12 — Coexistence: a new route, new modules, nothing modified

`POST /lisan/concept` is mounted next to the untouched `POST /lisan/analyze`, and `/lexical` shows
both readings for the same root. A mode flag on the existing route was rejected: it changes a
shipped contract, and the brief forbids touching the current engine.

New code lives in a new package `linguistics/lisan/concept/` — `features.py` (sheet → feature
vocabulary), `primitives.py` (the frozen table), `compose.py` (positions, rarity order, template),
`phrasing.py` (optional LLM + containment), `confront.py` (the only module that may read the aṣl).
`api/routers/lisan.py` gains one route; `api/main.py` mounts it; `served-surface`'s route list gains
one entry.

### D13 — The collision probe runs before any curation, and can redirect the design

§D4's profile collision was first written as a prediction to confirm afterwards. That was the wrong
place for it: it is an hour of work, it needs no curated data, and it decides whether curating 40
roots is worth doing at all. It is therefore a **gate**, run as soon as a minimal generation path
exists and **before** a single witness root is touched.

**Method.** Take real QAC roots differing by exactly one profile-identical letter, generate their
concepts, and compare against the aṣl already on disk in `maqayis_asl.csv` — no curation, no witness
root, no `root_cores.json` entry required. The probe compares **realised primitives**, not
sentences, so §5's template, the LLM pass, the route and the page are all unnecessary to run it.

#### The comparison criterion, fixed before the probe runs

"Identical" has to mean something precise or the verdict is elastic. Three outcomes, and only three:

| Outcome | Definition |
|---|---|
| **identical** | the same multiset of realised primitives, at the same positions, in the same order |
| **order-distinct** | the same primitives, at different positions or in a different order |
| **distinct** | different realised primitives |

**`order-distinct` counts as a partial collision and is reported as one.** It is not filed on the
reassuring side: two roots whose concepts are built from one set of primitives shuffled differ by
the composition rule alone, not by anything the table knows about their letters.

#### Divergence on the aṣl side

A probe root may carry several aṣl. The pair counts as **aṣl-divergent** only when **no** aṣl of one
root matches **any** aṣl of the other. Taking the whole set rather than a primary makes the test
*harder* to satisfy, so the rule cannot inflate a collision verdict.

This rule is needed, not hypothetical: of the five roots in the two classes confirmed by review,
`حرب` carries 3 aṣl, `حرد` 3 and `تبر` 2.

**Rejected alternates, and why the sample is not changed.** Single-aṣl minimal pairs exist —
`بدل`/`جدل` (40 · 27) for `ب`/`ج`/`د`, though only as a pair where `حرب`/`حرج`/`حرد` is a three-way
test, and `ستر`/`سكر` (3 · 6) for `ت`/`ك`, at a tenth of the volume. They are cleaner, and they are
**not** taken. The decisive reason is not the cost: **changing the sample after seeing the
complication is choosing roots by looking at the data**, which is the one thing the whole protocol
exists to prevent. A probe whose roots were swapped once the awkwardness appeared would carry the
same defect as a table edited to make a root work. The set rule handles the complication without
touching the sample, and it handles it in the conservative direction.

#### The probe roots

| Collision class | Probe roots | Occurrences | Attested aṣl |
|---|---|---|---|
| `ب`/`ج`/`د` | `حرب` · `حرج` · `حرد` | 11 · 11 · 1 | 3 ‖ 1 ‖ 3 — السلب/دويبة/بعض المجالس ‖ تجمع الشيء وضيقه ‖ القصد/الغضب/التنحي |
| `ت`/`ك` | `تبر` · `كبر` | 4 · 153 | 2 ‖ 1 — الهلاك/جوهر من جواهر الأرض ‖ خلاف الصغر |
| `و`/`ي` | `كود` · `كيد` | 24 · 29 | 1 ‖ 1 — التماس شيء ببعض العناء ‖ معالجة لشيء بشدة |

`كود`/`كيد` was confirmed by review on exactly the right ground, and the data bears it out: one aṣl
each, cleanly separated, balanced volumes. The alternates were rejected — `صور` because Ibn Fāris
declines to unify it at all («كلمات كثيرة متباينة الأصول»), and `دون`/`دين` because `دين`'s aṣl, while
single, is a contentless formula («أصل واحد إليه يرجع فروعه كلها») that announces an aṣl without ever
stating it. Neither offers anything to compare against.

> The review's original third pair, `روح`/`ريح`, was withdrawn: `ريح` is **not a QAC root key** — it
> is a derivative of `ر-و-ح` — so the pair had nothing to compare.

#### Probe result — run 1, 2026-09-25, on the ṣifāt-only draft

| Class | Comparison | Outcome |
|---|---|---|
| ب/ج/د | حرب ∼ حرج · حرب ∼ حرد · حرج ∼ حرد | `identical` ×3 |
| ت/ك | تبر ∼ كبر | `identical` |
| و/ي | كود ∼ كيد | `identical` |

**5 of 5 qualifying comparisons, 7 roots over 3 classes.** No `order-distinct`, no `distinct`. All
three classes qualified, so the probe ran at full declared size and no emptied-class rule fired.

The verdict was not a surprise and was not allowed to be one: §D4 had predicted 18 profiles for 28
letters and named the seven collision groups. Independent confirmation, run before accepting the
result: the composer reproduces exactly those seven groups (`بجد` `تك` `ثحفه` `طق` `ظغ` `من` `وي`),
so the collision is the table's structure and not a defect in the composition.

**The pre-declared consequence was applied, and nothing else was.** The probe was **not** widened to
`ط`/`ق`, `ث`/`ح`/`ف`/`ه` or `م`/`ن` — widening requires a clean sweep and this was its opposite. No
witness root was touched, no `uses[]` frozen, no concept generated for the holdout. §D3's option (a)
became v1.0.0. The record, including the superseded draft's digest, is
`data/references/concept_collision_probe.json`.

#### Run 2 — on v1.0.0

The rebuilt table is put through the same three classes, the same criterion and the same
qualification table. The sample is unchanged: swapping probe roots between runs would be choosing
roots by looking at a result, which is exactly what §D13 exists to prevent. The run-1 record is kept
alongside rather than overwritten — it is the reason run 2 exists, and deleting it would leave the
table's replacement unexplained.

#### The qualification table is published before the probe runs

For each pair in the three classes, the aṣl sets of both roots and a **qualifying** /
**non-qualifying** verdict under the set rule above are written out and **committed before a single
concept is composed**.

Without it, a class turning out to hold one usable pair — or none — would be discovered after the
comparison, when the real size of the test can no longer be stated honestly. Publishing it first
fixes the denominator before anyone knows the numerator.

| Class | Roots | Comparisons |
|---|---|---|
| `ب`/`ج`/`د` | `حرب` · `حرج` · `حرد` | 3, correlated — حرب∼حرج, حرب∼حرد, حرج∼حرد |
| `ت`/`ك` | `تبر` · `كبر` | 1 |
| `و`/`ي` | `كود` · `كيد` | 1 |

**The test is counted in roots, never in pairs.** `حرب∼حرج`, `حرب∼حرد` and `حرج∼حرد` share their
roots: three correlated comparisons over three roots, not three independent tests. Reporting "five
pairs" would inflate the probe's own `n` by counting the same evidence twice. The size of this probe
is **7 roots over 3 classes** (3 + 2 + 2), and the report SHALL state it that way.

Two of the three classes rest on a **single** comparison each, so a non-qualifying verdict empties
them immediately. That fragility is stated here rather than discovered at the table.

**Decision rule for an emptied class, fixed now — before the qualification table is seen:**

- **`ب`/`ج`/`د` is the carrying class.** If it qualifies, the probe remains valid even if both
  others fall. Run with what qualifies, report the reduced size, and replace nothing.
- **If `ب`/`ج`/`د` falls to zero, the probe can no longer decide.** Stop and report. Only then are
  the alternates examined — and the report SHALL say explicitly that the choice was made after
  observing an **empty sample**. That is not the same thing as choosing after seeing a *result*, but
  it must be visible to anyone re-reading, who is owed the distinction rather than asked to trust it.
- **In every case, no root is added to compensate a fallen class.**

#### Widening is conditional, never automatic

Run the three classes and stop there.

- **If even one class returns `identical` where the aṣl diverge** — the verdict is in. **Do not
  widen.** Report, and §D3's option (a), mapping the five classical مخرج zones, becomes **v1.0.0**
  of the table rather than a later lock bump. Steps 1–3 of the migration are redone before anything
  else proceeds.
- **If all three discriminate** — an outcome the review does not expect — **only then** extend to
  the four remaining classes (`ط`/`ق`, `ث`/`ح`/`ف`/`ه`, `م`/`ن`, and only those) before concluding
  anything.
- **`ظ`/`غ` stays out of the probe in every case.** Its only real minimal pair is `ظلم`/`غلم`, and
  `ظلم` is one of the five roots already curated in `root_cores.json` — contaminated, and therefore
  useless as evidence either way.

Probe roots are **not** witness roots and SHALL NOT enter the witness set; none of the seven above
is in it.

## Risks / Trade-offs

- **The table is too coarse to separate 10 of the 28 letters** → No longer left to the witness
  results: §D13 probes it directly, before curation, and can promote D3's option (a) to v1. The
  answer is never a per-letter patch.
- **`ظُهور` (17/28) and `جَرَيان` (15/28) are near-free of information** → Rarity ordering (D5)
  demotes them out of the realised sentence automatically. If they still dilute, demoting them to
  non-realised modifiers is a table-level change with a stated reason, in a lock bump.
- **The generated sentence reads bluntly next to a scholar's** → Permanent and accepted (D6). The
  containment check is what guarantees the bluntness is honest rather than a failure to try.
- **k/40 may be low — possibly very low** → That is a result. The change is worth shipping at k=8
  if the 8 are real, and is worth *not* shipping at k=35 obtained by editing the table. The
  protocol exists to make the first outcome publishable and the second impossible.
- **The curator judges coverage on roots they can read** → Mitigated by freezing `uses[]` before
  generation (D9) and by publishing everything needed to redo the judgement (D11). Not eliminated,
  and deliberately not dressed up: there is no second judge, the note claims audit*ability*, not
  audit.
- **Most of the 15 rows are the project's own hypothesis, not received scholarship** → Declared per
  row by `status` (D4) rather than smoothed over by a borrowed citation. The exposure is real and it
  is what `k / 40` is for: a hypothesis that cannot be blamed on a source is one the measurement can
  actually falsify.
- **Two engines on one page doubles the UI surface** → Accepted for the duration of the comparison.
  The change that ends the comparison removes one of them; this one does not pre-judge which.
- **A 15-primitive vocabulary is itself a curated interpretive act** → True, and the method's real
  exposure. The defences are that it is written against the *feature list* rather than against
  roots, that it is frozen by digest before the first root, that every row is sourced, and that the
  witness set can falsify it. It is not claimed to be objective — only fixed, cited, and testable.

## Migration Plan

Additive throughout; nothing to migrate.

1. Datasets + `paths.py` / `loaders.py` / `manifest.py` entries, and the validator, **before** any
   engine code — the table must be locked before the first root is composed. Every row carries a
   `status`; no row waits on a citation it cannot produce.
2. Witness set file + its reproducibility test, committed in the same step.
3. The **minimal generation path only** — features, table store, rarity ordering. Not the sentence
   template, not the LLM, not the route, not the page: the probe compares realised primitives.
4. **§D13's collision probe — HARD STOP.** Run it, report it, and wait. If it confirms the
   collision, the table is rebuilt as v1.0.0 with the five مخرج zones and steps 1–3 are redone
   before anything below starts.
5. The rest of `linguistics/lisan/concept/` and its tests; `ضرب` is the regression case.
6. Route, then frontend panel.
7. Confrontation records filled root by root, each `uses[]` committed before its concept; then
   `k / 40` with its signature-letter split.

**Rollback** is one `include_router` line, on the repo's existing quarantine convention: the route
stops being mounted, the code stays imported and type-checked, and the datasets stay valid. The
core-first engine is untouched at every step, so no rollback path runs through it.

## Resolved by review — 2026-09-25

The §0 gate is lifted. The four questions this note opened are answered, and the answers are folded
into the decisions above rather than left here.

1. **Citations (§D4)** — *the constraint changed, so the blocker is gone.* Ibn Jinnī states the
   principle and illustrates it on a handful of cases; he never tabulates the صفات. Ḥasan ʿAbbās
   gives senses per **letter**, not per صفة, and draws them partly from the words themselves. No
   page carries «شدة → قَطْع» as a general rule. The table is therefore a construction of this
   project, declared row by row through `status` — `attested` demands real pages, `hypothesis` owns
   the claim and may cite support but never authority. Neither an empty field nor an approximate
   page is accepted.
2. **`ضرب` (§D9)** — a **regression** case pinning the composition, not a coverage gate: it was used
   to verify the rule, so coverage measured on it proves nothing. Its coverage is published anyway,
   expected partial.
3. **Attestation records (§D9)** — `data/references/concept_attestation.json`, committed. `tests/`
   is git-ignored, which would make the metric unverifiable to anyone cloning the repo.
4. **A second judge (§D11)** — none, and no invented panel. Everything needed to redo the judgement
   is committed; the claim is that an audit is *possible*, not that one was performed.

Two amendments were added to the design: §D13 (the collision probe, promoted from a post-hoc
prediction to a gate before curation) and the bias split in §D11 (`k / 40` broken down by signature
letter, declared before the measurement).

## Resolved by review — second pass

5. **The `و`/`ي` probe pair (§D13)** — `كود`/`كيد` confirmed, on the ground that each carries a
   single, clearly separated aṣl with balanced volumes. Verified against `maqayis_asl.csv`:
   `asl_count=1` for both. The alternates are rejected, one of them for a stronger reason than the
   review gave — `صور` because Ibn Fāris explicitly declines to unify it, and `دون`/`دين` not for
   carrying several aṣl (`دين` carries one) but because that one aṣl is a contentless formula.
6. **Widening the probe (§D13)** — conditional, never automatic. Three classes, then stop; a single
   `identical` verdict ends it and promotes the مخرج zones to v1; only a clean sweep licenses the
   four remaining classes. `ظ`/`غ` is excluded in every case, its sole pair running through the
   already-curated `ظلم`.
7. **The comparison criterion (§D13)** — fixed before execution: `identical` / `order-distinct` /
   `distinct`, with `order-distinct` counted and reported as a partial collision rather than filed
   as a pass.
8. **The multi-aṣl probe roots (§D13)** — **no swap.** `حرب`/`حرج`/`حرد` and `تبر`/`كبر` stand.
   The set rule is sufficient and errs in the conservative direction, but the decisive reason is
   that changing the sample after the complication appeared would be selecting roots by looking at
   the data — the one move the protocol exists to prevent. The cleaner alternates stay recorded in
   §D13 as rejected, with that reason.
9. **A qualification table is published before execution (§D13)** — every pair's aṣl sets and its
   qualifying / non-qualifying verdict, committed before a concept is composed, so the test's real
   size is fixed before its result is known. A class falling to zero qualifying pairs stops the work
   for a reviewer decision.

## Resolved by review — third pass, 2026-09-25 (after probe run 1)

10. **§D13's probe fired at full strength** — `identical` on 5 of 5. §D3's option (a) was applied as
    pre-declared: the five classical مخرج zones are mapped and become table **v1.0.0**, not a later
    lock bump. The superseded ṣifāt-only draft's digest is recorded in the lock's `history[0]`.
11. **The cap moved 15 → 20 (§D4)** — by exactly five, to admit a closed classical partition rather
    than five free parameters. Evicting five صفات primitives to hold 15 was weighed and refused:
    two of the five most-covered carry real signal.
12. **The realised window moved 2 → 3 (§D5), and this one is an honest exposure.** It was widened
    *after* a measurement, so «the rule was fixed before it was checked» no longer covers the window
    — only the positions, the rarity order and the tie-break. It was decided against the letter
    sheet with no root read and the holdout untouched, and it is declared before run 2. The
    distinction between «not shaped by the thing it is measured on» and «fixed in advance» is real,
    and the reader is owed it rather than asked to trust the older sentence.
13. **`ح`/`ه` stay merged, and `حافة اللسان` is grouped with `طرف اللسان`** — both declared costs of
    a five-zone cut. Adding a sixth zone, or splitting `الحلق`, would be choosing granularity by its
    result.

## Open Questions

None blocking. The design is settled through §4 of `tasks.md` for the rebuilt table; the next
decision point is probe run 2's verdict on v1.0.0.
