import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Menlo", "monospace"],
      },
      colors: {
        surface: {
          0: "#09090b",
          1: "#0f0f13",
          2: "#16161d",
          3: "#1e1e28",
        },
        border: {
          DEFAULT: "#27272f",
          light: "#32323e",
        },
        accent: {
          DEFAULT: "#7c6af7",
          muted: "#7c6af740",
        },
      },
    },
  },
  plugins: [],
};

export default config;
