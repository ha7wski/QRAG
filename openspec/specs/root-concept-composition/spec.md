# root-concept-composition Specification

## Purpose

Define how a root's مفهوم is composed from its letters' physics alone — the invariant positional
rule, the rarity ordering and its realised window, non-triliteral and hamza/alef handling,
partial concepts, the output contract, LLM containment, `POST /lisan/concept`, and how
`/lexical` presents the result.

**The engine this describes is a CLOSED EXPERIMENT** (`k / 40 = 0`, see
`concept-attestation-protocol`). The route stays mounted and the panel stays on screen,
labelled as closed; the composition rule is not to be retuned.

## Requirements

### Requirement: The concept is generated blind, and blindness is enforced by the import graph

The modules that extract features, read the primitive table and compose the concept SHALL NOT
import, directly or transitively, any module that reads `root_cores.json`, `maqayis_asl.csv`,
`letter_senses.csv` or `semantic_axes.json`. The confrontation module SHALL import the concept
result; the composer SHALL NOT import the confrontation module.

A procedural rule — "generate first, then look" — is kept by whoever runs it. This requirement makes
peeking impossible without deleting the test that forbids it.

#### Scenario: The composer cannot reach the attested core

- **WHEN** the import graph of `linguistics/lisan/concept/compose.py` is resolved transitively
- **THEN** it SHALL NOT contain `root_core_store`, `sense_selection`, `qlisan_data`, or any reader
  of `root_cores.json` or `maqayis_asl.csv`
- **AND** `tests/test_import_direction.py` SHALL assert this edge

#### Scenario: The same root always yields the same concept

- **WHEN** the same root is composed twice in two fresh processes
- **THEN** the مفهوم, its realised primitives and their order SHALL be byte-identical

### Requirement: Positions are fixed in advance and never adapted to a root

The positional rule SHALL be: the **first** radical opens the action, the **second** is its body,
the **third** concludes it. It SHALL be documented before the first root is composed and SHALL NOT
be varied, extended or overridden for any root.

#### Scenario: The rule is applied uniformly

- **WHEN** any triliteral root is composed
- **THEN** its three radicals SHALL fill the opening, body and closing slots in that order
- **AND** no code path SHALL exist that assigns them otherwise

### Requirement: Within a position, primitives are ordered by rarity, and the top three are realised

Primitives of a letter SHALL be ordered by **ascending letter-coverage** — the primitive carried by
the fewest letters first — with ties broken by declaration order in the table. The sentence SHALL
realise the **top three** per position. The remainder SHALL be returned as `carried` and displayed
under the sentence; they SHALL NOT be discarded.

The window was **two** while the table mapped ṣifāt alone, and it was widened to three **after** a
measurement: with the مخرج zones mapped, the zone separating `و` from `ي` ranks third and at a
window of two never reached the output, so the profiles became distinct while the concepts stayed
identical. The positional rule, the rarity order and the tie-break were fixed before they were
checked and have not moved; **the window has**, and any statement of this requirement SHALL say so
rather than imply the whole rule was fixed in advance. The window SHALL NOT be varied per root, per
position or per outcome — a window that adapts to make a position discriminating is a composition
rule tuned on its own result.

The ordering SHALL be computed from the table alone. It SHALL NOT consult the root, its meaning, its
aṣl or its occurrences.

The rule has a known structural consequence: the seven letters owning a صفة no other letter carries
— `ر` (تكرير), `ش` (تفشي), `ض` (استطالة), `ل` (انحراف), `ص`/`ز`/`س` (صفير) — always lead with their
own signature, while profile-identical letters always lead with something generic. This SHALL be
measured by the metric's split and SHALL NOT be corrected by weighting the order on anything other
than the table, which would be the first step back toward selecting by meaning.

#### Scenario: A near-universal primitive is demoted automatically

- **WHEN** a letter carries both `ظُهور` (17 of 28 letters) and a primitive carried by one letter
- **THEN** the rarer primitive SHALL rank first
- **AND** `ظُهور` SHALL fall out of the realised set unless the letter has fewer than four primitives

#### Scenario: The signature bias is not corrected away

- **WHEN** roots built only from profile-identical letters are composed
- **THEN** their realised primitives SHALL still come from the rarity order alone
- **AND** no weighting, boost or exception SHALL be applied to compensate for the flatter reading

#### Scenario: The acceptance case composes as recorded

- **WHEN** `ضرب` is composed
- **THEN** the realised triples SHALL be `امتِداد · ضَخامة · طَرَف` for `ض`, `تَكرار · تَمَهُّل · طَرَف`
  for `ر`, and `بُرُوز · ارتِداد · قَطْع` for `ب`
- **AND** this SHALL be a permanent regression test
- **AND** the superseded ṣifāt-only values (`امتِداد · ضَخامة` / `تَكرار · تَمَهُّل` / `ارتِداد · قَطْع`)
  SHALL be recorded beside them, so the change is readable as a consequence of the zones rather than
  as a quiet edit to a pinned case

### Requirement: The output is a مفهوم — one sentence, and nothing the primitives did not license

The response SHALL carry a single Arabic sentence, fixed and context-independent, containing no
example, no Quranic citation and no hedging. The deterministic template SHALL be the ground truth.

Where an optional LLM phrasing pass is enabled, it SHALL only re-word the realised primitives. Its
output SHALL be **containment-checked**: every content word SHALL map to a declared lemma of a
realised primitive. A phrasing that introduces any other notion SHALL be rejected and SHALL NOT be
shown; the template output SHALL be used instead. The pass SHALL be off by default.

#### Scenario: An invented notion is rejected, not displayed

- **WHEN** the phrasing pass returns a sentence containing a notion absent from the realised
  primitives
- **THEN** the sentence SHALL be rejected
- **AND** the deterministic template's sentence SHALL be returned
- **AND** the rejection SHALL be recorded in the response

#### Scenario: The engine does not reach the brief's richer gloss, and does not pretend to

- **WHEN** `ضرب`'s concept is rendered
- **THEN** it SHALL NOT assert a second participant or a trace left behind, neither being derivable
  from its nine realised primitives
- **AND** no configuration SHALL make it assert them

### Requirement: A silent letter makes the concept partial, and the screen says so

If a letter yields no primitive, the response SHALL carry `partial: true` and name the letter in
`silent_letters`. The sentence SHALL omit that position rather than substitute a filler, and the
`/lexical` page SHALL display which letter is silent and why.

There SHALL be no fallback to a default primitive, and no flag restoring one.

#### Scenario: A bare alef in a root key is reported, not invented

- **WHEN** a root whose key carries a bare `ا` (`اني`, `اول`, `هاء`, `هات`) is composed
- **THEN** that position SHALL yield no primitive
- **AND** the response SHALL be `partial: true` naming `ا`
- **AND** the page SHALL state that the letter has no مخرج of its own in the sheet

#### Scenario: A hamza carrier is folded, not dropped

- **WHEN** a root key carries `أ`, `ؤ`, `ئ` or `آ`
- **THEN** it SHALL resolve to `ء` for the sheet lookup only, through an explicit carrier→hamza map
- **AND** the root's stored spelling SHALL be unchanged
- **AND** the concept SHALL NOT be partial on that account
- **AND** `arabic_text.fold_carrier` SHALL NOT be used for this: it folds toward the CARRIER
  (`أ`→`ا`, `ؤ`→`و`, `ئ`→`ي`), deleting the hamza the sheet is keyed on, so it would resolve all 139
  seat positions to a letter absent from the 28-letter sheet and return them as the documented
  silent case with a plausible-looking reason instead of raising

### Requirement: Roots the positional rule does not cover return no concept

A root that is not triliteral SHALL return no concept, with a stated reason. The three-slot rule
SHALL NOT be stretched to four slots for the 43 quadriliteral roots: adapting the rule to the case
is precisely what this design forbids. A four-position rule is a future change, posed in advance.

#### Scenario: A quadriliteral root is refused explicitly

- **WHEN** `برزخ` or another quadriliteral root is requested
- **THEN** the response SHALL carry no مفهوم
- **AND** it SHALL state that the composition rule covers three positions only
- **AND** the page SHALL show that statement rather than an empty panel

### Requirement: The page presents the مفهوم as three positional groups

Widening the realised window to three bought discrimination with readability: nine مصادر joined by
و is grammatical Arabic that enumerates rather than states. The window SHALL NOT be narrowed back to
recover the reading — it moved once after a measurement, and moving it a second time against the
*appearance* of the output is how a pre-registered rule becomes a tuned one.

The presentation SHALL change instead, and only the presentation. The `/lexical` page SHALL render
the realised primitives as **three positional groups** — opens / body / concludes — each legible as
one letter's reading. The deterministic chain SHALL remain the ground truth: it is what the composer
returns, what the confrontation judges, what the record stores and what `k / 40` is measured on, and
the page SHALL also show it verbatim as the thing that was recorded. No primitive SHALL be dropped,
reordered or re-worded for display.

#### Scenario: The nine primitives arrive grouped, and the chain is still shown

- **WHEN** a triliteral concept is displayed
- **THEN** the page SHALL show three groups, each naming its radical and its position
- **AND** the recorded sentence SHALL be shown verbatim alongside them
- **AND** the union of the groups SHALL be exactly the realised primitives, in composition order

#### Scenario: Presentation never reaches the record

- **WHEN** the page groups a concept
- **THEN** the stored `sentence` and `realised_primitives` SHALL be byte-identical to the composer's
- **AND** no grouping SHALL exist in the API response that the composer did not produce

### Requirement: The `/lexical` page distinguishes مفهوم from معنى

The page SHALL state, in Arabic and in its own words rather than in a value returned by the API,
that the مفهوم is fixed and that the معنى depends on context. This distinction is the point of the
approach and SHALL be visible without interaction.

#### Scenario: The distinction is on screen

- **WHEN** a concept is displayed
- **THEN** the page SHALL carry the fixed-concept / contextual-meaning statement
- **AND** a frontend test SHALL assert its presence

### Requirement: `POST /lisan/concept` is additive and `POST /lisan/analyze` is untouched

The new route SHALL be mounted alongside the existing one. `POST /lisan/analyze`'s request and
response contract SHALL be unchanged by this change, and no module under `linguistics/lisan/`
existing before this change SHALL be modified.

The response SHALL carry the مفهوم, the per-letter physical profile, the realised and carried
primitives per position, `partial`, `silent_letters`, the table's lock `version`, and any phrasing
rejection.

#### Scenario: The existing engine still answers identically

- **WHEN** `POST /lisan/analyze` is called for `خير`, `خبث` and `كفر` after this change
- **THEN** the responses SHALL be identical to before it
- **AND** `tests/test_lisan_regression.py` SHALL pass unmodified

#### Scenario: The response publishes its evidence

- **WHEN** `POST /lisan/concept` answers for a triliteral root
- **THEN** it SHALL carry each letter's `makhraj_ar` and features, the primitives each feature
  produced, the rarity order, and which two were realised
- **AND** the lock `version` under which the concept was produced
