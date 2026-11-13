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
      },
    },
  },
  plugins: [],
};
