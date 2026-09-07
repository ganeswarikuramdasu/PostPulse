/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Deep, vibrant plum/violet base — the "entertainment night club" backdrop
        bg: "#170B2E",
        surface: "#221240",
        "surface-hover": "#2A1650",
        "surface-raised": "#33195F",
        border: "#4A2B78",
        "text-primary": "#FDF4FF",
        "text-secondary": "#C4B5FD",
        "text-muted": "#8B7BB8",

        // Lively neon palette: orange → pink → violet
        accent: "#FF6B4A",        // bright orange (primary CTA)
        "accent-orange": "#FF8A4C",
        "accent-pink": "#F43F9E",  // hot pink
        "accent-violet": "#A855F7",// violet
        "accent-teal": "#2DD4BF",  // mint highlight
        "accent-dim": "#3D2218",

        // Score colors (vibrant)
        "score-low": "#FF4D6D",
        "score-medium": "#FFC531",
        "score-high": "#4ADE80",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        glow: "0 0 45px -8px rgba(255, 107, 74, 0.55)",
        "glow-pink": "0 0 45px -8px rgba(244, 63, 158, 0.55)",
        "glow-violet": "0 0 45px -8px rgba(168, 85, 247, 0.55)",
      },
      backgroundImage: {
        "vibrant-cta": "linear-gradient(135deg, #FF8A4C 0%, #F43F9E 55%, #A855F7 100%)",
        "vibrant-hero": "linear-gradient(120deg, #FF8A4C, #F43F9E 45%, #A855F7)",
        "vibrant-text": "linear-gradient(120deg, #FFB175 0%, #F43F9E 45%, #C084FC 100%)",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-12px)" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.5" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        "pulse-glow": "pulse-glow 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
}
