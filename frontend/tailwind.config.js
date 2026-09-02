/** @type {import('tailwindcss').Config} */
module.exports = {
  // Class strategy, not media: the founder's explicit choice has to win over the
  // OS setting, and the toggle needs something to flip.
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Channels, not hex: Tailwind needs `r g b` to compose an alpha for
        // modifiers like `bg-stone-border/40`, which fourteen places use.
        // Every semantic token resolves through a CSS variable, so `.dark`
        // redefining the variable flips the whole app. Without this, dark mode
        // means adding a `dark:` variant to every colour class in the codebase.
        stone: {
          canvas: "rgb(var(--color-stone-canvas) / <alpha-value>)",
          border: "rgb(var(--color-stone-border) / <alpha-value>)",
          muted: "rgb(var(--color-stone-muted) / <alpha-value>)",
        },
        ash: {
          gray: "rgb(var(--color-ash-gray) / <alpha-value>)",
        },
        warm: {
          gray: "rgb(var(--color-warm-gray) / <alpha-value>)",
        },
        ink: {
          black: "rgb(var(--color-ink-black) / <alpha-value>)",
        },
        soot: "rgb(var(--color-soot) / <alpha-value>)",
        sky: {
          wash: "rgb(var(--color-sky-wash) / <alpha-value>)",
        },
        // The brand accent is the one thing that does not invert: it is the
        // identity, and it carries adequate contrast on both grounds.
        cyan: {
          signal: "#3ba6f1",
          edge: "#3398e1",
        },
        //: A dark chip that stays dark in both themes — brand tiles, selected pills.
        inverse: "rgb(var(--color-inverse) / <alpha-value>)",
        //: The raised surface — cards, inputs, message bubbles.
        surface: "rgb(var(--color-surface) / <alpha-value>)",
      },
      borderRadius: {
        cards: "10px",
        inputs: "6px",
        buttons: "9999px",
        feature: "16px",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        preview: "var(--shadow-preview)",
        subtle: "var(--shadow-subtle)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
