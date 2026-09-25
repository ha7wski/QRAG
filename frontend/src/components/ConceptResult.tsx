import { Info, Quote, Scale, TriangleAlert } from "lucide-react";
import type {
  AttestedUse,
  Concept,
  ConceptResponse,
  Confrontation,
  LisanResponse,
  PositionReading,
  PrimitiveHit,
  PrimitiveStatus,
  RootCore,
} from "@/lib/lisanTypes";
import { S } from "@/lib/strings";

/**
 * The مفهوم composed from a root's letters — the SECOND engine on «تحليل اللسان».
 *
 * `LisanResult` beside it argues core-first: the attested aṣl selects among each
 * letter's sourced senses. This one argues the other way round — the concept is
 * composed from the tajwīd description of the letters and from nothing else, and
 * Ibn Fāris arrives AFTERWARDS, as the test the concept is put to. Nothing here
 * may call either engine correct, better, or the other's fallback: the comparison
 * between them is not decided, and the page is what that undecidedness looks like.
 *
 * Three things this component owes the reader and cannot get from the payload:
 *
 *   1. the Arabic wording of the positional rule (يَفتَح · جَسَد · يَختِم). The API
 *      sends `opens`/`body`/`concludes` and nothing else, the same division of
 *      labour `LetterIdentity.position` already follows.
 *   2. the مفهوم / معنى distinction, in the page's own words and visible without
 *      any interaction — it is the point of the approach, and a reader who never
 *      opens a disclosure is exactly the one who would read the مفهوم as a gloss.
 *   3. what `attested` and `hypothesis` mean. Most rows are the project's own
 *      hypotheses, and rendering them like transmitted scholarship is the single
 *      way this panel could mislead.
 *
 * The grouping into three positions is a READING AID and never a replacement: the
 * deterministic chain is shown verbatim beside the groups, because it is what the
 * composer returned, what the confrontation judges and what the metric is measured
 * on. No primitive is dropped, reordered or re-worded here — the union of the three
 * groups is exactly `realised_primitives`, in composition order.
 *
 * The disclaimer is NOT repeated here: it is the same string `LisanResult`
 * publishes at the foot of the same page.
 *
 * Arabic-only; the document is RTL, so the logical properties (`ms-`, `ps-`,
 * `border-s-`) resolve right-to-left and the three groups read first-radical-first.
 */

/** The sourcing regime, as a colour. Deliberately far apart: `attested` borrows
 *  the citation tone the cited-aṣl blocks use, `hypothesis` the amber this app
 *  reserves for «ours, and unproven». The labels live in `S.concept.status`. */
const STATUS_STYLES: Record<PrimitiveStatus, string> = {
  attested: "bg-brand-light text-brand-dark ring-1 ring-brand/30",
  hypothesis: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
};

export default function ConceptResult({
  data,
  lisan = null,
}: {
  data: ConceptResponse;
  /** The core-first reading of the SAME word, for the comparison panel. Optional:
   *  the two engines are fetched independently, and a missing counterpart costs
   *  the comparison, never the concept. */
  lisan?: LisanResponse | null;
}) {
  const { concept, confrontation } = data;
  // No root resolved: `LisanResult` already carries the message and the
  // disclaimer for that path, and there is no مفهوم to distinguish from a معنى.
  if (!concept) return null;

  return (
    <div className="space-y-4">
      <header className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap items-baseline gap-3">
          <h2 className="font-arabic text-lg font-semibold text-gray-800">
            {S.concept.heading}
          </h2>
          <span className="font-arabic text-2xl text-brand-dark">
            {concept.root}
          </span>
        </div>
        <p className="mt-1 font-arabic text-sm text-gray-500">
          {S.concept.caption}
        </p>
      </header>

      {/* Page-owned, and above everything it could be confused with. */}
      <ConceptVsMeaning />

      {concept.refused ? (
        <Refusal concept={concept} />
      ) : (
        <>
          {concept.partial && (
            <PartialBanner letters={concept.silent_letters} />
          )}
          <StatusLegend />
          <PositionGroups positions={concept.positions} />
          <RecordedChain concept={concept} />
        </>
      )}

      {confrontation && (
        <Comparison
          concept={concept}
          confrontation={confrontation}
          lisan={lisan}
          reservation={data.metric_reservation}
        />
      )}
    </div>
  );
}

/* ── The distinction the approach rests on ──────────────────────────────── */

/** Fixed مفهوم against contextual معنى, stated by the PAGE. It is not a field of
 *  the response and must not become one: a value the backend could stop sending
 *  is a claim the screen could stop making. */
function ConceptVsMeaning() {
  return (
    <p className="rounded-lg border border-brand/30 bg-brand-light p-4 font-arabic leading-relaxed text-brand-dark">
      {S.concept.conceptVsMeaning}
    </p>
  );
}

/* ── 9.3 — what the two badges mean, before any badge is read ───────────── */

function StatusLegend() {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
      <h3 className="flex items-center gap-2 font-arabic text-sm font-semibold text-gray-700">
        <Info aria-hidden className="h-4 w-4 shrink-0" />
        {S.concept.statusLegendHeading}
      </h3>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <StatusBadge status="attested" />
        <StatusBadge status="hypothesis" />
      </div>
      <p className="mt-2 font-arabic text-sm leading-relaxed text-gray-600">
        {S.concept.statusLegend}
      </p>
    </div>
  );
}

function StatusBadge({ status }: { status: PrimitiveStatus }) {
  return (
    <span
      title={S.concept.statusTitle[status]}
      className={`rounded px-1.5 py-0.5 font-arabic text-[11px] font-medium ${STATUS_STYLES[status]}`}
    >
      {S.concept.status[status]}
    </span>
  );
}

/* ── 9.2 — the مفهوم as three positional groups ─────────────────────────── */

/**
 * Nine مصادر joined by و is grammatical Arabic that enumerates rather than states,
 * so the presentation is what changed — and ONLY the presentation. The window that
 * decides how many primitives reach the sentence stays at three: narrowing it back
 * to make the output read better is how a pre-registered rule becomes a tuned one.
 */
function PositionGroups({ positions }: { positions: PositionReading[] }) {
  if (positions.length === 0) return null;

  return (
    <section aria-labelledby="concept-positions">
      <h3
        id="concept-positions"
        className="font-arabic font-semibold text-gray-800"
      >
        {S.concept.positionsHeading}
      </h3>
      <p className="mb-2 font-arabic text-sm leading-relaxed text-gray-500">
        {S.concept.positionsNote}
      </p>
      <div className="grid gap-3 lg:grid-cols-3">
        {positions.map((reading) => (
          <PositionGroup key={reading.position} reading={reading} />
        ))}
      </div>
    </section>
  );
}

function PositionGroup({ reading }: { reading: PositionReading }) {
  const { position } = reading;

  return (
    <article className="rounded-lg border border-gray-200 bg-white p-3">
      <header className="flex items-center gap-3">
        <span className="font-arabic text-4xl leading-none text-brand">
          {reading.letter}
        </span>
        <div className="min-w-0">
          <div className="font-arabic text-sm text-gray-500">
            {S.concept.ordinal[position]}
          </div>
          <div className="font-arabic text-lg font-semibold text-gray-800">
            {S.concept.role[position]}
          </div>
          <div className="font-arabic text-xs text-gray-500">
            {S.concept.roleSentence[position]}
          </div>
        </div>
      </header>

      {reading.silent ? (
        // The position is OMITTED, never filled. The sentence under it is the
        // backend's and says whose gap it is; there is no default primitive and
        // no flag that restores one.
        <div className="mt-3 rounded bg-amber-50 p-2">
          <span className="rounded bg-amber-100 px-1.5 py-0.5 font-arabic text-[11px] font-medium text-amber-800">
            {S.concept.silentBadge}
          </span>
          <p className="mt-1.5 font-arabic text-sm leading-relaxed text-amber-900">
            {reading.silent_reason}
          </p>
        </div>
      ) : (
        <>
          <dl className="mt-3 space-y-1 font-arabic text-xs text-gray-600">
            {/* Both halves are conditional: a label over an empty value reads as
                a datum the sheet holds and the page lost. */}
            {reading.makhraj_ar && (
              <div className="flex gap-1">
                <dt className="shrink-0 text-gray-400">
                  {S.concept.makhrajLabel}
                </dt>
                <dd>{reading.makhraj_ar}</dd>
              </div>
            )}
            {reading.features.length > 0 && (
              <div className="flex flex-wrap items-baseline gap-1">
                <dt className="shrink-0 text-gray-400">
                  {S.concept.featuresLabel}
                </dt>
                <dd className="flex flex-wrap gap-1">
                  {reading.features.map((feature) => (
                    <span
                      key={feature}
                      // The features are the sheet's own keys, Latin
                      // transliterations: `dir="auto"` keeps one from reordering
                      // the Arabic row it sits in.
                      dir="auto"
                      className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-600"
                    >
                      {feature}
                    </span>
                  ))}
                </dd>
              </div>
            )}
          </dl>

          {/* A hamza seat is read from the `ء` row. The root keeps its own
              spelling, so the page names the row rather than the glyph. */}
          {reading.sheet_letter && reading.sheet_letter !== reading.letter && (
            <p className="mt-1 font-arabic text-[11px] text-gray-400">
              {S.concept.sheetLetter(reading.sheet_letter)}
            </p>
          )}

          <HitList
            id={`concept-realised-${position}`}
            label={S.concept.realisedLabel}
            hits={reading.realised}
            tone="realised"
          />

          {reading.carried.length > 0 && (
            <>
              <HitList
                id={`concept-carried-${position}`}
                label={S.concept.carriedLabel}
                hits={reading.carried}
                tone="carried"
              />
              <p className="mt-1 font-arabic text-[11px] leading-relaxed text-gray-400">
                {S.concept.carriedNote}
              </p>
            </>
          )}

          <RarityOrder position={position} hits={reading.ordered} />
        </>
      )}
    </article>
  );
}

/** One position's primitives, in the order the composer produced them. The
 *  primitive's own name opens each row: everything after it — the gloss, the
 *  badge, the coverage — is apparatus around a word that is never re-worded. */
function HitList({
  id,
  label,
  hits,
  tone,
}: {
  id: string;
  label: string;
  hits: PrimitiveHit[];
  tone: "realised" | "carried";
}) {
  const realised = tone === "realised";

  return (
    <div className="mt-3">
      <h4
        id={id}
        className={`font-arabic text-xs ${
          realised ? "font-semibold text-gray-700" : "text-gray-400"
        }`}
      >
        {label}
      </h4>
      <ol
        aria-labelledby={id}
        className={`mt-1 space-y-1 ${realised ? "" : "opacity-70"}`}
      >
        {hits.map((hit) => (
          <li
            key={`${hit.primitive}-${hit.declaration_index}`}
            className="flex flex-wrap items-baseline gap-1.5"
          >
            <span
              className={`font-arabic ${
                realised ? "text-base text-gray-800" : "text-sm text-gray-600"
              }`}
            >
              {hit.primitive}
            </span>
            <StatusBadge status={hit.status} />
            <span className="font-arabic text-[11px] text-gray-500">
              {hit.gloss_ar}
            </span>
            <span
              title={S.concept.coverageTitle}
              className="rounded bg-gray-100 px-1.5 py-0.5 font-arabic text-[11px] text-gray-500"
            >
              {S.concept.coverage(hit.coverage)}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** The whole rarity order with its coverage figures — the cut between realised
 *  and carried is a consequence of these numbers, and printing them is what lets
 *  a reader redo the ordering instead of taking it on trust. */
function RarityOrder({
  position,
  hits,
}: {
  position: string;
  hits: PrimitiveHit[];
}) {
  if (hits.length === 0) return null;
  const id = `concept-ordered-${position}`;

  return (
    <div className="mt-3 border-t border-gray-100 pt-2">
      <h4 id={id} className="font-arabic text-[11px] text-gray-400">
        {S.concept.orderedLabel}
      </h4>
      <ol aria-labelledby={id} className="mt-1 flex flex-wrap gap-1">
        {hits.map((hit) => (
          <li
            key={`${hit.primitive}-${hit.declaration_index}`}
            className="rounded bg-gray-50 px-1.5 py-0.5 font-arabic text-[11px] text-gray-500"
          >
            {hit.primitive} · {S.concept.coverage(hit.coverage)}
          </li>
        ))}
      </ol>
      <p className="mt-1 font-arabic text-[11px] leading-relaxed text-gray-400">
        {S.concept.orderedNote}
      </p>
    </div>
  );
}

/* ── The ground truth, beside its reading aid ───────────────────────────── */

/** The chain exactly as the composer returned it. It is shown verbatim because it
 *  is the thing that was recorded and measured — the groups above are a way of
 *  reading it, not a version of it. */
function RecordedChain({ concept }: { concept: Concept }) {
  if (!concept.sentence) return null;

  return (
    <section
      aria-labelledby="concept-sentence"
      className="rounded-lg border border-gray-200 bg-gray-50 p-4"
    >
      <h3
        id="concept-sentence"
        className="font-arabic font-semibold text-gray-800"
      >
        {S.concept.sentenceHeading}
      </h3>
      <p className="mt-2 whitespace-pre-wrap font-arabic text-lg leading-relaxed text-gray-800">
        {concept.sentence}
      </p>
      <p className="mt-2 font-arabic text-xs leading-relaxed text-gray-500">
        {S.concept.sentenceNote}
      </p>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-arabic text-[11px] text-gray-400">
        <span>{S.concept.sentenceSource[concept.sentence_source]}</span>
        <span dir="auto">{S.concept.lockVersion(concept.lock_version)}</span>
      </div>

      {/* Only ever set when a phrasing was produced AND vetoed. */}
      {concept.phrasing_rejection && (
        <div className="mt-2 rounded border border-amber-200 bg-amber-50 p-2">
          <h4 className="font-arabic text-xs font-semibold text-amber-900">
            {S.concept.phrasingRejectionHeading}
          </h4>
          <p className="mt-1 font-arabic text-sm leading-relaxed text-amber-800">
            {concept.phrasing_rejection}
          </p>
        </div>
      )}
    </section>
  );
}

/* ── The two failures, kept apart ───────────────────────────────────────── */

/** The rule does not reach this root at all. A stated reason, not an empty panel:
 *  «the composition rule covers three positions only» IS the answer. */
function Refusal({ concept }: { concept: Concept }) {
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
      <h3 className="flex items-center gap-2 font-arabic font-semibold text-amber-900">
        <TriangleAlert aria-hidden className="h-4 w-4 shrink-0" />
        {S.concept.refusedHeading}
      </h3>
      <p className="mt-1 font-arabic leading-relaxed text-amber-800">
        {concept.refusal_reason}
      </p>
    </div>
  );
}

/** A letter yielded nothing, so the concept is honestly short by that position.
 *  A DIFFERENT fact from a refusal — the rule applied here — and it gets its own
 *  banner so the two can never be read as one state. */
function PartialBanner({ letters }: { letters: string[] }) {
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-3">
      <h3 className="flex items-center gap-2 font-arabic font-semibold text-amber-900">
        <TriangleAlert aria-hidden className="h-4 w-4 shrink-0" />
        {S.concept.partialHeading}
      </h3>
      {letters.length > 0 && (
        <p className="mt-1 font-arabic text-sm text-amber-800">
          {S.concept.partialLetters(letters.join(" · "))}
        </p>
      )}
    </div>
  );
}

/* ── 9.5 — the two engines, side by side and undecided ──────────────────── */

function Comparison({
  concept,
  confrontation,
  lisan,
  reservation,
}: {
  concept: Concept;
  confrontation: Confrontation;
  lisan: LisanResponse | null;
  reservation: string;
}) {
  // Only a constrained reading has a synthesis to set beside the مفهوم. On the
  // unconstrained path the other engine composes nothing at all — which is stated,
  // not filled in with its inventory.
  const readings =
    lisan?.constrained === true
      ? lisan.readings.filter((reading) => reading.synthesis)
      : [];

  return (
    <section aria-labelledby="concept-comparison">
      <h3
        id="concept-comparison"
        className="flex items-center gap-2 font-arabic font-semibold text-gray-800"
      >
        <Scale aria-hidden className="h-4 w-4 shrink-0" />
        {S.concept.comparisonHeading}
      </h3>
      <p className="mb-2 font-arabic text-sm leading-relaxed text-gray-500">
        {S.concept.comparisonNote}
      </p>

      {/* Two panels of the same weight, same border, same ground: the layout is
          part of the claim that neither has been preferred. */}
      <div className="grid gap-3 md:grid-cols-2">
        <article className="rounded-lg border border-gray-200 bg-white p-3">
          <h4 className="font-arabic text-sm font-semibold text-gray-700">
            {S.concept.physicsSide}
          </h4>
          <p className="mt-2 whitespace-pre-wrap font-arabic leading-relaxed text-gray-800">
            {concept.refused ? S.concept.refusedSide : concept.sentence}
          </p>
        </article>

        <article className="rounded-lg border border-gray-200 bg-white p-3">
          <h4 className="font-arabic text-sm font-semibold text-gray-700">
            {S.concept.coreSide}
          </h4>
          {readings.length > 0 ? (
            <div className="mt-2 space-y-3">
              {readings.map((reading, i) => (
                <div key={`${reading.core.gloss}-${i}`}>
                  {readings.length > 1 && (
                    <p className="font-arabic text-xs text-gray-500">
                      {S.lexical.readingOn(reading.core.gloss)}
                    </p>
                  )}
                  <p className="whitespace-pre-wrap font-arabic leading-relaxed text-gray-800">
                    {reading.synthesis}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            // «it composed no reading» and «it never answered» are different
            // facts, and the second must not be published as the first: a failed
            // request would otherwise read as a finding about the root.
            <p className="mt-2 font-arabic leading-relaxed text-gray-500">
              {lisan === null
                ? S.concept.noCoreAnswer
                : S.concept.noCoreReading}
            </p>
          )}
        </article>
      </div>

      <AslCitation
        cores={confrontation.cores}
        status={confrontation.core_status}
      />

      <p className="mt-3 font-arabic text-sm text-gray-600">
        {S.concept.occurrences(confrontation.occurrences)}
      </p>

      <Uses uses={confrontation.uses} />

      <Verdict confrontation={confrontation} reservation={reservation} />
    </section>
  );
}

/** Ibn Fāris' own words, quoted — and when there are none, WHOSE silence that is.
 *  The keyed half of that sentence is what separates our untranscribed gap from
 *  his entry actually stating no aṣl; one sentence for all three is what told a
 *  reader that Maqāyīs holds no aṣl for حرب, where he gives three. */
function AslCitation({
  cores,
  status,
}: {
  cores: RootCore[];
  status: Confrontation["core_status"];
}) {
  if (cores.length === 0) {
    // An absent or unknown status reads as OUR gap: an unknown reason must never
    // be published as «Ibn Fāris states no aṣl».
    const whose =
      (status && S.lexical.noCoreHeading[status]) ||
      S.lexical.noCoreHeadingFallback;
    return (
      <p className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-3 font-arabic text-sm leading-relaxed text-gray-600">
        {S.concept.noCoreLead}
        {whose}
      </p>
    );
  }

  return (
    <div className="mt-3 space-y-2">
      <h4 className="font-arabic text-sm font-semibold text-gray-700">
        {S.concept.aslHeading}
      </h4>
      <p className="font-arabic text-xs leading-relaxed text-gray-500">
        {S.concept.aslNote}
      </p>
      {cores.map((core, i) => (
        <div
          key={`${core.gloss}-${i}`}
          className="rounded-lg border border-gray-200 bg-white p-3"
        >
          {/* His words, not ours. The quotation mark is an icon rather than a
              character: a mirrored glyph resolves its direction from the run
              around it, an SVG never does. */}
          <blockquote className="flex gap-2 border-s-4 border-gray-200 p-1">
            <Quote aria-hidden className="h-4 w-4 shrink-0 text-gray-400" />
            <p className="font-arabic leading-relaxed text-gray-800">
              {core.verbatim}
            </p>
          </blockquote>
          <p className="mt-1 font-arabic text-xs text-gray-500" dir="auto">
            {S.lexical.coreSource(core.source, core.edition)}
          </p>
        </div>
      ))}
    </div>
  );
}

/** The senses frozen for this root before its concept existed, each with the
 *  verdict and the reason that lets a reader who disagrees redo the judgement. */
function Uses({ uses }: { uses: AttestedUse[] }) {
  if (uses.length === 0) return null;

  return (
    <div className="mt-3">
      <h4
        id="concept-uses"
        className="font-arabic text-sm font-semibold text-gray-700"
      >
        {S.concept.usesHeading}
      </h4>
      <p className="font-arabic text-xs leading-relaxed text-gray-500">
        {S.concept.usesNote}
      </p>
      <ol aria-labelledby="concept-uses" className="mt-2 space-y-2">
        {uses.map((use, i) => (
          <li
            key={`${use.verse}-${i}`}
            className="rounded-lg border border-gray-200 bg-white p-2"
          >
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-arabic text-gray-800">{use.gloss}</span>
              <span
                dir="auto"
                className="rounded bg-gray-100 px-1.5 py-0.5 font-arabic text-[11px] text-gray-600"
              >
                {use.verse}
              </span>
              <span className="rounded bg-gray-100 px-1.5 py-0.5 font-arabic text-[11px] font-medium text-gray-700">
                {S.concept.useVerdict[use.verdict]}
              </span>
            </div>
            {use.reason && (
              <p className="mt-1 font-arabic text-xs leading-relaxed text-gray-600">
                <span className="text-gray-400">
                  {S.concept.useReasonLabel}
                </span>{" "}
                {use.reason}
              </p>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

/**
 * The coverage verdict, and the reservation that may never be separated from it.
 *
 * The rule is not «show the reservation somewhere on the page»: it travels WITH
 * the number, on the same panel, out in the open. Behind a disclosure or one
 * click away is exactly the shape the spec forbids, because a verdict is read and
 * repeated long before anything under it is opened.
 */
function Verdict({
  confrontation,
  reservation,
}: {
  confrontation: Confrontation;
  reservation: string;
}) {
  return (
    <section
      aria-labelledby="concept-verdict"
      className="mt-3 rounded-lg border border-indigo-200 bg-indigo-50 p-3"
    >
      <div className="flex flex-wrap items-baseline gap-2">
        <h4
          id="concept-verdict"
          className="font-arabic text-sm font-semibold text-indigo-900"
        >
          {S.concept.verdictHeading}
        </h4>
        <span className="font-arabic text-indigo-900">
          {S.concept.verdict[confrontation.verdict]}
        </span>
      </div>

      {/* A published exclusion, never a silence. */}
      <p className="mt-1 font-arabic text-xs text-indigo-800">
        {confrontation.counts_toward_k
          ? S.concept.inWitnessSet
          : S.concept.excludedFromK}
      </p>

      {(confrontation.uses_frozen_at || confrontation.concept_recorded_at) && (
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 font-arabic text-[11px] text-indigo-700">
          {confrontation.uses_frozen_at && (
            <span dir="auto">
              {S.concept.frozenAt(confrontation.uses_frozen_at)}
            </span>
          )}
          {confrontation.concept_recorded_at && (
            <span dir="auto">
              {S.concept.recordedAt(confrontation.concept_recorded_at)}
            </span>
          )}
        </div>
      )}

      {/* The reservation carries its own opening words («تحفُّظٌ يُنشَرُ مع الرقم»),
          so it is rendered whole and unlabelled: a heading of ours in front of it
          would say the same thing twice and read as chrome around the number
          rather than as part of it. */}
      {reservation && (
        <p className="mt-2 border-s-2 border-indigo-300 ps-2 font-arabic text-xs leading-relaxed text-indigo-900">
          {reservation}
        </p>
      )}
    </section>
  );
}
