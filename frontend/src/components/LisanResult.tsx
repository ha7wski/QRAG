import Link from "next/link";
import { ArrowLeft, ChevronDown, ListTree } from "lucide-react";
import IslambouliStages from "@/components/IslambouliStages";
import SarfiRows from "@/components/SarfiRows";
import type { LisanResponse } from "@/lib/lisanTypes";
import type { QlisanFormResponse } from "@/lib/types";
import { S } from "@/lib/strings";

/**
 * Renders a Lisan Analysis result, in this order:
 *
 *   root (QAC) → its letters, with Samer Islambouli's gloss → Islambouli's own
 *   sentence (if published), the project's assembly of his rows and the gap →
 *   the cultural stage (only when cited or signed) → the occurrences → صرف/إعراب
 *
 * Every section is sourced. The letter gloss is Islambouli's PUBLISHED table,
 * quoted verbatim and attributed to him under the section heading: it is his
 * statement about a letter, never selected against the aṣl and never composed
 * into a sentence about the root by him. The one sentence the page composes is
 * the project's mechanical assembly of his rows, labelled as the project's.
 *
 * The letter reading that used to follow the morphology (the reported مذهب of
 * Ḥasan ʿAbbās, the per-core readings or the unselected inventory, Ibn Jinnī's
 * ishtiqāq al-akbar) is no longer rendered, nor is Ibn Fāris' cited aṣl (or
 * the amber banner that stood in for it). The backend still sends those fields;
 * nothing here reads them.
 *
 * The feature is Arabic-only; the document is RTL (`<html dir="rtl">`), so the
 * logical properties (`ms-`, `ps-`, `border-s-`) resolve right-to-left.
 */

/** How many verse references the المواضع section prints before it says how many
 *  it is not printing. A sample, deliberately: the exhaustive vocalized list with
 *  the matched word highlighted is «دراسة الآية»'s job, and this section links
 *  there instead of growing a second copy of it. */
const REF_SAMPLE = 8;

export default function LisanResult({
  data,
  sarfi = null,
  onReadingSaved,
}: {
  data: LisanResponse;
  /** Re-run the analysis once a signed personal reading is stored. */
  onReadingSaved?: () => void;
  /** Position-free morphology (POST /qlisan/form). Optional and independently
   *  fetched: the analysis must not depend on it. */
  sarfi?: QlisanFormResponse | null;
}) {
  // No root resolved → helpful message. The
  // grammar section still renders: a function word (مِن, الذي) is rootless in QAC
  // yet fully analysed morphologically, so there is real content to show here.
  // `constrained` is false on this path too, but there is no root to warn about.
  if (!data.root) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 font-arabic text-amber-800">
          {data.message || S.lexical.noRoot(data.word)}
        </div>
        <GrammarSection sarfi={sarfi} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1 — Root + fallback badge */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="font-arabic text-sm text-gray-500">
            {S.lexical.rootLabel}
          </span>
          <span className="font-arabic text-3xl text-brand-dark">
            {data.root}
          </span>
          {data.root_source === "fallback" && (
            <span
              title={S.lexical.fallbackBadgeTitle}
              className="rounded bg-amber-100 px-2 py-0.5 font-arabic text-xs font-medium text-amber-800"
            >
              {S.lexical.fallbackBadge}
            </span>
          )}
          <span className="ms-auto font-arabic text-2xl text-gray-700">
            {data.word}
          </span>
        </div>
      </div>

      {/* 2 — The root's letters: name, مخرج, position, and Islambouli's gloss,
             quoted and attributed. */}
      <LetterCards letters={data.letters} />

      {/* 3 — Islambouli: his own sentence when he published one, the PROJECT's
             mechanical junction of his three rows, the gap between them, and the
             cultural stage only when it is cited or signed. */}
      <IslambouliStages
        root={data.root}
        assembly={data.islambouli_assembly}
        cultural={data.cultural_stage}
        onSaved={onReadingSaved}
      />

      {/* 4 — المواضع: what the corpus itself attests. Figures, the written forms,
             a sample of references, and the link to the page that displays them
             all, vocalized and highlighted. */}
      <Occurrences
        word={data.word}
        occurrences={data.occurrences}
        words={data.occurrence_words}
        verses={data.occurrence_verses}
        forms={data.forms}
      />

      {/* 5 — الصرف والإعراب: deterministic morphology (collapsible). The last
             section of the page. */}
      <GrammarSection sarfi={sarfi} />
    </div>
  );
}

/* ── المواضع — the attested occurrences ─────────────────────────────────── */

/**
 * What the corpus attests for the root: how many words and how many āyāt hold
 * it, which ألفاظ it is written as, and a SAMPLE of references — then the way
 * out to the page that shows all of them properly.
 *
 * Every figure here is «الكلمة في الآيات»'s own — one backend computation feeds
 * both pages (`VerseLookup.root_forms`). They used to be counted separately, and
 * the separation showed: this section listed رَحْمَةً / رَحْمَةٍ / رَحْمَةُ as three of 43
 * «ألفاظ» where the other page showed 31 distinct written forms.
 *
 * The sample is a sample and says so with a number, so nothing here pretends to
 * be exhaustive. The exhaustive display — every āya, vocalized, with the matched
 * word highlighted at its position — is «دراسة الآية», and the link is how this
 * section stays a summary instead of becoming a worse second copy of that page.
 *
 * These are facts with a source that can be checked against the corpus, which is
 * why they sit above the morphology. They
 * used to reach the screen only through the concept engine's confrontation
 * block: an attested datum displayed only while an experimental route was up.
 */
function Occurrences({
  word,
  occurrences,
  words,
  verses,
  forms,
}: {
  word: string;
  occurrences: number;
  words: number;
  verses: string[];
  forms: string[];
}) {
  const sample = verses.slice(0, REF_SAMPLE);
  const remaining = verses.length - sample.length;
  // A root the resolver produced but the corpus does not attest — a heuristic
  // fallback root, typically. Stated, not left as an empty frame.
  const empty = occurrences === 0 && verses.length === 0 && forms.length === 0;

  return (
    <section
      aria-labelledby="lisan-occurrences"
      className="rounded-lg border border-gray-200 bg-white p-4"
    >
      <h2
        id="lisan-occurrences"
        className="font-arabic font-semibold text-gray-800"
      >
        {S.lexical.occurrencesHeading}
      </h2>
      <p className="mt-1 font-arabic text-xs text-gray-500" dir="auto">
        {S.lexical.occurrencesNote}
      </p>

      {empty ? (
        <p className="mt-3 font-arabic text-gray-600">
          {S.lexical.noOccurrences}
        </p>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap gap-2">
            {/* مواضع before آيات, as «الكلمة في الآيات» orders them: a word count
                and an āya count are different questions (رحم is 339 in 313), and
                the two pages now read them off the same computation. */}
            <span className="rounded bg-brand-light px-2 py-1 font-arabic text-base text-brand-dark">
              {S.lexical.occurrencesWords(words)}
            </span>
            <span className="rounded bg-brand-light px-2 py-1 font-arabic text-base text-brand-dark">
              {S.lexical.occurrencesAyat(occurrences)}
            </span>
            <span className="rounded bg-gray-100 px-2 py-1 font-arabic text-base text-gray-700">
              {S.lexical.occurrencesForms(forms.length)}
            </span>
          </div>

          {forms.length > 0 && (
            <div className="mt-3 flex flex-wrap items-baseline gap-1.5">
              <span className="font-arabic text-xs text-gray-500">
                {S.lexical.formsLabel}
              </span>
              {forms.map((form) => (
                <span
                  key={form}
                  className="rounded bg-gray-50 px-1.5 py-0.5 font-arabic text-lg text-gray-800"
                >
                  {form}
                </span>
              ))}
            </div>
          )}

          {sample.length > 0 && (
            <div className="mt-3 flex flex-wrap items-baseline gap-1.5">
              <span className="font-arabic text-xs text-gray-500">
                {S.lexical.occurrencesSampleLabel}
              </span>
              {sample.map((ref) => (
                // `2:255` is a Latin-digit run: without `dir="auto"` its colon
                // reorders against the Arabic line it sits in (design D15).
                <span
                  key={ref}
                  dir="auto"
                  className="rounded bg-gray-50 px-1.5 py-0.5 font-arabic text-sm text-gray-600"
                >
                  {ref}
                </span>
              ))}
              {remaining > 0 && (
                <span className="font-arabic text-xs text-gray-500">
                  {S.lexical.occurrencesMore(remaining)}
                </span>
              )}
            </div>
          )}

          <Link
            href={`/verse-study?word=${encodeURIComponent(word)}`}
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-brand px-4 py-2 font-arabic text-white transition hover:bg-brand-dark"
          >
            <ListTree aria-hidden className="h-4 w-4" />
            {S.lexical.occurrencesLink}
            <ArrowLeft aria-hidden className="h-4 w-4" />
          </Link>
        </>
      )}
    </section>
  );
}

/* ── The letters, with Islambouli's gloss ──────────────────────────────── */

/**
 * One card per radical: the letter, its name and مخرج, its position in the root,
 * and Samer Islambouli's gloss for it, verbatim. The صفات chips and the «N وجوه»
 * count that used to sit here are gone: the gloss replaces the first, and the
 * second counted senses this page no longer shows.
 */
function LetterCards({ letters }: { letters: LisanResponse["letters"] }) {
  if (letters.length === 0) return null;

  return (
    <section aria-labelledby="lisan-letters">
      <h2
        id="lisan-letters"
        className="font-arabic font-semibold text-gray-800"
      >
        {S.lexical.lettersHeading}
      </h2>
      <p className="mb-2 mt-1 font-arabic text-xs text-gray-500">
        {S.lexical.lettersNote}
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {letters.map((l) => (
          <div
            key={l.index}
            className="rounded-lg border border-gray-200 bg-white p-3"
          >
            <div className="flex items-center gap-3">
              <span className="font-arabic text-4xl leading-none text-brand">
                {l.letter}
              </span>
              <div className="min-w-0">
                <div className="truncate font-arabic text-sm font-medium text-gray-800">
                  {l.name}
                </div>
                <div className="font-arabic text-xs text-gray-500">
                  {l.makhraj}
                </div>
              </div>
              <span
                title={S.lexical.positionLabel}
                className="ms-auto rounded bg-gray-100 px-1.5 py-0.5 font-arabic text-[11px] text-gray-600"
              >
                {S.lexical.position[l.position]}
              </span>
            </div>

            {l.islambouli ? (
              <p className="mt-2 font-arabic text-base leading-relaxed text-gray-800">
                {l.islambouli}
              </p>
            ) : (
              <p className="mt-2 font-arabic text-sm text-gray-400">
                {S.lexical.islambouliMissing}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

/** «الصرف والإعراب» — the deterministic morphology of the typed word, collapsed by
 *  default.
 *
 * The reader typed a bare word, so there is no verse position — and QAC annotates
 * tokens IN CONTEXT, with no form→morphology lexicon. The backend therefore reads
 * the fiche from the word's FIRST occurrence and strips everything that belongs to
 * that occurrence rather than to the form (الحالة الإعرابية, حالة الفعل, العلامة).
 * النظائر stays: root and lemma decide it, so it holds for the form wherever it
 * occurs. Only rows that are true of the form are rendered, so the card carries no
 * provenance line — the response still names the occurrence in `ref` for callers
 * that want it.
 *
 * Renders nothing at all while the request is in flight or if it failed — the
 * letter reading is the page, this only supplements it.
 */
function GrammarSection({ sarfi }: { sarfi: QlisanFormResponse | null }) {
  if (!sarfi) return null;

  return (
    <details className="group rounded-lg border border-gray-200 bg-white p-4">
      <summary className="flex cursor-pointer items-center gap-2 font-arabic font-semibold text-gray-800">
        <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
        {S.lexical.sarfiSection}
        {sarfi.available && (
          <span className="ms-auto rounded-full bg-brand-light px-2 py-0.5 font-arabic text-xs text-brand-dark">
            {S.lexical.verifiedDatum}
          </span>
        )}
      </summary>

      <div className="mt-3">
        {sarfi.available ? (
          <SarfiRows level={sarfi.sarfi} />
        ) : (
          <p className="font-arabic text-base text-gray-500">
            {sarfi.message || S.lexical.noSarfi}
          </p>
        )}
      </div>
    </details>
  );
}
