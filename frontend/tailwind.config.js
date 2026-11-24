/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#dce8ed",
        muted: "#8da3ad",
        canvas: "#f3f6f7",
        navy: "#112d3d",
        ocean: "#24566a",
        teal: "#287f80",
        line: "#dce5e9",
        surface: "#ffffff",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
