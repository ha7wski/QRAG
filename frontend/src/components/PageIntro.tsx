"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, Info, type LucideIcon } from "lucide-react";
import { S } from "@/lib/strings";

/**
 * «عن هذه الصفحة» — a short, foldable introduction under a page's heading.
 *
 * Three pieces, because the toggle sits on the heading row while the region
 * sits under the caption, and only the page knows both places:
 * - `usePageIntro(id)` owns the folded state and its persistence;
 * - `PageIntroToggle` is the button for the `h1` row;
 * - `PageIntro` (default) is the region itself.
 *
 * The copy comes from `S.intro.<page>`; the icons stay in the page, since an
 * icon is a component and the dictionary holds strings only.
 */

export interface PageIntroFeature {
  icon: LucideIcon;
  title: string;
  how: string;
}

// localStorage, on the `lib/readingPosition.ts` pattern: SSR-guarded, and every
// access in try/catch — a storage that refuses to answer (private mode, blocked
// site data) leaves the introduction open, which is also the server's render.
const storageKey = (id: string) => `intro.${id}.folded`;

function readFolded(id: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(storageKey(id)) === "1";
  } catch {
    return false;
  }
}

function writeFolded(id: string, folded: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (folded) window.localStorage.setItem(storageKey(id), "1");
    else window.localStorage.removeItem(storageKey(id));
  } catch {
    // Quota or blocked storage: the fold still applies for this visit.
  }
}

/**
 * The folded state of one page's introduction.
 *
 * The server renders it open and the stored value is read in an effect, so the
 * first client render matches the server's. `ready` turns true two frames AFTER
 * that read has been committed: the region enables its fold transition only
 * then, so a page remembered folded does not visibly collapse on load.
 */
export function usePageIntro(id: string) {
  const [open, setOpen] = useState(true);
  const [read, setRead] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setOpen(!readFolded(id));
    setRead(true);
  }, [id]);

  useEffect(() => {
    if (!read) return;
    let second = 0;
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => setReady(true));
    });
    return () => {
      cancelAnimationFrame(first);
      cancelAnimationFrame(second);
    };
  }, [read]);

  const toggle = useCallback(() => {
    setOpen((was) => {
      writeFolded(id, was);
      return !was;
    });
  }, [id]);

  return { open, toggle, regionId: `page-intro-${id}`, ready };
}

/** The ghost button for the heading row: «عن هذه الصفحة» with an info icon and a chevron. */
export function PageIntroToggle({
  open,
  onToggle,
  controls,
}: {
  open: boolean;
  onToggle: () => void;
  controls: string;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      aria-controls={controls}
      className="inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm text-brand-dark transition hover:bg-brand-light focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 motion-reduce:transition-none"
    >
      <Info className="h-4 w-4" aria-hidden="true" />
      {S.intro.toggle}
      <ChevronDown
        className={`h-4 w-4 transition-transform duration-200 motion-reduce:transition-none ${
          open ? "rotate-180" : ""
        }`}
        aria-hidden="true"
      />
    </button>
  );
}

/**
 * The introduction region: one summary sentence and a grid of feature cards.
 *
 * Folding animates the grid row from `1fr` to `0fr` (~200 ms) and is instant
 * under `prefers-reduced-motion`. A folded region is `invisible` and
 * `aria-hidden`, so its cards are neither focusable nor read out; `visibility`
 * is in the transition list so the content stays visible while it collapses.
 *
 * `ready` is `usePageIntro`'s flag; without it the region enables its
 * transition on its own two frames after mount, which is the same guarantee
 * for the usual case where the hook and the region mount together.
 */
export default function PageIntro({
  id,
  summary,
  features,
  open,
  regionId,
  ready,
}: {
  id: string;
  summary: string;
  features: PageIntroFeature[];
  open: boolean;
  regionId?: string;
  ready?: boolean;
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    let second = 0;
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => setMounted(true));
    });
    return () => {
      cancelAnimationFrame(first);
      cancelAnimationFrame(second);
    };
  }, []);
  const animate = ready ?? mounted;

  // Two cards fill a 2-column row and four make a 2 × 2 block on wide screens,
  // rather than leaving an empty third track or a 3 + 1 orphan row.
  const wide =
    features.length === 2 || features.length === 4 ? "lg:grid-cols-2" : "lg:grid-cols-3";

  return (
    <section
      role="region"
      aria-label={S.intro.region}
      id={regionId ?? `page-intro-${id}`}
      aria-hidden={!open}
      className={`grid ${open ? "grid-rows-[1fr]" : "invisible grid-rows-[0fr]"} ${
        animate
          ? "transition-[grid-template-rows,visibility] duration-200 ease-out motion-reduce:transition-none"
          : ""
      }`}
    >
      <div className="min-h-0 overflow-hidden">
        <div className="rounded-xl border border-brand/20 bg-brand-light/40 p-4 sm:p-5">
          <p className="max-w-3xl text-[15px] leading-relaxed text-gray-700">{summary}</p>
          <ul className={`mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 ${wide}`}>
            {features.map(({ icon: Icon, title, how }) => (
              <li key={title} className="rounded-lg border border-gray-200 bg-white p-3">
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-light">
                    <Icon className="h-4 w-4 text-brand-dark" aria-hidden="true" />
                  </span>
                  <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">{how}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
