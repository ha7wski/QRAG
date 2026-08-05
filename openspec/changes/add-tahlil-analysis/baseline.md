# Baseline — grounding availability for Tahlil, measured before the proposal

Run: `python openspec/changes/add-tahlil-analysis/baseline.py --dump`
(pure stdlib + on-disk artifacts, whole corpus, no sampling; per-word rows in
`baseline-coverage.tsv`). Frozen on `main` before any Tahlil code exists.

Tahlil is **cite-or-omit**, so the number that decides the feature is not "can the model
write it" but **"for how many words does the evidence exist at all"**. That is what this
sweeps, per block.

```
corpus : 77 429 words, 49 967 rooted (64.5 %), 1 642 roots, 76 639 in treebank
```

All rates below are over the **49 967 rooted words** — a rootless word (حروف, ضمائر,
أسماء إشارة, most أعلام) has no letters to decompose and no naẓāʾir, and is out of scope
for the الحروف/دلالي blocks by construction.

| block | evidence | words | share |
|---|---|---:|---:|
| **1 الحروف** | all root letters found, dataset keys as-is | 45 269 | 90.6 % |
| | all root letters found, **`هـ`→`ه` folded** | **49 967** | **100 %** |
| | …recovered by that single fold | 4 698 | 9.4 % |
| | every letter also carries `position_notes` | 41 605 | 83.3 % |
| **2 صرفي** | mīzān `verified` | 46 719 | 93.5 % |
| | باب present (verbs only, by definition) | 19 356 | 38.7 % |
| | a **contrast lemma** attested under the same root | 44 581 | 89.2 % |
| | block grounded (wazn **or** bab) | 47 008 | 94.1 % |
| **3 نحوي** | iʿrāb composable (in treebank, has relation) | 49 967 | 100 % |
| | `head_ref` (المتعلَّق) present | 39 874 | 79.8 % |
| | **Zero relation** (إسناد/تخصيص/إضافة/توضيح) | **0** | **dependency — not on disk** |
| **4 دلالي** | Maqāyīs aṣl for the root | 37 844 | 75.7 % |
| | ≥1 same-lemma naẓīr | 48 212 | 96.5 % |
| | ≥3 same-lemma naẓāʾir | 45 845 | 91.8 % |
| | block grounded (aṣl **or** naẓīr) | 49 514 | 99.1 % |
| **5 تركيب** | **all four blocks carry evidence** | **46 557** | **93.2 %** |

Omission reasons: `no-contrast-lemma-under-root` 5 386 · `no-asl-and-no-nazir` 453.

## What the numbers force into the spec

1. **The `هـ` key gap is real and silent.** The dataset keys hāʾ as «هـ» (two codepoints,
   letter + tatweel); root keys use the bare «ه». Unfolded, 4 698 words (9.4 %) lose a
   root letter *without any error* — the synthesis would simply be built from two letters
   instead of three. A key-normalizing loader is a prerequisite, not a nicety.
2. **Position claims cannot be universal.** د, ذ and ط carry no `position_notes` in the
   source; 16.7 % of rooted words contain one. The أول/وسط/آخر line must be omitted per
   letter, never generalized from the letters that do have one.
3. **The contrastive «أبلغ من X» needs two licensed flavours, not one.** The pinned
   example's own contrast — «يُسارِعون أبلغ من يُسرِعون» — compares against a form that
   **does not occur in the Quran**: the only lemmas attested under `سرع` are يُسَٰرِعُ
   (III), سَرِيع, أَسْرَع, سِرَاع. A rule of "cite an attested naẓīr or omit" would delete
   the reference analysis's best sentence. The spec therefore licenses *attested* contrast
   (cite the ref) **and** *unattested* contrast (the alternative باب is well-formed but
   absent from the corpus — an absence that is itself deterministically verifiable against
   `root_graph.json`), and forbids only the third case: a contrast form asserted without
   checking attestation either way.
4. **باب is not a fallback for nouns.** 38.7 % looks low only because باب is a verb
   property; 100 % of the 19 356 verbs have one. Nominal words get their تعليل from the
   mīzān + derived-noun features instead, so the form-KB must be keyed on both.
5. **The Zero relation is a hard dependency.** `analysis/zero_relations.py` does not
   exist; `add-nahwi-zero-relations` is unimplemented (all tasks unchecked). Its own
   baseline projects 87.6 % verified / 88.6 % shown. Tahlil's نحوي تعليل degrades to
   cite-or-omit when the fields are absent, so it can ship before that change lands — but
   the السبب line, which is the point of the block, will be empty until it does.
6. **The verb-mood marker the reference analysis asserts does not exist yet.**
   «مضارع مرفوع وعلامته ثبوت النون» is *not* produced today: `qac_labels.case_marker`
   covers nominal case only and returns `None` for 23:61:2. It is fully derivable —
   an IMPF verb with no `verb_mood` tag is مرفوع (5 582 words), `MOOD:JUS` مجزوم (1 418),
   `MOOD:SUBJ` منصوب (1 330); of these, 3 567 carry an أفعال خمسة `pgn`, 2 593 of them
   مرفوع بثبوت النون. That makes it a **new deterministic fact** (badge محقّق), not
   something the model may assert.

## The pinned gold case

The reference analysis is for **23:61:2** (المؤمنون — «أُولَٰئِكَ يُسَارِعُونَ فِي
الْخَيْرَاتِ وَهُمْ لَهَا سَابِقُونَ»), not آل عمران; 3:114:10 is وَيُسَارِعُونَ, its
closest naẓīr. Its baseline row is fully grounded on all five blocks:

```
ref      word         root  lemma  b1 b2 b3 b4 b5  wazn         bab      nazair root_occ asl
23:61:2  يُسارعون      سرع   يسرع    1  1  1  1  1   يُفَاعِلُونَ   فَاعَلَ    8      23       1
```

Everything the reference analysis states as *fact* is already on disk and deterministic:
root `سرع`, wazn `يُفَاعِلُونَ` (`verified`), باب `فَاعَلَ`, نحوي relation `Pred`/«خبر»
with `head_ref` `23:61:1` (أُولَٰئِكَ), 8 same-lemma naẓāʾir, 23 root occurrences,
Maqāyīs aṣl «السين والراء والعين أصل صحيح يدل على خلاف البطء», and the صفات behind the
صوتي claim (س مهموسة رخوة + صفير · ر مجهورة متوسطة + تكرير · ع مجهورة متوسطة).

What is **missing** for that one word is exactly the generated layer this change adds —
plus two deterministic gaps it must close first: the mood marker (§6) and the Zero
relation (§5).

## Caveat on the surface form

`qac_words["23:61:2"].uthmani` is `يُسرعُون` — the alif of the مفاعلة is absent from the
QAC surface field, while the chakl corpus has the correct `يُسَارِعُونَ`. The صوتي block
must therefore read its surface from `chakl_by_ref()` via the existing token alignment
(as `verse_tokens` already does), never from the QAC `uthmani` field, or the syllable
decomposition of the pinned example would be wrong at the first letter.
