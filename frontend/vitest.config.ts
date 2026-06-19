import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// Vitest is fully separate from `next build` — it transpiles with esbuild and
// never runs as part of the Next pipeline, so it cannot affect the production
// build. Test files and this config are excluded from tsconfig (see exclude),
// so `next build`'s typecheck ignores them too.
export default defineConfig({
  plugins: [react()],
  resolve: {
    // Mirror the tsconfig path alias so tests can import "@/lib/...".
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom", // provides window + localStorage for the storage layer
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    clearMocks: true, // reset mock call state before each test
    restoreMocks: true, // restore spied-on originals after each test (no leakage)
  },
});
