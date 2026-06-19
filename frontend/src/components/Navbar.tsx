import Link from "next/link";
import { BookOpen, MessageSquare, Search, Type } from "lucide-react";

const links = [
  { href: "/chat", label: "Talk to Quran", icon: MessageSquare },
  { href: "/search", label: "Search Verse", icon: Search },
  { href: "/lexical", label: "Lexical", icon: Type },
];

export default function Navbar() {
  return (
    <header className="border-b border-gray-200 bg-white">
      <nav className="mx-auto flex max-w-4xl items-center gap-6 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold text-brand-dark">
          <BookOpen className="h-5 w-5" />
          Quran RAG
        </Link>
        <div className="flex items-center gap-4 text-sm">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-1.5 text-gray-600 hover:text-brand-dark"
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
