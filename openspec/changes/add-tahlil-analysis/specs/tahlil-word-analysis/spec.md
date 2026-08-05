## ADDED Requirements

### Requirement: Clicking يُسَارِعُونَ produces the reference analysis, every claim badged and anchored

This is the pinned acceptance scenario of the whole change. Selecting the word at **23:61:2**
(المؤمنون — «أُولَٰئِكَ يُسَارِعُونَ فِي الْخَيْرَاتِ وَهُمْ لَهَا سَابِقُونَ») SHALL produce a
five-block analysis matching the reference exemplar in structure and substance, in Arabic, where
every single assertion carries a badge (محقّق / مُولَّد / تأويلي) and at least one resolvable
citation.

The reference exemplar attributes the verse to آل عمران; the corpus is authoritative — 23:61 is
the pinned ref and 3:114:10 (وَيُسَارِعُونَ) SHALL appear among its naẓāʾir.

#### Scenario: The five blocks are produced with the exemplar's substance

- **WHEN** `POST /tahlil/word {"surah": 23, "ayah": 61, "word": 2}` is called with generation
  enabled
- **THEN** the response carries five blocks in the fixed order الحروف/الصوتي → صرفي → نحوي →
  دلالي → تركيب
- **AND** the الحروف block decomposes س‑ر‑ع, states that س is مهموسة/رخوة with صفير and ر is
  مجهورة/متوسطة with تكرير (badge محقّق), and reads a sense of continuous flowing motion from
  their دلالة (badge تأويلي)
- **AND** the صرفي block states الجذر «سرع», الوزن «يُفَاعِلُونَ», باب «فَاعَلَ» (badge محقّق) and
  explains that the مفاعلة here is not المشاركة but المبالغة/طلب السبق — badged **مُولَّد when the
  claim cites a corpus disambiguator** (a same-lemma naẓīr or a syntactic fact of the verse)
  **and تأويلي when it cites only the multi-sense KB row**
- **AND** the نحوي block states «فعل مضارع مرفوع وعلامته ثبوت النون» and that the sentence is
  «في محلّ رفع خبر» for اسم الإشارة «أُولَٰئِكَ» at `head_ref` 23:61:1 (badge محقّق), and reads
  التجدّد والاستمرار from the مضارع (badge مُولَّد)
- **AND** the دلالي block gives the core sense from Ibn Fāris' aṣl «السين والراء والعين أصل صحيح
  يدل على خلاف البطء» (badge محقّق for the citation, مُولَّد for the reading) and the contextual
  sense of competing in الخيرات inferred from the naẓāʾir alone
- **AND** the تركيب block composes the four levels into a single thesis naming each of them, with
  a contrastive clause
- **AND** no claim in any block lacks a badge or a citation.

#### Scenario: The contrastive clause of the exemplar survives the citation gate

- **WHEN** the same analysis is produced
- **THEN** the contrast «يُسارِعون أبلغ من يُسرِعون» is emitted as an **unattested** contrast —
  it states that the أفعَلَ form of this root does not occur in the Quran **as a verb**
- **AND** that absence is verified in code at `(lemma, POS/باب)` granularity, so the same-root
  elative أَسْرَع (6:62) does not make the candidate attested
- **AND** the verdict is computed by the system, not asserted by the model
- **AND** the claim is badged تأويلي, never محقّق.

#### Scenario: The exemplar's facts come from the deterministic layer, not the model

- **WHEN** the same analysis is produced with `TAHLIL_GENERATION_ENABLED=0`
- **THEN** الجذر, الوزن, الباب, البنية, العلامة, الموقع الإعرابي, المتعلَّق, the naẓāʾir, the
  letters' صفات and the Maqāyīs aṣl are all still present and badged محقّق
- **AND** only the free prose (per-level تعليل, the تركيب thesis) is absent, each with a stated
  reason
- **AND** the page renders without error.

### Requirement: Every claim carries exactly one of three badges, and generation can never mint محقّق

The system SHALL badge each rendered assertion with exactly one of:

- **محقّق** — read from the QAC treebank, or derived from it deterministically (mīzān, باب,
  iʿrāب, العلامة including the verb-mood marker, the naẓāʾir list, the letters' صفات, the cited
  Maqāyīs aṣl text).
- **مُولَّد** — generated, with every citation resolving to a naẓīr, a form-KB row, or the
  Maqāyīs aṣl.
- **تأويلي** — generated over letter دلالة / phono-semantics, or any contrastive «أبلغ من X».

A claim produced by the generation path SHALL NOT carry «محقّق» under any circumstance. The
validator SHALL drop such a claim rather than re-badge it, and SHALL log the drop — a generator
that attempts to mint محقّق is a defect to be seen, not silently corrected.

**«تأويلي» SHALL be reserved for the genuinely contested**: the letters doctrine and any
comparative «أبلغ من X». A claim anchored on the corpus — the Quran's own usage or a syntactic
fact of the verse read from the treebank — SHALL NOT be badged تأويلي, because a grammatical role
and its head are not disputed by anyone: they are facts. The only exception is the single
downgrade below, which fires when a multi-sense selection cites **neither** usage **nor** a
syntactic fact. This is a measurement requirement as much as a labelling one: acceptance judges
the prompt by the badge distribution, so a fact filed under «contested» would corrupt the measure
before it is taken.

#### Scenario: A syntactic fact of the verse anchors a sense selection

- **WHEN** a claim selects one sense of a multi-sense KB row and cites the verse's own
  `qac:relation` or `qac:head_ref`
- **THEN** it is badged مُولَّد, not تأويلي
- **AND** no `sense-selection-unanchored` entry is logged for it.

#### Scenario: Nothing corpus-anchored is filed under «contested»

- **WHEN** the badge is computed for any claim whose citations are all naẓāʾir, QAC fields, KB
  rows or the Maqāyīs aṣl
- **THEN** the result is تأويلي **only** when the claim selects from a multi-sense row without
  citing a naẓīr or a syntactic fact
- **AND** in every other combination it is مُولَّد.

#### Scenario: A generated claim asking for محقّق is dropped

- **WHEN** the generator returns a claim with `badge: "محقّق"`
- **THEN** the claim is not rendered
- **AND** it is written to the coverage log with reason `generated-claimed-verified`.

#### Scenario: صفات and دلالة of a letter are never merged into one claim

- **WHEN** the الحروف block renders any letter
- **THEN** its صفات appear as a claim badged محقّق and its دلالة as a separate claim badged تأويلي
- **AND** the two are never combined into a single sentence or a single badge.

### Requirement: A generated claim that only repeats its source is a quotation, not a تعليل

A generated claim whose text adds **nothing** to one of the sources it cites SHALL be recognised
as a quotation and SHALL NOT be rendered as generated تعليل; it SHALL be logged
`claim-is-quotation`. Refusing it costs no true statement: a restatement of a Quranic verse or of
a cited aṣl cannot be false, and the same words are already on the page under the **محقّق** badge,
rendered by the deterministic layer. What is removed is a redundant restatement wearing the badge
of a reading — which is not information, and which inflates the count of «anchored readings» that
acceptance measures.

Recognition SHALL be by **strict containment**: the whole claim, modulo whitespace, tashkīl and
edge punctuation, appears verbatim inside a single source **the block was shown**. Containment
SHALL be tested against one source at a time, never against a concatenation of several, and SHALL
NOT be restricted to the sources the claim cites — a restatement of one source while citing
another is still a restatement. Any word the claim adds SHALL disqualify it as a quotation —
otherwise the rule becomes a way to launder an interpretation as «it is only the verse».

Two generated claims with the **same text** within one block SHALL be rendered once. The first
occurrence keeps its own citations; the second SHALL be logged `duplicate-claim`. Nothing SHALL be
merged.

#### Scenario: A restatement counts even when it cites a different source

- **WHEN** a generated صرفي claim reproduces a naẓīr's verse verbatim while citing only
  `qac:relation` and `qac:head_ref`
- **THEN** it is recognised as a quotation and is not rendered
- **AND** the coverage log records reason `claim-is-quotation`.

#### Scenario: The same sentence twice is one claim

- **WHEN** the generator returns two claims whose text is identical, differing only in citations
- **THEN** exactly one is rendered, carrying the first occurrence's citations
- **AND** the coverage log records reason `duplicate-claim` for the second.

#### Scenario: A bare restatement of a naẓīr is refused

- **WHEN** a generated دلالي claim consists of the naẓīr's own word and cites that naẓīr
- **THEN** the claim is not rendered
- **AND** the coverage log records reason `claim-is-quotation`.

#### Scenario: A quotation with an interpretation attached is not a quotation

- **WHEN** a generated claim quotes a naẓīr and appends a clause of its own
- **THEN** it is NOT recognised as a quotation
- **AND** it is judged by the ordinary citation gate like any other claim.

### Requirement: A naẓīra is shown to the model as a window centred on the word

The snippet of a naẓīra verse handed to the model SHALL be a window **centred on the occurrence
of the word**, never a prefix of the verse. The window SHALL include the word and what follows it;
where a budget forces a choice, what FOLLOWS the word SHALL be preferred over what precedes it.
The window SHALL begin and end on word boundaries, and each elided side SHALL be marked, so a
fragment is never presented as a whole verse.

The word's position SHALL be located by its recorded index when that index holds the word, and by
matching the surface form otherwise: the vocalized corpus prepends the Basmala to āya 1, shifting
every index in that āya, and a window centred on the wrong token is a plausible snippet of the
wrong part of the verse — undetectable downstream.

This is a grounding requirement, not a formatting one. For a verb the contextual reading **is** the
complement (يسارعون في الخيرات against في الكفر against في الإثم); a prefix window deletes the
discriminating material and then asks what the word means in context, and the gate cannot detect
that the cited line was cut before the part that mattered.

#### Scenario: The complement survives truncation

- **WHEN** naẓīra 3:114 is longer than the snippet budget
- **THEN** the snippet contains «وَيُسَارِعُونَ» and «فِي الْخَيْرَاتِ»
- **AND** the elided opening of the verse is marked.

#### Scenario: No snippet ends mid-word

- **WHEN** any naẓīra is truncated
- **THEN** every token of the snippet is a token the verse contains.

### Requirement: A دلالي claim resting on a single naẓīra is a verse gloss

A دلالي claim whose only citation is one naẓīra SHALL NOT be rendered; it SHALL be logged
`claim-is-verse-gloss`. The block admits a محوري reading standing on the lexical aṣl and the
letters, and ONE سياقي reading synthesised across the naẓāʾir — a claim resting on a single verse
is neither, and is a gloss of that verse, which this capability forbids.

The rule SHALL read the citation shape only, never the prose, and SHALL apply only in the rejecting
direction. It SHALL be scoped to دلالي: elsewhere a single naẓīra is correct by design.

#### Scenario: One verse, one claim, refused

- **WHEN** a generated دلالي claim cites exactly one naẓīra and nothing else
- **THEN** the claim is not rendered
- **AND** the coverage log records reason `claim-is-verse-gloss`.

#### Scenario: A reading synthesised across two naẓāʾir survives

- **WHEN** a generated دلالي claim cites two naẓāʾir
- **THEN** the rule does not refuse it, and it is judged by the ordinary citation gate.

### Requirement: A claim that copies the prompt's worked example is refused

The system contract SHALL carry one worked example claim, and a generated claim containing that
example's text SHALL NOT be rendered; it SHALL be logged `claim-echoes-the-example`. The example is
fluent Arabic the model was shown but not given as evidence, and the quotation rule compares a
claim only against the evidence lines — so a copied example would pass the gate wearing real
citations, which is a fabrication carrying a clean provenance record.

#### Scenario: The example is not a source

- **WHEN** a generated claim reproduces the system prompt's example, with or without an appended
  clause, while citing real evidence
- **THEN** the claim is not rendered
- **AND** the coverage log records reason `claim-echoes-the-example`.

### Requirement: Cite-or-omit is enforced by a code validator, not by prompt instruction

Every generated claim SHALL carry a machine-readable list of evidence ids. Before rendering, the
system SHALL validate each claim against the evidence bundle that produced it and SHALL DROP the
claim when: its `cites` list is empty; any cited id is absent from the bundle; the claim's badge is
inadmissible for its citations; or the text contains Latin word-characters or CJK (the Arabic
purity post-check already used by `madar`).

The gate SHALL have exactly one **downgrade** outcome rather than a drop: a sense selected from a
multi-sense form-KB row with no corpus disambiguator among its citations SHALL be re-badged from
مُولَّد to تأويلي, rendered, and logged `sense-selection-unanchored`. Every other failed check
SHALL drop the claim.

Dropped and downgraded claims SHALL be recorded in a coverage log with ref, block, reason and the
offending text, so both can be triaged. The set of reasons SHALL be closed — a reason outside it
SHALL fail the sweep — and a block whose claims are all dropped SHALL render as «قيد الإعداد» with
its reason, never as an empty or fabricated block.

#### Scenario: A claim citing an id absent from the bundle is dropped

- **WHEN** a generated claim cites `nazir:19:97:5`, a ref not present in the assembled bundle
- **THEN** the claim is not rendered
- **AND** the coverage log records reason `unresolved-citation`.

#### Scenario: A claim with no citation is dropped

- **WHEN** a generated claim returns an empty `cites` list
- **THEN** the claim is not rendered
- **AND** the coverage log records reason `no-citation`.

#### Scenario: Latin or CJK leakage voids the claim

- **WHEN** a generated claim contains a Latin word-character or a CJK codepoint
- **THEN** the claim is dropped with reason `non-arabic-output`
- **AND** if every claim of a block is dropped for that reason, the block renders as «قيد الإعداد».

#### Scenario: An unanchored sense selection is downgraded, not dropped

- **WHEN** a claim selects one sense from a multi-sense form-KB row and cites only that row
- **THEN** the claim is rendered with the badge تأويلي instead of مُولَّد
- **AND** the coverage log records reason `sense-selection-unanchored`
- **AND** this is the only outcome of the gate that re-badges rather than drops.

#### Scenario: Surviving claims display their citations

- **WHEN** any generated claim is rendered
- **THEN** its citations are shown beneath it
- **AND** a naẓīr citation is rendered as a link to that verse
- **AND** a letter citation shows the author and page number
- **AND** a form-KB citation shows the KB row id and its version.

### Requirement: The analysis is assembled from the existing QLisan fiche without modifying it

Tahlil SHALL obtain الجذر, اللفظ, البنية الصرفية, الميزان, الباب, the morphological features, the
segments, الموقع الإعرابي, العلامة, المتعلَّق and the naẓāʾir by calling the existing per-word
assembler, and SHALL NOT re-derive, re-parse, or duplicate them. `analysis/word_analysis.py` and
the `/qlisan` routes SHALL remain behaviourally unchanged by this capability.

#### Scenario: The QLisan fiche is unchanged by Tahlil

- **WHEN** `POST /qlisan/word` is called for any word before and after this change
- **THEN** the response is byte-identical apart from fields added by other, separately-specified
  changes
- **AND** the four-level order صوتي → صرفي → نحوي → دلالي is preserved.

#### Scenario: Deterministic facts in Tahlil match the QLisan fiche exactly

- **WHEN** a Tahlil analysis is produced for any word
- **THEN** every محقّق value it renders is identical to the corresponding value in that word's
  QLisan fiche
- **AND** no محقّق value is re-worded, rounded, or re-derived by Tahlil.

### Requirement: Generation is env-gated off by default and degrades honestly

The generative layer SHALL be controlled by `TAHLIL_GENERATION_ENABLED`, defaulting to `0`. When
it is off, when the model is unreachable, or when generation fails, the system SHALL still return
every deterministic block and every KB table lookup, and SHALL state per absent block why it is
absent. It SHALL NOT return an error, an empty page, or a placeholder analysis.

#### Scenario: No model available

- **WHEN** a Tahlil analysis is requested and the LLM health check fails
- **THEN** the response returns 200 with all deterministic blocks populated
- **AND** each generated block carries a message stating the model is unavailable
- **AND** the coverage log records the request as `generation-unavailable`.

### Requirement: Analyses are generated on the fly and cached under a version-derived key

The system SHALL generate on demand and SHALL cache the result keyed on
`(ref, prompt_version, kb_version, letters_version, model_id)` in the application SQLite store. A
change to the prompt, to a knowledge base, or to the letters dataset SHALL invalidate the cached
entry by construction. The system SHALL NOT pre-compute the corpus.

#### Scenario: A repeated request is served from cache

- **WHEN** the same word is requested twice with no version change in between
- **THEN** the second response is served from the cache without an LLM call
- **AND** its content is identical to the first.

#### Scenario: A prompt version bump invalidates

- **WHEN** the prompt version is bumped and the same word is requested
- **THEN** the cached entry is not used and a fresh analysis is generated.

### Requirement: Generated content carries a review state that is visible until reviewed

Each cached analysis SHALL carry a persisted `reviewed` state (reviewer, timestamp, optional note),
default un-reviewed. Un-reviewed generated content SHALL be visibly marked as such in the UI, and
an expert action SHALL be able to mark an analysis reviewed. Review SHALL NOT block rendering.

#### Scenario: Un-reviewed content is visibly un-reviewed

- **WHEN** an analysis with generated blocks has never been reviewed
- **THEN** the generated blocks display an un-reviewed indicator alongside their badge.

#### Scenario: Marking reviewed persists

- **WHEN** `POST /tahlil/review` marks an analysis reviewed
- **THEN** the state persists across restarts
- **AND** subsequent responses for that analysis report it as reviewed.

### Requirement: The page reuses the QLisan verse selector and adds no new selection mechanism

The `/tahlil` page SHALL select a word through the existing vocalized verse + QAC-aligned token
boundaries endpoint, so a token index equals the QAC `word_id` by construction. It SHALL NOT
introduce a second alignment path.

#### Scenario: Word selection round-trips

- **WHEN** the user picks 23:61 and clicks the second word
- **THEN** the request carries `word: 2`
- **AND** the analysed word is يُسَارِعُونَ.

### Requirement: The surface form used for phonetic claims comes from the vocalized corpus

Any claim about the word's letters, syllables or vocalization SHALL read the surface from the
vocalized (chakl) corpus through the existing token alignment, and SHALL NOT read the QAC
`uthmani` field, which is not reliably vocalized.

#### Scenario: The pinned word's surface is the vocalized one

- **WHEN** the الحروف block is assembled for 23:61:2
- **THEN** the surface it analyses is `يُسَارِعُونَ`
- **AND** not the QAC `uthmani` value `يُسرعُون`.

### Requirement: Acceptance requires a gold set and per-source inspection, never a coverage rate alone

Acceptance SHALL require a gold set of ~30 expert exemplars, with 23:61:2 pinned, and SHALL
require reading samples of at least 20 claims **for each evidence source separately** — letters,
naẓāʾir, form-KB, Maqāyīs. A coverage or citation-resolution rate SHALL NOT be sufficient
evidence of correctness, because a claim that is confidently wrong is complete-looking and
therefore invisible in the rate.

The corpus-wide sweep SHALL report claims emitted, claims dropped by reason, blocks rendered per
badge, and the grounding rates measured in the change's baseline, and SHALL fail when a grounding
rate regresses below the frozen baseline.

#### Scenario: Per-source samples are read before acceptance

- **WHEN** the change is reviewed for acceptance
- **THEN** ≥20 claims are read for each of the four evidence sources separately
- **AND** acceptance is not granted on the aggregate citation-resolution rate alone.

#### Scenario: The grounding sweep does not regress

- **WHEN** the corpus grounding sweep is run
- **THEN** الحروف coverage is 100 % of rooted words, صرفي ≥ 94.1 %, نحوي ≥ 100 %, دلالي ≥ 99.1 %
  and all-four ≥ 93.2 %
- **AND** a lower rate fails the sweep.
