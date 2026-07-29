"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  ListTree,
  Menu,
  MessageSquare,
  Type,
  X,
} from "lucide-react";

const links = [
  { href: "/chat", label: "Talk to Quran", icon: MessageSquare },
  { href: "/verse-study", label: "Verse Study", icon: ListTree },
  { href: "/lexical", label: "Lisan Analysis", icon: Type },
];

/**
 * Navigation. On md+ it's a persistent left sidebar; on small screens it becomes
 * a slide-in drawer opened from a top bar's hamburger (backdrop + item click
 * close it). The active route is highlighted. Main content is offset with
 * `md:ml-64` (see app/layout.tsx).
 */
export default function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <>
      {/* Mobile top bar (hamburger + brand) — hidden on md+. */}
      <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-gray-200 bg-white px-4 py-3 md:hidden">
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="فتح القائمة"
          className="text-gray-700"
        >
          <Menu className="h-6 w-6" />
        </button>
        <Link href="/" className="flex items-center gap-2 text-brand-dark">
          <BookOpen className="h-5 w-5 shrink-0" />
          <span className="font-semibold">Quran RAG</span>
        </Link>
      </header>

      {/* Drawer backdrop (mobile only, when open). */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setOpen(false)}
          aria-hidden
        />
      )}

      {/* Sidebar (md+) / slide-in drawer (mobile). */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col overflow-y-auto border-r border-gray-200 bg-white transition-transform duration-200 md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
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
            <span className="text-lg font-semibold">Quran RAG</span>
          </Link>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="إغلاق القائمة"
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
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  active
                    ? "bg-gradient-to-r from-brand to-brand-dark text-white shadow-sm"
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
