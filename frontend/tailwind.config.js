/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0E1A",
        surface: "#121826",
        "surface-hover": "#171F30",
        "surface-raised": "#1A2233",
        border: "#232C40",
        "text-primary": "#EDF1F7",
        "text-secondary": "#8891A5",
        "text-muted": "#5C6478",
        accent: "#FF6B4A",
        "accent-dim": "#3D241C",
        teal: "#2DD4BF",
        "score-low": "#FB7185",
        "score-medium": "#FBBF24",
        "score-high": "#34D399",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(255, 107, 74, 0.35)",
      },
    },
  },
  plugins: [],
}
