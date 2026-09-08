"use client";

import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { health } from "@/lib/api";
import type { HealthStatus } from "@/lib/types";
import { S } from "@/lib/strings";

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
    // The English original told the reader to run `./local-dev/start.sh`. That
    // path is git-excluded, so a cloner does not have it — naming no path at all
    // is more useful than naming one that may not exist.
    message = S.health.unreachable;
  } else if (state.status === "starting") {
    message = S.health.starting;
  } else {
    const down = [
      !state.qdrant && S.health.partIndex,
      !state.llm && S.health.partModel,
    ].filter(Boolean) as string[];
    // The waw is a proclitic: a space BEFORE it and none after, so `join(" و ")`
    // would be wrong Arabic. Each part already carries its Latin brand name
    // inside FSI/PDI isolates (design D15), without which the parentheses
    // reorder and «(Qdrant)» renders as «)Qdrant(».
    message = S.health.degraded(
      down.join(S.health.and) || S.health.fallbackPart,
    );
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
