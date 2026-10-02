/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        void: "var(--void)",
        "void-elevated": "var(--void-elevated)",
        "void-soft": "var(--void-soft)",
        ash: "var(--ash)",
        "ash-bright": "var(--ash-bright)",
        ink: "var(--ink)",
        "ink-muted": "var(--ink-muted)",
        "ink-faint": "var(--ink-faint)",
        line: "var(--line)",
        "shiva-blue": "var(--shiva-blue)",
        "shiva-bright": "var(--shiva-bright)",
        "shiva-soft": "var(--shiva-soft)",
        cta: "var(--cta)",
        "cta-ink": "var(--cta-ink)",
      },
      fontFamily: {
        sans: ["var(--font-manrope)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        panel: "1.5rem",
        pill: "999px",
      },
    },
  },
  plugins: [],
};
