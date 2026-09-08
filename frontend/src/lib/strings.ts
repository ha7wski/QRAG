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
 * writing «١ آية» or «٢ آيتين» is redundant and reads as a machine translation.
 */
export function count(n: number, forms: NounForms, digits = String(n)): string {
  const k = Math.abs(Math.trunc(n));
  if (k === 1 || k === 2) return nounFor(k, forms);
  return `${digits} ${nounFor(k, forms)}`;
}

/** The noun series the interface counts. */
export const NOUNS = {
  aya: { one: "آية", two: "آيتين", few: "آيات", many: "آية" },
  surah: { one: "سورة", two: "سورتين", few: "سور", many: "سورة" },
  fasila: { one: "فاصلة", two: "فاصلتين", few: "فواصل", many: "فاصلة" },
  asl: { one: "أصل", two: "أصلين", few: "أصول", many: "أصلًا" },
  lafz: { one: "لفظ", two: "لفظين", few: "ألفاظ", many: "لفظًا" },
  minute: { one: "دقيقة", two: "دقيقتين", few: "دقائق", many: "دقيقة" },
  hour: { one: "ساعة", two: "ساعتين", few: "ساعات", many: "ساعة" },
  day: { one: "يوم", two: "يومين", few: "أيام", many: "يومًا" },
} as const satisfies Record<string, NounForms>;

export const S = {
  /** The application's only name. "Quran RAG" appears nowhere. */
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
    verseStudy: "دراسة الآية",
    fassila: "الفواصل",
    lexical: "تحليل اللسان",
    tahlil: "التحليل النحوي",
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
    cta: "ابدأ المحاورة",
    cards: {
      chat: {
        title: "محاورة القرآن",
        desc: "اطرح سؤالك فتأتيك إجابةٌ مبنيّةٌ على نصّ الآيات، وكلُّ دعوى فيها مسنَدةٌ إلى الآيات التي جاءت منها.",
      },
      verseStudy: {
        title: "دراسة الآية",
        desc: "اكتب كلمةً عربيّةً واحدةً، فترى كلَّ آيةٍ ورد فيها جذرها في القرآن كلِّه، مشكولةً، والكلمةُ مميَّزةٌ في موضعها.",
      },
      lexical: {
        title: "تحليل اللسان",
        desc: "اطلب اللفظ بجذره، فترى مواضعه في القرآن وما يحمله من وجوه المعنى باختلاف السياق.",
      },
    },
    note: "الأجوبةُ مستوًى أوّلُ من النظر، وهي تذكر مصادرها دائمًا؛ ولا تقوم مقام التفسير.",
  },

  chat: {
    placeholder: "اكتب سؤالك…",
    send: "إرسال",
    empty: "اطرح سؤالًا عن القرآن.",
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
    heading: "دراسة الآية",
    caption: "اكتب كلمةً عربيّةً واحدةً — فترى كلَّ آيةٍ ورد فيها جذرها، مشكولةً.",
    tabs: {
      word: "الكلمة في الآيات",
      /** «النظائر» is rejected: it names a different discipline (design D21). */
      similar: "الآيات القريبة في المعنى",
      context: "الآية في سياقها",
    },
    search: "بحث",
    wordPlaceholder: "اكتب كلمة عربية",
    phrasePlaceholder: "اكتب آية أو عبارة",
    /**
     * Echoes the user's own query. The query may be Latin script, so the guillemets
     * and the token go through `iso()` together — otherwise the mirrored guillemets
     * reorder around a Latin run and the sentence breaks. The caller additionally
     * renders the span `dir="auto"` (design D15, D19).
     */
    questionWord: (word: string) =>
      `ما هي الآيات والسور التي وردت فيها ${iso(`«${word}»`)} ؟`,
    questionPhrase: (q: string) =>
      `ما هي الآيات القريبة في المعنى من ${iso(`«${q}»`)} ؟`,
    similarNote: `بحثٌ بالجذر واللفظ في ${iso(6236)} آية، مرتَّبٌ بحسب القرب في المعنى — يُعيد أقرب المواضع.`,
    nearest: (n: number) => `أقرب ${count(n, NOUNS.aya)}`,
    contextCaption: "اختر السورة والآية لقراءتها في سياقها — مع الآيات الثلاث قبلها وبعدها.",
    showVerse: "اعرض الآية",
    loadingContext: "جارٍ تحميل السياق…",
    root: "الجذر",
    ayahCount: (n: number, digits: string) => `عدد الآيات : ${digits}`,
    surahCount: (n: number, digits: string) => `عدد السور : ${digits}`,
    lafzCount: (n: number, digits: string) => `عدد الألفاظ : ${digits}`,
  },

  qlisan: {
    heading: "بطاقة الكلمة",
    caption:
      "اختر آيةً، ثم اضغط كلمةً واحدةً لترى تحليلها في أربعة مستويات — صوتي، صرفي، نحوي، دلالي. والصرفُ والنحوُ مأخوذان على وجه الحتم من المدوّنة المُعرَبة، لا من نموذج لغويّ.",
    loadVerse: "اعرض الآية",
  },

  tahlil: {
    heading: "التحليل النحوي",
    caption:
      "اختر آيةً، ثم اضغط كلمةً لترى تحليلها في خمسة أبواب — الحروف، صرفي، نحوي، دلالي، تركيب. وكلُّ دعوى تحمل شارةَ مصدرها والدليلَ الذي تقوم عليه؛ والشارةُ تُخبر من أين جاءت العبارة، لا أنّها صحيحة.",
    loadVerse: "اعرض الآية",
  },

  lexical: {
    heading: "تحليل اللسان",
    caption:
      "اكتب كلمةً عربيّةً لقراءة جذرها حرفًا حرفًا — قراءةٌ تأويليّةٌ لرمزيّة الحروف في اللسان.",
    analyze: "حلِّل",
    word: "الكلمة",
    loading: "جارٍ قراءة الجذر… (قد يستغرق التركيبُ لحظة)",
    /** Renamed from «تحليل نحوي» to end the D11 collision; SarfiRows renders صرف. */
    sarfiSection: "الصرف والإعراب",
    /** LexicalResult — kept for the interim; the restructure deletes the component. */
    resultRoot: "الجذر",
    resultAnalysis: "التحليل",
    resultKeyVerses: "آياتٌ شاهدة",
    noRoot: (word: string) => `لم يُعرف جذرٌ للكلمة ${iso(`«${word}»`)}.`,
  },

  /** Shared verse chrome. */
  verse: {
    ayahNumber: "رقم الآية",
    surah: "السورة",
    surahNumber: (digits: string) => `السورة ${digits}`,
    ayahCount: (n: number, digits: string) => count(n, NOUNS.aya, digits),
    juz: (digits: string) => `الجزء ${digits}`,
    score: "درجة المطابقة",
    openSurah: "اعرض السورة كاملة",
    prevSurah: "السورة السابقة",
    nextSurah: "السورة التالية",
    prevAyah: "الآية السابقة",
    nextAyah: "الآية التالية",
    backToStudy: "رجوع إلى دراسة الآية",
    /**
     * Backend `period` values, mapped rather than rendered raw. The keys are the
     * transliterations the corpus actually emits — `makkiyya` (4613 verses) and
     * `madani` (1623), asymmetric in the source and not the `Meccan` / `Medinan`
     * pair one would guess. Verified against `verses_final.json` and `GET /surah/1`.
     */
    period: { makkiyya: "مكية", madani: "مدنية" },
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
  | "analysis"
  | "search"
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
    return S.errors.verseNotFound;
  }
  if (status === 503) return S.errors.unavailable;
  if (kind === "surahList") return S.errors.surahListFailed;
  if (kind === "analysis") return S.errors.analysisFailed;
  if (kind === "search") return S.errors.searchFailed;
  return S.errors.generic;
}
