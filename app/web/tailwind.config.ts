import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        space: { 950: "#060a14", 900: "#0a1020", 850: "#0d1426", 800: "#111a2e", 700: "#1a2540", 600: "#25324f" },
        lunar: { 50: "#f3f5f8", 100: "#e3e7ee", 200: "#c9ced6", 300: "#aab2bf", 400: "#8b94a5", 500: "#6c7587" },
        mars: { 300: "#f6a77c", 400: "#f08a55", 500: "#e8743b", 600: "#c95a24", 700: "#9c4419" },
        signal: { cyan: "#67d4ee", green: "#4ade80", amber: "#fbbf24", pink: "#f472b6" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: { panel: "0 0 0 1px rgba(148,163,184,0.08), 0 10px 30px -12px rgba(0,0,0,0.6)" },
    },
  },
  plugins: [],
};
export default config;
