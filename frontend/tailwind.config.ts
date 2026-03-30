import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        tv: {
          bg: "rgb(var(--tv-bg) / <alpha-value>)",
          panel: "rgb(var(--tv-panel) / <alpha-value>)",
          "panel-hover": "rgb(var(--tv-panel-hover) / <alpha-value>)",
          border: "rgb(var(--tv-border) / <alpha-value>)",
          text: "rgb(var(--tv-text) / <alpha-value>)",
          muted: "rgb(var(--tv-muted) / <alpha-value>)",
          accent: "rgb(var(--tv-accent) / <alpha-value>)",
          up: "rgb(var(--tv-up) / <alpha-value>)",
          down: "rgb(var(--tv-down) / <alpha-value>)",
          "info-border": "var(--tv-info-border)",
          "info-bg": "var(--tv-info-bg)",
        },
        "pnl-positive": "rgb(var(--tv-up) / <alpha-value>)",
        "pnl-negative": "rgb(var(--tv-down) / <alpha-value>)",
        "pnl-neutral": "rgb(var(--tv-muted) / <alpha-value>)",
      },
    },
  },
  plugins: [],
};
export default config;
