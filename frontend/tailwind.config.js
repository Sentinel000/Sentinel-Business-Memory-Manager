/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        stone: {
          canvas: "#fafaf9",
          border: "#e8e6e5",
          muted: "#d6d3d1",
        },
        ash: {
          gray: "#a8a29e",
        },
        warm: {
          gray: "#78716c",
        },
        ink: {
          black: "#0c0a09",
        },
        soot: "#1c1917",
        sky: {
          wash: "#c1e1f7",
        },
        cyan: {
          signal: "#3ba6f1",
          edge: "#3398e1",
        },
      },
      borderRadius: {
        cards: "10px",
        inputs: "6px",
        buttons: "9999px",
        feature: "16px",
      },
      boxShadow: {
        card: "rgba(0, 0, 0, 0.05) 0px 4px 16px 0px",
        preview: "rgba(17, 12, 46, 0.12) 0px 12px 45px 0px",
        subtle: "rgba(0, 0, 0, 0.05) 0px 1px 2px 0px",
      },
    },
  },
  plugins: [],
};
