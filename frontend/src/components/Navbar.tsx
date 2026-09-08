"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BookOpen,
  ListTree,
  Menu,
  MessageSquare,
  Type,
  X,
} from "lucide-react";
import { S } from "@/lib/strings";

// Five entries. `/qlisan` keeps its route, its page and its endpoints but leaves
// the navigation (design D11), so it is reachable by direct URL only — which is
// why it is still Arabized and re-directioned like every other route.
const links = [
  { href: "/chat", label: S.nav.chat, icon: MessageSquare },
  { href: "/verse-study", label: S.nav.verseStudy, icon: ListTree },
  { href: "/fassila", label: S.nav.fassila, icon: Activity },
  { href: "/lexical", label: S.nav.lexical, icon: Type },
  { href: "/tahlil", label: S.nav.tahlil, icon: BookOpen },
];

/**
 * Navigation. On md+ it's a persistent sidebar pinned to the inline-start edge —
 * the right, under the document's RTL direction; on small screens it becomes a
 * slide-in drawer opened from a top bar's hamburger (backdrop + item click close
 * it). The active route is highlighted. Main content is offset with `md:ms-64`
 * (see app/layout.tsx).
 */
export default function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <>
      {/* Mobile top bar (hamburger + brand) — hidden on md+. The hamburger is
          first in source order, so RTL puts it at the right on its own. */}
      <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-gray-200 bg-white px-4 py-3 md:hidden">
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label={S.nav.openMenu}
          className="text-gray-700"
        >
          <Menu className="h-6 w-6" />
        </button>
        <Link href="/" className="flex items-center gap-2 text-brand-dark">
          <BookOpen className="h-5 w-5 shrink-0" />
          <span className="font-semibold">{S.app.name}</span>
        </Link>
      </header>

      {/* Drawer backdrop (mobile only, when open). `inset-0` is symmetric, so it
          needs no logical form. */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setOpen(false)}
          aria-hidden
        />
      )}

      {/* Sidebar (md+) / slide-in drawer (mobile).
          `start-0` anchors it to the inline-start edge, and `border-e` puts its
          border on the side facing the content — both follow the document
          direction. The transform does NOT: `translate-x-*` is a CSS transform,
          and transforms are physical. Under RTL the hidden drawer has to slide
          off to the *right*, so the sign is flipped by hand — there is no
          logical utility for it (design D3). */}
      <aside
        className={`fixed inset-y-0 start-0 z-50 flex w-64 flex-col overflow-y-auto border-e border-gray-200 bg-white transition-transform duration-200 md:translate-x-0 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Brand (+ close button on mobile) */}
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
          <Link
            href="/"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 text-brand-dark"
          >
            <BookOpen className="h-6 w-6 shrink-0" />
            <span className="text-lg font-semibold">{S.app.name}</span>
          </Link>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label={S.nav.closeMenu}
            className="text-gray-500 md:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {links.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                /* `bg-gradient-to-l`, not `-to-r`: a linear-gradient direction is
                   physical and never follows `dir`, so under RTL the `-to-r`
                   original put the dark end under the icon and label instead of
                   at the pill's trailing edge. */
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  active
                    ? "bg-gradient-to-l from-brand to-brand-dark text-white shadow-sm"
                    : "text-gray-600 hover:bg-brand-light hover:text-brand-dark"
                }`}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
