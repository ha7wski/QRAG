import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  ListTree,
  MessageSquare,
  Type,
} from "lucide-react";
import { S } from "@/lib/strings";

const features = [
  {
    href: "/chat",
    icon: MessageSquare,
    ...S.home.cards.chat,
  },
  {
    href: "/verse-study",
    icon: ListTree,
    ...S.home.cards.verseStudy,
  },
  {
    href: "/lexical",
    icon: Type,
    ...S.home.cards.lexical,
  },
];

export default function HomePage() {
  return (
    <div className="space-y-10 py-4">
      {/* Hero */}
      <section className="space-y-4 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-light">
          <BookOpen className="h-7 w-7 text-brand-dark" />
        </div>
        <h1 className="text-3xl font-semibold text-gray-900 sm:text-4xl">
          {S.home.heading}
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-gray-600">{S.home.lede}</p>
        <div className="flex justify-center gap-3 pt-2">
          <Link
            href="/chat"
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-5 py-2.5 text-white hover:opacity-90"
          >
            <MessageSquare className="h-4 w-4" />
            {S.nav.chat}
          </Link>
          <Link
            href="/lexical"
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-5 py-2.5 text-gray-700 hover:bg-gray-50"
          >
            <Type className="h-4 w-4" />
            {S.nav.lexical}
          </Link>
        </div>
      </section>

      {/* Feature cards */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {features.map(({ href, icon: Icon, title, desc, cta }) => (
          <Link
            key={href}
            href={href}
            className="group flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition hover:border-brand hover:shadow-md"
          >
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-light">
              <Icon className="h-5 w-5 text-brand-dark" />
            </div>
            <h2 className="mb-1 font-semibold text-gray-900">{title}</h2>
            <p className="flex-1 text-sm text-gray-600">{desc}</p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-dark">
              {cta}
              {/* An icon is an SVG: it does not mirror with `dir` (design D14).
                  This arrow means "go here", so under RTL it points left — and
                  the hover nudge follows it, hence the negative sign. */}
              <ArrowLeft className="h-4 w-4 transition group-hover:-translate-x-0.5" />
            </span>
          </Link>
        ))}
      </section>

      {/* Note */}
      <p className="mx-auto max-w-2xl text-center text-sm text-gray-400">
        {S.home.note}
      </p>
    </div>
  );
}
