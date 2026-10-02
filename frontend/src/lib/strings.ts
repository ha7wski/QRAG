/**
 * The Arabic interface dictionary — the single place the wording is reviewed.
 *
 * Every user-facing string lives here, grouped by page/component. Components read
 * from `S` instead of embedding Arabic literals, so the whole interface copy can be
 * read as one artefact by a reader of Arabic (design D5).
 *
 * Two documented exemptions: text interpolated from backend data, and Arabic domain
 * terminology a component derives from a typed map it already owns (QLisan's
 * feature-key -> label map, the نحوي role labels). Those are corpus vocabulary, not
 * interface copy, and stay with their domain type.
 *
 * Comments and identifiers are English, per the project convention. Only the values
 * are Arabic.
 */

import type { SensePosition } from "./lisanTypes";

/**
 * Isolate a Latin or numeric token inside an Arabic sentence.
 *
 * A dictionary entry returns a `string`, so it cannot emit a `dir="ltr"` element.
 * FSI...PDI (U+2068 / U+2069) is the only isolation available to a plain string —
 * and it also works inside `title` and `aria-label`, where an element cannot go.
 * Without it, a bracketed Latin token reorders: "(Qdrant)" renders as ")Qdrant(",
 * because the mirrored parentheses resolve to the surrounding RTL level (design D15).
 *
 * Rule: every `${…}` holding a Latin or numeric token passes through `iso()`.
 */
export const iso = (token: string | number): string => `⁨${token}⁩`;

/**
 * Arabic counted nouns take four forms, not one (العدد والمعدود):
 *   1        -> singular          آية
 *   2        -> dual              آيتين
 *   3..10    -> plural            آيات
 *   11 and up-> singular accusative آية
 *
 * `two` is stored in the form the interface actually needs. Every count in this app
 * sits after a preposition or in an annexation (أقرب آيتين، قبل دقيقتين), so the
 * oblique dual is the useful one; the nominative (آيتان) is not used in the UI and is
 * deliberately absent rather than stored unused (design D18).
 */
export type NounForms = {
  /** n === 1 */
  one: string;
  /** n === 2, oblique/annexed */
  two: string;
  /** 3 <= n <= 10 */
  few: string;
  /** n >= 11, singular accusative */
  many: string;
};

/** Pick the noun form for `n`. Returns the noun alone — the caller places the digit. */
export function nounFor(n: number, forms: NounForms): string {
  const k = Math.abs(Math.trunc(n));
  if (k === 1) return forms.one;
  if (k === 2) return forms.two;
  if (k >= 3 && k <= 10) return forms.few;
  return forms.many;
}

/**
 * Render "<n> <noun>" with the right noun form. For n === 1 and n === 2 the digit is
 * omitted, because Arabic carries the number in the noun itself: «آية», «آيتين» —
 * writing «1 آية» or «2 آيتين» is redundant and reads as a machine translation.
 */
export function count(n: number, forms: NounForms): string {
  const { digits, noun } = countParts(n, forms);
  return digits === null ? noun : `${digits} ${noun}`;
}

/**
 * `count()` split into its parts, for a caller that styles the numeral
 * differently from the noun — «<b>93</b> آية». `digits` is null at 1 and 2,
 * where the noun's own form carries the number; the rule stays here rather
 * than being re-decided in JSX, which is how «2 آية» reached production.
 *
 * The numeral is always Western (0-9). These helpers used to take a
 * pre-rendered `digits` string so a "reading" surface could pass Arabic-Indic
 * forms; the interface now uses one numeral system everywhere, so the
 * parameter is gone rather than left as a way back into two.
 */
export function countParts(
  n: number,
  forms: NounForms,
): { digits: string | null; noun: string } {
  const k = Math.abs(Math.trunc(n));
  return {
    digits: k === 1 || k === 2 ? null : String(n),
    noun: nounFor(k, forms),
  };
}

/** The noun series the interface counts. */
export const NOUNS = {
  aya: { one: "آية", two: "آيتين", few: "آيات", many: "آية" },
  surah: { one: "سورة", two: "سورتين", few: "سور", many: "سورة" },
  fasila: { one: "فاصلة", two: "فاصلتين", few: "فواصل", many: "فاصلة" },
  asl: { one: "أصل", two: "أصلين", few: "أصول", many: "أصلًا" },
  lafz: { one: "لفظ", two: "لفظين", few: "ألفاظ", many: "لفظًا" },
  mawdi: { one: "موضع", two: "موضعين", few: "مواضع", many: "موضعًا" },
  root: { one: "جذر", two: "جذرين", few: "جذور", many: "جذرًا" },
  /**
   * Noun + adjective as one form. The adjective agrees with the number too
   * («فواصل مميّزة», «فاصلتين مميّزتين»), so storing the bare noun and
   * appending the adjective would need a second agreement rule; a phrase
   * needs none.
   */
  fasilaMumayyaza: {
    one: "فاصلة مميّزة",
    two: "فاصلتين مميّزتين",
    few: "فواصل مميّزة",
    many: "فاصلة مميّزة",
  },
  ayaMuhallala: {
    one: "آية محلَّلة",
    two: "آيتين محلَّلتين",
    few: "آيات محلَّلة",
    many: "آية محلَّلة",
  },
  /** A «وجه» of a letter: one member of its sense bundle. */
  wajh: { one: "وجه", two: "وجهين", few: "وجوه", many: "وجهًا" },
  minute: { one: "دقيقة", two: "دقيقتين", few: "دقائق", many: "دقيقة" },
  hour: { one: "ساعة", two: "ساعتين", few: "ساعات", many: "ساعة" },
  day: { one: "يوم", two: "يومين", few: "أيام", many: "يومًا" },
} as const satisfies Record<string, NounForms>;

/**
 * The Lisan enum dictionaries.
 *
 * They are declared apart from `S` only to carry an explicit `Record<Enum, string>`
 * annotation: that is what turns a backend enum member added without a label here
 * into a COMPILE error instead of a blank badge on the page. They are read through
 * `S.lexical.*` like every other string — nothing imports them directly.
 */

/** Where a letter sits in the root. */
const POSITIONS: Record<SensePosition, string> = {
  initial: "أول",
  medial: "وسط",
  final: "آخر",
  any: "أيّ موضع",
};

export const S = {
  /** The application's only name. The old Latin brand appears nowhere —
   *  including here: naming it would be the sole hit of the 9.2c check. */
  app: {
    name: "القرآن بالقرآن",
    /** <title> — kept identical to the name so the browser tab is recognisable. */
    title: "القرآن بالقرآن",
    /** <meta name="description"> */
    description:
      "دراسةُ القرآن بالقرآن: سؤالٌ يُجاب من نصّ الآيات، وتتبُّعٌ للجذر في مواضعه، وقراءةٌ للآية في سياقها.",
  },

  nav: {
    chat: "محاورة القرآن",
    surahs: "سور القرآن",
    verseStudy: "دراسة الآيات",
    fassila: "فواصل الآيات والسور",
    lexical: "تحليل لساني عربي",
    roots: "فهرس الجذور",
    /** Not in the navigation — the page keeps its name for its heading and deep links. */
    qlisan: "بطاقة الكلمة",
    openMenu: "فتح القائمة",
    closeMenu: "إغلاق القائمة",
  },

  /**
   * Landing page. Rewritten rather than translated: the English prose led with
   * trilingual question-answering, which is no longer what the product leads with.
   */
  home: {
    heading: "دراسةُ القرآن بالقرآن",
    lede: "أداةٌ لقراءة القرآن ودراسة ألفاظه: تسأل فتُجاب من نصّ الآيات، وتتتبّع الجذر في مواضعه، وتقرأ الآية في سياقها. وكلُّ قولٍ مسنَدٌ إلى آيته.",
    /* The hero had two buttons of its own, pointing at routes the cards
       below already carry. They are gone: the cards are the single entry
       point, so a destination is named exactly once. The verb phrases live
       here, where a description is followed by an invitation. */
    cards: {
      chat: {
        title: "محاورة القرآن",
        desc: "اطرح سؤالك فتأتيك إجابةٌ مبنيّةٌ على نصّ الآيات، وكلُّ دعوى فيها مسنَدةٌ إلى الآيات التي جاءت منها.",
        cta: "ابدأ محاورة",
      },
      verseStudy: {
        title: "دراسة الآيات",
        desc: "اكتب كلمةً عربيّةً واحدةً، فترى كلَّ آيةٍ ورد فيها جذرها في القرآن كلِّه، مشكولةً، والكلمةُ مميَّزةٌ في موضعها.",
        cta: "ادرس كلمة",
      },
      lexical: {
        title: "تحليل لساني عربي",
        desc: "اطلب اللفظ بجذره، فترى مواضعه في القرآن وما يحمله من وجوه المعنى باختلاف السياق.",
        cta: "حلِّل كلمة",
      },
    },
    note: "الأجوبةُ مستوًى أوّلُ من النظر، وهي تذكر مصادرها دائمًا؛ ولا تقوم مقام التفسير.",
  },

  chat: {
    placeholder: "اكتب سؤالك…",
    /** Accessible name for the composer. A placeholder is only the
     *  fallback name in the accname spec, and it disappears on the
     *  first keystroke — so the field is left unnamed exactly while it
     *  is being used. */
    inputLabel: "سؤالك",
    send: "إرسال",
    empty: "اطرح سؤالًا عن القرآن.",
    exampleHint: "مثال: ما يقول القرآن عن الصبر؟",
    retry: "أعد المحاولة",
    conversations: "المحادثات",
    newConversation: "محادثة جديدة",
    /** The stacked button under the switcher — short on purpose. */
    newShort: "جديدة",
    noSaved: "لا توجد محادثات محفوظة",
    deleteConversation: "حذف المحادثة",
    sources: "المصادر",
    noVerses: "لم تُطابِق أيُّ آية — جوابٌ عامّ.",
    helpful: "مفيد",
    notHelpful: "غير مفيد",
    /** Relative time for the conversation switcher (design D18). */
    justNow: "الآن",
    minutesAgo: (n: number) => `قبل ${count(n, NOUNS.minute)}`,
    hoursAgo: (n: number) => `قبل ${count(n, NOUNS.hour)}`,
    daysAgo: (n: number) => `قبل ${count(n, NOUNS.day)}`,
  },

  verseStudy: {
    /** Nothing found for the typed word. */
    notFound: "لم يُعثر على هذه الكلمة في الجذور المعروفة",
    /** The box held a phrase: the lookup reads one word. */
    oneWordOnly: "اكتب كلمةً واحدةً فقط، لا عبارة — فالبحث يتتبّع جذرَ كلمةٍ واحدة.",
    /** Lead-in of the «هل تقصد» suggestions — each one a button. */
    didYouMean: "هل تقصد:",
    heading: "دراسة الآيات",
    caption: "اكتب كلمةً عربيّةً واحدةً — فترى كلَّ آيةٍ ورد فيها جذرها، مشكولةً.",
    tabs: {
      word: "الكلمة في الآيات",
      /** «النظائر» is rejected: it names a different discipline (design D21). */
      similar: "الآيات المتشابهات",
      context: "الآية في سياقها",
    },
    search: "بحث",
    wordPlaceholder: "اكتب كلمة عربية",
    phrasePlaceholder: "اكتب آية أو عبارة",
    /** Accessible names — see `chat.inputLabel` for why these are not
     *  the placeholders repeated. */
    wordLabel: "الكلمة",
    phraseLabel: "الآية أو العبارة",
    /**
     * Echoes the user's own query. The query may be Latin script, so the guillemets
     * and the token go through `iso()` together — otherwise the mirrored guillemets
     * reorder around a Latin run and the sentence breaks. The caller additionally
     * renders the span `dir="auto"` (design D15, D19).
     */
    questionWord: (word: string) =>
      `ما هي الآيات والسور التي وردت فيها ${iso(`«${word}»`)} ؟`,
    questionPhrase: (q: string) =>
      `ما هي الآيات القريبة في المعنى والتركيب اللغوي من ${iso(`«${q}»`)} ؟`,
    similarNote: `بحثٌ بالجذر واللفظ في ${iso(6236)} آية، مرتَّبٌ بحسب القرب في المعنى — يُعيد أقرب المواضع.`,
    nearest: (n: number) => `أقرب ${count(n, NOUNS.aya)}`,
    contextCaption: "اختر السورة والآية لقراءتها في سياقها — مع الآيات الثلاث قبلها وبعدها.",
    showVerse: "اعرض الآية",
    loadingContext: "جارٍ تحميل السياق…",
    root: "الجذر",
    properNoun: "اسم علم",
    formJump: "اذهب إلى مواضع هذا اللفظ",
    openInContext: "افتح الآية في سياقها",
    noneFound: "لم يُعثر على آيات قريبة",
    /**
     * Label fragments, not whole sentences. The counted-noun rule of `count()`
     * does not apply here: «عدد الآيات» is a definite plural in an annexation, so
     * one form is correct for every value. They are fragments rather than
     * functions because the sentence they belong to embeds one clickable button
     * per لفظ, so it has to be composed in JSX (design D5).
     */
    ayahCountLabel: "عدد الآيات :",
    surahCountLabel: "عدد السور :",
    lafzCountLabel: "عدد الألفاظ :",
    /**
     * The ordering control of "Word in Verses". It sorts on «عدد الآيات» — the
     * count each row already prints, on the لفظ block header as on the surah
     * card — not on مواضع: the header also counts words, and a control that
     * silently ranked on a different number than the one on screen would be
     * unreadable. «حسب المصحف» is the backend's own order and stays the default;
     * the two others name what is being counted rather than saying
     * تصاعدي/تنازلي, which would leave "more of what?" unanswered. آياتٍ is a
     * tamyīz — منصوب, and a sound feminine plural takes kasra there.
     *
     * The label is «الترتيب», not «ترتيب السور» as it read when the control
     * moved only the surah cards: one selection now orders the لفظ blocks AND
     * the cards inside them, so naming a single level would be false on screen.
     */
    sortLabel: "الترتيب :",
    sortMushaf: "حسب المصحف",
    sortDesc: "الأكثر آياتٍ",
    sortAsc: "الأقلّ آياتٍ",
    sortGroupLabel: "الترتيب",
  },

  qlisan: {
    notYetAvailable: "غير متاح بعد.",
    noIrab: "لا يوجد إعراب محقّق لهذه الكلمة.",
    heading: "بطاقة الكلمة",
    caption:
      "اختر آيةً، ثم اضغط كلمةً واحدةً لترى تحليلها في أربعة مستويات — صوتي، صرفي، نحوي، دلالي. والصرفُ والنحوُ مأخوذان على وجه الحتم من المدوّنة المُعرَبة، لا من نموذج لغويّ.",
    loadVerse: "اعرض الآية",
  },

  lexical: {
    heading: "تحليل لساني عربي",
    /**
     * The sections in the order the page renders them: the verified root, its
     * letters with Samer Islambouli's gloss — named as HIS — then the
     * occurrences and the morphology.
     *
     * It used to read «اكتب كلمةً عربيّةً لقراءة جذرها حرفًا حرفًا — قراءةٌ تأويليّةٌ
     * لرمزيّة الحروف في اللسان», which led with the letters and let the whole page
     * be read as a tool that derives a root's meaning from them. It does not, and
     * the first sentence a reader sees is where that has to be said.
     */
    caption:
      "اكتب كلمةً عربيّةً فترى جذرَها المُحقَّق، ودلالةَ حروفه كما نشرها سامر إسلامبولي منسوبةً إليه، ومواضعَه في الآيات، وصرفَه وإعرابَه.",
    analyze: "حلِّل",
    word: "الكلمة",
    /** The input's example word. It was the last Arabic literal left in a
     *  component — and an example word IS interface copy: it teaches what the
     *  field takes (one bare word, not a phrase), so it is reviewed here. */
    wordPlaceholder: "رحمة",
    loading: "جارٍ قراءة الجذر… (قد يستغرق التركيبُ لحظة)",
    /** Renamed from «تحليل نحوي» to end the D11 collision; SarfiRows renders صرف. */
    sarfiSection: "الصرف والإعراب",
    /** Fallbacks for a backend `message` field that arrives empty. They were
     *  Arabic already, and inline — which is how a string escapes the review
     *  gate: nothing about them looks like a translation to be done. */
    noSarfi: "لا يوجد تحليل صرفي لهذه الكلمة.",
    noRoot: (word: string) => `لم يُعرف جذرٌ للكلمة ${iso(`«${word}»`)}.`,

    /* ── The root header ─────────────────────────────────────────────── */
    rootLabel: "الجذر",
    fallbackBadge: "جذر تقديري",
    fallbackBadgeTitle: `جذر تقديري من المُجذِّر الحدسي، لا من مدوّنة ${iso("QAC")} المُحقَّقة.`,
    /** The «معطى محقّق» chip on the morphology section. */
    verifiedDatum: "معطى محقّق",

    /* ── المواضع: the attested occurrences, above everything composed ──
     *
     * Figures and a short sample only. The exhaustive vocalized display with
     * the matched word highlighted belongs to «دراسة الآية», and this section
     * links there rather than growing a second copy of it. */
    occurrencesHeading: "المواضع",
    occurrencesNote: `ورودُ الجذر في القرآن كما تُثبِته مدوّنةُ ${iso("QAC")} المُحقَّقة.`,
    /** «339 موضعًا» / «313 آية» / «31 لفظًا» — three figures, each counted on its
     *  own set and none the sum of another: رحم is 339 words in 313 āyāt written
     *  as 31 ألفاظ. No label in front of any: the counted noun already says what
     *  is counted, and «عدد الآيات : 313 آية» says it twice.
     *
     *  The same three «الكلمة في الآيات» prints, from the same computation — a
     *  لفظ there is a WRITTEN form (proclitics stripped, grammatical-tool
     *  occurrences out), where this page used to show vocalized surfaces and
     *  count رَحْمَةً / رَحْمَةٍ / رَحْمَةُ as three. */
    occurrencesWords: (n: number) => count(n, NOUNS.mawdi),
    occurrencesAyat: (n: number) => count(n, NOUNS.aya),
    occurrencesForms: (n: number) => count(n, NOUNS.lafz),
    formsLabel: "الألفاظ :",
    /** The sample is a SAMPLE and says so; the remainder is stated as a number
     *  rather than trailed off, so the reader knows what is not on screen. */
    occurrencesSampleLabel: "من مواضعه :",
    occurrencesMore: (n: number) => `و${count(n, NOUNS.aya)} أخرى`,
    occurrencesLink: "اعرض المواضع كاملةً، مشكولةً، في «دراسة الآيات»",
    /** A root QAC records with no occurrence — the state is stated, not blank. */
    noOccurrences: "لم يُسجَّل لهذا الجذر موضعٌ في المدوّنة.",

    /* ── The letters: name, مخرج, position, and Islambouli's gloss ──
     *
     * The gloss is HIS, quoted verbatim from the frozen transcription of his
     * published table, and the note says so before any card is read. It is
     * never selected against the aṣl and never composed into a sentence. */
    lettersHeading: "حروف الجذر",
    lettersNote:
      "دلالةُ كلِّ حرفٍ كما نشرها سامر إسلامبولي في جدوله، منقولةً بنصِّها ومنسوبةً إليه — قولُه، لا استنباطُ هذا التطبيق.",
    islambouliMissing: "لا دلالةَ لهذا الحرف في جدول إسلامبولي.",
    // ── Islambouli: his sentence, the project's assembly, the gap ──
    citedHeading: "ما نشره إسلامبولي لهذا الجذر",
    citedAttribution: "سامر إسلامبولي — برنامج «مفاهيم»، منقولٌ بنصّه وبعنوانه كما طُبع",
    citedClassification:
      "تصنيفُ هذه الجملة «حالةً فيزيائية» تصنيفُنا نحن لا عنوانُه؛ فالعنوان المطبوع هو المعروض.",
    assemblyHeading: "تركيب الأسطر الثلاثة",
    assemblyLabel:
      "تركيبٌ آليٌّ للأسطر الثلاثة، من صنع هذا التطبيق — لا تعريفٌ، ولا قولُ إسلامبولي",
    assemblyAlternativesNote:
      "ما بين القوسين بدائلُ يذكرها الجدول بـ«أو»؛ لا يختار التطبيقُ بينها.",
    assemblyChoiceBy: (author: string) =>
      `اختيارُ ${author} بين البدائل — تأويلٌ، لا من الجدول`,
    assemblyRefused: "لا تركيب لهذا الجذر:",
    gapHeading: "الفرق بين الجملتين",
    gapOnlyAssembly: "في التركيب وحده:",
    gapOnlyCited: "في جملة إسلامبولي وحدها:",
    gapNone: "—",
    assemblyPosition: { opens: "الحرف الأول", body: "الحرف الثاني", concludes: "الحرف الثالث" },
    chooseLabel: (position: string) => `اختر بديلًا (${position}):`,
    chooseAll: "كلُّ البدائل",
    // ── the cultural stage, only when sourced ──
    culturalHeading: "الحالة الثقافية",
    culturalCited: "سامر إسلامبولي — منقولٌ بنصّه",
    culturalPersonal: (author: string) => `قراءةٌ شخصية — ${author}`,
    // ── the signed personal reading ──
    readingSummary: "قراءتك الشخصية (موقَّعةٌ باسمك)",
    readingAuthor: "الاسم",
    readingAuthorRequired: "اكتب اسمك أولًا: كلُّ اختيارٍ وكلُّ قراءةٍ تُنسب إلى صاحبها.",
    readingText: "الحالة الثقافية كما تقرؤها أنت",
    readingSave: "احفظ",
    readingSaved: "حُفظت.",
    readingFailed: "تعذّر الحفظ.",
    positionLabel: "الموضع",
    position: POSITIONS,

  },

  /**
   * «فهرس الجذور» — the root inventory, browsed by first radical.
   *
   * The reading on each card is the project's mechanical assembly, shown under
   * `S.lexical.assemblyLabel` and refused with `S.lexical.assemblyRefused` —
   * read from there, not retyped, so the index and `/lexical` cannot word the
   * same disclaimer two ways. Islambouli's own sentence and the cultural stage
   * have no string here because the page never shows them.
   */
  roots: {
    heading: "فهرس الجذور",
    caption:
      "جذورُ القرآن مرتَّبةً على حروف المعجم، لا يُكتب فيها شيء: لكلِّ جذرٍ مواضعُه وآياتُه وسورُه، وتركيبٌ آليٌّ لحروفه الثلاثة.",
    /** The whole inventory, under the strip: «1654 جذرًا في القرآن». */
    total: (n: number) => `${count(n, NOUNS.root)} في القرآن`,
    lettersLabel: "حروف المعجم",
    /** The accessible name of one strip button — the visible face is the
     *  letter over its digit, which a screen reader would read as two words. */
    letterButton: (letter: string, n: number) => `${letter} — ${count(n, NOUNS.root)}`,
    pickLetter: "اختر حرفًا لترى الجذور التي تبدأ به.",
    loading: "جارٍ تحميل الجذور…",
    noRoots: "لا جذرَ في القرآن يبدأ بهذا الحرف.",
    /** «ب — 81 جذرًا». */
    groupHeading: (letter: string, n: number) => `${letter} — ${count(n, NOUNS.root)}`,
    /** One notice for the page when the letter or وصف table fails its lock:
     *  the figures are still served, the readings are not. */
    readingsUnavailable:
      "جدولُ الحروف أو جدولُ الوصف لا يطابق نسختَه المقفلة، فلا تُعرض التراكيب الآليّة في هذه الصفحة؛ أمّا الجذور وأعدادها فمعروضةٌ كما هي.",
    surahsLabel: "السور :",
    /** The root's distinct written forms — the Quran's words that come from it. */
    formsLabel: "المواضع :",
    /** The fold control's accessible name. */
    expandCard: (root: string) => `اعرض تفاصيل الجذر ${root}`,
    collapseCard: (root: string) => `أخفِ تفاصيل الجذر ${root}`,
    openVerseStudy: "الكلمة في الآيات",
    openLexical: "تحليل لساني",
  },

  /** Shared verse chrome. */
  verse: {
    loadingSurah: "جارٍ تحميل السورة…",
    loadingVerse: "جارٍ تحميل الآية…",
    ayahNumber: "رقم الآية",
    surah: "السورة",
    ayahLabel: (n: number) => `الآية ${n}`,
    ayahCount: (n: number) => count(n, NOUNS.aya),
    juz: (n: number) => `الجزء ${n}`,
    score: "درجة المطابقة",
    openSurah: "اعرض السورة كاملة",
    prevSurah: "السورة السابقة",
    nextSurah: "السورة التالية",
    prevAyah: "الآية السابقة",
    nextAyah: "الآية التالية",
    backToStudy: "رجوع إلى دراسة الآيات",
    /**
     * Backend `period` values, mapped rather than rendered raw. The keys are the
     * transliterations the corpus actually emits — `makkiyya` (4613 verses) and
     * `madani` (1623), asymmetric in the source and not the `Meccan` / `Medinan`
     * pair one would guess. Verified against `verses_final.json` and `GET /surah/1`.
     */
    period: { makkiyya: "مكية", madani: "مدنية" },
  },

  /** The «سور القرآن» reading page: the picker above the surah, and its failures. */
  reading: {
    pickerLabel: "اختر السورة",
    /** The picker's placeholder on the main page, shown greyed out. */
    pickerPlaceholder: "سور القرآن العظيم",
    /** Option text: «2 · البقرة» — Western digits, like every other numeral
     *  in the interface. */
    option: (n: number, name: string) => `${n} · ${name}`,
    loadingSurahs: "جارٍ تحميل السور…",
    /** The picker failed while the surah itself may still be readable, so the
     *  note invites a retry rather than reporting the page as broken. */
    surahsFailed: "تعذّر تحميل قائمة السور؛ أعد المحاولة.",
    heading: "سور القرآن",
    caption:
      "اقرأ السورة كاملةً بنصّها المشكول، آيةً بعد آية، ثم انتقل إلى ما قبلها أو ما بعدها.",
    /** The range tabs of a long surah (more than one chunk of āyāt). */
    rangesLabel: "مقاطع السورة",
    /** Under the block: the next range, «الآيات 51–100». */
    nextRange: "الآيات التالية",
  },

  health: {
    /** Names no script path: `local-dev/start.sh` is git-excluded (task 6.1a). */
    unreachable: "تعذّر الاتصال بالخادم؛ تأكّد من تشغيله ثم أعد المحاولة.",
    starting: "الخادمُ في طور التشغيل؛ قد لا تتوفّر الأجوبة بعد.",
    degraded: (parts: string) =>
      `الخدمةُ منقوصة: ${parts} غير متاح. وقد تتعذّر الأجوبة حتى يستعيد عمله.`,
    partIndex: `فهرس البحث ${iso("(Qdrant)")}`,
    partModel: `نموذج اللغة ${iso("(Ollama)")}`,
    /**
     * Join for the degraded list. The waw is a proclitic: a space BEFORE it and none
     * after. `join(" و ")` is wrong Arabic.
     */
    and: " و",
    fallbackPart: "أحدُ المكوّنات",
  },

  /**
   * Failure sentences, selected by KIND rather than one per call site, so an
   * actionable backend diagnostic does not become vaguer in Arabic than it was in
   * English (design D17). Raw exception text is never the sentence; it may appear as
   * a subordinate dir="ltr" lang="en" line under `detailLabel`.
   */
  errors: {
    nonArabicWord: "تُكتب الكلمة بالحرف العربي.",
    emptyInput: "اكتب كلمةً أوّلًا.",
    verseNotFound: "لا وجود لهذه الآية.",
    wordNotFound: "لا وجود لهذه الكلمة في هذا الموضع.",
    surahNotFound: "لا وجود لهذه السورة.",
    surahListFailed: "تعذّر تحميل قائمة السور.",
    rootLetterNotFound: "ليس هذا من حروف المعجم.",
    rootIndexFailed: "تعذّر تحميل فهرس الجذور.",
    analysisFailed: "تعذّر التحليل.",
    searchFailed: "تعذّر البحث.",
    unavailable: "الخدمةُ غير متاحة مؤقّتًا.",
    unreachable: "تعذّر الاتصال بالخادم.",
    generic: "تعذّر إتمام الطلب.",
    detailLabel: "تفصيل تقنيّ",
  },

  /** Scroll-to-top control. */
  common: {
    scrollToTop: "الرجوع إلى الأعلى",
  },
} as const;

/** The failure kinds `forStatus` distinguishes. */
export type FailureKind =
  | "nonArabicWord"
  | "emptyInput"
  | "verse"
  | "word"
  | "surah"
  | "surahList"
  | "rootIndex"
  | "analysis"
  | "search"
  | "chat"
  | "network";

/**
 * Choose the Arabic sentence for a failure. `status` is the HTTP status when there
 * was a response, `undefined` when the fetch itself rejected.
 */
export function forStatus(status: number | undefined, kind?: FailureKind): string {
  if (status === undefined) return S.errors.unreachable;
  if (status === 400 || status === 422) {
    if (kind === "nonArabicWord") return S.errors.nonArabicWord;
    if (kind === "emptyInput") return S.errors.emptyInput;
  }
  if (status === 404) {
    if (kind === "word") return S.errors.wordNotFound;
    if (kind === "surah") return S.errors.surahNotFound;
    if (kind === "rootIndex") return S.errors.rootLetterNotFound;
    return S.errors.verseNotFound;
  }
  if (status === 503) return S.errors.unavailable;
  if (kind === "surahList") return S.errors.surahListFailed;
  if (kind === "rootIndex") return S.errors.rootIndexFailed;
  if (kind === "analysis") return S.errors.analysisFailed;
  if (kind === "search") return S.errors.searchFailed;
  // A chat turn needs no sentence of its own: a failure there is either an
  // outage or the network, both already covered above.
  if (kind === "chat") return S.errors.generic;
  return S.errors.generic;
}
