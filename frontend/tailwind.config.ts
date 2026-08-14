import type { Config } from "tailwindcss";

// Tokens as CSS custom properties (see src/styles/tokens.css) so light/dark
// swap without a class toggle on every element, and `rgb(var(--x) / <alpha>)`
// so Tailwind's opacity modifiers (bg-accent/10) work on top of a CSS-variable
// color the way they would on a plain Tailwind palette color.
function withOpacity(variable: string) {
  return `rgb(var(${variable}) / <alpha-value>)`;
}

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class"],
  theme: {
    extend: {
      colors: {
        ink: withOpacity("--ink"),
        accent: withOpacity("--accent"),
        paper: withOpacity("--paper"),
        surface: withOpacity("--surface"),
        border: withOpacity("--border"),
        muted: withOpacity("--muted"),
        good: withOpacity("--good"),
        warn: withOpacity("--warn"),
        critical: withOpacity("--critical"),
        info: withOpacity("--info"),
      },
      fontFamily: {
        sans: ["Public Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer 1.6s ease-in-out infinite",
      },
      // Shared card elevation - rest state and hover state, tokenized so
      // every card/panel lifts by the same amount instead of each component
      // hand-typing its own rgb(var(--ink)/…) shadow value.
      boxShadow: {
        card: "0 1px 3px rgb(var(--ink) / 0.05)",
        "card-hover": "0 8px 22px rgb(var(--ink) / 0.08)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
