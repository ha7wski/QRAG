// Types for the Fāṣila (rhyme-letter) analysis — mirrors api/models/fassila.py.

/** One āya: its fāṣila and the final word it was read from. */
export interface FassilaAyah {
  ayah: number;
  /** null for muqaṭṭaʿāt āyāt, which carry no fāṣila. */
  fasila: string | null;
  /** Final word in Uthmānī rasm (vocalized). */
  word: string;
  /** "surah:ayah:word" — aligned with the QAC token spine. */
  word_ref: string;
  is_muqattaat: boolean;
}

/** One distinct fāṣila and its share of the analysed āyāt. */
export interface FassilaCount {
  letter: string;
  count: number;
  /** Over analysed āyāt (muqaṭṭaʿāt excluded from the denominator). */
  percentage: number;
}

export interface FassilaDominant {
  letter: string;
  count: number;
  percentage: number;
}

export interface FassilaResponse {
  surah: number;
  surah_name: string;
  total_ayahs: number;
  analysed_ayahs: number;
  excluded_ayahs: number;
  distinct_count: number;
  dominant: FassilaDominant | null;
  /** Descending frequency — drives the bar chart and the methodology table. */
  counts: FassilaCount[];
  /** Order of first occurrence — drives the line chart's Y axis, bottom to top. */
  first_appearance: string[];
  ayahs: FassilaAyah[];
}

/** One sūra as the cross-sūra comparison reads it — no per-āya detail. */
export interface FassilaSurahSummary {
  surah: number;
  surah_name: string;
  total_ayahs: number;
  analysed_ayahs: number;
  excluded_ayahs: number;
  distinct_count: number;
  /**
   * The sūra's distinct fāṣila letters, same order as `FassilaResponse.counts`
   * (descending count, ties on first appearance). Not reconstructible from
   * `distinct_count` or `dominant` — the status line needs the union of these
   * across a whole selection of sūras.
   */
  fawasil: string[];
  dominant: FassilaDominant | null;
}

/**
 * How many sūras carry a given number of distinct fawāṣil. Buckets arrive
 * contiguous from the observed minimum to the observed maximum — a value no sūra
 * attains still ships with `surah_count: 0`, so the client never has to
 * reconstruct a missing step.
 */
export interface FassilaBucket {
  distinct: number;
  surah_count: number;
  /** Of the 114 sūras, one decimal — computed server-side with the other figures. */
  percentage: number;
}

/** The whole muṣḥaf at once: 114 summaries plus the corpus aggregates. */
export interface FassilaOverviewResponse {
  surah_count: number;
  /** One decimal, same convention as the percentages. */
  mean_distinct: number;
  mono_fasila_count: number;
  max_distinct: number;
  /** Sūra number(s) attaining `max_distinct`. */
  max_distinct_surahs: number[];
  buckets: FassilaBucket[];
  surahs: FassilaSurahSummary[];
}
