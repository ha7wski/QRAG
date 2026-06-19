import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  MessageSquare,
  Search,
  Type,
} from "lucide-react";

const features = [
  {
    href: "/chat",
    icon: MessageSquare,
    title: "Talk to Quran",
    desc: "Ask a question in Arabic, French, or English and get a clear answer grounded in the text — every claim backed by the exact verses it comes from.",
    cta: "Start a conversation",
  },
  {
    href: "/lexical",
    icon: Type,
    title: "Lisan Analysis",
    desc: "Look up an Arabic word by its root and see every place it appears in the Quran, with the shades of meaning it carries across contexts.",
    cta: "Analyze a word",
  },
  {
    href: "/search",
    icon: Search,
    title: "Search Verse",
    desc: "Jump straight to any verse: pick a surah and ayah number to read it in its surrounding context.",
    cta: "Look up a verse",
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
          Explore the Quran, with its sources
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-gray-600">
          A trilingual companion for reading and understanding the Quran — ask
          questions, study the meaning of words, and look up any verse. Every
          answer points you back to the verses themselves.
        </p>
        <div className="flex justify-center gap-3 pt-2">
          <Link
            href="/chat"
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-5 py-2.5 text-white hover:opacity-90"
          >
            <MessageSquare className="h-4 w-4" />
            Talk to Quran
          </Link>
          <Link
            href="/lexical"
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-5 py-2.5 text-gray-700 hover:bg-gray-50"
          >
            <Type className="h-4 w-4" />
            Lisan Analysis
          </Link>
        </div>
      </section>

      {/* Feature cards */}
      <section className="grid gap-4 sm:grid-cols-3">
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
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </span>
          </Link>
        ))}
      </section>

      {/* Note */}
      <p className="mx-auto max-w-2xl text-center text-sm text-gray-400">
        Answers are a first level of exploration and always cite their sources —
        they don&apos;t replace scholarly interpretation (tafsir).
      </p>
    </div>
  );
}
