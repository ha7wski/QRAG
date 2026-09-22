import { ChevronDown, Info, Quote, Scale, TriangleAlert } from "lucide-react";
import SarfiRows from "@/components/SarfiRows";
import type {
  Confidence,
  CoreStatus,
  Divergence,
  LetterInventory,
  LetterReading,
  LisanResponse,
  Polarity,
  Reading,
  RootCore,
} from "@/lib/lisanTypes";
import type { QlisanFormResponse } from "@/lib/types";
import { S } from "@/lib/strings";

/**
 * Renders a Lisan Analysis result.
 *
 * The page publishes the CONSTRAINT, not just the conclusion. A letter holds a
 * bundle of sourced senses, and which member applies depends on the root's
 * attested aṣl — so the order on screen is the order of the argument:
 *
 *   root → the cited core(s) → the letters' phonetics → one reading per core
 *
 * The core comes FIRST because it is what the reading is built on; each reading
 * names the aṣl it belongs to, and a root with two aṣl gets two parallel readings
 * that are never merged into one paragraph. Under every letter, the senses the
 * core did not admit stay reachable with the reason they were dropped: hiding them
 * would leave the reader with a single gloss again, only a different one.
 *
 * There is no path here that composes a paragraph out of letter glosses. That is
 * the defect this component replaces — it read خ-ي-ر as «القذارة والخشونة والخواء»
 * against Ibn Fāris' «أصله العطف والميل». When no core is on record, the page says
 * so in an amber banner and lists the senses as an UNSELECTED inventory; it does
 * not compose a reading, and no prop or flag makes it.
 *
 * The feature is Arabic-only; the document is RTL (`<html dir="rtl">`), so the
 * logical properties (`ms-`, `ps-`, `border-s-`) resolve right-to-left.
 */

/** Source confidence of a sense, as a colour. The labels live in `S.lexical.confidence` —
 *  an Arabic literal here is exactly what the string table exists to prevent. */
const CONFIDENCE_STYLES: Record<Confidence, string> = {
  verified: "bg-brand-light text-brand-dark",
  high: "bg-blue-50 text-blue-700",
  summary: "bg-amber-50 text-amber-700",
};

const UNKNOWN_STYLE = "bg-gray-100 text-gray-500";

/** The charge of an aṣl or of a sense. `neutral` is deliberately colourless: it is
 *  a verdict about the citation, not a middle score. */
const POLE_STYLES: Record<Polarity, string> = {
  positive: "bg-emerald-50 text-emerald-700",
  negative: "bg-rose-50 text-rose-700",
  neutral: "bg-gray-100 text-gray-600",
};

export default function LisanResult({
  data,
  sarfi = null,
}: {
  data: LisanResponse;
  /** Position-free morphology (POST /qlisan/form). Optional and independently
   *  fetched: the letter reading must not depend on it. */
  sarfi?: QlisanFormResponse | null;
}) {
  // No root resolved → helpful message, still carrying the disclaimer. The
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
        <Disclaimer text={data.disclaimer} sources={data.sources} />
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

      {/* 2 — What the reading stands on: the cited aṣl, or the amber banner
             saying there is none. Above the letters, because the letters are
             read THROUGH it. */}
      {data.constrained ? (
        <CoresCitation cores={data.cores} axisLabels={data.axis_labels} />
      ) : (
        <UnconstrainedBanner warning={data.warning} status={data.core_status} />
      )}

      {/* 3 — The letters' phonetic identity. Stable across cores, so it is
             published once and carries no meaning. */}
      <LetterPhonetics letters={data.letters} />

      {/* 4 — الصرف والإعراب: deterministic morphology (collapsible) — the established
             facts about the word come before the interpretive reading of its letters. */}
      <GrammarSection sarfi={sarfi} />

      {/* 5 — The readings, one per core; or the unselected inventory. Never both,
             and never a synthesis on the inventory path. */}
      {data.constrained ? (
        <Readings readings={data.readings} axisLabels={data.axis_labels} />
      ) : (
        <Inventory inventory={data.inventory} />
      )}

      {/* 6 — Ibn Jinni: ishtiqaq al-akbar (collapsible, interpretive) */}
      {data.ishtiqaq_akbar.length > 0 && (
        <details className="group rounded-lg border border-gray-200 bg-white p-4">
          <summary className="flex cursor-pointer items-center gap-2 font-arabic font-semibold text-gray-800">
            <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
            {S.lexical.ishtiqaqHeading}
            <span className="font-arabic text-xs font-normal text-gray-400">
              {S.lexical.ishtiqaqNote}
            </span>
          </summary>
          <div className="mt-3 flex flex-wrap gap-2">
            {data.ishtiqaq_akbar.map((p) => (
              <span
                key={p.form}
                title={p.gloss || undefined}
                className={`rounded px-2 py-1 font-arabic text-lg ${
                  p.gloss
                    ? "bg-brand-light text-brand-dark"
                    : "bg-gray-50 text-gray-500"
                }`}
              >
                {p.form}
              </span>
            ))}
          </div>
          <p className="mt-2 font-arabic text-xs text-gray-400">
            {S.lexical.ishtiqaqFooter}
          </p>
        </details>
      )}

      <Disclaimer text={data.disclaimer} sources={data.sources} />
    </div>
  );
}

/* ── The cited core(s) ──────────────────────────────────────────────────── */

/**
 * The aṣl as Ibn Fāris states it, rendered as a CITATION: `verbatim` is his own
 * words and is set apart from the curated `gloss` beside it, so a reader can see
 * at a glance which half is quoted and which half is ours.
 */
function CoresCitation({
  cores,
  axisLabels,
}: {
  cores: RootCore[];
  axisLabels: Record<string, string>;
}) {
  if (cores.length === 0) return null;

  return (
    <section>
      <h2 className="mb-2 font-arabic font-semibold text-gray-800">
        {S.lexical.coresHeading(cores.length)}
      </h2>
      <div className="space-y-3">
        {cores.map((core, i) => (
          <div
            key={`${core.gloss}-${i}`}
            className="rounded-lg border border-brand/30 bg-brand-light p-4"
          >
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-arabic text-sm text-gray-500">
                {S.lexical.coreGlossLabel}
              </span>
              <span className="font-arabic text-2xl text-brand-dark">
                {core.gloss}
              </span>
              <PoleBadge
                pole={core.polarity}
                title={S.lexical.corePolarityTitle}
              />
            </div>

            {/* His words, not ours: quoted, on its own ground, with the source
                under it. The quotation mark is an icon rather than a character —
                a mirrored punctuation glyph resolves its direction from the
                surrounding run, an SVG never does (design D14). */}
            <blockquote className="mt-2 flex gap-2 border-s-4 border-brand/40 bg-white/70 p-3">
              <Quote aria-hidden className="h-4 w-4 shrink-0 text-brand/60" />
              <p className="font-arabic text-lg leading-relaxed text-gray-800">
                {core.verbatim}
              </p>
            </blockquote>

            <p className="mt-2 font-arabic text-xs text-gray-500" dir="auto">
              {S.lexical.coreSource(core.source, core.edition)}
            </p>

            <AxisChips axes={core.axes} labels={axisLabels} tone="core" />
          </div>
        ))}
      </div>
    </section>
  );
}

/* ── The letters, as phonetics only ─────────────────────────────────────── */

function LetterPhonetics({ letters }: { letters: LisanResponse["letters"] }) {
  if (letters.length === 0) return null;

  return (
    <section>
      <h2 className="mb-2 font-arabic font-semibold text-gray-800">
        {S.lexical.lettersHeading}
      </h2>
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

            {l.sifat.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {l.sifat.map((s) => (
                  <span
                    key={s}
                    className="rounded bg-gray-100 px-1.5 py-0.5 font-arabic text-[11px] text-gray-600"
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}

            {/* How many senses the bundle holds — the count is the honest replacement
                for the single gloss that used to sit here. */}
            <div className="mt-2 font-arabic text-xs text-gray-400">
              {S.lexical.senseCount(l.sense_count)}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ── The readings ───────────────────────────────────────────────────────── */

/**
 * One block per core, side by side and never merged. Each announces its own aṣl in
 * its heading; when there is more than one, each also repeats the verbatim it was
 * built from, so two hypotheses about the same root can never be read as one.
 */
function Readings({
  readings,
  axisLabels,
}: {
  readings: Reading[];
  axisLabels: Record<string, string>;
}) {
  if (readings.length === 0) return null;
  const parallel = readings.length > 1;

  return (
    <div className="space-y-5">
      {parallel && (
        <p className="font-arabic text-sm text-gray-500">
          {S.lexical.parallelNote}
        </p>
      )}

      {readings.map((reading, i) => {
        // Whether the core selected ANYTHING. A reading can be entirely
        // unmatched — ظلم's first aṣl selects for none of ظ ل م — and the note
        // over the paragraph must not then claim it was composed «من الوجوه
        // المختارة». The prose itself already says no letter was matched.
        const anySelected = reading.letters.some(
          (l) => l.selection_rule !== "unmatched" && l.selected,
        );
        return (
          <article
            key={`${reading.core.gloss}-${i}`}
            className="rounded-lg border-2 border-brand/20 bg-white p-4"
          >
            <header>
              <h2 className="font-arabic text-lg font-semibold text-brand-dark">
                {S.lexical.readingOn(reading.core.gloss)}
              </h2>
              {parallel && (
                <p className="mt-1 border-s-2 border-brand/30 ps-2 font-arabic text-sm text-gray-600">
                  {reading.core.verbatim}
                </p>
              )}
            </header>

            {reading.divergence && (
              <DivergenceBanner divergence={reading.divergence} />
            )}

            <ol className="mt-4 space-y-3">
              {reading.letters.map((letter) => (
                <LetterReadingRow
                  key={letter.index}
                  reading={letter}
                  axisLabels={axisLabels}
                />
              ))}
            </ol>

            {reading.synthesis && (
              <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="mb-2 flex flex-wrap items-baseline gap-2">
                  <h3 className="font-arabic font-semibold text-gray-800">
                    {S.lexical.synthesisHeading}
                  </h3>
                  <span className="font-arabic text-xs text-gray-400">
                    {anySelected
                      ? S.lexical.synthesisNote
                      : S.lexical.synthesisNoteUnselected}
                  </span>
                </div>
                <p className="whitespace-pre-wrap font-arabic text-lg leading-relaxed text-gray-800">
                  {reading.synthesis}
                </p>
              </div>
            )}
          </article>
        );
      })}
    </div>
  );
}

/**
 * What ONE core made of ONE letter: the selected sense with the axes it shares with
 * the aṣl and the citation that admits it — or, when nothing was eligible, a stated
 * gap. The gap is never filled with the letter's first or most-confident sense:
 * that substitution is the behaviour being removed.
 */
function LetterReadingRow({
  reading,
  axisLabels,
}: {
  reading: LetterReading;
  axisLabels: Record<string, string>;
}) {
  // Two independent signals of the same fact, and EITHER is the gap: a payload
  // that carries `unmatched` beside a non-null `selected` must not assert a
  // meaning — the rule is the verdict, the sense is only what it points at.
  // Narrowing here is also what lets `S.lexical.selectionRule` be keyed on the
  // two rules that can actually be rendered.
  const matched =
    reading.selection_rule !== "unmatched" && reading.selected
      ? { rule: reading.selection_rule, sense: reading.selected }
      : null;

  return (
    <li className="rounded-lg border border-gray-200 p-3">
      <div className="flex items-start gap-3">
        <span className="font-arabic text-3xl leading-none text-brand">
          {reading.letter}
        </span>

        <div className="min-w-0 flex-1">
          {matched ? (
            <>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-arabic text-xs text-gray-500">
                  {S.lexical.selectedLabel}
                </span>
                <span className="font-arabic text-lg text-gray-800">
                  {matched.sense.gloss_ar}
                </span>
                <PoleBadge
                  pole={matched.sense.pole}
                  title={S.lexical.sensePolarityTitle}
                />
                <span
                  className={`rounded px-1.5 py-0.5 font-arabic text-[11px] font-medium ${
                    CONFIDENCE_STYLES[matched.sense.confidence] || UNKNOWN_STYLE
                  }`}
                >
                  {S.lexical.confidence[matched.sense.confidence] ||
                    matched.sense.confidence}
                </span>
              </div>

              {reading.matched_axes.length > 0 && (
                <div className="mt-1.5 flex flex-wrap items-center gap-1">
                  <span className="font-arabic text-xs text-gray-500">
                    {S.lexical.axesLabel}
                  </span>
                  <AxisChips
                    axes={reading.matched_axes}
                    labels={axisLabels}
                    tone="match"
                  />
                </div>
              )}

              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 font-arabic text-xs text-gray-500">
                <span>
                  {S.lexical.selectionRule[matched.rule] || matched.rule}
                </span>
                <span dir="auto">
                  {S.lexical.senseSource(
                    matched.sense.source,
                    matched.sense.page,
                  )}
                </span>
              </div>
            </>
          ) : (
            <div className="rounded bg-gray-50 p-2">
              <span className="rounded bg-gray-200 px-1.5 py-0.5 font-arabic text-[11px] text-gray-700">
                {S.lexical.unmatchedBadge}
              </span>
              <p className="mt-1.5 font-arabic text-sm leading-relaxed text-gray-600">
                {S.lexical.unmatchedNote}
              </p>
            </div>
          )}
        </div>
      </div>

      {reading.discarded.length > 0 && (
        <details className="mt-2 rounded bg-gray-50 p-2">
          <summary className="cursor-pointer font-arabic text-xs text-gray-600">
            {S.lexical.discardedSummary}
          </summary>
          <ul className="mt-2 space-y-1.5">
            {reading.discarded.map((d) => (
              <li
                key={d.sense.sense_id}
                className="flex flex-wrap items-baseline gap-2"
              >
                <span className="font-arabic text-sm text-gray-700">
                  {d.sense.gloss_ar}
                </span>
                <span className="rounded bg-white px-1.5 py-0.5 font-arabic text-[11px] text-gray-500">
                  {S.lexical.discardedReason[d.reason] || d.reason}
                </span>
                <span
                  dir="auto"
                  className="font-arabic text-[11px] text-gray-400"
                >
                  {S.lexical.senseSource(d.sense.source, d.sense.page)}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </li>
  );
}

/* ── The two banner states ──────────────────────────────────────────────── */

/**
 * No attested aṣl on record: amber, and it says so. A large minority of QAC roots
 * land here — it is a normal outcome, not an edge case — and the honest empty
 * hand is preferred over the reading that produced the خ-ي-ر bug.
 */
function UnconstrainedBanner({
  warning,
  status,
}: {
  warning: string | null;
  status: CoreStatus | null;
}) {
  // The heading names WHOSE silence this is. Defaulting a null status to the
  // project's own gap is the safe direction: an unknown reason must never be
  // published as «Ibn Fāris states no aṣl».
  const heading =
    (status && S.lexical.noCoreHeading[status]) || S.lexical.noCoreHeadingFallback;
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
      <h2 className="flex items-center gap-2 font-arabic font-semibold text-amber-900">
        <TriangleAlert aria-hidden className="h-4 w-4 shrink-0" />
        {heading}
      </h2>
      <p className="mt-1 font-arabic leading-relaxed text-amber-800">
        {warning || S.lexical.noCoreFallback}
      </p>
    </div>
  );
}

/**
 * The guard fired: the reading's aggregate pole contradicts its own core's. Indigo
 * and a balance, deliberately NOT the amber of the missing-core banner and not the
 * red of a failure — it reports a finding about the data, and it corrected nothing.
 */
function DivergenceBanner({ divergence }: { divergence: Divergence }) {
  return (
    <div className="mt-3 rounded-lg border border-indigo-300 bg-indigo-50 p-3">
      <h3 className="flex items-center gap-2 font-arabic font-semibold text-indigo-900">
        <Scale aria-hidden className="h-4 w-4 shrink-0" />
        {S.lexical.divergenceHeading}
      </h3>
      <p className="mt-1 font-arabic text-sm text-indigo-900">
        {S.lexical.divergencePoles(
          S.lexical.polarity[divergence.core_polarity],
          S.lexical.polarity[divergence.reading_polarity],
        )}
      </p>
      {divergence.letters.length > 0 && (
        <div className="mt-1 flex flex-wrap items-center gap-1">
          <span className="font-arabic text-sm text-indigo-700">
            {S.lexical.divergenceLettersLabel}
          </span>
          {divergence.letters.map((letter, i) => (
            <span
              key={`${letter}-${i}`}
              className="rounded bg-white px-1.5 py-0.5 font-arabic text-sm text-indigo-900"
            >
              {letter}
            </span>
          ))}
        </div>
      )}
      {divergence.message && (
        <p className="mt-1 font-arabic text-sm leading-relaxed text-indigo-800">
          {divergence.message}
        </p>
      )}
      <p className="mt-1 font-arabic text-xs text-indigo-600">
        {S.lexical.divergenceNote}
      </p>
    </div>
  );
}

/* ── The unconstrained inventory ────────────────────────────────────────── */

/**
 * Every sense of every letter, plainly listed and explicitly UNSELECTED. Listing
 * sourced senses is informative; composing them into an assertive paragraph is
 * what this whole change removes, so there is no synthesis on this path.
 */
function Inventory({ inventory }: { inventory: LetterInventory[] }) {
  if (inventory.length === 0) return null;

  return (
    <section>
      <h2 className="font-arabic font-semibold text-gray-800">
        {S.lexical.inventoryHeading}
      </h2>
      <p className="mb-2 font-arabic text-sm text-gray-500">
        {S.lexical.inventoryNote}
      </p>
      <ol className="space-y-3">
        {inventory.map((entry) => (
          <li
            key={entry.index}
            className="rounded-lg border border-gray-200 bg-white p-3"
          >
            <div className="flex items-start gap-3">
              <span className="font-arabic text-3xl leading-none text-brand">
                {entry.letter}
              </span>
              <ul className="min-w-0 flex-1 space-y-1.5">
                {entry.senses.map((sense) => (
                  <li
                    key={sense.sense_id}
                    className="flex flex-wrap items-baseline gap-2"
                  >
                    <span className="font-arabic text-base text-gray-700">
                      {sense.gloss_ar}
                    </span>
                    <PoleBadge
                      pole={sense.pole}
                      title={S.lexical.sensePolarityTitle}
                    />
                    <span
                      dir="auto"
                      className="font-arabic text-[11px] text-gray-400"
                    >
                      {S.lexical.senseSource(sense.source, sense.page)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ── Small shared pieces ────────────────────────────────────────────────── */

/** Axis ids rendered as their Arabic labels. The map comes from the payload — the
 *  frontend holds no copy of the vocabulary — and an unknown id falls back to the
 *  id itself, so a curation gap shows up rather than disappearing. */
function AxisChips({
  axes,
  labels,
  tone,
}: {
  axes: string[];
  labels: Record<string, string>;
  tone: "core" | "match";
}) {
  if (axes.length === 0) return null;
  const style =
    tone === "core"
      ? "bg-white/80 text-brand-dark"
      : "bg-brand-light text-brand-dark";

  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {axes.map((axis) => (
        <span
          key={axis}
          // `dir="auto"`: the fallback below renders the raw axis id, which is
          // Latin — an unlabelled id must show up as a wrong-looking chip, not
          // reorder the row it sits in.
          dir="auto"
          className={`rounded px-1.5 py-0.5 font-arabic text-[11px] ${style}`}
        >
          {labels[axis] || axis}
        </span>
      ))}
    </div>
  );
}

function PoleBadge({ pole, title }: { pole: Polarity; title: string }) {
  return (
    <span
      title={title}
      className={`rounded px-1.5 py-0.5 font-arabic text-[11px] font-medium ${
        POLE_STYLES[pole] || UNKNOWN_STYLE
      }`}
    >
      {S.lexical.polarity[pole] || pole}
    </span>
  );
}

/** «الصرف والإعراب» — the deterministic morphology of the typed word, collapsed by
 *  default (same `<details>` grammar as the ابن جنّي section below it).
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

/** Persistent low-key disclaimer with a hover "sources" tooltip. */
function Disclaimer({
  text,
  sources,
}: {
  text: string;
  sources: Record<string, string>;
}) {
  const entries = Object.entries(sources || {});
  return (
    <div className="flex items-center gap-1.5 font-arabic text-xs text-gray-400">
      <Info className="h-3.5 w-3.5 shrink-0" />
      <span>{text}</span>
      {entries.length > 0 && (
        <span className="group relative ms-1">
          <button
            type="button"
            className="cursor-help underline decoration-dotted underline-offset-2"
          >
            {S.lexical.sourcesTooltip}
          </button>
          <span className="pointer-events-none absolute bottom-full start-0 z-10 mb-1 hidden w-72 rounded-lg border border-gray-200 bg-white p-3 text-start text-gray-600 shadow-lg group-hover:block">
            {entries.map(([k, v]) => (
              <span key={k} className="mb-1 block last:mb-0" dir="ltr">
                <span className="font-medium capitalize text-gray-700">
                  {k.replace("_", " ")}:
                </span>{" "}
                {v}
              </span>
            ))}
          </span>
        </span>
      )}
    </div>
  );
}
