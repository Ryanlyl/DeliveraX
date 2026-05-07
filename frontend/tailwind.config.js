/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: '#2563eb',
          'blue-light': '#3b82f6',
          cyan: '#38bdf8',
        },
      },
    },
  },
  plugins: [],
}
