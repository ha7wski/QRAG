"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { S } from "@/lib/strings";
import { readPosition, resumeHref } from "@/lib/readingPosition";

/**
 * The «سور القرآن» entry point: resume where the reader left off.
 *
 * A CLIENT component, and it must be — a server-side `redirect()` cannot read
 * the stored position, which lives in the browser. `replace` rather than `push`
 * keeps the hop out of the back history, so Back from a resumed surah returns
 * to the page the reader came from instead of bouncing through here.
 *
 * It renders NO surah of its own: painting one before the hop would flash the
 * wrong text. A neutral loading state is the whole page.
 */
export default function SurahResumePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(resumeHref(readPosition()));
  }, [router]);

  return (
    <div className="flex items-center gap-2 text-gray-500">
      <Loader2 className="h-4 w-4 animate-spin" /> {S.reading.resuming}
    </div>
  );
}
