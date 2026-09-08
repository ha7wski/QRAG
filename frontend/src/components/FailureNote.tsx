/**
 * The one way this application reports a failure.
 *
 * The sentence the reader sees is always Arabic, chosen by the calling site from
 * the dictionary. Raw exception text is never that sentence — under a network
 * failure it would be the browser's own English string, which is precisely when
 * the reader most needs to understand what happened (design D10).
 *
 * The exception text is still worth keeping, so it is rendered below as a
 * subordinate technical line. It declares BOTH `dir="ltr"`, so it lays out
 * left-to-right inside the RTL document, AND `lang="en"`, so a screen reader
 * does not spell English out with an Arabic voice.
 */

export type Failure = {
  /** The Arabic sentence. Always present, always from the dictionary. */
  text: string;
  /** English diagnostic. Optional, and never promoted to the sentence. */
  detail?: string;
};

export default function FailureNote({
  failure,
  className = "",
  children,
}: {
  failure: Failure;
  /** The host decides the surface — an inline strip, a card, a banner. */
  className?: string;
  /** An affordance the host wants beside the message, e.g. a retry button. */
  children?: React.ReactNode;
}) {
  return (
    <div className={className} role="status">
      <div className="flex items-center justify-between gap-3">
        <span>{failure.text}</span>
        {children}
      </div>
      {failure.detail ? (
        <p
          dir="ltr"
          lang="en"
          className="mt-1 font-mono text-xs opacity-60"
        >
          {failure.detail}
        </p>
      ) : null}
    </div>
  );
}
