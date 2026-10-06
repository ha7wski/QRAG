## Context

Six feature pages (the chat aside) open on `h1` + one grey `text-sm` caption (`S.<page>.heading` / `.caption`), then
their controls. The captions say what to type, not what the page offers. The landing page `/` already
uses the visual vocabulary this change wants: rounded `border-gray-200` white cards, a `bg-brand-light`
icon tile with a `text-brand-dark` lucide icon, `text-[15px] leading-relaxed text-gray-600` body. The
introductions reuse that vocabulary at a smaller scale so the app reads as one design.

Constraints carried from existing specs: every string Arabic and in `lib/strings.ts`
(`arabic-ui-locale`); logical properties only, Amiri everywhere, icons that do not mirror
(`rtl-app-shell`); browser storage wrapped in try/catch (`lib/readingPosition.ts` is the precedent).

## Goals / Non-Goals

**Goals:**
- One shared component, so six introductions look and behave identically.
- Each page explained in ≤ 1 summary sentence + 2–6 one-sentence feature cards.
- Never in the way of a returning reader: foldable, remembered folded, one line when folded.

**Non-Goals:**
- No onboarding tour, tooltips, modal or coach marks.
- No change to the existing captions, controls, routes or data.
- No introduction on `/` (already a presentation) or `/verse/[surah]/[ayah]` (a single verse).
- **No change to «محاورة القرآن» (`/chat`)**: no heading, no introduction, no layout change. Its
  presentation will be handled in a later change.
- No illustrations or screenshots inside the cards — icons only.

## Decisions

### D1 — One `PageIntro` component, data-driven
`components/PageIntro.tsx` takes `{ id, summary, features: { icon, title, how }[] }`. Each page passes
its entry from `S.intro.<page>` plus its icons (icons are components, so they stay in the page, not
in the dictionary). *Alternative:* per-page bespoke markup — rejected, six variants would drift
visually within a month.

### D2 — Visual layout
```
┌ «دراسة الآيات»                                   [ⓘ عن هذه الصفحة ▾] ┐
│ caption (unchanged, grey)                                            │
├──────────────────────────────────────────────────────────────────────┤
│ summary — text-[15px] text-gray-700, max-w-3xl                       │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                    │
│ │ [icon] Title │ │ [icon] Title │ │ [icon] Title │   grid gap-3       │
│ │ one sentence │ │ one sentence │ │ one sentence │                    │
│ └──────────────┘ └──────────────┘ └──────────────┘                    │
└──────────────────────────────────────────────────────────────────────┘
```
- Container: `rounded-xl border border-brand/20 bg-brand-light/40 p-4 sm:p-5` — tinted, so it reads
  as *about* the page and is not mistaken for a result.
- Cards: `rounded-lg bg-white border border-gray-200 p-3`, icon tile `h-8 w-8 rounded-lg
  bg-brand-light` with a `h-4 w-4 text-brand-dark` icon *inline-start* of the title (`text-sm
  font-semibold text-gray-900`), sentence below (`text-sm leading-relaxed text-gray-600`).
- Grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`; a 2- or 4-card page uses `lg:grid-cols-2`
  (one full row, or 2 × 2) rather than an empty third track or a 3 + 1 orphan row — the landing page hit the same empty-track problem.
- Height budget: 3 cards on one desktop row ≈ 180–220 px total; 6 cards on two rows ≈ 320 px.
- Fold/unfold: `grid-rows-[0fr]→[1fr]` transition (~200 ms), disabled under
  `prefers-reduced-motion`.

### D3 — Toggle on the heading line, folded state remembered per page
The `h1` row becomes `flex items-center justify-between`: heading at inline-start, a ghost button
«عن هذه الصفحة» with an `Info` icon and a chevron at inline-end. State key
`intro.<id>.folded` in `localStorage`, read in an effect (no SSR mismatch: server renders open), every
access in try/catch. *Alternative:* always open — rejected, the reader who knows the page loses
200 px on every visit. *Alternative:* folded by default — rejected, then nobody discovers it.

### D4 — Copy lives in `S.intro`, feature names are references
`S.intro.<page> = { summary, features: [{ title, how }] }` where `title` *references* the existing
string when one exists (`S.verseStudy.tabs.word`, `S.reading.annotations.toggle`, …), so a renamed tab
renames its card. Toggle label and region name: `S.intro.toggle` = «عن هذه الصفحة», `S.intro.region`
= «تعريف بالصفحة».

### D5 — Chat is out of scope
`/chat` and `ChatInterface.tsx` are not touched. A chat is a fixed-height column where any block above
the messages costs reading space, so its presentation needs its own design and is deferred to a later
change.

### D6 — Reading page: in `SurahPicker`'s heading block
Both `/surah` and `/surah/[number]` render `SurahPicker`'s heading, so the intro goes there once and
appears on both routes with one `id` (`surah`): folding it while reading folds it on the picker too.

### D7 — Draft copy (Arabic, to be reviewed by the user before implementation)
Word counts are within the spec bounds. Titles in «» are existing strings, referenced.

**سور القرآن** — icons `BookOpen`, `Layers`, `Bookmark`, `Highlighter`
- Summary: «اقرأ السورة كاملةً بنصّها المشكول، وانتقل بين السور، واكشف عند الحاجة ما يتقارب من آياتها.»
- اختيار السورة: «اختر السورة من القائمة، وتنقّل إلى السابقة أو اللاحقة بالسهمين.»
- «مقاطع السورة»: «السورة الطويلة تُعرض خمسين آيةً في كلِّ مقطع، تنتقل بينها بالألسنة.»
- موضع القراءة: «يُحفظ آخرُ موضعٍ قرأته، فإعادة تحميل الصفحة تُرجعك إلى آيتك.»
- «إظهار الآيات المتقاربة»: «الأخضر آيةٌ تقاربها آياتٌ من سورتها، والبرتقالي آيةٌ تقاربها أو تشاركها كلماتٌ في سورٍ أخرى؛ انقر لترى قريناتها.»

**دراسة الآيات** — icons `Search`, `GitCompareArrows`, `ScrollText`
- Summary: «ثلاثُ طرقٍ لدراسة الآيات: تتبُّعُ جذر كلمةٍ في القرآن كلِّه، والبحثُ عن الآيات المتقاربة، وقراءةُ آيةٍ في سياقها.»
- «الكلمة في الآيات»: «اكتب كلمةً واحدةً فيُحدَّد جذرها، وتُعرض كلُّ آيةٍ ورد فيها، مجمّعةً بحسب اللفظ ثم السورة، والكلمةُ مميَّزة.»
- «الآيات المتقاربات»: «داخل سورةٍ: مجموعاتُ آياتها المتقاربة؛ في سائر القرآن: جدولُ السور المتقاربة؛ من عبارة: أقربُ الآيات إلى ما تكتب.»
- «الآية في سياقها»: «اختر السورة والآية فتُعرض مع الآيات الثلاث قبلها وبعدها.»

**فهرس الجذور** — icons `ListTree`, `Hash`, `ChevronsUpDown`, `ArrowLeftRight`
- Summary: «جذور القرآن كلُّها مرتَّبةً على حروف المعجم، ولكلِّ جذرٍ أرقامُه وألفاظُه وتركيبُ حروفه.»
- «حروف المعجم»: «اختر حرفًا فتظهر الجذور التي تبدأ به، وبجانب كلِّ حرفٍ عددُ جذوره.»
- بطاقة الجذر: «تعرض عددَ مواضع الجذر وآياته وسوره في القرآن.»
- تفصيل الجذر: «انقر البطاقة فتنفتح على تركيب حروفه الثلاثة، وسوره، وألفاظه.»
- الانتقال: «من كلِّ جذرٍ زرّان: إلى «الكلمة في الآيات» وإلى «تحليل لساني عربي».»

**تحليل لساني عربي** — icons `Sprout`, `Type`, `Quote`, `Puzzle`, `MapPin`, `Network`
- Summary: «اكتب كلمةً فترى جذرها المحقَّق وما قيل في حروفه، ومواضعَه في القرآن، وصرفَه وإعرابه.»
- «الجذر»: «يُستخرج الجذر من مدوّنة القرآن المُعرَبة المحقَّقة، لا من تخمين.»
- «حروف الجذر»: «لكلِّ حرفٍ اسمُه ومخرجه وموضعه، ودلالتُه كما نشرها سامر إسلامبولي منسوبةً إليه.»
- «ما نشره إسلامبولي لهذا الجذر»: «جملتُه المنشورة لهذا الجذر، إن وُجدت، بنصِّها وعنوانها.»
- «تركيب الأسطر الثلاثة»: «تركيبٌ آليٌّ من التطبيق لدلالات الحروف الثلاثة، مع الفرق بينه وبين جملة إسلامبولي.»
- «المواضع»: «عددُ مواضع الجذر وآياته وألفاظه، مع نماذج، ورابطٌ إلى المواضع كاملةً.»
- «الصرف والإعراب»: «تحليلُ الكلمة الصرفيُّ والنحويُّ كما تُثبته المدوّنة المُعرَبة.»

**فواصل الآيات والسور** — icons `AlignEndHorizontal`, `ChartLine`, `ChartPie`
- Summary: «الفاصلة آخرُ حرفٍ في الآية عند الوقف؛ تُدرس هنا في كلِّ سورة، ثم تُقارن السور بها.»
- «تحليل الفواصل»: «اختر سورةً فترى توزيعَ فواصلها، وتتابعَها آيةً بعد آية.»
- «مقارنة السور»: «تُصنَّف السور المئة والأربع عشرة بعدد فواصلها المختلفة؛ انقر فئةً في الدائرة لتصفية القائمة.»

**بطاقة الكلمة** — icons `AudioLines`, `Shapes`, `Network`, `Lightbulb`
- Summary: «اختر آيةً ثم انقر كلمةً منها، فتُحلَّل في أربعة مستويات، من الصوت إلى المعنى.»
- صوتي: «حروف الكلمة ومخارجها وصفاتها.»
- صرفي: «جذرها ووزنها وبنيتها كما تُثبتها المدوّنة المُعرَبة.»
- نحوي: «موقعها في الجملة وإعرابها من المدوّنة، لا من نموذجٍ لغوي.»
- دلالي: «ما تدلّ عليه الكلمة في سياق آيتها.»

The «بطاقة الكلمة» level names are to be checked against the strings the
page actually renders (`LevelCard`) at implementation, and referenced if they exist.

## Risks / Trade-offs

- [Copy drifts from features — a mode is renamed or removed and its card still describes it] →
  titles reference existing strings (D4); a Vitest asserts each page's card titles are among the
  strings the page renders.
- [Visual noise on dense pages (`/lexical`, 6 cards)] → tinted container + 3-column grid keeps it to
  two rows; if still too tall at review, merge «ما نشره إسلامبولي» and «تركيب الأسطر الثلاثة» into one
  card.
- [Hydration flash: server renders open, client folds] → the fold animation is skipped on the first
  client read, so a folded page does not visibly collapse on load.
- [Accuracy of claims about features (e.g. what is persisted, what a root card unfolds to)] → every sentence is
  checked against the code at implementation; any feature claim that cannot be pointed to in the code
  is rewritten or dropped.

## Open Questions

- Should «فواصل الآيات والسور» keep its hard-coded caption literal (currently inline in
  `app/fassila/page.tsx`, contrary to `arabic-ui-locale`)? Proposed: move it to `S.fassila.caption`
  in the same change since the header is being edited anyway.
- Is the copy in D7 the wording the user wants? It is a draft to review before `/opsx:apply`.
