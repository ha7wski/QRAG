# Arabic review — `frontend/src/lib/strings.ts`

Reviewer: **the owner** (single signatory, settled 2026-09-08). Date: **2026-09-08**

## ✅ Signed off — 2026-09-08

**The whole file is accepted as drafted**, Part A and Part B together, including the seven
editorial choices recorded at the end. No corrections were raised.

Consequences:

- **The blocking gate (task 4.6) is lifted — group 5 may start.**
- Part B was signed in advance of the per-page commits, so wiring a page is not gated on a
  further reading of the strings it already contains (task 4.6b).
- **Task 4.6c still stands.** Any string *added or changed* during groups 5-7 — a state a
  page turns out to need, a failure kind the wiring reveals, a label shortened to fit — is a
  delta that comes back for review before 9.1. The sign-off covers what was drafted, not
  whatever the implementation discovers.
- The pre-approved fallback for a tight tab strip («التقارب في المعنى», group A3) needs no new
  sign-off if the 9.2 walk calls for it.

Read this file, not the TypeScript. Three columns: the dictionary key, the Arabic as
drafted, and the English it replaces (`—` where the string is new, or where the code was
already Arabic). Mark each group **accepted** or **corrected**; apply corrections to
`strings.ts` before signing off.

Nothing is wired yet: `strings.ts` exists and typechecks (`tsc --noEmit` clean) but no
component imports it. Corrections here cost one edit, not a re-wiring.

---

## Part A — Blocking core (task 4.6)

These ~25 strings reach across pages, so a late correction is the expensive kind.
**Group 5 does not start until Part A is signed.**

### A1 · Application name and metadata

| Key | Arabic | Replaces |
|---|---|---|
| `app.name` | القرآن بالقرآن | `Quran RAG` |
| `app.title` | القرآن بالقرآن | `Quran RAG` |
| `app.description` | دراسةُ القرآن بالقرآن: سؤالٌ يُجاب من نصّ الآيات، وتتبُّعٌ للجذر في مواضعه، وقراءةٌ للآية في سياقها. | `Explore the Quran with retrieval-augmented search and analysis.` |

- [x] **accepted** — 2026-09-08, no corrections

### A2 · Navigation (five entries, top to bottom)

| Key | Arabic | Replaces |
|---|---|---|
| `nav.chat` | محاورة القرآن | `Talk to Quran` |
| `nav.verseStudy` | دراسة الآية | `Verse Study` |
| `nav.fassila` | الفواصل | `Fassila` |
| `nav.lexical` | تحليل اللسان | `Lisan Analysis` |
| `nav.tahlil` | التحليل النحوي | `Tahlil` |
| `nav.qlisan` *(page name; not in nav)* | بطاقة الكلمة | `QLisan` |
| `nav.openMenu` | فتح القائمة | — *(already Arabic)* |
| `nav.closeMenu` | إغلاق القائمة | — *(already Arabic)* |

- [x] **accepted** — 2026-09-08, no corrections

### A3 · Verse Study tab labels

| Key | Arabic | Replaces |
|---|---|---|
| `verseStudy.tabs.word` | الكلمة في الآيات | `Word in Verses` |
| `verseStudy.tabs.similar` | الآيات القريبة في المعنى | `Similar Verses` |
| `verseStudy.tabs.context` | الآية في سياقها | `Find Verse context` |

Pre-approved shorter form for `similar` if the three-tab strip proves tight at the 9.2
walk: **التقارب في المعنى**.

- [x] **accepted** — 2026-09-08, no corrections

### A4 · Landing copy (rewritten, not translated)

| Key | Arabic | Replaces |
|---|---|---|
| `home.heading` | دراسةُ القرآن بالقرآن | `Explore the Quran, with its sources` |
| `home.lede` | أداةٌ لقراءة القرآن ودراسة ألفاظه: تسأل فتُجاب من نصّ الآيات، وتتتبّع الجذر في مواضعه، وتقرأ الآية في سياقها. وكلُّ قولٍ مسنَدٌ إلى آيته. | `A trilingual companion for reading and understanding the Quran — ask questions, study the meaning of words, and look up any verse. Every answer points you back to the verses themselves.` |
| `home.cta` | ابدأ المحاورة | `Talk to Quran` |
| `home.cards.chat.desc` | اطرح سؤالك فتأتيك إجابةٌ مبنيّةٌ على نصّ الآيات، وكلُّ دعوى فيها مسنَدةٌ إلى الآيات التي جاءت منها. | `Ask a question in Arabic, French, or English and get a clear answer grounded in the text — every claim backed by the exact verses it comes from.` |
| `home.cards.verseStudy.desc` | اكتب كلمةً عربيّةً واحدةً، فترى كلَّ آيةٍ ورد فيها جذرها في القرآن كلِّه، مشكولةً، والكلمةُ مميَّزةٌ في موضعها. | `Type a single Arabic word and see every verse where its root appears across the whole Quran — fully vocalized, with the word highlighted in place.` |
| `home.cards.lexical.desc` | اطلب اللفظ بجذره، فترى مواضعه في القرآن وما يحمله من وجوه المعنى باختلاف السياق. | `Look up an Arabic word by its root and see every place it appears in the Quran, with the shades of meaning it carries across contexts.` |
| `home.note` | الأجوبةُ مستوًى أوّلُ من النظر، وهي تذكر مصادرها دائمًا؛ ولا تقوم مقام التفسير. | `Answers are a first level of exploration and always cite their sources — they don't replace scholarly interpretation (tafsir).` |

The `Arabic, French, or English` claim is dropped from the copy per task 5.1. The
capability itself remains in the backend — which is why the answer bubble still needs
`dir="auto"` (task 5.2b).

- [x] **accepted** — 2026-09-08, no corrections

### A5 · Shared failure vocabulary

Used by every page, so the register has to be settled once.

| Key | Arabic | Replaces |
|---|---|---|
| `errors.nonArabicWord` | تُكتب الكلمة بالحرف العربي. | `word must be written in Arabic script` *(backend detail)* |
| `errors.emptyInput` | اكتب كلمةً أوّلًا. | `word must not be empty` *(backend detail)* |
| `errors.verseNotFound` | لا وجود لهذه الآية. | `Verse not found` |
| `errors.wordNotFound` | لا وجود لهذه الكلمة في هذا الموضع. | `Word {s}:{a}:{w} not found` |
| `errors.surahNotFound` | لا وجود لهذه السورة. | `Surah {n} not found` |
| `errors.surahListFailed` | تعذّر تحميل قائمة السور. | `Failed to load surah list` |
| `errors.analysisFailed` | تعذّر التحليل. | `Analysis failed` |
| `errors.searchFailed` | تعذّر البحث. | `Search failed` / `Lookup failed` |
| `errors.unavailable` | الخدمةُ غير متاحة مؤقّتًا. | — *(new: 503 was indistinct)* |
| `errors.unreachable` | تعذّر الاتصال بالخادم. | `Failed to fetch` *(browser)* |
| `errors.generic` | تعذّر إتمام الطلب. | `Request failed` |
| `errors.detailLabel` | تفصيل تقنيّ | — *(new: labels the `dir="ltr"` line)* |

- [x] **accepted** — 2026-09-08, no corrections

---

## Part B — Rolling review (task 4.6b), per page at its own group-5 commit

Non-blocking. Each block is signed when its page is wired.

### B1 · `/chat` — `ChatInterface`

| Key | Arabic | Replaces |
|---|---|---|
| `chat.placeholder` | اكتب سؤالك… | `Type your question...` |
| `chat.send` | إرسال | — *(icon-only today, no label at all)* |
| `chat.empty` | اطرح سؤالًا عن القرآن. | `Ask a question about the Quran.` |
| `chat.conversations` | المحادثات | `Conversations` |
| `chat.newConversation` | محادثة جديدة | `New conversation` *(also the persisted default)* |
| `chat.newShort` | جديدة | `New` |
| `chat.noSaved` | لا توجد محادثات محفوظة | `No saved conversations` |
| `chat.deleteConversation` | حذف المحادثة | `Delete conversation` |
| `chat.sources` | المصادر | `Sources` |
| `chat.noVerses` | لم تُطابِق أيُّ آية — جوابٌ عامّ. | `No verses matched — general answer.` |
| `chat.helpful` | مفيد | `Helpful` |
| `chat.notHelpful` | غير مفيد | `Not helpful` |
| `chat.justNow` | الآن | `just now` |
| `chat.minutesAgo(n)` | قبل دقيقة / قبل دقيقتين / قبل ٥ دقائق / قبل ١١ دقيقة | `{n}m ago` |
| `chat.hoursAgo(n)` | قبل ساعة / قبل ساعتين / قبل ٥ ساعات / قبل ١١ ساعة | `{n}h ago` |
| `chat.daysAgo(n)` | قبل يوم / قبل يومين / قبل ٥ أيام / قبل ١١ يومًا | `{n}d ago` |

- [x] **accepted** — 2026-09-08, no corrections

### B2 · `/verse-study`

| Key | Arabic | Replaces |
|---|---|---|
| `verseStudy.heading` | دراسة الآية | `Verse Study` |
| `verseStudy.caption` | اكتب كلمةً عربيّةً واحدةً — فترى كلَّ آيةٍ ورد فيها جذرها، مشكولةً. | `Type a single Arabic word — see every verse where its root appears, fully vocalized.` |
| `verseStudy.search` | بحث | — *(already Arabic)* |
| `verseStudy.wordPlaceholder` | اكتب كلمة عربية | — *(already Arabic)* |
| `verseStudy.phrasePlaceholder` | اكتب آية أو عبارة | — *(already Arabic)* |
| `verseStudy.similarNote` | بحثٌ بالجذر واللفظ في ⁨6236⁩ آية، مرتَّبٌ بحسب القرب في المعنى — يُعيد أقرب المواضع. | `Root-aware + keyword search across all 6236 verses, reranked by relevance — returns the closest matches (top 20).` |
| `verseStudy.nearest(n)` | أقرب آية / آيتين / ٥ آيات / ١١ آية | `nearest {n}` *(was «أقرب {n} آية» — wrong count form)* |
| `verseStudy.contextCaption` | اختر السورة والآية لقراءتها في سياقها — مع الآيات الثلاث قبلها وبعدها. | `Pick a surah and an ayah to read that verse in context — shown with the three verses before and after it.` |
| `verseStudy.showVerse` | اعرض الآية | `Show verse` |
| `verseStudy.loadingContext` | جارٍ تحميل السياق… | — *(already Arabic)* |
| `verse.ayahNumber` | رقم الآية | `Ayah number` *(aria-label)* |
| `verse.surah` | السورة | `Surah` *(aria-label; missing on two selects)* |

- [x] **accepted** — 2026-09-08, no corrections

### B3 · `/qlisan` — «بطاقة الكلمة»

| Key | Arabic | Replaces |
|---|---|---|
| `qlisan.heading` | بطاقة الكلمة | `QLisan` |
| `qlisan.caption` | اختر آيةً، ثم اضغط كلمةً واحدةً لترى تحليلها في أربعة مستويات — صوتي، صرفي، نحوي، دلالي. والصرفُ والنحوُ مأخوذان على وجه الحتم من المدوّنة المُعرَبة، لا من نموذج لغويّ. | `Pick a verse, then click a single word to see its four-level analysis — صوتي, صرفي, نحوي, دلالي. Morphology and syntax are served deterministically from the parsed corpus (no LLM).` |
| `qlisan.loadVerse` | اعرض الآية | `Load verse` |

- [x] **accepted** — 2026-09-08, no corrections

### B4 · `/tahlil` — «التحليل النحوي»

| Key | Arabic | Replaces |
|---|---|---|
| `tahlil.heading` | التحليل النحوي | `Tahlil` |
| `tahlil.caption` | اختر آيةً، ثم اضغط كلمةً لترى تحليلها في خمسة أبواب — الحروف، صرفي، نحوي، دلالي، تركيب. وكلُّ دعوى تحمل شارةَ مصدرها والدليلَ الذي تقوم عليه؛ والشارةُ تُخبر من أين جاءت العبارة، لا أنّها صحيحة. | `Pick a verse, then click a word for its five-block analysis — الحروف, صرفي, نحوي, دلالي, تركيب. Every claim carries a provenance badge and the evidence it stands on. A badge says where a sentence came from, never that it is correct.` |
| `tahlil.loadVerse` | اعرض الآية | `Load verse` |

- [x] **accepted** — 2026-09-08, no corrections

### B5 · `/lexical` — «تحليل اللسان»

| Key | Arabic | Replaces |
|---|---|---|
| `lexical.heading` | تحليل اللسان | `Lisan Analysis` |
| `lexical.caption` | اكتب كلمةً عربيّةً لقراءة جذرها حرفًا حرفًا — قراءةٌ تأويليّةٌ لرمزيّة الحروف في اللسان. | `Enter an Arabic word to read its root letter-by-letter — an interpretive letter-symbolism reading of the lisān.` |
| `lexical.analyze` | حلِّل | `Analyze` |
| `lexical.word` | الكلمة | — *(new aria-label; the field had only a sample placeholder)* |
| `lexical.loading` | جارٍ قراءة الجذر… (قد يستغرق التركيبُ لحظة) | `Reading the root… (synthesis may take a moment)` |
| `lexical.sarfiSection` | الصرف والإعراب | `تحليل نحوي` *(renamed: ends the D11 collision; the section renders صرف)* |
| `lexical.noRoot(word)` | لم يُعرف جذرٌ للكلمة ⁨«…»⁩. | `No root found for "…"` *(also replaces the English backend `message`)* |
| `lexical.resultRoot` | الجذر | `Root` |
| `lexical.resultAnalysis` | التحليل | `Analysis` |
| `lexical.resultKeyVerses` | آياتٌ شاهدة | `Key verses` |

- [x] **accepted** — 2026-09-08, no corrections

### B6 · Verse chrome — `VerseCard`, `VerseContextCard`, `/surah`, `/verse`

| Key | Arabic | Replaces |
|---|---|---|
| `verse.juz(n)` | الجزء ٣ | `Juz 3` |
| `verse.score` | درجة المطابقة | `score` |
| `verse.openSurah` | اعرض السورة كاملة | `Open full Sourate page` |
| `verse.surahNumber(n)` | السورة ٢ | `Surah 2` |
| `verse.ayahCount(n)` | آية / آيتين / ٧ آيات / ٢٨٦ آية | `{n} verses` |
| `verse.prevSurah` | السورة السابقة | — *(arrow-only today)* |
| `verse.nextSurah` | السورة التالية | — *(arrow-only today)* |
| `verse.prevAyah` | الآية السابقة | — *(arrow-only today)* |
| `verse.nextAyah` | الآية التالية | — *(arrow-only today)* |
| `verse.backToStudy` | رجوع إلى دراسة الآية | `← Back to Verse Study` |
| `verse.period.Meccan` | مكية | `Meccan` |
| `verse.period.Medinan` | مدنية | `Medinan` |
| `common.scrollToTop` | الرجوع إلى الأعلى | — *(already Arabic)* |

- [x] **accepted** — 2026-09-08, no corrections

### B7 · `HealthBanner`

| Key | Arabic | Replaces |
|---|---|---|
| `health.unreachable` | تعذّر الاتصال بالخادم؛ تأكّد من تشغيله ثم أعد المحاولة. | `Backend unreachable — start it with ./local-dev/start.sh.` |
| `health.starting` | الخادمُ في طور التشغيل؛ قد لا تتوفّر الأجوبة بعد. | `Backend is still starting up — answers may be unavailable.` |
| `health.degraded(parts)` | الخدمةُ منقوصة: … غير متاح. وقد تتعذّر الأجوبة حتى يستعيد عمله. | `Service degraded: … is unavailable. Answers may fail until it recovers.` |
| `health.partIndex` | فهرس البحث ⁨(Qdrant)⁩ | `the search index (Qdrant)` |
| `health.partModel` | نموذج اللغة ⁨(Ollama)⁩ | `the language model (Ollama)` |
| `health.and` | ` و` *(space before, none after — the waw is proclitic)* | ` and ` |
| `health.fallbackPart` | أحدُ المكوّنات | `a component` |

The script path is **dropped**, not translated: `local-dev/` is git-excluded, so a
cloner does not have it. If you would rather name the committed launcher, the
replacement is «شغِّله بالأمر ⁨./scripts/run.sh⁩».

- [x] **accepted** — 2026-09-08, no corrections

### B8 · Arabic templates that stay in components (task 4.6b)

Not in `strings.ts` — they are domain vocabulary owned by their component. Three are
`title` / `aria-label` text that no visual pass can see, which is why they are listed.

| Site | What it renders |
|---|---|
| `FassilaDiversityLine.tsx:251` | tooltip: `{name} · {n} آية · {n} فاصلة` — needs the count forms |
| `FassilaLine.tsx:178` | tooltip: `آية {n} · {fasila} · {word}` |
| `FassilaDistributionPie.tsx:187` | **aria-label**: `{n} فاصلة مميّزة — {n} سورة` — needs the count forms |
| `FassilaBars.tsx:33` | **title**: `{letter} · {n} من {n} (…%)` — needs isolation |
| `FassilaAnalysisTab.tsx:109-111` | `استُبعدت {n} آية مقطّعة` / `{n} آية محلَّلة` |
| `SarfiRows.tsx:63` | صرف row labels |
| `qlisan/page.tsx:293-294` | level captions |
| `TahlilClaim.tsx:89` | provenance sentence |
| `MadarAslCard.tsx:17-22` | count forms — `n >= 11` is wrong today («١١ أصول» → «١١ أصلًا») |

- [x] **accepted** — 2026-09-08, no corrections

---

## Editorial choices made in the draft — all confirmed 2026-09-08

Not translations — decisions taken on the owner's behalf while drafting, and accepted as
drafted:

1. **Counts drop the digit at 1 and 2.** «آية» and «آيتين», not «١ آية» / «٢ آيتين»: Arabic
   carries the number in the noun, and writing both reads as machine output. `count()`
   implements this; if you want the digit kept, it is one line.
2. **The dual is stored in the oblique form only** (آيتين, not آيتان). Every count in the
   app sits after a preposition or in an annexation, so the nominative is never needed and
   is deliberately absent rather than stored unused.
3. **`home.heading` is «دراسةُ القرآن بالقرآن»**, deliberately near but not identical to the
   application name, so the hero does not simply repeat the brand.
4. **`lexical.analyze` is «حلِّل»** (imperative) rather than a nominal «تحليل», to match the
   other action buttons («بحث» is nominal today — if you prefer consistency, the pair is
   either «حلِّل»/«ابحث» or «تحليل»/«بحث»).
5. **`verse.score` is «درجة المطابقة»** — "degree of match" — rather than a transliteration
   of `score`.
6. **`errors.unavailable` and `errors.detailLabel` are new strings**: the code had no
   distinct 503 message and no label for the technical line D10 introduces.
7. **Vocalization is partial and deliberate**: applied where it disambiguates or carries
   the register (مسنَدٌ، مشكولةً، الخادمُ), omitted elsewhere. Say if you want it uniform.

---

## Part C — The delta from groups 5-9 (task 4.6c)

**Decided by the implementer, 2026-09-08, at the owner's instruction** («je veux que tu te
débrouilles pour les seize chaînes»). Recorded in full because there was no second reader:
the same person drafted these and passed them, so what follows is the reasoning, not a
verdict to be taken on trust. Anything here can be reversed with one edit.

Sixteen strings. **Three changed, thirteen kept.**

### Changed

| key | was | is now | why |
|---|---|---|---|
| `home.cta` | «ابدأ المحاورة» | *deleted* — the hero uses `nav.chat` «محاورة القرآن» | It sat one definite article away from `home.cards.chat.cta` «ابدأ محاورة», **on the same screen, pointing at the same route**. And the hero's own pair was already mismatched: an action phrase beside a feature name (`nav.lexical`). Each register now does one job — hero buttons name where they go, card CTAs name what you do — which also carries one phrase from sidebar to hero to card title. |
| `lexical.noOccurrences` | «لم يرد للجذر رحم — جذرِ ⁨«الرحمن»⁩ — موضعٌ في القرآن.» | «لم يُعثر على موضعٍ لجذر ⁨«الرحمن»⁩ (رحم) في القرآن.» | The apposition between em-dashes is a European construction, and the sentence had no reason to invent a shape: `verseStudy.noneFound` already says «لم يُعثر على…». The root moves into parentheses, the reference style the cards use («البقرة (2)») — both sides Arabic, so the mirrored brackets carry no bidi risk. |
| `NOUNS.ayaMuqattaa` | «آية مقطّعة» ×4 forms | *deleted*; the line reads «استُبعدت من التحليل آية من الحروف المقطّعة» | The agreement was right and **the noun was wrong**, and it predates this change: an āya is not «مقطّعة», it is an āya *of* the disconnected letters. Naming the letters instead needs no series at all — `NOUNS.aya` carries it — and fronting «من التحليل» stops the sentence being read as "an āya was excluded *from* the letters". |

### Kept

| key | value | why it stands |
|---|---|---|
| `home.cards.chat.cta` | «ابدأ محاورة» | Verb + indefinite object, parallel across the three cards. Indefinite is the accurate form: a first-time reader has no conversation to resume. |
| `home.cards.verseStudy.cta` | «ادرس كلمة» | ⟪ same ⟫ |
| `home.cards.lexical.cta` | «حلِّل كلمة» | ⟪ same ⟫ |
| `chat.exampleHint` | «مثال: ما يقول القرآن عن الصبر؟» | «ما» rather than the modern «ماذا», matching the interrogative the dictionary already uses in `verseStudy.questionWord` («ما هي الآيات…»). This is the one place the app shows a reader **how to address the corpus**, so it is deliberately a whole question and not a topic. |
| `chat.retry` | «أعد المحاولة» | Standard imperative; no competing form. |
| `verse.loadingSurah` | «جارٍ تحميل السورة…» | `جارٍ` + maṣdar is already the file's loading idiom (`verseStudy.loadingContext`, `lexical.loading`). Changing it would mean changing all four. |
| `verse.loadingVerse` | «جارٍ تحميل الآية…» | ⟪ same ⟫ |
| `chat.inputLabel` | «سؤالك» | An accessible name, heard alone. Possessive where the other two are definite nouns, and that asymmetry is **meant**: this field holds the reader's own question, the other two hold a lookup key. |
| `verseStudy.wordLabel` | «الكلمة» | Echoes its tab («الكلمة في الآيات»), which is the phrase a screen reader speaks just before it. |
| `verseStudy.phraseLabel` | «الآية أو العبارة» | Definite form of its own placeholder — a name, not a repeat of the hint, which an `aria-label` would otherwise cost the reader. |
| `NOUNS.mawdi` | موضع / موضعين / مواضع / موضعًا | Sound plural مواضع, singular accusative at 11+. Correct at every boundary. |
| `NOUNS.fasilaMumayyaza` | فاصلة مميّزة / فاصلتين مميّزتين / فواصل مميّزة / فاصلة مميّزة | The adjective agrees with the number too, which is why the phrase is stored whole. Non-human plural takes the feminine singular adjective: «فواصل مميّزة», not «مميّزات». |
| `NOUNS.ayaMuhallala` | آية محلَّلة / آيتين محلَّلتين / آيات محلَّلة / آية محلَّلة | ⟪ same rule ⟫ |
| `verse.ayahLabel` | «الآية 255» | Same shape as `verse.surahNumber` «السورة ٢» beside it. Western digits here, Arabic-Indic there, because this header is chrome *about* a verse and that one is a reading context (task 3.4c). |

### Verified in the running page

The rewritten muqaṭṭaʿāt line, on three sūras:

```
sūra 2   استُبعدت من التحليل آية من الحروف المقطّعة · 285 آية محلَّلة
sūra 7   استُبعدت من التحليل آية من الحروف المقطّعة · 205 آية محلَّلة
sūra 42  استُبعدت من التحليل آيتين من الحروف المقطّعة · 51 آية محلَّلة
```

Sūra 42 is worth naming: الشورى opens with **two** muqaṭṭaʿāt āyāt (حم, عسق), so it is the
one place in the corpus where this line prints a **dual** — the form the review above calls
invisible in production until a count of 2 occurs. It prints «آيتين», with no digit.

And the landing page: the hero's two buttons now read «محاورة القرآن» and «تحليل اللسان»,
both destination names, while the cards below keep «ابدأ محاورة» / «ادرس كلمة» / «حلِّل كلمة».

### Observed and deliberately not changed

`verseStudy.search` is the nominal «بحث» while `lexical.analyze` is the imperative «حلِّل» —
the inconsistency editorial choice **4** already named, and which the owner confirmed as
drafted on 2026-09-08. It is outside this delta and stays until they say otherwise.

### Not in this delta, and why

`lexical.noSarfi`, `qlisan.notYetAvailable` and `qlisan.noIrab` became dictionary entries at
task 5.9c but are **not new strings**: they were already on screen as inline literals, so
they have been read by anyone who used those pages. Listed so their absence is a decision
rather than an oversight.
