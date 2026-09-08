import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Amiri stays reserved for Qurʾānic text (design D6).
        arabic: ["Amiri", "Scheherazade New", "serif"],
        // The interface face. `ui` is the explicit handle (`font-ui`); `sans`
        // is overridden to the same stack so Tailwind's preflight makes it the
        // document default — `font-sans` appears nowhere in the source, so the
        // override changes no existing class.
        ui: ["IBM Plex Sans Arabic", "Segoe UI", "system-ui", "sans-serif"],
        sans: ["IBM Plex Sans Arabic", "Segoe UI", "system-ui", "sans-serif"],
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
