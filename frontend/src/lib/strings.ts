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

import type {
  ConceptPosition,
  Confidence,
  ConfrontationVerdict,
  CoreStatus,
  PositionKind,
  DiscardReason,
  MatchedRule,
  Polarity,
  PrimitiveStatus,
  SensePosition,
  SentenceSource,
  UseVerdict,
} from "./lisanTypes";

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

/** Why a sense was dropped, in the reader's words. `outranked` is not a rejection:
 *  the sense was eligible and lost the ranking, which is a different fact. */
const DISCARD_REASONS: Record<DiscardReason, string> = {
  "no-shared-axis": "لا يشترك مع أصل الجذر في محور",
  "conflicting-axis": "يحمل محورًا مضادًّا لمحور الأصل",
  "wrong-position": "نصَّ صاحبُه على موضعٍ آخر من اللفظة",
  outranked: "مؤهَّل لكنه دون المختار في الترتيب",
};

/** What selected the sense. Keyed on `MatchedRule`, not `SelectionRule`: the
 *  `unmatched` case renders the stated gap («بلا وجهٍ مختار» + its sentence), so a
 *  label for it would be a string no code path can reach. */
const SELECTION_RULES: Record<MatchedRule, string> = {
  "axis-match": "اشتراكٌ في المحور",
  "axis-match+position": "اشتراكٌ في المحور وموافقةُ الموضع",
};

/** The charge of an aṣl or of a sense. `neutral` is a verdict, not a blank. */
const POLARITIES: Record<Polarity, string> = {
  positive: "إيجابي",
  negative: "سلبي",
  neutral: "محايد",
};

/** How well sourced a sense is (the backend ranks verified > high > summary). */
const CONFIDENCES: Record<Confidence, string> = {
  verified: "مُحقَّق",
  high: "مُرجَّح",
  summary: "مُلخَّص",
};

/** Where a letter sits, or where a sense applies. */
/**
 * Why there is no core — and the headings are asymmetric ON PURPOSE.
 *
 * Two of them report OUR gap; only `no_asl_in_source` speaks for Ibn Fāris, and
 * it is used only where the dataset positively records that his entry states no
 * aṣl. The page used to head every one of them «لا أصلَ منصوصًا لهذا الجذر»,
 * which for حرب is false — he gives three aṣl there, and محراب belongs to the
 * third. A heading that lends an authority a silence he never kept is a factual
 * error, not a wording preference.
 */
const CORE_STATUSES: Record<CoreStatus, string> = {
  not_curated: "أصلٌ مذكورٌ عند ابن فارس، لم يُسجَّل بعدُ في هذا المشروع",
  not_recorded: "لا أصلَ مُسجَّلًا في هذا المشروع لهذا الجذر",
  no_asl_in_source: "لم يذكر ابن فارس أصلًا لهذا الجذر",
};

/** What a stated position claims. Shown beside the position itself, because
 *  «mostly in final» and «only in final» are different claims and the page
 *  should not let a proportion read as a rule. */
const POSITION_KINDS: Record<PositionKind, string> = {
  exclusive: "حصراً",
  dominant: "غالباً",
};

const POSITIONS: Record<SensePosition, string> = {
  initial: "أول",
  medial: "وسط",
  final: "آخر",
  any: "أيّ موضع",
};

/* ── The physics-first engine's vocabulary (POST /lisan/concept) ────────────
 *
 * The API sends the ENGLISH keys `opens` / `body` / `concludes` and nothing else:
 * the positional rule is the backend's, the Arabic wording is the page's, exactly
 * as `LetterIdentity.position` already splits it. These maps are the whole of
 * that wording, and the `Record<Enum, string>` annotation is what turns a fourth
 * position — should the rule ever be widened — into a compile error here rather
 * than a nameless card on screen.
 */

/** The role each radical plays, by the rule fixed before any root was composed. */
const CONCEPT_ROLES: Record<ConceptPosition, string> = {
  opens: "يَفتَح",
  body: "جَسَد",
  concludes: "يَختِم",
};

/** Which radical it is. Named beside the role so a group states both — the
 *  reading aid has to say WHICH letter it is grouping, or it is just a third of
 *  a sentence with no owner. */
const CONCEPT_ORDINALS: Record<ConceptPosition, string> = {
  opens: "الحرف الأوَّل",
  body: "الحرف الثاني",
  concludes: "الحرف الثالث",
};

/** The role spelled out as the rule states it, for the card's own line. */
const CONCEPT_ROLE_SENTENCES: Record<ConceptPosition, string> = {
  opens: "يفتَحُ الحدث",
  body: "جسَدُ الحدث",
  concludes: "يختِمُ الحدث",
};

/**
 * The sourcing regime of a primitive — and the two labels are deliberately
 * asymmetric, because the facts are.
 *
 * `attested` means a named authority with real pages states the mapping;
 * `hypothesis` means THIS PROJECT asserts it, resting on an uncontested tajwīd
 * fact rather than on anyone's word. Most rows are hypotheses, and a badge that
 * read the same for both would publish the project's own construction as if it
 * were transmitted scholarship.
 */
const PRIMITIVE_STATUSES: Record<PrimitiveStatus, string> = {
  attested: "منصوص",
  hypothesis: "فرضُ المشروع",
};

const PRIMITIVE_STATUS_TITLES: Record<PrimitiveStatus, string> = {
  attested: "نصَّ على هذه النسبة مصدرٌ مُسمًّى بصفحاته",
  hypothesis: "دعوى هذا المشروع، مبناها واقعةٌ تجويديةٌ لا خلافَ فيها، لا قولُ عالِم",
};

/** Where the concept's sentence came from. The template is the ground truth; the
 *  generated phrasing is an optional pass that may only re-word what the template
 *  already realised, and is vetoed before it can reach the page. */
const SENTENCE_SOURCES: Record<SentenceSource, string> = {
  template: "قالبٌ حتميّ",
  phrasing: "صياغةٌ مولَّدة",
};

/** Whether the مفهوم covers one attested Quranic sense. `not_judged` is the
 *  mandated intermediate state — the uses were frozen before the concept
 *  existed — and it is not a middle grade between the other two. */
const USE_VERDICTS: Record<UseVerdict, string> = {
  covered: "يشملُه المفهوم",
  not_covered: "لا يشملُه المفهوم",
  not_judged: "لم يُحكَم بعد",
};

/** The root-level coverage verdict. Never rendered without the reservation
 *  beside it — see `S.concept.reservationLabel`. */
const CONFRONTATION_VERDICTS: Record<ConfrontationVerdict, string> = {
  covers_all: "يشملُ الوجوهَ المُثبَتةَ كلَّها",
  partial: "يشملُ بعضَ الوجوهِ المُثبَتة",
  not_recorded: "لم يُسجَّل حكمٌ بعد",
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
        title: "دراسة الآية",
        desc: "اكتب كلمةً عربيّةً واحدةً، فترى كلَّ آيةٍ ورد فيها جذرها في القرآن كلِّه، مشكولةً، والكلمةُ مميَّزةٌ في موضعها.",
        cta: "ادرس كلمة",
      },
      lexical: {
        title: "تحليل اللسان",
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
      `ما هي الآيات القريبة في المعنى من ${iso(`«${q}»`)} ؟`,
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

  tahlil: {
    heading: "التحليل النحوي",
    caption:
      "اختر آيةً، ثم اضغط كلمةً لترى تحليلها في خمسة أبواب — الحروف، صرفي، نحوي، دلالي، تركيب. وكلُّ دعوى تحمل شارةَ مصدرها والدليلَ الذي تقوم عليه؛ والشارةُ تُخبر من أين جاءت العبارة، لا أنّها صحيحة.",
    loadVerse: "اعرض الآية",
  },

  lexical: {
    heading: "تحليل اللسان",
    /**
     * The page leads with the ATTESTED layers, in the order it now renders them:
     * the verified root, Ibn Fāris' cited aṣl, the occurrences, the morphology.
     * The letter reading is named last and named for what it is — a transmitted
     * مذهب, displayed with its sources.
     *
     * It used to read «اكتب كلمةً عربيّةً لقراءة جذرها حرفًا حرفًا — قراءةٌ تأويليّةٌ
     * لرمزيّة الحروف في اللسان», which led with the letters and let the whole page
     * be read as a tool that derives a root's meaning from them. It does not, and
     * the first sentence a reader sees is where that has to be said.
     */
    caption:
      "اكتب كلمةً عربيّةً فترى جذرَها المُحقَّق، وأصلَه كما نصَّ عليه ابن فارس، ومواضعَه في الآيات، وصرفَه وإعرابَه. ويأتي بعدَ ذلك مذهبُ القائلين بدلالةِ الحروف، منسوبًا إلى أصحابه — عَرضًا لقولهم، لا استنباطًا لمعنى الجذر من حروفه.",
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

    /* ── The cited aṣl, above the letters: the reading is built ON it ── */
    coresHeading: (n: number) =>
      n > 1 ? "أصول الجذر المنصوصة" : "أصل الجذر المنصوص",
    coreGlossLabel: "الأصل",
    corePolarityTitle: "قطبُ الأصل كما نُصَّ عليه",
    /** Provenance under the verbatim quotation. Both parts are backend data, and
     *  the edition is a Latin key in the shipped dataset (`Harun_DarAlFikr`), so
     *  it is isolated: without FSI…PDI the dash and the Latin run reorder around
     *  each other inside the RTL paragraph (design D15). */
    coreSource: (source: string, edition: string) =>
      edition ? `${source} — ${iso(edition)}` : source,

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
    occurrencesLink: "اعرض المواضع كاملةً، مشكولةً، في «دراسة الآية»",
    /** A root QAC records with no occurrence — the state is stated, not blank. */
    noOccurrences: "لم يُسجَّل لهذا الجذر موضعٌ في المدوّنة.",

    /* ── The letters, as phonetics only. Meaning belongs to a reading. ── */
    lettersHeading: "حروف الجذر — المخارج والصفات",
    positionLabel: "الموضع",
    position: POSITIONS,
    positionKind: POSITION_KINDS,
    /** «3 وجوه» — how many senses the letter's bundle holds. */
    senseCount: (n: number) => count(n, NOUNS.wajh),

    /* ── What the letter reading IS, said once and without interaction ──
     *
     * Everything below this banner is a REPORTED مذهب: what Ḥasan ʿAbbās says a
     * letter carries, and Ibn Jinnī's ishtiqāq al-akbar. Each sense already
     * names its source and page; the banner is what says what the whole section
     * is, in the page's own words, for the reader who opens no disclosure.
     *
     * The application does not derive a root's meaning from its letters, and
     * this is the sentence that states it where it could be believed otherwise. */
    madhhabHeading: "ما يلي مذهبٌ منقولٌ في دلالة الحروف",
    madhhabNote:
      "ما يُعرَض بعدُ هو قولُ حسن عبّاس في خصائص الحروف وقولُ ابن جنّي في الاشتقاق الأكبر، منسوبًا إلى أصحابه، كلُّ وجهٍ بمصدره وصفحته. عَرضُ مذهبٍ وحكايتُه، لا تبنٍّ له.",
    madhhabDisavowal:
      "وهذا التطبيقُ لا يستنبط معنى الجذر من حروفه؛ إنّما مستندُه ما تقدَّم: الجذرُ المُحقَّق، والأصلُ المنصوصُ عند ابن فارس، والمواضعُ في الآيات.",

    /* ── One reading per core, never a blend ─────────────────────────── */
    readingOn: (gloss: string) => `قراءةٌ على أصل «${gloss}»`,
    parallelNote:
      "لكلِّ أصلٍ منصوصٍ قراءةٌ مستقلّة، لا تُمزج بغيرها ولا تُضمّ محاورُها إلى محاور سواها.",
    selectedLabel: "الوجه المختار",
    sensePolarityTitle: "قطبُ الوجه",
    axesLabel: "المحاور المشتركة :",
    selectionRule: SELECTION_RULES,
    confidence: CONFIDENCES,
    polarity: POLARITIES,
    /** Source + page of a sense. The page is a Latin/numeric token (p110-113). */
    senseSource: (source: string, page: string) =>
      page ? `${source} — ${iso(page)}` : source,

    /** A letter no sense of which the core admits. The gap is shown, not filled:
     *  the sentence has to ASSERT that no meaning is carried, because saying
     *  nothing would read as an omission rather than as the finding it is. */
    unmatchedBadge: "بلا وجهٍ مختار",
    unmatchedNote:
      "لا يشترك أيُّ وجهٍ من وجوه هذا الحرف مع أصل الجذر في محور، فلا يُحمَّل الحرفُ هنا معنًى.",

    /** The rejected members of the bundle, collapsed but never hidden: dropping
     *  them would leave the reader with a single gloss again, only a different one. */
    discardedSummary: "معانٍ أخرى للحرف لم تُعتمد هنا",
    discardedReason: DISCARD_REASONS,

    /* ── The composed reading ──────────────────────────────────────────
     *
     * «قراءة اللسان» was the heading, and standing alone over a paragraph about
     * a root it read as that root's meaning. The heading now names what the
     * paragraph is a reading OF — the letters, on this one aṣl, on the مذهب the
     * banner above declared — and the note denies the definition outright. */
    synthesisHeading: "قراءةُ الحروف على هذا الأصل",
    synthesisNote: "مُولَّد آليًّا من الوجوه المختارة — لا تعريفَ للجذر",
    /** The same paragraph when the core selected NOTHING — a real and frequent
     *  shape (ظلم's first aṣl selects for none of ظ ل م). Saying it was composed
     *  «من الوجوه المختارة» would assert a provenance the reading does not have;
     *  the prose under it already says no letter was matched. */
    synthesisNoteUnselected: "مُولَّد آليًّا — لم يُعتمد لأيِّ حرفٍ وجه",

    /* ── The unconstrained state: no attested aṣl, so no reading ─────── */
    /** Keyed on `core_status`; the fallback is used when it arrives null. */
    noCoreHeading: CORE_STATUSES,
    noCoreHeadingFallback: "لا أصلَ مُسجَّلًا في هذا المشروع لهذا الجذر",
    /** Used only if the backend `warning` arrives empty — the sentence is the
     *  backend's to write, this is the guarantee that the state is never silent. */
    noCoreFallback:
      "لم يُنَصَّ لهذا الجذر على أصلٍ في المعجم المعتمد، فلا تُركَّب له قراءة.",
    inventoryHeading: "وجوه الحروف — جردٌ غير مقيَّد",
    /** The out-of-position half of the inventory. Shown, never dropped: the
     *  reader is told the sense exists and where its authority puts it. */
    inventoryElsewhereHeading: "وجوهٌ نصَّ أصحابُها على موضعٍ آخر من اللفظة حصراً",
    inventoryNote:
      "وجوهٌ مسنَدةٌ لكلِّ حرف، معروضةٌ كما هي؛ لم يُختَر منها شيء، ولم تُركَّب منها قراءة.",

    /* ── The guard: it reports, it never corrects ────────────────────── */
    divergenceHeading: "القراءةُ تخالف قطبَ الأصل",
    divergencePoles: (core: string, reading: string) =>
      `قطب الأصل: ${core} · قطب القراءة: ${reading}`,
    divergenceLettersLabel: "الحروف المعنيّة :",
    divergenceNote: "كشفٌ لا تصحيح: لم يتغيّر شيءٌ من الاختيار.",

    /* ── Ibn Jinnī ───────────────────────────────────────────────────── */
    ishtiqaqHeading: "ابن جنّي — الاشتقاق الأكبر",
    ishtiqaqNote: "(تقاليب · تأويلي)",
    ishtiqaqFooter: "الصيغ المُظلَّلة جذورٌ مُثبَتة في المصحف.",

    /** The disclaimer's hover tooltip. */
    sourcesTooltip: "المصادر",
  },

  /**
   * The مفهوم panel on the same «تحليل اللسان» page — a SECOND engine, grouped
   * apart from `lexical` because it argues the other way round: it composes the
   * concept from the letters' physics alone and only then sets Ibn Fāris beside
   * it. Its wording must be reviewable as one block, since the whole risk of the
   * panel is a sentence that quietly promotes a construction into a transmitted
   * reading, or that lets one engine read as the other's correction.
   */
  concept: {
    /* ── The closure, at the top of the panel and before anything it frames ──
     *
     * The experiment is over and its result is negative. The header states the
     * number, not a mood: `0 / 40` witness roots have a concept covering ALL of
     * their frozen uses. It also states WHY the failure is not parametric —
     * 162 of the 176 misses are `imported`, i.e. the notion the gloss needs is
     * absent from the feature vocabulary altogether — so that no reader takes
     * «it needs tuning» away from a panel that is not being tuned.
     *
     * The figures are literals here on purpose: they belong to a measurement
     * that is closed and frozen, not to a payload that could change under them.
     */
    closureHeading: "تجربةٌ مغلقة — لا يجري إصلاحُها",
    closureMetricLabel: "من الجذور الأربعين الشاهدة، ما غطَّى مفهومُه كلَّ شواهده المجمَّدة :",
    /** Isolated: a Latin/numeric run inside an Arabic paragraph reorders around
     *  its own separators without FSI…PDI (design D15). */
    closureMetric: iso("0 / 40"),
    closureBody: `أُغلقت هذه التجربةُ على نتيجتها. ومن ${iso(176)} إخفاقًا، ${iso(162)} من صنف «المستورَد»: الدلالةُ التي تطلبها الشاهدةُ غائبةٌ أصلًا عن معجمِ الصفات — فالخللُ ليس في ضبطِ وسيطٍ ولا في دقّةِ التفصيل، ولا يُرجى من توسيعِ نافذةٍ ولا من إعادةِ ترتيبٍ شيء.`,
    closureNotAlternative:
      "وليست هذه اللوحةُ قراءةً بديلةً يُخيَّر القارئُ بينها وبين ما فوقها، ولم يُحكَم لمحرِّكٍ على الآخر بصوابٍ ولا خطأ. تبقى منشورةً لأنّ النتيجةَ السالبةَ خبرٌ يُنشَر، وسلسلتُها مسجَّلةٌ كما وقعت.",

    heading: "المفهوم — من فيزياءِ الحروف",
    caption:
      "مفهومٌ مُركَّبٌ من وصفِ حروفِ الجذرِ في التجويدِ وحدَه — مخارجِها وصفاتِها — لا من معنًى منقولٍ ولا من أصلٍ في المعاجم.",

    /**
     * The distinction the whole approach rests on, in the page's OWN words: it
     * is not a field of the response and must never become one. Rendered without
     * any interaction, because a reader who never opens a disclosure is exactly
     * the reader who would take the مفهوم for a dictionary meaning.
     */
    conceptVsMeaning:
      "المفهومُ ثابتٌ لا يتبدَّلُ بالسياق: هو ما تُمليه فيزياءُ حروفِ الجذرِ وترتيبُها فيه. وأمَّا المعنى فبالسياقِ يتعيَّن؛ فاللفظةُ الواحدةُ يختلفُ معناها من آيةٍ إلى آية، والمفهومُ تحتَها واحدٌ لا يختلف. وهذه اللوحةُ تعرضُ المفهومَ وحدَه، ولا تعرضُ المعنى.",

    /* ── 9.2: the three positional groups ────────────────────────────── */
    positionsHeading: "المواضعُ الثلاثة",
    positionsNote:
      "قاعدةٌ واحدةٌ تجري على كلِّ جذرٍ ثلاثيّ: الحرفُ الأوَّلُ يفتَحُ الحدثَ، والثاني جسَدُه، والثالثُ يختِمُه. وُضِعَت قبلَ أن يُركَّبَ جذرٌ واحد، ولا تُبدَّلُ لجذرٍ ولا لنتيجة.",
    role: CONCEPT_ROLES,
    ordinal: CONCEPT_ORDINALS,
    roleSentence: CONCEPT_ROLE_SENTENCES,
    makhrajLabel: "المخرج",
    featuresLabel: "الصفات",
    /** A hamza seat is read from the `ء` row; the root's own spelling is never
     *  rewritten, so the page says which row it read rather than showing a letter
     *  the reader did not type. */
    sheetLetter: (letter: string) => `قُرئ من صفِّ الحرف «${letter}»`,
    realisedLabel: "الأصولُ البالغةُ العبارة",
    carriedLabel: "أصولٌ يحملُها الحرفُ ولم تبلغِ العبارة",
    carriedNote:
      "الحدُّ ثلاثةٌ في كلِّ موضع، وهو حدُّ عرضٍ لا نفيَ لما وراءه؛ ولذلك تُنشَرُ ولا تُطوى.",
    orderedLabel: "الترتيبُ بالنُّدرة",
    orderedNote:
      "الأندرُ أوَّلًا، ويفصلُ بين المتساويَين ترتيبُ الجدولِ نفسُه — فيستطيعُ القارئُ أن يعيدَ الترتيبَ بيدِه.",
    /** The ordering signal itself: how many of the 28 letters carry the
     *  primitive. Printed on every hit so the cut is checkable, not asserted. */
    coverage: (n: number) => `${n} من 28 حرفًا`,
    coverageTitle: "عددُ الحروفِ التي تحملُ هذا الأصل",

    /* ── 9.3: the sourcing regime ────────────────────────────────────── */
    status: PRIMITIVE_STATUSES,
    statusTitle: PRIMITIVE_STATUS_TITLES,
    statusLegendHeading: "ما معنى «منصوص» و«فرضُ المشروع»",
    statusLegend:
      "«منصوص» يعني أنَّ مصدرًا مُسمًّى بصفحاتِه نصَّ على نسبةِ هذا الأصلِ إلى هذه الصفة. و«فرضُ المشروع» يعني أنَّ هذا المشروعَ هو الذي ادَّعى النسبة، مبناها واقعةٌ تجويديةٌ لا خلافَ فيها، لا قولُ عالِم. وأكثرُ ما في الجدولِ فروضٌ، فلا تُقرأ قراءةَ المنقول.",

    /* ── The recorded chain: the ground truth beside its reading aid ─── */
    sentenceHeading: "العبارةُ المُسجَّلة",
    sentenceNote:
      "هذه هي العبارةُ كما ركَّبَها المُركِّبُ حرفًا بحرف، وعليها وحدَها يقعُ التسجيلُ والقياسُ والعَرضُ على الأصل. والتقسيمُ إلى ثلاثةِ مواضعَ أعلاه تيسيرٌ للقراءةِ لا بديلٌ عنها: لم يُحذَف أصلٌ، ولا قُدِّمَ ولا أُخِّر، ولا أُعيدَت صياغتُه.",
    sentenceSource: SENTENCE_SOURCES,
    lockVersion: (version: string) => `جدولُ الأصول، النسخة ${iso(version)}`,
    /** Set only when a generated phrasing was produced AND vetoed. «the model
     *  invented something» and «the model was not running» must not look alike. */
    phrasingRejectionHeading: "صياغةٌ مولَّدةٌ رُدَّت",

    /* ── The two failures, kept apart ────────────────────────────────── */
    partialHeading: "مفهومٌ ناقص",
    partialLetters: (letters: string) => `الحرفُ الساكت: ${letters}`,
    silentBadge: "موضعٌ ساكت",
    /** The rule does not reach this root at all — a different fact from a silent
     *  letter, and it gets its own heading rather than the partial banner. */
    refusedHeading: "لا مفهومَ لهذا الجذر",

    /* ── 9.5: the two engines, side by side and undecided ────────────── */
    comparisonHeading: "المحرِّكانِ جنبًا إلى جنب",
    comparisonNote:
      "محرِّكانِ مستقلّان: هذا يبني المفهومَ من الحروفِ وحدَها ثمَّ يُعرَضُ عليه الأصلُ المنصوص، وذاك يقرأُ الحروفَ على الأصلِ ابتداءً. ولم يُحكَم لأحدِهما على الآخر — لا أصوبَ، ولا أولى، ولا بديلًا عند عجزِ صاحبِه — والمقارنةُ بينهما لم تُقضَ بعد.",
    physicsSide: "المفهوم — من الحروف",
    coreSide: "القراءة — على الأصلِ المنصوص",
    noCoreReading: "لم يُركِّب المحرِّكُ الآخرُ قراءةً لهذا الجذر.",
    /** The counterpart never answered — its request failed or has not returned.
     *  A DIFFERENT fact from «it composed no reading», and stating the second in
     *  its place would publish a missing response as a finding about the root. */
    noCoreAnswer: "لم يصل جوابُ المحرِّكِ الآخرِ عن هذه الكلمة.",
    refusedSide: "لا عبارةَ هنا: القاعدةُ لا تتناولُ هذا الجذر.",

    aslHeading: "الأصلُ المنصوصُ عند ابن فارس",
    aslNote:
      "يأتي الأصلُ بعدَ المفهومِ لا قبلَه، عَرضًا عليه؛ فقد يوافقُه وقد يخالفُه، ولا يُعادُ التركيبُ من أجلِه.",
    /** Which silence it is. The differentiating half is `S.lexical.noCoreHeading`,
     *  keyed on `core_status` — one sentence for all three is what told the reader
     *  that Maqāyīs holds no aṣl for حرب, where Ibn Fāris gives three. */
    noCoreLead: "لا أصلَ يُعرَضُ عليه المفهوم — ",

    occurrences: (n: number) => `مواضعُ الجذرِ في القرآن: ${n}`,
    usesHeading: "الوجوهُ المُثبَتةُ للجذرِ في القرآن",
    usesNote:
      "وجوهٌ كُتِبَت وجُمِّدَت قبلَ أن يُولَّدَ مفهومُ هذا الجذر، حتَّى يكونَ العَرضُ عليها عَرضًا لا مصادرة.",
    useVerdict: USE_VERDICTS,
    useReasonLabel: "التعليل :",

    verdictHeading: "حكمُ الشمول",
    verdict: CONFRONTATION_VERDICTS,
    /* The §D11 reservation travels WITH the verdict, on the same panel — a
       coverage verdict printed without it is precisely what is forbidden. It has
       no entry here on purpose: the backend sends the sentence, opening words
       included, and a label of ours in front of it would repeat them. */
    /** A published exclusion, never a silence: a root outside the holdout is
     *  confronted and shown like any other, and says that it counts for nothing. */
    excludedFromK: "خارجَ عيِّنةِ القياس: لا يدخلُ هذا الجذرُ في حسابِ النسبة.",
    inWitnessSet: "من عيِّنةِ القياسِ المسحوبةِ سلفًا.",
    frozenAt: (date: string) => `جُمِّدَت الوجوهُ في ${iso(date)}`,
    recordedAt: (date: string) => `سُجِّلَ المفهومُ في ${iso(date)}`,
  },

  /** Shared verse chrome. */
  verse: {
    loadingSurah: "جارٍ تحميل السورة…",
    loadingVerse: "جارٍ تحميل الآية…",
    ayahNumber: "رقم الآية",
    surah: "السورة",
    surahNumber: (n: number) => `السورة ${n}`,
    ayahLabel: (n: number) => `الآية ${n}`,
    ayahCount: (n: number) => count(n, NOUNS.aya),
    juz: (n: number) => `الجزء ${n}`,
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

  /** The «سور القرآن» reading page: the picker above the surah, and its failures. */
  reading: {
    pickerLabel: "اختر السورة",
    /** Option text: «2 · البقرة» — Western digits, like every other numeral
     *  in the interface. */
    option: (n: number, name: string) => `${n} · ${name}`,
    loadingSurahs: "جارٍ تحميل السور…",
    /** The picker failed while the surah itself may still be readable, so the
     *  note invites a retry rather than reporting the page as broken. */
    surahsFailed: "تعذّر تحميل قائمة السور؛ أعد المحاولة.",
    resuming: "جارٍ فتح آخر ما قرأت…",
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
    return S.errors.verseNotFound;
  }
  if (status === 503) return S.errors.unavailable;
  if (kind === "surahList") return S.errors.surahListFailed;
  if (kind === "analysis") return S.errors.analysisFailed;
  if (kind === "search") return S.errors.searchFailed;
  // A chat turn needs no sentence of its own: a failure there is either an
  // outage or the network, both already covered above.
  if (kind === "chat") return S.errors.generic;
  return S.errors.generic;
}
