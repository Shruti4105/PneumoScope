const v = (name) => `rgb(var(--c-${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Colours are CSS variables (see index.css) so the signed-in app can switch
      // to the dark theme with one class (.theme-dark) while Home/Login stay light.
      colors: {
        canvas: v("canvas"),
        surface: v("surface"),
        subtle: v("subtle"),
        ink: { DEFAULT: v("ink"), soft: v("ink-soft") },
        muted: { DEFAULT: v("muted"), light: v("muted-light") },
        line: { DEFAULT: v("line"), strong: v("line-strong") },
        brand: {
          50: v("brand-50"), 100: v("brand-100"), 200: v("brand-200"), 500: v("brand-500"),
          600: v("brand-600"), 700: v("brand-700"), 800: v("brand-800"), 900: v("brand-900"),
        },
        sage: { DEFAULT: v("sage"), light: v("sage-light") },
        warn: { DEFAULT: v("warn"), bg: v("warn-bg"), line: v("warn-line") },
        danger: { DEFAULT: v("danger"), bg: v("danger-bg"), line: v("danger-line") },
        ok: { DEFAULT: v("ok"), bg: v("ok-bg"), line: v("ok-line") },
      },
      fontFamily: {
        sans: ['"Inter Variable"', "Inter", "system-ui", "sans-serif"],
        display: ['"Inter Variable"', "Inter", "system-ui", "sans-serif"],
        mono: ['ui-monospace', '"SF Mono"', "Menlo", "Consolas", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      borderRadius: { DEFAULT: "6px", md: "8px", lg: "10px", xl: "12px" },
      boxShadow: {
        card: "0 1px 2px rgba(32,39,37,0.04), 0 1px 1px rgba(32,39,37,0.02)",
        raised: "0 4px 16px -6px rgba(32,39,37,0.10), 0 1px 2px rgba(32,39,37,0.05)",
      },
      maxWidth: { content: "1240px" },
    },
  },
  plugins: [],
};
