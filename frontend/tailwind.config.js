/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Sampled directly from the Skill Bay Academy logo.
        brand: {
          maroon: "#8B1D55", // primary — actions, key numbers, active nav
          purple: "#72398C", // secondary — structural accents
          pink: "#DE4F73", // tertiary — highlights, positive deltas
          yellow: "#EFBC19", // warnings, "in progress" states
        },
        surface: {
          DEFAULT: "rgb(var(--surface-r) var(--surface-g) var(--surface-b) / <alpha-value>)",
          dim: "rgb(var(--surface-dim-r) var(--surface-dim-g) var(--surface-dim-b) / <alpha-value>)",
          low: "rgb(var(--surface-low-r) var(--surface-low-g) var(--surface-low-b) / <alpha-value>)",
          container: "rgb(var(--surface-container-r) var(--surface-container-g) var(--surface-container-b) / <alpha-value>)",
          high: "rgb(var(--surface-high-r) var(--surface-high-g) var(--surface-high-b) / <alpha-value>)",
          border: "rgb(var(--surface-border-r) var(--surface-border-g) var(--surface-border-b) / <alpha-value>)",
        },
        ink: {
          DEFAULT: "rgb(var(--ink-r) var(--ink-g) var(--ink-b) / <alpha-value>)",
          muted: "rgb(var(--ink-muted-r) var(--ink-muted-g) var(--ink-muted-b) / <alpha-value>)",
          faint: "rgb(var(--ink-faint-r) var(--ink-faint-g) var(--ink-faint-b) / <alpha-value>)",
        },
        success: "#22C55E",
        warning: "#F59E0B",
        danger: "#EF4444",
      },
      fontFamily: {
        display: ["Geist", "ui-sans-serif", "system-ui", "sans-serif"],
        body: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
      },
      boxShadow: {
        card: "var(--card-shadow)",
      },
    },
  },
  plugins: [],
};
