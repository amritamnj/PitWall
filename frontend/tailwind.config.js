/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      colors: {
        f1: {
          bg: "#0a0c10",
          surface: "#12141c",
          card: "#181b25",
          border: "#262a36",
          muted: "#3a3f4f",
          text: "#e2e8f0",
          dim: "#8892a8",
          red: "#e10600",
        },
        compound: {
          c1: "#d4d4d8",
          c2: "#a8a8ad",
          c3: "#eab308",
          c4: "#ef4444",
          c5: "#dc2626",
          inter: "#22c55e",
          wet: "#3b82f6",
        },
      },
      boxShadow: {
        glow: "0 0 20px rgba(234, 179, 8, 0.15)",
        "glow-red": "0 0 20px rgba(239, 68, 68, 0.15)",
        "glow-green": "0 0 20px rgba(34, 197, 94, 0.15)",
        "glow-blue": "0 0 20px rgba(59, 130, 246, 0.15)",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
        shimmer: "shimmer 1.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
