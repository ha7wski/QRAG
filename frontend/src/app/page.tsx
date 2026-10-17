import Link from "next/link";
import {
  Activity,
  ArrowLeft,
  BookOpen,
  ListOrdered,
  ListTree,
  MessageSquare,
  ScrollText,
  Type,
} from "lucide-react";
import { S } from "@/lib/strings";

// One card per navigation entry, in the navigation's order and with its icon.
const features = [
  {
    href: "/chat",
    icon: MessageSquare,
    ...S.home.cards.chat,
  },
  {
    href: "/surah",
    icon: ScrollText,
    ...S.home.cards.surahs,
  },
  {
    href: "/verse-study",
    icon: ListTree,
    ...S.home.cards.verseStudy,
  },
  {
    href: "/roots",
    icon: ListOrdered,
    ...S.home.cards.roots,
  },
  {
    href: "/lexical",
    icon: Type,
    ...S.home.cards.lexical,
  },
  {
    href: "/fassila",
    icon: Activity,
    ...S.home.cards.fassila,
  },
];

export default function HomePage() {
  return (
    <div className="space-y-12 py-4">
      {/* Hero */}
      <section className="space-y-4 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-light">
          <BookOpen className="h-7 w-7 text-brand-dark" />
        </div>
        <h1 className="text-3xl font-semibold text-gray-900 sm:text-4xl">
          {S.home.heading}
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-gray-600">{S.home.lede}</p>
      </section>

      {/* Feature cards. Six cards fill two rows of three exactly: a 4-column
          grid would leave empty tracks and push a row off the page's centre. */}
      <section className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {features.map(({ href, icon: Icon, title, desc, cta }) => (
          <Link
            key={href}
            href={href}
            className="group flex flex-col rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition hover:border-brand hover:shadow-md"
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-light">
              <Icon className="h-6 w-6 text-brand-dark" />
            </div>
            <h2 className="mb-2 text-lg font-semibold text-gray-900">{title}</h2>
            <p className="flex-1 text-[15px] leading-relaxed text-gray-600">
              {desc}
            </p>
            <span className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-brand-dark">
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
