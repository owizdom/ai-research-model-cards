import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'DM Sans'", "system-ui", "sans-serif"],
        serif: ["'Source Serif 4'", "Georgia", "serif"],
        mono: ["JetBrains Mono", "Menlo", "monospace"],
      },
      colors: {
        surface: {
          0: "#FAF9F7",
          1: "#FFFFFF",
          2: "#F0EFEB",
          3: "#E5E4E0",
        },
        border: {
          DEFAULT: "#E0DED8",
          light: "#D0CEC8",
        },
        accent: {
          DEFAULT: "#D97757",
          muted: "#D9775740",
        },
        data: {
          DEFAULT: "#1A7A6D",
          strong: "#1A7A6D",
          moderate: "#1A7A6D66",
          weak: "#1A7A6D26",
          missing: "#F0EFEB",
        },
      },
    },
  },
  plugins: [],
};

export default config;
