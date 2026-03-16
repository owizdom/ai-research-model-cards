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
          0: "#0a0a0f",
          1: "#111118",
          2: "#18181f",
          3: "#22222c",
        },
        border: "#2a2a36",
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
