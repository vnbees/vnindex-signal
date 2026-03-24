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
        "pnl-positive": "#16a34a",
        "pnl-negative": "#dc2626",
        "pnl-neutral": "#6b7280",
      },
    },
  },
  plugins: [],
};
export default config;
