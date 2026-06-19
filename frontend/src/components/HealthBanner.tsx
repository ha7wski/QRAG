"use client";

import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { health } from "@/lib/api";
import type { HealthStatus } from "@/lib/types";

/**
 * Polls /health and surfaces a banner when the backend is degraded or
 * unreachable, so a failed chat reads as "a service is down" rather than a
 * generic error. Silent when everything is healthy.
 */
export default function HealthBanner() {
  const [state, setState] = useState<HealthStatus | "unreachable" | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const h = await health();
        if (!cancelled) setState(h);
      } catch {
        if (!cancelled) setState("unreachable");
      }
    };
    check();
    const id = setInterval(check, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (state === null) return null;
  if (state !== "unreachable" && state.status === "ok") return null;

  let message: string;
  if (state === "unreachable") {
    message = "Backend unreachable — start it with ./local-dev/start.sh.";
  } else if (state.status === "starting") {
    message = "Backend is still starting up — answers may be unavailable.";
  } else {
    const down = [
      !state.qdrant && "the search index (Qdrant)",
      !state.llm && "the language model (Ollama)",
    ].filter(Boolean);
    message = `Service degraded: ${down.join(" and ") || "a component"} is unavailable. Answers may fail until it recovers.`;
  }

  return (
    <div
      role="status"
      className="mb-3 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
