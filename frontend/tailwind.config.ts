import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // One stack, twice. Amiri now carries the whole interface, so the
        // Qurʾānic handle (`font-arabic`) and the document default (`sans`,
        // applied to `html` by Tailwind's preflight) are the same list.
        //
        // The second entry is load-bearing, not a fallback: Amiri is declared
        // over the Arabic ranges only (globals.css), so every digit, `2:255`,
        // QAC tag and translation paragraph finds no Amiri face and resolves
        // here — which is how numbers keep the rendering they have today
        // without a class of their own.
        //
        // "Scheherazade New" left the stack with the Amiri Latin subsets: its
        // job was to catch an Amiri that failed to load, and Plex — vendored,
        // self-hosted, already next in line — does that with a face actually
        // guaranteed to be present.
        arabic: ["Amiri", "IBM Plex Sans Arabic", "Segoe UI", "system-ui", "serif"],
        sans: ["Amiri", "IBM Plex Sans Arabic", "Segoe UI", "system-ui", "serif"],
        // The secondary face, first: the explicit opt-out for a surface that
        // must be sans in Arabic too. Used nowhere today — it is the named
        // handle the spec's "secondary face" refers to.
        ui: ["IBM Plex Sans Arabic", "Segoe UI", "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          DEFAULT: "#0e7c66",
          dark: "#0a5c4c",
          light: "#e6f4f0",
        },
      },
    },
  },
  plugins: [],
};

export default config;
