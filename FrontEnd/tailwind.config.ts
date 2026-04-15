import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        soft: "0 20px 60px -28px rgba(15, 23, 42, 0.25)",
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "Noto Sans SC", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;

