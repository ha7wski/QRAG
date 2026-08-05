## Context

QLisan is deterministic by construction: `analysis/word_analysis.py` assembles a four-level fiche
where every field is read verbatim from `qac_words.json` / `qac_syntax.json` / `root_graph.json`,
`analysis/mizan.py` projects the mīzān (98.8 % `verified` after the hardening change), and the
صوتي/دلالي levels are honest stubs. The badge «معطى محقّق» means *this string came from the
treebank*, and that meaning is load-bearing across the product.

Tahlil breaks that symmetry deliberately: **80 % of its output is generated**. Every prior LLM
attempt in this repo failed in the same direction, and those failures are the design constraints:

- **`lisan/`**: the Qwen synthesis produced fluent Arabic that contradicted the attested root
  sense, and once injected a Latin fragment mid-word. It was **deleted** and replaced by a
  deterministic template.
- **`madar/`**: LLM synthesis is env-gated **off** by default; ~50 % of witness-root outputs were
  problematic. The UI centres the cited aṣl and the occurrences, and the synthesis is voided by a
  deterministic Arabic-purity post-check when it drifts.
- **mīzān**: lafẓ al-jalāla produced a confident, complete, wrong answer that no coverage rate
  could see. The lesson written into that change: **inspect samples per source, not the aggregate.**

So the question is not "can Qwen write a تعليل" — it can, fluently, and that is precisely the
danger. It is: **what structural guarantee prevents a fluent-but-false sentence from reaching the
page?** This design answers with one mechanism: the model never supplies facts, only prose over an
evidence bundle assembled deterministically, and every sentence it emits must resolve to a
citation *in code* or be dropped before rendering.

Measured state before implementation (`baseline.md`): of 49 967 rooted words, 93.2 % have evidence
for all four blocks; the letters dataset covers 100 % of roots only after a `هـ`→`ه` key fold that
today silently truncates 4 698 roots; the Zero relation layer does not exist yet.

## Goals / Non-Goals

**Goals**

- Reproduce the reference exemplar's *shape* for 23:61:2 — five blocks, وصف→تعليل per level, one
  تركيب thesis with a contrastive clause — with every assertion badged and citation-anchored.
- Keep the three badges structurally, not editorially, separated: **محقّق** can only be produced by
  code paths that read the treebank or derive from it deterministically; the generation path is
  physically incapable of emitting it.
- Add zero risk to QLisan: Tahlil is a reader of `analyze_word`, not a modifier.
- Degrade honestly at every level: no evidence → block absent with a stated reason, never filled.
- Make the whole thing measurable: coverage log, citation-resolution rate, gold set, per-source
  sampling.

**Non-Goals**

- **No tafsīr, no أسباب النزول, no external commentary**, in any collection, prompt, or fallback.
- **No Zero pyramid view of the verse** (explicitly out of scope; separate change).
- **No Rāghib in this change** — not on disk; acquisition + extraction + licence is its own work.
- **No bilingual output** — generated prose is Arabic only.
- **No batch pre-computation** of the corpus.
- **No new Qdrant collection** (see decision 6).
- No modification of `/lexical`, `/madar`, `/qlisan`, chat, or search behaviour.

## Decisions

### 1. The model receives an evidence bundle and returns prose keyed to it — never free text

`tahlil/evidence.py` assembles a JSON bundle first, entirely from disk: the QLisan fiche, the
per-letter rows (with page numbers), the naẓāʾir with their vocalized verse text, the form-KB rows
that matched, the Maqāyīs aṣl, the contrast candidates with their attestation status. Each evidence
item gets a stable **id** (`letter:س@p161`, `nazir:3:114:10`, `sigha:bab.III.mubalagha@v1`,
`maqayis:سرع`).

The prompt asks for a JSON array of claims, each `{block, text_ar, cites: [id, …], badge}`. The
generator never sees the free corpus and is never asked to recall a verse.

*Alternative rejected:* prose-out with post-hoc citation matching (what most RAG systems do). The
`madar` experience is decisive — a fluent paragraph is *harder* to audit than a claim list, and
post-hoc matching rewards vagueness: the vaguer the sentence, the easier it "matches" a source.

### 2. Cite-or-omit is a code gate, not a prompt instruction

`tahlil/citations.py` validates every returned claim against the bundle: unknown id → drop;
empty `cites` → drop; `badge == "محقّق"` on a generated claim → drop (the generation path can never
mint محقّق); Latin/CJK leakage → drop the claim, and void the whole block if the leakage is
systemic (the `madar` post-check, applied per claim). Dropped claims are written to the coverage
log with their reason.

The page then renders **only surviving claims**, each with its citations shown beneath it, naẓīr
ids rendered as links to the verse. A block whose claims were all dropped renders as
«قيد الإعداد» with the reason — the same honest-stub contract QLisan already uses.

*Rationale:* a prompt instruction to "only cite the given sources" is a request; a validator is a
guarantee. The distinction matters because the failure mode here is invisible: nobody reading
«توحي بحركة منسابة متواصلة» can tell whether the letter dataset actually says that.

### 3. Three badges map onto three *provenances*, decided by which code path produced the claim

| badge | produced by | example |
|---|---|---|
| **محقّق** | treebank read, or a deterministic derivation of one (mīzān, باب, iʿrāب, the new mood marker, the letters' صفات, the naẓāʾir list) | «وزن يُفاعِلون» · «س: مهموسة رخوة، فيها صفير» |
| **مُولَّد** | generated, every cite resolving to a naẓīr, a form-KB row, or the Maqāyīs aṣl — **and, for a multi-sense KB row, a corpus disambiguator among the cites** | «صيغة المفاعلة هنا تفيد المبالغة» *when a naẓīr or a syntactic fact of the context is cited* |
| **تأويلي** | generated over the letter دلالة, any «أبلغ من X» contrast, **or a multi-sense selection made without a corpus disambiguator** | «السين مع الراء توحيان بحركة منسابة» |

The letters block is the one place where a single row splits across two badges: **صفات = محقّق**
(established phonetic classification), **دلالة = تأويلي** (a contested theoretical framework — the
dataset's own `honesty_flags` says so in writing). The UI must show them as two rows, never merged
into one sentence, or the fact silently lends its authority to the interpretation.

**A multi-sense KB row does not launder an interpretive choice into مُولَّد.** The المفاعلة row
lists both المشاركة and المبالغة/طلب الفعل; saying «هنا المبالغة لا المشاركة» is not a lookup, it is
a reading — the citation proves the *sense exists in the KB*, never that *this* sense holds here.
So the badge is decided by what else the claim cites:

- **single-sense row** → مُولَّد. The cite settles the claim; there is nothing to choose.
- **multi-sense row + a corpus disambiguator among the cites** (a naẓīr showing the same form used
  the same way, or a syntactic fact of this verse's context) → مُولَّد. The selection is anchored in
  the corpus, which is exactly the standard the rest of the page holds.
- **multi-sense row with no disambiguator** → **downgraded to تأويلي**, and logged
  `sense-selection-unanchored`. Not dropped: the reading may well be right and is worth showing —
  it just has no more evidential standing than a letter reading, and must not borrow the badge of
  one that does.

Downgrade rather than drop is deliberate here, and it is the only downgrade in the gate. Everywhere
else a failed check means the claim had no provenance at all; here the provenance is real but
under-determines the claim, so the honest response is a weaker badge, not silence.

### 3b. Badge labels are part of the contract, because the guarantee bounds provenance, not truth

A badge that reads as a quality mark defeats the whole design: مُولَّد means *we checked where this
came from*, never *we checked that it is right*. The label and tooltip are therefore specified, not
left to the UI:

| badge | label (Arabic) | tooltip |
|---|---|---|
| **محقّق** | «معطى محقّق» | «معطى محقّق من الإعراب/الصرف» — a deterministic corpus fact |
| **مُولَّد** | «مُولَّد» | «مُولَّد ومُسنَد إلى شواهد، غير مُحقَّق» — generated, anchored on naẓāʾir/KB/Maqāyīs, **not verified for correctness** |
| **تأويلي** | «تأويلي» | «تأويلي: إطار نظري مُختلَف فيه (دلالة الحروف / المقارنة البلاغية)» |

The «غير مُحقَّق» wording is load-bearing and appears on every generated block that has not been
reviewed, tying the badge to the `reviewed` flag: an un-reviewed generated block states its
un-verified status in words, not only in colour. تأويلي must never be visually confusable with
محقّق — different tone *and* different label text, so the distinction survives greyscale, a
colour-blind reader, and a screenshot.

### 4. The contrastive «أبلغ من X» has two licensed flavours and one forbidden case

The baseline killed the naive rule: the exemplar's own contrast (يُسارِعون vs يُسرِعون) points at
a form **absent from the Quran** — `سرع` attests only يُسَٰرِعُ (III), سَرِيع, أَسْرَع, سِرَاع.

**Attestation is computed at the granularity of the candidate — the (lemma, POS/باب) pair — never
at the granularity of the root.** The root is the wrong unit and would invert the verdict on the
pinned word: `سرع` does contain أَسْرَع, but that is an **اسم تفضيل** (6:62 «أَسْرَعُ الْحَاسِبِينَ»),
not a verb of باب أفعَلَ. A root-level check would see the string, call the contrast attested, and
silently turn the exemplar's strongest sentence into a false one. So:

> a contrast candidate counts as attested **iff the corpus contains a word of *this* lemma **and**
> of *this* باب/POS**. A noun, an elative, or a participle sharing the root never attests a verb of
> a given باب, and vice versa.

- **Attested contrast** — a word of that lemma *and* that باب/POS occurs. Cite the ref. Badge
  تأويلي (the *comparison* is interpretive even when both forms are facts).
- **Unattested contrast** — the alternative is a well-formed باب of the same root with **no word of
  that باب/POS** in the corpus. The claim must say so, and say it at the right granularity —
  «ولم ترد صيغة أفعَلَ **فعلاً** من هذا الجذر» — since a bare «لم ترد أفعَلَ» would be false in the
  presence of أَسْرَع. Verified in code against `root_graph.json` + the lemma index + the POS/باب
  of each occurrence. Badge تأويلي.
- **Forbidden** — a contrast form emitted without an attestation check. Dropped by the validator:
  the contrast candidate must come from `bab_contrast.json`, and its attestation flag is computed
  by us, never asserted by the model.

This is what makes the pinned scenario pass while keeping the rule strict.

### 5. The نحوي block consumes the Zero layer; it does not implement it

`add-nahwi-zero-relations` owns `analysis/zero_relations.py`. Tahlil reads `zero_relation`,
`zero_role`, `zero_reason`, `zero_verified` if present and omits the relation line if not (logged
as `zero-layer-absent`). Ordering is therefore free: Tahlil can ship first with a thinner نحوي
block, and gains the السبب line the day the other change lands, with no Tahlil code change.

What Tahlil *does* add deterministically is the **verb-mood marker** the exemplar asserts and QAC
supports but `qac_labels.case_marker` never computed: IMPF + no `verb_mood` → مرفوع (and
«وعلامته ثبوت النون» when the `pgn` is one of الأفعال الخمسة), `MOOD:JUS` → مجزوم بحذف النون,
`MOOD:SUBJ` → منصوب بحذفها. It lives in `qac_labels.py` beside `case_marker` (additive, nominal
path untouched) because it is the same kind of derivation, and it is badged محقّق.

### 6. No `quran_usage` collection — the deterministic index already is the evidence

The checklist calls for a Qdrant `quran_usage` collection of occurrences + contexts. Deliberately
not built:

- `root_graph.json` maps root → **every** occurrence ref, exactly and completely. Cite-or-omit
  needs exact attestation, and a vector index would layer approximate recall over data that is
  already exhaustive — strictly worse evidence for this purpose.
- The verse text and vocalization already come from `chakl_by_ref()`.
- What retrieval *is* good for here is **selection**: 41 204 rooted words have ≥10 same-lemma
  siblings, and the bundle can only carry a handful. So `retrieval/similar_verses.py` (root ∪ BM25
  → cross-encoder → coverage blend, already built and evaluated) ranks which naẓāʾir enter the
  bundle, over the existing `quran_verses` collection.

*Trade-off:* the حقل دلالي loses the thematic breadth a dedicated usage index might give. Since the
QAC ontology the checklist assumed **does not exist in this repo** (verified — no file, no loader),
the حقل is derived from co-occurrence around the root's own occurrences and badged مُولَّد. If that
proves too thin at review, adding the collection later is additive and changes no contract.

### 7. On-the-fly generation, SQLite cache, version-keyed

Cache key: `(ref, prompt_version, kb_version, letters_version, model_id)`. A prompt edit or a KB
bump therefore invalidates by construction rather than by memory. Stored in the existing
`data/runtime/app.db` via `api/store.py` (`tahlil_cache`), alongside `tahlil_review` for the
`reviewed` flag, reviewer note, and timestamp.

*Alternative rejected:* pre-computing 49 967 words. Hours of local Qwen per prompt iteration, and —
worse — 49 967 unread outputs presented with the authority of a stored artifact. The gold
exemplars are the exception: they are generated once and **frozen into the repo** so tests are
reproducible without a live model.

### 8. Generation is env-gated off by default; deterministic blocks always render

`TAHLIL_GENERATION_ENABLED=0` by default, mirroring `MADAR_SYNTHESIS_ENABLED` and the project's
other quality toggles. With it off, `/tahlil` still renders the letters (صفات + دلالة + citation),
the صرفي facts, the نحوي facts, the naẓāʾir and the Maqāyīs aṣl — everything محقّق, plus the
KB-matched form senses, which are **table lookups, not generation**, and stay مُولَّد-badged
without a model. Only the free prose (per-level تعليل, تركيب, verse synthesis) disappears.

This keeps the page useful on a machine with no Ollama, and gives a clean A/B for review: the same
word with and without the generated layer.

### 9. Verse granularity composes word analyses; it never re-reads the verse

`POST /tahlil/verse` runs the word pipeline over the verse's own tokens (mean 12.4 words/verse,
max 128) and generates one synthesis whose evidence bundle is **the resulting word claims** — not
the verse text. A verse claim must cite the word claims it composes, so verse-level output can
never assert something no word-level analysis supports. Words are capped and the cap is logged;
verses above the cap synthesize over the content words (rooted words) only, stated in the output.

### 10. The letters dataset gets one loader, one source of truth

`tahlil/huruf.py` owns a `@lru_cache` loader over `data/references/arabic_letter_semantics_hasan_abbas.json`
(the `data/processed/` copy is byte-identical and is deleted — a duplicated table is a future
divergence). It normalizes keys (`هـ`→`ه`, hamza seats → `ء`, following the existing
`letter_lexicon` convention) and **raises** on a root letter it cannot resolve rather than skipping
it, so the 4 698-word silent truncation cannot recur.

**It decomposes the unfolded root, not the index key.** Found during implementation: the processed
corpus stores roots hamza-folded onto alif (`اله`, `امن`, `شيا`), and `root_display` is identical
to `root` for all 49 967 rooted words — so `normalize_root` has already destroyed the seat before
the seat-fold could ever fire, and the fold was dead code on the real path. Since the dataset holds
**ء (الهمزة, p94-95)** and **ا (الألف اللينة, p96)** as two distinct entries, a folded root
attributes the wrong meaning *and the wrong page citation* to **133 roots / 9 780 words (19.6 %)** —
twice the hāʾ bug, and equally silent. The raw QAC morphology source keeps the seat (`ROOT:أله`),
and the normalized→raw mapping is **unambiguous: zero collisions over 1 651 roots**, so recovery is
deterministic. (139 hamza-bearing roots exist in the raw file; 6 have no root-graph counterpart,
leaving the 133 above.) This is the third instance of the same lesson in this project: the thing that breaks
is never the letter you cannot find, it is the letter you find *wrongly*.

The disclaimer strings are the module's own, in Arabic. The dataset's `honesty_flags` and part of
its `source` block are written in French; rendering them would both break the Arabic-only rule and
trip the Latin-purity gate that voids a block.

`lisan/letter_lexicon.py` and `/lexical` keep the old CSV in this change. Migrating them is a
separate, behaviour-visible change; noted here so the split is deliberate and documented rather
than an accident of two datasets drifting.

### 11. A claim that only repeats its source is a quotation — recognised, not rendered

Added after the first live qwen run, which produced two claims that passed the gate saying
nothing: a bare «يُسَارِعُونَ» in دلالي and a near-verbatim naẓīr verse in نحوي. Both cited
resolvable evidence, so both were correctly kept and correctly badged. **No coverage rate can see
that** — which is why it needed a rule rather than a note in a report.

The rule is sound in the direction it is used, and that is the whole argument for it: a sentence
that merely restates a Quranic verse cannot be false, so recognising one costs no true statement.
The same words are already on the page under **محقّق**, rendered by the deterministic layer. What
is removed is a redundant restatement wearing the badge of a *reading*, which inflates precisely
the count acceptance will read as «anchored readings produced».

**Strict containment is the entire safeguard.** If a claim could append a clause and still be
called a quotation, the rule would invert into a laundering channel — «it's only the verse» —
for an interpretation nobody checked. So the whole claim, modulo whitespace, tashkīl and *edge*
punctuation, must appear verbatim inside **one** cited source. Interior punctuation is part of the
text. A concatenation of sources is never the comparison target: a join creates spans that exist
in no source, and a claim spliced across one would be declared a quotation of something nobody
wrote.

Known limit, recorded rather than papered over: a **re-ordered** splice — the same words in a
different order, adding nothing — is not contiguous in any source and survives. Catching it means
matching "most of the words, in any order", and a rule that fuzzy deletes real تعليل built from
the evidence's own vocabulary. The safeguard is worth more than the case; the case belongs to the
per-source human inspection (task 12.4).

Lives in the generation layer (`GENERATION_LOG_REASONS`), not the gate, so `citations.REASONS`
stays closed — it is not a citation verdict but a judgement about whether a sentence is a claim at
all.

### 12. «تأويلي» means *contested*, and a QAC fact is not contested — settled

This closes the open question raised when the gate was built: a `qac:` cite is available on
98.98 % of words, so keeping it among the corpus disambiguators makes the one downgrade erasable
almost everywhere. Removing it was considered and **rejected**.

تأويلي denotes a contested theoretical framework — the letters doctrine, a بلاغة comparison. A
word's grammatical role and the word it depends on are neither: they are read off the treebank and
nobody disputes them. A reading anchored on one is anchored on a fact, so badging it تأويلي files
a fact under «disputed».

The decisive argument is about measurement, not taxonomy. Task 12 judges prompt quality by the
badge distribution. If facts are counted as contested, that measure is wrong at its source — and
wrong in the direction that hides the problem, since a prompt that stopped citing usage would be
masked by the mass of QAC-anchored claims already sitting in the same bucket. So the downgrade
stays deliberately narrow: it fires when a multi-sense selection cites **neither** the Quran's
usage **nor** a syntactic fact of the verse — i.e. when it rests on the KB row alone, which proves
only that the sense exists, never that it holds here.

Machine-checked rather than asserted: the badge lattice is enumerated exhaustively over every
combination of corpus kinds, and the only routes to تأويلي are the two intended unanchored
selections.

### 13. The naẓīra snippet is a window centred on the WORD, not a prefix of the verse

Decided by the first live recording, which produced the failure mode this whole change is built
against: prose that is fluent, correctly cited, and **false**. Five دلالي claims came back, one per
naẓīra, and two of them said the opposite of their source — 5:41's «يسارعون في الكفر» rendered as
«يتركون الأفكار الكافرة ويتجهون نحو الإيمان». Every claim resolved to a real citation, so the gate
kept all five and the coverage rate read 100%.

The cause was not the wording. `_nazir_line` cut `verse_text[:120]` — a blind prefix — which for
3:114 stops one word before «الْخَيْرَاتِ», and for 5:41 and 5:52 stops mid-word. For a verb of
hastening the entire contextual reading **is** the complement: يسارعون في الخيرات against في الكفر
against في الإثم. The prompt deleted exactly the discriminating material and then asked what the
word means in context; the model supplied the missing complement out of nothing. A prefix also
shows the verse's opening, where the word usually is not, so «what does this word do here» was
answered by summarising a verse the word had not yet appeared in.

The window therefore locates the word (by recorded index, then by matching — `quran_chakl.csv`
prepends the Basmala to āya 1 and shifts every index there), snaps to whitespace, marks each
elided side, and grows forward twice per backward step so the complement survives a tight budget.

This is the clearest evidence so far for the discipline the change is named after: **an
anti-hallucination gate cannot compensate for evidence that has been mutilated upstream.** The gate
proves provenance; it has no way to know the cited line was cut before the part that mattered.

### 14. A دلالي claim resting on ONE naẓīra is refused as a verse gloss

The same recording, same root cause, different lever. The block's contract admits exactly two
claims: a محوري reading standing on the lexical aṣl and the letters, and ONE سياقي reading
synthesised **across** the naẓāʾir. A claim resting on a single verse satisfies neither — whatever
it says, it is a gloss of that verse, which is the one thing `tahlil-dalali` forbids.

The rule is **structural**: it reads the citation shape, never the prose, so it cannot become a
semantic judgement smuggled into the licensing direction. And it runs only in the rejecting
direction, so it cannot launder anything. It is scoped to دلالي because elsewhere a single naẓīra
is correct by design — صرفي anchors a form's sense on exactly one, which is what
`check_sense_selection` demands.

### 15. The system prompt carries one worked example, and a rule guards it

Two live recordings showed that an abstract field contract does not land on qwen2.5:7b. Told that
`text_ar` is «the full claim» and `sense_ar` «a technical field», it kept filing the reasoning under
`sense_ar` and a bare quotation under `text_ar` — `{"text_ar": "يُسَارِعُونَ في الخيرات", "sense_ar":
"الخبر"}`. The second time this emptied four blocks: every claim was refused, correctly, as a
quotation. Prose rules ٣ and ٤ were written against exactly this and did not hold.

An example lands where a description does not, so the contract now shows one complete claim. That
opens a hole the gate cannot close: `check_quotation` compares a claim only against the EVIDENCE
lines, so a claim copying the example would pass wearing real citations — a fabrication with a
clean provenance record, the worst shape this change can produce. `check_prompt_echo` closes it by
containment against the example, rejecting-direction only, exactly as the quotation rule works
against the evidence. One source of truth: the guarded string is the string interpolated into the
prompt, asserted by test.

## Risks / Trade-offs

- **A fluent-but-false تعليل passes every mechanical check** (correct citations, correct Arabic,
  wrong reading). → The validator bounds *provenance*, not *truth*. Mitigation is procedural and
  mandatory: the ~30-word gold set with expert exemplars, **per-source sample inspection** (letters
  / naẓāʾir / form-KB / Maqāyīs read separately, ≥20 claims each), and the `reviewed` flag making
  un-reviewed generated content visibly un-reviewed. Acceptance is never granted on a coverage
  rate — the explicit lesson from lafẓ al-jalāla.
- **The reader mistakes a badge for a quality mark.** This is the same risk one layer out: the
  guarantee is about provenance, and a user who reads «مُولَّد» as «vérifié» has been misled by our
  own UI. → The labels and tooltips of decision 3b are **mandatory, specified strings**, not a UI
  choice: مُولَّد explicitly says «غير مُحقَّق», تأويلي explicitly says «إطار نظري مُختلَف فيه», and
  the «غير مُحقَّق» mention rides on every un-reviewed generated block. تأويلي and محقّق must differ
  in *label text*, not only in colour, so the distinction survives greyscale and colour-blindness.
  A test asserts the three labels and the three tooltips are present and pairwise distinct.
- **The letter framework is contested scholarship presented in a Quranic tool.** → Badge تأويلي,
  the dataset's own honesty flag surfaced in the UI, the author + page number cited under every
  letter claim, صفات never merged with دلالة, and the synthesis validated against actual usage
  before it is shown.
- **Qwen 7B may not sustain the exemplar's register in Arabic.** → The gold set measures this
  before rollout; `LLM_PROVIDER=anthropic` is the escape hatch; the deterministic layer stands
  alone if the answer is no. This is a *quality* decision to be taken on measured output, not
  assumed at design time.
- **Maqāyīs covers 75.7 % of rooted words.** → The remaining 24.3 % lose their lexical anchor; the
  core sense then rests on letters (تأويلي) + usage, and the block must say which anchors it had.
- **Cache staleness across KB edits.** → Version fields participate in the key; a KB file without a
  bumped version fails the loader's check.
- **Latency**: word analysis = QLisan lookup (ms) + naẓīr ranking (reranker, already warmed for
  `/search`) + one Qwen call. Verse analysis multiplies the word path. → Cache first; verse
  synthesis reuses cached word analyses; the reranker pool caps mirror `/search`'s measured ones.
- **Scope**: six new capabilities is a lot for one change. → They are deliberately severable —
  blocks 1/2/3 are deterministic-heavy and ship independently of 4/5, and `tahlil-verse-synthesis`
  is last in the task order so it can be dropped without touching the word path.

## Migration Plan

Purely additive; no data migration, no re-ingest, no schema change to the QAC artifacts.

1. Deterministic foundations first (letters loader + key fix, form KB, mood marker) — verifiable
   with no model running.
2. Evidence bundle + citation validator, with the generator stubbed — the citation-resolution
   sweep runs before any prose exists.
3. Generation behind `TAHLIL_GENERATION_ENABLED=0`; gold exemplars generated, reviewed, frozen.
4. Frontend page; nav entry last.
5. Rollback = flip the toggle off (generated layer vanishes, deterministic page remains) or drop
   the route; nothing else depends on Tahlil.

## Open Questions

- **Does Qwen 7B hold the register?** Decided on the gold set at task 9, not now. If it does not,
  the fallback order is Anthropic → deterministic-only page.
- **Should the 24.3 % of roots with no Maqāyīs aṣl carry a visible "no lexical anchor" marker in
  the دلالي header**, or is the citation strip's absence enough? Decide after the first review pass.
- **Rāghib** — deferred, revisit once a licence-clean, page-citable edition is on disk.
- **Migrating `/lexical` to the new letters dataset** — deliberately out of scope; a follow-up
  decision once Tahlil's block 1 has been reviewed in production use.
- **Whether the 5 386 words with no contrast lemma deserve a KB-only contrast** (باب opposition
  with no attested sibling at all) or should simply omit the contrastive clause. Currently: omit.
