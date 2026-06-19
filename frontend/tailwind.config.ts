import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        arabic: ["Amiri", "Scheherazade New", "serif"],
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
