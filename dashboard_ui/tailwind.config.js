/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        panel: "var(--panel)",
        line: "var(--line)",
        ink: "var(--text)",
        muted: "var(--muted)",
        navy: { 950: "#133050", 800: "#2c4765" },
        steel: { 500: "#8d9db2", 300: "#b7c5d6", 200: "#d9e3f3" },
        ice: "#f2f7fe",
      },
    },
  },
  plugins: [],
};
