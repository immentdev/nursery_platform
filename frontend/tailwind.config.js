/** @type {import('tailwindcss').Config} */
const tok = (name) => `hsl(var(${name}) / <alpha-value>)`;
const steps = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 72, 80, 96];
const spacing = { px: "1px" };
steps.forEach((s) => {
  spacing[String(s)] = s === 0 ? "0px" : `calc(var(--space-unit) * ${s})`;
});

module.exports = {
  blocklist: ["overline"],
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    spacing,
    fontSize: {
      xs: "var(--text-xs)",
      sm: "var(--text-sm)",
      base: "var(--text-base)",
      lg: "var(--text-lg)",
      xl: "var(--text-xl)",
      "2xl": "var(--text-2xl)",
      "3xl": "var(--text-3xl)",
      "4xl": "var(--text-4xl)",
    },
    extend: {
      fontFamily: {
        heading: "var(--font-heading)",
        body: "var(--font-body)",
        mono: "var(--font-mono)",
      },
      maxWidth: { content: "var(--content-max)" },
      width: { sidebar: "var(--sidebar-width)" },
      boxShadow: { card: "var(--shadow-card)" },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      colors: {
        canvas: tok("--color-canvas"),
        surface: tok("--color-surface"),
        subtle: tok("--color-subtle"),
        hoverbg: tok("--color-hover"),
        ink: { DEFAULT: tok("--color-ink"), soft: tok("--color-ink-soft"), muted: tok("--color-ink-muted") },
        line: { DEFAULT: tok("--color-line"), strong: tok("--color-line-strong") },
        brand: { DEFAULT: tok("--color-brand"), hover: tok("--color-brand-hover"), soft: tok("--color-brand-soft"), fg: tok("--color-brand-fg") },
        ok: { bg: tok("--color-ok-bg"), fg: tok("--color-ok-fg") },
        warn: { bg: tok("--color-warn-bg"), fg: tok("--color-warn-fg") },
        danger: { bg: tok("--color-danger-bg"), fg: tok("--color-danger-fg") },
        neutral: { bg: tok("--color-neutral-bg"), fg: tok("--color-neutral-fg") },
        background: tok("--background"),
        foreground: tok("--foreground"),
        card: { DEFAULT: tok("--card"), foreground: tok("--card-foreground") },
        popover: { DEFAULT: tok("--popover"), foreground: tok("--popover-foreground") },
        primary: { DEFAULT: tok("--primary"), foreground: tok("--primary-foreground") },
        secondary: { DEFAULT: tok("--secondary"), foreground: tok("--secondary-foreground") },
        muted: { DEFAULT: tok("--muted"), foreground: tok("--muted-foreground") },
        accent: { DEFAULT: tok("--accent"), foreground: tok("--accent-foreground") },
        destructive: { DEFAULT: tok("--destructive"), foreground: tok("--destructive-foreground") },
        border: tok("--border"),
        input: tok("--input"),
        ring: tok("--ring"),
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
