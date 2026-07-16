"use client";

import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";

/**
 * Floating "back to top" button. It stays hidden until the page is scrolled past
 * `threshold` pixels, then appears in a fixed corner and smooth-scrolls the
 * window back to the top on click. Handy on long results pages (Verse Study).
 */
export default function ScrollToTop({ threshold = 400 }: { threshold?: number }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > threshold);
    onScroll(); // reflect the current position on mount
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [threshold]);

  if (!visible) return null;

  return (
    <button
      type="button"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      aria-label="العودة إلى الأعلى"
      title="العودة إلى الأعلى"
      className="fixed bottom-6 right-6 z-50 flex h-11 w-11 items-center justify-center rounded-full bg-brand text-white shadow-lg transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand/50"
    >
      <ArrowUp className="h-5 w-5" />
    </button>
  );
}
